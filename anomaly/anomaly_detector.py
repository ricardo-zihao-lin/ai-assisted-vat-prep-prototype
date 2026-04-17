"""Simple statistical anomaly detection for spreadsheet transaction records.

This module highlights unusual transactions using transparent statistical
heuristics that can be readily explained to non-technical reviewers. The design
preference is interpretability: suspicious records are ranked and reported, but
the underlying financial entries are never altered automatically.
"""

import logging
from dataclasses import replace
from typing import Any

import numpy as np
import pandas as pd

from review.issue_interpreter import RawIssueSignal, interpret_signal
from review.models import Issue

LOGGER = logging.getLogger(__name__)
EMPTY_ANOMALY_RESULT: list[Issue] = []
MAX_ANOMALY_FLAGS = 50
ANOMALY_RATIO_CAP = 0.02
MIN_CONTEXTUAL_GROUP_SIZE = 4
CONTEXT_COLUMNS = ("customer_supplier_id", "counterparty_ref")


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


def _resolve_context_column(dataframe: pd.DataFrame) -> str | None:
    for column in CONTEXT_COLUMNS:
        if column in dataframe.columns:
            return column
    return None


def _normalise_context_series(series: pd.Series) -> pd.Series:
    """Normalise supplier-context values for grouping without mutating the source data."""
    normalised = series.astype("string").str.strip()
    return normalised.replace("", pd.NA)


def _build_iqr_bounds(series: pd.Series) -> tuple[float, float]:
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1
    lower_bound = q1 - (1.5 * iqr)
    upper_bound = q3 + (1.5 * iqr)
    return float(lower_bound), float(upper_bound)


def _build_review_message(
    *,
    observed_value: Any,
    column: str,
    detection_scope: str,
    context_label: str | None,
) -> str:
    value_text = _normalise_scalar(observed_value)
    scope_text = "contextual" if detection_scope == "contextual" else "global"
    if context_label:
        return (
            f"The {column} value {value_text} is outside the {scope_text} IQR bounds for {context_label}. "
            "Please compare it with the source record and supporting evidence to confirm whether it is legitimate."
        )
    return (
        f"The {column} value {value_text} is outside the {scope_text} IQR bounds. "
        "Please compare it with the source record and supporting evidence to confirm whether it is legitimate."
    )


def _build_anomaly_issue(
    dataframe: pd.DataFrame,
    row_index: int,
    column: str,
    observed_value: Any,
    anomaly_score: float,
    lower_bound: float,
    upper_bound: float,
    method: str,
    detection_scope: str,
    context_label: str | None = None,
) -> Issue:
    """Create one interpreted issue object for an unusual transaction."""
    message = _build_review_message(
        observed_value=observed_value,
        column=column,
        detection_scope=detection_scope,
        context_label=context_label,
    )
    issue = interpret_signal(
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
                "detection_scope": detection_scope,
                "message": message,
                "context_label": context_label,
            },
            evidence_expected="Invoice, receipt, or supporting transaction evidence",
            source_snapshot=_build_source_snapshot(dataframe, row_index),
        )
    )
    possible_vat_review_impact = (
        "The amount is atypical for this supplier context and may need evidence-based confirmation before review is closed."
        if detection_scope == "contextual"
        else "The amount is unusual relative to the wider dataset and may need evidence-based confirmation before review is closed."
    )
    return replace(
        issue,
        detection_summary=message,
        possible_vat_review_impact=possible_vat_review_impact,
        detection_scope=detection_scope,
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
        global_lower_bound, global_upper_bound = _build_iqr_bounds(valid_rows[column])
        context_column = _resolve_context_column(valid_rows)

        effective_lower_bound = pd.Series(global_lower_bound, index=valid_rows.index, dtype="float64")
        effective_upper_bound = pd.Series(global_upper_bound, index=valid_rows.index, dtype="float64")
        detection_scope = pd.Series("global", index=valid_rows.index, dtype="object")
        context_label = pd.Series([None] * len(valid_rows), index=valid_rows.index, dtype="object")

        if context_column is not None:
            context_keys = _normalise_context_series(valid_rows[context_column])
            context_present_mask = context_keys.notna()

            contextual_rows = valid_rows.loc[context_present_mask, [column]].copy()
            contextual_rows["_context_key"] = context_keys.loc[context_present_mask]
            group_quantiles = contextual_rows.groupby("_context_key")[column].quantile([0.25, 0.75]).unstack()
            contextual_group_sizes = context_keys.map(context_keys[context_present_mask].value_counts()).fillna(0).astype(int)

            contextual_q1 = context_keys.map(group_quantiles[0.25]) if not group_quantiles.empty else pd.Series(index=valid_rows.index, dtype="float64")
            contextual_q3 = context_keys.map(group_quantiles[0.75]) if not group_quantiles.empty else pd.Series(index=valid_rows.index, dtype="float64")
            contextual_iqr = contextual_q3 - contextual_q1
            contextual_lower = contextual_q1 - (1.5 * contextual_iqr)
            contextual_upper = contextual_q3 + (1.5 * contextual_iqr)

            contextual_eligible = context_present_mask & (contextual_group_sizes >= MIN_CONTEXTUAL_GROUP_SIZE)
            effective_lower_bound.loc[contextual_eligible] = contextual_lower.loc[contextual_eligible]
            effective_upper_bound.loc[contextual_eligible] = contextual_upper.loc[contextual_eligible]
            detection_scope.loc[contextual_eligible] = "contextual"
            context_label.loc[contextual_eligible] = (
                context_column + "=" + context_keys.loc[contextual_eligible].astype("string")
            )

        anomaly_distance = np.where(
            valid_rows[column] < effective_lower_bound,
            effective_lower_bound - valid_rows[column],
            np.where(valid_rows[column] > effective_upper_bound, valid_rows[column] - effective_upper_bound, 0.0),
        )
        suspicious_mask = anomaly_distance > 0

        suspicious_rows = valid_rows.loc[suspicious_mask].copy()
        suspicious_rows["checked_column"] = column
        suspicious_rows["observed_value"] = suspicious_rows[column]
        suspicious_rows["anomaly_score"] = anomaly_distance[suspicious_mask]
        suspicious_rows["lower_bound"] = effective_lower_bound.loc[suspicious_mask]
        suspicious_rows["upper_bound"] = effective_upper_bound.loc[suspicious_mask]
        suspicious_rows["reason"] = np.where(
            detection_scope.loc[suspicious_mask].eq("contextual"),
            "Outside contextual IQR bounds",
            "Outside global IQR bounds",
        )
        suspicious_rows["method"] = method
        suspicious_rows["detection_scope"] = detection_scope.loc[suspicious_mask].to_numpy()
        suspicious_rows["context_label"] = context_label.loc[suspicious_mask].to_numpy()

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
            detection_scope=str(getattr(row, "detection_scope", "global")),
            context_label=_normalise_scalar(getattr(row, "context_label", None)),
        )
        for row in suspicious_rows.itertuples(index=False)
    ]
