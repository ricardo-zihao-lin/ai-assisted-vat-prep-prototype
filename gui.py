"""Local Gradio interface for the VAT spreadsheet preparation prototype."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import gradio as gr
import pandas as pd

from pipeline import run_pipeline

LOGGER = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parent
UI_OUTPUT_ROOT = BASE_DIR / "output" / "ui_runs"
ISSUE_PREVIEW_ROWS = 50


def _build_run_output_dir() -> Path:
    """Create a distinct per-run output directory for the local UI."""
    run_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}"
    output_dir = UI_OUTPUT_ROOT / run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def _format_summary(
    input_name: str,
    rows_loaded: int,
    issues_found: int,
    anomalies_flagged: int,
    status: str,
    stop_reason: str | None,
) -> str:
    """Return a concise text summary for display in the UI."""
    summary_lines = [
        f"Input file: {input_name}",
        f"Rows loaded: {rows_loaded}",
        f"Issues found: {issues_found}",
        f"Anomalies flagged: {anomalies_flagged}",
        f"Status: {status}",
    ]
    if stop_reason:
        summary_lines.append(f"Stop reason: {stop_reason}")
    return "\n".join(summary_lines)


def run_analysis(uploaded_file) -> tuple[str, pd.DataFrame, str, str, str]:
    """Execute the existing pipeline for an uploaded file and prepare UI outputs."""
    if uploaded_file is None:
        raise gr.Error("Please upload a CSV or Excel file before running the analysis.")

    input_path = Path(uploaded_file)
    output_dir = _build_run_output_dir()
    LOGGER.info("Running local UI analysis for %s", input_path)

    result = run_pipeline(str(input_path), str(output_dir))
    issue_report_preview = pd.read_csv(result.issue_report_path).head(ISSUE_PREVIEW_ROWS)
    summary = _format_summary(
        input_name=input_path.name,
        rows_loaded=result.rows_loaded,
        issues_found=result.issues_found,
        anomalies_flagged=result.anomalies_flagged,
        status=result.status,
        stop_reason=result.stop_reason,
    )

    return (
        summary,
        issue_report_preview,
        result.dataset_snapshot_path,
        result.issue_report_path,
        result.review_log_path,
    )


def build_interface() -> gr.Blocks:
    """Construct the local browser-based research prototype interface."""
    with gr.Blocks(title="VAT Spreadsheet Preparation Prototype") as demo:
        gr.Markdown(
            """
            # VAT Spreadsheet Preparation Prototype
            Upload a local CSV or Excel file and run the existing review-oriented analysis pipeline.
            """
        )

        with gr.Row():
            uploaded_file = gr.File(
                label="Spreadsheet File",
                file_types=[".csv", ".xlsx", ".xls"],
                type="filepath",
            )
            run_button = gr.Button("Run Analysis", variant="primary")

        summary_output = gr.Textbox(
            label="Run Summary",
            lines=6,
            interactive=False,
        )
        issue_report_preview = gr.Dataframe(
            label="Issue Report Preview",
            interactive=False,
        )

        with gr.Row():
            dataset_snapshot_file = gr.File(label="Download Dataset Snapshot", interactive=False)
            issue_report_file = gr.File(label="Download Issue Report", interactive=False)
            review_log_file = gr.File(label="Download Review Log", interactive=False)

        run_button.click(
            fn=run_analysis,
            inputs=uploaded_file,
            outputs=[
                summary_output,
                issue_report_preview,
                dataset_snapshot_file,
                issue_report_file,
                review_log_file,
            ],
        )

    return demo


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    build_interface().launch()
