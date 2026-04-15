from __future__ import annotations

import html

import gradio as gr
import pandas as pd
from matplotlib.figure import Figure

from explanation.local_explainer import ISSUE_TYPE_LABELS

from .constants import (
    DASHBOARD_PRIORITY_COLUMNS,
    DECISION_SORT_RANK,
    DOWNLOAD_PREVIEW_COLUMNS,
    ISSUE_TYPE_SORT_RANK,
    QUEUE_PREVIEW_COLUMNS,
    REVIEW_CONTEXT_COLUMNS,
    REVIEW_SIGNAL_TYPES,
    STATUS_SORT_RANK,
    TYPE_FILTER_MAP,
)
from .io import read_output_csv


def _normalise_issue_label(issue_type: str) -> str:
    return ISSUE_TYPE_LABELS.get(issue_type, issue_type.replace("_", " ").title())


def _format_user_status(status: str) -> str:
    return {
        "stopped_after_reporting": "Stopped after reporting",
        "unsupported_input": "Unsupported input",
        "completed": "Completed",
    }.get(status, status.replace("_", " ").title())


def _format_user_stop_reason(status: str, stop_reason: str | None) -> str | None:
    if status == "stopped_after_reporting" and stop_reason:
        return f"Stopped early: {stop_reason}"
    if status == "unsupported_input" and stop_reason:
        return f"Not fully processed: {stop_reason}"
    return stop_reason


def _format_preparation_status(preparation_status: str) -> str:
    return {
        "canonical": "Canonical input",
        "normalised": "Normalised input",
        "unsupported": "Unsupported input",
    }.get(preparation_status, preparation_status.replace("_", " ").title())


def _format_results_overview(
    input_name: str,
    rows_loaded: int,
    issues_found: int,
    anomalies_flagged: int,
    status: str,
    stop_reason: str | None,
    preparation_status: str,
    preparation_message: str | None,
    missing_required_fields: list[str] | None = None,
) -> str:
    status_label = _format_user_status(status)
    prep_label = _format_preparation_status(preparation_status)
    reason_label = _format_user_stop_reason(status, stop_reason)
    missing_fields_text = ", ".join(missing_required_fields or []) if missing_required_fields else "None"
    details = [
        f"Input file: {html.escape(input_name)}",
        f"Rows loaded: {rows_loaded}",
        f"Issues found: {issues_found}",
        f"Anomalies flagged: {anomalies_flagged}",
        f"Status: {html.escape(status_label)}",
        f"Preparation: {html.escape(prep_label)}",
        f"Missing required fields: {html.escape(missing_fields_text)}",
    ]
    if reason_label:
        details.append(f"Stop reason: {html.escape(reason_label)}")
    if preparation_message:
        details.append(f"Preparation note: {html.escape(preparation_message)}")
    return " | ".join(details)


def _build_message_figure(title: str, message: str) -> Figure:
    fig = Figure(figsize=(6.2, 2.0))
    ax = fig.add_subplot(111)
    ax.axis("off")
    ax.text(0.5, 0.62, title, ha="center", va="center", fontsize=14, fontweight="bold")
    ax.text(0.5, 0.32, message, ha="center", va="center", fontsize=11, wrap=True)
    fig.tight_layout()
    return fig


def _icon_svg(name: str) -> str:
    icons = {
        "insight": '<span class="inline-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 2v4"></path><path d="M12 18v4"></path><path d="M4.93 4.93l2.83 2.83"></path><path d="M16.24 16.24l2.83 2.83"></path><path d="M2 12h4"></path><path d="M18 12h4"></path><path d="M4.93 19.07l2.83-2.83"></path><path d="M16.24 7.76l2.83-2.83"></path><circle cx="12" cy="12" r="4"></circle></svg></span>',
        "review": '<span class="inline-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 6h16"></path><path d="M4 12h16"></path><path d="M4 18h10"></path><path d="M17 15l3 3 4-4"></path></svg></span>',
        "reason": '<span class="inline-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 3a7 7 0 0 0-7 7c0 2.4 1.2 4.1 2.8 5.3.6.5 1 1.1 1 1.8V19h6v-1.9c0-.7.4-1.3 1-1.8 1.6-1.2 2.8-2.9 2.8-5.3a7 7 0 0 0-7-7Z"></path><path d="M10 21h4"></path></svg></span>',
        "rows": '<span class="inline-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="4" width="18" height="16" rx="2"></rect><path d="M3 9h18"></path><path d="M8 4v16"></path></svg></span>',
        "action": '<span class="inline-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 12h16"></path><path d="M13 5l7 7-7 7"></path></svg></span>',
        "queue": '<span class="inline-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="4" width="18" height="16" rx="2"></rect><path d="M7 8h10"></path><path d="M7 12h10"></path><path d="M7 16h6"></path></svg></span>',
        "findings": '<span class="inline-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 20V10"></path><path d="M10 20V4"></path><path d="M16 20v-8"></path><path d="M22 20H2"></path></svg></span>',
        "pending": '<span class="inline-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="9"></circle><path d="M12 7v5l3 2"></path></svg></span>',
        "reviewed": '<span class="inline-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 12l5 5L20 6"></path></svg></span>',
        "duplicate": '<span class="inline-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="8" y="8" width="11" height="11" rx="2"></rect><rect x="5" y="5" width="11" height="11" rx="2"></rect></svg></span>',
        "anomaly": '<span class="inline-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 3l9 16H3L12 3Z"></path><path d="M12 9v4"></path><circle cx="12" cy="17" r="1"></circle></svg></span>',
        "field": '<span class="inline-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 7h16"></path><path d="M4 12h16"></path><path d="M4 17h10"></path></svg></span>',
        "interpret": '<span class="inline-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="9"></circle><path d="M12 8v1"></path><path d="M12 11v5"></path></svg></span>',
        "check": '<span class="inline-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M7 12l3 3 7-7"></path><rect x="3" y="3" width="18" height="18" rx="2"></rect></svg></span>',
    }
    return icons.get(name, "")


