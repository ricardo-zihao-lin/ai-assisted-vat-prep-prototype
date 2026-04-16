# VAT Review Rules for Pre-Submission Record Checking

## 1. Purpose and Scope

This document defines implementation-oriented review rules for a local-first, human-in-the-loop prototype that supports pre-submission review of spreadsheet-based VAT records before VAT return preparation.

The purpose of these rules is to help identify records that are clearly invalid, potentially problematic, incomplete, or in need of structured manual review before VAT figures are prepared for submission. The system is intended to support review, correction, explanation, and decision logging. It is not intended to make final tax decisions.

This document is designed for a workflow in which the system:

1. Imports spreadsheet records.
2. Standardises column names and record structure.
3. Runs deterministic checks and risk-signal checks.
4. Maps issues into VAT/MTD review categories.
5. Assigns status and risk level.
6. Explains why the issue matters and its possible VAT review impact.
7. Suggests a manual review action.
8. Supports recording user decisions, notes, evidence checked, and timestamps.
9. Produces a pre-submission review summary.

This document does not define logic for:

- VAT return submission to HMRC
- final VAT liability calculation as a legal conclusion
- automated tax advice
- complete legal compliance certification
- penalty handling
- full accounting software behaviour
- replacing a qualified accountant or tax adviser

## 2. Review Philosophy

The prototype should apply three types of review logic.

### 2.1 Deterministic checking

Deterministic checks should be used where the system can reliably detect a concrete data or record-quality issue from the imported spreadsheet alone.

Typical examples include:

- missing required fields
- invalid date format
- non-numeric amounts
- exact duplicate rows
- arithmetic inconsistency between related numeric fields

These checks are appropriate because they are explainable, repeatable, and can be implemented without making legal or commercial assumptions.

### 2.2 Risk signals

Some patterns cannot be treated as definitive non-compliance, but they are reasonable indicators that a record may require review before VAT preparation.

Typical examples include:

- unusually high `net_amount`
- repeated invoice references
- blank description with otherwise valid numeric values
- missing supplier or customer reference
- unusual dates near period boundaries

These checks should not automatically state that the VAT treatment is wrong. They should instead trigger structured user review.

### 2.3 Judgements reserved for the user

Some decisions require supporting evidence, business context, or tax interpretation that the system does not possess. These must remain with the user.

Typical examples include:

- whether an expense is recoverable for VAT purposes
- whether a transaction belongs in a given VAT period after considering the underlying evidence
- whether a duplicate-looking entry is a true duplicate or a legitimate repeat
- whether an unusual amount is valid because of a one-off business event

The system should therefore emphasise:

- explainability: each issue must say what was detected and why it matters
- traceability: each user decision must be logged with note and evidence reference
- bounded automation: the system assists review but does not replace professional judgement

## 3. Review Status Categories

### 3.1 Non-compliant

**Definition**

A record has a clear, direct, and detectable issue that prevents it from being treated as review-ready for VAT preparation in its current form.

**Typical conditions**

- a required field is missing
- a date field cannot be parsed
- a numeric field required for review is non-numeric
- the row is an exact duplicate of another row
- related amounts fail a defined arithmetic consistency rule

**Expected user action**

The user should correct the record, confirm exclusion, or document why the apparent issue is acceptable in context before the record is treated as review-complete.

### 3.2 Potentially non-compliant

**Definition**

A record contains a strong indication of potential record-quality or VAT review risk, but the system cannot determine from the spreadsheet alone whether the record is truly wrong.

**Typical conditions**

- a repeated invoice reference appears across multiple rows
- evidence or reference fields are missing where they would normally support traceability
- amounts are unusual relative to the dataset
- a date falls outside the expected period window
- transaction details are too limited to support confident review

**Expected user action**

The user should inspect source documents, confirm whether the record is valid, and log the decision with supporting note or evidence reference.

### 3.3 Review required

**Definition**

A record is not clearly invalid, but there is insufficient confidence, context, or supporting detail for the system to treat it as low-risk.

**Typical conditions**

- description is blank or vague
- supplier/customer identifier is missing
- the record is structurally valid but lacks traceability
- transaction timing or amount appears unusual but not clearly wrong

**Expected user action**

The user should perform a targeted manual review, record what was checked, and either confirm the record, correct it, or escalate outside the system.

### 3.4 Status Mapping Table

