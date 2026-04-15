"""Export routines for prototype outputs and audit-oriented artefacts."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from uuid import uuid4

import pandas as pd

from ingestion.input_preparation import INPUT_DIAGNOSTIC_COLUMNS, PreparationResult, build_input_diagnostics
from review.models import Issue, issues_to_records
from review.review_manager import EMPTY_REVIEW_HISTORY, EMPTY_REVIEW_LOG

LOGGER = logging.getLogger(__name__)
ISSUE_REPORT_COLUMNS = [
    "issue_id",
    "rule_id",
    "record_id",
    "finding_id",
    "finding_summary",
    "row_index",
    "issue_type",
    "issue_category",
    "status",
    "risk_level",
    "determinism_type",
    "review_state",
    "detected_at",
    "column",
    "field_names",
    "detected_value",
    "expected_value",
    "evidence_expected",
    "checked_column",
    "value",
    "observed_value",
    "anomaly_score",
    "lower_bound",
    "upper_bound",
    "reason",
    "method",
    "message",
    "why_it_matters",
    "possible_vat_review_impact",
    "recommended_manual_check",
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

CONTEXT_COLUMNS = [
    "date",
    "invoice_reference",
    "description",
    "net_amount",
    "vat_amount",
    "gross_amount",
    "counterparty_ref",
    "document_reference",
    "category",
]
SUMMARY_OPEN_STATES = {"open", "in_review", "escalated"}
REVIEW_SIGNAL_ISSUE_TYPES = {
    "unusual_net_amount",
    "negative_or_unusually_low_net_amount",
    "suspicious_zero_value_amount_combination",
}
REVIEW_SUMMARY_COLUMNS = [
    "summary_id",
    "dataset_id",
    "source_filename",
    "generated_at",
    "total_records",
    "records_with_issues",
    "records_without_issues",
    "total_issues",
    "issues_by_status",
    "issues_by_risk",
    "issues_by_review_state",
    "issues_by_category",
    "issues_by_rule",
    "decisions_by_type",
    "corrected_issue_count",
    "false_positive_count",
    "accepted_with_note_count",
    "excluded_record_count",
    "unresolved_issue_count",
    "high_risk_open_count",
    "escalated_issue_count",
    "review_completion_rate",
    "is_review_complete",
    "completion_criteria_note",
    "summary_note",
    "generated_by",
]
INPUT_DIAGNOSTIC_FILE_NAME = "input_diagnostics.csv"


def _decision_to_review_state(decision: str) -> str:
    mapping = {
        "pending": "open",
        "confirmed_issue": "in_review",
        "corrected": "corrected",
        "accepted_with_note": "accepted_with_note",
        "false_positive": "false_positive",
        "excluded_from_review_set": "excluded",
        "escalated": "escalated",
    }
    return mapping.get(str(decision or "").strip().lower(), "open")


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


def _flatten_issue_records(issues: list[Issue] | list[dict]) -> pd.DataFrame:
    """Convert schema-aligned issues into a dataframe compatible with exports."""
    records: list[dict] = []
    for issue in issues_to_records(issues):
        record = dict(issue)
        record["issue_id"] = record.get("issue_id")
        record["finding_id"] = record.get("issue_id")
        record["issue_category"] = record.get("category")
        record.pop("category", None)

        field_names = record.get("field_names") or []
        if isinstance(field_names, str):
            field_names = [field_names]
        record["field_names"] = ", ".join(field_names)

        if "column" not in record:
            record["column"] = field_names[0] if field_names else None
        if "checked_column" not in record:
            record["checked_column"] = record.get("column")

        detected_value = record.get("detected_value")
        record["value"] = detected_value
        record["message"] = record.get("detection_summary")

        if record.get("issue_type") in REVIEW_SIGNAL_ISSUE_TYPES:
            expected_value = record.get("expected_value") or {}
            if isinstance(expected_value, dict):
                record["observed_value"] = detected_value
                record["anomaly_score"] = expected_value.get("anomaly_score")
                record["lower_bound"] = expected_value.get("lower_bound")
                record["upper_bound"] = expected_value.get("upper_bound")
                record["reason"] = record.get("detection_summary")
                record["method"] = expected_value.get("method")

        source_snapshot = record.get("source_snapshot") or {}
        if isinstance(source_snapshot, dict):
            for context_column in CONTEXT_COLUMNS:
                record.setdefault(context_column, source_snapshot.get(context_column))

        records.append(record)

    return pd.DataFrame(records)


def _build_metadata(row: pd.Series) -> pd.Series:
    issue_type = str(row.get("issue_type") or "")
    checked_column = row.get("column") or row.get("checked_column") or "record"
    value = row.get("value")
    if pd.isna(value):
        value = row.get("observed_value")

    row_index = _safe_int(row.get("row_index"))
    row_label = "dataset-level" if row_index is None or row_index < 0 else f"row {row_index}"

    if issue_type in {"missing_transaction_date", "missing_net_amount", "missing_vat_amount", "missing_required_review_field"}:
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

    if issue_type == "exact_duplicate_row":
        return pd.Series(
            {
                "finding_summary": f"{row_label}: repeated row detected",
                "trigger_reason": f"The full record appears more than once in the uploaded dataset at {row_label}.",
                "trigger_rule": "The validation check compares rows exactly and flags records that are duplicated.",
                "fields_to_check": "full row",
                "suggested_action": "Confirm whether the repeated record is a legitimate repeat or an accidental duplicate entry.",
                "review_note": (
                    "This is a high-priority record-quality issue. Resolve it or document why the repeated row is "
                    "acceptable before treating it as review-complete."
                ),
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

    if issue_type in {"non_numeric_net_amount", "non_numeric_vat_amount"}:
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

    if issue_type == "unusual_net_amount":
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

    if issue_type in {"blank_description", "missing_transaction_category_support_field"}:
        return pd.Series(
            {
                "finding_summary": f"{row_label}: review support detail is missing",
                "trigger_reason": f"The {checked_column} field is blank in {row_label}.",
                "trigger_rule": f"The review-support rule flagged missing context in `{checked_column}`.",
                "fields_to_check": checked_column,
                "suggested_action": "Check the source record and add enough context for the transaction to be reviewed with confidence.",
                "review_note": "This does not automatically make the record invalid, but it reduces review clarity and traceability.",
            }
        )

    if issue_type == "negative_or_unusually_low_net_amount":
        return pd.Series(
            {
                "finding_summary": f"{row_label}: negative or unusually low net amount",
                "trigger_reason": f"The net amount in {row_label} is negative or unexpectedly low for ordinary review use.",
                "trigger_rule": "The review rule flags negative or unusually low net amounts because they often need extra context.",
                "fields_to_check": checked_column,
                "suggested_action": "Confirm whether the record is a refund, credit, reversal, or another legitimate negative transaction.",
                "review_note": "This is a review signal rather than proof of error.",
            }
        )

    if issue_type == "suspicious_zero_value_amount_combination":
        return pd.Series(
            {
                "finding_summary": f"{row_label}: suspicious zero-value amount combination",
                "trigger_reason": f"Net and VAT amounts are both zero in {row_label}.",
                "trigger_rule": "The review rule flags all-zero amount combinations because they may represent placeholders or incomplete records.",
                "fields_to_check": "net_amount, vat_amount",
                "suggested_action": "Confirm whether the record should remain in the dataset and document why the zero-value combination is acceptable.",
                "review_note": "This is a low-risk review prompt and should be resolved with a short note or exclusion decision.",
            }
        )

    if issue_type == "duplicate_invoice_reference":
        return pd.Series(
            {
                "finding_summary": f"{row_label}: repeated invoice reference detected",
                "trigger_reason": f"The invoice reference `{_format_value(value)}` appears more than once in the dataset.",
                "trigger_rule": "The review rule flags repeated invoice references because they may indicate duplication or another repeated-record pattern.",
                "fields_to_check": checked_column,
                "suggested_action": "Compare the related rows and confirm whether the repeated invoice reference is legitimate.",
                "review_note": "This is a high-value review signal and should be checked against source evidence before acceptance.",
            }
        )

    if issue_type == "inconsistent_totals":
        return pd.Series(
            {
                "finding_summary": f"{row_label}: inconsistent net, VAT, and gross amounts",
                "trigger_reason": "The gross amount does not reconcile with net amount plus VAT amount within the configured tolerance.",
                "trigger_rule": "The amount consistency rule checks arithmetic agreement between related amount fields.",
                "fields_to_check": "net_amount, vat_amount, gross_amount",
                "suggested_action": "Check the source invoice or export and confirm which amount should be corrected.",
                "review_note": "This is normally a concrete data-quality issue rather than a soft review prompt.",
            }
        )

    if issue_type == "missing_counterparty_reference":
        return pd.Series(
            {
                "finding_summary": f"{row_label}: counterparty reference is missing",
                "trigger_reason": f"The {checked_column} field is blank in {row_label}.",
                "trigger_rule": "The traceability rule flags missing counterparty references when the dataset uses them for review.",
                "fields_to_check": checked_column,
                "suggested_action": "Add the supplier, customer, or counterparty reference from the source evidence if available.",
                "review_note": "This does not always make the record invalid, but it weakens traceability and review confidence.",
            }
        )

    if issue_type == "missing_evidence_reference":
        return pd.Series(
            {
                "finding_summary": f"{row_label}: document or evidence reference is missing",
                "trigger_reason": f"The {checked_column} field is blank in {row_label}.",
                "trigger_rule": "The evidence traceability rule flags missing document references where the dataset uses them for review support.",
                "fields_to_check": checked_column,
                "suggested_action": "Record the invoice number, receipt reference, attachment name, or other evidence identifier for this row.",
                "review_note": "This is a traceability issue that should normally be resolved or explicitly noted during review.",
            }
        )

    if issue_type == "conflicting_amount_sign_pattern":
        return pd.Series(
            {
                "finding_summary": f"{row_label}: conflicting sign pattern across amount fields",
                "trigger_reason": "Related amount fields contain a mixed sign pattern that does not match the expected transaction shape.",
                "trigger_rule": "The amount consistency rule checks whether net, VAT, and gross fields follow a coherent sign pattern.",
                "fields_to_check": "net_amount, vat_amount, gross_amount",
                "suggested_action": "Check whether the row is a credit, refund, reversal, or incorrectly entered transaction and record the evidence reviewed.",
                "review_note": "This is a high-priority review signal because sign conflicts are easy to misinterpret.",
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
    anomaly_results: list[Issue],
) -> pd.DataFrame:
    combined_issues = [*validation_results["issues"], *anomaly_results]
    issue_rows = _flatten_issue_records(combined_issues)

    issue_rows = _attach_prepared_context(issue_rows, prepared_dataframe)
    if issue_rows.empty:
        return pd.DataFrame(columns=ISSUE_REPORT_COLUMNS)

    metadata_columns = issue_rows.apply(_build_metadata, axis=1)
    issue_rows = pd.concat([issue_rows, metadata_columns], axis=1)
    return issue_rows.reindex(columns=ISSUE_REPORT_COLUMNS)


def _json_counts(series: pd.Series) -> str:
    if series.empty:
        return json.dumps({})
    counts = series.dropna().astype(str).value_counts().sort_index().to_dict()
    return json.dumps(counts)


def _build_summary_note(
    total_issues: int,
    records_with_issues: int,
    unresolved_issue_count: int,
    escalated_issue_count: int,
    high_risk_open_count: int,
) -> str:
    if total_issues == 0:
        return "No issues were detected under the prototype's implemented checks for this review run."

    parts = [
        f"{total_issues} issue(s) were detected across {records_with_issues} record(s).",
    ]
    if unresolved_issue_count > 0:
        parts.append(f"{unresolved_issue_count} issue(s) remain unresolved.")
    if high_risk_open_count > 0:
        parts.append(f"{high_risk_open_count} unresolved issue(s) are high risk.")
    if escalated_issue_count > 0:
        parts.append(f"{escalated_issue_count} issue(s) are escalated for further review.")
    if unresolved_issue_count == 0 and escalated_issue_count == 0:
        parts.append("All generated issues have recorded review outcomes under the prototype workflow.")
    return " ".join(parts)


def _build_review_summary(
    issue_rows: pd.DataFrame,
    prepared_dataframe: pd.DataFrame,
    review_log: pd.DataFrame,
    *,
    dataset_id: str,
    source_filename: str | None,
) -> pd.DataFrame:
    summary_issue_rows = issue_rows.copy()
    if not summary_issue_rows.empty and review_log is not None and not review_log.empty:
        latest_review = review_log.copy()
        if "issue_id" not in latest_review.columns and "finding_id" in latest_review.columns:
            latest_review["issue_id"] = latest_review["finding_id"]
        latest_review["decision"] = latest_review.get("decision", "").astype(str)
        latest_review["review_state_from_decision"] = latest_review["decision"].map(_decision_to_review_state)
        latest_review = latest_review.drop_duplicates(subset=["issue_id"], keep="last")
        summary_issue_rows = summary_issue_rows.merge(
            latest_review[["issue_id", "decision", "review_state_from_decision"]],
            on="issue_id",
            how="left",
        )
        summary_issue_rows["review_state"] = summary_issue_rows["review_state_from_decision"].where(
            summary_issue_rows["review_state_from_decision"].notna(),
            summary_issue_rows["review_state"],
        )
        summary_issue_rows = summary_issue_rows.drop(columns=["review_state_from_decision"])

    total_records = len(prepared_dataframe)
    total_issues = len(summary_issue_rows)
    records_with_issues = 0
    if not summary_issue_rows.empty and "record_id" in summary_issue_rows.columns:
        records_with_issues = int(summary_issue_rows["record_id"].dropna().astype(str).nunique())
    records_without_issues = max(total_records - records_with_issues, 0)

    review_state_series = summary_issue_rows["review_state"] if "review_state" in summary_issue_rows.columns else pd.Series(dtype="object")
    unresolved_issue_count = int(review_state_series.astype(str).isin(SUMMARY_OPEN_STATES).sum()) if not review_state_series.empty else 0
    high_risk_open_count = 0
    if not summary_issue_rows.empty and {"review_state", "risk_level"}.issubset(summary_issue_rows.columns):
        high_risk_open_count = int(
            (
                summary_issue_rows["review_state"].astype(str).isin(SUMMARY_OPEN_STATES)
                & summary_issue_rows["risk_level"].astype(str).eq("High")
            ).sum()
        )
    escalated_issue_count = int(review_state_series.astype(str).eq("escalated").sum()) if not review_state_series.empty else 0

    decision_series = review_log["decision"] if review_log is not None and not review_log.empty and "decision" in review_log.columns else pd.Series(dtype="object")
    corrected_issue_count = int(decision_series.astype(str).eq("corrected").sum()) if not decision_series.empty else 0
    false_positive_count = int(decision_series.astype(str).eq("false_positive").sum()) if not decision_series.empty else 0
    accepted_with_note_count = int(decision_series.astype(str).eq("accepted_with_note").sum()) if not decision_series.empty else 0
    excluded_record_count = int(decision_series.astype(str).eq("excluded_from_review_set").sum()) if not decision_series.empty else 0
    resolved_issue_count = total_issues - unresolved_issue_count
    review_completion_rate = 0.0 if total_issues == 0 else round((resolved_issue_count / total_issues) * 100.0, 1)
    is_review_complete = high_risk_open_count == 0 and unresolved_issue_count == 0

    if is_review_complete:
        completion_criteria_note = "All generated issues have reached closed review states under the prototype workflow."
    else:
        completion_criteria_note = (
            "Review is not complete because one or more issues remain open, in review, or escalated under the prototype workflow."
        )

    summary_record = {
        "summary_id": f"SUM-{uuid4().hex[:12].upper()}",
        "dataset_id": dataset_id,
        "source_filename": source_filename or "",
        "generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds").replace("+00:00", "Z"),
        "total_records": total_records,
        "records_with_issues": records_with_issues,
        "records_without_issues": records_without_issues,
        "total_issues": total_issues,
        "issues_by_status": _json_counts(summary_issue_rows["status"]) if "status" in summary_issue_rows.columns else json.dumps({}),
        "issues_by_risk": _json_counts(summary_issue_rows["risk_level"]) if "risk_level" in summary_issue_rows.columns else json.dumps({}),
        "issues_by_review_state": _json_counts(review_state_series),
        "issues_by_category": _json_counts(summary_issue_rows["issue_category"]) if "issue_category" in summary_issue_rows.columns else json.dumps({}),
        "issues_by_rule": _json_counts(summary_issue_rows["rule_id"]) if "rule_id" in summary_issue_rows.columns else json.dumps({}),
        "decisions_by_type": _json_counts(decision_series),
        "corrected_issue_count": corrected_issue_count,
        "false_positive_count": false_positive_count,
        "accepted_with_note_count": accepted_with_note_count,
        "excluded_record_count": excluded_record_count,
        "unresolved_issue_count": unresolved_issue_count,
        "high_risk_open_count": high_risk_open_count,
        "escalated_issue_count": escalated_issue_count,
        "review_completion_rate": review_completion_rate,
        "is_review_complete": is_review_complete,
        "completion_criteria_note": completion_criteria_note,
        "summary_note": _build_summary_note(
            total_issues,
            records_with_issues,
            unresolved_issue_count,
            escalated_issue_count,
            high_risk_open_count,
        ),
        "generated_by": "system",
    }
    return pd.DataFrame([summary_record], columns=REVIEW_SUMMARY_COLUMNS)


def export_review_summary(
    issue_report_df: pd.DataFrame,
    prepared_dataframe: pd.DataFrame,
    review_log: pd.DataFrame,
    output_path: str | Path,
    *,
    dataset_id: str,
    source_filename: str | None = None,
) -> Path:
    """Write a review summary CSV derived from current issue and review data."""
    summary_df = _build_review_summary(
        issue_report_df,
        prepared_dataframe,
        review_log,
        dataset_id=dataset_id,
        source_filename=source_filename,
    )
    summary_path = Path(output_path)
    summary_df.to_csv(summary_path, index=False)
    return summary_path


def export_input_diagnostics(
    raw_dataframe: pd.DataFrame,
    preparation_result: PreparationResult,
    output_dir: str | Path,
) -> dict[str, Path]:
    """Export the raw snapshot plus a compact unsupported-input diagnostic report."""
    LOGGER.info("Exporting unsupported-input diagnostics to %s", output_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    dataset_snapshot_path = output_path / "dataset_snapshot.csv"
    diagnostics_path = output_path / INPUT_DIAGNOSTIC_FILE_NAME

    raw_dataframe.to_csv(dataset_snapshot_path, index=False)
    diagnostics_df = build_input_diagnostics(raw_dataframe, preparation_result)
    diagnostics_df = diagnostics_df.reindex(columns=[*INPUT_DIAGNOSTIC_COLUMNS])
    diagnostics_df.to_csv(diagnostics_path, index=False)

    LOGGER.info("Unsupported-input diagnostics written to %s", diagnostics_path)
    return {
        "dataset_snapshot": dataset_snapshot_path,
        "input_diagnostics": diagnostics_path,
    }


def export_outputs(
    raw_dataframe: pd.DataFrame,
    prepared_dataframe: pd.DataFrame,
    validation_results: dict,
    anomaly_results: list[Issue],
    review_log: pd.DataFrame | None,
    review_history: pd.DataFrame | None,
    output_dir: str | Path,
    source_filename: str | None = None,
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
    review_summary_path = output_path / "review_summary.csv"

    raw_dataframe.to_csv(dataset_snapshot_path, index=False)
    prepared_dataframe.to_csv(prepared_canonical_records_path, index=False)

    issue_rows = _build_issue_rows(prepared_dataframe, validation_results, anomaly_results)
    issue_rows.to_csv(issue_report_path, index=False)

    resolved_review_log = review_log if review_log is not None else EMPTY_REVIEW_LOG.copy()
    resolved_review_history = review_history if review_history is not None else EMPTY_REVIEW_HISTORY.copy()
    resolved_review_log.to_csv(review_log_path, index=False)
    resolved_review_history.to_csv(review_history_path, index=False)
    export_review_summary(
        issue_rows,
        prepared_dataframe,
        resolved_review_log,
        review_summary_path,
        dataset_id=f"DATASET-{output_path.name}",
        source_filename=source_filename,
    )

    LOGGER.debug(
        "Exported files created: %s, %s, %s, %s, %s",
        dataset_snapshot_path,
        prepared_canonical_records_path,
        issue_report_path,
        review_log_path,
        review_history_path,
        review_summary_path,
    )

    return {
        "dataset_snapshot": dataset_snapshot_path,
        "prepared_canonical_records": prepared_canonical_records_path,
        "issue_report": issue_report_path,
        "review_log": review_log_path,
        "review_history": review_history_path,
        "review_summary": review_summary_path,
    }
