# Evaluation Plan for VAT Pre-Submission Review Prototype

## 1. Purpose

This document defines the evaluation plan for the local-first, human-in-the-loop prototype for pre-submission VAT record review.

The purpose of the evaluation is to assess whether the prototype is effective as a review-support tool for spreadsheet-based VAT record preparation before submission activity.

The evaluation is not intended to prove that the system:

- performs final tax judgement
- guarantees legal compliance
- replaces an accountant
- eliminates submission risk entirely

Instead, the evaluation should assess whether the prototype successfully supports:

- detection of review-relevant record issues
- explainable presentation of those issues
- structured manual review
- traceable decision logging
- generation of a useful pre-submission review summary

## 2. Evaluation Goal

The overall evaluation goal is:

> To determine whether the prototype provides a practical, explainable, and traceable workflow for identifying and reviewing potentially problematic spreadsheet records before VAT preparation proceeds further.

This goal aligns with the revised project scope as a pre-submission review and correction support prototype rather than an automated compliance engine.

## 3. Evaluation Principles

The evaluation should follow these principles:

- **Scope alignment**: evaluation criteria should match the prototype's actual purpose.
- **Realistic claims**: the system should be evaluated as a review-support tool, not as a full VAT decision system.
- **Mixed evidence**: use both technical and user/workflow-oriented evaluation where possible.
- **Traceability focus**: assess whether outputs are understandable and review actions can be followed.
- **Prototype realism**: measures should be feasible for an undergraduate project with limited data, time, and participant access.

## 4. Evaluation Questions

The evaluation should answer the following main questions.

## 4.1 Functional Evaluation Questions

- Can the prototype import and normalise spreadsheet records reliably?
- Can the prototype detect deterministic record-quality issues correctly on prepared test data?
- Can the prototype generate structured issues with appropriate status and risk labels?
- Can the prototype support end-to-end issue review and decision logging?
- Can the prototype generate a coherent pre-submission review summary?

## 4.2 Explainability and Workflow Evaluation Questions

- Are flagged issues presented in a way that a user can understand?
- Do the explanations and manual-check suggestions help users know what to review?
- Does the workflow clearly support human judgement rather than replacing it?
- Does the decision log provide a traceable record of what was reviewed and what was decided?

## 4.3 Practical Usefulness Questions

- Does the prototype help identify records that deserve attention before VAT preparation?
- Does the prototype make review work more structured than using an unassisted spreadsheet alone?
- Does the summary output help the user understand unresolved and escalated items?

## 5. What Should Be Evaluated

The prototype should be evaluated across five main dimensions:

1. technical correctness of implemented checks
2. issue classification and output quality
3. workflow completeness
4. traceability and explainability
5. practical usefulness within stated scope

## 6. Evaluation Scope

The evaluation should cover the following implemented components:

- spreadsheet import
- record normalisation
- deterministic checks
- unusual transaction review using IQR on `net_amount`
- issue generation
- status and risk mapping
- user-facing issue output
- decision logging
- review-state updates
- pre-submission review summary generation

The unusual-transaction signal is intentionally implemented with IQR rather than a more complex machine-learning anomaly detector such as Isolation Forest. This keeps the flagged result explainable within a finance review workflow: a reviewer can be told that a value falls outside the observed interquartile spread, rather than being asked to trust a harder-to-interpret model score. That trade-off is important because the prototype is evaluated as a local-first, human-in-the-loop review tool, not as a black-box anomaly ranking engine.

This choice also keeps the evaluation proportionate to the project scope. IQR can be reproduced locally with low computational overhead, no model-training stage, and limited tuning burden. More complex learned detectors may surface additional patterns, but they also introduce a higher risk of opaque flagging behaviour. In a financial review setting, that opacity weakens explainability and makes the resulting review prompt harder to justify to the user who must still make the final decision.

The evaluation should not attempt to validate:

- legal correctness in all VAT scenarios
- full real-world tax interpretation
- HMRC submission behaviour
- penalty logic
- production scalability

## 7. Evaluation Method Structure

A practical evaluation plan for this prototype should combine:

1. scenario-based technical testing
2. output inspection against expected behaviour
3. workflow demonstration and traceability review
4. limited user-oriented feedback if feasible

This is more realistic than attempting a large formal user study or broad legal validation.

## 8. Proposed Evaluation Components

## 8.1 Component A: Rule and Detection Testing

### Objective

Assess whether implemented rules correctly flag known issues in prepared datasets.

### Method

Use prepared test spreadsheets containing controlled examples such as:

- missing transaction date
- invalid date format
- missing net amount
- non-numeric VAT amount
- exact duplicate rows
- duplicate invoice references
- inconsistent totals
- blank description
- missing supplier/customer reference
- unusual `net_amount` outliers

### Measures

- whether the expected issue is detected
- whether the correct rule is triggered
- whether the resulting status and risk level are as intended

### Output

- test case table
- automated pass/fail comparison
- missing and unexpected issue mismatch report

## 8.2 Component B: Issue Output Evaluation

### Objective

Assess whether generated issues are structured, understandable, and aligned with the defined schemas.

### Method

Inspect representative issues and verify:

- required fields are present
- explanation fields are populated
- recommended manual checks are meaningful
- issue category, status, and risk mappings are appropriate

### Measures

- schema completeness
- explanation quality
- consistency of issue formatting

### Output

- issue output inspection checklist

## 8.3 Component C: Workflow Evaluation

### Objective

Assess whether the prototype supports the intended review workflow from issue detection to final summary.

### Method

Run end-to-end scenarios where a user:

1. imports a dataset
2. reviews flagged issues
3. records decisions
4. updates issue states
5. generates a review summary

### Measures

- whether all workflow stages function in sequence
- whether issue state changes are reflected correctly
- whether decision logs link correctly to issues
- whether the final summary reflects underlying issues and decisions

### Output

- workflow walkthrough results

## 8.4 Component D: Traceability Evaluation

### Objective

Assess whether the prototype provides traceable links between source records, issues, review decisions, and final summary outputs.

### Method

Select sample flagged records and verify whether it is possible to trace:

- the source row
- the triggered rule
- the generated issue
- the user decision
- the summary outcome

### Measures

- traceability completeness
- ease of following review history

### Output

- traceability inspection table

## 8.5 Component E: Limited User-Centred Evaluation

### Objective

Assess whether the prototype appears understandable and practically helpful to users.

### Method

If feasible, conduct a small-scale, informal evaluation with a limited number of users or reviewers such as:

- peers
- supervisor feedback
- self-evaluation using structured task scenarios

Possible tasks:

- identify what a flagged issue means
- explain what manual check should be done
- record a decision for a flagged record
- interpret the review summary

### Measures

- perceived clarity
- perceived usefulness
- ease of following workflow
- ease of understanding issue explanations

### Output

- small feedback summary or structured observation notes

### Note

If participant access is limited, the dissertation can still justify a structured scenario-based evaluation rather than a broad user study.

## 9. Evaluation Datasets

The evaluation should use small, controlled, and explainable datasets.

Recommended dataset types:

- clean dataset with few or no issues
- dataset with deterministic errors
- dataset with duplicate-risk patterns
- dataset with unusual amount outliers
- dataset with mixed issue types for end-to-end review

The datasets should be designed so that expected outputs are known in advance.

This makes evaluation more rigorous and easier to explain in the dissertation.

## 10. Example Evaluation Scenarios

The following scenarios are suitable for the prototype.

## 10.1 Scenario 1: Deterministic Validation Scenario

Dataset contains:

- one missing transaction date
- one invalid date
- one non-numeric VAT amount
- one duplicate row

Expected outcome:

- all four issues are detected
- issue objects are created with appropriate status and risk
- issue explanations clearly describe the problem

## 10.2 Scenario 2: Manual Review Signal Scenario

Dataset contains:

- duplicate invoice reference
- blank description
- unusually high `net_amount`

Expected outcome:

- issues are flagged as review-worthy rather than definitive tax failures
- user can inspect and log decisions

