"""Local Gradio interface for the VAT spreadsheet preparation prototype."""

from __future__ import annotations

import argparse
import html
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import gradio as gr
import pandas as pd
from matplotlib.figure import Figure

from ai.provider_catalog import (
    DEFAULT_PROVIDER,
    get_default_model,
    get_provider_choices,
    get_standard_model_options,
)
from ai.prompts import DEFAULT_EDITABLE_EXPLANATION_PROMPT
from ai.snapshot_builder import build_issue_snapshot
from ai.suggestions_service import generate_advanced_ai_suggestions, try_generate_default_ai_suggestions
from explanation.local_explainer import ISSUE_TYPE_LABELS, generate_automatic_explanation
from export.exporter import ISSUE_REPORT_COLUMNS, export_review_summary
from pipeline import STATUS_STOPPED_AFTER_REPORTING, STATUS_UNSUPPORTED_INPUT, run_pipeline
from review.review_manager import (
    REVIEW_DECISION_OPTIONS,
    REVIEW_HISTORY_COLUMNS,
    REVIEW_LOG_COLUMNS,
    build_review_queue,
    persist_review_outputs,
)

LOGGER = logging.getLogger(__name__)

APP_MODE_LOCAL = "local"
APP_MODE_PUBLIC_DEMO = "public_demo"
DEFAULT_GUI_HOST = "127.0.0.1"
DEFAULT_GUI_PORT = 7860
DEFAULT_PUBLIC_DEMO_MAX_FILE_SIZE = "10mb"
PUBLIC_DEMO_AI_DISABLED_MESSAGE = (
    "AI suggestions are disabled in this public demo. The local automatic explanation is still available."
)
PUBLIC_DEMO_PRIVACY_NOTE = (
    "Public demo mode uses the same local-first GUI shell, but it is intended for limited demonstration only. "
    "Do not upload sensitive spreadsheets. Full source files are not sent to AI by default, and any optional AI path "
    "continues to use a compact findings snapshot only."
)
STATUS_FILTER_OPTIONS = [
    "All review states",
    "Pending",
    "Confirmed issue",
    "Corrected",
    "Accepted with note",
    "False positive",
    "Excluded",
    "Escalated",
]
TYPE_FILTER_MAP = {
    "All finding types": None,
    "Missing values": [
        "missing_transaction_date",
        "missing_net_amount",
        "missing_vat_amount",
        "missing_required_review_field",
    ],
    "Duplicate rows": ["exact_duplicate_row"],
    "Invalid dates": ["invalid_date_format"],
    "Invalid numeric values": ["non_numeric_net_amount", "non_numeric_vat_amount"],
    "Traceability gaps": [
        "missing_counterparty_reference",
        "missing_evidence_reference",
        "missing_transaction_category_support_field",
        "blank_description",
    ],
    "Amount consistency": [
        "inconsistent_totals",
        "conflicting_amount_sign_pattern",
    ],
    "Missing columns": ["missing_column"],
    "Anomalies": [
        "unusual_net_amount",
        "negative_or_unusually_low_net_amount",
        "suspicious_zero_value_amount_combination",
    ],
}
QUEUE_PREVIEW_COLUMNS = ["issue_id", "row_index", "issue_type", "status", "risk_level", "finding_summary", "decision"]
DOWNLOAD_PREVIEW_COLUMNS = [
    "issue_id",
    "finding_summary",
    "why_it_matters",
    "possible_vat_review_impact",
    "trigger_reason",
    "trigger_rule",
    "fields_to_check",
    "suggested_action",
    "review_note",
]
REVIEW_CONTEXT_COLUMNS = [
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
REVIEW_SIGNAL_TYPES = {
    "unusual_net_amount",
    "negative_or_unusually_low_net_amount",
    "suspicious_zero_value_amount_combination",
}
DASHBOARD_PRIORITY_COLUMNS = [
    "issue_id",
    "row_index",
    "issue_type",
    "status",
    "risk_level",
    "decision",
    "finding_summary",
    "why_it_matters",
    "fields_to_check",
    "suggested_action",
]

DECISION_SORT_RANK = {
    "pending": 0,
    "escalated": 1,
    "confirmed_issue": 2,
    "corrected": 3,
    "accepted_with_note": 4,
    "false_positive": 5,
    "excluded_from_review_set": 6,
}

STATUS_SORT_RANK = {
    "Non-compliant": 0,
    "Potentially non-compliant": 1,
    "Review required": 2,
}

ISSUE_TYPE_SORT_RANK = {
    "non_numeric_net_amount": 0,
    "non_numeric_vat_amount": 0,
    "invalid_date_format": 1,
    "missing_transaction_date": 2,
    "missing_net_amount": 2,
    "missing_vat_amount": 2,
    "inconsistent_totals": 3,
    "conflicting_amount_sign_pattern": 3,
    "exact_duplicate_row": 4,
    "duplicate_invoice_reference": 4,
    "missing_required_review_field": 5,
    "missing_column": 5,
    "missing_counterparty_reference": 6,
    "missing_evidence_reference": 6,
    "missing_transaction_category_support_field": 6,
    "blank_description": 7,
    "unusual_net_amount": 8,
    "negative_or_unusually_low_net_amount": 8,
    "suspicious_zero_value_amount_combination": 8,
}


@dataclass(frozen=True)
class GuiLaunchOptions:
    """Thin runtime configuration for launching the shared Gradio shell."""

    host: str
    port: int
    open_browser: bool
    share: bool
    root_path: str | None
    max_file_size: str | None
    strict_cors: bool
    app_mode: str
    enable_ai_assistant: bool


CURRENT_GUI_OPTIONS: GuiLaunchOptions | None = None


def _get_runtime_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


RUNTIME_ROOT = _get_runtime_root()
UI_OUTPUT_ROOT = RUNTIME_ROOT / "output" / "ui_runs"


def _normalise_app_mode(value: str | None) -> str:
    """Keep launch profiles small and explicit."""
    normalised = (value or APP_MODE_LOCAL).strip().lower().replace("-", "_")
    if normalised not in {APP_MODE_LOCAL, APP_MODE_PUBLIC_DEMO}:
        raise ValueError(f"Unsupported GUI mode: {value}")
    return normalised


def _parse_bool(value: str | None, default: bool) -> bool:
    """Parse environment-style booleans conservatively."""
    if value is None:
        return default

    normalised = value.strip().lower()
    if normalised in {"1", "true", "yes", "on"}:
        return True
    if normalised in {"0", "false", "no", "off"}:
        return False
    return default


def _parse_int(value: str | None, default: int) -> int:
    """Parse integer launch settings conservatively."""
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _default_enable_ai_assistant(app_mode: str | None = None) -> bool:
    """Keep AI enabled locally by default, but not for the public-demo profile."""
    resolved_mode = app_mode or _normalise_app_mode(os.getenv("VAT_GUI_MODE"))
    return resolved_mode != APP_MODE_PUBLIC_DEMO


def _is_ai_assistant_enabled(override: bool | None = None) -> bool:
    """Resolve AI availability from explicit overrides, launch settings, or environment."""
    if override is not None:
        return override
    if CURRENT_GUI_OPTIONS is not None:
        return CURRENT_GUI_OPTIONS.enable_ai_assistant
    return _parse_bool(os.getenv("VAT_GUI_ENABLE_AI"), _default_enable_ai_assistant())


def _read_output_csv(file_path: str | None, default_columns: list[str] | None = None) -> pd.DataFrame:
    if not file_path:
        return pd.DataFrame(columns=default_columns or [])
    try:
        return pd.read_csv(file_path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame(columns=default_columns or [])


def _build_run_output_dir() -> Path:
    run_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}"
    output_dir = UI_OUTPUT_ROOT / run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def _normalise_issue_label(issue_type: str) -> str:
    return ISSUE_TYPE_LABELS.get(issue_type, issue_type.replace("_", " "))


def _format_user_status(status: str) -> str:
    if status == STATUS_UNSUPPORTED_INPUT:
        return "Input not supported"
    if status == STATUS_STOPPED_AFTER_REPORTING:
        return "Review needed"
    return "Analysis completed"


def _format_user_stop_reason(status: str, stop_reason: str | None) -> str | None:
    if status == STATUS_UNSUPPORTED_INPUT:
        return "The uploaded file could not be prepared with the current conservative mapping rules."
    if status == STATUS_STOPPED_AFTER_REPORTING or stop_reason:
        return "Reports were created successfully. Review the flagged findings and save a decision trail."
    return None


def _format_preparation_status(preparation_status: str) -> str:
    if preparation_status == "canonical":
        return "Canonical input"
    if preparation_status == "mapped":
        return "Mapped to canonical schema"
    if preparation_status == "unsupported":
        return "Unsupported input"
    return preparation_status.replace("_", " ").title()


def _format_results_overview(
    input_name: str,
    rows_loaded: int,
    issues_found: int,
    anomalies_flagged: int,
    status: str,
    stop_reason: str | None,
    preparation_status: str,
    preparation_message: str,
    missing_required_fields: tuple[str, ...],
) -> str:
    lines = [
        f"## {_format_user_status(status)}",
        "",
        f"**Input file:** `{input_name}`",
        "",
        f"**Rows loaded:** {rows_loaded}  ",
        f"**Preparation:** {_format_preparation_status(preparation_status)}  ",
        f"**Preparation note:** {preparation_message}",
    ]
    if status == STATUS_UNSUPPORTED_INPUT:
        if missing_required_fields:
            lines.append(f"**Missing required fields:** {', '.join(missing_required_fields)}")
    else:
        lines.extend(
            [
                f"**Issues found:** {issues_found}  ",
                f"**Anomaly flags:** {anomalies_flagged}",
            ]
        )
    follow_up_note = _format_user_stop_reason(status, stop_reason)
    if follow_up_note:
        lines.extend(["", f"> {follow_up_note}"])
    return "\n".join(lines)


def _build_message_figure(title: str, message: str) -> Figure:
    figure = Figure(figsize=(5.0, 3.0), layout="constrained")
    axes = figure.subplots()
    axes.axis("off")
    axes.set_title(title, fontsize=11, pad=10)
    axes.text(0.5, 0.5, message, ha="center", va="center", fontsize=10, color="#4b5563")
    return figure


def _icon_svg(name: str) -> str:
    icons = {
        "rows": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 10h18M9 4v16M15 4v16"/></svg>',
        "findings": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M12 9v4"/><path d="M12 17h.01"/><path d="m10.29 3.86-7.5 13A2 2 0 0 0 4.5 20h15a2 2 0 0 0 1.71-3.14l-7.5-13a2 2 0 0 0-3.42 0Z"/></svg>',
        "pending": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="8"/><path d="M12 8v5l3 2"/></svg>',
        "reviewed": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>',
        "duplicate": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><rect x="8" y="8" width="11" height="11" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>',
        "anomaly": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19h16"/><path d="m5 15 4-4 3 3 7-8"/></svg>',
        "review": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5V5a2 2 0 0 1 2-2h8l6 6v10.5a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2Z"/><path d="M14 3v6h6"/></svg>',
        "reason": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="8"/><path d="M9.1 9a3 3 0 0 1 5.8 1c0 2-3 2-3 4"/><path d="M12 17h.01"/></svg>',
        "rule": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M8 6h13"/><path d="M8 12h13"/><path d="M8 18h13"/><path d="M3 6h.01"/><path d="M3 12h.01"/><path d="M3 18h.01"/></svg>',
        "check": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="m21 21-4.3-4.3"/><circle cx="10" cy="10" r="6"/></svg>',
        "action": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="m14 4 6 6-9 9H5v-6l9-9Z"/><path d="m13 5 6 6"/></svg>',
        "interpret": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v18"/><path d="M5 8c0-2.8 3.1-5 7-5s7 2.2 7 5-3.1 5-7 5-7-2.2-7-5Z"/><path d="M5 16c0-2.8 3.1-5 7-5s7 2.2 7 5"/></svg>',
        "context": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M12 21s7-4.35 7-11a7 7 0 1 0-14 0c0 6.65 7 11 7 11Z"/><circle cx="12" cy="10" r="2.5"/></svg>',
        "queue": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M8 6h13"/><path d="M8 12h13"/><path d="M8 18h13"/><path d="M3 6h.01"/><path d="M3 12h.01"/><path d="M3 18h.01"/></svg>',
        "status": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M4 12h4l2-6 4 12 2-6h4"/></svg>',
        "field": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 9h18"/><path d="M9 9v11"/></svg>',
        "priority": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3 14.8 8.7 21 9.6l-4.5 4.3 1.1 6.1L12 17l-5.6 3 1.1-6.1L3 9.6l6.2-.9L12 3Z"/></svg>',
        "insight": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18h6"/><path d="M10 22h4"/><path d="M12 2a7 7 0 0 0-4 12.7c.7.48 1.2 1.16 1.4 1.95L9.5 18h5l.1-1.35c.2-.79.7-1.47 1.4-1.95A7 7 0 0 0 12 2Z"/></svg>',
    }
    return f'<span class="inline-icon" aria-hidden="true">{icons.get(name, icons["insight"])}</span>'


def _issue_type_colour(issue_type: str) -> str:
    palette = {
        "missing_transaction_date": "#f97316",
        "missing_net_amount": "#f97316",
        "missing_vat_amount": "#fb7185",
        "missing_required_review_field": "#f59e0b",
        "exact_duplicate_row": "#6366f1",
        "invalid_date_format": "#ef4444",
        "non_numeric_net_amount": "#ec4899",
        "non_numeric_vat_amount": "#db2777",
        "blank_description": "#a78bfa",
        "duplicate_invoice_reference": "#8b5cf6",
        "inconsistent_totals": "#f43f5e",
        "missing_counterparty_reference": "#60a5fa",
        "missing_evidence_reference": "#38bdf8",
        "missing_transaction_category_support_field": "#60a5fa",
        "missing_column": "#a855f7",
        "unusual_net_amount": "#14b8a6",
        "negative_or_unusually_low_net_amount": "#0ea5e9",
        "suspicious_zero_value_amount_combination": "#22c55e",
        "conflicting_amount_sign_pattern": "#ef4444",
    }
    return palette.get(issue_type, "#94a3b8")


def _build_issue_type_counts_plot(issue_report_df: pd.DataFrame) -> Figure:
    if issue_report_df.empty or "issue_type" not in issue_report_df.columns:
        return _build_message_figure("Issue Type Counts", "No findings to plot.")

    issue_counts = issue_report_df["issue_type"].dropna().astype(str).value_counts().sort_values(ascending=False)
    if issue_counts.empty:
        return _build_message_figure("Issue Type Counts", "No findings to plot.")

    labels = [_normalise_issue_label(issue_type) for issue_type in issue_counts.index]
    values = issue_counts.tolist()
    figure = Figure(figsize=(5.3, 3.4), layout="constrained")
    axes = figure.subplots()
    colors = [_issue_type_colour(issue_type) for issue_type in issue_counts.index][::-1]
    bars = axes.barh(labels[::-1], values[::-1], color=colors, height=0.62)
    axes.bar_label(bars, padding=4, color="#d8e2f1", fontsize=8)
    axes.set_title("Findings by Type", fontsize=11, pad=10)
    axes.set_xlabel("Count")
    axes.grid(axis="x", color="#d9dee3", linewidth=0.8, alpha=0.4)
    axes.set_axisbelow(True)
    axes.set_facecolor("#0f172a")
    figure.patch.set_facecolor("#0f172a")
    axes.tick_params(colors="#d8e2f1", labelsize=8.5)
    axes.xaxis.label.set_color("#d8e2f1")
    axes.title.set_color("#f8fafc")
    for spine in axes.spines.values():
        spine.set_color("#334155")
    return figure


def _build_review_status_plot(review_queue_df: pd.DataFrame) -> Figure:
    if review_queue_df.empty or "decision" not in review_queue_df.columns:
        return _build_message_figure("Review Status", "Run an analysis to load review status metrics.")

    status_order = [
        ("pending", "Pending", "#60a5fa"),
        ("confirmed_issue", "Confirmed", "#22c55e"),
        ("corrected", "Corrected", "#16a34a"),
        ("accepted_with_note", "Accepted", "#94a3b8"),
        ("false_positive", "False positive", "#c084fc"),
        ("excluded_from_review_set", "Excluded", "#f97316"),
        ("escalated", "Escalated", "#f87171"),
    ]
    counts = review_queue_df["decision"].fillna("pending").astype(str).value_counts()
    labels = [label for _, label, _ in status_order]
    values = [int(counts.get(status, 0)) for status, _, _ in status_order]
    colors = [color for _, _, color in status_order]

    figure = Figure(figsize=(5.3, 3.4), layout="constrained")
    axes = figure.subplots()
    bars = axes.bar(labels, values, color=colors, width=0.62)
    axes.bar_label(bars, padding=4, color="#d8e2f1", fontsize=8)
    axes.set_title("Review Status", fontsize=11, pad=10)
    axes.set_ylabel("Findings")
    axes.grid(axis="y", color="#d9dee3", linewidth=0.8, alpha=0.35)
    axes.set_axisbelow(True)
    axes.set_facecolor("#0f172a")
    figure.patch.set_facecolor("#0f172a")
    axes.tick_params(colors="#d8e2f1", labelsize=8.5)
    axes.yaxis.label.set_color("#d8e2f1")
    axes.title.set_color("#f8fafc")
    for spine in axes.spines.values():
        spine.set_color("#334155")
    return figure


def _derive_review_field_series(issue_report_df: pd.DataFrame) -> pd.Series:
    if issue_report_df.empty:
        return pd.Series(dtype=int)

    field_values: list[str] = []
    for _, row in issue_report_df.iterrows():
        value = row.get("fields_to_check")
        if pd.isna(value) or not str(value).strip():
            value = row.get("checked_column") or row.get("column")
        if pd.isna(value) or not str(value).strip():
            continue
        for part in str(value).split(","):
            cleaned = part.strip().lower()
            if cleaned:
                field_values.append(cleaned)
    if not field_values:
        return pd.Series(dtype=int)
    return pd.Series(field_values).value_counts().head(6)


def _build_field_focus_plot(issue_report_df: pd.DataFrame) -> Figure:
    field_counts = _derive_review_field_series(issue_report_df)
    if field_counts.empty:
        return _build_message_figure("Field Focus", "No field-level review targets were recorded for this run.")

    labels = [field.replace("_", " ") for field in field_counts.index]
    values = field_counts.tolist()
    figure = Figure(figsize=(5.3, 3.4), layout="constrained")
    axes = figure.subplots()
    bars = axes.barh(labels[::-1], values[::-1], color="#38bdf8", height=0.62)
    axes.bar_label(bars, padding=4, color="#d8e2f1", fontsize=8)
    axes.set_title("Fields Attracting Review", fontsize=11, pad=10)
    axes.set_xlabel("Findings")
    axes.grid(axis="x", color="#d9dee3", linewidth=0.8, alpha=0.35)
    axes.set_axisbelow(True)
    axes.set_facecolor("#0f172a")
    figure.patch.set_facecolor("#0f172a")
    axes.tick_params(colors="#d8e2f1", labelsize=8.5)
    axes.xaxis.label.set_color("#d8e2f1")
    axes.title.set_color("#f8fafc")
    for spine in axes.spines.values():
        spine.set_color("#334155")
    return figure


def _build_anomaly_amount_plot(issue_report_df: pd.DataFrame) -> Figure:
    if issue_report_df.empty or "issue_type" not in issue_report_df.columns:
        return _build_message_figure("Review Signal Overview", "No amount-based review signals were recorded for this run.")

    anomaly_rows = issue_report_df[issue_report_df["issue_type"].isin(REVIEW_SIGNAL_TYPES)].copy()
    if anomaly_rows.empty:
        return _build_message_figure("Review Signal Overview", "No amount-based review signals were recorded for this run.")

    anomaly_rows["observed_value"] = anomaly_rows["observed_value"].where(
        anomaly_rows["observed_value"].notna(),
        anomaly_rows.get("value"),
    )
    anomaly_rows["observed_value"] = pd.to_numeric(anomaly_rows["observed_value"], errors="coerce")
    anomaly_rows = anomaly_rows.dropna(subset=["observed_value"])
    if anomaly_rows.empty:
        return _build_message_figure("Review Signal Overview", "No amount-based review signals were recorded for this run.")

    lower_bound = pd.to_numeric(anomaly_rows["lower_bound"], errors="coerce").dropna()
    upper_bound = pd.to_numeric(anomaly_rows["upper_bound"], errors="coerce").dropna()
    lower_value = lower_bound.iloc[0] if not lower_bound.empty else None
    upper_value = upper_bound.iloc[0] if not upper_bound.empty else None

    deviation = pd.Series(0.0, index=anomaly_rows.index)
    if lower_value is not None:
        deviation = deviation.where(anomaly_rows["observed_value"] >= lower_value, lower_value - anomaly_rows["observed_value"])
    if upper_value is not None:
        deviation = deviation.where(anomaly_rows["observed_value"] <= upper_value, anomaly_rows["observed_value"] - upper_value)
    anomaly_rows["deviation"] = deviation.abs()
    anomaly_rows = anomaly_rows.sort_values(["deviation", "observed_value"], ascending=[False, False]).head(10)
    labels = [f"{row['issue_id']} | row {int(row['row_index'])}" for _, row in anomaly_rows.iterrows()]

    figure = Figure(figsize=(5.3, 3.4), layout="constrained")
    axes = figure.subplots()
    bars = axes.barh(labels[::-1], anomaly_rows["observed_value"].tolist()[::-1], color="#f59e0b", height=0.62)
    axes.bar_label(
        bars,
        labels=[f"{value:,.0f}" for value in anomaly_rows["observed_value"].tolist()[::-1]],
        padding=4,
        color="#d8e2f1",
        fontsize=8,
    )
    if lower_value is not None:
        axes.axvline(lower_value, color="#93c5fd", linestyle="--", linewidth=1.2, label="Lower bound")
    if upper_value is not None:
        axes.axvline(upper_value, color="#c4b5fd", linestyle="--", linewidth=1.2, label="Upper bound")
    axes.set_title("Top Unusual Amounts", fontsize=11, pad=10)
    axes.set_xlabel("Observed net amount")
    axes.grid(axis="x", color="#d9dee3", linewidth=0.8, alpha=0.35)
    axes.set_axisbelow(True)
    axes.set_facecolor("#0f172a")
    figure.patch.set_facecolor("#0f172a")
    axes.tick_params(colors="#d8e2f1", labelsize=8.3)
    axes.xaxis.label.set_color("#d8e2f1")
    axes.title.set_color("#f8fafc")
    if lower_value is not None or upper_value is not None:
        axes.legend(loc="best", fontsize=8)
    for spine in axes.spines.values():
        spine.set_color("#334155")
    return figure


def _format_amount(value: object) -> str:
    numeric_value = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric_value):
        return "blank"
    return f"GBP {float(numeric_value):,.2f}"


