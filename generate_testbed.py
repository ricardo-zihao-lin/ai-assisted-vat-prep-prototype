"""
Create a controlled VAT evaluation testbed from public seed datasets.

Inputs:
  data/public_raw/raw_sales_seed.csv
  data/public_raw/raw_purchase_seed.csv

Outputs:
  data/evaluation/evaluation_testbed_clean.csv
  data/evaluation/evaluation_testbed_poisoned.csv
  data/evaluation/poisoning_log.json

Usage:
  python generate_testbed.py
"""

from __future__ import annotations

import json
import random
import warnings
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")


RANDOM_SEED = 42
rng = np.random.default_rng(RANDOM_SEED)
random.seed(RANDOM_SEED)

QUARTER_START = date(2025, 1, 1)
QUARTER_END = date(2025, 3, 31)

TARGET_SALES_ROWS = 400
TARGET_PURCHASE_ROWS = 200

VAT_WEIGHTS = [0.75, 0.15, 0.10]
VAT_CODES = ["SR", "ZR", "EXEMPT"]
VAT_RATES = {"SR": 0.20, "ZR": 0.00, "EXEMPT": 0.00}

FRAC_VAT_MATH_ERR = 0.04
FRAC_GROSS_ERR = 0.03
FRAC_MISSING = 0.04
FRAC_INVALID_NUM = 0.025
FRAC_INVALID_DATE = 0.025
N_DUPLICATE_SEEDS = 8
N_OUTLIER_ROWS = 5
N_SEMANTIC_RISK = 10

SEMANTIC_RISK_DESCS = [
    "Client Hospitality Lunch",
    "Staff Party Entertainment",
    "Director's Gym Membership",
    "Team Building Away Day",
    "Corporate Box - Premier League",
    "Client Golf Day",
    "Christmas Party - All Staff",
    "Executive Dining - Board Dinner",
    "Spa Vouchers - Client Gift",
    "Employee Wellness Retreat",
]

MALFORMED_DATES = [
    "32/01/2025",
    "2025-13-01",
    "not-a-date",
    "01-2025",
    "2025/99/99",
    "Jan 2025",
    "Q1-2025",
    "00/00/0000",
]

MALFORMED_NUMERICS = ["N/A", "#REF!", "TBC", "??", "-", "nil", "GBPerr", "VOID"]

ROOT = Path(__file__).resolve().parent
INPUT_SALES = ROOT / "data" / "public_raw" / "raw_sales_seed.csv"
INPUT_PURCHASE = ROOT / "data" / "public_raw" / "raw_purchase_seed.csv"
OUTPUT_DIR = ROOT / "data" / "evaluation"
OUT_CLEAN = OUTPUT_DIR / "evaluation_testbed_clean.csv"
OUT_POISONED = OUTPUT_DIR / "evaluation_testbed_poisoned.csv"
OUT_LOG = OUTPUT_DIR / "poisoning_log.json"


def generate_quarter_dates(n: int, seed: int = RANDOM_SEED) -> list[str]:
    """Return quarter dates with weekdays weighted above weekends."""
    rng_local = np.random.default_rng(seed)
    total_days = (QUARTER_END - QUARTER_START).days + 1
    all_dates = [QUARTER_START + timedelta(days=i) for i in range(total_days)]
    weights = [4 if d.weekday() < 5 else 1 for d in all_dates]
    probabilities = np.array(weights, dtype=float)
    probabilities /= probabilities.sum()
    chosen = rng_local.choice(len(all_dates), size=n, replace=True, p=probabilities)
    return [all_dates[i].strftime("%Y-%m-%d") for i in chosen]


def assign_vat_codes(n: int) -> tuple[list[str], list[float]]:
    """Draw VAT codes from the configured mix and return codes and rates."""
    codes = random.choices(VAT_CODES, weights=VAT_WEIGHTS, k=n)
    rates = [VAT_RATES[code] for code in codes]
    return codes, rates


