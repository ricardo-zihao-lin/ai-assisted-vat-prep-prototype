"""Local Gradio interface for the VAT spreadsheet preparation prototype."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import gradio as gr
import pandas as pd

from ai.provider_catalog import (
    DEFAULT_PROVIDER,
    get_default_model,
    get_provider_choices,
    get_standard_model_options,
)
from ai.prompts import DEFAULT_EDITABLE_EXPLANATION_PROMPT
from ai.snapshot_builder import build_issue_snapshot
from ai.suggestions_service import generate_advanced_ai_suggestions, try_generate_default_ai_suggestions
from explanation.local_explainer import generate_automatic_explanation
from export.exporter import ISSUE_REPORT_COLUMNS, export_findings_summary, export_review_summary
from pipeline import STATUS_UNSUPPORTED_INPUT, run_pipeline
from review.review_manager import (
    REVIEW_DECISION_OPTIONS,
    REVIEW_HISTORY_COLUMNS,
    REVIEW_LOG_COLUMNS,
    build_review_queue,
    persist_review_outputs,
)
from ui import rendering as ui_rendering
from ui.assets import build_custom_css, build_heading, build_theme, build_welcome_markdown
from ui.constants import (
    APP_MODE_LOCAL,
    APP_MODE_PUBLIC_DEMO,
    DEFAULT_GUI_HOST,
    DEFAULT_GUI_PORT,
    DEFAULT_PUBLIC_DEMO_MAX_FILE_SIZE,
    GuiLaunchOptions,
    PUBLIC_DEMO_AI_DISABLED_MESSAGE,
    PUBLIC_DEMO_PRIVACY_NOTE,
    STATUS_FILTER_OPTIONS,
    TYPE_FILTER_MAP,
)
from ui.io import read_output_csv

LOGGER = logging.getLogger(__name__)
CURRENT_GUI_OPTIONS: GuiLaunchOptions | None = None


def _get_runtime_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


RUNTIME_ROOT = _get_runtime_root()
UI_OUTPUT_ROOT = RUNTIME_ROOT / "output" / "ui_runs"


def _normalise_app_mode(value: str | None) -> str:
    normalised = (value or APP_MODE_LOCAL).strip().lower().replace("-", "_")
    if normalised not in {APP_MODE_LOCAL, APP_MODE_PUBLIC_DEMO}:
        raise ValueError(f"Unsupported GUI mode: {value}")
    return normalised


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    normalised = value.strip().lower()
    if normalised in {"1", "true", "yes", "on"}:
        return True
    if normalised in {"0", "false", "no", "off"}:
        return False
    return default


def _parse_int(value: str | None, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _default_enable_ai_assistant(app_mode: str | None = None) -> bool:
    resolved_mode = app_mode or _normalise_app_mode(os.getenv("VAT_GUI_MODE"))
    return resolved_mode != APP_MODE_PUBLIC_DEMO


def _is_ai_assistant_enabled(override: bool | None = None) -> bool:
    if override is not None:
        return override
    if CURRENT_GUI_OPTIONS is not None:
        return CURRENT_GUI_OPTIONS.enable_ai_assistant
    return _parse_bool(os.getenv("VAT_GUI_ENABLE_AI"), _default_enable_ai_assistant())


def _build_run_output_dir() -> Path:
    run_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}"
    output_dir = UI_OUTPUT_ROOT / run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


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
    issue_report_df = read_output_csv(result.issue_report_path, default_columns=ISSUE_REPORT_COLUMNS)
    review_log_df = read_output_csv(result.review_log_path, default_columns=REVIEW_LOG_COLUMNS)
    review_history_df = read_output_csv(result.review_history_path, default_columns=REVIEW_HISTORY_COLUMNS)
    review_summary_df = read_output_csv(result.review_summary_path)
    findings_summary_df = read_output_csv(result.findings_summary_path)
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
        "findings_summary_path": result.findings_summary_path,
        "prepared_records_path": result.prepared_canonical_records_path,
        "source_filename": input_path.name,
    }
    review_workspace = ui_rendering._build_review_workspace(
        review_queue_df,
        review_history_df,
        review_paths,
        "All review states",
        "All finding types",
        "",
        None,
    )
    visual_bundle = ui_rendering._build_visual_insights_bundle(
        issue_report_df,
        review_queue_df,
        review_history_df,
        result.prepared_canonical_records_path,
        result.review_summary_path,
    )

    return (
        ui_rendering._format_results_overview(
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
        result.findings_summary_path,
        result.issue_report_path,
        result.review_log_path,
        result.review_history_path,
        result.review_summary_path,
        result.dataset_snapshot_path,
        result.prepared_canonical_records_path,
        ui_rendering._build_downloads_plain_language_html(issue_report_df, review_summary_df),
        "All review states",
        "All finding types",
        "",
        *review_workspace,
        ui_rendering._queue_to_records(review_queue_df),
        ui_rendering._queue_to_records(review_history_df),
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
    review_queue_df = ui_rendering._records_to_queue(review_queue_records)
    review_history_df = ui_rendering._records_to_queue(review_history_records)
    return ui_rendering._build_review_workspace(
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

    review_queue_df = ui_rendering._records_to_queue(review_queue_records)
    review_queue_df = ui_rendering._ensure_issue_id_column(review_queue_df)
    if review_queue_df.empty:
        raise gr.Error("There are no issues available for review in the current run.")

    issue_id = ui_rendering._extract_issue_id(selected_issue)
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
    issue_report_df = read_output_csv(review_paths["issue_report_path"], default_columns=ISSUE_REPORT_COLUMNS)
    prepared_records_df = read_output_csv(review_paths.get("prepared_records_path"))
    if review_paths.get("review_summary_path"):
        export_review_summary(
            issue_report_df,
            prepared_records_df,
            current_log_df,
            review_paths["review_summary_path"],
            dataset_id=f"DATASET-{Path(review_paths['review_summary_path']).resolve().parent.name}",
            source_filename=review_paths.get("source_filename"),
        )
    if review_paths.get("findings_summary_path"):
        export_findings_summary(
            issue_report_df,
            prepared_records_df,
            current_log_df,
            review_paths["findings_summary_path"],
            source_filename=review_paths.get("source_filename"),
        )
    review_summary_df = read_output_csv(review_paths.get("review_summary_path"))
    refreshed_queue_df = build_review_queue(issue_report_df, current_log_df)
    review_workspace = ui_rendering._build_review_workspace(
        refreshed_queue_df,
        review_history_df,
        review_paths,
        status_filter,
        type_filter,
        search_text,
        selected_issue,
    )
    visual_bundle = ui_rendering._build_visual_insights_bundle(
        issue_report_df,
        refreshed_queue_df,
        review_history_df,
        review_paths.get("prepared_records_path"),
        review_paths.get("review_summary_path"),
    )

    return (
        "Review decision, notes, and evidence checked were saved to the current review log and appended to review history.",
        review_paths["findings_summary_path"],
        review_paths["review_log_path"],
        review_paths["review_history_path"],
        review_paths["review_summary_path"],
        *visual_bundle,
        *review_workspace,
        ui_rendering._queue_to_records(refreshed_queue_df),
        ui_rendering._queue_to_records(review_history_df),
        ui_rendering._build_downloads_plain_language_html(issue_report_df, review_summary_df),
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
    custom_css = build_custom_css()
    theme = build_theme()

    with gr.Blocks(title="VAT Spreadsheet Review Centre") as demo:
        with gr.Column(elem_classes="workspace-root"):
            gr.Markdown(build_heading(app_mode))

            with gr.Tabs():
                with gr.TabItem("Welcome"):
                    gr.Markdown(build_welcome_markdown(app_mode))

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
                                gr.HTML(
                                    """
                                <div class="module-intro">
                                  <div class="eyebrow">Controls</div>
                                  <div class="module-intro-title">Review Controls</div>
                                </div>
                                """
                                )
                                review_summary_html = gr.HTML(ui_rendering._build_summary_html(pd.DataFrame(), pd.DataFrame()))
                                with gr.Group(elem_classes="queue-filter-grid"):
                                    status_filter_input = gr.Dropdown(label="Review state filter", choices=STATUS_FILTER_OPTIONS, value="All review states")
                                    type_filter_input = gr.Dropdown(label="Issue type", choices=list(TYPE_FILTER_MAP.keys()), value="All finding types")
                                    search_text_input = gr.Textbox(label="Search review list", placeholder="Search by issue id, row number, or summary", lines=1, max_lines=1)
                                filter_hint_html = gr.HTML(ui_rendering._build_filter_hint_html(pd.DataFrame(), pd.DataFrame(), ""))
                        with gr.Column(scale=9, elem_classes="review-flow-panel"):
                            with gr.Column(elem_classes=["panel", "active-finding-panel"]):
                                gr.HTML(
                                    """
                                <div class="module-intro">
                                  <div class="eyebrow">Selection</div>
                                  <div class="module-intro-title">Active Issue</div>
                                </div>
                                """
                                )
                                issue_selector = gr.Dropdown(label="Open issue", choices=[], value=None)
                                header_html = gr.HTML(ui_rendering._build_header_html(None, 0, 0), visible=False)
                            row_preview_html = gr.HTML(ui_rendering._build_row_preview_html(None, None))
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
                                record_context_html = gr.HTML(ui_rendering._build_record_context_html(None))
                            with gr.Accordion("Issue explanation and review guidance", open=False, elem_classes="secondary-accordion"):
                                explanation_html = gr.HTML(ui_rendering._build_explanation_html(None))
                            with gr.Accordion("Visible review list", open=False, elem_classes="secondary-accordion"):
                                review_queue_preview = gr.Dataframe(label="Visible queue", show_label=False, interactive=False, max_height=520, wrap=False)
                            with gr.Accordion("Saved review history", open=False, elem_classes="history-accordion"):
                                review_history_preview = gr.Dataframe(label="Saved review history", show_label=False, interactive=False, max_height=260, wrap=False)

                with gr.TabItem("Visual Insights"):
                    dashboard_summary_html = gr.HTML(ui_rendering._build_visual_summary_html(pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), None))
                    dashboard_highlights_html = gr.HTML(ui_rendering._build_visual_highlights_html(pd.DataFrame(), pd.DataFrame(), pd.DataFrame()))
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
                    gr.HTML(
                        """
                        <div class="downloads-shell">
                          <div class="downloads-hero">
                            <div class="downloads-kicker">Downloads</div>
                            <div class="downloads-title">Choose the export that matches your next step</div>
                            <div class="downloads-copy">
                              Start with the summary if you need the headline result, or open the issue details report if you are following up flagged rows.
                              Audit and raw-data exports are still available below for traceability and downstream processing.
                            </div>
                          </div>
                        </div>
                        """
                    )
                    gr.Markdown("### Recommended downloads")
                    with gr.Row(elem_classes=["downloads-grid"]):
                        with gr.Column(elem_classes=["download-card", "download-card-primary"]):
                            gr.HTML(
                                """
                                <div class="download-card-copy">
                                  <div class="download-card-title">Summary report</div>
                                  <div class="download-card-text">
                                    Best for a quick overview of issues found, unresolved risk, and review completion.
                                  </div>
                                </div>
                                """
                            )
                            review_summary_file = gr.File(label="Download summary report", interactive=False)
                        with gr.Column(elem_classes=["download-card"]):
                            gr.HTML(
                                """
                                <div class="download-card-copy">
                                  <div class="download-card-title">Issue details report</div>
                                  <div class="download-card-text">
                                    Best for investigating flagged rows, understanding why they matter, and sharing next actions.
                                  </div>
                                </div>
                                """
                            )
                            issue_report_file = gr.File(label="Download issue details report", interactive=False)
                    with gr.Accordion("Advanced exports", open=False, elem_classes="secondary-accordion downloads-accordion"):
                        gr.HTML(
                            """
                            <div class="downloads-section-copy">
                              These exports support audit traceability, downstream processing, and technical review history.
                            </div>
                            """
                        )
                        with gr.Row(elem_classes=["downloads-grid"]):
                            with gr.Column(elem_classes=["download-card"]):
                                gr.HTML(
                                    """
                                    <div class="download-card-copy">
                                      <div class="download-card-title">Standardized records</div>
                                      <div class="download-card-text">
                                        Cleaned and prepared records for downstream analysis or handoff.
                                      </div>
                                    </div>
                                    """
                                )
                                prepared_canonical_records_file = gr.File(label="Download standardized records", interactive=False)
                            with gr.Column(elem_classes=["download-card"]):
                                gr.HTML(
                                    """
                                    <div class="download-card-copy">
                                      <div class="download-card-title">Source data snapshot</div>
                                      <div class="download-card-text">
                                        A saved copy of the processed source dataset for audit traceability.
                                      </div>
                                    </div>
                                    """
                                )
                                dataset_snapshot_file = gr.File(label="Download source data snapshot", interactive=False)
                        with gr.Row(elem_classes=["downloads-grid"]):
                            with gr.Column(elem_classes=["download-card"]):
                                gr.HTML(
                                    """
                                    <div class="download-card-copy">
                                      <div class="download-card-title">Findings summary table</div>
                                      <div class="download-card-text">
                                        Compact metrics and section totals for lightweight reporting.
                                      </div>
                                    </div>
                                    """
                                )
                                findings_summary_file = gr.File(label="Download findings summary table", interactive=False)
                            with gr.Column(elem_classes=["download-card"]):
                                gr.HTML(
                                    """
                                    <div class="download-card-copy">
                                      <div class="download-card-title">Review activity history</div>
                                      <div class="download-card-text">
                                        Reviewer decisions saved over time, useful when you need an audit trail of actions taken.
                                      </div>
                                    </div>
                                    """
                                )
                                review_history_file = gr.File(label="Download review activity history", interactive=False)
                        with gr.Row(elem_classes=["downloads-grid"]):
                            with gr.Column(elem_classes=["download-card"]):
                                gr.HTML(
                                    """
                                    <div class="download-card-copy">
                                      <div class="download-card-title">Validation log</div>
                                      <div class="download-card-text">
                                        Technical run output for troubleshooting or detailed validation review.
                                      </div>
                                    </div>
                                    """
                                )
                                review_log_file = gr.File(label="Download validation log", interactive=False)
                    with gr.Accordion("Preview before downloading", open=True, elem_classes="secondary-accordion downloads-accordion"):
                        downloads_plain_language_html = gr.HTML(
                            ui_rendering._build_downloads_plain_language_html(pd.DataFrame(), pd.DataFrame())
                        )

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
                findings_summary_file,
                issue_report_file,
                review_log_file,
                review_history_file,
                review_summary_file,
                dataset_snapshot_file,
                prepared_canonical_records_file,
                downloads_plain_language_html,
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
                findings_summary_file,
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
                downloads_plain_language_html,
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
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    launch_interface(build_launch_options(argv))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
