"""Build side-by-side usefulness-validation artefacts for review evaluation.

This script creates comparable outputs for a minimal raw issue-list baseline
and the current review-oriented prototype output. The goal is to support the
usefulness validation described in ``docs/evaluation_plan.md`` without
requiring manual CSV assembly.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline import run_pipeline

EVALUATION_DATASET_ROOT = PROJECT_ROOT / "data" / "evaluation"
OUTPUT_ROOT = PROJECT_ROOT / "output" / "usefulness_validation_pack"
TASK_PACK_OUTPUT_PATH = OUTPUT_ROOT / "usefulness_validation_task_pack.csv"
MANIFEST_OUTPUT_PATH = OUTPUT_ROOT / "usefulness_validation_manifest.csv"
COMPARISON_RESULTS_OUTPUT_PATH = OUTPUT_ROOT / "usefulness_comparison_results.csv"
COMPARISON_SUMMARY_OUTPUT_PATH = OUTPUT_ROOT / "usefulness_comparison_summary.csv"

USEFULNESS_DATASETS = {
    "review_support_case.csv": "Explainability and prioritisation comparison",
    "decision_logging_case.csv": "Workflow and decision-support comparison",
}

RAW_BASELINE_COLUMNS = [
    "issue_id",
    "dataset_name",
    "row_index",
    "rule_id",
    "issue_type",
    "checked_field",
    "short_error_label",
    "raw_issue_list_entry",
]

ENHANCED_OUTPUT_COLUMNS = [
    "issue_id",
    "dataset_name",
    "row_index",
    "rule_id",
    "issue_type",
    "status",
    "risk_level",
    "finding_summary",
    "why_it_matters",
    "possible_vat_review_impact",
    "recommended_manual_check",
    "fields_to_check",
    "suggested_action",
]

SIDE_BY_SIDE_COLUMNS = [
    "issue_id",
    "dataset_name",
    "row_index",
    "rule_id",
    "issue_type",
    "raw_issue_list_entry",
    "status",
    "risk_level",
    "finding_summary",
    "why_it_matters",
    "possible_vat_review_impact",
    "recommended_manual_check",
    "fields_to_check",
    "suggested_action",
]

TASK_PACK_COLUMNS = [
    "task_id",
    "dataset_name",
    "scenario_goal",
    "issue_focus",
    "row_index",
    "rule_id",
    "raw_issue_list_entry",
    "enhanced_output_focus",
    "evaluation_prompt",
    "what_to_judge",
]

COMPARISON_RESULT_COLUMNS = [
    "dataset_name",
    "scenario_goal",
    "task_id",
    "issue_focus",
    "row_index",
    "rule_id",
    "baseline_support_feature_count",
    "enhanced_support_feature_count",
    "support_feature_gap",
    "comparison_result",
    "comparison_basis",
    "raw_issue_list_entry",
    "status",
    "risk_level",
    "finding_summary",
    "why_it_matters",
    "recommended_manual_check",
]

COMPARISON_SUMMARY_COLUMNS = [
    "dataset_name",
    "scenario_goal",
    "comparison_row_count",
    "enhanced_more_useful_count",
    "baseline_more_useful_count",
    "tie_count",
    "average_support_feature_gap",
    "enhanced_more_useful_rate",
]


def _normalise_row_index(value: object) -> int | None:
    numeric_value = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric_value):
        return None
    return int(numeric_value)


def _read_issue_report(issue_report_path: str | None) -> pd.DataFrame:
    if not issue_report_path:
        return pd.DataFrame()

    issue_report = pd.read_csv(issue_report_path)
    if issue_report.empty:
        return issue_report

    if "row_index" in issue_report.columns:
        issue_report["row_index"] = issue_report["row_index"].map(_normalise_row_index)
    return issue_report


def _build_raw_issue_list(issue_report: pd.DataFrame, dataset_name: str) -> pd.DataFrame:
    """Build a minimal baseline view resembling a basic issue list."""
    if issue_report.empty:
        return pd.DataFrame(columns=RAW_BASELINE_COLUMNS)

    baseline_df = issue_report.copy()
    baseline_df["dataset_name"] = dataset_name
    baseline_df["checked_field"] = (
        baseline_df.get("column", "")
        .fillna("")
        .where(baseline_df.get("column", "").fillna("").astype(str).str.len() > 0, baseline_df.get("fields_to_check", "record"))
    )
    baseline_df["short_error_label"] = baseline_df.get("issue_type", "").fillna("").astype(str)
    baseline_df["raw_issue_list_entry"] = baseline_df.apply(
        lambda row: f"row {row['row_index']} | {row['issue_type']} | {row['checked_field']}",
        axis=1,
    )
    return baseline_df.reindex(columns=RAW_BASELINE_COLUMNS).sort_values(["row_index", "rule_id", "issue_id"])


def _build_enhanced_output(issue_report: pd.DataFrame, dataset_name: str) -> pd.DataFrame:
    """Keep only the fields needed for usefulness validation."""
    if issue_report.empty:
        return pd.DataFrame(columns=ENHANCED_OUTPUT_COLUMNS)

    enhanced_df = issue_report.copy()
    enhanced_df["dataset_name"] = dataset_name
    return enhanced_df.reindex(columns=ENHANCED_OUTPUT_COLUMNS).sort_values(["row_index", "rule_id", "issue_id"])


def _build_side_by_side_output(raw_df: pd.DataFrame, enhanced_df: pd.DataFrame) -> pd.DataFrame:
    if raw_df.empty:
        return pd.DataFrame(columns=SIDE_BY_SIDE_COLUMNS)

    comparison_df = raw_df.merge(
        enhanced_df[
            [
                "issue_id",
                "status",
                "risk_level",
                "finding_summary",
                "why_it_matters",
                "possible_vat_review_impact",
                "recommended_manual_check",
                "fields_to_check",
                "suggested_action",
            ]
        ],
        on="issue_id",
        how="left",
    )
    return comparison_df.reindex(columns=SIDE_BY_SIDE_COLUMNS).sort_values(["row_index", "rule_id", "issue_id"])


def _build_task_rows(side_by_side_df: pd.DataFrame, dataset_name: str, scenario_goal: str) -> list[dict[str, object]]:
    if side_by_side_df.empty:
        return []

    task_rows: list[dict[str, object]] = []
    for task_number, row in enumerate(side_by_side_df.itertuples(index=False), start=1):
        task_rows.append(
            {
                "task_id": f"{Path(dataset_name).stem.upper()}-{task_number:02d}",
                "dataset_name": dataset_name,
                "scenario_goal": scenario_goal,
                "issue_focus": row.issue_type,
                "row_index": row.row_index,
                "rule_id": row.rule_id,
                "raw_issue_list_entry": row.raw_issue_list_entry,
                "enhanced_output_focus": row.finding_summary,
                "evaluation_prompt": (
                    "Compare the raw issue-list entry with the enhanced output and decide which one better supports "
                    "understanding, prioritisation, and next-step review action."
                ),
                "what_to_judge": (
                    "Is the issue easier to understand? Is the significance clearer? Is the next manual check "
                    "more obvious? Would it be easier to record a confident review decision?"
                ),
            }
        )
    return task_rows


def _count_support_features(row: pd.Series, columns: list[str]) -> int:
    count = 0
    for column in columns:
        value = row.get(column)
        if pd.notna(value) and str(value).strip():
            count += 1
    return count


def _build_comparison_rows(
    side_by_side_df: pd.DataFrame,
    dataset_name: str,
    scenario_goal: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if side_by_side_df.empty:
        empty_results = pd.DataFrame(columns=COMPARISON_RESULT_COLUMNS)
        empty_summary = pd.DataFrame(columns=COMPARISON_SUMMARY_COLUMNS)
        return empty_results, empty_summary

    baseline_support_columns = [
        "row_index",
        "rule_id",
        "issue_type",
        "checked_field",
        "short_error_label",
    ]
    enhanced_support_columns = [
        "status",
        "risk_level",
        "finding_summary",
        "why_it_matters",
        "possible_vat_review_impact",
        "recommended_manual_check",
        "fields_to_check",
        "suggested_action",
    ]

    comparison_rows: list[dict[str, object]] = []
    for task_number, row in enumerate(side_by_side_df.itertuples(index=False), start=1):
        row_series = pd.Series(row._asdict())
        baseline_score = _count_support_features(row_series, baseline_support_columns)
        enhanced_score = _count_support_features(row_series, enhanced_support_columns)
        score_gap = enhanced_score - baseline_score
        if score_gap > 0:
            comparison_result = "enhanced_more_useful"
        elif score_gap < 0:
            comparison_result = "baseline_more_useful"
        else:
            comparison_result = "tie"

        comparison_rows.append(
            {
                "dataset_name": dataset_name,
                "scenario_goal": scenario_goal,
                "task_id": f"{Path(dataset_name).stem.upper()}-{task_number:02d}",
                "issue_focus": row.issue_type,
                "row_index": row.row_index,
                "rule_id": row.rule_id,
                "baseline_support_feature_count": baseline_score,
                "enhanced_support_feature_count": enhanced_score,
                "support_feature_gap": score_gap,
                "comparison_result": comparison_result,
                "comparison_basis": (
                    "Enhanced output adds status, risk, explanation, impact, and next-step guidance "
                    "beyond the raw issue-list baseline."
                ),
                "raw_issue_list_entry": row.raw_issue_list_entry,
                "status": row.status,
                "risk_level": row.risk_level,
                "finding_summary": row.finding_summary,
                "why_it_matters": row.why_it_matters,
                "recommended_manual_check": row.recommended_manual_check,
            }
        )

    comparison_df = pd.DataFrame(comparison_rows, columns=COMPARISON_RESULT_COLUMNS)
    comparison_summary = (
        comparison_df.groupby(["dataset_name", "scenario_goal"], as_index=False)
        .agg(
            comparison_row_count=("task_id", "count"),
            enhanced_more_useful_count=("comparison_result", lambda series: int((series == "enhanced_more_useful").sum())),
            baseline_more_useful_count=("comparison_result", lambda series: int((series == "baseline_more_useful").sum())),
            tie_count=("comparison_result", lambda series: int((series == "tie").sum())),
            average_support_feature_gap=("support_feature_gap", "mean"),
        )
    )
    comparison_summary["enhanced_more_useful_rate"] = (
        comparison_summary["enhanced_more_useful_count"] / comparison_summary["comparison_row_count"] * 100.0
    ).round(1)
    comparison_summary = comparison_summary.reindex(columns=COMPARISON_SUMMARY_COLUMNS).sort_values(
        ["dataset_name"]
    )
    return comparison_df, comparison_summary


def main() -> None:
    """Generate usefulness-validation artefacts for the evaluation datasets."""
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    manifest_rows: list[dict[str, str]] = []
    task_rows: list[dict[str, object]] = []
    comparison_rows: list[pd.DataFrame] = []
    comparison_summaries: list[pd.DataFrame] = []

    for dataset_name, scenario_goal in USEFULNESS_DATASETS.items():
        dataset_path = EVALUATION_DATASET_ROOT / dataset_name
        dataset_output_dir = OUTPUT_ROOT / dataset_path.stem
        dataset_output_dir.mkdir(parents=True, exist_ok=True)

        run_result = run_pipeline(str(dataset_path), str(dataset_output_dir))
        issue_report = _read_issue_report(run_result.issue_report_path)
        raw_df = _build_raw_issue_list(issue_report, dataset_name)
        enhanced_df = _build_enhanced_output(issue_report, dataset_name)
        comparison_df = _build_side_by_side_output(raw_df, enhanced_df)
        comparison_result_df, comparison_summary_df = _build_comparison_rows(
            comparison_df,
            dataset_name,
            scenario_goal,
        )

        raw_output_path = dataset_output_dir / "raw_issue_list_baseline.csv"
        enhanced_output_path = dataset_output_dir / "review_oriented_output.csv"
        comparison_output_path = dataset_output_dir / "usefulness_side_by_side.csv"

        raw_df.to_csv(raw_output_path, index=False)
        enhanced_df.to_csv(enhanced_output_path, index=False)
        comparison_df.to_csv(comparison_output_path, index=False)
        comparison_result_df.to_csv(OUTPUT_ROOT / f"{dataset_path.stem}_comparison_results.csv", index=False)
        comparison_rows.append(comparison_result_df)
        comparison_summaries.append(comparison_summary_df)

        manifest_rows.extend(
            [
                {
                    "dataset_name": dataset_name,
                    "scenario_goal": scenario_goal,
                    "artifact_type": "raw_issue_list_baseline",
                    "path": str(raw_output_path),
                },
                {
                    "dataset_name": dataset_name,
                    "scenario_goal": scenario_goal,
                    "artifact_type": "review_oriented_output",
                    "path": str(enhanced_output_path),
                },
                {
                    "dataset_name": dataset_name,
                    "scenario_goal": scenario_goal,
                    "artifact_type": "usefulness_side_by_side",
                    "path": str(comparison_output_path),
                },
            ]
        )
        task_rows.extend(_build_task_rows(comparison_df, dataset_name, scenario_goal))

    pd.DataFrame(task_rows, columns=TASK_PACK_COLUMNS).to_csv(TASK_PACK_OUTPUT_PATH, index=False)
    pd.DataFrame(manifest_rows, columns=["dataset_name", "scenario_goal", "artifact_type", "path"]).to_csv(
        MANIFEST_OUTPUT_PATH,
        index=False,
    )
    if comparison_rows:
        pd.concat(comparison_rows, ignore_index=True).to_csv(COMPARISON_RESULTS_OUTPUT_PATH, index=False)
    else:
        pd.DataFrame(columns=COMPARISON_RESULT_COLUMNS).to_csv(COMPARISON_RESULTS_OUTPUT_PATH, index=False)

    if comparison_summaries:
        pd.concat(comparison_summaries, ignore_index=True).to_csv(COMPARISON_SUMMARY_OUTPUT_PATH, index=False)
    else:
        pd.DataFrame(columns=COMPARISON_SUMMARY_COLUMNS).to_csv(COMPARISON_SUMMARY_OUTPUT_PATH, index=False)

    print("Usefulness validation artefacts written:")
    print(MANIFEST_OUTPUT_PATH)
    print(TASK_PACK_OUTPUT_PATH)


if __name__ == "__main__":
    main()
