"""Build dissertation-ready evaluation tables from the current outputs.

The script produces three presentation layers:

1. a legacy raw-count table from the synthetic summary
2. an assertion-based validation table for the dissertation core evidence
3. a combined overview that also includes usefulness-comparison outputs

The source artefacts remain unchanged. This script only reshapes the CSV files
that already exist in ``output/`` into compact, dissertation-ready tables.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = PROJECT_ROOT / "output"
EVIDENCE_ROOT = OUTPUT_ROOT / "evidence" / "evaluation"
LEGACY_OUTPUT_ROOT = OUTPUT_ROOT

SUMMARY_INPUT_PATH = EVIDENCE_ROOT / "synthetic_evaluation_summary.csv"
ASSERTION_SUMMARY_INPUT_PATH = EVIDENCE_ROOT / "evaluation_assertion_summary.csv"
USEFULNESS_SUMMARY_INPUT_PATH = EVIDENCE_ROOT / "usefulness_validation_pack" / "usefulness_comparison_summary.csv"

LEGACY_TABLE_OUTPUT_PATH = EVIDENCE_ROOT / "synthetic_evaluation_results_table.csv"
ASSERTION_TABLE_OUTPUT_PATH = EVIDENCE_ROOT / "evaluation_assertion_results_table.csv"
OVERVIEW_TABLE_OUTPUT_PATH = EVIDENCE_ROOT / "evaluation_results_overview.csv"

LEGACY_COLUMNS = [
    "dataset_name",
    "row_count",
    "validation_issue_count",
    "count_review_signals",
    "review_item_count",
    "count_missing_transaction_date",
    "count_invalid_date_format",
    "count_missing_net_amount",
    "count_non_numeric_net_amount",
    "count_exact_duplicate_row",
    "count_blank_description",
    "count_unusual_net_amount",
]

ASSERTION_COLUMNS = [
    "dataset_name",
    "row_count",
    "total_assertions",
    "passed_assertions",
    "failed_assertions",
    "missing_expected_issues",
    "unexpected_actual_issues",
    "duplicate_actual_issues",
    "field_mismatches",
    "exact_match_rate",
    "pipeline_status",
    "stop_reason",
]

OVERVIEW_COLUMNS = [
    "evaluation_track",
    "dataset_name",
    "scenario_goal",
    "row_count",
    "validation_issue_count",
    "total_assertions",
    "passed_assertions",
    "failed_assertions",
    "exact_match_rate",
    "comparison_rows",
    "enhanced_more_useful_count",
    "baseline_more_useful_count",
    "tie_count",
    "enhanced_more_useful_rate",
    "note",
]


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def _read_first_existing(paths: list[Path]) -> pd.DataFrame:
    for path in paths:
        if path.exists():
            return pd.read_csv(path)
    return pd.DataFrame()


def _safe_row_count(dataset_name: str) -> int | None:
    dataset_path = PROJECT_ROOT / "data" / "evaluation" / dataset_name
    if not dataset_path.exists():
        return None
    return int(pd.read_csv(dataset_path).shape[0])


def _build_legacy_table(summary_df: pd.DataFrame) -> pd.DataFrame:
    if summary_df.empty:
        return pd.DataFrame(columns=LEGACY_COLUMNS)
    legacy_df = summary_df[LEGACY_COLUMNS].copy()
    return legacy_df.sort_values("dataset_name").reset_index(drop=True)


def _build_assertion_table(assertion_df: pd.DataFrame) -> pd.DataFrame:
    if assertion_df.empty:
        return pd.DataFrame(columns=ASSERTION_COLUMNS)

    assertion_table = assertion_df.copy()
    assertion_table["row_count"] = assertion_table["dataset_name"].map(_safe_row_count)
    assertion_table = assertion_table.reindex(columns=ASSERTION_COLUMNS)
    return assertion_table.sort_values("dataset_name").reset_index(drop=True)


def _build_usefulness_overview(usefulness_summary_df: pd.DataFrame) -> pd.DataFrame:
    if usefulness_summary_df.empty:
        return pd.DataFrame(columns=OVERVIEW_COLUMNS)

    usefulness_overview = pd.DataFrame(
        {
            "evaluation_track": "usefulness_comparison",
            "dataset_name": usefulness_summary_df["dataset_name"],
            "scenario_goal": usefulness_summary_df["scenario_goal"],
            "row_count": pd.NA,
            "validation_issue_count": pd.NA,
            "total_assertions": pd.NA,
            "passed_assertions": pd.NA,
            "failed_assertions": pd.NA,
            "exact_match_rate": pd.NA,
            "comparison_rows": usefulness_summary_df["comparison_row_count"],
            "enhanced_more_useful_count": usefulness_summary_df["enhanced_more_useful_count"],
            "baseline_more_useful_count": usefulness_summary_df["baseline_more_useful_count"],
            "tie_count": usefulness_summary_df["tie_count"],
            "enhanced_more_useful_rate": usefulness_summary_df["enhanced_more_useful_rate"],
            "note": "Enhanced review-oriented output adds explanation, risk, and manual-check guidance over the raw issue list.",
        }
    )
    return usefulness_overview.reindex(columns=OVERVIEW_COLUMNS).sort_values("dataset_name").reset_index(drop=True)


def _build_assertion_overview(assertion_table: pd.DataFrame) -> pd.DataFrame:
    if assertion_table.empty:
        return pd.DataFrame(columns=OVERVIEW_COLUMNS)

    assertion_overview = pd.DataFrame(
        {
            "evaluation_track": "technical_validation",
            "dataset_name": assertion_table["dataset_name"],
            "scenario_goal": "Assertion-based rule validation",
            "row_count": assertion_table["row_count"],
            "validation_issue_count": pd.NA,
            "total_assertions": assertion_table["total_assertions"],
            "passed_assertions": assertion_table["passed_assertions"],
            "failed_assertions": assertion_table["failed_assertions"],
            "exact_match_rate": assertion_table["exact_match_rate"],
            "comparison_rows": pd.NA,
            "enhanced_more_useful_count": pd.NA,
            "baseline_more_useful_count": pd.NA,
            "tie_count": pd.NA,
            "enhanced_more_useful_rate": pd.NA,
            "note": "Machine-checkable pass/fail comparison against expected issue assertions.",
        }
    )
    return assertion_overview.reindex(columns=OVERVIEW_COLUMNS).sort_values("dataset_name").reset_index(drop=True)


def main() -> None:
    """Create presentation-ready evaluation tables."""
    EVIDENCE_ROOT.mkdir(parents=True, exist_ok=True)
    legacy_summary_df = _read_first_existing(
        [
            SUMMARY_INPUT_PATH,
            LEGACY_OUTPUT_ROOT / "synthetic_evaluation_summary.csv",
        ]
    )
    assertion_summary_df = _read_first_existing(
        [
            ASSERTION_SUMMARY_INPUT_PATH,
            LEGACY_OUTPUT_ROOT / "evaluation_assertion_summary.csv",
        ]
    )
    usefulness_summary_df = _read_first_existing(
        [
            USEFULNESS_SUMMARY_INPUT_PATH,
            LEGACY_OUTPUT_ROOT / "usefulness_validation_pack" / "usefulness_comparison_summary.csv",
        ]
    )

    legacy_table = _build_legacy_table(legacy_summary_df)
    legacy_table.to_csv(LEGACY_TABLE_OUTPUT_PATH, index=False)

    assertion_table = _build_assertion_table(assertion_summary_df)
    assertion_table.to_csv(ASSERTION_TABLE_OUTPUT_PATH, index=False)

    overview_table = pd.concat(
        [
            _build_assertion_overview(assertion_table),
            _build_usefulness_overview(usefulness_summary_df),
        ],
        ignore_index=True,
        sort=False,
    ).reindex(columns=OVERVIEW_COLUMNS).sort_values(["evaluation_track", "dataset_name"])
    overview_table.to_csv(OVERVIEW_TABLE_OUTPUT_PATH, index=False)

    print("Legacy synthetic evaluation table")
    print("----------------------------------")
    print(legacy_table.to_string(index=False))
    print()
    print(f"Saved legacy table to: {LEGACY_TABLE_OUTPUT_PATH}")
    print()
    print("Assertion-based validation table")
    print("--------------------------------")
    print(assertion_table.to_string(index=False))
    print()
    print(f"Saved assertion table to: {ASSERTION_TABLE_OUTPUT_PATH}")
    print()
    print("Combined evaluation overview")
    print("----------------------------")
    print(overview_table.to_string(index=False))
    print()
    print(f"Saved overview table to: {OVERVIEW_TABLE_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
