"""Generate a reproducible synthetic VAT transaction dataset for realism checks.

The realism dataset is a supplemental evaluation asset. It is designed to make
the prototype look less toy-like by using a public retail-transaction substrate
and a simple, explicit VAT-generation logic. It does not replace the controlled
evaluation datasets used for rule-correctness and usefulness comparison.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_PATH = PROJECT_ROOT / "data" / "realism" / "uci_online_retail_like_seed.csv"
DEFAULT_CALIBRATION_PATH = PROJECT_ROOT / "data" / "realism" / "monthly_direction_calibration.csv"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output" / "runs" / "realism_dataset"

OUTPUT_COLUMNS = [
    "date",
    "invoice_reference",
    "description",
    "net_amount",
    "vat_amount",
    "gross_amount",
    "counterparty_ref",
    "document_reference",
    "category",
    "vat_rate",
    "vat_treatment",
    "country",
    "quantity",
    "unit_price",
    "month_key",
    "calibration_group",
    "direction_multiplier",
    "source_dataset",
]

SUMMARY_COLUMNS = [
    "source_dataset",
    "input_row_count",
    "output_row_count",
    "cancelled_row_count",
    "export_zero_rated_count",
    "standard_rated_count",
    "reduced_rated_count",
    "zero_rated_count",
    "exempt_count",
    "total_net_amount",
    "total_vat_amount",
    "total_gross_amount",
    "month_range",
]

COUNTRY_ZERO_RATE_OVERRIDES = {
    "france",
    "germany",
    "spain",
    "belgium",
    "netherlands",
    "portugal",
}

ZERO_RATED_KEYWORDS = ("book", "books", "cake cases", "food")
REDUCED_RATE_KEYWORDS = ("energy", "warmer", "heating")
EXEMPT_KEYWORDS = ("postage",)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a synthetic VAT realism dataset.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH, help="UCI-style retail transaction file.")
    parser.add_argument(
        "--calibration-file",
        type=Path,
        default=DEFAULT_CALIBRATION_PATH,
        help="Monthly direction calibration CSV used to shape transaction magnitudes.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory where the generated realism dataset and summary should be written.",
    )
    parser.add_argument(
        "--source-label",
        default="uci_online_retail_like_seed",
        help="Human-readable source label stored in the generated dataset metadata.",
    )
    return parser


def _load_transaction_substrate(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Transaction substrate not found: {path}")

    if path.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    return pd.read_csv(path)


def _load_calibration_table(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Calibration file not found: {path}")
    calibration_df = pd.read_csv(path)
    calibration_df["month_key"] = calibration_df["month_key"].astype(str)
    calibration_df["calibration_group"] = calibration_df["calibration_group"].astype(str)
    return calibration_df


def _clean_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def _normalise_country(value: object) -> str:
    return _clean_text(value).lower()


def _classify_vat_treatment(description: str, country: str) -> tuple[str, float, str]:
    description_lower = description.lower()

    if country in COUNTRY_ZERO_RATE_OVERRIDES:
        return "zero_rated_export", 0.00, "exports_zero"
    if any(keyword in description_lower for keyword in EXEMPT_KEYWORDS):
        return "exempt_proxy", 0.00, "goods_zero"
    if any(keyword in description_lower for keyword in ZERO_RATED_KEYWORDS):
        return "zero_rated_goods", 0.00, "goods_zero"
    if any(keyword in description_lower for keyword in REDUCED_RATE_KEYWORDS):
        return "reduced_rate_goods", 0.05, "goods_standard"
    return "standard_rate_goods", 0.20, "goods_standard"


def _derive_category(description: str, vat_treatment: str) -> str:
    description_lower = description.lower()
    if "postage" in description_lower:
        return "Logistics"
    if "cake" in description_lower or "teacup" in description_lower or "snack" in description_lower:
        return "Hospitality supplies"
    if "warmer" in description_lower or "light" in description_lower or "lantern" in description_lower:
        return "Home goods"
    if "jumbo bag" in description_lower or "holder" in description_lower:
        return "Retail goods"
    if vat_treatment == "zero_rated_export":
        return "Export sale"
    return "General merchandise"


def _build_document_reference(stock_code: object, description: str) -> str:
    stock_text = _clean_text(stock_code)
    stable_suffix = hashlib.sha1(description.encode("utf-8")).hexdigest()[:8].upper()
    return f"DOC-{stock_text or 'GEN'}-{stable_suffix}"


def _apply_monthly_calibration(dataframe: pd.DataFrame, calibration_df: pd.DataFrame) -> pd.DataFrame:
    calibrated_df = dataframe.merge(
        calibration_df[["month_key", "calibration_group", "multiplier"]],
        on=["month_key", "calibration_group"],
        how="left",
    )
    calibrated_df["multiplier"] = calibrated_df["multiplier"].fillna(1.0)
    calibrated_df["direction_multiplier"] = calibrated_df["multiplier"]
    calibrated_df["net_amount"] = (calibrated_df["net_amount"] * calibrated_df["direction_multiplier"]).round(2)
    calibrated_df["vat_amount"] = (calibrated_df["net_amount"] * calibrated_df["vat_rate"]).round(2)
    calibrated_df["gross_amount"] = (calibrated_df["net_amount"] + calibrated_df["vat_amount"]).round(2)
    return calibrated_df.drop(columns=["multiplier"])


def _build_realism_dataset(raw_df: pd.DataFrame, calibration_df: pd.DataFrame, source_label: str) -> pd.DataFrame:
    working_df = raw_df.copy()
    working_df["InvoiceDate"] = pd.to_datetime(working_df["InvoiceDate"], errors="coerce")
    working_df["Quantity"] = pd.to_numeric(working_df["Quantity"], errors="coerce")
    working_df["UnitPrice"] = pd.to_numeric(working_df["UnitPrice"], errors="coerce")
    working_df = working_df.dropna(subset=["InvoiceDate", "Quantity", "UnitPrice", "Description", "InvoiceNo"])
    working_df = working_df[working_df["UnitPrice"] > 0].copy()

    working_df["country_normalised"] = working_df["Country"].map(_normalise_country)
    working_df["description_clean"] = working_df["Description"].map(_clean_text)
    working_df["is_cancellation"] = working_df["InvoiceNo"].astype(str).str.upper().str.startswith("C") | (working_df["Quantity"] < 0)
    working_df["quantity_abs"] = working_df["Quantity"].abs()
    working_df["base_amount"] = (working_df["quantity_abs"] * working_df["UnitPrice"]).round(2)
    working_df["signed_base_amount"] = working_df.apply(
        lambda row: -row["base_amount"] if row["is_cancellation"] else row["base_amount"],
        axis=1,
    )

    vat_info = working_df.apply(
        lambda row: _classify_vat_treatment(row["description_clean"], row["country_normalised"]),
        axis=1,
        result_type="expand",
    )
    vat_info.columns = ["vat_treatment", "vat_rate", "calibration_group"]
    working_df = pd.concat([working_df, vat_info], axis=1)

    working_df["category"] = working_df.apply(
        lambda row: _derive_category(row["description_clean"], row["vat_treatment"]),
        axis=1,
    )
    working_df["month_key"] = working_df["InvoiceDate"].dt.strftime("%Y-%m")
    working_df["net_amount"] = working_df["signed_base_amount"]
    working_df["vat_amount"] = (working_df["net_amount"] * working_df["vat_rate"]).round(2)
    working_df["gross_amount"] = (working_df["net_amount"] + working_df["vat_amount"]).round(2)
    working_df = _apply_monthly_calibration(working_df, calibration_df)

    output_df = pd.DataFrame(
        {
            "date": working_df["InvoiceDate"].dt.strftime("%d/%m/%Y"),
            "invoice_reference": working_df["InvoiceNo"].astype(str),
            "description": working_df["description_clean"],
            "net_amount": working_df["net_amount"],
            "vat_amount": working_df["vat_amount"],
            "gross_amount": working_df["gross_amount"],
            "counterparty_ref": working_df["Country"].astype(str),
            "document_reference": working_df.apply(
                lambda row: _build_document_reference(row["StockCode"], row["description_clean"]),
                axis=1,
            ),
            "category": working_df["category"],
            "vat_rate": working_df["vat_rate"],
            "vat_treatment": working_df["vat_treatment"],
            "country": working_df["Country"].astype(str),
            "quantity": working_df["Quantity"],
            "unit_price": working_df["UnitPrice"],
            "month_key": working_df["month_key"],
            "calibration_group": working_df["calibration_group"],
            "direction_multiplier": working_df["direction_multiplier"],
            "source_dataset": source_label,
        }
    )
    return output_df.reindex(columns=OUTPUT_COLUMNS)


def _build_summary(output_df: pd.DataFrame, input_row_count: int, source_label: str) -> pd.DataFrame:
    month_values = output_df["month_key"].dropna().astype(str).sort_values().tolist()
    month_range = ""
    if month_values:
        month_range = f"{month_values[0]} to {month_values[-1]}"

    summary_row = {
        "source_dataset": source_label,
        "input_row_count": input_row_count,
        "output_row_count": len(output_df),
        "cancelled_row_count": int(output_df["invoice_reference"].astype(str).str.upper().str.startswith("C").sum()),
        "export_zero_rated_count": int(output_df["vat_treatment"].astype(str).eq("zero_rated_export").sum()),
        "standard_rated_count": int(output_df["vat_rate"].eq(0.20).sum()),
        "reduced_rated_count": int(output_df["vat_rate"].eq(0.05).sum()),
        "zero_rated_count": int((output_df["vat_rate"].eq(0.00) & output_df["vat_treatment"].ne("exempt_proxy")).sum()),
        "exempt_count": int(output_df["vat_treatment"].astype(str).eq("exempt_proxy").sum()),
        "total_net_amount": round(float(output_df["net_amount"].sum()), 2),
        "total_vat_amount": round(float(output_df["vat_amount"].sum()), 2),
        "total_gross_amount": round(float(output_df["gross_amount"].sum()), 2),
        "month_range": month_range,
    }
    return pd.DataFrame([summary_row], columns=SUMMARY_COLUMNS)


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    raw_df = _load_transaction_substrate(args.input)
    calibration_df = _load_calibration_table(args.calibration_file)
    output_df = _build_realism_dataset(raw_df, calibration_df, args.source_label)
    summary_df = _build_summary(output_df, len(raw_df), args.source_label)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    dataset_output_path = args.output_dir / "synthetic_vat_realism_dataset.csv"
    summary_output_path = args.output_dir / "synthetic_vat_realism_summary.csv"
    metadata_output_path = args.output_dir / "synthetic_vat_realism_metadata.json"

    output_df.to_csv(dataset_output_path, index=False)
    summary_df.to_csv(summary_output_path, index=False)
    metadata_output = {
        "source_input": str(args.input),
        "calibration_file": str(args.calibration_file),
        "source_label": args.source_label,
        "main_purpose": "Supplemental realism dataset for evaluation, not replacement for controlled usefulness validation.",
        "generation_rules": {
            "country_zero_rate_overrides": sorted(COUNTRY_ZERO_RATE_OVERRIDES),
            "zero_rated_keywords": list(ZERO_RATED_KEYWORDS),
            "reduced_rate_keywords": list(REDUCED_RATE_KEYWORDS),
            "exempt_keywords": list(EXEMPT_KEYWORDS),
            "cancellation_rule": "InvoiceNo starting with C or negative Quantity produces signed negative reversal rows.",
        },
        "output_files": {
            "dataset": str(dataset_output_path),
            "summary": str(summary_output_path),
        },
    }
    metadata_output_path.write_text(json.dumps(metadata_output, indent=2), encoding="utf-8")

    print("Synthetic VAT realism dataset written:")
    print(dataset_output_path)
    print(summary_output_path)
    print(metadata_output_path)


if __name__ == "__main__":
    main()
