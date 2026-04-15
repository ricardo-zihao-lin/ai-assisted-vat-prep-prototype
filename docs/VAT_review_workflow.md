# VAT Review Workflow for Pre-Submission Record Checking

## 1. Purpose

This document defines the operational workflow for the local-first, human-in-the-loop prototype for pre-submission VAT record review.

The workflow describes how spreadsheet records move through the prototype from import to review summary generation. It is intended to connect the rule logic, issue schema, and decision logging model into one coherent process.

This workflow supports:

- spreadsheet-based record intake
- structured record normalisation
- deterministic rule checking and risk-signal detection
- issue classification by status and risk level
- explainable user-facing review output
- manual review and decision logging
- generation of a pre-submission review summary

This workflow does not cover:

- HMRC VAT return submission
- automated filing
- final legal compliance determination
- automatic tax advice
- penalty processing
- full accounting workflow management

## 2. Workflow Design Principles

The workflow should be designed around the following principles:

- **Local-first operation**: records are reviewed within the prototype without relying on cloud-only processing.
- **Human-in-the-loop review**: the system flags issues and supports review, but does not make final tax judgements.
- **Explainability**: each flagged issue should be accompanied by a clear reason and suggested manual check.
- **Traceability**: the workflow should preserve links between source record, triggered rule, generated issue, and final decision.
- **Progressive review**: the workflow should support moving from raw import to structured review rather than trying to automate everything in one step.
- **Practical implementation scope**: the workflow should be realistic for an undergraduate prototype.

## 3. High-Level Workflow

The end-to-end workflow should follow this sequence:

1. import spreadsheet records
2. standardise record structure
3. validate field presence and data format
4. run deterministic rules and risk-signal checks
5. generate issue objects for flagged records
6. assign issue category, status, and risk level
7. present explainable review output to the user
8. support manual review and decision logging
9. update issue review states
10. generate pre-submission review summary

## 4. Workflow Stages

## 4.1 Stage 1: Import Spreadsheet Records

### Purpose

Load spreadsheet data into the prototype from CSV or Excel sources.

### Inputs

- CSV files
- Excel files

### Main actions

- read file content
- extract rows and column headers
- assign internal dataset identifier
- assign row index or temporary record identifier

### Outputs

- raw imported dataset
- initial row references
- import metadata such as filename, timestamp, and record count

### Notes

At this stage, the prototype should not yet make review judgements. The goal is to ingest data reliably.

## 4.2 Stage 2: Standardise Data

### Purpose

Convert imported spreadsheet data into a normalised internal record format that later rule logic can use consistently.

### Main actions

- standardise column names
- trim whitespace
- convert blank-like values to null where appropriate
- map source columns to expected review fields
- generate internal `record_id`

### Example normalised fields

- `record_id`
- `transaction_date`
- `invoice_reference`
- `description`
- `net_amount`
- `vat_amount`
- `gross_amount`
- `supplier_ref`
- `customer_ref`
- `document_reference`
- `transaction_type`

### Outputs

- normalised record set
- field mapping metadata
- optional record-level normalisation warnings

### Notes

This stage is critical because rule execution should operate on standardised fields rather than raw spreadsheet column names.

## 4.3 Stage 3: Run Deterministic Checks and Risk-Signal Checks

### Purpose

Evaluate each record against the implemented rule set.

### Main actions

- apply deterministic validation rules
- apply duplicate detection logic
- apply arithmetic consistency logic
- apply traceability/completeness checks
- apply unusual transaction detection such as IQR-based outlier logic on `net_amount`

### Rule types

- deterministic rules
- partly deterministic risk-signal rules
- manual-review prompt rules where configured

### Outputs

- raw rule trigger results
- per-record detection outcomes
- supporting context for issue generation

### Notes

This stage should not directly produce final tax conclusions. It should produce structured findings that can be turned into review issues.

## 4.4 Stage 4: Generate Issue Objects

### Purpose

Convert rule triggers into structured issue objects suitable for UI display, filtering, review, and traceability.

### Main actions

- create one issue per rule trigger per record
- assign `issue_id`
- attach `rule_id`, `record_id`, `issue_type`, and `category`
- populate explanation fields
- capture affected fields and detected values

### Outputs

- issue list
- issue counts by category, status, and risk level

### Notes

This stage should follow the schema defined in `issue_schema.md`.

## 4.5 Stage 5: Assign Status and Risk Level

### Purpose

Classify each issue according to the prototype's review model.

### Main actions