The prototype should apply status consistently so that developers, reviewers, and users understand what each result means operationally.

| Status | Operational meaning | When to use it | Typical examples | Default user action |
|---|---|---|---|---|
| `Non-compliant` | The record contains a directly detectable issue that makes it not review-ready in its current form | Use when the rule identifies a concrete failure in required structure, format, or arithmetic consistency | missing transaction date, invalid date format, non-numeric VAT amount, exact duplicate row, inconsistent totals | Correct the record, exclude it, or document a justified exception before treating it as resolved |
| `Potentially non-compliant` | The system has detected a strong risk indicator, but cannot conclude from spreadsheet data alone that the record is definitively wrong | Use when the pattern is suspicious and materially relevant, but still needs evidence-based confirmation | duplicate invoice reference, missing VAT amount, missing evidence reference, date outside review period, conflicting amount sign pattern | Review source evidence, confirm whether the issue is real, and record the decision with note and evidence checked |
| `Review required` | The record is not clearly invalid, but the available data is insufficient for confident review or traceability | Use when the record needs human inspection because detail, context, or support fields are weak rather than clearly invalid | missing supplier/customer reference, blank description, unusual net amount, missing transaction type/category support field | Perform targeted manual review, add context or correction if needed, and log the outcome |

## 4. Risk Levels

### 4.1 High

A high-risk issue is likely to materially affect pre-submission review quality, record completeness, traceability, or amount reliability.

Typical examples:

- missing transaction date
- missing or invalid amount
- exact duplicate row
- inconsistent totals
- missing evidence/reference for a high-value or unusual transaction

### 4.2 Medium

A medium-risk issue may not invalidate the record, but it introduces meaningful uncertainty or increases the chance of review error.

Typical examples:

- duplicate invoice reference
- missing supplier/customer reference
- blank description
- outlier `net_amount`

### 4.3 Low

A low-risk issue has limited direct impact on the record's core usability, but it still reduces transparency or review efficiency.

Typical examples:

- weak narrative description where other references exist
- minor traceability gaps in otherwise low-value records

### 4.4 Relationship Between Status and Risk

Status and risk should be related but not identical.

- `Non-compliant` issues are usually `High` risk, but may be `Medium` if the issue is narrow and easily resolvable.
- `Potentially non-compliant` issues may be `High` or `Medium` depending on likely impact.
- `Review required` issues are commonly `Medium` or `Low`, but may be `High` where the missing context affects a material transaction.

A practical implementation should avoid assuming that every high-risk issue is definitively non-compliant.

## 5. Rule Categories

### 5.1 Required Field Presence

**What the system checks**

Whether essential fields required for record review are present and non-blank.

**Why it matters**

A record cannot be reliably reviewed if core identifiers, dates, or amounts are missing.

**Typical failure patterns**

- missing transaction date
- missing `net_amount`
- missing VAT amount where expected in the dataset
- missing transaction description

**Likely status mapping**

- `Non-compliant` for core fields needed to interpret the record
- `Review required` for supporting fields

**Likely risk mapping**

- `High` for missing date or amount
- `Medium` for missing descriptive or reference fields

**Suggested manual review action**

Check the source document or ledger export, fill the missing value if known, or mark the record for exclusion or escalation.

### 5.2 Date Validity and Period Review

**What the system checks**

Whether date fields are parseable, logically valid, and plausibly aligned with the review period.

**Why it matters**

Dates are central to period review, record sequencing, and determining whether a record should be considered in the current review set.

**Typical failure patterns**

- unparseable date string
- impossible date
- missing date
- date outside expected review window

**Likely status mapping**

- `Non-compliant` for missing or invalid dates
- `Potentially non-compliant` or `Review required` for period-boundary concerns

**Likely risk mapping**

- `High` for invalid or missing dates
- `Medium` for period mismatch signals

**Suggested manual review action**

Check the source invoice, receipt, or export file; confirm the correct transaction date and whether the record belongs in the reviewed set.

### 5.3 Numeric Validity

**What the system checks**

Whether amount fields are present where needed and can be parsed as valid numeric values.

**Why it matters**

Amounts are necessary for reviewing transaction magnitude and preparing VAT-related figures.

**Typical failure patterns**

- non-numeric VAT amount
- non-numeric net amount
- blank amount field
- text, symbols, or malformed numbers in amount columns

**Likely status mapping**

- `Non-compliant`

**Likely risk mapping**

- `High`