def _build_anomaly_note(issue_report_df: pd.DataFrame) -> str:
    if issue_report_df.empty or "issue_type" not in issue_report_df.columns:
        return "No amount-based review signals were recorded for this run."
    anomaly_rows = issue_report_df[issue_report_df["issue_type"].isin(REVIEW_SIGNAL_TYPES)].copy()
    if anomaly_rows.empty:
        return "No amount-based review signals were recorded for this run."
    lower_bound = pd.to_numeric(anomaly_rows.get("lower_bound"), errors="coerce").dropna()
    upper_bound = pd.to_numeric(anomaly_rows.get("upper_bound"), errors="coerce").dropna()
    lines = [
        f"{len(anomaly_rows)} amount-oriented review signal(s) were flagged in this run.",
        "These prompts include unusual, negative, or otherwise context-sensitive amount patterns that should be checked against supporting evidence.",
    ]
    if not lower_bound.empty and not upper_bound.empty:
        lines.append(
            f"For this run, the lower bound was {_format_amount(lower_bound.iloc[0])} and the upper bound was {_format_amount(upper_bound.iloc[0])}."
        )
    lines.append("These flags are prompts for review, not automatic proof of error.")
    return " ".join(lines)


def _build_visual_summary_html(
    issue_report_df: pd.DataFrame,
    review_queue_df: pd.DataFrame,
    review_history_df: pd.DataFrame,
    prepared_records_path: str | None,
    review_summary_path: str | None = None,
) -> str:
    review_summary_df = _read_output_csv(review_summary_path) if review_summary_path else pd.DataFrame()
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

    prepared_rows = len(_read_output_csv(prepared_records_path, default_columns=REVIEW_CONTEXT_COLUMNS))
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
    """Normalise legacy queue/report dataframes to use ``issue_id`` as the primary key."""
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

    prepared_df = _read_output_csv(prepared_records_path, default_columns=REVIEW_CONTEXT_COLUMNS)
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


