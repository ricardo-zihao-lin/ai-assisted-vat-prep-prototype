"""Structured review-domain models for VAT pre-submission issue handling."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping


class IssueStatus(str, Enum):
    """Classification status used by the issue schema."""

    NON_COMPLIANT = "Non-compliant"
    POTENTIALLY_NON_COMPLIANT = "Potentially non-compliant"
    REVIEW_REQUIRED = "Review required"


class RiskLevel(str, Enum):
    """Risk level used by the issue schema."""

    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class DeterminismType(str, Enum):
    """Whether an issue was produced deterministically or as a review signal."""

    DETERMINISTIC = "Deterministic"
    PARTLY_DETERMINISTIC = "Partly deterministic"
    MANUAL_ONLY = "Manual only"


class ReviewState(str, Enum):
    """Lifecycle state for a detected issue."""

    OPEN = "open"
    IN_REVIEW = "in_review"
    RESOLVED = "resolved"
    ACCEPTED_WITH_NOTE = "accepted_with_note"
    CORRECTED = "corrected"
    FALSE_POSITIVE = "false_positive"
    EXCLUDED = "excluded"
    ESCALATED = "escalated"


def build_record_id(row_index: int | None) -> str:
    """Return a stable record identifier for row-level or dataset-level findings."""
    if row_index is None or row_index < 0:
        return "DATASET"
    return f"ROW-{row_index}"


def build_issue_id(rule_id: str, row_index: int | None, field_names: tuple[str, ...]) -> str:
    """Create a readable issue identifier without requiring global state."""
    row_token = "DATASET" if row_index is None or row_index < 0 else f"ROW-{row_index}"
    if not field_names:
        return f"ISSUE-{rule_id}-{row_token}"

    suffix = "-".join(field.upper().replace(" ", "_") for field in field_names[:3])
    return f"ISSUE-{rule_id}-{row_token}-{suffix}"


def utc_now_iso() -> str:
    """Return a stable UTC timestamp string for issue records."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


@dataclass(frozen=True)
class Issue:
    """Structured issue object aligned with ``docs/issue_schema.md``."""

    issue_id: str
    rule_id: str
    record_id: str
    issue_type: str
    category: str
    status: IssueStatus
    risk_level: RiskLevel
    determinism_type: DeterminismType
    detection_summary: str
    why_it_matters: str
    possible_vat_review_impact: str
    recommended_manual_check: str
    review_state: ReviewState
    detected_at: str
    dataset_id: str | None = None
    row_index: int | None = None
    field_names: tuple[str, ...] = ()
    detected_value: Any = None
    expected_value: Any = None
    evidence_expected: str | None = None
    source_snapshot: dict[str, Any] | None = None
    detection_scope: str | None = None
    is_resolved: bool = False
    created_by: str = "system"
    updated_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialise the issue into a JSON/CSV-friendly mapping."""
        payload = asdict(self)
        payload["status"] = self.status.value
        payload["risk_level"] = self.risk_level.value
        payload["determinism_type"] = self.determinism_type.value
        payload["review_state"] = self.review_state.value
        payload["field_names"] = list(self.field_names)
        return payload


def issue_to_record(issue: Issue | Mapping[str, Any]) -> dict[str, Any]:
    """Return a plain dictionary for either an ``Issue`` or mapping-like row."""
    if isinstance(issue, Issue):
        return issue.to_dict()
    return dict(issue)


def issues_to_records(issues: list[Issue] | tuple[Issue, ...] | list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Normalise a sequence of issue objects into serialisable records."""
    return [issue_to_record(issue) for issue in issues]
