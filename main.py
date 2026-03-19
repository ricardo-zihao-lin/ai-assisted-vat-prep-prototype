"""Entry point for the VAT spreadsheet preparation prototype.

The script orchestrates the end-to-end research workflow: data ingestion,
baseline validation, anomaly screening, simulated human review, and export of
supporting artefacts. Its purpose is demonstrative rather than production
oriented, showing how lightweight analytical assistance can support spreadsheet
record preparation without directly modifying financial data.
"""

import logging
from pathlib import Path

from anomaly.anomaly_detector import detect_anomalies
from export.exporter import export_outputs
from ingestion.loader import load_spreadsheet
from review.review_manager import ReviewManager
from validation.validator import validate_vat_data

LOGGER = logging.getLogger(__name__)


def print_section(title: str) -> None:
    """Print a simple console section heading for pipeline output.

    Parameters
    ----------
    title : str
        Section title to display in the console output.
    """
    print(f"\n{title}")
    print("-" * len(title))


def print_exported_files(exported_files: dict) -> None:
    """Display generated export artefacts in a consistent format."""
    print_section("Exported Files")
    for name, path in exported_files.items():
        print(f"{name}: {path}")


def main() -> None:
    """Execute the full research prototype pipeline on the sample dataset.

    Notes
    -----
    The routine coordinates all modules in sequence so the prototype can be run
    as a compact end-to-end demonstration. Logging records the main processing
    stages, while console output keeps the intermediate artefacts visible for
    inspection during development or academic demonstration.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    base_dir = Path(__file__).resolve().parent
    input_path = base_dir / "data" / "sample_data.csv"
    output_dir = base_dir / "output"

    LOGGER.info("Starting VAT spreadsheet preparation prototype")
    dataframe = load_spreadsheet(input_path)

    print_section("Loaded Data")
    print(dataframe)

    validation_results = validate_vat_data(dataframe)
    LOGGER.info("Validation stage completed with %s issues", validation_results["issue_count"])
    print_section("Validation Summary")
    print(f"Total issues found: {len(validation_results['issues'])}")
    for issue in validation_results["issues"]:
        print(
            f"[{issue['issue_type']}] row={issue['row_index']} "
            f"column={issue['column']} value={issue['value']}"
        )

    anomaly_results = detect_anomalies(dataframe, column="net_amount", method="iqr")
    LOGGER.info("Anomaly detection stage completed with %s flagged rows", len(anomaly_results))
    print_section("Suspicious Transactions")
    if anomaly_results.empty:
        print("No suspicious transactions detected.")
    else:
        print(
            anomaly_results[
                ["row_index", "date", "description", "net_amount", "anomaly_score", "reason"]
            ]
        )

    review_manager = ReviewManager()
    # Validation findings and anomaly flags are reviewed together to mirror a
    # single analyst worklist in the prototype workflow.
    review_items = validation_results["issues"] + anomaly_results.to_dict(orient="records")
    review_log = review_manager.review_issues(review_items)

    print_section("Review Decisions")
    print(review_log)

    rejected_items = review_log[review_log["decision"] == "reject"]

    if not rejected_items.empty:
        LOGGER.warning("Rejected review items found; exporting reporting artefacts and stopping pipeline")
        exported_files = export_outputs(
            dataframe=dataframe,
            validation_results=validation_results,
            anomaly_results=anomaly_results,
            review_log=review_log,
            output_dir=output_dir,
        )

        print_exported_files(exported_files)
        print_section("Pipeline Status")
        print("Rejected items were found during review.")
        print("Reporting artefacts have been exported.")
        print("Correct the source spreadsheet and rerun the pipeline.")
        LOGGER.info("Pipeline stopped after reporting because review produced rejected items")
        return

    exported_files = export_outputs(
        dataframe=dataframe,
        validation_results=validation_results,
        anomaly_results=anomaly_results,
        review_log=review_log,
        output_dir=output_dir,
    )
    LOGGER.info("Export stage completed successfully")

    print_exported_files(exported_files)

    LOGGER.info("Prototype pipeline finished")


if __name__ == "__main__":
    main()
