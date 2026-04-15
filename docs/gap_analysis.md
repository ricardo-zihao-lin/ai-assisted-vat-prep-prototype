# Gap Analysis for VAT Pre-Submission Review Prototype

## 1. Purpose

This document analyses the gap between the prototype's current implemented capabilities and the revised project objective.

The original implementation direction was closer to a spreadsheet validation and anomaly detection tool. The revised project direction is more specific and more suitable for the stated dissertation aim:

**a local-first, human-in-the-loop VAT pre-submission review and correction support prototype**

The purpose of this gap analysis is to:

- identify what the current system already does well
- identify what is missing for the revised project goal
- separate essential gaps from optional enhancements
- support realistic implementation planning for the MVP

This document is intended to support both development planning and dissertation justification.

## 2. Revised Target State

The target system is not simply a record validation tool.

It should support a pre-submission review workflow in which the system:

1. imports spreadsheet records
2. standardises them into a normalised structure
3. runs deterministic checks and review-risk checks
4. maps findings into VAT/MTD review categories
5. classifies them by status and risk level
6. explains why they matter
7. suggests a manual review action
8. allows the user to record decisions, notes, and evidence checked
9. generates a pre-submission review summary

This target state requires the system to move beyond error detection into structured review support.

## 3. Current System Baseline

Based on the current project description, the system already has the following capabilities:

- CSV and Excel import
- column name standardisation
- deterministic checks for:
  - missing values
  - duplicate rows
  - invalid date format
  - invalid numeric values
- IQR-based anomaly detection on `net_amount`
- output generation for:
  - dataset snapshot
  - issue report
  - review log

These are strong foundations for the revised prototype, especially because they already cover:

- data ingestion
- normalisation
- core record-quality checks
- unusual amount detection
- report generation

However, these capabilities mainly support validation and anomaly detection rather than full human-in-the-loop pre-submission review workflow.

## 4. High-Level Gap Summary

The main gap is not that the current system lacks all useful functionality. The main gap is that the current system is not yet fully framed or implemented as a structured VAT pre-submission review support tool.

At a high level:

- the current system can detect some issues
- the revised system must also classify, explain, guide review, log decisions, and summarise outcomes

This means the key gap areas are:

- issue interpretation and classification
- user-facing explainability
- review workflow support
- structured decision logging
- explicit pre-submission summary generation
- careful scoping and bounded claims

## 5. Gap Categories

## 5.1 Data Import and Normalisation

### Current state

The system already supports:

- CSV/Excel import
- column name standardisation

### Gap assessment

This area is relatively mature for MVP purposes.

### Remaining gaps

- internal field mapping may need to be made more explicit and documented
- record identifiers may need to be formalised
- normalised record structure may need clearer persistence for downstream issue linkage

### Priority

Low to medium.

### Conclusion

This is not a major functional gap. It is mainly a documentation and schema formalisation gap.

## 5.2 Deterministic Validation Logic

### Current state

The system already performs:

- missing value checks
- duplicate row checks
- invalid date checks
- invalid numeric checks

### Gap assessment

This is one of the strongest existing areas.

### Remaining gaps

- checks may need to be re-labelled and organised into VAT/MTD review categories
- rule outputs may need more structured metadata such as `rule_id`, `status`, and `risk_level`
- additional deterministic checks such as inconsistent totals may need to be added if not already implemented

### Priority

Medium.

### Conclusion

The gap is not the absence of validation logic, but the need to reframe and extend it into a formal rule set for pre-submission review.

## 5.3 Unusual Transaction Review

### Current state

The system already uses IQR-based outlier detection on `net_amount`.

### Gap assessment

This provides a useful starting point for unusual transaction review.

### Remaining gaps

- the output must be reframed as a review signal, not a compliance conclusion
- the outlier finding must be linked to issue classification and manual review action
- explanation text should clarify why unusual values matter in review terms

### Priority

Low to medium.

### Conclusion

The underlying analytical capability already exists. The main gap is interpretive framing and workflow integration.