def run_analysis(
    uploaded_file,
    editable_explanation_prompt: str,
    advanced_instructions: str | None,
    enable_ai_assistant: bool | None = None,
) -> tuple:
    if uploaded_file is None:
        raise gr.Error("Please upload a CSV or Excel file before running the analysis.")

    input_path = Path(uploaded_file)
    output_dir = _build_run_output_dir()
    LOGGER.info("Running local UI analysis for %s", input_path)

    result = run_pipeline(str(input_path), str(output_dir))
    issue_report_df = _read_output_csv(result.issue_report_path, default_columns=ISSUE_REPORT_COLUMNS)
    review_log_df = _read_output_csv(result.review_log_path, default_columns=REVIEW_LOG_COLUMNS)
    review_history_df = _read_output_csv(result.review_history_path, default_columns=REVIEW_HISTORY_COLUMNS)
    review_summary_df = _read_output_csv(result.review_summary_path)
    review_queue_df = build_review_queue(issue_report_df, review_log_df)

    if result.status == STATUS_UNSUPPORTED_INPUT:
        explanation = (
            "#### Preparation Result\n"
            "The uploaded file could not be prepared into the prototype's canonical schema, so validation and anomaly checks were not run.\n\n"
            "#### What To Check Next\n"
            "- Review the column headings in the source file.\n"
            "- Provide columns that clearly map to date, description, net amount, and VAT amount.\n"
            "- Re-upload the file after adjusting the headings."
        )
        ai_snapshot = None
        ai_suggestions = "AI suggestions are unavailable because the file could not be prepared for analysis."
    else:
        explanation = generate_automatic_explanation(result, issue_report_df, review_log_df)
        ai_snapshot = build_issue_snapshot(result, issue_report_df, review_log_df)
        if _is_ai_assistant_enabled(enable_ai_assistant):
            ai_suggestions = try_generate_default_ai_suggestions(
                ai_snapshot,
                editable_explanation_prompt,
                advanced_instructions,
            )
        else:
            ai_suggestions = PUBLIC_DEMO_AI_DISABLED_MESSAGE

    review_paths = {
        "issue_report_path": result.issue_report_path,
        "review_log_path": result.review_log_path,
        "review_history_path": result.review_history_path,
        "review_summary_path": result.review_summary_path,
        "prepared_records_path": result.prepared_canonical_records_path,
        "source_filename": input_path.name,
    }
    review_workspace = _build_review_workspace(
        review_queue_df,
        review_history_df,
        review_paths,
        "All review states",
        "All finding types",
        "",
        None,
    )
    visual_bundle = _build_visual_insights_bundle(
        issue_report_df,
        review_queue_df,
        review_history_df,
        result.prepared_canonical_records_path,
        result.review_summary_path,
    )

    return (
        _format_results_overview(
            input_name=input_path.name,
            rows_loaded=result.rows_loaded,
            issues_found=result.issues_found,
            anomalies_flagged=result.anomalies_flagged,
            status=result.status,
            stop_reason=result.stop_reason,
            preparation_status=result.preparation_status,
            preparation_message=result.preparation_message,
            missing_required_fields=result.missing_required_fields,
        ),
        explanation,
        ai_suggestions,
        ai_snapshot,
        *visual_bundle,
        result.issue_report_path,
        result.review_log_path,
        result.review_history_path,
        result.review_summary_path,
        result.dataset_snapshot_path,
        result.prepared_canonical_records_path,
        _build_issue_report_preview(issue_report_df),
        _build_review_summary_preview(review_summary_df),
        "All review states",
        "All finding types",
        "",
        *review_workspace,
        _queue_to_records(review_queue_df),
        _queue_to_records(review_history_df),
        review_paths,
    )


