"""Simple statistical anomaly detection for spreadsheet transaction records.

This module highlights unusual transactions using transparent statistical
heuristics that can be readily explained to non-technical reviewers. The design
preference is interpretability: suspicious records are ranked and reported, but
the underlying financial entries are never altered automatically.
"""

import logging

import pandas as pd

LOGGER = logging.getLogger(__name__)
EMPTY_ANOMALY_RESULT = pd.DataFrame(columns=["row_index", "anomaly_score", "reason"])


def detect_anomalies(dataframe: pd.DataFrame, column: str = "net_amount", method: str = "iqr") -> pd.DataFrame:
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
    pandas.DataFrame
        DataFrame containing suspicious rows sorted by anomaly score in
        descending order. An empty DataFrame is returned when no anomalies can
        be identified.

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
        suspicious_rows["reason"] = "Absolute z-score above 2.0"
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
        suspicious_rows["anomaly_score"] = distance.abs()
        suspicious_rows["reason"] = "Outside IQR bounds"

    if suspicious_rows.empty:
        LOGGER.info("No suspicious transactions detected for column %s", column)
        return EMPTY_ANOMALY_RESULT.copy()

    suspicious_rows = suspicious_rows.sort_values("anomaly_score", ascending=False)
    LOGGER.info("Anomaly detection produced %s suspicious rows", len(suspicious_rows))
    LOGGER.debug("Top anomaly rows: %s", suspicious_rows["row_index"].tolist())
    return suspicious_rows