- map each triggered rule to a default `status`
- map each triggered rule to a default `risk_level`
- store `determinism_type`
- allow rule-specific overrides where necessary

### Status values

- `Non-compliant`
- `Potentially non-compliant`
- `Review required`

### Risk values

- `High`
- `Medium`
- `Low`

### Outputs

- classified issues ready for user review

### Notes

Status reflects the nature of the finding. Risk reflects likely review impact. They should be related but not treated as identical.

## 4.6 Stage 6: Present Explainable Review Output

### Purpose

Show the user what was flagged, why it matters, and what should be checked next.

### Main actions

- display issue type, status, and risk
- display `why_it_matters`
- display `possible_vat_review_impact`
- display `recommended_manual_check`
- group issues by record, category, or severity if needed

### Outputs

- issue table or issue cards in the UI
- filtered and sortable issue view

### Notes

This stage is where explainability becomes visible to the user. It should avoid vague warnings and instead provide concrete review guidance.

## 4.7 Stage 7: Manual Review and Evidence Checking

### Purpose

Allow the user to inspect flagged issues and verify them against source evidence or business context.

### Main actions

- user opens issue details
- user checks supporting evidence
- user decides whether the issue is real, acceptable, corrected, excluded, or escalated
- user records notes where necessary

### Typical evidence checked

- invoice copy
- receipt
- supplier/customer reference
- original spreadsheet export
- supporting file or internal transaction report

### Outputs

- human review action ready to be logged

### Notes

This is the core human-in-the-loop stage. The prototype should make it easy to review issues, but should not automate the judgement itself.

## 4.8 Stage 8: Record Decision Log Entry

### Purpose

Store the user's review outcome in a structured and traceable way.

### Main actions

- create `decision_id`
- link decision to `issue_id` and `record_id`
- store `decision`
- store `decision_reason`
- store `evidence_checked`
- store `timestamp`
- optionally store correction details

### Typical decision values

- `confirmed_issue`
- `false_positive`
- `corrected`
- `accepted_with_note`
- `excluded_from_review_set`
- `escalated`

### Outputs

- decision log entry

### Notes

This stage should follow the structure defined in `decision_log_schema.md`.

## 4.9 Stage 9: Update Issue Review State

### Purpose

Reflect the effect of user review on the issue lifecycle.

### Main actions

- update the linked issue's `review_state`
- optionally mark `is_resolved`
- set `resolved_at` where applicable
- link the latest `decision_id` to the issue

### Typical review state transitions

```text
open -> in_review -> corrected
open -> in_review -> accepted_with_note
open -> in_review -> false_positive
open -> in_review -> excluded
open -> in_review -> escalated
```

### Outputs

- updated issue record
- current review progress status

### Notes

This stage keeps the issue list aligned with the user's actual review actions.

## 4.10 Stage 10: Generate Pre-Submission Review Summary

### Purpose

Produce a structured summary of the review session before any VAT preparation proceeds further.

### Main actions

- count total records reviewed
- count total issues generated
- summarise issues by category, status, and risk level
- summarise review outcomes
- identify unresolved or escalated issues
- identify corrected issues
- capture review timestamp or review batch metadata

### Outputs

- pre-submission review summary
- optionally exportable summary report

### Notes

The review summary should not claim that the dataset is fully compliant. It should state what was checked, what was flagged, what was reviewed, and what remains unresolved.

## 5. Workflow Input and Output Map

| Stage | Main input | Main output |
|---|---|---|
| Import spreadsheet records | CSV/Excel file | Raw dataset and import metadata |
| Standardise data | Raw dataset | Normalised records |
| Run checks | Normalised records | Rule trigger results |
| Generate issue objects | Rule trigger results | Structured issues |
| Assign status and risk | Structured issues | Classified issues |
| Present review output | Classified issues | User-facing issue list |
| Manual review | User-facing issue list and source evidence | Review decisions |
| Record decision log | Review decisions | Decision log entries |
| Update issue review state | Decision log entries and issues | Updated issue lifecycle state |
| Generate summary | Updated issues and decisions | Pre-submission review summary |

## 6. Workflow Status and State Mapping

The workflow should distinguish between issue classification and issue lifecycle state.

### 6.1 Issue classification

This is assigned when the issue is generated.

- `status`: `Non-compliant`, `Potentially non-compliant`, `Review required`
- `risk_level`: `High`, `Medium`, `Low`

These values describe the nature of the finding.

### 6.2 Issue lifecycle state