def refresh_review_workspace(
    selected_issue: str | None,
    status_filter: str,
    type_filter: str,
    search_text: str,
    review_queue_records: list[dict] | None,
    review_history_records: list[dict] | None,
    review_paths: dict | None,
) -> tuple:
    review_queue_df = _records_to_queue(review_queue_records)
    review_history_df = _records_to_queue(review_history_records)
    return _build_review_workspace(
        review_queue_df,
        review_history_df,
        review_paths or {},
        status_filter,
        type_filter,
        search_text,
        selected_issue,
    )


def save_review_decision(
    selected_issue: str | None,
    decision: str,
    evidence_checked: str,
    notes: str,
    status_filter: str,
    type_filter: str,
    search_text: str,
    review_queue_records: list[dict] | None,
    review_paths: dict | None,
) -> tuple:
    if not review_paths or not review_paths.get("review_log_path") or not review_paths.get("review_history_path"):
        raise gr.Error("Run an analysis first so the review files can be created.")

    review_queue_df = _records_to_queue(review_queue_records)
    review_queue_df = _ensure_issue_id_column(review_queue_df)
    if review_queue_df.empty:
        raise gr.Error("There are no issues available for review in the current run.")

    issue_id = _extract_issue_id(selected_issue)
    if not issue_id:
        raise gr.Error("Select an issue before saving a review decision.")

    matching_rows = review_queue_df["issue_id"] == issue_id
    if not matching_rows.any():
        raise gr.Error("The selected issue could not be located in the current review queue.")

    normalised_decision = (decision or "pending").strip().lower()
    normalised_evidence = (evidence_checked or "").strip()
    normalised_notes = (notes or "").strip()

    if normalised_decision != "pending":
        if not normalised_evidence:
            raise gr.Error("Record what evidence was checked before saving a review decision.")
        if not normalised_notes:
            raise gr.Error("Add a short decision reason or review note before saving a review decision.")

    review_queue_df.loc[matching_rows, "decision"] = normalised_decision
    review_queue_df.loc[matching_rows, "evidence_checked"] = normalised_evidence
    review_queue_df.loc[matching_rows, "notes"] = normalised_notes

    current_log_df, review_history_df = persist_review_outputs(
        review_queue_df,
        review_paths["review_log_path"],
        review_paths["review_history_path"],
    )
    issue_report_df = _read_output_csv(review_paths["issue_report_path"], default_columns=ISSUE_REPORT_COLUMNS)
    prepared_records_df = _read_output_csv(review_paths.get("prepared_records_path"))
    if review_paths.get("review_summary_path"):
        export_review_summary(
            issue_report_df,
            prepared_records_df,
            current_log_df,
            review_paths["review_summary_path"],
            dataset_id=f"DATASET-{Path(review_paths['review_summary_path']).resolve().parent.name}",
            source_filename=review_paths.get("source_filename"),
        )
    review_summary_df = _read_output_csv(review_paths.get("review_summary_path"))
    refreshed_queue_df = build_review_queue(issue_report_df, current_log_df)
    review_workspace = _build_review_workspace(
        refreshed_queue_df,
        review_history_df,
        review_paths,
        status_filter,
        type_filter,
        search_text,
        selected_issue,
    )
    visual_bundle = _build_visual_insights_bundle(
        issue_report_df,
        refreshed_queue_df,
        review_history_df,
        review_paths.get("prepared_records_path"),
        review_paths.get("review_summary_path"),
    )

    return (
        "Review decision, notes, and evidence checked were saved to the current review log and appended to review history.",
        review_paths["review_log_path"],
        review_paths["review_history_path"],
        review_paths["review_summary_path"],
        *visual_bundle,
        *review_workspace,
        _queue_to_records(refreshed_queue_df),
        _queue_to_records(review_history_df),
        _build_review_summary_preview(review_summary_df),
    )


def request_enhanced_ai_suggestions(
    snapshot: dict | None,
    provider: str,
    model: str,
    custom_model: str,
    base_url: str,
    api_key: str,
    editable_explanation_prompt: str,
    advanced_instructions: str | None,
    enable_ai_assistant: bool | None = None,
) -> str:
    if not _is_ai_assistant_enabled(enable_ai_assistant):
        return PUBLIC_DEMO_AI_DISABLED_MESSAGE

    return generate_advanced_ai_suggestions(
        snapshot,
        provider,
        model,
        custom_model,
        base_url,
        api_key,
        editable_explanation_prompt,
        advanced_instructions,
    )


def update_provider_configuration(provider: str):
    if provider == "custom_openai_compatible":
        return (
            gr.update(choices=[], value=None, visible=False),
            gr.update(value="", visible=True),
            gr.update(value="", visible=True),
        )

    model_options = get_standard_model_options(provider)
    default_model = get_default_model(provider)
    if default_model not in model_options and model_options:
        default_model = model_options[0]
    return (
        gr.update(choices=model_options, value=default_model, visible=True),
        gr.update(value="", visible=False),
        gr.update(value="", visible=False),
    )


