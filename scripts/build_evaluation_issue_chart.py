"""Build a dissertation-ready evaluation figure.

The figure combines the two evidence layers that matter most for the write-up:

1. assertion-based validation exact-match rates
2. usefulness-comparison dominance counts for the review-oriented output

This keeps the presentation layer aligned with the evaluation story rather than
only showing raw issue counts.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = PROJECT_ROOT / "output"
EVIDENCE_ROOT = OUTPUT_ROOT / "evidence" / "evaluation"
ASSERTION_TABLE_INPUT_PATH = EVIDENCE_ROOT / "evaluation_assertion_results_table.csv"
USEFULNESS_SUMMARY_INPUT_PATH = EVIDENCE_ROOT / "usefulness_validation_pack" / "usefulness_comparison_summary.csv"
CHART_OUTPUT_PATH = EVIDENCE_ROOT / "figures" / "evaluation_evidence_chart.png"

ASSERTION_LABELS = {
    "deterministic_validation_case.csv": "Deterministic",
    "review_support_case.csv": "Review support",
    "decision_logging_case.csv": "Decision logging",
}

USEFULNESS_LABELS = {
    "review_support_case.csv": "Explainability",
    "decision_logging_case.csv": "Workflow support",
}


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def _read_first_existing(paths: list[Path]) -> pd.DataFrame:
    for path in paths:
        if path.exists():
            return pd.read_csv(path)
    return pd.DataFrame()


def main() -> None:
    """Create a two-panel evidence chart for the dissertation write-up."""
    assertion_table = _read_first_existing(
        [
            ASSERTION_TABLE_INPUT_PATH,
            OUTPUT_ROOT / "evaluation_assertion_results_table.csv",
        ]
    )
    usefulness_summary = _read_first_existing(
        [
            USEFULNESS_SUMMARY_INPUT_PATH,
            OUTPUT_ROOT / "usefulness_validation_pack" / "usefulness_comparison_summary.csv",
        ]
    )

    if assertion_table.empty and usefulness_summary.empty:
        raise SystemExit("No evaluation summary data found. Run the evaluation scripts first.")

    figure, (validation_axis, usefulness_axis) = plt.subplots(1, 2, figsize=(12, 5))

    if not assertion_table.empty:
        validation_data = (
            assertion_table.set_index("dataset_name")
            .reindex(list(ASSERTION_LABELS.keys()))["exact_match_rate"]
            .rename(index=ASSERTION_LABELS)
        )
        validation_axis.bar(
            validation_data.index,
            validation_data.values,
            color="#355C7D",
            edgecolor="black",
        )
        validation_axis.set_title("Assertion-based validation")
        validation_axis.set_xlabel("Dataset")
        validation_axis.set_ylabel("Exact match rate (%)")
        validation_axis.set_ylim(0, 105)
        validation_axis.grid(axis="y", linestyle="--", linewidth=0.5, alpha=0.6)
        for index, value in enumerate(validation_data.values):
            validation_axis.text(index, value + 1.5, f"{value:.1f}%", ha="center", va="bottom", fontsize=9)
    else:
        validation_axis.set_axis_off()

    if not usefulness_summary.empty:
        usefulness_data = (
            usefulness_summary.set_index("dataset_name")
            .reindex(list(USEFULNESS_LABELS.keys()))[
                ["enhanced_more_useful_count", "baseline_more_useful_count", "tie_count"]
            ]
        )
        usefulness_data.index = usefulness_data.index.map(USEFULNESS_LABELS)
        usefulness_data.plot(
            kind="bar",
            stacked=True,
            ax=usefulness_axis,
            color=["#2E8B57", "#C44E52", "#8C8C8C"],
            edgecolor="black",
            width=0.75,
        )
        usefulness_axis.set_xticklabels(usefulness_data.index, rotation=0)
        usefulness_axis.set_title("Usefulness comparison rubric")
        usefulness_axis.set_xlabel("Scenario")
        usefulness_axis.set_ylabel("Comparison rows")
        usefulness_axis.grid(axis="y", linestyle="--", linewidth=0.5, alpha=0.6)
        usefulness_axis.legend(
            ["Enhanced more useful", "Baseline more useful", "Tie"],
            frameon=False,
            title="Outcome",
        )
        for index, (_, row) in enumerate(usefulness_data.iterrows()):
            total = int(row.sum())
            usefulness_axis.text(index, total + 0.2, f"{total}", ha="center", va="bottom", fontsize=9)
    else:
        usefulness_axis.set_axis_off()

    figure.suptitle("Evaluation evidence for dissertation write-up")
    figure.tight_layout(rect=(0, 0, 1, 0.95))
    CHART_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(CHART_OUTPUT_PATH, dpi=300, bbox_inches="tight")
    plt.close(figure)

    print(f"Saved chart to: {CHART_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
