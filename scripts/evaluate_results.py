#!/usr/bin/env python3
"""
Evaluate VAT audit detection results against a known poisoning log.

Purpose
-------
This script compares the ground-truth injected issues recorded in a poisoning
log against the prototype's detected issue report. It performs row-level
matching only and produces:

1. Overall evaluation metrics:
   - True Positives (TP)
   - False Positives (FP)
   - False Negatives (FN)
   - Precision
   - Recall

2. Per-category recall breakdown by poison_type

3. A missed case export for manual qualitative review:
   - data/evaluation/missed_cases.txt

Usage
-----
Run from the project root, for example:

    python scripts/evaluate_results.py

Assumed default input paths:
    data/evaluation/poisoning_log.json
    issue_report.csv

You can optionally pass custom paths:

    python scripts/evaluate_results.py \
        --poisoning-log data/evaluation/poisoning_log.json \
        --issue-report issue_report.csv \
        --missed-out data/evaluation/missed_cases.txt
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_POISONING_LOG = Path("data/evaluation/poisoning_log.json")
DEFAULT_ISSUE_REPORT = Path("issue_report.csv")
DEFAULT_MISSED_OUT = Path("data/evaluation/missed_cases.txt")


def safe_divide(numerator: int | float, denominator: int | float) -> float:
    """Safely divide two values, returning 0.0 if the denominator is zero."""
    if denominator == 0:
        return 0.0
    return float(numerator) / float(denominator)


def normalise_row_index(value: Any) -> str | None:
    """
    Convert row_index into a stable comparable string form.

    Rules:
    - Ignore missing / blank values
    - Handle string vs int mismatches
    - Convert numeric-looking values consistently
    - Strip whitespace
    - Convert values like 12.0 -> "12"
    """
    if pd.isna(value):
        return None

    text = str(value).strip()
    if not text:
        return None

    try:
        numeric = float(text)
        if numeric.is_integer():
            return str(int(numeric))
        return str(numeric)
    except (ValueError, TypeError):
        return text


def load_json_file(path: Path) -> Any:
    """Load JSON safely with a helpful error message."""
    if not path.exists():
        raise FileNotFoundError(f"Poisoning log file not found: {path}")

    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in poisoning log: {path}\n{exc}") from exc


def parse_poisoning_log(path: Path) -> pd.DataFrame:
    """
    Load and normalise the poisoning log.

    Supported structures:
    - top-level list
    - {"issues": [...]}

    Required logical fields:
    - row_index
    - poison_type

    record_id is exported when available.
    """
    payload = load_json_file(path)

    if isinstance(payload, list):
        issues = payload
    elif isinstance(payload, dict) and isinstance(payload.get("issues"), list):
        issues = payload["issues"]
    else:
        raise ValueError(
            "Unsupported poisoning log structure. Expected either a top-level "
            "list or a dictionary containing an 'issues' list."
        )

    if not issues:
        return pd.DataFrame(columns=["record_id", "row_index", "poison_type", "row_key"])

    df = pd.DataFrame(issues)

    if "row_index" not in df.columns:
        raise KeyError("Poisoning log is missing required column: 'row_index'")
    if "poison_type" not in df.columns:
        raise KeyError("Poisoning log is missing required column: 'poison_type'")

    if "record_id" not in df.columns:
        df["record_id"] = ""

    df["row_key"] = df["row_index"].apply(normalise_row_index)
    df = df[df["row_key"].notna()].copy()
    df["poison_type"] = df["poison_type"].fillna("UNKNOWN").astype(str).str.strip()
    df.loc[df["poison_type"] == "", "poison_type"] = "UNKNOWN"
    return df


def parse_issue_report(path: Path) -> pd.DataFrame:
    """
    Load and normalise the issue report CSV.

    Required logical field:
    - row_index
    """
    if not path.exists():
        raise FileNotFoundError(f"Issue report file not found: {path}")

    try:
        df = pd.read_csv(path)
    except Exception as exc:
        raise ValueError(f"Failed to read issue report CSV: {path}\n{exc}") from exc

    if "row_index" not in df.columns:
        raise KeyError("Issue report is missing required column: 'row_index'")

    df["row_key"] = df["row_index"].apply(normalise_row_index)
    df = df[df["row_key"].notna()].copy()
    return df


def build_overall_metrics(poison_df: pd.DataFrame, issue_df: pd.DataFrame) -> dict[str, Any]:
    """
    Compute overall row-level evaluation metrics.

    Matching rule:
    - Use row-level matching only.
    - Deduplicate rows before scoring.
    """
    injected_rows = set(poison_df["row_key"].dropna().unique())
    flagged_rows = set(issue_df["row_key"].dropna().unique())

    true_positive_rows = injected_rows & flagged_rows
    false_positive_rows = flagged_rows - injected_rows
    false_negative_rows = injected_rows - flagged_rows

    tp = len(true_positive_rows)
    fp = len(false_positive_rows)
    fn = len(false_negative_rows)

    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": safe_divide(tp, tp + fp),
        "recall": safe_divide(tp, tp + fn),
        "true_positive_rows": true_positive_rows,
        "false_positive_rows": false_positive_rows,
        "false_negative_rows": false_negative_rows,
    }


def build_category_breakdown(poison_df: pd.DataFrame, detected_rows: set[str]) -> pd.DataFrame:
    """
    Build a per-category recall table.

    To avoid row-level double counting:
    - Deduplicate by (row_key, poison_type)
    - Then measure detection at row level within each poison_type
    """
    if poison_df.empty:
        return pd.DataFrame(
            columns=["poison_type", "injected_rows", "detected_rows", "missed_rows", "recall"]
        )

    dedup = poison_df.drop_duplicates(subset=["row_key", "poison_type"]).copy()
    rows: list[dict[str, Any]] = []

    for poison_type, group in dedup.groupby("poison_type", dropna=False):
        category_rows = set(group["row_key"].dropna().unique())
        injected_count = len(category_rows)
        detected_count = len(category_rows & detected_rows)
        missed_count = len(category_rows - detected_rows)
        rows.append(
            {
                "poison_type": poison_type,
                "injected_rows": injected_count,
                "detected_rows": detected_count,
                "missed_rows": missed_count,
                "recall": safe_divide(detected_count, injected_count),
            }
        )

    result = pd.DataFrame(rows)
    if not result.empty:
        result = result.sort_values(
            by=["recall", "missed_rows", "poison_type"],
            ascending=[True, False, True],
        ).reset_index(drop=True)
    return result


def export_missed_cases(poison_df: pd.DataFrame, false_negative_rows: set[str], output_path: Path) -> None:
    """
    Export false negative cases for manual review.

    One readable line per missed case. We preserve issue-level entries here
    because qualitative review can benefit from seeing each missed injection.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    missed_df = poison_df[poison_df["row_key"].isin(false_negative_rows)].copy()

    with output_path.open("w", encoding="utf-8") as handle:
        handle.write("Missed Cases (False Negatives)\n")
        handle.write("=" * 40 + "\n\n")

        if missed_df.empty:
            handle.write("No missed cases.\n")
            return

        for _, row in missed_df.iterrows():
            handle.write(
                f"record_id={row.get('record_id', '')} | "
                f"row_index={row.get('row_index', '')} | "
                f"poison_type={row.get('poison_type', '')}\n"
            )