def build_interface() -> gr.Blocks:
    app_mode = CURRENT_GUI_OPTIONS.app_mode if CURRENT_GUI_OPTIONS is not None else _normalise_app_mode(os.getenv("VAT_GUI_MODE"))
    ai_enabled = _is_ai_assistant_enabled()
    custom_css = """
    :root {
      --app-panel-bg: rgba(255, 255, 255, 0.92);
      --app-card-bg: rgba(248, 250, 252, 0.96);
      --app-soft-bg: rgba(241, 245, 249, 0.96);
      --app-overlay-bg: rgba(226, 232, 240, 0.48);
      --app-input-bg: rgba(255, 255, 255, 0.98);
      --app-input-soft-bg: rgba(248, 250, 252, 0.96);
      --app-table-bg: #f8fafc;
      --app-table-alt-odd: #f8fafc;
      --app-table-alt-even: #eef2ff;
      --app-table-index: #e2e8f0;
      --app-table-highlight: #dbeafe;
      --app-table-current: #e0e7ff;
      --app-table-current-index: #c7d2fe;
      --app-table-head: #dbeafe;
      --app-table-head-index: #cbd5e1;
      --app-text-strong: #0f172a;
      --app-text-main: #1e293b;
      --app-text-muted: #334155;
      --app-text-soft: #475569;
      --app-text-label: #64748b;
      --app-border: rgba(148, 163, 184, 0.28);
      --app-border-strong: rgba(148, 163, 184, 0.34);
      --app-shadow-lg: 0 18px 48px rgba(148, 163, 184, 0.18);
      --app-shadow-md: 0 14px 36px rgba(148, 163, 184, 0.14);
      --app-alert-bg: linear-gradient(180deg, rgba(254, 242, 242, 0.98), rgba(255, 241, 242, 0.96));
      --app-alert-border: rgba(248, 113, 113, 0.32);
      --app-alert-title: #b91c1c;
      --app-alert-body: #7f1d1d;
      --app-alert-impact: #991b1b;
      --app-tab-bg: rgba(255, 255, 255, 0.96);
      --app-tab-hover-bg: rgba(239, 246, 255, 0.98);
      --app-tab-selected-bg: rgba(224, 231, 255, 0.92);
      --app-tab-selected-border: rgba(99, 102, 241, 0.35);
      --app-tab-selected-accent: #6366f1;
      --app-accordion-bg: rgba(248, 250, 252, 0.98);
      --app-accordion-hover-bg: rgba(239, 246, 255, 0.98);
      --app-divider-shadow: rgba(255,255,255,0);
    }
    @media (prefers-color-scheme: dark) {
      :root {
        --app-panel-bg: rgba(20, 30, 48, 0.9);
        --app-card-bg: rgba(32, 45, 68, 0.94);
        --app-soft-bg: rgba(15, 23, 42, 0.48);
        --app-overlay-bg: rgba(20, 30, 48, 0.44);
        --app-input-bg: rgba(58, 74, 101, 0.94);
        --app-input-soft-bg: rgba(20, 30, 48, 0.7);
        --app-table-bg: #1f2937;
        --app-table-alt-odd: #233149;
        --app-table-alt-even: #1f2b40;
        --app-table-index: #31415b;
        --app-table-highlight: #42517a;
        --app-table-current: #2e3d63;
        --app-table-current-index: #3b4c72;
        --app-table-head: #273449;
        --app-table-head-index: #334155;
        --app-text-strong: #f8fafc;
        --app-text-main: #dbe6ff;
        --app-text-muted: #c7d4ea;
        --app-text-soft: #b8c3d8;
        --app-text-label: #9fb2d1;
        --app-border: rgba(148, 163, 184, 0.18);
        --app-border-strong: rgba(148, 163, 184, 0.24);
        --app-shadow-lg: 10px 10px 24px rgba(5, 10, 22, 0.32), -6px -6px 18px rgba(255, 255, 255, 0.03);
        --app-shadow-md: 8px 8px 20px rgba(5, 10, 22, 0.26), -4px -4px 14px rgba(255, 255, 255, 0.025);
        --app-alert-bg: linear-gradient(180deg, rgba(127, 29, 29, 0.30), rgba(69, 10, 10, 0.18));
        --app-alert-border: rgba(248, 113, 113, 0.24);
        --app-alert-title: #fecaca;
        --app-alert-body: #fff1f2;
        --app-alert-impact: #fecdd3;
        --app-tab-bg: rgba(20, 30, 48, 0.88);
        --app-tab-hover-bg: rgba(32, 45, 68, 0.82);
        --app-tab-selected-bg: rgba(79, 70, 229, 0.22);
        --app-tab-selected-border: rgba(124, 131, 255, 0.45);
        --app-tab-selected-accent: #7c83ff;
        --app-accordion-bg: rgba(32, 45, 68, 0.94);
        --app-accordion-hover-bg: rgba(38, 54, 82, 0.96);
        --app-divider-shadow: rgba(255,255,255,0.03);
      }
    }
    .workspace-root { max-width: 1480px; margin: 0 auto; padding: 20px 0 36px; color: var(--app-text-main); }
    .panel { background: var(--app-panel-bg); border: 1px solid var(--app-border-strong); border-radius: 18px; padding: 18px; box-shadow: var(--app-shadow-lg); }
    .hero-card, .summary-card, .row-preview-card, .context-card, .dashboard-shell, .action-card, .reference-card { background: var(--app-card-bg); border: 1px solid var(--app-border); border-radius: 18px; padding: 18px; box-shadow: var(--app-shadow-md); }
    .hero-title { font-size: 1.45rem; font-weight: 700; line-height: 1.2; }
    .hero-subtitle { margin-top: 8px; font-size: 1rem; color: var(--app-text-main); }
    .eyebrow { text-transform: uppercase; letter-spacing: .08em; font-size: .72rem; color: var(--app-text-label); margin-bottom: 8px; }
    .hero-row { display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; }
    .hero-badges { display: flex; gap: 8px; flex-wrap: wrap; }
    .hero-meta { margin-top: 12px; color: var(--app-text-soft); font-size: .92rem; }
    .hero-alert { margin-top: 14px; padding: 14px 16px; border-radius: 16px; border: 1px solid var(--app-alert-border); background: var(--app-alert-bg); box-shadow: inset 0 1px 0 rgba(255,255,255,0.03); }
    .hero-alert-title { font-size: .84rem; font-weight: 700; letter-spacing: .04em; text-transform: uppercase; color: var(--app-alert-title); margin-bottom: 8px; }
    .hero-alert-body { color: var(--app-alert-body); font-size: .98rem; line-height: 1.5; }
    .hero-alert-impact { margin-top: 8px; color: var(--app-alert-impact); font-size: .92rem; line-height: 1.45; }
    .badge { display: inline-flex; align-items: center; padding: 6px 10px; border-radius: 999px; font-size: .8rem; font-weight: 600; }
    .badge-pending { background: rgba(96, 165, 250, 0.15); color: #bfdbfe; }
    .badge-confirm { background: rgba(34, 197, 94, 0.15); color: #bbf7d0; }
    .badge-reject { background: rgba(248, 113, 113, 0.16); color: #fecaca; }
    .badge-ignore { background: rgba(148, 163, 184, 0.16); color: #cbd5e1; }
    .badge-anomaly { background: rgba(245, 158, 11, 0.16); color: #fde68a; }
    .badge-data { background: rgba(244, 114, 182, 0.14); color: #fbcfe8; }
    .badge-neutral { background: rgba(148, 163, 184, 0.16); color: #e2e8f0; }
    .summary-title, .row-preview-title, .context-title, .action-title, .reference-title { font-size: 1.02rem; font-weight: 700; margin-bottom: 12px; }
    .metric-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
    .summary-inline-card { padding: 14px 16px; }
    .metric-strip { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
    .metric-chip { border-radius: 14px; padding: 10px 10px; border: 1px solid var(--app-border); background: var(--app-soft-bg); min-height: 64px; box-shadow: inset 1px 1px 0 rgba(255,255,255,0.03); }
    .metric-chip-value { font-size: 1.08rem; font-weight: 700; line-height: 1; }
    .metric-chip-label { margin-top: 5px; font-size: .76rem; line-height: 1.25; color: var(--app-text-soft); }
    .summary-footnote, .filter-hint, .row-preview-helper, .context-empty, .row-preview-empty, .action-helper, .reference-summary-copy { margin-top: 12px; color: var(--app-text-soft); font-size: .9rem; }
    .detail-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
    .reference-detail-card { background: var(--app-soft-bg); border: 1px solid var(--app-border); border-radius: 16px; padding: 16px; min-height: 124px; }
    .detail-title { font-size: .8rem; font-weight: 700; letter-spacing: .04em; text-transform: uppercase; color: var(--app-text-label); margin-bottom: 8px; }
    .detail-body { font-size: 1rem; line-height: 1.5; color: var(--app-text-strong); }
    .action-card { border-color: rgba(96, 165, 250, 0.24); box-shadow: inset 0 0 0 1px rgba(96, 165, 250, 0.08); padding: 14px 16px; }
    .action-body { font-size: .96rem; line-height: 1.45; color: var(--app-text-strong); }
    .reference-details { display: block; }
    .reference-summary { display: flex; justify-content: space-between; gap: 16px; align-items: center; cursor: pointer; list-style: none; }
    .reference-summary::-webkit-details-marker { display: none; }
    .reference-grid { margin-top: 14px; }
    .decision-panel { border-color: rgba(244, 114, 182, 0.18); }
    .module-intro { margin-bottom: 10px; padding-bottom: 8px; border-bottom: 1px solid var(--app-border); }
    .module-intro-title { font-size: 1.02rem; font-weight: 700; color: var(--app-text-strong); }
    .module-intro-copy { display: none; }
    .context-table, .row-preview-table { width: 100%; border-collapse: collapse; }
    .context-table th, .context-table td, .row-preview-table th, .row-preview-table td { padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--app-border); vertical-align: top; color: var(--app-text-main); }
    .context-table th, .row-preview-table th { color: var(--app-text-label); font-size: .82rem; text-transform: uppercase; letter-spacing: .04em; }
    .row-preview-table-wrap { overflow-x: auto; }
    .excel-sheet-wrap { margin-top: 12px; border: 1px solid var(--app-border-strong); border-radius: 10px; background: var(--app-table-bg); box-shadow: inset 0 1px 0 rgba(255,255,255,0.03); }
    .row-preview-table { font-family: Calibri, "Segoe UI", Arial, sans-serif; background: var(--app-table-bg); }
    .row-preview-table thead th { background: var(--app-table-head); color: var(--app-text-main); border-right: 1px solid var(--app-border-strong); border-bottom: 1px solid var(--app-border-strong); font-size: .78rem; font-weight: 700; letter-spacing: 0; }
    .row-preview-table thead th:first-child { background: var(--app-table-head-index); color: var(--app-text-strong); }
    .row-preview-table th, .row-preview-table td { padding: 8px 10px; font-size: .84rem; word-break: break-word; border-right: 1px solid var(--app-border); border-bottom: 1px solid var(--app-border); }
    .row-preview-table tbody tr:nth-child(odd) td { background: var(--app-table-alt-odd); }
    .row-preview-table tbody tr:nth-child(even) td { background: var(--app-table-alt-even); }
    .row-preview-table tbody td:first-child { background: var(--app-table-index); color: var(--app-text-strong); font-weight: 700; width: 72px; white-space: nowrap; }
    .current-row td { background: var(--app-table-current) !important; }
    .current-row td:first-child { background: var(--app-table-current-index) !important; }
    .flagged-cell { position: relative; background: var(--app-table-highlight) !important; font-weight: 700; box-shadow: inset 0 0 0 2px #22c55e; }
    .evidence-summary { display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; margin-bottom: 14px; padding-bottom: 12px; border-bottom: 1px solid var(--app-border); }
    .evidence-summary-main { min-width: 0; }
    .evidence-summary-title { font-size: 1.35rem; font-weight: 700; line-height: 1.2; color: var(--app-text-strong); }
    .evidence-summary-subtitle { margin-top: 6px; color: var(--app-text-main); font-size: .98rem; }
    .evidence-action { margin-top: 14px; padding-top: 14px; border-top: 1px solid var(--app-border); }
    .queue-subtitle { color: var(--app-text-soft); margin-top: 4px; margin-bottom: 12px; }
    .queue-filter-grid { display: grid; grid-template-columns: repeat(1, minmax(0, 1fr)); gap: 10px; margin-bottom: 10px; }
    .queue-table-wrap { margin-top: 10px; }
    .history-accordion { margin-top: 12px; }
    .review-shell { gap: 18px; align-items: flex-start; }
    .queue-panel, .review-flow-panel { gap: 14px; }
    .review-flow-panel { border-left: 1px solid var(--app-border-strong); padding-left: 22px; box-shadow: inset 1px 0 0 var(--app-divider-shadow); }
    .active-finding-panel { margin-bottom: 10px; }
    .secondary-accordion { margin-top: 12px; }
    .gradio-container .tab-wrapper, .gradio-container .tabs { border-bottom: 1px solid var(--app-border); margin-bottom: 18px; padding-bottom: 12px; box-shadow: inset 0 -1px 0 var(--app-divider-shadow); }
    .gradio-container .tab-nav { gap: 8px; padding: 6px; background: var(--app-tab-bg); border: 1px solid var(--app-border); border-radius: 16px; display: inline-flex; box-shadow: inset 0 1px 0 rgba(255,255,255,0.03); }
    .gradio-container .tab-nav button, .gradio-container button[role="tab"] { position: relative; padding: 10px 16px; border-radius: 12px; border: 1px solid transparent; color: var(--app-text-muted); background: transparent; }
    .gradio-container .tab-nav button:hover, .gradio-container button[role="tab"]:hover { background: var(--app-tab-hover-bg); color: var(--app-text-strong); border-color: var(--app-border); }
    .gradio-container .tab-nav button.selected, .gradio-container button[role="tab"][aria-selected="true"] { background: var(--app-tab-selected-bg); color: var(--app-text-strong); border-color: var(--app-tab-selected-border); box-shadow: inset 0 -2px 0 var(--app-tab-selected-accent), 0 0 0 1px rgba(255,255,255,0.03); }
    .gradio-container button, .gradio-container [role="button"] { transition: background .18s ease, border-color .18s ease, box-shadow .18s ease; }
    .gradio-container .secondary-accordion button, .gradio-container .history-accordion button, .gradio-container .accordion button { background: var(--app-accordion-bg); border: 1px solid var(--app-border-strong); color: var(--app-text-strong); box-shadow: 6px 6px 14px rgba(5,10,22,0.18), -3px -3px 10px rgba(255,255,255,0.02); }
    .gradio-container .secondary-accordion button:hover, .gradio-container .history-accordion button:hover, .gradio-container .accordion button:hover { border-color: rgba(96, 165, 250, 0.42); background: var(--app-accordion-hover-bg); }
    .gradio-container .secondary-accordion button::after, .gradio-container .history-accordion button::after, .gradio-container .accordion button::after { content: "v"; margin-left: auto; color: var(--app-text-main); font-size: .9rem; }
    .gradio-container .wrap .form > *, .gradio-container .form > * { border-color: rgba(148, 163, 184, 0.18); }
    .gradio-container .queue-filter-grid .wrap, .gradio-container .queue-filter-grid .form, .gradio-container .queue-filter-grid input, .gradio-container .queue-filter-grid textarea, .gradio-container .queue-filter-grid button { box-shadow: none; }
    .gradio-container .queue-filter-grid .wrap, .gradio-container .queue-filter-grid .form { border-top: 1px solid var(--app-border); padding-top: 10px; }
    .gradio-container .queue-filter-grid > *:first-child .wrap, .gradio-container .queue-filter-grid > *:first-child .form { border-top: none; padding-top: 0; }
    .gradio-container .queue-filter-grid button, .gradio-container .queue-filter-grid input, .gradio-container .queue-filter-grid textarea { border: 1px solid var(--app-border-strong); background: var(--app-input-bg); color: var(--app-text-strong); }
    .gradio-container .queue-filter-grid button:hover, .gradio-container .queue-filter-grid input:hover, .gradio-container .queue-filter-grid textarea:hover { border-color: rgba(96, 165, 250, 0.4); }
    .gradio-container .queue-filter-grid label, .gradio-container .decision-panel label { color: var(--app-text-main); }
    .gradio-container .queue-filter-grid textarea, .gradio-container .queue-filter-grid input[type="text"] { min-height: 48px !important; height: 48px !important; line-height: 1.35; padding-top: 12px; padding-bottom: 12px; resize: none; overflow: hidden; }
    .gradio-container .queue-filter-grid textarea::placeholder, .gradio-container .queue-filter-grid input[type="text"]::placeholder { color: var(--app-text-label); }
    .gradio-container .queue-filter-grid .scroll-hide, .gradio-container .queue-filter-grid [class*="scroll"] { scrollbar-width: thin; }
    .gradio-container .queue-filter-grid .form { overflow: visible; }
    .gradio-container .decision-panel { padding: 10px 14px 14px; margin-top: 6px; }
    .gradio-container .decision-panel .wrap { border: 1px solid var(--app-border); border-radius: 14px; background: var(--app-input-soft-bg); }
    .gradio-container .decision-panel .wrap label { padding: 6px 10px; border-right: 1px solid var(--app-border); }
    .gradio-container .decision-panel .wrap label:last-child { border-right: none; }
    .gradio-container .decision-panel .wrap label:hover { background: rgba(79, 70, 229, 0.12); }
    .inline-icon { display: inline-flex; width: 16px; height: 16px; margin-right: 8px; flex: 0 0 16px; vertical-align: -3px; }
    .inline-icon svg { width: 16px; height: 16px; }
    .title-with-icon { display: inline-flex; align-items: center; gap: 8px; }
    .dashboard-title-row { display: flex; justify-content: space-between; gap: 20px; align-items: flex-start; }
    .dashboard-title { font-size: 1.35rem; font-weight: 700; color: var(--app-text-strong); }
    .dashboard-subtitle { margin-top: 8px; color: var(--app-text-muted); line-height: 1.55; }
    .dashboard-section-kicker { display: inline-flex; align-items: center; gap: 8px; padding: 5px 10px; border-radius: 999px; background: rgba(79, 70, 229, 0.14); border: 1px solid rgba(124, 131, 255, 0.24); color: var(--app-text-muted); font-size: .72rem; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; }
    .dashboard-kpi-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin-top: 18px; }
    .dashboard-kpi-card { background: linear-gradient(180deg, var(--app-soft-bg), var(--app-card-bg)); border: 1px solid var(--app-border); border-radius: 16px; padding: 14px; min-height: 116px; }
    .dashboard-kpi-top { display: inline-flex; align-items: center; gap: 8px; color: var(--app-text-muted); font-size: .9rem; }
    .dashboard-kpi-value { margin-top: 16px; font-size: 1.9rem; font-weight: 700; color: var(--app-text-strong); }
    .dashboard-kpi-note { margin-top: 8px; color: var(--app-text-label); font-size: .84rem; line-height: 1.45; }
    .insight-shell { margin-top: 18px; padding: 18px; border: 1px solid var(--app-border); border-radius: 20px; background: var(--app-overlay-bg); }
    .insight-shell-header { display: flex; justify-content: space-between; gap: 18px; align-items: flex-start; margin-bottom: 14px; }
    .insight-shell-title { margin-top: 10px; font-size: 1.08rem; font-weight: 700; color: var(--app-text-strong); }
    .insight-shell-copy { max-width: 420px; color: var(--app-text-label); line-height: 1.5; font-size: .9rem; }
    .insight-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
    .insight-card { background: var(--app-panel-bg); border: 1px solid var(--app-border); border-radius: 18px; padding: 16px; min-height: 122px; }
    .insight-card-focus { border-left: 3px solid rgba(245, 158, 11, 0.72); }
    .insight-card-status { border-left: 3px solid rgba(96, 165, 250, 0.72); }
    .insight-title { display: inline-flex; align-items: center; gap: 8px; color: var(--app-text-strong); font-size: .92rem; font-weight: 700; }
    .insight-body { margin-top: 12px; color: var(--app-text-muted); line-height: 1.55; }
    @media (max-width: 960px) {
      .detail-grid, .insight-grid, .dashboard-kpi-grid, .metric-grid, .metric-strip { grid-template-columns: repeat(1, minmax(0, 1fr)); }
      .hero-row, .dashboard-title-row { flex-direction: column; }
      .reference-summary { flex-direction: column; align-items: flex-start; }
      .review-flow-panel { border-left: none; padding-left: 0; }
      .insight-shell-header { flex-direction: column; }
    }
    @media (min-width: 961px) {
      .queue-filter-grid { grid-template-columns: repeat(1, minmax(0, 1fr)); }
    }
    """

    theme = gr.themes.Soft(
        primary_hue="indigo",
        neutral_hue="slate",
        text_size="lg",
        spacing_size="lg",
        font=[gr.themes.GoogleFont("Inter"), "ui-sans-serif", "system-ui", "sans-serif"],
    )

    with gr.Blocks(title="VAT Spreadsheet Review Centre") as demo:
        with gr.Column(elem_classes="workspace-root"):
            heading = "# VAT Spreadsheet Review Centre"
            if app_mode == APP_MODE_PUBLIC_DEMO:
                heading += "\n\n_Limited public demo profile_"
            gr.Markdown(heading)

            with gr.Tabs():
                with gr.TabItem("Welcome"):
                    gr.Markdown(
                        (
                            "This local-first prototype helps you analyse VAT-related spreadsheets, explain why records were flagged, and record a human review trail.\n\n"
                            "**Architecture**\n"
                            "- Same Python core is reused by source run, local GUI, Docker, Windows package, and the web demo shell.\n"
                            "- The browser GUI is the current main interaction entry.\n"
                            "- Deployment shells stay thin so evaluation logic can continue changing separately.\n\n"
                            "**Workflow**\n"
                            "1. Upload a CSV or Excel file.\n"
                            "2. Run the analysis.\n"
                            "3. Review flagged findings in the dual-pane Review Centre.\n"
                            "4. Save decisions and export the review artefacts.\n"
                            + (
                                f"\n**Public Demo Boundary**\n- {PUBLIC_DEMO_PRIVACY_NOTE}\n"
                                if app_mode == APP_MODE_PUBLIC_DEMO
                                else "\n**Current Default Shape**\n- Run locally from source or a local package for demonstrations and dissertation work.\n"
                            )
                        )
                    )

                with gr.TabItem("Upload and Run"):
                    with gr.Column(elem_classes="panel"):
                        uploaded_file = gr.File(label="Spreadsheet file", file_types=[".csv", ".xlsx", ".xls"], type="filepath")
                        run_button = gr.Button("Run analysis", variant="primary")
                        results_overview_output = gr.Markdown("*Analysis results will appear here.*")
                        automatic_explanation_output = gr.Markdown()

                with gr.TabItem("Review Centre"):
                    with gr.Row(elem_classes="review-shell"):
                        with gr.Column(scale=3, elem_classes="queue-panel"):
                            with gr.Column(elem_classes="panel"):
                                gr.HTML("""
                                <div class="module-intro">
                                  <div class="eyebrow">Controls</div>
                                  <div class="module-intro-title">Review Controls</div>
                                </div>
                                """)
                                review_summary_html = gr.HTML(_build_summary_html(pd.DataFrame(), pd.DataFrame()))
                                with gr.Group(elem_classes="queue-filter-grid"):
                                    status_filter_input = gr.Dropdown(label="Review state filter", choices=STATUS_FILTER_OPTIONS, value="All review states")
                                    type_filter_input = gr.Dropdown(label="Issue type", choices=list(TYPE_FILTER_MAP.keys()), value="All finding types")
                                    search_text_input = gr.Textbox(label="Search review list", placeholder="Search by issue id, row number, or summary", lines=1, max_lines=1)
                                filter_hint_html = gr.HTML(_build_filter_hint_html(pd.DataFrame(), pd.DataFrame(), ""))
                        with gr.Column(scale=9, elem_classes="review-flow-panel"):
                            with gr.Column(elem_classes=["panel", "active-finding-panel"]):
                                gr.HTML("""
                                <div class="module-intro">
                                  <div class="eyebrow">Selection</div>
                                  <div class="module-intro-title">Active Issue</div>
                                </div>
                                """)
                                issue_selector = gr.Dropdown(label="Open issue", choices=[], value=None)
                                header_html = gr.HTML(_build_header_html(None, 0, 0), visible=False)
                            row_preview_html = gr.HTML(_build_row_preview_html(None, None))
                            with gr.Column(elem_classes=["panel", "decision-panel"]):
                                decision_input = gr.Radio(label="Review decision", choices=REVIEW_DECISION_OPTIONS, value="pending")
                                evidence_checked_input = gr.Textbox(
                                    label="Evidence checked",
                                    placeholder="Example: Invoice INV-2045, source spreadsheet export, receipt image",
                                    lines=2,
                                )
                                review_notes_input = gr.Textbox(
                                    label="Reviewer note",
                                    placeholder="Explain the decision, any correction made, or why the issue was accepted, excluded, or escalated.",
                                    lines=4,
                                )
                                save_review_button = gr.Button("Save review decision", variant="primary")
                                review_save_feedback = gr.Markdown("")
                            with gr.Accordion("Current record context", open=False, elem_classes="secondary-accordion"):
                                record_context_html = gr.HTML(_build_record_context_html(None))
                            with gr.Accordion("Issue explanation and review guidance", open=False, elem_classes="secondary-accordion"):
                                explanation_html = gr.HTML(_build_explanation_html(None))
                            with gr.Accordion("Visible review list", open=False, elem_classes="secondary-accordion"):
                                review_queue_preview = gr.Dataframe(label="Visible queue", show_label=False, interactive=False, max_height=520, wrap=False)
                            with gr.Accordion("Saved review history", open=False, elem_classes="history-accordion"):
                                review_history_preview = gr.Dataframe(label="Saved review history", show_label=False, interactive=False, max_height=260, wrap=False)

                with gr.TabItem("Visual Insights"):
                    dashboard_summary_html = gr.HTML(_build_visual_summary_html(pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), None))
                    dashboard_highlights_html = gr.HTML(_build_visual_highlights_html(pd.DataFrame(), pd.DataFrame(), pd.DataFrame()))
                    with gr.Row():
                        issue_type_counts_plot = gr.Plot(label="Findings by type")
                        review_status_plot = gr.Plot(label="Review status")
                    with gr.Row():
                        field_focus_plot = gr.Plot(label="Fields attracting review")
                        anomaly_amount_plot = gr.Plot(label="Top unusual amounts")
                    priority_findings_preview = gr.Dataframe(label="Priority findings", interactive=False, max_height=360, wrap=True)
                    anomaly_note_output = gr.Markdown()

                with gr.TabItem("Smart Assistant"):
                    ai_suggestions_output = gr.Markdown(
                        "Run an analysis first to see AI suggestions." if ai_enabled else PUBLIC_DEMO_AI_DISABLED_MESSAGE
                    )
                    if app_mode == APP_MODE_PUBLIC_DEMO:
                        gr.Markdown(PUBLIC_DEMO_PRIVACY_NOTE)
                    with gr.Accordion("Configure AI settings" if ai_enabled else "AI settings (disabled in this profile)", open=False):
                        advanced_provider_input = gr.Dropdown(label="Provider", choices=get_provider_choices(), value=DEFAULT_PROVIDER)
                        advanced_model_input = gr.Dropdown(label="Model", choices=get_standard_model_options(DEFAULT_PROVIDER), value=get_default_model(DEFAULT_PROVIDER))
                        advanced_api_key_input = gr.Textbox(label="API key", type="password", placeholder="Enter your provider API key")
                        advanced_custom_model_input = gr.Textbox(label="Custom model", visible=False)
                        advanced_base_url_input = gr.Textbox(label="Base URL", visible=False)
                        editable_explanation_prompt_input = gr.Textbox(label="Base explanation prompt", value=DEFAULT_EDITABLE_EXPLANATION_PROMPT, lines=4)
                        advanced_instructions_input = gr.Textbox(label="Extra instructions", placeholder="Example: use simple language and bullet points.", lines=2)
                        advanced_generate_button = gr.Button("Regenerate AI advice", variant="secondary")

                with gr.TabItem("Downloads"):
                    with gr.Row():
                        issue_report_file = gr.File(label="Issue report", interactive=False)
                        review_log_file = gr.File(label="Review log", interactive=False)
                        review_history_file = gr.File(label="Review history", interactive=False)
                        review_summary_file = gr.File(label="Review summary", interactive=False)
                        dataset_snapshot_file = gr.File(label="Dataset snapshot", interactive=False)
                        prepared_canonical_records_file = gr.File(label="Prepared canonical records", interactive=False)
                    issue_report_preview = gr.Dataframe(label="Explanation preview", interactive=False, max_height=420, wrap=True)
                    review_summary_preview = gr.Dataframe(label="Review summary preview", interactive=False, max_height=180, wrap=True)

        ai_snapshot_state = gr.State(value=None)
        review_queue_state = gr.State(value=[])
        review_history_state = gr.State(value=[])
        review_paths_state = gr.State(value={})

        run_button.click(
            fn=run_analysis,
            inputs=[uploaded_file, editable_explanation_prompt_input, advanced_instructions_input],
            outputs=[
                results_overview_output,
                automatic_explanation_output,
                ai_suggestions_output,
                ai_snapshot_state,
                dashboard_summary_html,
                dashboard_highlights_html,
                issue_type_counts_plot,
                review_status_plot,
                field_focus_plot,
                anomaly_amount_plot,
                priority_findings_preview,
                anomaly_note_output,
                issue_report_file,
                review_log_file,
                review_history_file,
                review_summary_file,
                dataset_snapshot_file,
                prepared_canonical_records_file,
                issue_report_preview,
                review_summary_preview,
                status_filter_input,
                type_filter_input,
                search_text_input,
                issue_selector,
                filter_hint_html,
                review_queue_preview,
                header_html,
                row_preview_html,
                record_context_html,
                explanation_html,
                decision_input,
                evidence_checked_input,
                review_notes_input,
                review_summary_html,
                review_history_preview,
                review_queue_state,
                review_history_state,
                review_paths_state,
            ],
        )

        for trigger in [status_filter_input.change, type_filter_input.change, search_text_input.change, issue_selector.change]:
            trigger(
                fn=refresh_review_workspace,
                inputs=[issue_selector, status_filter_input, type_filter_input, search_text_input, review_queue_state, review_history_state, review_paths_state],
                outputs=[
                    issue_selector,
                    filter_hint_html,
                    review_queue_preview,
                    header_html,
                    row_preview_html,
                    record_context_html,
                    explanation_html,
                    decision_input,
                    evidence_checked_input,
                    review_notes_input,
                    review_summary_html,
                    review_history_preview,
                ],
            )

        save_review_button.click(
            fn=save_review_decision,
            inputs=[issue_selector, decision_input, evidence_checked_input, review_notes_input, status_filter_input, type_filter_input, search_text_input, review_queue_state, review_paths_state],
            outputs=[
                review_save_feedback,
                review_log_file,
                review_history_file,
                review_summary_file,
                dashboard_summary_html,
                dashboard_highlights_html,
                issue_type_counts_plot,
                review_status_plot,
                field_focus_plot,
                anomaly_amount_plot,
                priority_findings_preview,
                anomaly_note_output,
                issue_selector,
                filter_hint_html,
                review_queue_preview,
                header_html,
                row_preview_html,
                record_context_html,
                explanation_html,
                decision_input,
                evidence_checked_input,
                review_notes_input,
                review_summary_html,
                review_history_preview,
                review_queue_state,
                review_history_state,
                review_summary_preview,
            ],
        )

        advanced_provider_input.change(
            fn=update_provider_configuration,
            inputs=[advanced_provider_input],
            outputs=[advanced_model_input, advanced_custom_model_input, advanced_base_url_input],
        )

        advanced_generate_button.click(
            fn=request_enhanced_ai_suggestions,
            inputs=[
                ai_snapshot_state,
                advanced_provider_input,
                advanced_model_input,
                advanced_custom_model_input,
                advanced_base_url_input,
                advanced_api_key_input,
                editable_explanation_prompt_input,
                advanced_instructions_input,
            ],
            outputs=[ai_suggestions_output],
        )

    setattr(demo, "_vat_launch_css", custom_css)
    setattr(demo, "_vat_launch_theme", theme)
    return demo