## 10.3 Scenario 3: End-to-End Review Scenario

Dataset contains a mixture of deterministic issues and review-only signals.

Expected outcome:

- issues are generated
- user decisions are logged
- issue states update correctly
- summary reflects corrected, accepted, unresolved, and escalated items

## 11. Evaluation Metrics

The prototype does not need overly complex metrics. A smaller number of clear and defensible metrics is better.

## 11.1 Technical Metrics

Recommended technical metrics:

- number of expected issues detected
- number of false negatives on prepared datasets
- rule trigger correctness by scenario
- schema completeness for issue and decision objects

Examples:

- expected issue detection rate
- issue generation success rate
- decision log linkage success rate

## 11.2 Workflow Metrics

Recommended workflow metrics:

- proportion of test scenarios completed end-to-end
- percentage of issues successfully moved from `open` to a reviewed state
- percentage of review summaries generated successfully

## 11.3 Traceability Metrics

Recommended traceability metrics:

- percentage of sampled issues traceable to source record, rule, and decision log
- proportion of reviewed issues with recorded evidence checked

## 11.4 User-Oriented Metrics

If small-scale feedback is collected, possible measures include:

- clarity of issue explanations
- usefulness of recommended manual checks
- ease of understanding review summary
- ease of using the review workflow

These may be collected qualitatively or using simple rating scales.

## 12. Success Criteria

The prototype may be considered successful if the evaluation shows that it can:

1. correctly detect the intended deterministic issues in prepared datasets
2. generate structured issue outputs with status, risk, explanation, and manual-check guidance
3. support manual decision logging for flagged issues
4. maintain traceability from issue detection to logged decision
5. produce a useful review summary highlighting unresolved and escalated items

For dissertation purposes, success should be framed as:

- demonstrating useful and structured pre-submission review support

not as:

- proving full VAT compliance automation

## 13. Evidence Collection Plan

The following artefacts should be collected during evaluation:

- test datasets
- expected-results tables
- actual issue outputs
- assertion runner outputs
- decision log outputs
- review summary outputs
- screenshots of the interface if relevant
- scenario walkthrough notes
- optional user feedback notes

These artefacts are useful both for internal validation and for dissertation evidence.

## 14. Limitations of the Evaluation

The evaluation should acknowledge realistic limitations.

Likely limitations include:

- use of controlled rather than real accounting datasets
- small-scale or informal user feedback
- no legal validation by tax professionals
- limited scope of implemented rules
- prototype-focused rather than production-focused performance testing

These limitations are acceptable if clearly stated and matched to the prototype's intended scope.

## 15. Threats to Validity

The evaluation should discuss possible threats to validity.

### 15.1 Internal validity threats

- prepared datasets may be too simple
- expected outcomes may be biased toward implemented rules

### 15.2 External validity threats

- prototype datasets may not reflect all real-world VAT record patterns
- user feedback from peers may not represent professional accounting users

### 15.3 Construct validity threats

- measuring issue detection alone may overstate usefulness if review support quality is weak
- user satisfaction alone may not prove technical correctness

### 15.4 Mitigation

Possible mitigations:

- include mixed datasets with multiple issue types
- evaluate both detection and workflow support
- use traceability and explainability criteria, not just detection counts
- describe scope limitations explicitly

## 16. Recommended Dissertation Evaluation Structure

A practical dissertation evaluation chapter can be structured as:

1. evaluation goals
2. evaluation criteria
3. datasets and scenarios
4. technical testing results
5. workflow and traceability evaluation
6. limited user or observational feedback
7. discussion of limitations

This structure fits the prototype well and avoids overstating what the system is designed to do.

## 17. Summary

The evaluation should assess the prototype as a structured pre-submission review support system rather than an automated VAT decision engine.

A strong evaluation plan should show whether the prototype:

- detects meaningful spreadsheet record issues
- presents them in an explainable way
- supports evidence-based manual review
- records review decisions transparently
- produces a useful final review summary

This evaluation approach is realistic, defensible, and aligned with the revised project scope of a local-first, human-in-the-loop VAT pre-submission review prototype.