def _issue_type_colour(issue_type: str) -> str:
    if issue_type in {
        "unusual_net_amount",
        "negative_or_unusually_low_net_amount",
        "suspicious_zero_value_amount_combination",
    }:
        return "#f97316"
    if issue_type in {"exact_duplicate_row", "duplicate_invoice_reference"}:
        return "#8b5cf6"
    if issue_type in {"inconsistent_totals", "conflicting_amount_sign_pattern"}:
        return "#ef4444"
    if issue_type in {"missing_column", "missing_transaction_date", "missing_net_amount", "missing_vat_amount"}:
        return "#0ea5e9"
    if issue_type in {"non_numeric_net_amount", "non_numeric_vat_amount", "invalid_date_format"}:
        return "#14b8a6"
    return "#64748b"


def _build_issue_type_counts_plot(issue_report_df: pd.DataFrame) -> Figure:
    if issue_report_df.empty or "issue_type" not in issue_report_df.columns:
        return _build_message_figure("Findings by type", "No findings available for the current run.")

    counts = issue_report_df["issue_type"].dropna().astype(str).value_counts().head(8)
    labels = [_normalise_issue_label(issue_type) for issue_type in counts.index]
    colours = [_issue_type_colour(issue_type) for issue_type in counts.index]

    fig = Figure(figsize=(7, 4.0))
    ax = fig.add_subplot(111)
    ax.barh(labels[::-1], counts.values[::-1], color=colours[::-1])
    ax.set_xlabel("Count")
    ax.set_title("Findings by type")
    ax.grid(axis="x", alpha=0.2)
    fig.tight_layout()
    return fig


def _build_review_status_plot(review_queue_df: pd.DataFrame) -> Figure:
    if review_queue_df.empty or "decision" not in review_queue_df.columns:
        return _build_message_figure("Review status", "No queue records available yet.")

    counts = review_queue_df["decision"].fillna("pending").astype(str).value_counts()
    labels = [
        "Pending",
        "Confirmed issue",
        "Corrected",
        "Accepted with note",
        "False positive",
        "Escalated",
    ]
    values = [
        int(counts.get("pending", 0)),
        int(counts.get("confirmed_issue", 0)),
        int(counts.get("corrected", 0)),
        int(counts.get("accepted_with_note", 0)),
        int(counts.get("false_positive", 0)),
        int(counts.get("escalated", 0)),
    ]
    fig = Figure(figsize=(7.2, 4.0))
    ax = fig.add_subplot(111)
    ax.bar(labels, values, color=["#64748b", "#22c55e", "#38bdf8", "#94a3b8", "#ef4444", "#f97316"])
    ax.set_title("Review status")
    ax.set_ylabel("Count")
    ax.tick_params(axis="x", rotation=18)
    ax.grid(axis="y", alpha=0.2)
    fig.tight_layout()
    return fig


def _derive_review_field_series(issue_report_df: pd.DataFrame) -> pd.Series:
    if issue_report_df.empty:
        return pd.Series(dtype=int)
    candidate_columns = [column for column in ["column", "checked_column", "field", "trigger_field"] if column in issue_report_df.columns]
    if not candidate_columns:
        return pd.Series(dtype=int)
    series = pd.Series(dtype=object)
    for column in candidate_columns:
        value_series = issue_report_df[column].dropna().astype(str)
        if value_series.empty:
            continue
        series = pd.concat([series, value_series])
    if series.empty:
        return pd.Series(dtype=int)
    return series.value_counts().head(8)


def _build_field_focus_plot(issue_report_df: pd.DataFrame) -> Figure:
    series = _derive_review_field_series(issue_report_df)
    if series.empty:
        return _build_message_figure("Fields attracting review", "No explicit review fields were captured in this run.")

    fig = Figure(figsize=(7.2, 4.0))
    ax = fig.add_subplot(111)
    ax.barh(series.index[::-1].astype(str), series.values[::-1], color="#0ea5e9")
    ax.set_title("Fields attracting review")
    ax.set_xlabel("Count")
    ax.grid(axis="x", alpha=0.2)
    fig.tight_layout()
    return fig


def _format_amount(value: object) -> str:
    try:
        return f"{float(value):,.2f}"
    except Exception:
        return str(value)


