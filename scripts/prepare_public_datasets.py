"""Prepare adapted public datasets for the local VAT prototype schema."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "public_raw"
ADAPTED_DIR = BASE_DIR / "data" / "public_adapted"
OUTPUT_COLUMNS = ["date", "description", "net_amount", "vat_amount", "category"]
READ_ENCODINGS = ("utf-8", "cp1252", "latin1")


def _load_csv(path: Path) -> pd.DataFrame:
    """Load a CSV using a small encoding fallback list."""
    last_error: Exception | None = None
    for encoding in READ_ENCODINGS:
        try:
            dataframe = pd.read_csv(path, encoding=encoding)
            dataframe.columns = [str(column).strip() for column in dataframe.columns]
            return dataframe
        except UnicodeDecodeError as error:
            last_error = error

    raise ValueError(f"Unable to read CSV file with supported encodings: {path}") from last_error


def _require_column(dataframe: pd.DataFrame, column_name: str, dataset_name: str) -> str:
    """Return the requested column name or fail with a helpful message."""
    if column_name not in dataframe.columns:
        raise ValueError(
            f"{dataset_name} is missing expected column '{column_name}'. "
            f"Available columns: {list(dataframe.columns)}"
        )
    return column_name


def _first_present_column(dataframe: pd.DataFrame, candidates: list[str], dataset_name: str, field_name: str) -> str:
    """Return the first available candidate column for a mapped field."""
    for candidate in candidates:
        if candidate in dataframe.columns:
            return candidate

    raise ValueError(
        f"{dataset_name} is missing a source column for '{field_name}'. "
        f"Expected one of: {candidates}. Available columns: {list(dataframe.columns)}"
    )


def _to_numeric_series(series: pd.Series) -> pd.Series:
    """Parse numeric values conservatively without inferring missing values."""
    cleaned = (
        series.astype(str)
        .str.strip()
        .replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})
    )
    return pd.to_numeric(cleaned, errors="coerce")


def _prepare_hmrc() -> Path:
    """Adapt the HMRC raw dataset to the prototype schema."""
    dataset_name = "hmrc_jan_2026.csv"
    dataframe = _load_csv(RAW_DIR / dataset_name)

    date_column = _require_column(dataframe, "Date", dataset_name)
    description_column = _require_column(dataframe, "Description", dataset_name)
    amount_column = _require_column(dataframe, "Amount", dataset_name)
    category_column = _first_present_column(
        dataframe,
        ["Expense type", "Expense area"],
        dataset_name,
        "category",
    )

    adapted = pd.DataFrame(
        {
            "date": dataframe[date_column],
            "description": dataframe[description_column],
            "net_amount": _to_numeric_series(dataframe[amount_column]),
            "vat_amount": 0.00,
            "category": dataframe[category_column],
        }
    )

    output_path = ADAPTED_DIR / "hmrc_jan_2026_adapted.csv"
    adapted.to_csv(output_path, index=False)
    return output_path


def _prepare_dft() -> Path:
    """Adapt the DfT raw dataset to the prototype schema."""
    dataset_name = "dft_mar_2025.csv"
    dataframe = _load_csv(RAW_DIR / dataset_name)

    date_column = _require_column(dataframe, "Date", dataset_name)
    description_column = _require_column(dataframe, "Item Text", dataset_name)
    amount_column = _require_column(dataframe, "£", dataset_name)
    category_column = _require_column(dataframe, "Expense Type", dataset_name)

    amount_values = (
        dataframe[amount_column]
        .astype(str)
        .str.replace("£", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.strip()
        .replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})
    )

    adapted = pd.DataFrame(
        {
            "date": dataframe[date_column],
            "description": dataframe[description_column],
            "net_amount": pd.to_numeric(amount_values, errors="coerce"),
            "vat_amount": 0.00,
            "category": dataframe[category_column],
        }
    )

    output_path = ADAPTED_DIR / "dft_mar_2025_adapted.csv"
    adapted.to_csv(output_path, index=False)
    return output_path


def _prepare_dwp() -> Path:
    """Adapt the DWP EPCS raw dataset to the prototype schema."""
    dataset_name = "dwp_epcs_july_2025.csv"
    dataframe = _load_csv(RAW_DIR / dataset_name)

    date_column = _require_column(dataframe, "Posting Date", dataset_name)
    description_column = _require_column(dataframe, "Description", dataset_name)
    amount_column = _require_column(dataframe, "FIN.Transaction Amount", dataset_name)
    category_column = _first_present_column(
        dataframe,
        [
            "MCH.Merchant Category Code (MCC)",
            "MCH.Merchant Name",
        ],
        dataset_name,
        "category",
    )

    filtered_dataframe = dataframe[dataframe[date_column].astype(str).str.contains("/", regex=False)].copy()

    adapted = pd.DataFrame(
        {
            "date": filtered_dataframe[date_column],
            "description": filtered_dataframe[description_column],
            "net_amount": _to_numeric_series(filtered_dataframe[amount_column]),
            "vat_amount": 0.00,
            "category": filtered_dataframe[category_column],
        }
    )

    output_path = ADAPTED_DIR / "dwp_epcs_july_2025_adapted.csv"
    adapted.to_csv(output_path, index=False)
    return output_path


def main() -> None:
    """Generate all adapted public datasets."""
    ADAPTED_DIR.mkdir(parents=True, exist_ok=True)

    output_paths = [
        _prepare_hmrc(),
        _prepare_dft(),
        _prepare_dwp(),
    ]

    print("Adapted public datasets written:")
    for output_path in output_paths:
        print(output_path)


if __name__ == "__main__":
    main()
