"""Thin source-run entry point for the VAT spreadsheet preparation prototype."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from pipeline import run_pipeline

LOGGER = logging.getLogger(__name__)


def _build_parser(base_dir: Path) -> argparse.ArgumentParser:
    """Create a small CLI for running the shared pipeline from source."""
    parser = argparse.ArgumentParser(
        description="Run the VAT spreadsheet preparation pipeline from a source checkout.",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=base_dir / "data" / "sample_data.csv",
        help="Path to the CSV or Excel file to analyse.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=base_dir / "output",
        help="Directory where the exported CSV artefacts should be written.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging verbosity for the source-run entry point.",
    )
    return parser


def _print_run_summary(result) -> None:
    """Print a stable, human-readable summary for source runs."""
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
    print(f"input_diagnostics: {result.input_diagnostics_path}")
    print(f"prepared_canonical_records: {result.prepared_canonical_records_path}")
    print(f"issue_report: {result.issue_report_path}")
    print(f"review_log: {result.review_log_path}")
    print(f"review_history: {result.review_history_path}")
    print(f"review_summary: {result.review_summary_path}")


def main(argv: list[str] | None = None) -> int:
    """Run the shared pipeline from source without adding deployment logic."""
    base_dir = Path(__file__).resolve().parent
    parser = _build_parser(base_dir)
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    input_path = args.input.resolve()
    output_dir = args.output_dir.resolve()

    if not input_path.exists():
        parser.error(f"Input file does not exist: {input_path}")

    LOGGER.info("Running source pipeline entry for %s", input_path)
    result = run_pipeline(str(input_path), str(output_dir))
    _print_run_summary(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