**Suggested manual review action**

Compare against the source document or export and correct the value formatting or underlying entry.

### 5.4 Duplicate Transaction Risk

**What the system checks**

Whether rows are exact duplicates or whether key identifiers suggest that the same transaction may appear more than once.

**Why it matters**

Duplicate records can lead to overstatement, confusion during review, or repeated inclusion in preparation work.

**Typical failure patterns**

- identical duplicate row
- same invoice reference repeated across records
- same date, counterparty, and amount repeated

**Likely status mapping**

- `Non-compliant` for exact duplicate row
- `Potentially non-compliant` for duplicate reference or near-duplicate pattern

**Likely risk mapping**

- `High` for exact duplicates
- `Medium` or `High` for duplicate references depending on amount and frequency

**Suggested manual review action**

Compare the candidate duplicate records, verify whether they reflect true duplication, instalments, credit notes, split lines, or legitimate repeated transactions.

### 5.5 Amount Consistency

**What the system checks**

Whether related numeric fields are internally consistent according to the rule set defined for the dataset.

**Why it matters**

Arithmetic inconsistency suggests entry error, transformation error, or incomplete data.

**Typical failure patterns**

- total does not reconcile with net plus VAT
- one amount present but related amount missing
- sign mismatch across related amount fields

**Likely status mapping**

- `Non-compliant` if arithmetic rules are defined and violated
- `Review required` if the dataset structure is incomplete

**Likely risk mapping**

- `High`

**Suggested manual review action**

Inspect the source record, confirm whether the spreadsheet uses gross, net, and VAT columns consistently, and correct or annotate exceptions.

### 5.6 Reference and Evidence Traceability

**What the system checks**

Whether the record includes references that support traceability to source evidence or external records.

**Why it matters**

A valid-looking row with weak traceability is harder to verify and less defensible during manual review.

**Typical failure patterns**

- missing invoice number
- missing supplier/customer reference
- missing evidence link or file reference
- missing document identifier in otherwise material transaction

**Likely status mapping**

- `Review required` or `Potentially non-compliant`

**Likely risk mapping**

- `Medium` or `High` depending on transaction materiality

**Suggested manual review action**

Locate and record the source document reference, add supplier/customer identifier, and log the evidence reviewed.

### 5.7 Digital Record Completeness

**What the system checks**

Whether the spreadsheet row contains enough structured information to support review as a digital business record.

**Why it matters**

Pre-submission review depends on more than amounts alone; incomplete records reduce confidence and auditability.

**Typical failure patterns**

- blank description
- missing transaction category or type where the dataset expects one
- insufficient detail to understand what the transaction represents

**Likely status mapping**

- `Review required`

**Likely risk mapping**

- `Medium` or `Low`

**Suggested manual review action**

Expand the record detail using source evidence and add enough description or reference to support future review.

### 5.8 Unusual Transaction Review

**What the system checks**

Whether a transaction is statistically unusual relative to the dataset, such as an IQR outlier on `net_amount`.

**Why it matters**

Unusual transactions may be legitimate, but they deserve attention because they are more likely to contain entry, classification, or omission issues.

**Typical failure patterns**

- unusually high `net_amount`
- unusually low or negative values if included in the rule set
- isolated values far from the main distribution

**Likely status mapping**

- `Review required` or `Potentially non-compliant`

**Likely risk mapping**

- `Medium` or `High` depending on materiality

**Suggested manual review action**

Check supporting evidence, confirm business context, and record why the unusual amount is valid or what correction was made.

## 6. Implementable Rule List