def safe_float(value: object, fallback: float = 0.0) -> float:
    """Coerce a value to float and fall back when conversion fails."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def log_entry(
    record_id: str,
    row_index: int,
    poison_type: str,
    field_changed: str,
    original_value: object,
    new_value: object,
    source_type: str,
) -> dict[str, object]:
    """Build a poisoning audit record."""
    return {
        "record_id": record_id,
        "row_index": int(row_index),
        "poison_type": poison_type,
        "field_changed": field_changed,
        "original_value": str(original_value),
        "new_value": str(new_value),
        "source_type": source_type,
    }


def load_sales(path: Path, n: int) -> pd.DataFrame:
    """Load and canonicalise UK retail sales seed rows."""
    print(f"  Loading sales from {path}")
    df = pd.read_csv(path, encoding="latin-1", on_bad_lines="skip", dtype={"Customer ID": str})

    df = df[df["Country"] == "United Kingdom"].copy()
    df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce")
    df["Price"] = pd.to_numeric(df["Price"], errors="coerce")
    df = df[(df["Quantity"] > 0) & (df["Price"] > 0)].dropna(
        subset=["Quantity", "Price", "Description"]
    )

    df = df.sample(n=min(n, len(df)), random_state=RANDOM_SEED).reset_index(drop=True)
    row_count = len(df)
    return pd.DataFrame(
        {
            "source_type": ["sale"] * row_count,
            "reference_id": df["Invoice"].astype(str).values,
            "description": df["Description"].str.strip().values,
            "net_amount": (df["Quantity"] * df["Price"]).round(2).values,
            "counterparty_ref": df["Customer ID"].fillna("UNKNOWN").astype(str).values,
            "country": ["United Kingdom"] * row_count,
            "category": ["sales"] * row_count,
        }
    )


def load_purchases(path: Path, n: int) -> pd.DataFrame:
    """Load and canonicalise purchase ledger seed rows."""
    print(f"  Loading purchases from {path}")
    df = pd.read_csv(path, encoding="latin-1", on_bad_lines="skip")
    df.columns = df.columns.str.strip()

    rename_map: dict[str, str] = {}
    for column in df.columns:
        lowered = column.lower()
        if lowered in ("inv_id", "inv id"):
            rename_map[column] = "Inv_ID"
        elif lowered in ("vendor_code", "vendor code"):
            rename_map[column] = "Vendor_Code"
        elif lowered in ("inv_amt", "inv amt"):
            rename_map[column] = "Inv_Amt"
        elif lowered in ("item_description", "item description"):
            rename_map[column] = "Item_Description"
    df = df.rename(columns=rename_map)

    df["Inv_Amt"] = pd.to_numeric(df["Inv_Amt"], errors="coerce")
    df = df.dropna(subset=["Inv_Amt", "Item_Description"])
    df = df[df["Inv_Amt"] > 0]
    df = df.sample(n=min(n, len(df)), random_state=RANDOM_SEED + 1).reset_index(drop=True)

    row_count = len(df)
    return pd.DataFrame(
        {
            "source_type": ["purchase"] * row_count,
            "reference_id": df["Inv_ID"].astype(str).values,
            "description": df["Item_Description"].str.strip().values,
            "net_amount": df["Inv_Amt"].round(2).values,
            "counterparty_ref": df["Vendor_Code"].astype(str).values,
            "country": ["United Kingdom"] * row_count,
            "category": ["purchases"] * row_count,
        }
    )


def build_clean_dataset(sales_partial: pd.DataFrame, purchases_partial: pd.DataFrame) -> pd.DataFrame:
    """Combine sales and purchases into a clean canonical baseline."""
    print("  Building clean baseline")
    combined = pd.concat([sales_partial, purchases_partial], ignore_index=True)
    row_count = len(combined)

    combined["date"] = generate_quarter_dates(row_count)
    codes, rates = assign_vat_codes(row_count)
    combined["vat_code"] = codes
    combined["vat_rate"] = rates
    combined["vat_amount"] = (combined["net_amount"] * combined["vat_rate"]).round(2)
    combined["gross_amount"] = (combined["net_amount"] + combined["vat_amount"]).round(2)
    combined.insert(0, "record_id", [f"REC-{i + 1:05d}" for i in range(row_count)])

    columns = [
        "record_id",
        "source_type",
        "date",
        "reference_id",
        "description",
        "net_amount",
        "vat_amount",
        "gross_amount",
        "counterparty_ref",
        "country",
        "category",
        "vat_code",
    ]
    return combined[columns].copy()


def pick_indices(df: pd.DataFrame, frac: float, mask: pd.Series | None = None) -> list[int]:
    """Pick positional indices to poison, optionally using a filtered mask."""
    candidates = df.index[mask].tolist() if mask is not None else df.index.tolist()
    if not candidates:
        return []
    count = max(1, int(len(df) * frac))
    count = min(count, len(candidates))
    return random.sample(candidates, count)


def poison_A_vat_math(df: pd.DataFrame, log: list[dict[str, object]]) -> None:
    """Inject incorrect VAT amounts on a fraction of standard-rated rows."""
    idxs = pick_indices(df, FRAC_VAT_MATH_ERR, mask=df["vat_code"] == "SR")
    for i in idxs:
        original = df.at[i, "vat_amount"]
        new_value = round(original * random.uniform(0.5, 1.5) + random.uniform(-5, 5), 2)
        if new_value == original:
            new_value = round(original + 1.23, 2)
        df.at[i, "vat_amount"] = new_value
        log.append(
            log_entry(
                df.at[i, "record_id"],
                i,
                "vat_math_inconsistency",
                "vat_amount",
                original,
                new_value,
                df.at[i, "source_type"],
            )
        )


def poison_B_gross(df: pd.DataFrame, log: list[dict[str, object]]) -> None:
    """Inject gross totals that no longer reconcile to net plus VAT."""
    idxs = pick_indices(df, FRAC_GROSS_ERR)
    for i in idxs:
        original = df.at[i, "gross_amount"]
        delta = random.choice([-1, 1]) * round(random.uniform(0.5, 20.0), 2)
        new_value = round(original + delta, 2)
        df.at[i, "gross_amount"] = new_value
        log.append(
            log_entry(
                df.at[i, "record_id"],
                i,
                "gross_inconsistency",
                "gross_amount",
                original,
                new_value,
                df.at[i, "source_type"],
            )
        )


def poison_C_missing(df: pd.DataFrame, log: list[dict[str, object]]) -> None:
    """Blank out required descriptive or date fields."""
    idxs = pick_indices(df, FRAC_MISSING)
    fields = ["description", "counterparty_ref", "date"]
    for i in idxs:
        field = random.choice(fields)
        original = df.at[i, field]
        df.at[i, field] = np.nan
        log.append(
            log_entry(
                df.at[i, "record_id"],
                i,
                "missing_value",
                field,
                original,
                np.nan,
                df.at[i, "source_type"],
            )
        )


def poison_D_invalid_numeric(df: pd.DataFrame, log: list[dict[str, object]]) -> None:
    """Replace numeric values with malformed strings."""
    fields = ["net_amount", "vat_amount"]
    for field in fields:
        df[field] = df[field].astype(object)

    idxs = pick_indices(df, FRAC_INVALID_NUM)
    for i in idxs:
        field = random.choice(fields)
        original = df.at[i, field]
        new_value = random.choice(MALFORMED_NUMERICS)
        df.at[i, field] = new_value
        log.append(
            log_entry(
                df.at[i, "record_id"],
                i,
                "invalid_numeric",
                field,
                original,
                new_value,
                df.at[i, "source_type"],
            )
        )


def poison_E_invalid_date(df: pd.DataFrame, log: list[dict[str, object]]) -> None:
    """Replace valid dates with malformed date strings."""
    df["date"] = df["date"].astype(object)
    idxs = pick_indices(df, FRAC_INVALID_DATE)
    for i in idxs:
        original = df.at[i, "date"]
        new_value = random.choice(MALFORMED_DATES)
        df.at[i, "date"] = new_value
        log.append(
            log_entry(
                df.at[i, "record_id"],
                i,
                "invalid_date_format",
                "date",
                original,
                new_value,
                df.at[i, "source_type"],
            )
        )


def poison_F_duplicates(df: pd.DataFrame, log: list[dict[str, object]]) -> pd.DataFrame:
    """Append exact and near-duplicate rows."""
    seed_idxs = random.sample(list(df.index), min(N_DUPLICATE_SEEDS, len(df)))
    duplicates = []

    for rank, i in enumerate(seed_idxs):
        dup = df.loc[i].copy()
        original_net = safe_float(dup["net_amount"])
        if rank % 2 == 1:
            new_net = round(original_net + 0.01, 2)
            dup["net_amount"] = new_net
            dup["gross_amount"] = round(new_net + safe_float(dup["vat_amount"]), 2)
            field_changed = "net_amount"
            original_value = original_net
            new_value = new_net
        else:
            field_changed = "(none - exact copy)"
            original_value = "(original row)"
            new_value = "(exact duplicate)"

        record_id = f"REC-DUP-{rank + 1:04d}"
        dup["record_id"] = record_id
        duplicates.append(dup)
        log.append(
            log_entry(
                record_id,
                len(df) + rank,
                "duplicate",
                field_changed,
                original_value,
                new_value,
                dup["source_type"],
            )
        )

    return pd.concat([df, pd.DataFrame(duplicates)], ignore_index=True)


def poison_G_outliers(df: pd.DataFrame, log: list[dict[str, object]]) -> None:
    """Inflate one transaction per eligible counterparty into an outlier."""
    counts = df["counterparty_ref"].value_counts()
    eligible = counts[counts >= 3].index.tolist()
    if not eligible:
        return

    chosen_counterparties = random.sample(eligible, min(N_OUTLIER_ROWS, len(eligible)))
    for counterparty in chosen_counterparties:
        cp_idxs = df.index[df["counterparty_ref"] == counterparty].tolist()
        pick_i = random.choice(cp_idxs)

        original_net = safe_float(df.at[pick_i, "net_amount"])
        median = df.loc[cp_idxs, "net_amount"].apply(safe_float).median()
        new_net = round(median * random.uniform(10, 20), 2)
        new_vat = round(new_net * VAT_RATES.get(df.at[pick_i, "vat_code"], 0.0), 2)
        new_gross = round(new_net + new_vat, 2)

        df.at[pick_i, "net_amount"] = new_net
        df.at[pick_i, "vat_amount"] = new_vat
        df.at[pick_i, "gross_amount"] = new_gross
        log.append(
            log_entry(
                df.at[pick_i, "record_id"],
                pick_i,
                "group_outlier_amount",
                "net_amount",
                original_net,
                new_net,
                df.at[pick_i, "source_type"],
            )
        )


def poison_H_semantic_risk(df: pd.DataFrame, log: list[dict[str, object]]) -> None:
    """Swap descriptions to VAT-sensitive hospitality and entertainment cases."""
    purchase_idxs = df.index[df["source_type"] == "purchase"].tolist()
    pool = purchase_idxs if len(purchase_idxs) >= N_SEMANTIC_RISK else list(df.index)
    idxs = random.sample(pool, min(N_SEMANTIC_RISK, len(pool)))

    for rank, i in enumerate(idxs):
        original = df.at[i, "description"]
        new_value = SEMANTIC_RISK_DESCS[rank % len(SEMANTIC_RISK_DESCS)]
        df.at[i, "description"] = new_value
        log.append(
            log_entry(
                df.at[i, "record_id"],
                i,
                "semantic_risk",
                "description",
                original,
                new_value,
                df.at[i, "source_type"],
            )
        )


def main() -> None:
    """Generate clean and poisoned evaluation datasets plus an audit log."""
    print("\n=== generate_testbed.py ===\n")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("[1/5] Ingesting seed data")
    if not INPUT_SALES.exists():
        raise FileNotFoundError(f"Missing input: {INPUT_SALES}")
    if not INPUT_PURCHASE.exists():
        raise FileNotFoundError(f"Missing input: {INPUT_PURCHASE}")

    sales_partial = load_sales(INPUT_SALES, TARGET_SALES_ROWS)
    purchase_partial = load_purchases(INPUT_PURCHASE, TARGET_PURCHASE_ROWS)

    print("[2/5] Building clean baseline")
    clean_df = build_clean_dataset(sales_partial, purchase_partial)
    clean_df.to_csv(OUT_CLEAN, index=False)
    print(f"  Wrote {OUT_CLEAN} ({len(clean_df)} rows)")

    print("[3/5] Injecting controlled issues")
    poisoned_df = clean_df.copy(deep=True)
    poison_log: list[dict[str, object]] = []
    poison_A_vat_math(poisoned_df, poison_log)
    poison_B_gross(poisoned_df, poison_log)
    poison_C_missing(poisoned_df, poison_log)
    poison_D_invalid_numeric(poisoned_df, poison_log)
    poison_E_invalid_date(poisoned_df, poison_log)
    poisoned_df = poison_F_duplicates(poisoned_df, poison_log)
    poison_G_outliers(poisoned_df, poison_log)
    poison_H_semantic_risk(poisoned_df, poison_log)

    print("[4/5] Writing poisoned dataset")
    poisoned_df.to_csv(OUT_POISONED, index=False)
    print(f"  Wrote {OUT_POISONED} ({len(poisoned_df)} rows)")

    print("[5/5] Writing poisoning log")
    with OUT_LOG.open("w", encoding="utf-8") as handle:
        json.dump(poison_log, handle, indent=2, ensure_ascii=False, default=str)
    print(f"  Wrote {OUT_LOG} ({len(poison_log)} entries)")

    type_counts: dict[str, int] = {}
    for entry in poison_log:
        poison_type = str(entry["poison_type"])
        type_counts[poison_type] = type_counts.get(poison_type, 0) + 1

    print("\nPoison type summary:")
    for poison_type, count in sorted(type_counts.items()):
        print(f"  {poison_type:<30} {count:>4}")

    print("\nDone.\n")


if __name__ == "__main__":
    main()
