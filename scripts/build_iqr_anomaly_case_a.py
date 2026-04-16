"""Build a dissertation-friendly IQR anomaly figure for synthetic case A."""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from anomaly.anomaly_detector import detect_anomalies
from ingestion.loader import load_spreadsheet

DATASET_PATH = PROJECT_ROOT / "data" / "demo" / "synthetic_eval_case_a.csv"
OUTPUT_PATH = PROJECT_ROOT / "output" / "iqr_anomaly_case_a.png"


def main() -> None:
    """Create a scatter plot showing the IQR anomaly result for case A."""
    dataframe = load_spreadsheet(DATASET_PATH)
    anomaly_results = detect_anomalies(dataframe, column="net_amount", method="iqr")

    if not anomaly_results:
        raise ValueError("No anomalies were returned for data/demo/synthetic_eval_case_a.csv.")

    plotting_frame = dataframe.copy()
    plotting_frame["row_index"] = plotting_frame.index
    plotting_frame["net_amount_numeric"] = pd.to_numeric(plotting_frame["net_amount"], errors="coerce")
    plotting_frame = plotting_frame.dropna(subset=["net_amount_numeric"]).copy()

    anomaly_indices = {issue.row_index for issue in anomaly_results if issue.row_index is not None}
    normal_rows = plotting_frame[~plotting_frame["row_index"].isin(anomaly_indices)]
    anomaly_rows = plotting_frame[plotting_frame["row_index"].isin(anomaly_indices)]

    expected_bounds = anomaly_results[0].expected_value or {}
    lower_bound = float(expected_bounds["lower_bound"])
    upper_bound = float(expected_bounds["upper_bound"])

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.scatter(
        normal_rows["row_index"],
        normal_rows["net_amount_numeric"],
        label="Normal transactions",
        marker="o",
        color="tab:blue",
    )
    ax.scatter(
        anomaly_rows["row_index"],
        anomaly_rows["net_amount_numeric"],
        label="Flagged anomalies",
        marker="x",
        s=90,
        linewidths=1.5,
        color="tab:red",
    )

    ax.axhline(lower_bound, color="tab:gray", linestyle="--", linewidth=1, label="IQR lower bound")
    ax.axhline(upper_bound, color="black", linestyle="--", linewidth=1, label="IQR upper bound")

    ax.set_title("IQR Anomaly Flagging for Case A")
    ax.set_xlabel("Row index")
    ax.set_ylabel("Net amount")
    ax.legend(frameon=False)
    ax.grid(axis="y", linestyle="--", linewidth=0.5, alpha=0.7)

    plt.tight_layout()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUTPUT_PATH, dpi=300, bbox_inches="tight")
    plt.close(fig)

    print(f"Saved figure to: {OUTPUT_PATH}")
    print(f"Flagged anomaly rows: {sorted(anomaly_indices)}")
    print(f"Lower bound: {lower_bound}")
    print(f"Upper bound: {upper_bound}")


if __name__ == "__main__":
    main()
