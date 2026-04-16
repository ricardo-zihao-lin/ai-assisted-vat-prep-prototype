# MVP Feature Specification for VAT Pre-Submission Review Prototype

## 1. Purpose

This document defines the minimum viable product (MVP) feature scope for the local-first, human-in-the-loop prototype:

**AI-Assisted Spreadsheet Records Preparation Tool for UK Making Tax Digital (MTD) VAT Reporting**

In its revised and more accurate scope, the prototype is a:

**local-first VAT pre-submission review and correction support prototype**

The purpose of this specification is to define:

- which features are required for the MVP
- which features are optional or lower priority
- which features are explicitly out of scope
- how the MVP should support explainability, traceability, and human review

This specification is intended to keep implementation realistic, defensible, and aligned with undergraduate project constraints.

## 2. Product Positioning

The MVP should be positioned as a prototype that helps users review spreadsheet-based VAT records before VAT preparation and submission activity.

The MVP is intended to:

- identify records that may be incomplete, invalid, inconsistent, or review-worthy
- explain why flagged records matter in a VAT/MTD pre-submission context
- support structured manual checking
- allow users to record review decisions and evidence checked
- produce a pre-submission review summary

The MVP is not intended to:

- submit VAT returns to HMRC
- provide professional tax advice
- calculate final VAT liability as a legal conclusion
- guarantee compliance
- replace accounting software
- replace an accountant

## 3. MVP Design Principles

The MVP should follow these principles:

- **Local-first**: the prototype should run primarily on local files and local processing.
- **Human-in-the-loop**: the system should support user judgement rather than replace it.
- **Implementation-oriented**: features should be concrete and demonstrable.
- **Explainable**: outputs should clearly show what was detected and why it matters.
- **Traceable**: the user should be able to trace issues back to rules, records, and decisions.
- **Narrow but strong**: the MVP should do a smaller number of things well rather than attempt full tax automation.

## 4. Core User Story

The primary MVP user story is:

> A user imports spreadsheet records before VAT preparation, the system standardises the records, flags likely problems and review risks, explains them, supports manual review and correction, records decisions and evidence checked, and generates a pre-submission review summary.

This user story should guide feature prioritisation.

## 5. Must-Have MVP Features

The following features should be included in the MVP.

## 5.1 Spreadsheet Import

### Description

The system must allow the user to import spreadsheet-based transaction records.

### Required support

- CSV import
- Excel import

### Why it is required

Import is the entry point for the entire workflow.

### Expected output

- loaded dataset
- row count
- source filename metadata

## 5.2 Column Standardisation and Record Normalisation

### Description

The system must convert imported spreadsheets into a standard internal record structure.

### Required support

- column name standardisation
- blank/null normalisation
- generation of internal record identifiers

### Why it is required

Rules cannot be applied reliably to inconsistent source column structures.

### Expected output

- normalised records
- internal field mapping

## 5.3 Deterministic Record Checks

### Description

The system must run a core set of deterministic review checks against imported records.

### Minimum required rules

- missing transaction date
- invalid date format
- missing net amount
- non-numeric net amount
- non-numeric VAT amount
- duplicate row
- inconsistent totals
- blank description
- missing supplier/customer reference
- missing evidence/reference field where configured

### Why it is required

These are the most defensible and implementable checks for the MVP.

### Expected output

- rule trigger results
- generated issues

## 5.4 Duplicate and Consistency Review

### Description

The system must detect duplicate and amount-consistency risks.

### Required support

- exact duplicate row detection
- duplicate invoice/reference detection
- arithmetic consistency check where fields are available

### Why it is required

These issues are directly relevant to pre-submission review quality and are practical to demonstrate.

## 5.5 Unusual Transaction Detection

### Description

The system must support a simple unusual-transaction review feature.

### Required support

- IQR-based outlier detection on `net_amount`

### Why it is required

This connects the prototype to its existing anomaly-detection capability while keeping the feature bounded and explainable.

### Constraint

The output should be framed as a review signal, not proof of non-compliance.

## 5.6 Issue Generation and Classification

### Description

The system must convert rule triggers into structured issue objects.

### Required support

- issue ID generation
- rule linkage
- record linkage
- category assignment
- status assignment
- risk level assignment
- explanation text
- recommended manual check

### Why it is required

This is the main bridge between backend rule logic and user-facing review support.

### Related documents

- `VAT_review_rules.md`
- `issue_schema.md`

## 5.7 User-Facing Issue Review View

### Description

The MVP must present flagged issues clearly to the user.

