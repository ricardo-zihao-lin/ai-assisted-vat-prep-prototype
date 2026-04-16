from __future__ import annotations

import pandas as pd

from anomaly.anomaly_detector import detect_anomalies


def test_detect_anomalies_flags_outlier_with_iqr() -> None:
    dataframe = pd.DataFrame(
        {
            "net_amount": [100.0] * 10 + [1000.0],
            "date": ["2026-01-01"] * 11,
            "description": ["Row"] * 11,
        }
    )

    result = detect_anomalies(dataframe, column="net_amount", method="iqr")

    assert len(result) == 1
    issue = result[0]
    assert issue.issue_type == "unusual_net_amount"
    assert issue.rule_id == "VR015"
    assert issue.row_index == 10
    assert issue.status.value == "Review required"


def test_detect_anomalies_returns_empty_when_column_is_missing() -> None:
    dataframe = pd.DataFrame({"date": ["2026-01-01"], "description": ["Row"]})

    result = detect_anomalies(dataframe, column="net_amount", method="iqr")

    assert result == []