def _build_anomaly_amount_plot(issue_report_df: pd.DataFrame) -> Figure:
    if issue_report_df.empty or "issue_type" not in issue_report_df.columns:
        return _build_message_figure("Top unusual amounts", "No anomaly findings available yet.")

    anomaly_df = issue_report_df[issue_report_df["issue_type"].astype(str).isin(REVIEW_SIGNAL_TYPES)].copy()
    if anomaly_df.empty:
        return _build_message_figure("Top unusual amounts", "No anomaly findings available yet.")

    if "net_amount" in anomaly_df.columns:
        anomaly_df["_amount_numeric"] = pd.to_numeric(anomaly_df["net_amount"], errors="coerce")
        source_column = "net_amount"
    elif "gross_amount" in anomaly_df.columns:
        anomaly_df["_amount_numeric"] = pd.to_numeric(anomaly_df["gross_amount"], errors="coerce")
        source_column = "gross_amount"
    else:
        anomaly_df["_amount_numeric"] = pd.Series(dtype=float)
        source_column = None

    anomaly_df = anomaly_df.dropna(subset=["_amount_numeric"])
    if anomaly_df.empty:
        return _build_message_figure("Top unusual amounts", "No numeric anomaly amounts were available for plotting.")

    top_df = anomaly_df.sort_values("_amount_numeric", ascending=False).head(6).copy()
    labels = top_df["issue_id"].astype(str)
    values = top_df["_amount_numeric"].astype(float)
    fig = Figure(figsize=(7.2, 4.0))
    ax = fig.add_subplot(111)
    ax.bar(labels[::-1], values[::-1], color="#f97316")
    ax.set_title("Top unusual amounts")
    ax.set_ylabel(source_column or "amount")
    ax.tick_params(axis="x", rotation=18)
    ax.grid(axis="y", alpha=0.2)
    fig.tight_layout()
    return fig


def _build_anomaly_note(issue_report_df: pd.DataFrame) -> str:
    if issue_report_df.empty or "issue_type" not in issue_report_df.columns:
        return "No anomalies were detected in this run."
    issue_counts = issue_report_df["issue_type"].dropna().astype(str).value_counts()
    anomaly_count = int(sum(issue_counts.get(issue_type, 0) for issue_type in REVIEW_SIGNAL_TYPES))
    if anomaly_count == 0:
        return "No review signals were detected in this run."
    return f"{anomaly_count} review signal(s) were flagged for manual checking because they may indicate unusual values or context-sensitive VAT review cases."


def _build_visual_summary_html(
    issue_report_df: pd.DataFrame,
    review_queue_df: pd.DataFrame,
    review_history_df: pd.DataFrame,
    prepared_records_path: str | None,
    review_summary_path: str | None = None,
) -> str:
    review_summary_df = read_output_csv(review_summary_path) if review_summary_path else pd.DataFrame()
    if issue_report_df.empty and review_queue_df.empty:
        return f"""
        <div class="dashboard-shell">
          <div class="dashboard-title-row">
            <div class="dashboard-title-group">
              <div class="eyebrow">{_icon_svg("insight")}Visual Insights</div>
              <div class="dashboard-title">Run-level dashboard</div>
              <div class="dashboard-subtitle">Run an analysis to populate KPI cards, management views, and priority findings.</div>
            </div>
          </div>
        </div>
        """

    prepared_rows = len(read_output_csv(prepared_records_path, default_columns=REVIEW_CONTEXT_COLUMNS))
    counts = review_queue_df["decision"].fillna("pending").astype(str).value_counts() if not review_queue_df.empty else pd.Series(dtype=int)
    reviewed_count = int(
        counts.get("confirmed_issue", 0)
        + counts.get("corrected", 0)
        + counts.get("accepted_with_note", 0)
        + counts.get("false_positive", 0)
        + counts.get("excluded_from_review_set", 0)
        + counts.get("escalated", 0)
    )
    issue_counts = issue_report_df["issue_type"].dropna().astype(str).value_counts() if "issue_type" in issue_report_df.columns else pd.Series(dtype=int)
    duplicate_count = int(issue_counts.get("exact_duplicate_row", 0))
    anomaly_count = int(sum(issue_counts.get(issue_type, 0) for issue_type in REVIEW_SIGNAL_TYPES))

    cards = [
        ("rows", "Rows loaded", prepared_rows, "Prepared records ready for inspection"),
        ("findings", "Findings", len(issue_report_df), "Combined validation and anomaly items"),
        ("pending", "Pending review", int(counts.get("pending", len(review_queue_df))), "Still waiting for a user decision"),
        ("reviewed", "Reviewed", reviewed_count, "Already captured in the decision log"),
        ("duplicate", "Duplicate rows", duplicate_count, "Potential repeated records"),
        ("anomaly", "Review signals", anomaly_count, "Unusual or context-sensitive amount prompts"),
    ]
    cards_html = "".join(
        f"""
        <div class="dashboard-kpi-card">
          <div class="dashboard-kpi-top">{_icon_svg(icon)}<span>{label}</span></div>
          <div class="dashboard-kpi-value">{value}</div>
          <div class="dashboard-kpi-note">{note}</div>
        </div>
        """
        for icon, label, value, note in cards
    )

    summary_note_html = ""
    if not review_summary_df.empty:
        summary_row = review_summary_df.iloc[0]
        summary_note = html.escape(str(summary_row.get("summary_note") or ""))
        unresolved = html.escape(str(summary_row.get("unresolved_issue_count") or "0"))
        high_risk_open = html.escape(str(summary_row.get("high_risk_open_count") or "0"))
        completion_note = html.escape(str(summary_row.get("completion_criteria_note") or ""))
        summary_note_html = f"""
        <div class="insight-card insight-card-status" style="margin-top: 14px;">
          <div class="insight-title">{_icon_svg("review")}<span>Review summary</span></div>
          <div class="insight-body">{summary_note}</div>
          <div class="summary-footnote">Unresolved issues: {unresolved} | Open high risk: {high_risk_open}</div>
          <div class="summary-footnote">{completion_note}</div>
        </div>
        """

    return f"""
    <div class="dashboard-shell">
      <div class="dashboard-title-row">
        <div class="dashboard-title-group">
          <div class="dashboard-section-kicker">Overview</div>
          <div class="dashboard-title">Review workload snapshot</div>
          <div class="dashboard-subtitle">Use this section to understand run size, current backlog, and the main categories driving review effort.</div>
        </div>
      </div>
      <div class="dashboard-kpi-grid">{cards_html}</div>
      {summary_note_html}
    </div>
    """


