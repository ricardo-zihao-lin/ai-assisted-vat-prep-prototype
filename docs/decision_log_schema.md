# Decision Log Schema for VAT Pre-Submission Review Prototype

## 1. Purpose

This document defines the decision log data schema used by the prototype to record human review actions taken on flagged issues during pre-submission VAT record checking.

The decision log exists to support a human-in-the-loop review process in which the system detects issues, the user checks evidence, and the final review outcome is recorded in a transparent and traceable way.

The decision log is intended to support:

- structured manual review of flagged issues
- traceability from system detection to human decision
- review transparency for dissertation demonstration and system evaluation
- evidence-aware correction and exception handling
- generation of pre-submission review summaries

This schema does not represent tax advice, final legal compliance certification, or automated VAT judgement.

## 2. Role in the Workflow

The decision log should be used after an issue has been flagged and presented to the user.

Its role in the workflow is:

1. a rule generates an issue
2. the user reviews the issue
3. the user checks source evidence or supporting information
4. the user records a decision
5. the system stores the decision with timestamp and notes
6. the linked issue is updated to reflect the current review state
7. the final summary includes both machine-detected issues and human review outcomes

The decision log is therefore the main record of human judgement in the prototype.

## 3. Design Principles

The decision log schema should follow these principles:

- **Human-centred**: it records what the user decided, not what the system assumes.
- **Traceable**: every decision should be linkable to an issue, a record, a time, and supporting evidence.
- **Explainable**: the log should capture enough detail to explain why the decision was made.
- **Minimal but useful**: the schema should be practical for an undergraduate prototype rather than over-engineered.
- **Non-legalistic**: the schema should support review decisions without presenting them as final tax rulings.

## 4. Core Entity Definition

A decision log entry represents one recorded human review outcome for one issue at a particular point in time.

In the simplest implementation:

- one issue may have one final decision log entry

In a more complete implementation:

- one issue may have multiple decision log entries over time
- the newest log entry represents the latest decision state

For an undergraduate prototype, either of the following is reasonable:

- single-decision model: store one decision per issue
- append-only model: store multiple decisions and link the latest one from the issue object

The append-only model is better for traceability, but the single-decision model is easier to implement.

## 5. Required Fields

Each decision log entry should include the following required fields.

| Field | Type | Required | Description |
|---|---|---|---|
| `decision_id` | string | Yes | Unique identifier for the decision log entry |
| `issue_id` | string | Yes | Identifier of the issue being reviewed |
| `record_id` | string | Yes | Identifier of the associated record |
| `decision` | enum | Yes | User's review decision |
| `decision_reason` | string | Yes | Short explanation of why the decision was made |
| `evidence_checked` | array of strings or string | Yes | Evidence or sources reviewed by the user |
| `timestamp` | datetime string | Yes | Time the decision was recorded |

## 6. Recommended Optional Fields

The following fields are strongly recommended.

| Field | Type | Required | Description |
|---|---|---|---|
| `dataset_id` | string | No | Identifier of the related dataset or review batch |
| `rule_id` | string | No | Rule associated with the linked issue |
| `reviewer_id` | string | No | Identifier of the reviewer, if the prototype supports it |
| `note` | string | No | Free-text note giving extra context |
| `correction_made` | boolean | No | Whether the record was changed as part of review |
| `corrected_fields` | array of strings | No | Fields changed during correction |
| `previous_values` | object | No | Previous values before correction |
| `updated_values` | object | No | New values after correction |
| `final_record_status` | enum/string | No | Final post-review state of the record or issue |
| `needs_escalation` | boolean | No | Whether the case should be escalated outside the prototype |
| `escalation_reason` | string | No | Why escalation is needed |
| `linked_issue_review_state` | string | No | Issue review state after this decision |
| `confidence_note` | string | No | Optional note on reviewer confidence or uncertainty |
| `attachment_reference` | string or array | No | Optional link or reference to supporting files |
| `created_by` | string | No | Usually `user` or a user identifier |
| `updated_at` | datetime string | No | Last modification time for the decision log entry |

## 7. Enumerations

### 7.1 `decision`

