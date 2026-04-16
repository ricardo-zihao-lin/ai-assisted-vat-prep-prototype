"""Canonical VAT review rule catalog.

The project docs describe issue generation as rule-driven. This module keeps
that metadata in one place so status, risk, and explanation text are not
scattered across the pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass

from review.models import DeterminismType, IssueStatus, RiskLevel


@dataclass(frozen=True)
class RuleDefinition:
    """Static metadata for one VAT review rule."""

    rule_id: str
    status: IssueStatus
    risk_level: RiskLevel
    determinism_type: DeterminismType
    detection_summary: str
    why_it_matters: str
    possible_vat_review_impact: str
    recommended_manual_check: str


RULE_DEFINITIONS: dict[str, RuleDefinition] = {
    "VR001": RuleDefinition("VR001", IssueStatus.NON_COMPLIANT, RiskLevel.HIGH, DeterminismType.DETERMINISTIC, "Transaction date is missing.", "A missing transaction date makes it harder to review period relevance and transaction timing.", "The record may be reviewed in the wrong period or may need correction before pre-submission review can continue.", "Check the source invoice, receipt, or ledger export and enter the correct transaction date."),
    "VR002": RuleDefinition("VR002", IssueStatus.NON_COMPLIANT, RiskLevel.HIGH, DeterminismType.DETERMINISTIC, "Date could not be parsed.", "An unreadable date reduces confidence in transaction timing and period review.", "The record may need correction before it can be reviewed for period relevance.", "Confirm the original date format and correct the transaction date field."),
    "VR004": RuleDefinition("VR004", IssueStatus.NON_COMPLIANT, RiskLevel.HIGH, DeterminismType.DETERMINISTIC, "Net amount is missing.", "A missing net amount prevents reliable review of the transaction magnitude.", "The record may need correction or exclusion before it can be treated as review-ready.", "Check the source record and supply the missing net amount or exclude the record from preparation."),
    "VR005": RuleDefinition("VR005", IssueStatus.NON_COMPLIANT, RiskLevel.HIGH, DeterminismType.DETERMINISTIC, "Net amount could not be parsed as a number.", "A non-numeric net amount prevents reliable review of the transaction magnitude.", "The record may need correction before it can be reconciled or prepared for review.", "Check the source amount format and replace the non-numeric net amount with the correct value."),
    "VR006": RuleDefinition("VR006", IssueStatus.POTENTIALLY_NON_COMPLIANT, RiskLevel.HIGH, DeterminismType.PARTLY_DETERMINISTIC, "VAT amount is missing.", "Missing VAT detail reduces confidence in the record and may indicate incomplete preparation.", "The user may need to confirm whether VAT should be present, whether the value is zero, or whether the record is incomplete.", "Check the source record and confirm whether the VAT amount should be entered, left as zero, or handled outside this dataset."),
    "VR007": RuleDefinition("VR007", IssueStatus.NON_COMPLIANT, RiskLevel.HIGH, DeterminismType.DETERMINISTIC, "VAT amount could not be parsed as a number.", "A non-numeric VAT amount reduces confidence in the record and may affect pre-submission preparation.", "The record may need correction before it can be treated as review-ready.", "Check the source amount format and replace the non-numeric VAT amount with the correct value."),
    "VR008": RuleDefinition("VR008", IssueStatus.NON_COMPLIANT, RiskLevel.HIGH, DeterminismType.DETERMINISTIC, "Exact duplicate row detected in the dataset.", "Exact duplicated records can lead to repeated inclusion in review and preparation work.", "The transaction may be overstated or counted more than once until the duplicate is resolved.", "Compare the repeated rows and confirm whether one should be removed, excluded, or annotated as a legitimate repeat."),
    "VR009": RuleDefinition("VR009", IssueStatus.POTENTIALLY_NON_COMPLIANT, RiskLevel.MEDIUM, DeterminismType.PARTLY_DETERMINISTIC, "Invoice reference appears more than once in the dataset.", "Repeated invoice references can indicate duplicate entry, split posting, or another pattern that needs confirmation before review continues.", "The transaction set may contain repeated or misinterpreted records until the duplicate-looking references are checked against evidence.", "Review the related rows and confirm whether the repeated reference reflects a true duplicate, a split line, or another legitimate pattern."),
    "VR011": RuleDefinition("VR011", IssueStatus.NON_COMPLIANT, RiskLevel.HIGH, DeterminismType.DETERMINISTIC, "Gross amount does not reconcile with net amount plus VAT amount.", "Arithmetic inconsistency reduces confidence in the record and suggests an entry, mapping, or transformation problem.", "The record may need correction before it can be treated as review-ready for pre-submission preparation.", "Check the source invoice or export and confirm which amount is incorrect."),
    "VR012": RuleDefinition("VR012", IssueStatus.REVIEW_REQUIRED, RiskLevel.MEDIUM, DeterminismType.DETERMINISTIC, "Counterparty reference is missing.", "Weak counterparty traceability makes the record harder to verify and reduces confidence during manual review.", "The user may need additional supporting context before accepting the record into the review set.", "Add the supplier, customer, or counterparty reference from the source evidence or note why it is unavailable."),
    "VR013": RuleDefinition("VR013", IssueStatus.REVIEW_REQUIRED, RiskLevel.MEDIUM, DeterminismType.DETERMINISTIC, "Description is blank.", "A record may be structurally valid but still too unclear to review confidently when its description is blank.", "The user may need additional context before deciding whether the transaction should remain in the review set.", "Check the source evidence and add a short meaningful description of the transaction."),
    "VR014": RuleDefinition("VR014", IssueStatus.POTENTIALLY_NON_COMPLIANT, RiskLevel.MEDIUM, DeterminismType.DETERMINISTIC, "Document or evidence reference is missing.", "Missing evidence linkage weakens traceability and makes later review harder to justify.", "The user may need to attach or record evidence details before the transaction can be treated as comfortably review-ready.", "Record the supporting invoice, receipt, attachment name, or other evidence reference used to support this transaction."),
    "VR015": RuleDefinition("VR015", IssueStatus.REVIEW_REQUIRED, RiskLevel.MEDIUM, DeterminismType.PARTLY_DETERMINISTIC, "`{column_name}` sits outside the expected IQR bounds for this dataset.", "Unusual transaction values may be legitimate, but they deserve closer review because they are more likely to reflect entry errors, omissions, or one-off events.", "The record may require evidence-based confirmation before it is treated as review-ready.", "Compare the unusual amount with the source record and supporting evidence to confirm whether it is legitimately unusual or needs correction."),
    "VR016": RuleDefinition("VR016", IssueStatus.REVIEW_REQUIRED, RiskLevel.MEDIUM, DeterminismType.PARTLY_DETERMINISTIC, "Net amount is negative or unusually low for review purposes.", "Negative or unusually low amounts can be valid, but they often need extra context because they may represent refunds, reversals, credits, or entry mistakes.", "The record may need manual interpretation before it is treated as comfortably review-ready for pre-submission preparation.", "Check whether the record is a refund, credit, reversal, or another legitimate negative transaction and record the evidence used."),
    "VR017": RuleDefinition("VR017", IssueStatus.REVIEW_REQUIRED, RiskLevel.MEDIUM, DeterminismType.DETERMINISTIC, "Value is missing in `{column_name}`.", "Missing supporting fields can weaken record completeness and traceability during pre-submission review.", "The user may need to supply additional context before the record can be reviewed with confidence.", "Check the source record and decide whether the missing field should be completed or documented as unavailable."),
    "VR018": RuleDefinition("VR018", IssueStatus.REVIEW_REQUIRED, RiskLevel.LOW, DeterminismType.PARTLY_DETERMINISTIC, "Amounts form a suspicious zero-value combination.", "All-zero amount combinations can be valid placeholders or non-financial lines, but they can also indicate incomplete record preparation.", "The record may need confirmation before it is retained in the review set.", "Confirm whether the record should remain in the dataset, and document why the zero-value combination is acceptable if it is retained."),
    "VR019": RuleDefinition("VR019", IssueStatus.REVIEW_REQUIRED, RiskLevel.LOW, DeterminismType.DETERMINISTIC, "Transaction category or support field is missing.", "Missing category context can make the record harder to understand during review, even when core amounts and dates are present.", "The record may still be reviewable, but the user may need extra context before treating it as comfortably review-ready.", "Check the source classification and add a transaction category or note if that context is available."),
    "VR020": RuleDefinition("VR020", IssueStatus.POTENTIALLY_NON_COMPLIANT, RiskLevel.HIGH, DeterminismType.PARTLY_DETERMINISTIC, "Related amount fields have a conflicting sign pattern.", "Conflicting signs across net, VAT, and gross amounts may indicate a malformed import, reversal error, or inconsistent handling of credits and refunds.", "The record may be interpreted incorrectly until the amount pattern is checked against source evidence.", "Verify whether the transaction is a credit, refund, reversal, or incorrectly entered record and document the supporting evidence."),
    "VR900": RuleDefinition("VR900", IssueStatus.NON_COMPLIANT, RiskLevel.HIGH, DeterminismType.DETERMINISTIC, "Validation expected a pandas DataFrame.", "The validation stage cannot run if the uploaded data is not represented as a tabular dataset.", "No record-level review can proceed until the input is loaded into the expected structure.", "Check the ingestion step and confirm that the uploaded spreadsheet was loaded successfully."),
    "VR901": RuleDefinition("VR901", IssueStatus.NON_COMPLIANT, RiskLevel.HIGH, DeterminismType.DETERMINISTIC, "Required column `{column_name}` is missing from the dataset.", "A required field is needed before record-level pre-submission review can be performed reliably.", "Records may be omitted from checking or interpreted incorrectly until the missing column is provided.", "Check the source spreadsheet headings and confirm that the required column is present or correctly mapped."),
}


def get_rule_definition(rule_id: str) -> RuleDefinition | None:
    """Return the canonical metadata for a rule identifier, if known."""
    return RULE_DEFINITIONS.get(rule_id)