def _build_visual_highlights_html(issue_report_df: pd.DataFrame, review_queue_df: pd.DataFrame, review_history_df: pd.DataFrame) -> str:
    if issue_report_df.empty and review_queue_df.empty:
        return '<div class="insight-shell"><div class="insight-shell-header"><div class="dashboard-section-kicker">Focus Areas</div><div class="insight-shell-title">What this run needs</div></div><div class="insight-grid"><div class="insight-card insight-card-focus"><div class="insight-title">No run loaded</div><div class="insight-body">Run an analysis to surface focused review guidance.</div></div></div></div>'

    pending_issue_df = issue_report_df.copy()
    if not review_queue_df.empty and {"issue_id", "decision"}.issubset(review_queue_df.columns):
        pending_issue_df = pending_issue_df.merge(
            review_queue_df[["issue_id", "decision"]],
            on="issue_id",
            how="left",
            suffixes=("", "_review"),
        )
        if "decision_review" in pending_issue_df.columns:
            pending_issue_df["decision"] = pending_issue_df["decision_review"]
            pending_issue_df = pending_issue_df.drop(columns=["decision_review"])
    if "decision" in pending_issue_df.columns:
        pending_issue_df["decision"] = pending_issue_df["decision"].fillna("pending").astype(str)
        unresolved_issue_df = pending_issue_df[pending_issue_df["decision"].eq("pending")]
        if not unresolved_issue_df.empty:
            pending_issue_df = unresolved_issue_df

    issue_counts = pending_issue_df["issue_type"].dropna().astype(str).value_counts() if "issue_type" in pending_issue_df.columns else pd.Series(dtype=int)
    top_issue = issue_counts.index[0] if not issue_counts.empty else "no finding types"
    top_issue_count = int(issue_counts.iloc[0]) if not issue_counts.empty else 0

    field_counts = _derive_review_field_series(pending_issue_df)
    top_field = field_counts.index[0].replace("_", " ") if not field_counts.empty else "review field not available"
    top_field_count = int(field_counts.iloc[0]) if not field_counts.empty else 0

    pending_count = 0
    if not review_queue_df.empty and "decision" in review_queue_df.columns:
        pending_count = int(review_queue_df["decision"].fillna("pending").astype(str).eq("pending").sum())

    last_saved = ""
    if not review_history_df.empty and "saved_at" in review_history_df.columns:
        saved_values = review_history_df["saved_at"].dropna().astype(str)
        if not saved_values.empty:
            last_saved = saved_values.iloc[-1]

    cards = [
        (
            "findings",
            "Largest review driver",
            f"{_normalise_issue_label(top_issue).title()} contributes {top_issue_count} finding(s) in this run.",
        ),
        (
            "field",
            "Most affected field",
            f"{top_field.title()} appears in {top_field_count} review prompt(s), so it is a strong candidate for focused checking.",
        ),
        (
            "reviewed",
            "Audit trail",
            "No decisions have been saved yet."
            if not last_saved
            else f"{len(review_history_df)} saved review action(s) have been recorded. Latest save: {last_saved}.",
        ),
        (
            "pending",
            "Current review pressure",
            f"{pending_count} finding(s) are still pending and need a user decision before the run is fully reviewed.",
        ),
    ]
    card_html = "".join(
        f"""
        <div class="insight-card {'insight-card-focus' if index < 2 else 'insight-card-status'}">
          <div class="insight-title">{_icon_svg(icon)}<span>{title}</span></div>
          <div class="insight-body">{html.escape(body)}</div>
        </div>
        """
        for index, (icon, title, body) in enumerate(cards)
    )
    return f"""
    <div class="insight-shell">
      <div class="insight-shell-header">
        <div>
          <div class="dashboard-section-kicker">Focus Areas</div>
          <div class="insight-shell-title">Where to focus next</div>
        </div>
        <div class="insight-shell-copy">These cues separate risk concentration from workflow status so the page reads less like one repeated block of cards.</div>
      </div>
      <div class="insight-grid">{card_html}</div>
    </div>
    """


