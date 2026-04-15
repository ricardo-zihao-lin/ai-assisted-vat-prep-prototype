"""Simple statistical anomaly detection for spreadsheet transaction records.

This module highlights unusual transactions using transparent statistical
heuristics that can be readily explained to non-technical reviewers. The design
preference is interpretability: suspicious records are ranked and reported, but
the underlying financial entries are never altered automatically.
"""

import logging
from typing import Any

import pandas as pd

from review.issue_interpreter import RawIssueSignal, interpret_signal
from review.models import Issue

LOGGER = logging.getLogger(__name__)
EMPTY_ANOMALY_RESULT: list[Issue] = []
MAX_ANOMALY_FLAGS = 50
ANOMALY_RATIO_CAP = 0.02


def _normalise_scalar(value: Any) -> Any:
    if value is None or pd.isna(value):
        return None
    if hasattr(value, "item"):
        try:
            return value.item()
        except ValueError:
            return value
    return value


def _build_source_snapshot(dataframe: pd.DataFrame, row_index: int) -> dict[str, Any] | None:
    if row_index not in dataframe.index:
        return None
    row = dataframe.loc[row_index]
    return {column: _normalise_scalar(value) for column, value in row.items()}


def _build_anomaly_issue(
    dataframe: pd.DataFrame,
    row_index: int,
    column: str,
    observed_value: Any,
    anomaly_score: float,
    lower_bound: float,
    upper_bound: float,
    method: str,
) -> Issue:
    """Create one interpreted issue object for an unusual transaction."""
    return interpret_signal(
        RawIssueSignal(
            rule_id="VR015",
            row_index=row_index,
            issue_type="unusual_net_amount",
            category="Unusual transaction review",
            field_names=(column,),
            detected_value=_normalise_scalar(observed_value),
            expected_value={
                "lower_bound": float(lower_bound),
                "upper_bound": float(upper_bound),
                "method": method,
                "anomaly_score": float(anomaly_score),
            },
            evidence_expected="Invoice, receipt, or supporting transaction evidence",
            source_snapshot=_build_source_snapshot(dataframe, row_index),
        )
    )


def detect_anomalies(dataframe: pd.DataFrame, column: str = "net_amount", method: str = "iqr") -> list[Issue]:
    """Rank suspicious transactions using a simple univariate method.

    Parameters
    ----------
    dataframe : pandas.DataFrame
        VAT records table to be screened for unusual values.
    column : str, default="net_amount"
        Numeric column on which anomaly screening should be performed.
    method : str, default="iqr"
        Statistical approach used to score anomalies. Supported values are
        ``"iqr"`` and ``"zscore"``.

    Returns
    -------
    list[Issue]
        Structured issue objects representing suspicious rows sorted by
        anomaly score in descending order. An empty list is returned when no
        anomalies can be identified.

    Notes
    -----
    The detector is intentionally lightweight for prototype use. It applies a
    single-variable screening rule to support human review rather than claim a
    comprehensive fraud or error detection capability.
    """
    LOGGER.info("Detecting anomalous transactions using the %s method", method)

    if not isinstance(dataframe, pd.DataFrame):
        LOGGER.error("Anomaly detection received an invalid input type: %s", type(dataframe).__name__)
        return EMPTY_ANOMALY_RESULT.copy()

    if column not in dataframe.columns:
        LOGGER.warning("Anomaly detection skipped because required column is missing: %s", column)
        return EMPTY_ANOMALY_RESULT.copy()

    working_dataframe = dataframe.copy()
    working_dataframe["row_index"] = working_dataframe.index
    # Coercion allows statistical screening while leaving the source dataframe untouched.
    working_dataframe[column] = pd.to_numeric(working_dataframe[column], errors="coerce")

    valid_rows = working_dataframe.dropna(subset=[column]).copy()
    if valid_rows.empty:
        LOGGER.warning("No valid numeric rows available for anomaly detection in column %s", column)
        return EMPTY_ANOMALY_RESULT.copy()

    if method == "zscore":
        mean_value = valid_rows[column].mean()
        std_value = valid_rows[column].std(ddof=0)
        if std_value == 0:
            LOGGER.warning("Anomaly detection skipped because standard deviation is zero for column %s", column)
            return EMPTY_ANOMALY_RESULT.copy()

        # The absolute z-score is used here as a transparent distance-from-mean measure.
        valid_rows["anomaly_score"] = ((valid_rows[column] - mean_value) / std_value).abs()
        suspicious_rows = valid_rows[valid_rows["anomaly_score"] > 2.0].copy()
        suspicious_rows["checked_column"] = column
        suspicious_rows["observed_value"] = suspicious_rows[column]
        suspicious_rows["lower_bound"] = mean_value - (2.0 * std_value)
        suspicious_rows["upper_bound"] = mean_value + (2.0 * std_value)
        suspicious_rows["reason"] = "Absolute z-score above 2.0"
        suspicious_rows["method"] = method
    else:
        q1 = valid_rows[column].quantile(0.25)
        q3 = valid_rows[column].quantile(0.75)
        iqr = q3 - q1
        lower_bound = q1 - (1.5 * iqr)
        upper_bound = q3 + (1.5 * iqr)

        # IQR bounds provide a robust rule-of-thumb for outlier screening in small datasets.
        suspicious_rows = valid_rows[
            (valid_rows[column] < lower_bound) | (valid_rows[column] > upper_bound)
        ].copy()

        distance = pd.Series(0.0, index=suspicious_rows.index)
        distance = distance.where(suspicious_rows[column] >= lower_bound, lower_bound - suspicious_rows[column])
        distance = distance.where(suspicious_rows[column] <= upper_bound, suspicious_rows[column] - upper_bound)
        suspicious_rows["checked_column"] = column
        suspicious_rows["observed_value"] = suspicious_rows[column]
        suspicious_rows["anomaly_score"] = distance.abs()
        suspicious_rows["lower_bound"] = lower_bound
        suspicious_rows["upper_bound"] = upper_bound
        suspicious_rows["reason"] = "Outside IQR bounds"
        suspicious_rows["method"] = method

    if suspicious_rows.empty:
        LOGGER.info("No suspicious transactions detected for column %s", column)
        return EMPTY_ANOMALY_RESULT.copy()

    suspicious_rows = suspicious_rows.sort_values("anomaly_score", ascending=False)
    anomaly_limit = min(MAX_ANOMALY_FLAGS, max(10, int(len(valid_rows) * ANOMALY_RATIO_CAP)))
    if len(suspicious_rows) > anomaly_limit:
        LOGGER.info(
            "Anomaly detection produced %s suspicious rows for %s, keeping the top %s most severe items for review usability",
            len(suspicious_rows),
            column,
            anomaly_limit,
        )
        suspicious_rows = suspicious_rows.head(anomaly_limit).copy()
    else:
        LOGGER.info("Anomaly detection produced %s suspicious rows", len(suspicious_rows))
    LOGGER.debug("Top anomaly rows: %s", suspicious_rows["row_index"].tolist())
    return [
        _build_anomaly_issue(
            dataframe=dataframe,
            row_index=int(row.row_index),
            column=column,
            observed_value=row.observed_value,
            anomaly_score=float(row.anomaly_score),
            lower_bound=float(row.lower_bound),
            upper_bound=float(row.upper_bound),
            method=str(row.method),
        )
        for row in suspicious_rows.itertuples(index=False)
    ]