## 5.4 Issue Structuring and Classification

### Current state

The system can produce issue reports, but the current project description does not indicate a fully formal issue schema with status/risk classification.

### Gap assessment

This is a significant gap.

### Missing capabilities

- structured issue object model
- formal `issue_id`
- rule-to-issue mapping
- issue category assignment
- status classification:
  - `Non-compliant`
  - `Potentially non-compliant`
  - `Review required`
- risk classification:
  - `High`
  - `Medium`
  - `Low`
- standard explanation fields
- standard manual review guidance

### Priority

High.

### Conclusion

This is one of the most important gaps because it turns raw detections into operational review outputs.

## 5.5 Explainability Layer

### Current state

The existing system description suggests issue reporting, but not necessarily a detailed explanation layer for each flagged finding.

### Gap assessment

This is a major gap relative to the revised project goal.

### Missing capabilities

- `why_it_matters`
- `possible_vat_review_impact`
- `recommended_manual_check`
- user-facing explanation templates per rule

### Priority

High.

### Conclusion

Without explainability, the system remains closer to a validation checker than a human-in-the-loop review support tool.

## 5.6 Human-in-the-Loop Review Workflow

### Current state

The current description does not clearly indicate a structured workflow for moving from detection to user review to logged outcome.

### Gap assessment

This is a critical gap.

### Missing capabilities

- issue review states
- explicit review interaction flow
- progression from open issue to reviewed outcome
- linkage between issue and user action

### Priority

High.

### Conclusion

This gap is central because the revised project identity depends on human-in-the-loop review rather than passive reporting alone.

## 5.7 Decision Logging and Evidence Recording

### Current state

The system already outputs a review log, but the current description does not show whether it captures structured decisions, evidence checked, and correction details in a formal schema.

### Gap assessment

This is a major gap if the current review log is only basic or unstructured.

### Missing capabilities

- formal decision log schema
- decision type enumeration
- evidence checked field
- timestamped review outcome
- correction details
- escalation support

### Priority

High.

### Conclusion

Decision logging is essential for traceability and is one of the key additions required by the revised project scope.

## 5.8 Review Summary Generation

### Current state

The system currently outputs reports, but the current description does not indicate a formal pre-submission review summary object that consolidates issue and decision outcomes.

### Gap assessment

This is a medium-to-high gap.

### Missing capabilities

- total issue and record metrics
- issue counts by status and risk
- decision outcome aggregation
- unresolved and escalated item reporting
- bounded narrative summary

### Priority

Medium to high.

### Conclusion

This is important for final usability, evaluation, and dissertation presentation.

## 5.9 User Interface Support for Review

### Current state

The current description does not fully specify whether the interface supports structured issue review, status display, and decision capture.

### Gap assessment

This is likely a major practical gap, depending on the current GUI state.

### Missing or potentially incomplete capabilities

- issue list with status and risk
- issue detail view
- review action controls
- decision logging form elements
- visibility of unresolved high-risk items

### Priority

High for demonstrable MVP.

### Conclusion

Even if the backend logic exists, the prototype cannot clearly demonstrate human-in-the-loop review without a usable review interface.

## 5.10 Scope Control and Claim Management

### Current state

The original framing of the project may risk presenting the system as a broader validation or compliance tool than intended.

### Gap assessment

This is a conceptual and documentation gap rather than a code-only gap.

### Missing elements

- explicit boundary statements
- careful wording around compliance
- clear out-of-scope judgements

### Priority

High for dissertation quality and academic defensibility.

### Conclusion

This gap must be addressed in documentation, UI wording, and evaluation narrative.

## 6. Gap Table

