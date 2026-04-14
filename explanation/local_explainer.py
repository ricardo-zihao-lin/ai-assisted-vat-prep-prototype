"""Local rule-based explanation generation for prototype pipeline runs."""

from __future__ import annotations

from collections import Counter

import pandas as pd

from pipeline import RunResult, STATUS_COMPLETED, STATUS_STOPPED_AFTER_REPORTING

ISSUE_TYPE_LABELS = {
    "missing_value": "missing values",
    "duplicate_row": "duplicate rows",
    "invalid_date_format": "dates that could not be read",
    "invalid_numeric_format": "amounts that could not be read as numbers",
    "anomaly": "unusual net amount values",
}


def _normalise_issue_type(issue_type: str) -> str:
    """Convert an internal issue type into restrained plain language."""
    return ISSUE_TYPE_LABELS.get(issue_type, issue_type.replace("_", " "))


def _normalise_decision(decision: str) -> str:
    """Convert an internal review decision into user-facing wording."""
    decision_labels = {
        "reject": "marked for follow-up",
        "confirm": "retained for review",
        "ignore": "not escalated",
    }
    return decision_labels.get(decision, decision.replace("_", " "))


def _format_issue_list(counts: Counter) -> str:
    """Format the main finding types as a short readable phrase."""
    if not counts:
        return "no recurring finding types"

    ordered_items = counts.most_common(3)
    parts = [_normalise_issue_type(issue_type) for issue_type, _ in ordered_items]

    if len(parts) == 1:
        return parts[0]
    if len(parts) == 2:
        return f"{parts[0]} and {parts[1]}"
    return f"{parts[0]}, {parts[1]}, and {parts[2]}"


def _build_review_note(review_log_df: pd.DataFrame, has_findings: bool) -> str:
    """Summarise review outcomes without exposing internal decision labels."""
    if review_log_df.empty or "decision" not in review_log_df.columns:
        if has_findings:
            return "Review decisions have not been recorded yet."
        return "No review follow-up was needed."

    decision_counts = Counter(review_log_df["decision"].dropna().astype(str))
    if not decision_counts:
        return "No review follow-up was needed."

    if decision_counts.get("reject", 0) > 0:
        return "Some flagged records were marked for follow-up."
    if decision_counts.get("confirm", 0) > 0 and decision_counts.get("ignore", 0) > 0:
        return "Some flagged records were kept for review, while lower-priority items were simply noted."
    if decision_counts.get("confirm", 0) > 0:
        return "Some flagged records were kept for review."
    if decision_counts.get("ignore", 0) > 0:
        return "The flagged items were noted without further escalation."

    ordered_items = decision_counts.most_common()
    parts = [f"{_normalise_decision(decision)} ({count})" for decision, count in ordered_items]
    return "Review notes recorded: " + ", ".join(parts) + "."


def _build_main_findings(run_result: RunResult, issue_report_df: pd.DataFrame, review_log_df: pd.DataFrame) -> str:
    """Summarise the main pipeline findings."""
    total_findings = run_result.issues_found + run_result.anomalies_flagged
    if total_findings == 0:
        return "No validation problems or unusual amount flags were recorded."

    issue_counts = Counter(issue_report_df.get("issue_type", pd.Series(dtype="object")).dropna().astype(str))
    dominant_findings = _format_issue_list(issue_counts)
    review_note = _build_review_note(review_log_df, has_findings=True)

    if len(issue_counts) == 1:
        return f"The main finding was {dominant_findings}. {review_note}"

    return f"The main findings were {dominant_findings}. {review_note}"


def _build_next_steps(issue_report_df: pd.DataFrame, run_result: RunResult) -> str:
    """Suggest restrained follow-up checks based on the recorded findings."""
    if run_result.issues_found == 0 and run_result.anomalies_flagged == 0:
        return "- No immediate follow-up checks were created by this run.\n- Keep the exported files if you want a traceable record."

    issue_types = set(issue_report_df.get("issue_type", pd.Series(dtype="object")).dropna().astype(str))
    next_steps: list[str] = []

    if "missing_value" in issue_types:
        next_steps.append("- Check whether blank cells in the source spreadsheet should be completed.")
    if "invalid_date_format" in issue_types:
        next_steps.append("- Check dates that were not in a readable format.")
    if "invalid_numeric_format" in issue_types:
        next_steps.append("- Check amount fields that could not be read as numbers.")
    if "duplicate_row" in issue_types:
        next_steps.append("- Review repeated rows to confirm whether they are genuine repeats or accidental duplicates.")
    if "anomaly" in issue_types:
        next_steps.append(
            "- Review unusual net amount values against the underlying records. These flags are prompts for review rather than proof of error."
        )

    if not next_steps:
        next_steps.append("- Use the issue report and review log to inspect the flagged items in more detail.")

    return "\n".join(next_steps[:3])


def generate_automatic_explanation(
    run_result: RunResult,
    issue_report_df: pd.DataFrame,
    review_log_df: pd.DataFrame,
) -> str:
    """Generate a fully local plain-language explanation for a pipeline run."""
    if run_result.status == STATUS_STOPPED_AFTER_REPORTING:
        overall_result = (
            "Reports were created, and the flagged records are ready for user review."
        )
    elif run_result.status == STATUS_COMPLETED and run_result.issues_found == 0 and run_result.anomalies_flagged == 0:
        overall_result = (
            "No issues or unusual amount flags were recorded in this run."
        )
    else:
        overall_result = (
            "Analysis completed and the prototype recorded some items for review."
        )

    if run_result.status == STATUS_STOPPED_AFTER_REPORTING:
        what_this_means = (
            "The source spreadsheet has findings that should now be reviewed by a user. "
            "The exported files show what was found, why it was flagged, and where review decisions should be recorded."
        )
    elif run_result.issues_found == 0 and run_result.anomalies_flagged == 0:
        what_this_means = (
            "Nothing in the file stood out under the current prototype checks. "
            "This is still a local research result, not a formal compliance judgement."
        )
    elif run_result.anomalies_flagged > 0:
        what_this_means = (
            "Some values sit outside the usual amount range for this file. "
            "These flags are advisory and should not be treated as confirmed errors."
        )
    else:
        what_this_means = (
            "The prototype found items worth checking, but the findings are advisory and intended to support local review of the spreadsheet."
        )

    sections = [
        "#### Overall Result",
        overall_result,
        "",
        "#### Main Findings",
        _build_main_findings(run_result, issue_report_df, review_log_df),
        "",
        "#### What This Means",
        what_this_means,
        "",
        "#### What To Check Next",
        _build_next_steps(issue_report_df, run_result),
    ]
    return "\n".join(sections)