Allowed values:

- `confirmed_issue`
- `false_positive`
- `corrected`
- `accepted_with_note`
- `excluded_from_review_set`
- `escalated`

Definitions:

- `confirmed_issue`: the user agrees the issue is real, but may not yet have corrected the record
- `false_positive`: the user concludes the issue should not be treated as a real problem
- `corrected`: the issue was resolved by changing the underlying record
- `accepted_with_note`: the user accepts the record after review and documents why
- `excluded_from_review_set`: the record should not be included in the current review/preparation set
- `escalated`: the user determines that further review outside the prototype is needed

### 7.2 Suggested `final_record_status`

If a controlled vocabulary is used, recommended values are:

- `open`
- `reviewed`
- `corrected`
- `accepted`
- `excluded`
- `escalated`

This field is optional because some prototypes may prefer to store final state only in the linked issue object.

## 8. Canonical Field Definitions

### 8.1 Identification Fields

#### `decision_id`

Unique identifier for the decision log entry.

Recommended format:

```text
DEC-000001
```

Requirements:

- unique across all decision log entries
- stable after creation
- not reused

#### `issue_id`

Identifier of the flagged issue that the user is reviewing.

This must link to an existing issue object in `issue_schema.md`.

#### `record_id`

Identifier of the record associated with the issue.

This redundancy is useful because it allows filtering decision logs by record even without loading the linked issue object first.

### 8.2 Decision Fields

#### `decision`

Stores the review outcome selected by the user.

This is the most important field in the decision log because it records the human outcome of the review process.

#### `decision_reason`

A short plain-English explanation of why the decision was made.

Examples:

- `Invoice copy confirmed the transaction date was missing in the spreadsheet.`
- `Repeated invoice reference was valid because the transaction was split across two lines.`
- `Outlier amount matched supporting evidence and was a legitimate one-off purchase.`

This field should be required because a decision without explanation weakens traceability.

#### `note`

Optional free-text note for extra context.

This can capture:

- uncertainty
- special business context
- follow-up action
- explanation not suitable for the shorter `decision_reason` field

### 8.3 Evidence Fields

#### `evidence_checked`

Stores what evidence or source information the user reviewed before deciding.

Recommended examples:

- `Invoice INV-2045`
- `Supplier statement for March 2026`
- `Original spreadsheet export`
- `Receipt image`
- `Internal transaction report`

This field should encourage specific references rather than vague wording such as `checked documents`.

#### `attachment_reference`

Optional reference to related evidence files, paths, or document identifiers.

Examples:

- `invoice_INV2045.pdf`
- `/evidence/2026-03/INV-2045.pdf`
- `SharePoint: VAT Evidence / March / INV-2045`

For a local-first prototype, this may simply be a filename or document reference string.

### 8.4 Correction Fields

#### `correction_made`

Boolean field indicating whether the review resulted in a data change.

Typical values:

- `true` when a field was edited
- `false` when the record was accepted, excluded, or escalated without data modification

#### `corrected_fields`

List of fields changed during correction.

Examples:

```json
["transaction_date"]
```

```json
["vat_amount", "gross_amount"]
```

#### `previous_values`

Optional snapshot of the original values before correction.

Example:

```json
{
  "transaction_date": ""
}
```

#### `updated_values`

Optional snapshot of the values after correction.

Example:

```json
{
  "transaction_date": "2026-03-31"
}
```

These fields are especially useful for demonstrating traceability in the dissertation.

### 8.5 Escalation Fields

#### `needs_escalation`

Boolean field indicating whether the issue requires review outside the prototype.

Typical reasons include:

- ambiguous tax treatment
- missing evidence that cannot be resolved immediately
- business context unavailable
- case needs accountant input

#### `escalation_reason`

Optional explanation of why the case was escalated.

Example:

- `Unable to determine correct treatment from available evidence; accountant review required.`

## 9. Relationship to Issue Schema

The decision log is tightly linked to the issue schema.

At minimum:

- each decision log entry must reference `issue_id`
- each decision log entry should reference `record_id`
- the linked issue's `review_state` should be updated after a decision is recorded

