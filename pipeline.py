"""High-level orchestration for the VAT spreadsheet preparation prototype.

This module keeps the end-to-end demo workflow reusable while preserving the
existing internal module boundaries. It coordinates ingestion, deterministic
validation, IQR-based anomaly flagging, review, and traceable CSV exports
without changing the underlying spreadsheet data.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from anomaly.anomaly_detector import detect_anomalies
from export.exporter import export_outputs
from ingestion.input_preparation import PREPARATION_STATUS_UNSUPPORTED, prepare_input_dataframe
from ingestion.loader import load_spreadsheet
from review.review_manager import EMPTY_REVIEW_HISTORY, EMPTY_REVIEW_LOG
from validation.validator import validate_vat_data

LOGGER = logging.getLogger(__name__)

STATUS_COMPLETED = "completed"
STATUS_STOPPED_AFTER_REPORTING = "stopped_after_reporting"
STATUS_UNSUPPORTED_INPUT = "unsupported_input"
STOP_REASON_REVIEW_REQUIRED = "review_required"
STOP_REASON_UNSUPPORTED_INPUT = "unsupported_input"


@dataclass(frozen=True)
class RunResult:
    """Structured summary of a prototype pipeline run."""

    input_file: str
    rows_loaded: int
    issues_found: int
    anomalies_flagged: int
    status: str
    stop_reason: str | None
    preparation_status: str
    preparation_message: str
    missing_required_fields: tuple[str, ...]
    dataset_snapshot_path: str | None
    prepared_canonical_records_path: str | None
    issue_report_path: str | None
    review_log_path: str | None
    review_history_path: str | None


def run_pipeline(input_path: str, output_dir: str) -> RunResult:
    """Run the research prototype pipeline and return a structured summary.

    Parameters
    ----------
    input_path : str
        Source spreadsheet path for the VAT records dataset.
    output_dir : str
        Directory where traceable CSV artefacts should be written.
    """
    resolved_input_path = Path(input_path)
    resolved_output_dir = Path(output_dir)

    LOGGER.info("Starting VAT spreadsheet preparation pipeline for %s", resolved_input_path)
    raw_dataframe = load_spreadsheet(resolved_input_path)
    preparation_result = prepare_input_dataframe(raw_dataframe)

    if preparation_result.status == PREPARATION_STATUS_UNSUPPORTED or preparation_result.prepared_dataframe is None:
        LOGGER.warning(
            "Input preparation failed for %s because required fields were missing: %s",
            resolved_input_path,
            preparation_result.missing_required_fields,
        )
        return RunResult(
            input_file=str(resolved_input_path),
            rows_loaded=len(raw_dataframe),
            issues_found=0,
            anomalies_flagged=0,
            status=STATUS_UNSUPPORTED_INPUT,
            stop_reason=STOP_REASON_UNSUPPORTED_INPUT,
            preparation_status=preparation_result.status,
            preparation_message=preparation_result.message,
            missing_required_fields=preparation_result.missing_required_fields,
            dataset_snapshot_path=None,
            prepared_canonical_records_path=None,
            issue_report_path=None,
            review_log_path=None,
            review_history_path=None,
        )

    prepared_dataframe = preparation_result.prepared_dataframe

    validation_results = validate_vat_data(prepared_dataframe)
    LOGGER.info("Validation stage completed with %s issues", validation_results["issue_count"])

    anomaly_results = detect_anomalies(prepared_dataframe, column="net_amount", method="iqr")
    LOGGER.info("Anomaly detection stage completed with %s flagged rows", len(anomaly_results))

    exported_files = export_outputs(
        raw_dataframe=raw_dataframe,
        prepared_dataframe=prepared_dataframe,
        validation_results=validation_results,
        anomaly_results=anomaly_results,
        review_log=EMPTY_REVIEW_LOG.copy(),
        review_history=EMPTY_REVIEW_HISTORY.copy(),
        output_dir=resolved_output_dir,
    )

    findings_pending_review = validation_results["issue_count"] > 0 or len(anomaly_results) > 0
    if findings_pending_review:
        LOGGER.info("Findings were exported and are ready for user review")
        status = STATUS_STOPPED_AFTER_REPORTING
        stop_reason = STOP_REASON_REVIEW_REQUIRED
    else:
        LOGGER.info("Pipeline completed successfully")
        status = STATUS_COMPLETED
        stop_reason = None

    return RunResult(
        input_file=str(resolved_input_path),
        rows_loaded=len(prepared_dataframe),
        issues_found=validation_results["issue_count"],
        anomalies_flagged=len(anomaly_results),
        status=status,
        stop_reason=stop_reason,
        preparation_status=preparation_result.status,
        preparation_message=preparation_result.message,
        missing_required_fields=preparation_result.missing_required_fields,
        dataset_snapshot_path=str(exported_files["dataset_snapshot"]),
        prepared_canonical_records_path=str(exported_files["prepared_canonical_records"]),
        issue_report_path=str(exported_files["issue_report"]),
        review_log_path=str(exported_files["review_log"]),
        review_history_path=str(exported_files["review_history"]),
    )