This changes as the user interacts with the issue.

- `open`
- `in_review`
- `resolved`
- `corrected`
- `accepted_with_note`
- `false_positive`
- `excluded`
- `escalated`

These values describe progress through the workflow.

### 6.3 Decision-to-state mapping

| User decision | Suggested issue review state | Meaning |
|---|---|---|
| `confirmed_issue` | `in_review` or `resolved` | The user agrees the issue is real; correction or follow-up may still be pending |
| `false_positive` | `false_positive` | The issue is closed because the user does not accept it as a real problem |
| `corrected` | `corrected` | The underlying record was changed and the issue is treated as resolved |
| `accepted_with_note` | `accepted_with_note` | The issue is closed with explanation, without necessarily changing the record |
| `excluded_from_review_set` | `excluded` | The record is removed from the current review/preparation set |
| `escalated` | `escalated` | The issue needs handling outside the prototype |

## 7. Human-in-the-Loop Control Points

The workflow should explicitly reserve the following points for human judgement:

- deciding whether a suspicious pattern is a real issue
- determining whether a record belongs in the reviewed period when evidence is ambiguous
- deciding whether a duplicate-looking entry is legitimate
- deciding whether an unusual amount is valid
- deciding whether correction, exclusion, or escalation is the right outcome

The system should support these decisions with evidence prompts and structured logging, not automatic conclusions.

## 8. Failure Handling and Edge Cases

The workflow should account for practical issues that may arise during prototype operation.

### 8.1 Import failure

Possible causes:

- unreadable file
- unsupported format
- corrupt spreadsheet

Recommended handling:

- show import error clearly
- do not continue review on invalid import
- log import failure separately from issue generation

### 8.2 Missing expected fields after normalisation

Possible causes:

- source columns do not match expected names
- incomplete export
- mapping failure

Recommended handling:

- report normalisation failure or warning
- allow user to inspect mapped fields if the prototype supports it
- avoid running dependent rules if required fields are absent

### 8.3 Excessive issue volume

Possible causes:

- poor source data quality
- overly broad rule thresholds
- duplicate-rich imports

Recommended handling:

- support sorting and filtering
- prioritise high-risk issues
- summarise issue counts clearly

### 8.4 Unresolved review items

Possible causes:

- missing evidence
- ambiguous business context
- time-limited review session

Recommended handling:

- keep issue state as open or escalated
- highlight unresolved items in the review summary
- do not imply that review is complete if unresolved high-risk items remain

## 9. Relationship to Other Documents

This workflow document should be read together with:

- `VAT_review_rules.md`
- `issue_schema.md`
- `decision_log_schema.md`

Relationship between the documents:

- `VAT_review_rules.md` defines what the system checks
- `issue_schema.md` defines how flagged findings are stored
- `decision_log_schema.md` defines how user decisions are stored
- `VAT_review_workflow.md` defines how these parts interact operationally

## 10. Implementation Notes for an Undergraduate Prototype

### 10.1 Keep the workflow linear and clear

A simple, well-defined sequential workflow is better than a highly dynamic workflow that is harder to explain and evaluate.

Recommended sequence:

1. import
2. normalise
3. check
4. generate issues
5. review
6. log decisions
7. summarise

### 10.2 Prioritise visibility of intermediate outputs

The prototype should allow the user to see:

- the normalised dataset snapshot
- the generated issues
- the decision log
- the final review summary

These intermediate outputs are useful both for usability and for dissertation evaluation.

### 10.3 Prioritise unresolved issue visibility

The workflow should make it easy to identify:

- unresolved high-risk issues
- issues awaiting evidence
- escalated cases

This is more valuable than trying to produce a simplistic pass/fail result.

### 10.4 Avoid overclaiming at the workflow level

The workflow should be described as:

- a pre-submission review support process
- an issue identification and structured correction support process
- an evidence-aware manual review workflow

It should not be described as:

- a full VAT compliance engine
- an automatic tax decision system
- a filing system

## 11. Summary

The VAT review workflow should provide a clear operational structure for moving from spreadsheet import to structured pre-submission review summary.

A strong prototype workflow should:

- normalise records consistently
- generate explainable issues from defined rules
- classify issues by status and risk
- support evidence-based manual review
- log user decisions in a structured way
- update issue state transparently
- produce a final summary without claiming legal certainty

This workflow is suitable for a local-first, human-in-the-loop undergraduate prototype focused on review support, traceability, and practical implementation rather than full tax automation.