def _build_priority_findings_preview(issue_report_df: pd.DataFrame, review_queue_df: pd.DataFrame) -> pd.DataFrame:
    if issue_report_df.empty:
        return pd.DataFrame(columns=DASHBOARD_PRIORITY_COLUMNS)

    preview_df = issue_report_df.copy()
    if not review_queue_df.empty and {"issue_id", "decision"}.issubset(review_queue_df.columns):
        preview_df = preview_df.merge(
            review_queue_df[["issue_id", "decision"]],
            on="issue_id",
            how="left",
            suffixes=("", "_review"),
        )
        if "decision_review" in preview_df.columns:
            preview_df["decision"] = preview_df["decision_review"]
            preview_df = preview_df.drop(columns=["decision_review"])
    if "decision" not in preview_df.columns:
        preview_df["decision"] = "pending"
    else:
        preview_df["decision"] = preview_df["decision"].fillna("pending").astype(str)
    preview_df["issue_rank"] = preview_df["issue_type"].map(ISSUE_TYPE_SORT_RANK).fillna(99)
    preview_df["decision_rank"] = preview_df["decision"].map(DECISION_SORT_RANK).fillna(99)
    preview_df["risk_rank"] = preview_df["risk_level"].astype(str).map({"High": 0, "Medium": 1, "Low": 2}).fillna(3)
    preview_df["anomaly_score_numeric"] = pd.to_numeric(preview_df.get("anomaly_score"), errors="coerce").fillna(0.0)
    preview_df = preview_df.sort_values(
        ["decision_rank", "risk_rank", "issue_rank", "anomaly_score_numeric", "row_index"],
        ascending=[True, True, True, False, True],
    )

    preview_df = preview_df.reindex(columns=DASHBOARD_PRIORITY_COLUMNS).head(12).copy()
    preview_df["issue_type"] = preview_df["issue_type"].map(_normalise_issue_label)
    preview_df["decision"] = preview_df["decision"].map(
        {
            "pending": "Pending",
            "confirmed_issue": "Confirmed issue",
            "corrected": "Corrected",
            "accepted_with_note": "Accepted with note",
            "false_positive": "False positive",
            "excluded_from_review_set": "Excluded",
            "escalated": "Escalated",
        }
    ).fillna("Pending")
    return preview_df


def _build_visual_insights_bundle(
    issue_report_df: pd.DataFrame,
    review_queue_df: pd.DataFrame,
    review_history_df: pd.DataFrame,
    prepared_records_path: str | None,
    review_summary_path: str | None = None,
) -> tuple:
    return (
        _build_visual_summary_html(
            issue_report_df,
            review_queue_df,
            review_history_df,
            prepared_records_path,
            review_summary_path,
        ),
        _build_visual_highlights_html(issue_report_df, review_queue_df, review_history_df),
        _build_issue_type_counts_plot(issue_report_df),
        _build_review_status_plot(review_queue_df),
        _build_field_focus_plot(issue_report_df),
        _build_anomaly_amount_plot(issue_report_df),
        _build_priority_findings_preview(issue_report_df, review_queue_df),
        _build_anomaly_note(issue_report_df),
    )


def _build_issue_report_preview(issue_report_df: pd.DataFrame) -> pd.DataFrame:
    return issue_report_df.reindex(columns=DOWNLOAD_PREVIEW_COLUMNS).head(50)


def _build_review_summary_preview(review_summary_df: pd.DataFrame) -> pd.DataFrame:
    if review_summary_df.empty:
        return pd.DataFrame(
            columns=[
                "total_records",
                "total_issues",
                "unresolved_issue_count",
                "high_risk_open_count",
                "escalated_issue_count",
                "review_completion_rate",
                "is_review_complete",
                "summary_note",
            ]
        )
    return review_summary_df.reindex(
        columns=[
            "total_records",
            "total_issues",
            "unresolved_issue_count",
            "high_risk_open_count",
            "escalated_issue_count",
            "review_completion_rate",
            "is_review_complete",
            "summary_note",
        ]
    ).head(1)


def _queue_to_records(review_queue_df: pd.DataFrame) -> list[dict]:
    return review_queue_df.to_dict(orient="records")


def _records_to_queue(review_queue_records: list[dict] | None) -> pd.DataFrame:
    if not review_queue_records:
        return pd.DataFrame()
    return pd.DataFrame(review_queue_records)


def _normalise_filter_status(filter_value: str) -> str | None:
    mapping = {
        "Pending": "pending",
        "Confirmed issue": "confirmed_issue",
        "Corrected": "corrected",
        "Accepted with note": "accepted_with_note",
        "False positive": "false_positive",
        "Excluded": "excluded_from_review_set",
        "Escalated": "escalated",
    }
    return mapping.get(filter_value)


def _ensure_issue_id_column(dataframe: pd.DataFrame) -> pd.DataFrame:
    if dataframe.empty:
        return dataframe
    normalised_df = dataframe.copy()
    if "issue_id" not in normalised_df.columns and "finding_id" in normalised_df.columns:
        normalised_df["issue_id"] = normalised_df["finding_id"]
    return normalised_df


def _apply_review_filters(
    review_queue_df: pd.DataFrame,
    status_filter: str,
    type_filter: str,
    search_text: str,
) -> pd.DataFrame:
    if review_queue_df.empty:
        return review_queue_df

    filtered_df = _ensure_issue_id_column(review_queue_df)
    status_value = _normalise_filter_status(status_filter)
    if status_value is not None:
        filtered_df = filtered_df[filtered_df["decision"].fillna("pending").astype(str) == status_value]

    issue_type_value = TYPE_FILTER_MAP.get(type_filter)
    if issue_type_value is not None:
        filtered_df = filtered_df[filtered_df["issue_type"].astype(str).isin(issue_type_value)]

    search_value = (search_text or "").strip().lower()
    if search_value:
        searchable = (
            filtered_df["issue_id"].astype(str).str.lower()
            + " "
            + filtered_df["finding_summary"].astype(str).str.lower()
            + " "
            + filtered_df["row_index"].astype(str).str.lower()
            + " "
            + filtered_df["issue_type"].astype(str).str.lower()
        )
        filtered_df = filtered_df[searchable.str.contains(search_value, na=False)]

    filtered_df = filtered_df.copy()
    filtered_df["decision_sort_rank"] = filtered_df["decision"].fillna("pending").astype(str).map(DECISION_SORT_RANK).fillna(99)
    filtered_df["risk_sort_rank"] = filtered_df["risk_level"].astype(str).map({"High": 0, "Medium": 1, "Low": 2}).fillna(3)
    filtered_df["status_sort_rank"] = filtered_df["status"].astype(str).map(STATUS_SORT_RANK).fillna(99)
    filtered_df["issue_sort_rank"] = filtered_df["issue_type"].astype(str).map(ISSUE_TYPE_SORT_RANK).fillna(99)
    filtered_df["row_index_numeric"] = pd.to_numeric(filtered_df["row_index"], errors="coerce").fillna(10**9)
    filtered_df = filtered_df.sort_values(
        ["decision_sort_rank", "risk_sort_rank", "status_sort_rank", "issue_sort_rank", "row_index_numeric", "issue_id"],
        ascending=[True, True, True, True, True, True],
    ).drop(columns=["decision_sort_rank", "risk_sort_rank", "status_sort_rank", "issue_sort_rank", "row_index_numeric"])

    return filtered_df.reset_index(drop=True)


