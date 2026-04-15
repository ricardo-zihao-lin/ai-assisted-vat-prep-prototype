"""Run a compact synthetic evaluation summary for the current prototype.

This helper script reuses the existing loading, validation, anomaly detection,
and review components against the fixed synthetic CSV datasets stored in
``data/``. Its purpose is not to perform full experimental evaluation, but to
provide a simple and reproducible summary of what the current prototype
detects.
"""

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from anomaly.anomaly_detector import detect_anomalies
from ingestion.loader import load_spreadsheet
from validation.validator import validate_vat_data

DATASET_PATHS = [
    PROJECT_ROOT / "data" / "synthetic_eval_case_a.csv",
    PROJECT_ROOT / "data" / "synthetic_eval_case_b.csv",
]

SUMMARY_OUTPUT_PATH = PROJECT_ROOT / "output" / "synthetic_evaluation_summary.csv"
ISSUE_TYPES = [
    "missing_column",
    "missing_value",
    "duplicate_row",
    "invalid_date_format",
    "invalid_numeric_format",
]


def summarise_dataset(dataset_path: Path) -> dict:
    """Run the current prototype logic on one dataset and return a compact summary."""
    dataframe = load_spreadsheet(dataset_path)
    validation_results = validate_vat_data(dataframe)
    anomaly_results = detect_anomalies(dataframe, column="net_amount", method="iqr")

    review_items = validation_results["issues"] + anomaly_results

    issue_type_counts = {
        f"count_{issue_type}": sum(1 for issue in validation_results["issues"] if issue.issue_type == issue_type)
        for issue_type in ISSUE_TYPES
    }

    return {
        "dataset_name": dataset_path.name,
        "row_count": len(dataframe),
        "validation_issue_count": validation_results["issue_count"],
        **issue_type_counts,
        "count_anomaly": len(anomaly_results),
        "review_item_count": len(review_items),
        "has_review_relevant_flags": bool(review_items),
        "has_reject_decision": False,
        "has_confirm_decision": False,
        "has_ignore_decision": False,
    }


def main() -> None:
    """Generate and persist a compact summary for the synthetic datasets."""
    summary_rows = [summarise_dataset(dataset_path) for dataset_path in DATASET_PATHS]
    summary_dataframe = pd.DataFrame(summary_rows)

    SUMMARY_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    summary_dataframe.to_csv(SUMMARY_OUTPUT_PATH, index=False)

    print("Synthetic Evaluation Summary")
    print("----------------------------")
    print(summary_dataframe.to_string(index=False))
    print()
    print(f"Saved summary CSV to: {SUMMARY_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
