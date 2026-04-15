from __future__ import annotations

from pathlib import Path

import pandas as pd

from export.exporter import export_outputs
from ingestion.input_preparation import prepare_input_dataframe
from validation.validator import validate_vat_data


def test_export_outputs_writes_artifacts_and_summary(tmp_path: Path, base_dataframe: pd.DataFrame) -> None:
    prepared = prepare_input_dataframe(base_dataframe).prepared_dataframe
    assert prepared is not None
    prepared = prepared.copy()
    prepared.at[0, "date"] = ""

    validation_results = validate_vat_data(prepared)
    exported = export_outputs(
        raw_dataframe=base_dataframe,
        prepared_dataframe=prepared,
        validation_results=validation_results,
        anomaly_results=[],
        review_log=pd.DataFrame(),
        review_history=pd.DataFrame(),
        output_dir=tmp_path,
        source_filename="sample.csv",
    )

    for path in exported.values():
        assert Path(path).exists()

    issue_report = pd.read_csv(exported["issue_report"])
    review_summary = pd.read_csv(exported["review_summary"])

    assert len(issue_report) == 1
    assert issue_report.iloc[0]["issue_type"] == "missing_transaction_date"
    assert review_summary.iloc[0]["total_issues"] == 1
    assert bool(review_summary.iloc[0]["is_review_complete"]) is False