### Required support

- issue list or issue table
- display of status and risk level
- display of why the issue matters
- display of suggested manual review action

### Why it is required

Without a usable issue view, the prototype cannot demonstrate human-in-the-loop review.

## 5.8 Manual Review Decision Logging

### Description

The user must be able to record a review outcome for a flagged issue.

### Required support

- decision selection
- note entry
- evidence checked entry
- timestamp capture
- optional correction flag

### Minimum decision values

- `confirmed_issue`
- `false_positive`
- `corrected`
- `accepted_with_note`
- `excluded_from_review_set`
- `escalated`

### Why it is required

Decision logging is central to explainability and traceability.

### Related document

- `decision_log_schema.md`

## 5.9 Review State Update

### Description

The system must update issue lifecycle state after user review.

### Required support

- `open`
- `in_review`
- `corrected`
- `accepted_with_note`
- `false_positive`
- `excluded`
- `escalated`

### Why it is required

The prototype must show not just what was detected, but what happened after review.

## 5.10 Pre-Submission Review Summary

### Description

The system must generate a summary of review outcomes for the current dataset or review batch.

### Minimum required summary contents

- total records
- total issues
- issues by status
- issues by risk level
- decisions by type
- unresolved issue count
- escalated issue count
- short narrative summary

### Why it is required

This is the final output of the workflow and is valuable for both user understanding and project demonstration.

### Related document

- `review_summary_schema.md`

## 5.11 Exportable Review Outputs

### Description

The MVP should generate review artefacts that can be saved or inspected after a session.

### Minimum required outputs

- dataset snapshot
- issue report
- review log
- review summary

### Why it is required

These outputs support traceability, demonstration, and evaluation.

## 6. Should-Have Features

The following features are useful and valuable, but not essential if time is limited.

## 6.1 Filtering and Sorting of Issues

Examples:

- filter by status
- filter by risk
- filter by category
- sort by severity or row number

This improves usability, especially when many issues are generated.

## 6.2 Record Detail View

Allow the user to inspect the relevant fields of the flagged record alongside the issue explanation.

This improves review quality and makes the prototype more demonstrable.

## 6.3 Editable Corrections Within the Interface

Allow the user to modify selected record fields directly in the prototype.

This is useful but not strictly required if the prototype can still log decisions and indicate needed corrections.

## 6.4 Configurable Required Fields

Allow some required review fields to be configured depending on dataset structure.

This improves flexibility but is not essential for the first MVP.

## 6.5 Review Progress Indicators

Examples:

- issues resolved count
- open issues count
- high-risk unresolved issues

This helps users understand where they are in the workflow.

## 7. Could-Have Features

The following features may be included if time allows, but should not displace core MVP delivery.

## 7.1 Multiple Review Sessions Per Dataset

Allow continued review over time with updated summary snapshots.

## 7.2 Advanced Duplicate Heuristics

Examples:

- fuzzy reference matching
- duplicate clustering

These are useful but can quickly expand complexity.

## 7.3 Configurable Risk Thresholds

Examples:

- editable outlier sensitivity
- configurable amount-consistency tolerance

## 7.4 Evidence Attachment Linking

Allow users to link filenames, local paths, or evidence references directly to issues or decisions.

## 7.5 Basic Dashboard View

Provide a high-level overview panel with issue and review metrics.

## 8. Explicitly Out of Scope for the MVP

The following features should not be included in the MVP scope.

## 8.1 HMRC Submission

The MVP must not submit VAT returns to HMRC.

## 8.2 Penalty Features

The MVP must not include:

- late submission penalty logic
- late payment penalty logic

## 8.3 Automated Tax Advice

The MVP must not provide:

- automatic VAT treatment recommendations as professional advice
- legal interpretation of ambiguous cases
- final liability conclusions

## 8.4 Full Accounting System Features

The MVP must not attempt to become:

- bookkeeping software
- invoice management software
- reconciliation platform
- end-to-end accounting suite

## 8.5 Complex Machine Learning Training

The MVP must not depend on:

- custom ML model training
- opaque predictive models
- difficult-to-explain classification pipelines

The prototype should remain explainable and lightweight.

## 8.6 Compliance Guarantee Claims

The MVP must not claim:

- guaranteed compliance
- guaranteed penalty avoidance
- legally complete review coverage

## 9. Functional Mapping to Existing Project Direction

The MVP should build on the current project capabilities.

