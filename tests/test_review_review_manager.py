from __future__ import annotations

from pathlib import Path

import pandas as pd

from review.review_manager import build_review_queue, persist_review_outputs


def test_build_review_queue_merges_latest_saved_decision() -> None:
    issue_report_df = pd.DataFrame(
        [
            {
                "issue_id": "ISSUE-VR004-ROW-0-NET_AMOUNT",
                "finding_id": "ISSUE-VR004-ROW-0-NET_AMOUNT",
                "record_id": "ROW-0",
                "finding_summary": "row 0: missing value in net_amount",
                "row_index": 0,
                "issue_type": "missing_net_amount",
                "issue_category": "Required field presence",
                "status": "Non-compliant",
                "risk_level": "High",
                "review_state": "open",
                "column": "net_amount",
                "value": None,
                "why_it_matters": "Missing net amount prevents review.",
                "possible_vat_review_impact": "The record may need correction.",
                "recommended_manual_check": "Check the source record.",
                "evidence_expected": "Invoice",
                "trigger_reason": "blank",
                "trigger_rule": "validation",
                "fields_to_check": "net_amount",
                "suggested_action": "Fix it",
                "review_note": "note",
            }
        ]
    )
    review_log_df = pd.DataFrame(
        [
            {
                "issue_id": "ISSUE-VR004-ROW-0-NET_AMOUNT",
                "finding_id": "ISSUE-VR004-ROW-0-NET_AMOUNT",
                "decision": "corrected",
                "note": "fixed in source",
                "evidence_checked": "invoice copy",
            }
        ]
    )

    queue = build_review_queue(issue_report_df, review_log_df)

    assert queue.iloc[0]["decision"] == "corrected"
    assert queue.iloc[0]["notes"] == "fixed in source"
    assert queue.iloc[0]["evidence_checked"] == "invoice copy"
    assert queue.iloc[0]["review_state"] == "corrected"


def test_persist_review_outputs_appends_history_for_changed_entries(tmp_path: Path) -> None:
    review_queue = pd.DataFrame(
        [
            {
                "issue_id": "ISSUE-VR015-ROW-10-NET_AMOUNT",
                "finding_id": "ISSUE-VR015-ROW-10-NET_AMOUNT",
                "record_id": "ROW-10",
                "row_index": 10,
                "issue_type": "unusual_net_amount",
                "decision": "pending",
                "notes": "",
                "evidence_checked": "",
            }
        ]
    )
    log_path = tmp_path / "review_log.csv"
    history_path = tmp_path / "review_history.csv"

    persist_review_outputs(review_queue, log_path, history_path)

    updated_queue = review_queue.copy()
    updated_queue.at[0, "decision"] = "corrected"
    updated_queue.at[0, "notes"] = "checked against invoice"
    updated_queue.at[0, "evidence_checked"] = "invoice copy"

    current_log, review_history = persist_review_outputs(updated_queue, log_path, history_path)

    assert log_path.exists()
    assert history_path.exists()
    assert current_log.iloc[0]["decision"] == "corrected"
    assert review_history.iloc[0]["final_record_status"] == "corrected"
    assert review_history.iloc[0]["needs_escalation"] is False

