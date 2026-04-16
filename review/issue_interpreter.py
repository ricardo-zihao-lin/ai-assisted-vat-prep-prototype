"""Rule interpretation layer for VAT pre-submission review issues."""

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
from vatrules import get_rule_definition


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


class _FormatContext(dict[str, str]):
    """Leave unknown placeholders intact when formatting rule templates."""

    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def _column_label(signal: RawIssueSignal) -> str:
    if signal.field_names:
        return signal.field_names[0]
    return "record"


def _format_template(template: str, signal: RawIssueSignal) -> str:
    return template.format_map(
        _FormatContext(
            column_name=_column_label(signal),
            rule_id=signal.rule_id,
            issue_type=signal.issue_type,
        )
    )


def _fallback_interpretation(signal: RawIssueSignal) -> IssueInterpretation:
    return IssueInterpretation(
        status=IssueStatus.REVIEW_REQUIRED,
        risk_level=RiskLevel.MEDIUM,
        determinism_type=DeterminismType.DETERMINISTIC,
        detection_summary=f"The rule `{signal.rule_id}` flagged a review item.",
        why_it_matters="The record contains a flagged condition that should be checked before pre-submission review is treated as complete.",
        possible_vat_review_impact="The user may need to inspect the record manually before deciding whether correction or acceptance is appropriate.",
        recommended_manual_check="Review the flagged record against the source spreadsheet and supporting evidence.",
    )


def _interpret_signal(signal: RawIssueSignal) -> IssueInterpretation:
    """Map one raw signal to the user-facing review fields from the rule catalog."""
    rule_definition = get_rule_definition(signal.rule_id)
    if rule_definition is None:
        return _fallback_interpretation(signal)

    return IssueInterpretation(
        status=rule_definition.status,
        risk_level=rule_definition.risk_level,
        determinism_type=rule_definition.determinism_type,
        detection_summary=_format_template(rule_definition.detection_summary, signal),
        why_it_matters=_format_template(rule_definition.why_it_matters, signal),
        possible_vat_review_impact=_format_template(rule_definition.possible_vat_review_impact, signal),
        recommended_manual_check=_format_template(rule_definition.recommended_manual_check, signal),
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
