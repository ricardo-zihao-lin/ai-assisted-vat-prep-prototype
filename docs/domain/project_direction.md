# Project Direction: Goal, Boundary, and Workflow

## Purpose

This document records the current project direction for the Final Year Project prototype.

The system is no longer framed as a general spreadsheet anomaly detector. It is framed as a local-first, human-in-the-loop pre-submission VAT record review and correction support tool for spreadsheet-based workflows in a UK MTD VAT context.

Its purpose is to help users identify records that may need attention before VAT submission, explain why those records matter, and support structured manual review with traceable decisions.

## Core Goal

The project goal is to support users in:

- identifying records that may be non-compliant
- identifying records that may be potentially non-compliant
- identifying records that require manual review before submission
- understanding why flagged records may matter for VAT record preparation and review
- recording evidence-based review decisions in a transparent and traceable way

The system is intended to reduce the risk of overlooked record issues before submission by improving clarity, prioritisation, and review discipline.

## Boundary

The prototype is explicitly bounded.

### In Scope

- local spreadsheet ingestion from CSV and Excel
- canonicalisation and field normalisation
- deterministic record checks
- bounded risk checks such as anomaly-style flags
- VAT / MTD-oriented interpretation of findings
- review prioritisation
- manual decision capture and review logging
- export of review-ready artefacts and summaries

### Out of Scope

- direct HMRC submission
- late submission handling
- late payment handling
- automatic tax advice
- automatic tax liability calculation in ambiguous cases
- a claim that the system can determine complete legal compliance
- complex machine learning training pipelines
- replacement of accountants or bookkeeping platforms

## Review Philosophy

The prototype follows three principles:

1. Deterministic where possible
   Straightforward record-quality and consistency checks should be rule-based and explainable.

2. Human judgement where necessary
   Unusual or context-dependent cases should be surfaced for user review rather than auto-resolved.

3. Traceable throughout
   The system should preserve a clear trail from detected issue to review outcome.

## Anomaly Detection Position

The prototype uses a bounded IQR-based check for unusual `net_amount` values rather than a more complex machine-learning anomaly model such as Isolation Forest.

This is a deliberate design choice, not a missing feature. In a VAT review setting, the project needs to explain to a reviewer why a record was surfaced and what should be checked next. An IQR threshold can be described in plain review language: the value sits outside the expected spread of the observed data and should therefore be reviewed. That level of explainability is easier to defend in a dissertation, easier to audit in a finance context, and easier for a human reviewer to challenge or confirm.

The same choice also supports the local-first operating model. IQR can run with minimal computational overhead, no model training step, no parameter-heavy tuning process, and no dependency on external compute services. More complex machine-learning detectors may sometimes identify additional unusual patterns, but they introduce a higher risk of opaque flagging behaviour. In a financial review workflow, that opacity is a practical and governance concern because users may be asked to trust a flag without being given a sufficiently transparent reason.

## Working Status Model

Flagged records should be represented using a bounded review status model:

- `Non-compliant`
  The record fails a rule or record requirement that can be checked with sufficient confidence from available data.

- `Potentially non-compliant`
  The record shows a strong indication of a review problem, but the final judgement still depends on human verification or external evidence.

- `Review required`
  The record is not clearly invalid, but it should be checked before being treated as comfortably review-ready.

## User-Facing Value

The value of the system should not be described as "finding more anomalies". Its value should come from helping users:

- see which records need attention first
- understand why those records matter
- know what to check next
- leave a review trail that can be revisited later

## Target Workflow

The target workflow is:

1. Import spreadsheet records.
2. Standardise data into a canonical structure.
3. Run deterministic rule checks and bounded risk checks.
4. Map findings into VAT / MTD review categories.
5. Assign review status and risk level.
6. Explain why each finding matters and what it may affect.
7. Suggest the next manual check.
8. Let the user record a decision, note, and evidence checked.
9. Produce a pre-submission review summary.

## Design Consequence

The codebase should therefore evolve from a pipeline that only reports issues into a system that supports a full pre-submission review loop:

- detection
- interpretation
- prioritisation
- manual decision capture
- traceable summary output

This document should be treated as the current product and system-direction baseline for further rule design, schema design, workflow design, code changes, and evaluation planning.