def build_launch_options(argv: list[str] | None = None) -> GuiLaunchOptions:
    """Build thin runtime settings for local, Docker, and public-demo launches."""
    env_mode = _normalise_app_mode(os.getenv("VAT_GUI_MODE"))

    parser = argparse.ArgumentParser(description="Launch the VAT Spreadsheet browser GUI.")
    parser.add_argument(
        "--mode",
        choices=["local", "public-demo"],
        default=env_mode.replace("_", "-"),
        help="Launch profile: local or limited public-demo.",
    )
    parser.add_argument(
        "--host",
        default=os.getenv("VAT_GUI_HOST"),
        help="Server host. Defaults to 127.0.0.1 locally and 0.0.0.0 for public-demo when unset.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=_parse_int(os.getenv("VAT_GUI_PORT"), DEFAULT_GUI_PORT),
        help="Server port for the Gradio UI.",
    )
    parser.add_argument(
        "--root-path",
        default=os.getenv("VAT_GUI_ROOT_PATH"),
        help="Optional reverse-proxy root path.",
    )
    parser.add_argument(
        "--max-file-size",
        default=os.getenv("VAT_GUI_MAX_FILE_SIZE"),
        help="Optional Gradio upload limit such as 10mb.",
    )

    browser_group = parser.add_mutually_exclusive_group()
    browser_group.add_argument("--browser", dest="open_browser", action="store_true", help="Open a browser automatically.")
    browser_group.add_argument("--no-browser", dest="open_browser", action="store_false", help="Do not open a browser automatically.")
    parser.set_defaults(open_browser=None)

    share_group = parser.add_mutually_exclusive_group()
    share_group.add_argument("--share", dest="share", action="store_true", help="Enable Gradio share mode.")
    share_group.add_argument("--no-share", dest="share", action="store_false", help="Disable Gradio share mode.")
    parser.set_defaults(share=None)

    cors_group = parser.add_mutually_exclusive_group()
    cors_group.add_argument("--strict-cors", dest="strict_cors", action="store_true", help="Keep strict CORS enabled.")
    cors_group.add_argument("--no-strict-cors", dest="strict_cors", action="store_false", help="Disable strict CORS when a proxy needs it.")
    parser.set_defaults(strict_cors=None)

    ai_group = parser.add_mutually_exclusive_group()
    ai_group.add_argument("--enable-ai", dest="enable_ai_assistant", action="store_true", help="Enable optional AI controls.")
    ai_group.add_argument("--disable-ai", dest="enable_ai_assistant", action="store_false", help="Disable optional AI controls.")
    parser.set_defaults(enable_ai_assistant=None)

    args = parser.parse_args(argv)
    app_mode = _normalise_app_mode(args.mode)

    default_host = DEFAULT_GUI_HOST if app_mode == APP_MODE_LOCAL else "0.0.0.0"
    default_open_browser = app_mode == APP_MODE_LOCAL
    default_max_file_size = None if app_mode == APP_MODE_LOCAL else DEFAULT_PUBLIC_DEMO_MAX_FILE_SIZE
    default_enable_ai_assistant = _default_enable_ai_assistant(app_mode)

    return GuiLaunchOptions(
        host=args.host or default_host,
        port=args.port,
        open_browser=_parse_bool(os.getenv("VAT_GUI_OPEN_BROWSER"), default_open_browser) if args.open_browser is None else args.open_browser,
        share=_parse_bool(os.getenv("VAT_GUI_SHARE"), False) if args.share is None else args.share,
        root_path=args.root_path,
        max_file_size=args.max_file_size or default_max_file_size,
        strict_cors=_parse_bool(os.getenv("VAT_GUI_STRICT_CORS"), True) if args.strict_cors is None else args.strict_cors,
        app_mode=app_mode,
        enable_ai_assistant=(
            _parse_bool(os.getenv("VAT_GUI_ENABLE_AI"), default_enable_ai_assistant)
            if args.enable_ai_assistant is None
            else args.enable_ai_assistant
        ),
    )


def launch_interface(options: GuiLaunchOptions):
    """Launch the existing GUI shell with deployment-specific runtime settings."""
    global CURRENT_GUI_OPTIONS

    CURRENT_GUI_OPTIONS = options
    allowed_paths = [str(RUNTIME_ROOT), str(UI_OUTPUT_ROOT)]

    LOGGER.info(
        "Launching GUI mode=%s host=%s port=%s ai_enabled=%s",
        options.app_mode,
        options.host,
        options.port,
        options.enable_ai_assistant,
    )
    demo = build_interface()
    return demo.launch(
        inbrowser=options.open_browser,
        share=options.share,
        server_name=options.host,
        server_port=options.port,
        root_path=options.root_path,
        max_file_size=options.max_file_size,
        strict_cors=options.strict_cors,
        allowed_paths=allowed_paths,
        show_error=True,
        css=getattr(demo, "_vat_launch_css", None),
        theme=getattr(demo, "_vat_launch_theme", None),
    )


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for the shared browser GUI shell."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    launch_interface(build_launch_options(argv))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
