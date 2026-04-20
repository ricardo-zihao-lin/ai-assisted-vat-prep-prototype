from __future__ import annotations

import pandas as pd

from anomaly.anomaly_detector import detect_anomalies


def test_detect_anomalies_flags_outlier_with_iqr() -> None:
    dataframe = pd.DataFrame(
        {
            "net_amount": [100.0, 101.0, 99.0, 100.0, 500.0],
            "counterparty_ref": ["SUP-1"] * 5,
            "date": ["2026-01-01"] * 5,
            "description": ["Row"] * 5,
        }
    )

    result = detect_anomalies(dataframe, column="net_amount", method="iqr")

    assert len(result) == 1
    issue = result[0]
    assert issue.issue_type == "unusual_net_amount"
    assert issue.rule_id == "VR015"
    assert issue.row_index == 4
    assert issue.status.value == "Review required"
    assert issue.detection_scope == "contextual"
    assert issue.expected_value["detection_scope"] == "contextual"
    assert "contextual IQR bounds" in issue.detection_summary


def test_detect_anomalies_prefers_customer_supplier_context_and_falls_back_globally() -> None:
    dataframe = pd.DataFrame(
        [
            {
                "customer_supplier_id": "CS-1",
                "counterparty_ref": "SUP-1",
                "net_amount": 100.0,
                "date": "2026-01-01",
                "description": "Row",
            },
            {
                "customer_supplier_id": "CS-2",
                "counterparty_ref": "SUP-1",
                "net_amount": 101.0,
                "date": "2026-01-01",
                "description": "Row",
            },
            {
                "customer_supplier_id": "CS-3",
                "counterparty_ref": "SUP-1",
                "net_amount": 99.0,
                "date": "2026-01-01",
                "description": "Row",
            },
            {
                "customer_supplier_id": "CS-4",
                "counterparty_ref": "SUP-1",
                "net_amount": 100.0,
                "date": "2026-01-01",
                "description": "Row",
            },
            {
                "customer_supplier_id": "CS-5",
                "counterparty_ref": "SUP-1",
                "net_amount": 5000.0,
                "date": "2026-01-01",
                "description": "Row",
            },
        ]
    )

    result = detect_anomalies(dataframe, column="net_amount", method="iqr")

    assert len(result) == 1
    issue = result[0]
    assert issue.row_index == 4
    assert issue.detection_scope == "global"
    assert issue.expected_value["detection_scope"] == "global"
    assert "global IQR bounds" in issue.detection_summary


def test_detect_anomalies_returns_empty_when_column_is_missing() -> None:
    dataframe = pd.DataFrame({"date": ["2026-01-01"], "description": ["Row"]})

    result = detect_anomalies(dataframe, column="net_amount", method="iqr")

    assert result == []

