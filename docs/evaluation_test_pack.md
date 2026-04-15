# Evaluation Test Pack for Review-Oriented Prototype Assessment

## 1. Purpose

This document defines a practical evaluation test pack for assessing whether the current prototype is more useful as a pre-submission VAT review decision-support tool than a simpler raw issue-list output.

The pack is designed to support the evaluation approach described in `evaluation_plan.md`. It provides:

- controlled test datasets
- scenario-based evaluation tasks
- expected issue assertions
- a comparison template for "raw issue list" versus "review-oriented output"

The evaluation focus is usefulness for structured review, explainability, and traceability. It is not intended to prove legal compliance or final VAT correctness.

## 2. Files Included

The following evaluation assets are included in `data/evaluation/`:

- `deterministic_validation_case.csv`
- `review_support_case.csv`
- `decision_logging_case.csv`
- `expected_issue_assertions.csv`
- `review_usefulness_comparison_template.csv`

The repository also includes `scripts/build_usefulness_validation_pack.py`,
which generates side-by-side usefulness comparison outputs under
`output/usefulness_validation_pack/`.

## 3. Dataset Roles

### 3.1 `deterministic_validation_case.csv`

Purpose:

- test deterministic issue detection
- verify high-confidence validation outputs
- verify expected status and risk mapping

Main patterns included:

- missing transaction date
- invalid date format
- missing net amount
- invalid numeric net amount
- duplicate row

This dataset is most suitable for technical correctness testing.

### 3.2 `review_support_case.csv`

Purpose:

- test mixed outputs that include both deterministic issues and review-oriented signals
- demonstrate why enriched issue interpretation is more useful than a raw issue list

Main patterns included:

- blank description
- outlier `net_amount`
- invalid numeric amount
- duplicate row

This dataset is most suitable for explainability and usefulness comparison.

### 3.3 `decision_logging_case.csv`

Purpose:

- test the human-in-the-loop workflow
- verify decision logging
- verify correction, acceptance, exclusion, and escalation paths

Main patterns included:

- blank description
- invalid date format
- unusual high amount
- invalid numeric amount
- duplicate row

This dataset is most suitable for end-to-end workflow evaluation.

## 4. Expected Issue Assertions

The file `expected_issue_assertions.csv` provides expected outputs for key rows.

Recommended use:

1. run the prototype on each dataset
2. compare generated issues against the assertion file
3. confirm whether the expected `rule_id`, `issue_type`, `status`, and `risk_level` were produced
4. record pass/fail for each assertion

The current runner writes `output/evaluation_assertion_results.csv` and `output/evaluation_assertion_summary.csv` so the comparison is machine-readable.

For dissertation presentation, the repository also builds:

- `output/evaluation_assertion_results_table.csv`
- `output/evaluation_results_overview.csv`
- `output/evaluation_evidence_chart.png`
- `docs/evaluation_results.md`

This gives a structured way to evaluate technical correctness without needing a large benchmark dataset.

## 5. Scenario-Based Evaluation Tasks

The following scenario tasks can be used in testing sessions, walkthroughs, or a small user-oriented evaluation.

## 5.1 Scenario A: Deterministic Issue Detection

Dataset:

- `deterministic_validation_case.csv`

Task:

1. import the dataset
2. run the analysis
3. inspect whether the expected deterministic issues were detected
4. compare results against `expected_issue_assertions.csv`

Evaluation questions:

- Were the expected issues detected?
- Were the assigned `status` and `risk_level` appropriate?
- Did the issue objects include usable explanation fields?

## 5.2 Scenario B: Explainability Comparison

Dataset:

- `review_support_case.csv`

Task:

1. run the dataset and open the generated issues
2. run `scripts/build_usefulness_validation_pack.py`
3. compare the generated `raw_issue_list_baseline.csv` with `review_oriented_output.csv`
4. use `usefulness_side_by_side.csv` and `review_usefulness_comparison_template.csv` to document the comparison

Evaluation questions:

- Does the enriched output help the reviewer understand why the issue matters?
- Does it help the reviewer know what to check next?
- Is the anomaly clearly framed as a review signal rather than a confirmed error?

## 5.3 Scenario C: Review Workflow and Decision Logging

Dataset:

- `decision_logging_case.csv`

Task:

1. run the dataset
2. choose at least four issues
3. record different decisions such as:
   - `corrected`
   - `accepted_with_note`
   - `excluded_from_review_set`
   - `escalated`
4. inspect `review_log.csv` and `review_history.csv`
5. confirm that `issue_id`, `decision`, `evidence_checked`, `timestamp`, `final_record_status`, and `needs_escalation` are recorded

Evaluation questions:

- Does the system support structured review decisions?
- Are review actions traceable from issue to log entry?
- Does the workflow clearly distinguish unresolved versus escalated items?

## 6. How to Compare Against a Raw Issue List

To support the dissertation argument that the enhanced prototype is more useful than a basic issue list, compare the outputs at two levels.

### 6.1 Raw issue list baseline

Treat the baseline as a minimal output containing only:

- row index
- issue type
- short error label

Example:

```text
row 1 | missing_transaction_date | date
row 5 | unusual_net_amount | net_amount
```

### 6.2 Review-oriented output

Treat the improved prototype output as the full issue object or issue detail view containing:

- `issue_id`
- `status`
- `risk_level`
- `why_it_matters`
- `possible_vat_review_impact`
- `recommended_manual_check`
- decision logging support

### 6.3 Comparison criteria

Use the following questions:

- Does the improved output help the user understand the significance of the issue?
- Does it suggest a concrete next step?
- Does it preserve a traceable review trail?
- Does it help distinguish deterministic failure from review-only signal?

Use `review_usefulness_comparison_template.csv` to document these comparisons.

## 7. Recommended Evaluation Outputs to Save

For each scenario, save:

- `dataset_snapshot.csv`
- `issue_report.csv`
- `review_log.csv`
- `review_history.csv`
- `evaluation_assertion_results.csv`
- `evaluation_assertion_summary.csv`
- `raw_issue_list_baseline.csv`
- `review_oriented_output.csv`
- `usefulness_side_by_side.csv`
- screenshots of the issue detail panel if needed
- a completed pass/fail table based on `expected_issue_assertions.csv`
- a completed usefulness comparison table based on `review_usefulness_comparison_template.csv`

These outputs can be cited directly in the dissertation.

## 8. Suggested Dissertation Use

You can use this evaluation pack in the dissertation as follows:

### Technical evaluation section

Use:

- `deterministic_validation_case.csv`
- `expected_issue_assertions.csv`

### Explainability/usefulness section

Use:

- `review_support_case.csv`
- `review_usefulness_comparison_template.csv`

### Workflow and traceability section

Use:

- `decision_logging_case.csv`
- saved `review_log.csv` / `review_history.csv` outputs

## 9. Summary

This evaluation test pack is intended to make prototype evaluation easier, more structured, and more defensible.

It supports three things:

- objective checking of expected detections
- comparison between basic issue listing and review-oriented outputs
- end-to-end testing of the human-in-the-loop review workflow

This makes it suitable for demonstrating that the prototype is more useful as a pre-submission VAT review support system than as a simple raw issue-list generator.
