from __future__ import annotations

import pandas as pd

from ingestion.input_preparation import (
    PREPARATION_STATUS_CANONICAL,
    PREPARATION_STATUS_MAPPED,
    PREPARATION_STATUS_UNSUPPORTED,
    prepare_input_dataframe,
)


def test_prepare_input_dataframe_returns_canonical_for_exact_headers(base_dataframe: pd.DataFrame) -> None:
    result = prepare_input_dataframe(base_dataframe)

    assert result.status == PREPARATION_STATUS_CANONICAL
    assert result.prepared_dataframe is not None
    assert tuple(result.prepared_dataframe.columns) == tuple(result.canonical_columns)
    assert result.mapping["date"] == "date"
    assert result.mapping["net_amount"] == "net_amount"
    assert result.message == "Input already matched the canonical schema."


def test_prepare_input_dataframe_maps_aliases_and_leaves_optional_fields_blank() -> None:
    raw = pd.DataFrame(
        [
            {
                "transaction_date": "2026-02-01",
                "invoice_no": "INV-100",
                "details": "Services",
                "amount": 200.0,
                "tax_amount": 40.0,
                "total_amount": 240.0,
                "supplier_ref": "SUP-9",
                "receipt_reference": "DOC-9",
            }
        ]
    )

    result = prepare_input_dataframe(raw)

    assert result.status == PREPARATION_STATUS_MAPPED
    assert result.prepared_dataframe is not None
    assert result.mapping["date"] == "transaction_date"
    assert result.mapping["invoice_reference"] == "invoice_no"
    assert result.mapping["category"] is None
    assert list(result.prepared_dataframe["category"]) == [""]
    assert list(result.prepared_dataframe.columns) == list(result.canonical_columns)


def test_prepare_input_dataframe_returns_unsupported_when_required_fields_are_missing() -> None:
    raw = pd.DataFrame(
        [
            {
                "invoice_no": "INV-200",
                "amount": 99.0,
            }
        ]
    )

    result = prepare_input_dataframe(raw)

    assert result.status == PREPARATION_STATUS_UNSUPPORTED
    assert result.prepared_dataframe is None
    assert set(result.missing_required_fields) == {"date", "description", "vat_amount"}
    assert result.mapping["net_amount"] == "amount"