def _build_issue_choices(filtered_df: pd.DataFrame) -> list[str]:
    if filtered_df.empty:
        return []
    return [f"{row['issue_id']} | row {row['row_index']} | {row['finding_summary']}" for _, row in filtered_df.iterrows()]


def _extract_issue_id(choice_value: str | None) -> str | None:
    if not choice_value:
        return None
    return choice_value.split("|", 1)[0].strip()


def _build_queue_preview(filtered_df: pd.DataFrame) -> pd.DataFrame:
    if filtered_df.empty:
        return pd.DataFrame(columns=QUEUE_PREVIEW_COLUMNS)
    preview_df = filtered_df.reindex(columns=QUEUE_PREVIEW_COLUMNS).copy()
    preview_df["issue_type"] = preview_df["issue_type"].map(_normalise_issue_label)
    return preview_df


def _build_review_history_preview(review_history_df: pd.DataFrame) -> pd.DataFrame:
    if review_history_df.empty:
        return pd.DataFrame(
            columns=["issue_id", "decision", "final_record_status", "needs_escalation", "evidence_checked", "note", "timestamp"]
        )
    preview_df = review_history_df.copy()
    preview_df = _ensure_issue_id_column(preview_df)
    if "note" not in preview_df.columns and "notes" in preview_df.columns:
        preview_df["note"] = preview_df["notes"]
    if "timestamp" not in preview_df.columns and "saved_at" in preview_df.columns:
        preview_df["timestamp"] = preview_df["saved_at"]
    return preview_df.reindex(
        columns=["issue_id", "decision", "final_record_status", "needs_escalation", "evidence_checked", "note", "timestamp"]
    )


def _resolve_selected_row(filtered_df: pd.DataFrame, selected_choice: str | None) -> pd.Series | None:
    if filtered_df.empty:
        return None
    issue_id = _extract_issue_id(selected_choice)
    if issue_id:
        match = filtered_df[filtered_df["issue_id"] == issue_id]
        if not match.empty:
            return match.iloc[0]
    return filtered_df.iloc[0]


def _html_escape(value: object) -> str:
    if value is None or pd.isna(value):
        return "blank"
    text = str(value)
    if not text:
        return "blank"
    return html.escape(text)


def _status_badge(decision: str) -> tuple[str, str]:
    mapping = {
        "pending": ("Pending", "badge-pending"),
        "confirmed_issue": ("Confirmed issue", "badge-confirm"),
        "corrected": ("Corrected", "badge-confirm"),
        "accepted_with_note": ("Accepted with note", "badge-ignore"),
        "false_positive": ("False positive", "badge-ignore"),
        "excluded_from_review_set": ("Excluded", "badge-reject"),
        "escalated": ("Escalated", "badge-reject"),
    }
    return mapping.get(decision, ("Pending", "badge-pending"))


def _issue_kind_badge(issue_type: str) -> tuple[str, str]:
    if issue_type in REVIEW_SIGNAL_TYPES:
        return "Review signal", "badge-anomaly"
    if issue_type in {
        "missing_transaction_date",
        "missing_net_amount",
        "missing_vat_amount",
        "missing_required_review_field",
        "invalid_date_format",
        "non_numeric_net_amount",
        "non_numeric_vat_amount",
        "inconsistent_totals",
        "missing_counterparty_reference",
        "missing_evidence_reference",
        "missing_transaction_category_support_field",
        "missing_column",
    }:
        return "Deterministic issue", "badge-data"
    return "Review issue", "badge-neutral"


def _build_header_html(selected_row: pd.Series | None, filtered_count: int, total_count: int) -> str:
    if selected_row is None:
        return """
        <div class="hero-card">
          <div class="hero-title">Review Centre</div>
          <div class="hero-subtitle">No issue matches the current filters.</div>
        </div>
        """

    decision_label, decision_class = _status_badge(str(selected_row.get("decision") or "pending"))
    kind_label, kind_class = _issue_kind_badge(str(selected_row.get("issue_type") or ""))
    issue_status = _html_escape(selected_row.get("status"))
    risk_level = _html_escape(selected_row.get("risk_level"))
    why_it_matters = _html_escape(selected_row.get("why_it_matters"))
    possible_impact = _html_escape(selected_row.get("possible_vat_review_impact"))
    return f"""
    <div class="hero-card">
      <div class="hero-row">
        <div>
          <div class="eyebrow">{_icon_svg("review")}Selected issue</div>
          <div class="hero-title">{_html_escape(selected_row.get('issue_id'))} - Row {_html_escape(selected_row.get('row_index'))}</div>
          <div class="hero-subtitle">{_html_escape(selected_row.get('finding_summary'))}</div>
          <div class="hero-meta">Issue status: {issue_status} | Risk level: {risk_level}</div>
        </div>
        <div class="hero-badges">
          <span class="badge {decision_class}">{decision_label}</span>
          <span class="badge {kind_class}">{kind_label}</span>
        </div>
      </div>
      <div class="hero-alert">
        <div class="hero-alert-title"><span class="title-with-icon">{_icon_svg("reason")}<span>Why This Is Risky</span></span></div>
        <div class="hero-alert-body">{why_it_matters}</div>
        <div class="hero-alert-impact"><strong>Possible impact:</strong> {possible_impact}</div>
      </div>
      <div class="hero-meta">Showing {filtered_count} issue(s) under the current filters out of {total_count} in this run.</div>
    </div>
    """


