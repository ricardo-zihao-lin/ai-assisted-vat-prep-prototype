from __future__ import annotations

import pandas as pd

from ingestion.input_preparation import prepare_input_dataframe
from validation.validator import validate_vat_data


def test_validate_vat_data_flags_missing_transaction_date(base_dataframe: pd.DataFrame) -> None:
    prepared = prepare_input_dataframe(base_dataframe).prepared_dataframe
    assert prepared is not None
    prepared = prepared.copy()
    prepared.at[0, "date"] = ""

    result = validate_vat_data(prepared)

    assert result["issue_count"] == 1
    issue = result["issues"][0]
    assert issue.issue_type == "missing_transaction_date"
    assert issue.rule_id == "VR001"
    assert issue.row_index == 0


def test_validate_vat_data_flags_duplicate_rows() -> None:
    dataframe = pd.DataFrame(
        [
            {"date": "2026-01-05", "description": "Client invoice", "net_amount": 100.0, "vat_amount": 20.0},
            {"date": "2026-01-05", "description": "Client invoice", "net_amount": 100.0, "vat_amount": 20.0},
        ]
    )

    result = validate_vat_data(dataframe)

    assert result["issue_count"] == 2
    assert {issue.issue_type for issue in result["issues"]} == {"exact_duplicate_row"}
    assert {issue.row_index for issue in result["issues"]} == {0, 1}


def test_validate_vat_data_flags_invalid_numeric_and_negative_amounts(base_dataframe: pd.DataFrame) -> None:
    prepared = prepare_input_dataframe(base_dataframe).prepared_dataframe
    assert prepared is not None
    prepared = prepared.copy()
    prepared["net_amount"] = prepared["net_amount"].astype(object)
    prepared.at[0, "net_amount"] = "not_available"
    prepared.at[1, "net_amount"] = -5.0
    prepared.at[1, "vat_amount"] = -1.0
    prepared.at[1, "gross_amount"] = -6.0

    result = validate_vat_data(prepared)
    issue_types = {issue.issue_type for issue in result["issues"]}

    assert "non_numeric_net_amount" in issue_types
    assert "negative_or_unusually_low_net_amount" in issue_types
    assert result["issue_count"] == 2


def test_validate_vat_data_flags_inconsistent_totals() -> None:
    raw = pd.DataFrame(
        [
            {
                "date": "2026-01-05",
                "invoice_reference": "INV-001",
                "description": "Client invoice",
                "net_amount": 100.0,
                "vat_amount": 20.0,
                "gross_amount": 150.0,
                "counterparty_ref": "SUP-1",
                "document_reference": "DOC-1",
                "category": "Sales",
            }
        ]
    )
    dataframe = prepare_input_dataframe(raw).prepared_dataframe
    assert dataframe is not None

    result = validate_vat_data(dataframe)

    assert result["issue_count"] == 1
    issue = result["issues"][0]
    assert issue.issue_type == "inconsistent_totals"
    assert issue.rule_id == "VR011"
