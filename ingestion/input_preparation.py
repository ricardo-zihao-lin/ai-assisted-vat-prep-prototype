"""Conservative raw-upload preparation for the local VAT prototype.

This module maps near-canonical source files into the small schema expected by
the existing prototype pipeline. The goal is to support simple, deterministic
header adaptation without introducing fuzzy matching or silent data invention.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

CANONICAL_COLUMNS = [
    "date",
    "invoice_reference",
    "description",
    "net_amount",
    "vat_amount",
    "gross_amount",
    "counterparty_ref",
    "document_reference",
    "category",
]
REQUIRED_COLUMNS = ["date", "description", "net_amount", "vat_amount"]

PREPARATION_STATUS_CANONICAL = "canonical"
PREPARATION_STATUS_MAPPED = "mapped"
PREPARATION_STATUS_UNSUPPORTED = "unsupported"

HEADER_ALIASES = {
    "date": ["transaction_date", "invoice_date"],
    "invoice_reference": ["invoice_no", "invoice_number", "invoice_id"],
    "description": ["details", "narrative"],
    "net_amount": ["net", "amount_ex_vat", "amount"],
    "vat_amount": ["vat", "tax_amount"],
    "gross_amount": ["gross", "total_amount", "amount_inc_vat"],
    "counterparty_ref": ["supplier_ref", "customer_ref", "counterparty", "supplier", "customer", "client_ref"],
    "document_reference": ["document_id", "doc_ref", "evidence_reference", "receipt_reference"],
    "category": ["type"],
}

INPUT_DIAGNOSTIC_COLUMNS = [
    "canonical_field",
    "field_role",
    "field_status",
    "mapping_type",
    "source_column",
    "candidate_columns",
    "accepted_aliases",
    "repair_guidance",
    "preparation_status",
    "preparation_message",
    "missing_required_fields",
]


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


def _collect_candidate_columns(dataframe: pd.DataFrame, canonical_field: str) -> tuple[str, ...]:
    """Return source columns that match the canonical field directly or through accepted aliases."""
    candidates: list[str] = []
    if canonical_field in dataframe.columns:
        candidates.append(canonical_field)

    for alias in HEADER_ALIASES.get(canonical_field, []):
        if alias in dataframe.columns and alias not in candidates:
            candidates.append(alias)
    return tuple(candidates)


def _format_column_list(columns: tuple[str, ...]) -> str:
    """Render a compact CSV-friendly list of column names."""
    return ", ".join(columns)


def _build_repair_guidance(
    canonical_field: str,
    *,
    source_column: str | None,
    candidate_columns: tuple[str, ...],
    is_required: bool,
) -> str:
    """Create a short actionable note for unsupported or mapped fields."""
    if source_column is not None:
        if source_column == canonical_field:
            return f"The `{canonical_field}` column is already aligned with the canonical schema."
        return (
            f"The `{canonical_field}` field was mapped from `{source_column}`. "
            f"Keep that heading or rename it to `{canonical_field}` for future runs."
        )

    if is_required:
        accepted_aliases = HEADER_ALIASES.get(canonical_field, ())
        if accepted_aliases:
            return (
                f"Add or rename a column to `{canonical_field}` or one of these accepted aliases: "
                f"{_format_column_list(tuple(accepted_aliases))}."
            )
        return f"Add a `{canonical_field}` column before rerunning the analysis."

    if candidate_columns:
        return (
            f"The `{canonical_field}` field is optional and no source column was mapped to it. "
            f"If you want to use it, rename one of the candidate columns to `{canonical_field}`."
        )

    return f"The `{canonical_field}` field is optional and can be left blank for this prototype."


def build_input_diagnostics(
    dataframe: pd.DataFrame,
    preparation_result: PreparationResult,
) -> pd.DataFrame:
    """Build a compact CSV-ready diagnostic table for unsupported input files."""
    missing_required_fields = set(preparation_result.missing_required_fields)
    mapping = preparation_result.mapping
    rows: list[dict[str, str]] = []

    for canonical_field in CANONICAL_COLUMNS:
        source_column = mapping.get(canonical_field)
        candidate_columns = _collect_candidate_columns(dataframe, canonical_field)
        accepted_aliases = tuple(HEADER_ALIASES.get(canonical_field, ()))
        field_role = "required" if canonical_field in REQUIRED_COLUMNS else "optional"

        if source_column is not None:
            field_status = "mapped"
            mapping_type = "exact" if source_column == canonical_field else "alias"
        elif canonical_field in missing_required_fields:
            field_status = "missing_required"
            mapping_type = "missing"
        else:
            field_status = "not_mapped"
            mapping_type = "unmapped_optional"

        rows.append(
            {
                "canonical_field": canonical_field,
                "field_role": field_role,
                "field_status": field_status,
                "mapping_type": mapping_type,
                "source_column": source_column or "",
                "candidate_columns": _format_column_list(candidate_columns),
                "accepted_aliases": _format_column_list(accepted_aliases),
                "repair_guidance": _build_repair_guidance(
                    canonical_field,
                    source_column=source_column,
                    candidate_columns=candidate_columns,
                    is_required=canonical_field in REQUIRED_COLUMNS,
                ),
                "preparation_status": preparation_result.status,
                "preparation_message": preparation_result.message,
                "missing_required_fields": _format_column_list(preparation_result.missing_required_fields),
            }
        )

    return pd.DataFrame(rows, columns=INPUT_DIAGNOSTIC_COLUMNS)


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
    prepared_dataframe.attrs["source_mapping"] = mapping
    prepared_dataframe.attrs["canonical_columns"] = tuple(CANONICAL_COLUMNS)

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