def _build_summary_html(review_queue_df: pd.DataFrame, review_history_df: pd.DataFrame) -> str:
    if review_queue_df.empty:
        return f"""
        <div class="summary-card">
          <div class="summary-title"><span class="title-with-icon">{_icon_svg("queue")}<span>Queue Summary</span></span></div>
          <div class="summary-empty">Run an analysis to load issues into the review workspace.</div>
        </div>
        """

    counts = review_queue_df["decision"].fillna("pending").astype(str).value_counts()
    last_saved = ""
    if not review_history_df.empty and "saved_at" in review_history_df.columns:
        saved_values = review_history_df["saved_at"].dropna().astype(str)
        if not saved_values.empty:
            last_saved = saved_values.iloc[-1]

    open_high_risk = 0
    if {"risk_level", "decision"}.issubset(review_queue_df.columns):
        open_high_risk = int(
            (
                review_queue_df["risk_level"].astype(str).eq("High")
                & review_queue_df["decision"].fillna("pending").astype(str).eq("pending")
            ).sum()
        )

    metrics = [
        ("Issues", len(review_queue_df), "metric-total"),
        ("Pending", int(counts.get("pending", 0)), "metric-pending"),
        ("Corrected", int(counts.get("corrected", 0)), "metric-confirm"),
        ("Accepted", int(counts.get("accepted_with_note", 0)), "metric-ignore"),
        ("Escalated", int(counts.get("escalated", 0)), "metric-reject"),
        ("Open High Risk", open_high_risk, "metric-reject"),
    ]
    metric_html = "".join(
        f'<div class="metric-chip {css_class}"><div class="metric-chip-value">{value}</div><div class="metric-chip-label">{label}</div></div>'
        for label, value, css_class in metrics
    )
    footer = f'<div class="summary-footnote">Last saved change: {html.escape(last_saved)}</div>' if last_saved else ""
    return f"""
    <div class="summary-card summary-inline-card">
      <div class="summary-title"><span class="title-with-icon">{_icon_svg("queue")}<span>Queue Summary</span></span></div>
      <div class="metric-strip">{metric_html}</div>
      {footer}
    </div>
    """


def _build_filter_hint_html(filtered_df: pd.DataFrame, total_df: pd.DataFrame, search_text: str) -> str:
    if total_df.empty:
        return '<div class="filter-hint">Filters will appear after you run an analysis.</div>'
    suffix = f' Search: "{html.escape(search_text.strip())}".' if (search_text or "").strip() else ""
    return f'<div class="filter-hint">Showing {len(filtered_df)} of {len(total_df)} issues.{suffix}</div>'


def _build_explanation_html(selected_row: pd.Series | None) -> str:
    if selected_row is None:
        return '<div class="context-empty">Select an issue to inspect the review guidance.</div>'

    cards = [
        ("reason", "Why It Matters", selected_row.get("why_it_matters")),
        ("interpret", "Possible VAT Review Impact", selected_row.get("possible_vat_review_impact")),
        ("action", "Recommended Manual Check", selected_row.get("recommended_manual_check")),
        ("check", "Evidence Expected", selected_row.get("evidence_expected")),
    ]
    card_html = "".join(
        f"""
        <div class="reference-detail-card">
          <div class="detail-title"><span class="title-with-icon">{_icon_svg(icon_name)}<span>{title}</span></span></div>
          <div class="detail-body">{_html_escape(value)}</div>
        </div>
        """
        for icon_name, title, value in cards
    )
    return f'<div class="detail-grid reference-grid">{card_html}</div>'


def _build_record_context_html(selected_row: pd.Series | None) -> str:
    if selected_row is None:
        return '<div class="context-empty">No source record is selected.</div>'

    rows = "".join(
        f"<tr><th>{column.replace('_', ' ').title()}</th><td>{_html_escape(selected_row.get(column))}</td></tr>"
        for column in REVIEW_CONTEXT_COLUMNS
    )
    return f'<table class="context-table">{rows}</table>'


