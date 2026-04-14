"""Conservative raw-upload preparation for the local VAT prototype.

This module maps near-canonical source files into the small schema expected by
the existing prototype pipeline. The goal is to support simple, deterministic
header adaptation without introducing fuzzy matching or silent data invention.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

CANONICAL_COLUMNS = ["date", "description", "net_amount", "vat_amount", "category"]
REQUIRED_COLUMNS = ["date", "description", "net_amount", "vat_amount"]

PREPARATION_STATUS_CANONICAL = "canonical"
PREPARATION_STATUS_MAPPED = "mapped"
PREPARATION_STATUS_UNSUPPORTED = "unsupported"

HEADER_ALIASES = {
    "date": ["transaction_date", "invoice_date"],
    "description": ["details", "narrative"],
    "net_amount": ["net", "amount_ex_vat", "amount"],
    "vat_amount": ["vat", "tax_amount"],
    "category": ["type"],
}


@dataclass(frozen=True)
class PreparationResult:
    """Structured result for a conservative input-preparation attempt."""

    status: str
    prepared_dataframe: pd.DataFrame | None
    canonical_columns: tuple[str, ...]
    missing_required_fields: tuple[str, ...]
    mapping: dict[str, str | None]
    message: str


def _resolve_source_column(
    dataframe: pd.DataFrame,
    canonical_field: str,
    used_columns: set[str],
) -> str | None:
    """Resolve one canonical field using exact match first, then aliases."""
    if canonical_field in dataframe.columns and canonical_field not in used_columns:
        return canonical_field

    for alias in HEADER_ALIASES.get(canonical_field, []):
        if alias in dataframe.columns and alias not in used_columns:
            return alias

    return None


def prepare_input_dataframe(dataframe: pd.DataFrame) -> PreparationResult:
    """Prepare a raw dataframe for the existing prototype pipeline.

    The preparation rules are intentionally conservative:
    - exact canonical headers are preferred
    - a small alias list supports near-canonical uploads
    - required fields must be identified explicitly
    - category remains optional and is left blank when absent
    """
    mapping: dict[str, str | None] = {}
    used_columns: set[str] = set()

    for canonical_field in CANONICAL_COLUMNS:
        source_column = _resolve_source_column(dataframe, canonical_field, used_columns)
        mapping[canonical_field] = source_column
        if source_column is not None:
            used_columns.add(source_column)

    missing_required_fields = tuple(
        canonical_field for canonical_field in REQUIRED_COLUMNS if mapping.get(canonical_field) is None
    )
    if missing_required_fields:
        missing_text = ", ".join(missing_required_fields)
        return PreparationResult(
            status=PREPARATION_STATUS_UNSUPPORTED,
            prepared_dataframe=None,
            canonical_columns=tuple(CANONICAL_COLUMNS),
            missing_required_fields=missing_required_fields,
            mapping=mapping,
            message=f"Required fields could not be identified: {missing_text}.",
        )

    prepared_columns: dict[str, pd.Series] = {}
    for canonical_field in CANONICAL_COLUMNS:
        source_column = mapping.get(canonical_field)
        if source_column is None:
            # Category remains intentionally blank rather than invented.
            prepared_columns[canonical_field] = pd.Series([""] * len(dataframe), index=dataframe.index, dtype="object")
        else:
            prepared_columns[canonical_field] = dataframe[source_column]

    prepared_dataframe = pd.DataFrame(prepared_columns, index=dataframe.index).reindex(columns=CANONICAL_COLUMNS)

    if all(mapping.get(column_name) == column_name for column_name in CANONICAL_COLUMNS):
        return PreparationResult(
            status=PREPARATION_STATUS_CANONICAL,
            prepared_dataframe=prepared_dataframe,
            canonical_columns=tuple(CANONICAL_COLUMNS),
            missing_required_fields=(),
            mapping=mapping,
            message="Input already matched the canonical schema.",
        )

    message = "Input columns were mapped to the canonical schema."
    if mapping.get("category") is None:
        message += " Category was not identified and was left blank."

    return PreparationResult(
        status=PREPARATION_STATUS_MAPPED,
        prepared_dataframe=prepared_dataframe,
        canonical_columns=tuple(CANONICAL_COLUMNS),
        missing_required_fields=(),
        mapping=mapping,
        message=message,
    )