def print_overall_summary(metrics: dict[str, Any]) -> None:
    """Print a dissertation-ready overall evaluation summary."""
    print("\n" + "=" * 72)
    print("VAT AUDIT SYSTEM EVALUATION SUMMARY")
    print("=" * 72)
    print(f"True Positives (TP) : {metrics['tp']}")
    print(f"False Positives (FP): {metrics['fp']}")
    print(f"False Negatives (FN): {metrics['fn']}")
    print("-" * 72)
    print(f"Precision           : {metrics['precision']:.4f}")
    print(f"Recall              : {metrics['recall']:.4f}")
    print("=" * 72 + "\n")


def print_category_table(category_df: pd.DataFrame) -> None:
    """Print a clean per-category table suitable for screenshots."""
    print("Per-Category Recall Breakdown")
    print("-" * 72)

    if category_df.empty:
        print("No poisoning categories found.\n")
        return

    display_df = category_df.copy()
    display_df["recall"] = display_df["recall"].map(lambda value: f"{value:.4f}")
    print(display_df.to_string(index=False))
    print()


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate VAT audit system detections against a poisoning log "
            "using row-level matching."
        )
    )
    parser.add_argument(
        "--poisoning-log",
        type=Path,
        default=DEFAULT_POISONING_LOG,
        help=f"Path to poisoning log JSON (default: {DEFAULT_POISONING_LOG})",
    )
    parser.add_argument(
        "--issue-report",
        type=Path,
        default=DEFAULT_ISSUE_REPORT,
        help=f"Path to issue_report.csv (default: {DEFAULT_ISSUE_REPORT})",
    )
    parser.add_argument(
        "--missed-out",
        type=Path,
        default=DEFAULT_MISSED_OUT,
        help=f"Path to missed cases output file (default: {DEFAULT_MISSED_OUT})",
    )
    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_args()

    try:
        poison_df = parse_poisoning_log(args.poisoning_log)
        issue_df = parse_issue_report(args.issue_report)

        metrics = build_overall_metrics(poison_df, issue_df)
        category_df = build_category_breakdown(
            poison_df=poison_df,
            detected_rows=metrics["true_positive_rows"],
        )

        export_missed_cases(
            poison_df=poison_df,
            false_negative_rows=metrics["false_negative_rows"],
            output_path=args.missed_out,
        )

        print_overall_summary(metrics)
        print_category_table(category_df)
        print(f"Missed cases written to: {args.missed_out}")
        return 0

    except FileNotFoundError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    except KeyError as exc:
        print(f"[ERROR] Missing required data field: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"[ERROR] Unexpected failure: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