| Existing capability | MVP role |
|---|---|
| CSV / Excel reading | retained as core import feature |
| column name standardisation | retained as core normalisation feature |
| missing value checks | retained and mapped into review rules |
| duplicate row checks | retained and expanded into duplicate review category |
| invalid date checks | retained as deterministic review rule |
| invalid numeric checks | retained as deterministic review rule |
| IQR outlier detection on `net_amount` | retained as unusual transaction review signal |
| dataset snapshot output | retained as supporting output |
| issue report output | retained and expanded into structured issue reporting |
| review log output | retained and expanded into decision logging |

This means the MVP is an extension and reframing of the current system, not a completely unrelated rebuild.

## 10. Functional Requirements Summary

The MVP should satisfy the following functional requirements.

| ID | Requirement |
|---|---|
| FR01 | The system shall import CSV and Excel spreadsheet records |
| FR02 | The system shall standardise source columns into a normalised internal structure |
| FR03 | The system shall run deterministic record-quality checks |
| FR04 | The system shall run duplicate detection logic |
| FR05 | The system shall run unusual transaction detection using IQR on `net_amount` |
| FR06 | The system shall generate structured issues from rule triggers |
| FR07 | The system shall assign status and risk level to each issue |
| FR08 | The system shall provide explainable issue output including why the issue matters and recommended manual check |
| FR09 | The system shall allow the user to record a decision, note, evidence checked, and timestamp |
| FR10 | The system shall update issue review state after user review |
| FR11 | The system shall generate a pre-submission review summary |
| FR12 | The system shall produce review artefacts suitable for later inspection or export |

## 11. Non-Functional Requirements Summary

The MVP should also satisfy the following non-functional requirements.

| ID | Requirement |
|---|---|
| NFR01 | The system should operate locally on spreadsheet files |
| NFR02 | The system should present outputs in clear, formal, and explainable language |
| NFR03 | The system should preserve traceability from issue detection to decision log |
| NFR04 | The system should avoid opaque automated judgement |
| NFR05 | The system should remain usable for a modest-sized spreadsheet dataset typical of a prototype demonstration |
| NFR06 | The system should use cautious wording that does not imply guaranteed compliance |

## 12. Acceptance Criteria for the MVP

The MVP can be considered complete for project purposes if it can demonstrate the following end-to-end flow:

1. a user imports a spreadsheet dataset
2. the system normalises the records
3. the system applies deterministic checks and unusual transaction review logic
4. the system generates issues with status, risk, explanation, and manual-check guidance
5. the user reviews selected issues
6. the user records decisions and evidence checked
7. the system updates issue review states
8. the system produces a pre-submission review summary

A strong MVP demonstration should also show:

- at least one deterministic issue
- at least one manual-review signal
- at least one logged decision
- at least one corrected or accepted issue
- a final summary highlighting unresolved or escalated items if present

## 13. Relationship to Other Project Documents

This MVP feature specification should be read together with:

- `VAT_review_rules.md`
- `issue_schema.md`
- `decision_log_schema.md`
- `VAT_review_workflow.md`
- `review_summary_schema.md`

Relationship between the documents:

- the rules document defines what is checked
- the schema documents define how outputs are stored
- the workflow document defines how the review process operates
- the MVP feature specification defines what must actually be implemented for the prototype

## 14. Implementation Guidance for an Undergraduate Project

### 14.1 Prioritise demonstrable end-to-end flow

A smaller set of working features is better than many incomplete features.

The MVP should first ensure:

- import works
- rules run
- issues are shown
- decisions can be logged
- summary can be produced

### 14.2 Prefer explainable features over ambitious features

If a feature is hard to justify, hard to explain, or hard to evaluate, it should not displace the core review workflow.

### 14.3 Reuse existing project capabilities

The current record validation and outlier components should be reused where possible and reframed within the new pre-submission review workflow.

### 14.4 Keep the user claim modest and accurate

The MVP should be described as:

- a VAT pre-submission review support prototype
- a human-in-the-loop record checking and correction support tool
- a local-first review assistance system

It should not be described as:

- an HMRC submission tool
- a compliance guarantee engine
- an automated tax adviser

## 15. Summary

The MVP should focus on delivering a clear, useful, and defensible prototype that supports spreadsheet-based VAT record review before submission preparation.

A successful MVP should:

- import and normalise records
- apply explainable review rules
- generate structured issues
- support manual review and decision logging
- produce a pre-submission review summary
- remain clearly bounded in scope

This specification keeps the project aligned with its revised goal: not full tax automation, but practical support for structured, explainable, and traceable VAT pre-submission review.