| Rule ID | Rule name | Description | Required input fields | Detection logic | Output status | Risk level | Why it matters | Recommended manual check | Type |
|---|---|---|---|---|---|---|---|---|---|
| VR001 | Missing transaction date | Flags records with no transaction date value | `transaction_date` | Field is null, blank, or whitespace after normalisation | Non-compliant | High | The record cannot be reliably placed in time or reviewed for period relevance | Check source invoice, receipt, or ledger export and enter the correct date | Deterministic |
| VR002 | Invalid date format | Flags unparseable or invalid date values | `transaction_date` | Date parser fails or value is impossible | Non-compliant | High | Invalid dates reduce reliability of period review and record integrity | Confirm the original date format and correct the field | Deterministic |
| VR003 | Date outside review period | Flags records outside the configured review period or tolerance window | `transaction_date`, review period config | Parsed date is before or after the review period bounds | Potentially non-compliant | Medium | The record may have been included in the wrong pre-submission review set | Verify whether the transaction belongs in this review period and document the decision | Partly deterministic |
| VR004 | Missing net amount | Flags records with no net amount | `net_amount` | Field is null, blank, or whitespace | Non-compliant | High | Missing base amount prevents reliable review of the transaction magnitude | Check the source record and supply the missing amount or exclude the record | Deterministic |
| VR005 | Non-numeric net amount | Flags net amounts that cannot be parsed numerically | `net_amount` | Numeric parser fails after permitted cleaning rules | Non-compliant | High | A non-numeric amount cannot be reviewed or reconciled | Correct formatting or replace with the proper numeric value from source evidence | Deterministic |
| VR006 | Missing VAT amount | Flags missing VAT amount where the dataset includes a VAT amount column used for review | `vat_amount` | Field is blank in a dataset where VAT amount is expected | Potentially non-compliant | High | The absence may indicate incomplete record preparation or missing VAT detail | Confirm whether VAT should be present, whether the value is zero, or whether the field is missing in error | Partly deterministic |
| VR007 | Non-numeric VAT amount | Flags VAT amounts that cannot be parsed numerically | `vat_amount` | Numeric parser fails after permitted cleaning rules | Non-compliant | High | Invalid VAT values reduce reliability of pre-submission preparation | Check the source record and correct the value | Deterministic |
| VR008 | Exact duplicate row | Flags rows that are identical across the selected duplicate key or full-row signature | full normalised row or duplicate key fields | Hash or field-comparison match identifies identical duplicate rows | Non-compliant | High | Exact duplication can cause repeated inclusion in review and preparation | Compare both rows and decide which entry should be retained, excluded, or annotated | Deterministic |
| VR009 | Duplicate invoice reference | Flags repeated invoice or document references | `invoice_reference` or equivalent | Same non-blank reference appears in multiple records | Potentially non-compliant | Medium | Repeated references may indicate duplication, split posting, or legitimate reuse that needs confirmation | Review the related records and confirm whether they represent one transaction, split lines, or separate valid entries | Partly deterministic |
| VR010 | Near-duplicate transaction pattern | Flags records with matching date, amount, and counterparty pattern | `transaction_date`, `net_amount`, `counterparty_ref` or name | Matching or highly similar key combination appears multiple times | Potentially non-compliant | Medium | Similar records may indicate double entry or repeated import | Inspect source evidence and determine whether the records are duplicates or legitimate repeats | Partly deterministic |
| VR011 | Inconsistent totals | Flags records where gross does not reconcile with net plus VAT within tolerance | `net_amount`, `vat_amount`, `gross_amount` | `abs((net_amount + vat_amount) - gross_amount) > tolerance` | Non-compliant | High | Arithmetic inconsistency suggests entry or transformation error | Confirm the source values and correct the inconsistent field | Deterministic |
| VR012 | Missing supplier/customer reference | Flags records lacking counterparty identifier | `supplier_ref` or `customer_ref` | Field is blank or null | Review required | Medium | Weak counterparty traceability makes validation harder and reduces review confidence | Add the supplier/customer reference from the source document or note why unavailable | Deterministic |
| VR013 | Blank description with otherwise valid record | Flags records with no narrative description despite valid date and amounts | `description`, `transaction_date`, `net_amount` | Description blank while core fields are present | Review required | Medium | A record may be structurally valid but still too unclear to review confidently | Check source evidence and add a short meaningful description | Deterministic |
| VR014 | Missing evidence/reference field | Flags absence of document ID, attachment reference, or evidence link where such field exists | `document_reference` or evidence field | Field blank or null | Potentially non-compliant | Medium | Missing evidence linkage weakens traceability and later review | Record the invoice, receipt, file name, or evidence identifier used to support the transaction | Deterministic |
| VR015 | Unusually high net amount | Flags `net_amount` outliers using the configured IQR rule | `net_amount` | Value exceeds upper outlier threshold based on dataset IQR logic | Review required | Medium | Outliers are more likely to reflect one-off events, entry errors, or transactions needing closer review | Check source evidence and confirm whether the amount is correct and expected | Partly deterministic |
| VR016 | Unusually low or negative net amount | Flags negative or unusually low outlier values if enabled | `net_amount` | Value is negative when unexpected, or below lower outlier threshold | Review required | Medium | Negative or unusual low values may be valid, but often need interpretation | Confirm whether the entry is a refund, credit, reversal, or error | Partly deterministic |
| VR017 | Missing key fields for digital record completeness | Flags records lacking the minimum structured detail defined by the prototype | configured required review fields | One or more configured completeness fields missing | Review required | Medium | Incomplete structured records reduce explainability and traceability | Add the missing structured detail or document why not available | Deterministic |
| VR018 | Suspicious zero-value amount combination | Flags records where net, VAT, and gross values are all zero or unexpectedly blank-equivalent | `net_amount`, `vat_amount`, `gross_amount` | All relevant amounts equal zero, where this pattern is not expected | Review required | Low | Zero-value records may be valid but can indicate placeholder or incomplete entries | Confirm whether the record should exist in the review set and annotate the reason | Partly deterministic |
| VR019 | Missing transaction type/category support field | Flags missing transaction type or category where the dataset relies on it for review interpretation | `transaction_type` or category field | Field blank in a dataset configured to use it | Review required | Low | Missing context reduces the reviewer's ability to understand the transaction | Check the source classification and fill the field if available | Deterministic |
| VR020 | Conflicting amount sign pattern | Flags cases where one related amount is negative and others are positive without expected pattern | `net_amount`, `vat_amount`, `gross_amount` | Signs do not align with the configured arithmetic pattern | Potentially non-compliant | High | Sign inconsistency may indicate reversal error or malformed import | Verify whether the record is a credit, refund, or incorrectly entered transaction | Partly deterministic |

