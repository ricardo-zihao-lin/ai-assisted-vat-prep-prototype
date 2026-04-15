"""Helpers for review-oriented user decisions and review history."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pandas as pd

REVIEW_DECISION_OPTIONS = [
    "pending",
    "confirmed_issue",
    "corrected",
    "accepted_with_note",
    "false_positive",
    "excluded_from_review_set",
    "escalated",
]
REVIEW_LOG_COLUMNS = [
    "decision_id",
    "issue_id",
    "finding_id",
    "record_id",
    "row_index",
    "issue_type",
    "decision",
    "decision_reason",
    "note",
    "evidence_checked",
    "correction_made",
    "final_record_status",
    "needs_escalation",
    "timestamp",
    "saved_at",
]
REVIEW_HISTORY_COLUMNS = [
    "decision_id",
    "issue_id",
    "finding_id",
    "record_id",
    "row_index",
    "issue_type",
    "decision",
    "decision_reason",
    "note",
    "evidence_checked",
    "correction_made",
    "final_record_status",
    "needs_escalation",
    "timestamp",
    "saved_at",
]
REVIEW_QUEUE_COLUMNS = [
    "issue_id",
    "record_id",
    "finding_summary",
    "row_index",
    "issue_type",
    "issue_category",
    "status",
    "risk_level",
    "review_state",
    "column",
    "value",
    "decision",
    "notes",
    "evidence_checked",
    "why_it_matters",
    "possible_vat_review_impact",
    "recommended_manual_check",
    "evidence_expected",
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

EMPTY_REVIEW_LOG = pd.DataFrame(columns=REVIEW_LOG_COLUMNS)
EMPTY_REVIEW_HISTORY = pd.DataFrame(columns=REVIEW_HISTORY_COLUMNS)


def _normalise_decision(value: object) -> str:
    decision = str(value or "").strip().lower()
    if decision not in REVIEW_DECISION_OPTIONS:
        return "pending"
    return decision


def _normalise_notes(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def _normalise_evidence(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def _derive_final_record_status(decision: str) -> str:
    mapping = {
        "pending": "open",
        "confirmed_issue": "reviewed",
        "corrected": "corrected",
        "accepted_with_note": "accepted",
        "false_positive": "accepted",
        "excluded_from_review_set": "excluded",
        "escalated": "escalated",
    }
    return mapping.get(decision, "open")


def _derive_review_state(decision: str) -> str:
    mapping = {
        "pending": "open",
        "confirmed_issue": "in_review",
        "corrected": "corrected",
        "accepted_with_note": "accepted_with_note",
        "false_positive": "false_positive",
        "excluded_from_review_set": "excluded",
        "escalated": "escalated",
    }
    return mapping.get(decision, "open")


def _derive_needs_escalation(decision: str) -> bool:
    return decision == "escalated"


def _derive_correction_made(decision: str) -> bool:
    return decision == "corrected"


def _build_decision_id() -> str:
    return f"DEC-{uuid4().hex[:12].upper()}"


def build_review_queue(issue_report_df: pd.DataFrame, review_log_df: pd.DataFrame | None = None) -> pd.DataFrame:
    """Return a review queue joined with the latest saved decisions."""
    if issue_report_df.empty:
        return pd.DataFrame(columns=REVIEW_QUEUE_COLUMNS)

    queue_df = issue_report_df.copy()
    if "issue_id" not in queue_df.columns and "finding_id" in queue_df.columns:
        queue_df["issue_id"] = queue_df["finding_id"]
    queue_df["value"] = queue_df.get("value")
    if "observed_value" in queue_df.columns:
        queue_df["value"] = queue_df["value"].where(queue_df["value"].notna(), queue_df["observed_value"])

    queue_df["decision"] = "pending"
    queue_df["notes"] = ""
    queue_df["evidence_checked"] = ""
    if "review_state" not in queue_df.columns:
        queue_df["review_state"] = "open"

    if review_log_df is not None and not review_log_df.empty:
        latest_review = review_log_df.copy()
        if "issue_id" not in latest_review.columns and "finding_id" in latest_review.columns:
            latest_review["issue_id"] = latest_review["finding_id"]
        if "finding_id" not in latest_review.columns and "issue_id" in latest_review.columns:
            latest_review["finding_id"] = latest_review["issue_id"]
        if "evidence_checked" not in latest_review.columns:
            latest_review["evidence_checked"] = ""
        if "note" not in latest_review.columns:
            latest_review["note"] = latest_review.get("notes", "")
        latest_review["decision"] = latest_review["decision"].map(_normalise_decision)
        latest_review["note"] = latest_review["note"].map(_normalise_notes)
        latest_review["evidence_checked"] = latest_review["evidence_checked"].map(_normalise_evidence)
        latest_review = latest_review.drop_duplicates(subset=["issue_id"], keep="last")
        queue_df = queue_df.merge(
            latest_review[["issue_id", "decision", "note", "evidence_checked"]],
            on="issue_id",
            how="left",
            suffixes=("", "_saved"),
        )
        queue_df["decision"] = queue_df["decision_saved"].where(queue_df["decision_saved"].notna(), queue_df["decision"])
        note_column = "note_saved" if "note_saved" in queue_df.columns else "note"
        evidence_column = (
            "evidence_checked_saved" if "evidence_checked_saved" in queue_df.columns else "evidence_checked"
        )
        queue_df["notes"] = queue_df[note_column].where(queue_df[note_column].notna(), queue_df["notes"])
        queue_df["evidence_checked"] = queue_df[evidence_column].where(queue_df[evidence_column].notna(), queue_df["evidence_checked"])
        drop_columns = [column for column in ["decision_saved", "note_saved", "note", "evidence_checked_saved"] if column in queue_df.columns]
        queue_df = queue_df.drop(columns=drop_columns)

    queue_df["decision"] = queue_df["decision"].map(_normalise_decision)
    queue_df["notes"] = queue_df["notes"].map(_normalise_notes)
    queue_df["evidence_checked"] = queue_df["evidence_checked"].map(_normalise_evidence)
    queue_df["review_state"] = queue_df["decision"].map(_derive_review_state)
    return queue_df.reindex(columns=REVIEW_QUEUE_COLUMNS)


def persist_review_outputs(
    review_queue_df: pd.DataFrame,
    review_log_path: str | Path,
    review_history_path: str | Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Persist the latest review log and append changed entries to history."""
    current_log_df = review_queue_df.copy()
    if "issue_id" not in current_log_df.columns and "finding_id" in current_log_df.columns:
        current_log_df["issue_id"] = current_log_df["finding_id"]
    if "finding_id" not in current_log_df.columns and "issue_id" in current_log_df.columns:
        current_log_df["finding_id"] = current_log_df["issue_id"]
    if "record_id" not in current_log_df.columns:
        current_log_df["record_id"] = ""
    current_log_df = current_log_df.reindex(
        columns=["issue_id", "finding_id", "record_id", "row_index", "issue_type", "decision", "notes", "evidence_checked"]
    ).copy()
    current_log_df["decision"] = current_log_df["decision"].map(_normalise_decision)
    current_log_df["notes"] = current_log_df["notes"].map(_normalise_notes)
    current_log_df["evidence_checked"] = current_log_df["evidence_checked"].map(_normalise_evidence)
    timestamp = datetime.now().isoformat(timespec="seconds")
    current_log_df["decision_reason"] = current_log_df["notes"]
    current_log_df["note"] = current_log_df["notes"]
    current_log_df["correction_made"] = current_log_df["decision"].map(_derive_correction_made)
    current_log_df["final_record_status"] = current_log_df["decision"].map(_derive_final_record_status)
    current_log_df["needs_escalation"] = current_log_df["decision"].map(_derive_needs_escalation)
    current_log_df["timestamp"] = timestamp
    current_log_df["saved_at"] = timestamp
    current_log_df["decision_id"] = [_build_decision_id() for _ in range(len(current_log_df))]
    current_log_df = current_log_df.reindex(columns=REVIEW_LOG_COLUMNS)

    review_log_file = Path(review_log_path)
    review_history_file = Path(review_history_path)

    if review_log_file.exists():
        try:
            previous_log_df = pd.read_csv(review_log_file)
        except pd.errors.EmptyDataError:
            previous_log_df = EMPTY_REVIEW_LOG.copy()
    else:
        previous_log_df = EMPTY_REVIEW_LOG.copy()

    previous_log_df = previous_log_df.reindex(columns=REVIEW_LOG_COLUMNS)

    if review_history_file.exists():
        try:
            review_history_df = pd.read_csv(review_history_file)
        except pd.errors.EmptyDataError:
            review_history_df = EMPTY_REVIEW_HISTORY.copy()
    else:
        review_history_df = EMPTY_REVIEW_HISTORY.copy()

    review_history_df = review_history_df.reindex(columns=REVIEW_HISTORY_COLUMNS)

    changed_entries: list[dict] = []
    if "issue_id" not in previous_log_df.columns and "finding_id" in previous_log_df.columns:
        previous_log_df["issue_id"] = previous_log_df["finding_id"]

    previous_lookup = previous_log_df.set_index("issue_id").to_dict(orient="index") if not previous_log_df.empty else {}

    for row in current_log_df.to_dict(orient="records"):
        previous_row = previous_lookup.get(row["issue_id"])
        if previous_row is None:
            if row["decision"] != "pending" or row["note"] or row["evidence_checked"]:
                changed_entries.append(row)
            continue

        previous_decision = _normalise_decision(previous_row.get("decision"))
        previous_notes = _normalise_notes(previous_row.get("note", previous_row.get("notes")))
        previous_evidence = _normalise_evidence(previous_row.get("evidence_checked"))
        if (
            row["decision"] != previous_decision
            or row["note"] != previous_notes
            or row["evidence_checked"] != previous_evidence
        ):
            changed_entries.append(row)

    if changed_entries:
        review_history_df = pd.concat(
            [review_history_df, pd.DataFrame(changed_entries, columns=REVIEW_HISTORY_COLUMNS)],
            ignore_index=True,
        )

    current_log_df.to_csv(review_log_file, index=False)
    review_history_df.to_csv(review_history_file, index=False)
    return current_log_df, review_history_df
