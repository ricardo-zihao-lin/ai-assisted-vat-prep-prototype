"""Validation routines for identifying basic VAT data quality issues.

The validation layer captures structural and formatting issues that commonly
appear in spreadsheet-based bookkeeping workflows. The checks are intentionally
simple and interpretable so that they can support a human reviewer without
introducing opaque automated corrections.
"""

import logging

import pandas as pd

LOGGER = logging.getLogger(__name__)

EXPECTED_COLUMNS = ["date", "description", "net_amount", "vat_amount"]
NUMERIC_COLUMNS = ["net_amount", "vat_amount"]


def _build_issue(row_index: int, column: str, issue_type: str, value, message: str) -> dict:
    """Create a structured issue record used across validation outputs."""
    return {
        "row_index": row_index,
        "column": column,
        "issue_type": issue_type,
        "value": value,
        "message": message,
    }


def validate_vat_data(dataframe: pd.DataFrame) -> dict:
    """Perform baseline validation checks on the VAT transaction dataset.

    Parameters
    ----------
    dataframe : pandas.DataFrame
        Input VAT records table produced by the ingestion stage.

    Returns
    -------
    dict
        Dictionary containing a list of structured issue records and a summary
        issue count.

    Notes
    -----
    The validator focuses on high-value, low-complexity checks suitable for a
    research prototype: missing values, duplicated rows, unparseable dates, and
    invalid numeric entries. Findings are reported rather than corrected so that
    the financial record remains under user control.
    """
    LOGGER.info("Running validation checks on VAT dataset")
    issues: list[dict] = []

    if not isinstance(dataframe, pd.DataFrame):
        LOGGER.error("Validation received an invalid input type: %s", type(dataframe).__name__)
        issues.append(
            _build_issue(
                -1,
                "dataframe",
                "invalid_input",
                type(dataframe).__name__,
                "Validation expected a pandas DataFrame.",
            )
        )
        return {
            "issues": issues,
            "issue_count": len(issues),
        }

    for column in EXPECTED_COLUMNS:
        if column not in dataframe.columns:
            LOGGER.warning("Expected column missing from dataset: %s", column)
            issues.append(_build_issue(-1, column, "missing_column", None, "Expected column is missing."))

    # Missing values are surfaced explicitly because absent bookkeeping fields
    # can undermine both tax calculations and later anomaly screening.
    missing_mask = dataframe.isna()
    for row_index, row in missing_mask.iterrows():
        for column, is_missing in row.items():
            if is_missing:
                LOGGER.warning("Missing value detected at row %s, column %s", row_index, column)
                issues.append(
                    _build_issue(row_index, column, "missing_value", dataframe.at[row_index, column], "Value is missing.")
                )

    # Duplicate rows are preserved but flagged, as duplicates may indicate
    # accidental re-entry of transactions rather than legitimate repetition.
    duplicate_mask = dataframe.duplicated(keep=False)
    for row_index in dataframe.index[duplicate_mask]:
        LOGGER.warning("Duplicate row detected at row %s", row_index)
        issues.append(
            _build_issue(row_index, "row", "duplicate_row", None, "Row appears more than once in the dataset.")
        )

    # Date parsing is deferred to pandas so the check remains concise and
    # aligned with the prototype's spreadsheet-oriented workflow.
    if "date" in dataframe.columns:
        parsed_dates = pd.to_datetime(dataframe["date"], errors="coerce")
        invalid_date_mask = dataframe["date"].notna() & parsed_dates.isna()
        for row_index in dataframe.index[invalid_date_mask]:
            LOGGER.warning("Invalid date format detected at row %s", row_index)
            issues.append(
                _build_issue(
                    row_index,
                    "date",
                    "invalid_date_format",
                    dataframe.at[row_index, "date"],
                    "Date could not be parsed.",
                )
            )

    for column in NUMERIC_COLUMNS:
        if column not in dataframe.columns:
            continue

        # Numeric coercion is used only for validation; the source values remain
        # intact so the record can still be reviewed in its original form.
        numeric_values = pd.to_numeric(dataframe[column], errors="coerce")
        invalid_numeric_mask = dataframe[column].notna() & numeric_values.isna()
        for row_index in dataframe.index[invalid_numeric_mask]:
            LOGGER.warning("Invalid numeric format detected at row %s, column %s", row_index, column)
            issues.append(
                _build_issue(
                    row_index,
                    column,
                    "invalid_numeric_format",
                    dataframe.at[row_index, column],
                    "Numeric value could not be parsed.",
                )
            )

    LOGGER.info("Validation completed with %s issues", len(issues))
    return {
        "issues": issues,
        "issue_count": len(issues),
    }