## 7. Rules Suitable for Deterministic Checking

The following rules are the strongest candidates for an undergraduate prototype because they are transparent, feasible, and defensible:

- missing transaction date
- invalid date format
- missing net amount
- non-numeric net amount
- non-numeric VAT amount
- exact duplicate row
- inconsistent totals
- missing supplier/customer reference
- blank description
- missing evidence/reference field
- missing configured required review fields

These rules fit the prototype well because they:

- can be implemented directly from spreadsheet data
- produce clear user explanations
- do not require advanced tax interpretation
- support auditable review output
- align well with human-in-the-loop correction workflow

A sensible implementation priority is:

1. Required field presence
2. Date validity
3. Numeric validity
4. Exact duplicate detection
5. Amount consistency
6. Traceability and completeness checks
7. Outlier-based unusual transaction review

## 8. Rules That Should Only Trigger Manual Review

The following conditions should not be treated as definitive violations by the system:

- date outside review period
- duplicate invoice reference
- near-duplicate transaction pattern
- unusually high `net_amount`
- unusually low or negative amount where credits or reversals may exist
- missing supplier/customer reference in low-detail legacy exports
- blank description where source evidence may still be sufficient
- missing evidence field where the evidence exists externally but has not yet been linked
- transactions close to period boundaries
- one-off high-value transactions

These should produce a review prompt, not an automated tax conclusion. The user should be asked to confirm the record against evidence and log the outcome.

## 9. Out-of-Scope Judgements

The system should not automatically determine:

- final VAT liability
- whether a transaction is legally recoverable for VAT in an ambiguous case
- complete legal compliance in all respects
- whether a record set guarantees compliance with HMRC expectations
- final legal interpretation of timing, treatment, or exception cases
- late submission penalties
- late payment penalties
- professional tax advice
- final filing decisions
- whether a business is fully compliant overall

The system should instead state that it supports pre-submission review and correction, not final legal or tax judgement.

## 10. Mapping to User-Facing Output

Each flagged issue should be represented as a structured output object. At minimum, the system should produce:

- `issue_id`: unique identifier for this flagged issue instance
- `rule_id`: identifier of the rule that triggered
- `issue_type`: short machine-readable label
- `record_id`: internal record identifier or row reference
- `category`: VAT/MTD review category
- `status`: `Non-compliant`, `Potentially non-compliant`, or `Review required`
- `risk_level`: `High`, `Medium`, or `Low`
- `field_names`: fields involved in the issue
- `detected_value`: value or summary of the problematic content
- `detection_summary`: short explanation of what the system detected
- `why_it_matters`: explanation of why the issue matters for pre-submission review
- `possible_vat_review_impact`: explanation of the possible review consequence
- `recommended_manual_check`: specific user action to verify or correct the issue
- `evidence_expected`: optional description of the evidence that may help resolve it
- `determinism_type`: `Deterministic`, `Partly deterministic`, or `Manual only`
- `detected_at`: timestamp of system detection
- `review_state`: current user workflow state such as `open`, `reviewed`, `resolved`, `escalated`

