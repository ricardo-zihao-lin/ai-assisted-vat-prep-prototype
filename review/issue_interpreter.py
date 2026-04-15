"""Rule interpretation layer for VAT pre-submission review issues.

This module maps raw validation and anomaly signals into schema-aligned
``Issue`` objects with review-oriented status, risk, and explanation fields.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from review.models import (
    DeterminismType,
    Issue,
    IssueStatus,
    ReviewState,
    RiskLevel,
    build_issue_id,
    build_record_id,
    utc_now_iso,
)


@dataclass(frozen=True)
class RawIssueSignal:
    """Minimal machine-detected finding before review interpretation is applied."""

    rule_id: str
    issue_type: str
    category: str
    row_index: int
    field_names: tuple[str, ...] = ()
    detected_value: Any = None
    expected_value: Any = None
    source_snapshot: dict[str, Any] | None = None
    evidence_expected: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    dataset_id: str | None = None


@dataclass(frozen=True)
class IssueInterpretation:
    """Review-oriented interpretation for a raw rule signal."""

    status: IssueStatus
    risk_level: RiskLevel
    determinism_type: DeterminismType
    detection_summary: str
    why_it_matters: str
    possible_vat_review_impact: str
    recommended_manual_check: str


def _column_label(signal: RawIssueSignal) -> str:
    if signal.field_names:
        return signal.field_names[0]
    return "record"


def _interpret_signal(signal: RawIssueSignal) -> IssueInterpretation:
    """Map one raw signal to the user-facing review fields from the rules doc."""
    column_name = _column_label(signal)

    if signal.rule_id == "VR001":
        return IssueInterpretation(
            status=IssueStatus.NON_COMPLIANT,
            risk_level=RiskLevel.HIGH,
            determinism_type=DeterminismType.DETERMINISTIC,
            detection_summary="Transaction date is missing.",
            why_it_matters="A missing transaction date makes it harder to review period relevance and transaction timing.",
            possible_vat_review_impact="The record may be reviewed in the wrong period or may need correction before pre-submission review can continue.",
            recommended_manual_check="Check the source invoice, receipt, or ledger export and enter the correct transaction date.",
        )

    if signal.rule_id == "VR002":
        return IssueInterpretation(
            status=IssueStatus.NON_COMPLIANT,
            risk_level=RiskLevel.HIGH,
            determinism_type=DeterminismType.DETERMINISTIC,
            detection_summary="Date could not be parsed.",
            why_it_matters="An unreadable date reduces confidence in transaction timing and period review.",
            possible_vat_review_impact="The record may need correction before it can be reviewed for period relevance.",
            recommended_manual_check="Confirm the original date format and correct the transaction date field.",
        )

    if signal.rule_id == "VR004":
        return IssueInterpretation(
            status=IssueStatus.NON_COMPLIANT,
            risk_level=RiskLevel.HIGH,
            determinism_type=DeterminismType.DETERMINISTIC,
            detection_summary="Net amount is missing.",
            why_it_matters="A missing net amount prevents reliable review of the transaction magnitude.",
            possible_vat_review_impact="The record may need correction or exclusion before it can be treated as review-ready.",
            recommended_manual_check="Check the source record and supply the missing net amount or exclude the record from preparation.",
        )

    if signal.rule_id == "VR005":
        return IssueInterpretation(
            status=IssueStatus.NON_COMPLIANT,
            risk_level=RiskLevel.HIGH,
            determinism_type=DeterminismType.DETERMINISTIC,
            detection_summary="Net amount could not be parsed as a number.",
            why_it_matters="A non-numeric net amount prevents reliable review of the transaction magnitude.",
            possible_vat_review_impact="The record may need correction before it can be reconciled or prepared for review.",
            recommended_manual_check="Check the source amount format and replace the non-numeric net amount with the correct value.",
        )

    if signal.rule_id == "VR006":
        return IssueInterpretation(
            status=IssueStatus.POTENTIALLY_NON_COMPLIANT,
            risk_level=RiskLevel.HIGH,
            determinism_type=DeterminismType.PARTLY_DETERMINISTIC,
            detection_summary="VAT amount is missing.",
            why_it_matters="Missing VAT detail reduces confidence in the record and may indicate incomplete preparation.",
            possible_vat_review_impact="The user may need to confirm whether VAT should be present, whether the value is zero, or whether the record is incomplete.",
            recommended_manual_check="Check the source record and confirm whether the VAT amount should be entered, left as zero, or handled outside this dataset.",
        )

    if signal.rule_id == "VR007":
        return IssueInterpretation(
            status=IssueStatus.NON_COMPLIANT,
            risk_level=RiskLevel.HIGH,
            determinism_type=DeterminismType.DETERMINISTIC,
            detection_summary="VAT amount could not be parsed as a number.",
            why_it_matters="A non-numeric VAT amount reduces confidence in the record and may affect pre-submission preparation.",
            possible_vat_review_impact="The record may need correction before it can be treated as review-ready.",
            recommended_manual_check="Check the source amount format and replace the non-numeric VAT amount with the correct value.",
        )

    if signal.rule_id == "VR008":
        return IssueInterpretation(
            status=IssueStatus.NON_COMPLIANT,
            risk_level=RiskLevel.HIGH,
            determinism_type=DeterminismType.DETERMINISTIC,
            detection_summary="Exact duplicate row detected in the dataset.",
            why_it_matters="Exact duplicated records can lead to repeated inclusion in review and preparation work.",
            possible_vat_review_impact="The transaction may be overstated or counted more than once until the duplicate is resolved.",
            recommended_manual_check="Compare the repeated rows and confirm whether one should be removed, excluded, or annotated as a legitimate repeat.",
        )

    if signal.rule_id == "VR009":
        return IssueInterpretation(
            status=IssueStatus.POTENTIALLY_NON_COMPLIANT,
            risk_level=RiskLevel.MEDIUM,
            determinism_type=DeterminismType.PARTLY_DETERMINISTIC,
            detection_summary="Invoice reference appears more than once in the dataset.",
            why_it_matters="Repeated invoice references can indicate duplicate entry, split posting, or another pattern that needs confirmation before review continues.",
            possible_vat_review_impact="The transaction set may contain repeated or misinterpreted records until the duplicate-looking references are checked against evidence.",
            recommended_manual_check="Review the related rows and confirm whether the repeated reference reflects a true duplicate, a split line, or another legitimate pattern.",
        )

    if signal.rule_id == "VR013":
        return IssueInterpretation(
            status=IssueStatus.REVIEW_REQUIRED,
            risk_level=RiskLevel.MEDIUM,
            determinism_type=DeterminismType.DETERMINISTIC,
            detection_summary="Description is blank.",
            why_it_matters="A record may be structurally valid but still too unclear to review confidently when its description is blank.",
            possible_vat_review_impact="The user may need additional context before deciding whether the transaction should remain in the review set.",
            recommended_manual_check="Check the source evidence and add a short meaningful description of the transaction.",
        )

    if signal.rule_id == "VR015":
        return IssueInterpretation(
            status=IssueStatus.REVIEW_REQUIRED,
            risk_level=RiskLevel.MEDIUM,
            determinism_type=DeterminismType.PARTLY_DETERMINISTIC,
            detection_summary=f"`{column_name}` sits outside the expected IQR bounds for this dataset.",
            why_it_matters="Unusual transaction values may be legitimate, but they deserve closer review because they are more likely to reflect entry errors, omissions, or one-off events.",
            possible_vat_review_impact="The record may require evidence-based confirmation before it is treated as review-ready.",
            recommended_manual_check="Compare the unusual amount with the source record and supporting evidence to confirm whether it is legitimately unusual or needs correction.",
        )

    if signal.rule_id == "VR016":
        return IssueInterpretation(
            status=IssueStatus.REVIEW_REQUIRED,
            risk_level=RiskLevel.MEDIUM,
            determinism_type=DeterminismType.PARTLY_DETERMINISTIC,
            detection_summary="Net amount is negative or unusually low for review purposes.",
            why_it_matters="Negative or unusually low amounts can be valid, but they often need extra context because they may represent refunds, reversals, credits, or entry mistakes.",
            possible_vat_review_impact="The record may need manual interpretation before it is treated as comfortably review-ready for pre-submission preparation.",
            recommended_manual_check="Check whether the record is a refund, credit, reversal, or another legitimate negative transaction and record the evidence used.",
        )

    if signal.rule_id == "VR018":
        return IssueInterpretation(
            status=IssueStatus.REVIEW_REQUIRED,
            risk_level=RiskLevel.LOW,
            determinism_type=DeterminismType.PARTLY_DETERMINISTIC,
            detection_summary="Amounts form a suspicious zero-value combination.",
            why_it_matters="All-zero amount combinations can be valid placeholders or non-financial lines, but they can also indicate incomplete record preparation.",
            possible_vat_review_impact="The record may need confirmation before it is retained in the review set.",
            recommended_manual_check="Confirm whether the record should remain in the dataset, and document why the zero-value combination is acceptable if it is retained.",
        )

    if signal.rule_id == "VR017":
        return IssueInterpretation(
            status=IssueStatus.REVIEW_REQUIRED,
            risk_level=RiskLevel.MEDIUM,
            determinism_type=DeterminismType.DETERMINISTIC,
            detection_summary=f"Value is missing in `{column_name}`.",
            why_it_matters="Missing supporting fields can weaken record completeness and traceability during pre-submission review.",
            possible_vat_review_impact="The user may need to supply additional context before the record can be reviewed with confidence.",
            recommended_manual_check="Check the source record and decide whether the missing field should be completed or documented as unavailable.",
        )

    if signal.rule_id == "VR019":
        return IssueInterpretation(
            status=IssueStatus.REVIEW_REQUIRED,
            risk_level=RiskLevel.LOW,
            determinism_type=DeterminismType.DETERMINISTIC,
            detection_summary="Transaction category or support field is missing.",
            why_it_matters="Missing category context can make the record harder to understand during review, even when core amounts and dates are present.",
            possible_vat_review_impact="The record may still be reviewable, but the user may need extra context before treating it as comfortably review-ready.",
            recommended_manual_check="Check the source classification and add a transaction category or note if that context is available.",
        )

    if signal.rule_id == "VR011":
        return IssueInterpretation(
            status=IssueStatus.NON_COMPLIANT,
            risk_level=RiskLevel.HIGH,
            determinism_type=DeterminismType.DETERMINISTIC,
            detection_summary="Gross amount does not reconcile with net amount plus VAT amount.",
            why_it_matters="Arithmetic inconsistency reduces confidence in the record and suggests an entry, mapping, or transformation problem.",
            possible_vat_review_impact="The record may need correction before it can be treated as review-ready for pre-submission preparation.",
            recommended_manual_check="Check the source invoice or export and confirm which amount is incorrect.",
        )

    if signal.rule_id == "VR012":
        return IssueInterpretation(
            status=IssueStatus.REVIEW_REQUIRED,
            risk_level=RiskLevel.MEDIUM,
            determinism_type=DeterminismType.DETERMINISTIC,
            detection_summary="Counterparty reference is missing.",
            why_it_matters="Weak counterparty traceability makes the record harder to verify and reduces confidence during manual review.",
            possible_vat_review_impact="The user may need additional supporting context before accepting the record into the review set.",
            recommended_manual_check="Add the supplier, customer, or counterparty reference from the source evidence or note why it is unavailable.",
        )

    if signal.rule_id == "VR014":
        return IssueInterpretation(
            status=IssueStatus.POTENTIALLY_NON_COMPLIANT,
            risk_level=RiskLevel.MEDIUM,
            determinism_type=DeterminismType.DETERMINISTIC,
            detection_summary="Document or evidence reference is missing.",
            why_it_matters="Missing evidence linkage weakens traceability and makes later review harder to justify.",
            possible_vat_review_impact="The user may need to attach or record evidence details before the transaction can be treated as comfortably review-ready.",
            recommended_manual_check="Record the supporting invoice, receipt, attachment name, or other evidence reference used to support this transaction.",
        )

    if signal.rule_id == "VR020":
        return IssueInterpretation(
            status=IssueStatus.POTENTIALLY_NON_COMPLIANT,
            risk_level=RiskLevel.HIGH,
            determinism_type=DeterminismType.PARTLY_DETERMINISTIC,
            detection_summary="Related amount fields have a conflicting sign pattern.",
            why_it_matters="Conflicting signs across net, VAT, and gross amounts may indicate a malformed import, reversal error, or inconsistent handling of credits and refunds.",
            possible_vat_review_impact="The record may be interpreted incorrectly until the amount pattern is checked against source evidence.",
            recommended_manual_check="Verify whether the transaction is a credit, refund, reversal, or incorrectly entered record and document the supporting evidence.",
        )

    if signal.rule_id == "VR901":
        return IssueInterpretation(
            status=IssueStatus.NON_COMPLIANT,
            risk_level=RiskLevel.HIGH,
            determinism_type=DeterminismType.DETERMINISTIC,
            detection_summary=f"Required column `{column_name}` is missing from the dataset.",
            why_it_matters="A required field is needed before record-level pre-submission review can be performed reliably.",
            possible_vat_review_impact="Records may be omitted from checking or interpreted incorrectly until the missing column is provided.",
            recommended_manual_check="Check the source spreadsheet headings and confirm that the required column is present or correctly mapped.",
        )

    if signal.rule_id == "VR900":
        return IssueInterpretation(
            status=IssueStatus.NON_COMPLIANT,
            risk_level=RiskLevel.HIGH,
            determinism_type=DeterminismType.DETERMINISTIC,
            detection_summary="Validation expected a pandas DataFrame.",
            why_it_matters="The validation stage cannot run if the uploaded data is not represented as a tabular dataset.",
            possible_vat_review_impact="No record-level review can proceed until the input is loaded into the expected structure.",
            recommended_manual_check="Check the ingestion step and confirm that the uploaded spreadsheet was loaded successfully.",
        )

    return IssueInterpretation(
        status=IssueStatus.REVIEW_REQUIRED,
        risk_level=RiskLevel.MEDIUM,
        determinism_type=DeterminismType.DETERMINISTIC,
        detection_summary=f"The rule `{signal.rule_id}` flagged a review item.",
        why_it_matters="The record contains a flagged condition that should be checked before pre-submission review is treated as complete.",
        possible_vat_review_impact="The user may need to inspect the record manually before deciding whether correction or acceptance is appropriate.",
        recommended_manual_check="Review the flagged record against the source spreadsheet and supporting evidence.",
    )


def interpret_signal(signal: RawIssueSignal) -> Issue:
    """Convert one raw signal into a schema-aligned issue object."""
    interpretation = _interpret_signal(signal)
    return Issue(
        issue_id=build_issue_id(signal.rule_id, signal.row_index, signal.field_names),
        rule_id=signal.rule_id,
        record_id=build_record_id(signal.row_index),
        issue_type=signal.issue_type,
        category=signal.category,
        status=interpretation.status,
        risk_level=interpretation.risk_level,
        determinism_type=interpretation.determinism_type,
        detection_summary=interpretation.detection_summary,
        why_it_matters=interpretation.why_it_matters,
        possible_vat_review_impact=interpretation.possible_vat_review_impact,
        recommended_manual_check=interpretation.recommended_manual_check,
        review_state=ReviewState.OPEN,
        detected_at=utc_now_iso(),
        dataset_id=signal.dataset_id,
        row_index=signal.row_index,
        field_names=signal.field_names,
        detected_value=signal.detected_value,
        expected_value=signal.expected_value,
        evidence_expected=signal.evidence_expected,
        source_snapshot=signal.source_snapshot,
    )
