from __future__ import annotations

from dataclasses import dataclass

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
FINDINGS_SUMMARY_PREVIEW_COLUMNS = ["section", "metric", "value", "note"]
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