def _build_row_preview_html(selected_row: pd.Series | None, prepared_records_path: str | None) -> str:
    if selected_row is None or not prepared_records_path:
        return f'<div class="row-preview-card"><div class="eyebrow">Evidence</div><div class="row-preview-title"><span class="title-with-icon">{_icon_svg("rows")}<span>Row Preview</span></span></div><div class="row-preview-empty">Run an analysis and select a finding to preview the relevant row.</div></div>'

    prepared_df = read_output_csv(prepared_records_path, default_columns=REVIEW_CONTEXT_COLUMNS)
    if prepared_df.empty:
        return f'<div class="row-preview-card"><div class="eyebrow">Evidence</div><div class="row-preview-title"><span class="title-with-icon">{_icon_svg("rows")}<span>Row Preview</span></span></div><div class="row-preview-empty">Prepared records are not available for preview.</div></div>'

    row_index = pd.to_numeric(pd.Series([selected_row.get("row_index")]), errors="coerce").iloc[0]
    if pd.isna(row_index):
        return f'<div class="row-preview-card"><div class="eyebrow">Evidence</div><div class="row-preview-title"><span class="title-with-icon">{_icon_svg("rows")}<span>Row Preview</span></span></div><div class="row-preview-empty">This finding is not tied to a single row.</div></div>'

    row_index = int(row_index)
    if row_index < 0 or row_index >= len(prepared_df):
        return f'<div class="row-preview-card"><div class="eyebrow">Evidence</div><div class="row-preview-title"><span class="title-with-icon">{_icon_svg("rows")}<span>Row Preview</span></span></div><div class="row-preview-empty">The selected row could not be located in the prepared records.</div></div>'

    issue_type = str(selected_row.get("issue_type") or "")
    if issue_type == "exact_duplicate_row":
        current_record = prepared_df.iloc[row_index]
        matching_mask = prepared_df.eq(current_record).all(axis=1)
        preview_df = prepared_df.loc[matching_mask].copy()
        helper = "The duplicate check is showing the matching repeated rows so you can compare them directly before recording a decision."
    else:
        start = max(0, row_index - 1)
        end = min(len(prepared_df), row_index + 2)
        preview_df = prepared_df.iloc[start:end].copy()
        helper = "The highlighted row is the selected issue. Use it with the explanation panel and supporting evidence before recording a review decision."

    preview_df = preview_df.reset_index(names="row_index")
    flagged_field = str(selected_row.get("column") or selected_row.get("checked_column") or "").strip()
    header_html = "".join(f"<th>{html.escape(column)}</th>" for column in preview_df.columns)
    body_rows: list[str] = []
    decision_label, decision_class = _status_badge(str(selected_row.get("decision") or "pending"))
    kind_label, kind_class = _issue_kind_badge(str(selected_row.get("issue_type") or ""))
    suggested_action = _html_escape(selected_row.get("suggested_action"))
    for _, row in preview_df.iterrows():
        row_class = "current-row" if int(row["row_index"]) == row_index else ""
        cells: list[str] = []
        for column in preview_df.columns:
            cell_class = ""
            if column == flagged_field and int(row["row_index"]) == row_index:
                cell_class = "flagged-cell"
            cells.append(f'<td class="{cell_class}">{_html_escape(row[column])}</td>')
        body_rows.append(f'<tr class="{row_class}">{"".join(cells)}</tr>')

    return f"""
    <div class="row-preview-card">
      <div class="eyebrow">Evidence</div>
      <div class="evidence-summary">
        <div class="evidence-summary-main">
          <div class="evidence-summary-title">{_html_escape(selected_row.get('issue_id'))} - Row {_html_escape(selected_row.get('row_index'))}</div>
          <div class="evidence-summary-subtitle">{_html_escape(selected_row.get('finding_summary'))}</div>
        </div>
        <div class="hero-badges">
          <span class="badge {decision_class}">{decision_label}</span>
          <span class="badge {kind_class}">{kind_label}</span>
        </div>
      </div>
      <div class="row-preview-title"><span class="title-with-icon">{_icon_svg("rows")}<span>Row Preview</span></span></div>
      <div class="row-preview-helper">{helper}</div>
      <div class="row-preview-table-wrap excel-sheet-wrap">
        <table class="row-preview-table">
          <thead><tr>{header_html}</tr></thead>
          <tbody>{''.join(body_rows)}</tbody>
        </table>
      </div>
      <div class="evidence-action">
        <div class="eyebrow">Next step</div>
        <div class="action-title"><span class="title-with-icon">{_icon_svg("action")}<span>Recommended Manual Check</span></span></div>
        <div class="action-body">{suggested_action}</div>
      </div>
    </div>
    """


def _build_review_workspace(
    review_queue_df: pd.DataFrame,
    review_history_df: pd.DataFrame,
    review_paths: dict,
    status_filter: str,
    type_filter: str,
    search_text: str,
    selected_issue: str | None,
) -> tuple:
    filtered_df = _apply_review_filters(review_queue_df, status_filter, type_filter, search_text)
    selected_row = _resolve_selected_row(filtered_df, selected_issue)
    selected_choice = None if selected_row is None else f"{selected_row['issue_id']} | row {selected_row['row_index']} | {selected_row['finding_summary']}"
    choices = _build_issue_choices(filtered_df)
    decision_value = "pending" if selected_row is None else str(selected_row.get("decision") or "pending")
    notes_value = "" if selected_row is None else str(selected_row.get("notes") or "")
    evidence_value = "" if selected_row is None else str(selected_row.get("evidence_checked") or "")

    return (
        gr.update(choices=choices, value=selected_choice),
        _build_filter_hint_html(filtered_df, review_queue_df, search_text),
        _build_queue_preview(filtered_df),
        _build_header_html(selected_row, len(filtered_df), len(review_queue_df)),
        _build_row_preview_html(selected_row, review_paths.get("prepared_records_path")),
        _build_record_context_html(selected_row),
        _build_explanation_html(selected_row),
        decision_value,
        evidence_value,
        notes_value,
        _build_summary_html(review_queue_df, review_history_df),
        _build_review_history_preview(review_history_df),
    )

