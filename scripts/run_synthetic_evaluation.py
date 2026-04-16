"""Run the prototype's synthetic summary and assertion-based evaluation.

This helper reuses the existing pipeline and validation layers against the
fixed CSV datasets stored in ``data/``. It now produces two outputs:

- a compact synthetic summary for the legacy demo datasets
- a pass/fail assertion report that compares expected and actual issue outputs
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from anomaly.anomaly_detector import detect_anomalies
from ingestion.loader import load_spreadsheet
from pipeline import run_pipeline
from validation.validator import validate_vat_data

SYNTHETIC_DATASET_PATHS = [
    PROJECT_ROOT / "data" / "demo" / "synthetic_eval_case_a.csv",
    PROJECT_ROOT / "data" / "demo" / "synthetic_eval_case_b.csv",
]

OUTPUT_ROOT = PROJECT_ROOT / "output"
RUNS_OUTPUT_ROOT = OUTPUT_ROOT / "runs" / "evaluation"
EVIDENCE_OUTPUT_ROOT = OUTPUT_ROOT / "evidence" / "evaluation"
ASSERTION_DATASET_OUTPUT_ROOT = RUNS_OUTPUT_ROOT / "assertion_runs"
SUMMARY_OUTPUT_PATH = EVIDENCE_OUTPUT_ROOT / "synthetic_evaluation_summary.csv"
ASSERTION_RESULTS_OUTPUT_PATH = EVIDENCE_OUTPUT_ROOT / "evaluation_assertion_results.csv"
ASSERTION_SUMMARY_OUTPUT_PATH = EVIDENCE_OUTPUT_ROOT / "evaluation_assertion_summary.csv"
EXPECTED_ASSERTIONS_PATH = PROJECT_ROOT / "data" / "evaluation" / "expected_issue_assertions.csv"
EVALUATION_DATASET_ROOT = PROJECT_ROOT / "data" / "evaluation"

ACTUAL_ISSUE_TYPES = [
    "missing_column",
    "missing_transaction_date",
    "invalid_date_format",
    "missing_net_amount",
    "non_numeric_net_amount",
    "missing_vat_amount",
    "non_numeric_vat_amount",
    "blank_description",
    "missing_required_review_field",
    "exact_duplicate_row",
    "duplicate_invoice_reference",
    "missing_counterparty_reference",
    "missing_evidence_reference",
    "missing_transaction_category_support_field",
    "negative_or_unusually_low_net_amount",
    "suspicious_zero_value_amount_combination",
    "inconsistent_totals",
    "conflicting_amount_sign_pattern",
    "unusual_net_amount",
]

ASSERTION_COLUMNS = [
    "dataset_name",
    "row_index",
    "rule_id",
    "expected_issue_type",
    "expected_status",
    "expected_risk",
    "expected_decision_example",
    "actual_issue_id",
    "actual_issue_type",
    "actual_status",
    "actual_risk",
    "pass",
    "result_kind",
    "issue_type_match",
    "status_match",
    "risk_match",
    "message",
]


def _normalise_scalar(value: object) -> object:
    if value is None or pd.isna(value):
        return None
    if hasattr(value, "item"):
        try:
            return value.item()
        except ValueError:
            return value
    return value


def summarise_dataset(dataset_path: Path) -> dict:
    """Run the current prototype logic on one dataset and return a compact summary."""
    dataframe = load_spreadsheet(dataset_path)
    validation_results = validate_vat_data(dataframe)
    anomaly_results = detect_anomalies(dataframe, column="net_amount", method="iqr")

    review_items = validation_results["issues"] + anomaly_results
    issue_counter = Counter(issue.issue_type for issue in review_items)

    summary_row = {
        "dataset_name": dataset_path.name,
        "row_count": len(dataframe),
        "validation_issue_count": validation_results["issue_count"],
        "count_review_signals": len(anomaly_results),
        "review_item_count": len(review_items),
        "has_review_relevant_flags": bool(review_items),
    }
    for issue_type in ACTUAL_ISSUE_TYPES:
        summary_row[f"count_{issue_type}"] = int(issue_counter.get(issue_type, 0))
    return summary_row


def _load_expected_assertions() -> pd.DataFrame:
    assertions = pd.read_csv(EXPECTED_ASSERTIONS_PATH)
    assertions["row_index"] = pd.to_numeric(assertions["row_index"], errors="coerce").astype("Int64")
    return assertions


def _load_actual_issue_report(dataset_path: Path) -> tuple[pd.DataFrame, str, str | None]:
    dataset_output_dir = ASSERTION_DATASET_OUTPUT_ROOT / dataset_path.stem
    run_result = run_pipeline(str(dataset_path), str(dataset_output_dir))

    if not run_result.issue_report_path:
        return pd.DataFrame(), run_result.status, run_result.stop_reason

    issue_report = pd.read_csv(run_result.issue_report_path)
    if not issue_report.empty and "row_index" in issue_report.columns:
        issue_report["row_index"] = pd.to_numeric(issue_report["row_index"], errors="coerce").astype("Int64")
    return issue_report, run_result.status, run_result.stop_reason


def _build_actual_lookup(issue_report: pd.DataFrame) -> dict[tuple[int, str], pd.DataFrame]:
    if issue_report.empty:
        return {}

    lookup: dict[tuple[int, str], pd.DataFrame] = {}
    for _, row in issue_report.iterrows():
        row_index = row.get("row_index")
        rule_id = str(row.get("rule_id") or "")
        if pd.isna(row_index):
            continue
        key = (int(row_index), rule_id)
        lookup.setdefault(key, pd.DataFrame())
        lookup[key] = pd.concat([lookup[key], row.to_frame().T], ignore_index=True)
    return lookup


def _evaluate_assertions_for_dataset(dataset_path: Path, assertions: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    issue_report, pipeline_status, stop_reason = _load_actual_issue_report(dataset_path)
    actual_lookup = _build_actual_lookup(issue_report)

    dataset_name = dataset_path.name
    dataset_assertions = assertions[assertions["dataset_name"] == dataset_name].copy()
    if dataset_assertions.empty:
        return pd.DataFrame(columns=ASSERTION_COLUMNS), {
            "dataset_name": dataset_name,
            "total_assertions": 0,
            "passed_assertions": 0,
            "failed_assertions": 0,
            "missing_expected_issues": 0,
            "unexpected_actual_issues": int(len(issue_report)),
            "pipeline_status": pipeline_status,
            "stop_reason": stop_reason or "",
        }

    result_rows: list[dict[str, object]] = []
    matched_actual_keys: set[tuple[int, str]] = set()

    for assertion in dataset_assertions.itertuples(index=False):
        row_index = _normalise_scalar(assertion.row_index)
        key = (int(row_index), str(assertion.rule_id))
        expected_issue_type = str(assertion.issue_type)
        expected_status = str(assertion.expected_status)
        expected_risk = str(assertion.expected_risk)
        expected_decision_example = str(assertion.expected_decision_example)

        matching_actual = actual_lookup.get(key)
        if matching_actual is None or matching_actual.empty:
            result_rows.append(
                {
                    "dataset_name": dataset_name,
                    "row_index": int(row_index),
                    "rule_id": str(assertion.rule_id),
                    "expected_issue_type": expected_issue_type,
                    "expected_status": expected_status,
                    "expected_risk": expected_risk,
                    "expected_decision_example": expected_decision_example,
                    "actual_issue_id": "",
                    "actual_issue_type": "",
                    "actual_status": "",
                    "actual_risk": "",
                    "pass": False,
                    "result_kind": "missing_expected_issue",
                    "issue_type_match": False,
                    "status_match": False,
                    "risk_match": False,
                    "message": "No matching issue was produced by the pipeline.",
                }
            )
            continue

        if len(matching_actual) > 1:
            actual_issue_types = ", ".join(sorted({str(value) for value in matching_actual["issue_type"].tolist()}))
            result_rows.append(
                {
                    "dataset_name": dataset_name,
                    "row_index": int(row_index),
                    "rule_id": str(assertion.rule_id),
                    "expected_issue_type": expected_issue_type,
                    "expected_status": expected_status,
                    "expected_risk": expected_risk,
                    "expected_decision_example": expected_decision_example,
                    "actual_issue_id": "",
                    "actual_issue_type": actual_issue_types,
                    "actual_status": "",
                    "actual_risk": "",
                    "pass": False,
                    "result_kind": "duplicate_actual_issue",
                    "issue_type_match": False,
                    "status_match": False,
                    "risk_match": False,
                    "message": "More than one pipeline issue matched the same row/rule key.",
                }
            )
            continue

        actual_row = matching_actual.iloc[0]
        matched_actual_keys.add(key)
        actual_issue_type = str(actual_row.get("issue_type") or "")
        actual_status = str(actual_row.get("status") or "")
        actual_risk = str(actual_row.get("risk_level") or "")
        issue_type_match = actual_issue_type == expected_issue_type
        status_match = actual_status == expected_status
        risk_match = actual_risk == expected_risk
        passed = issue_type_match and status_match and risk_match
        result_rows.append(
            {
                "dataset_name": dataset_name,
                "row_index": int(row_index),
                "rule_id": str(assertion.rule_id),
                "expected_issue_type": expected_issue_type,
                "expected_status": expected_status,
                "expected_risk": expected_risk,
                "expected_decision_example": expected_decision_example,
                "actual_issue_id": str(actual_row.get("issue_id") or ""),
                "actual_issue_type": actual_issue_type,
                "actual_status": actual_status,
                "actual_risk": actual_risk,
                "pass": passed,
                "result_kind": "pass" if passed else "field_mismatch",
                "issue_type_match": issue_type_match,
                "status_match": status_match,
                "risk_match": risk_match,
                "message": "" if passed else "One or more compared fields did not match the expectation.",
            }
        )

    for key, matching_actual in actual_lookup.items():
        if key in matched_actual_keys:
            continue
        if matching_actual.empty:
            continue
        actual_row = matching_actual.iloc[0]
        result_rows.append(
            {
                "dataset_name": dataset_name,
                "row_index": int(key[0]),
                "rule_id": key[1],
                "expected_issue_type": "",
                "expected_status": "",
                "expected_risk": "",
                "expected_decision_example": "",
                "actual_issue_id": str(actual_row.get("issue_id") or ""),
                "actual_issue_type": str(actual_row.get("issue_type") or ""),
                "actual_status": str(actual_row.get("status") or ""),
                "actual_risk": str(actual_row.get("risk_level") or ""),
                "pass": False,
                "result_kind": "unexpected_actual_issue",
                "issue_type_match": False,
                "status_match": False,
                "risk_match": False,
                "message": "The pipeline produced an issue that is not listed in expected_issue_assertions.csv.",
            }
        )

    result_dataframe = pd.DataFrame(result_rows, columns=ASSERTION_COLUMNS)
    summary_row = {
        "dataset_name": dataset_name,
        "total_assertions": int(len(dataset_assertions)),
        "passed_assertions": int((result_dataframe["pass"] == True).sum()) if not result_dataframe.empty else 0,  # noqa: E712
        "failed_assertions": int((result_dataframe["pass"] == False).sum()) if not result_dataframe.empty else int(len(dataset_assertions)),  # noqa: E712
        "missing_expected_issues": int((result_dataframe["result_kind"] == "missing_expected_issue").sum()) if not result_dataframe.empty else 0,
        "unexpected_actual_issues": int((result_dataframe["result_kind"] == "unexpected_actual_issue").sum()) if not result_dataframe.empty else 0,
        "duplicate_actual_issues": int((result_dataframe["result_kind"] == "duplicate_actual_issue").sum()) if not result_dataframe.empty else 0,
        "field_mismatches": int((result_dataframe["result_kind"] == "field_mismatch").sum()) if not result_dataframe.empty else 0,
        "pipeline_status": pipeline_status,
        "stop_reason": stop_reason or "",
    }
    summary_row["exact_match_rate"] = 0.0 if summary_row["total_assertions"] == 0 else round(
        (summary_row["passed_assertions"] / summary_row["total_assertions"]) * 100.0,
        1,
    )
    return result_dataframe, summary_row


def run_assertion_evaluation() -> tuple[pd.DataFrame, pd.DataFrame]:
    assertions = _load_expected_assertions()
    evaluation_dataset_paths = sorted(EVALUATION_DATASET_ROOT.glob("*_case.csv"))
    result_frames: list[pd.DataFrame] = []
    summary_rows: list[dict] = []

    for dataset_path in evaluation_dataset_paths:
        dataset_results, dataset_summary = _evaluate_assertions_for_dataset(dataset_path, assertions)
        result_frames.append(dataset_results)
        summary_rows.append(dataset_summary)

    results_dataframe = pd.concat(result_frames, ignore_index=True) if result_frames else pd.DataFrame(columns=ASSERTION_COLUMNS)
    summary_dataframe = pd.DataFrame(summary_rows)
    return results_dataframe, summary_dataframe


def main() -> None:
    """Generate and persist the synthetic summary plus assertion evaluation."""
    summary_rows = [summarise_dataset(dataset_path) for dataset_path in SYNTHETIC_DATASET_PATHS]
    summary_dataframe = pd.DataFrame(summary_rows)

    ASSERTION_DATASET_OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    ASSERTION_RESULTS_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ASSERTION_SUMMARY_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    summary_dataframe.to_csv(SUMMARY_OUTPUT_PATH, index=False)

    assertion_results, assertion_summary = run_assertion_evaluation()
    assertion_results.to_csv(ASSERTION_RESULTS_OUTPUT_PATH, index=False)
    assertion_summary.to_csv(ASSERTION_SUMMARY_OUTPUT_PATH, index=False)

    print("Synthetic Evaluation Summary")
    print("----------------------------")
    print(summary_dataframe.to_string(index=False))
    print()
    print("Assertion Evaluation Summary")
    print("----------------------------")
    print(assertion_summary.to_string(index=False))
    print()
    print(f"Saved synthetic summary CSV to: {SUMMARY_OUTPUT_PATH}")
    print(f"Saved assertion results CSV to: {ASSERTION_RESULTS_OUTPUT_PATH}")
    print(f"Saved assertion summary CSV to: {ASSERTION_SUMMARY_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
