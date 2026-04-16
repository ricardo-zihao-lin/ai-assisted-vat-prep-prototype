from __future__ import annotations

import pandas as pd
import pytest


@pytest.fixture()
def base_dataframe() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "date": "2026-01-05",
                "invoice_reference": "INV-001",
                "description": "Client invoice",
                "net_amount": 100.0,
                "vat_amount": 20.0,
                "gross_amount": 120.0,
                "counterparty_ref": "SUP-1",
                "document_reference": "DOC-1",
                "category": "Sales",
            },
            {
                "date": "2026-01-06",
                "invoice_reference": "INV-002",
                "description": "Office supplies",
                "net_amount": 50.0,
                "vat_amount": 10.0,
                "gross_amount": 60.0,
                "counterparty_ref": "SUP-2",
                "document_reference": "DOC-2",
                "category": "Expense",
            },
        ]
    )