Suggested mapping from `decision` to issue `review_state`:

| Decision | Suggested issue `review_state` |
|---|---|
| `confirmed_issue` | `in_review` or `resolved` |
| `false_positive` | `false_positive` |
| `corrected` | `corrected` |
| `accepted_with_note` | `accepted_with_note` |
| `excluded_from_review_set` | `excluded` |
| `escalated` | `escalated` |

If the prototype uses only terminal end states, `confirmed_issue` may map to `resolved` after the issue has been acknowledged and handled.

## 10. JSON Example Schema Shape

A practical decision log entry may look like this:

```json
{
  "decision_id": "DEC-000021",
  "dataset_id": "DATASET-2026-04-14-01",
  "issue_id": "ISSUE-000123",
  "record_id": "ROW-45",
  "rule_id": "VR011",
  "decision": "corrected",
  "decision_reason": "Source invoice confirmed that gross amount should be 120.00 rather than 150.00.",
  "note": "Spreadsheet entry appears to have been mistyped during manual preparation.",
  "evidence_checked": [
    "Invoice INV-2045",
    "Original spreadsheet export"
  ],
  "correction_made": true,
  "corrected_fields": ["gross_amount"],
  "previous_values": {
    "gross_amount": 150.0
  },
  "updated_values": {
    "gross_amount": 120.0
  },
  "final_record_status": "corrected",
  "needs_escalation": false,
  "linked_issue_review_state": "corrected",
  "created_by": "user",
  "timestamp": "2026-04-14T10:45:00Z",
  "updated_at": "2026-04-14T10:45:00Z"
}
```

## 11. Minimal Schema for an Undergraduate Prototype

If implementation time is limited, the minimum viable decision log schema should contain:

- `decision_id`
- `issue_id`
- `record_id`
- `decision`
- `decision_reason`
- `evidence_checked`
- `timestamp`

This minimal set is enough to support:

- traceability from issue to user review
- clear record of human judgement
- basic evidence logging
- review summary generation

If possible, also include:

- `note`
- `correction_made`
- `corrected_fields`

These significantly improve the prototype's demonstration value.

## 12. Recommended Validation Rules

The decision log entry itself should be validated.

Recommended validation constraints:

- `decision_id` must be unique and non-empty
- `issue_id` must reference an existing issue
- `record_id` should match the linked issue's record
- `decision` must be one of the allowed enum values
- `decision_reason` must not be blank
- `evidence_checked` must not be blank
- `timestamp` must be a valid timestamp
- if `correction_made = true`, then `corrected_fields` should not be empty
- if `needs_escalation = true`, `escalation_reason` should preferably be present
- if `previous_values` is present, `updated_values` should normally also be present

## 13. Storage and History Considerations

### 13.1 Single-decision model

In the simplest implementation:

- each issue has one decision log entry
- updating a decision overwrites the previous entry

Advantages:

- easier to implement
- fewer joins or history records

Limitations:

- weaker auditability
- less useful for showing review progression

### 13.2 Append-only history model

In a stronger implementation:

- each user action creates a new decision log entry
- the latest entry is treated as the current decision state

Advantages:

- better traceability
- better support for iterative review
- stronger dissertation evidence for transparency

Limitations:

- slightly more complex data handling

For an undergraduate prototype, the append-only model is preferable if it is not too costly to implement.

## 14. Suggested Output for User Interface

When displaying decision logs in the UI, the prototype should at minimum show:

- decision
- decision reason
- evidence checked
- whether a correction was made
- timestamp

Optional helpful fields:

- note
- corrected fields
- escalation reason
- linked issue identifier
- reviewer identifier

This allows users to understand not just what the system flagged, but also what action was taken.

## 15. Summary

The decision log schema should serve as the structured record of human judgement within the prototype.

A good decision log schema should:

- link clearly to the flagged issue
- record the user's decision in a controlled way
- capture why the decision was made
- record what evidence was checked
- record whether correction occurred
- support escalation where needed
- preserve traceability over time

This makes the schema suitable for a local-first, human-in-the-loop VAT pre-submission review prototype where transparency and review accountability are more important than automated tax decision-making.