A concise example structure is:

```json
{
  "issue_id": "ISSUE-000123",
  "rule_id": "VR011",
  "issue_type": "inconsistent_totals",
  "record_id": "ROW-45",
  "category": "Amount consistency",
  "status": "Non-compliant",
  "risk_level": "High",
  "field_names": ["net_amount", "vat_amount", "gross_amount"],
  "detected_value": {
    "net_amount": 100.00,
    "vat_amount": 20.00,
    "gross_amount": 150.00
  },
  "detection_summary": "Gross amount does not reconcile with net amount plus VAT amount.",
  "why_it_matters": "Arithmetic inconsistency reduces confidence in the record and may affect preparation of VAT figures.",
  "possible_vat_review_impact": "The transaction may be reviewed incorrectly or require correction before inclusion in pre-submission preparation.",
  "recommended_manual_check": "Check the source invoice or export and confirm which amount is incorrect.",
  "evidence_expected": "Invoice or transaction source document",
  "determinism_type": "Deterministic",
  "detected_at": "2026-04-14T10:30:00Z",
  "review_state": "open"
}
```

## 11. Decision Logging Guidance

The prototype should require or strongly encourage a user review log entry when a flagged issue is reviewed. Each decision log should capture:

- `issue_id`
- `record_id`
- `reviewer_decision`
- `decision_reason`
- `note`
- `evidence_checked`
- `timestamp`
- `correction_made`
- `corrected_fields`
- `final_record_status`
- `needs_escalation`

Recommended decision values include:

- `confirmed_issue`
- `false_positive`
- `corrected`
- `accepted_with_note`
- `excluded_from_review_set`
- `escalated`

Recommended evidence logging should be explicit rather than vague. For example:

- invoice number checked
- receipt reviewed
- supplier statement checked
- source spreadsheet compared
- supporting file reference verified

A practical review log entry should answer:

- What did the system flag?
- What did the reviewer check?
- What decision was made?
- What evidence supported the decision?
- Was the record corrected?
- When was the decision made?

This is important for transparency, repeatability, and demonstrating that the system supports a structured review process rather than opaque automation.

## 12. Design Notes for an Undergraduate Prototype

The prototype should prioritise a narrow but well-executed scope.

### 12.1 Prioritise deterministic rules first

The strongest implementation path is to build reliable checks for:

- missing values
- invalid dates
- invalid numeric values
- duplicate rows
- duplicate references
- arithmetic inconsistency
- outlier detection on `net_amount`
- missing traceability fields

These give strong demonstration value without requiring complex tax inference.

### 12.2 Prioritise explainability over sophistication

For each issue, the system should clearly show:

- what was detected
- which fields were involved
- why the issue matters
- what the user should check next

A simpler but well-explained rule set is better than a more complex system that cannot justify its outputs.

### 12.3 Prioritise traceability over automation claims

The prototype should be designed so that each issue can be:

- traced back to a rule
- traced back to a source row
- reviewed by a user
- resolved with a recorded decision and timestamp

This supports the project's core value as a pre-submission review assistant.

### 12.4 Avoid presenting the system as an automatic tax decision-maker

The system should not claim to:

- decide correct VAT treatment in all cases
- guarantee compliance
- replace professional judgement
- remove the need for evidence checking

Instead, it should present outputs as review support signals.

### 12.5 Keep the user interaction structured

The user-facing workflow should consistently move from:

1. issue detected
2. explanation shown
3. manual check suggested
4. user decision recorded
5. issue marked resolved or escalated

This structure is more valuable for the project than attempting full accounting functionality.

### 12.6 Use risk and status carefully

A useful prototype should separate:

- certainty of the detected issue
- severity of possible review impact

This is why both `status` and `risk_level` should be stored and displayed.

### 12.7 Core project value

The prototype's main value is not automatic VAT judgement. Its value is helping users conduct a more structured, transparent, and evidence-based pre-submission review of spreadsheet records before VAT preparation.

Accordingly, the system should be framed as:

- local-first
- review-oriented
- human-in-the-loop
- explainable
- traceable
- limited in scope, but practically useful for reducing avoidable record-review errors before submission
