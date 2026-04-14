"""Helpers for user-driven review decisions and review history."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

REVIEW_DECISION_OPTIONS = ["pending", "confirm", "reject", "ignore"]
REVIEW_LOG_COLUMNS = ["finding_id", "row_index", "issue_type", "decision", "notes", "saved_at"]
REVIEW_HISTORY_COLUMNS = ["finding_id", "row_index", "issue_type", "decision", "notes", "saved_at"]
REVIEW_QUEUE_COLUMNS = [
    "finding_id",
    "finding_summary",
    "row_index",
    "issue_type",
    "column",
    "value",
    "decision",
    "notes",
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


def build_review_queue(issue_report_df: pd.DataFrame, review_log_df: pd.DataFrame | None = None) -> pd.DataFrame:
    """Return a review queue joined with the latest saved decisions."""
    if issue_report_df.empty:
        return pd.DataFrame(columns=REVIEW_QUEUE_COLUMNS)

    queue_df = issue_report_df.copy()
    queue_df["value"] = queue_df.get("value")
    if "observed_value" in queue_df.columns:
        queue_df["value"] = queue_df["value"].where(queue_df["value"].notna(), queue_df["observed_value"])

    queue_df["decision"] = "pending"
    queue_df["notes"] = ""

    if review_log_df is not None and not review_log_df.empty and "finding_id" in review_log_df.columns:
        latest_review = review_log_df.copy()
        latest_review["decision"] = latest_review["decision"].map(_normalise_decision)
        latest_review["notes"] = latest_review["notes"].map(_normalise_notes)
        latest_review = latest_review.drop_duplicates(subset=["finding_id"], keep="last")
        queue_df = queue_df.merge(
            latest_review[["finding_id", "decision", "notes"]],
            on="finding_id",
            how="left",
            suffixes=("", "_saved"),
        )
        queue_df["decision"] = queue_df["decision_saved"].where(queue_df["decision_saved"].notna(), queue_df["decision"])
        queue_df["notes"] = queue_df["notes_saved"].where(queue_df["notes_saved"].notna(), queue_df["notes"])
        queue_df = queue_df.drop(columns=["decision_saved", "notes_saved"])

    queue_df["decision"] = queue_df["decision"].map(_normalise_decision)
    queue_df["notes"] = queue_df["notes"].map(_normalise_notes)
    return queue_df.reindex(columns=REVIEW_QUEUE_COLUMNS)


def persist_review_outputs(
    review_queue_df: pd.DataFrame,
    review_log_path: str | Path,
    review_history_path: str | Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Persist the latest review log and append changed entries to history."""
    current_log_df = review_queue_df.reindex(columns=["finding_id", "row_index", "issue_type", "decision", "notes"]).copy()
    current_log_df["decision"] = current_log_df["decision"].map(_normalise_decision)
    current_log_df["notes"] = current_log_df["notes"].map(_normalise_notes)
    current_log_df["saved_at"] = datetime.now().isoformat(timespec="seconds")

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
    previous_lookup = previous_log_df.set_index("finding_id").to_dict(orient="index") if not previous_log_df.empty else {}

    for row in current_log_df.to_dict(orient="records"):
        previous_row = previous_lookup.get(row["finding_id"])
        if previous_row is None:
            if row["decision"] != "pending" or row["notes"]:
                changed_entries.append(row)
            continue

        previous_decision = _normalise_decision(previous_row.get("decision"))
        previous_notes = _normalise_notes(previous_row.get("notes"))
        if row["decision"] != previous_decision or row["notes"] != previous_notes:
            changed_entries.append(row)

    if changed_entries:
        review_history_df = pd.concat(
            [review_history_df, pd.DataFrame(changed_entries, columns=REVIEW_HISTORY_COLUMNS)],
            ignore_index=True,
        )

    current_log_df.to_csv(review_log_file, index=False)
    review_history_df.to_csv(review_history_file, index=False)
    return current_log_df, review_history_df