| Area | Current capability | Gap level | Why it matters | MVP response |
|---|---|---|---|---|
| Import | CSV/Excel import already available | Low | Import is already functional | Retain and document clearly |
| Normalisation | Column standardisation already available | Low | Needed for rule consistency | Formalise field mapping and record IDs |
| Deterministic checks | Missing, duplicate, invalid date, invalid numeric checks exist | Medium | Must be framed as review rules | Organise into formal rule set |
| Amount consistency checks | Not clearly confirmed in baseline | Medium | Important for review integrity | Add if missing |
| Outlier detection | IQR on `net_amount` already available | Low | Useful review signal | Reframe as manual-review trigger |
| Issue schema | Not clearly formalised | High | Needed for structured outputs | Implement issue schema |
| Status/risk mapping | Not clearly formalised | High | Needed for review prioritisation | Implement classification model |
| Explainability | Likely partial or missing | High | Core to revised system goal | Add explanation and guidance fields |
| Manual review workflow | Not clearly formalised | High | Core human-in-the-loop requirement | Implement issue lifecycle workflow |
| Decision logging | Review log exists but may be under-specified | High | Needed for traceability | Implement structured decision log |
| Review summary | Not clearly formalised | Medium to High | Needed for final workflow output | Implement review summary schema |
| UI review support | Unclear or incomplete | High | Needed for demonstrable use | Add issue review and decision UI |
| Scope control | Needs stronger project framing | High | Important for academic credibility | Tighten claims and out-of-scope statements |

## 7. Most Critical Gaps for the MVP

The most critical gaps are:

1. structured issue classification
2. explainable issue outputs
3. human-in-the-loop review workflow
4. structured decision logging
5. final review summary generation
6. careful scoping and bounded system claims

These are more important than adding many new detection algorithms.

## 8. Gap Analysis by Project Layer

## 8.1 Existing technical base

The technical base is already strong enough for an MVP because the project already includes:

- file ingestion
- standardisation
- basic validation
- anomaly detection
- report generation

This means the prototype does not need to start from zero.

## 8.2 Missing workflow integration

The biggest weakness is workflow integration.

The current baseline appears stronger at:

- detecting issues

than at:

- guiding review
- capturing human decisions
- closing the loop with summary output

## 8.3 Missing product framing

The revised project requires the prototype to be presented as:

- a review support tool

rather than:

- a validation-only tool
- a compliance engine

This framing change is important for both system design and dissertation writing.

## 9. Recommended MVP Response to the Gaps

The best response is not to build a much larger system. The best response is to build a better-structured one.

Recommended MVP development priorities:

1. preserve the current import and validation pipeline
2. formalise rule definitions and issue outputs
3. add status and risk classification
4. add explanation fields and manual review prompts
5. implement structured decision logging
6. implement issue review-state updates
7. implement review summary generation
8. align UI wording and documentation with bounded claims

This approach reuses existing work while directly addressing the revised project aim.

## 10. Implications for Dissertation Positioning

This gap analysis supports a stronger dissertation narrative.

Instead of claiming to build a general VAT compliance system, the project can be positioned as:

- an explainable review-support prototype
- a human-in-the-loop pre-submission checking workflow
- a local-first tool for reducing avoidable record-preparation risk

This is academically stronger because it:

- matches the realistic scope of the implementation
- avoids overclaiming
- highlights design choices around explainability and traceability
- shows clear progression from baseline validation tool to structured review-support prototype

## 11. Risks if the Gaps Are Not Addressed

If the identified gaps are not addressed, the project risks being evaluated as:

- too close to a generic spreadsheet validator
- insufficiently connected to VAT pre-submission review practice
- lacking a clear human-in-the-loop contribution
- weak on traceability and explainability
- conceptually over-claiming relative to implementation

Addressing the gaps therefore improves both technical coherence and dissertation defensibility.

## 12. Summary

The current system already provides a useful technical foundation through import, normalisation, validation, and anomaly detection.

The main gaps are not primarily about missing advanced analytics. They are about missing structure around:

- issue classification
- explanation
- manual review workflow
- decision logging
- review summary generation
- bounded system framing

For the MVP, the correct response is to convert the current system from a validation-oriented tool into a structured, explainable, and traceable VAT pre-submission review support prototype.
