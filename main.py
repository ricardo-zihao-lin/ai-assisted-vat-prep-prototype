"""Thin demo entry point for the VAT spreadsheet preparation prototype."""

import logging
from pathlib import Path

from pipeline import run_pipeline

LOGGER = logging.getLogger(__name__)


def main() -> None:
    """Run the sample dataset through the reusable prototype pipeline."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    base_dir = Path(__file__).resolve().parent
    input_path = base_dir / "data" / "sample_data.csv"
    output_dir = base_dir / "output"

    result = run_pipeline(str(input_path), str(output_dir))

    print("VAT Spreadsheet Preparation Prototype")
    print(f"Input file: {result.input_file}")
    print(f"Rows loaded: {result.rows_loaded}")
    print(f"Preparation status: {result.preparation_status}")
    print(f"Preparation note: {result.preparation_message}")
    print(f"Issues found: {result.issues_found}")
    print(f"Anomalies flagged: {result.anomalies_flagged}")
    print(f"Status: {result.status}")
    if result.stop_reason:
        print(f"Stop reason: {result.stop_reason}")
    if result.missing_required_fields:
        print(f"Missing required fields: {', '.join(result.missing_required_fields)}")
    print(f"dataset_snapshot: {result.dataset_snapshot_path}")
    print(f"prepared_canonical_records: {result.prepared_canonical_records_path}")
    print(f"issue_report: {result.issue_report_path}")
    print(f"review_log: {result.review_log_path}")
    print(f"review_history: {result.review_history_path}")


if __name__ == "__main__":
    main()
