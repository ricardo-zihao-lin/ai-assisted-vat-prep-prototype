"""Export routines for prototype outputs and audit-oriented artefacts."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from review.review_manager import EMPTY_REVIEW_HISTORY, EMPTY_REVIEW_LOG

LOGGER = logging.getLogger(__name__)
ISSUE_REPORT_COLUMNS = [
    "finding_id",
    "finding_summary",
    "row_index",
    "issue_type",
    "column",
    "checked_column",
    "value",
    "observed_value",
    "anomaly_score",
    "lower_bound",
    "upper_bound",
    "reason",
    "method",
    "message",
    "trigger_reason",
    "trigger_rule",
    "fields_to_check",
    "suggested_action",
    "review_note",
    "date",
    "description",
    "net_amount",
    "vat_amount",
    "category",
]

CONTEXT_COLUMNS = ["date", "description", "net_amount", "vat_amount", "category"]


def _format_value(value: object) -> str:
    if value is None or pd.isna(value):
        return "blank"
    return str(value)


def _format_amount(value: object) -> str:
    numeric_value = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric_value):
        return _format_value(value)
    return f"GBP {float(numeric_value):,.2f}"


def _safe_int(value: object) -> int | None:
    numeric_value = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric_value):
        return None
    return int(numeric_value)


def _attach_prepared_context(issue_rows: pd.DataFrame, prepared_dataframe: pd.DataFrame) -> pd.DataFrame:
    if issue_rows.empty or "row_index" not in issue_rows.columns:
        return issue_rows

    prepared_context = prepared_dataframe.reset_index(names="row_index")
    prepared_context = prepared_context.reindex(columns=["row_index", *CONTEXT_COLUMNS])
    issue_rows = issue_rows.merge(prepared_context, on="row_index", how="left", suffixes=("", "_prepared"))
    for column in CONTEXT_COLUMNS:
        prepared_column = f"{column}_prepared"
        if prepared_column in issue_rows.columns:
            if column not in issue_rows.columns:
                issue_rows[column] = issue_rows[prepared_column]
            else:
                issue_rows[column] = issue_rows[column].where(issue_rows[column].notna(), issue_rows[prepared_column])
            issue_rows = issue_rows.drop(columns=[prepared_column])
    return issue_rows


def _build_metadata(row: pd.Series) -> pd.Series:
    issue_type = str(row.get("issue_type") or "")
    checked_column = row.get("column") or row.get("checked_column") or "record"
    value = row.get("value")
    if pd.isna(value):
        value = row.get("observed_value")

    row_index = _safe_int(row.get("row_index"))
    row_label = "dataset-level" if row_index is None or row_index < 0 else f"row {row_index}"

    if issue_type == "missing_value":
        return pd.Series(
            {
                "finding_summary": f"{row_label}: missing value in {checked_column}",
                "trigger_reason": f"The {checked_column} cell is blank in {row_label}.",
                "trigger_rule": f"The validation check flagged an empty value in the `{checked_column}` field.",
                "fields_to_check": checked_column,
                "suggested_action": "Check the source spreadsheet and decide whether this value should be completed or corrected.",
                "review_note": "This is usually a concrete data-quality problem and should normally be resolved before reuse.",
            }
        )

    if issue_type == "duplicate_row":
        return pd.Series(
            {
                "finding_summary": f"{row_label}: repeated row detected",
                "trigger_reason": f"The full record appears more than once in the uploaded dataset at {row_label}.",
                "trigger_rule": "The validation check compares rows exactly and flags records that are duplicated.",
                "fields_to_check": "full row",
                "suggested_action": "Confirm whether the repeated record is a legitimate repeat or an accidental duplicate entry.",
                "review_note": "This is a review prompt. Some repeated rows can still be legitimate business events.",
            }
        )

    if issue_type == "invalid_date_format":
        return pd.Series(
            {
                "finding_summary": f"{row_label}: unreadable date value",
                "trigger_reason": f"The date value `{_format_value(value)}` could not be parsed in {row_label}.",
                "trigger_rule": "The validation check attempts to parse the date field with pandas and flags unreadable values.",
                "fields_to_check": checked_column,
                "suggested_action": "Check the original date formatting and make sure the spreadsheet stores a valid transaction date.",
                "review_note": "This is usually a concrete data-quality problem and should normally be corrected in the source file.",
            }
        )

    if issue_type == "invalid_numeric_format":
        return pd.Series(
            {
                "finding_summary": f"{row_label}: unreadable numeric value in {checked_column}",
                "trigger_reason": f"The value `{_format_value(value)}` in {checked_column} could not be read as a number.",
                "trigger_rule": f"The validation check coerces `{checked_column}` to numeric form and flags values that fail conversion.",
                "fields_to_check": checked_column,
                "suggested_action": "Check the source amount format and remove text or symbols that stop the value being parsed correctly.",
                "review_note": "This is usually a concrete data-quality problem and should normally be corrected in the source file.",
            }
        )

    if issue_type == "missing_column":
        return pd.Series(
            {
                "finding_summary": f"Missing required column: {checked_column}",
                "trigger_reason": f"The required field `{checked_column}` was not found in the uploaded dataset.",
                "trigger_rule": "The validation check expects the canonical VAT preparation fields to be present before review can proceed cleanly.",
                "fields_to_check": checked_column,
                "suggested_action": "Check the source headings and map the spreadsheet so the required field is present.",
                "review_note": "This is a structural problem rather than a transaction-level warning.",
            }
        )

    if issue_type == "anomaly":
        lower_bound = _format_amount(row.get("lower_bound"))
        upper_bound = _format_amount(row.get("upper_bound"))
        observed_value = _format_amount(row.get("observed_value"))
        return pd.Series(
            {
                "finding_summary": f"{row_label}: unusual {checked_column} value",
                "trigger_reason": f"The observed value {observed_value} sits outside the usual range for this file in {row_label}.",
                "trigger_rule": (
                    f"The IQR screening rule on `{checked_column}` flags values below {lower_bound} "
                    f"or above {upper_bound}."
                ),
                "fields_to_check": checked_column,
                "suggested_action": "Compare the amount against the source record and supporting evidence to decide whether it is legitimately unusual.",
                "review_note": "This is advisory only. It highlights an unusual value and is not proof of error.",
            }
        )

    return pd.Series(
        {
            "finding_summary": f"{row_label}: flagged record",
            "trigger_reason": "The prototype recorded this item for review.",
            "trigger_rule": _format_value(row.get("message") or row.get("reason")),
            "fields_to_check": checked_column,
            "suggested_action": "Review the flagged record in the issue report and compare it with the source spreadsheet.",
            "review_note": "This entry should be reviewed before relying on the exported records.",
        }
    )


def _build_issue_rows(
    prepared_dataframe: pd.DataFrame,
    validation_results: dict,
    anomaly_results: pd.DataFrame,
) -> pd.DataFrame:
    issue_rows = pd.DataFrame(validation_results["issues"])
    if not anomaly_results.empty:
        anomaly_issue_rows = anomaly_results.copy()
        anomaly_issue_rows["issue_type"] = "anomaly"
        anomaly_issue_rows["column"] = anomaly_issue_rows["checked_column"]
        anomaly_issue_rows["value"] = anomaly_issue_rows["observed_value"]
        anomaly_issue_rows["message"] = anomaly_issue_rows["reason"]
        issue_rows = pd.concat([issue_rows, anomaly_issue_rows], ignore_index=True, sort=False)

    issue_rows = _attach_prepared_context(issue_rows, prepared_dataframe)
    if issue_rows.empty:
        return pd.DataFrame(columns=ISSUE_REPORT_COLUMNS)

    metadata_columns = issue_rows.apply(_build_metadata, axis=1)
    issue_rows = pd.concat([issue_rows, metadata_columns], axis=1)
    issue_rows.insert(0, "finding_id", [f"F{index:03d}" for index in range(1, len(issue_rows) + 1)])
    return issue_rows.reindex(columns=ISSUE_REPORT_COLUMNS)


def export_outputs(
    raw_dataframe: pd.DataFrame,
    prepared_dataframe: pd.DataFrame,
    validation_results: dict,
    anomaly_results: pd.DataFrame,
    review_log: pd.DataFrame | None,
    review_history: pd.DataFrame | None,
    output_dir: str | Path,
) -> dict:
    """Export the prototype outputs to CSV files on disk."""
    LOGGER.info("Exporting dataset snapshot and reporting artefacts to %s", output_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    dataset_snapshot_path = output_path / "dataset_snapshot.csv"
    prepared_canonical_records_path = output_path / "prepared_canonical_records.csv"
    issue_report_path = output_path / "issue_report.csv"
    review_log_path = output_path / "review_log.csv"
    review_history_path = output_path / "review_history.csv"

    raw_dataframe.to_csv(dataset_snapshot_path, index=False)
    prepared_dataframe.to_csv(prepared_canonical_records_path, index=False)

    issue_rows = _build_issue_rows(prepared_dataframe, validation_results, anomaly_results)
    issue_rows.to_csv(issue_report_path, index=False)

    (review_log if review_log is not None else EMPTY_REVIEW_LOG.copy()).to_csv(review_log_path, index=False)
    (review_history if review_history is not None else EMPTY_REVIEW_HISTORY.copy()).to_csv(review_history_path, index=False)

    LOGGER.debug(
        "Exported files created: %s, %s, %s, %s, %s",
        dataset_snapshot_path,
        prepared_canonical_records_path,
        issue_report_path,
        review_log_path,
        review_history_path,
    )

    return {
        "dataset_snapshot": dataset_snapshot_path,
        "prepared_canonical_records": prepared_canonical_records_path,
        "issue_report": issue_report_path,
        "review_log": review_log_path,
        "review_history": review_history_path,
    }
