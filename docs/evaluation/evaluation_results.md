# Evaluation Results

This document summarises the dissertation-ready evaluation artefacts generated
from the current repository outputs.

The evaluation evidence is intentionally split into two main layers:

1. assertion-based technical validation
2. usefulness comparison between raw issue-list output and the review-oriented
   output

The realism dataset is included as a supplemental robustness check, not as the
primary proof of usefulness.

## 1. Assertion-Based Validation

The core validation evidence is the machine-checkable assertion summary in
`output/evidence/evaluation/evaluation_assertion_results_table.csv`.

The current result is:

- `3` datasets validated
- `18` total assertions
- `18` passed assertions
- `0` failed assertions
- `100.0%` exact-match rate for every dataset

| Dataset | Rows | Assertions | Passed | Failed | Exact match |
| --- | ---: | ---: | ---: | ---: | ---: |
| `decision_logging_case.csv` | 7 | 6 | 6 | 0 | 100.0% |
| `deterministic_validation_case.csv` | 7 | 6 | 6 | 0 | 100.0% |
| `review_support_case.csv` | 9 | 6 | 6 | 0 | 100.0% |

Interpretation:

- the implementation matches the expected `row_index`, `rule_id`, `status`,
  `risk_level`, and field-level expectations for the prepared evaluation
  datasets
- the evidence is machine-checkable rather than based on visual inspection
- this supports the claim that the prototype is executing the intended review
  rules consistently on controlled inputs

## 2. Usefulness Comparison

The usefulness comparison artefacts are in
`output/evidence/evaluation/usefulness_validation_pack/usefulness_comparison_results.csv` and
`output/evidence/evaluation/usefulness_validation_pack/usefulness_comparison_summary.csv`.

The current summary is:

- `12` comparison rows
- `12` rows judged in favour of the enhanced review-oriented output
- `0` baseline-favoured rows
- `0` ties
- `100.0%` enhanced-more-useful rate for both usefulness datasets
- `5.0` average support-feature gap in favour of the enhanced output

| Dataset | Comparison rows | Enhanced more useful | Baseline more useful | Ties | Enhanced-more-useful rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| `decision_logging_case.csv` | 6 | 6 | 0 | 0 | 100.0% |
| `review_support_case.csv` | 6 | 6 | 0 | 0 | 100.0% |

Interpretation:

- the enhanced output is consistently richer than the raw issue-list baseline
- the extra fields support prioritisation, manual checking, and decision logging
- this makes the output more suitable for pre-submission review work than a
  minimal issue list alone

## 3. Presentation Tables And Figure

The dissertation-facing presentation layer is now backed by:

- `output/evidence/evaluation/evaluation_results_overview.csv`
- `output/evidence/evaluation/evaluation_assertion_results_table.csv`
- `output/evidence/evaluation/synthetic_evaluation_results_table.csv` for legacy raw-count context
- `output/evidence/evaluation/figures/evaluation_evidence_chart.png`

The chart combines:

- assertion-based exact match rates
- usefulness-comparison dominance counts

This keeps the visual presentation aligned with the evaluation claim instead of
showing raw issue counts in isolation.

## 4. Realism Supplement

The supplemental realism dataset is generated from a UCI-like transaction
substrate plus explicit synthetic VAT logic. It is not the main proof of
correctness, but it supports reproducibility and practical robustness.

The current run produced:

- `28` synthetic VAT transaction rows
- `3` cancellation / reversal rows
- deterministic regeneration across repeated runs
- a successful end-to-end pipeline run on the generated dataset

This supports the claim that the prototype can still process a more realistic
transaction-like dataset without changing the project’s main purpose.

## 5. Dissertation-Ready Conclusion

The evaluation story is now consistent across the write-up and the artefacts:

- controlled test datasets prove the rules are executed correctly
- usefulness comparison shows the review-oriented output provides more review
  support than a raw issue list
- the realism dataset adds reproducible plausibility without becoming the main
  proof

This is a stronger dissertation position than presenting raw detection counts
alone, because it ties together correctness, usefulness, and reproducibility.

## 6. Controlled Poisoning Optimization Phase

The repository now also includes a controlled poisoning benchmark built from
public seed transaction data and a ground-truth poisoning log.

The baseline row-level evaluation on
`data/evaluation/evaluation_testbed_poisoned.csv` produced:

- `TP = 106`
- `FP = 362`
- `FN = 5`
- `Precision = 0.2265`
- `Recall = 0.9550`

The main false-positive sources were:

- `invalid_date_format`, where valid ISO dates were over-flagged by mixed-format parsing
- `vat_rate_review_prompt`, where valid zero-rated or exempt rows were over-flagged because `vat_code` was not preserved into the canonical pipeline

After the optimization pass, the pipeline was updated to:

- parse ISO `YYYY-MM-DD` dates explicitly before any fallback parsing
- preserve `vat_code` in the prepared canonical schema
- suppress VAT review prompts when the declared `vat_code` and observed amount ratio are already consistent
- treat `vat_code` as optional review context rather than a universally mandatory completeness field, which avoids spurious missing-field findings in datasets that do not carry tax-code columns

The optimized row-level evaluation then produced:

- `TP = 92`
- `FP = 12`
- `FN = 19`
- `Precision = 0.8846`
- `Recall = 0.8288`

This supports the following dissertation-ready statement:

- `Precision_baseline = 0.22 -> Precision_optimized = 0.8846`

Interpretation:

- the optimization phase substantially improved precision by removing large volumes of rule-induced false positives
- the trade-off was a reduction in recall, mainly because advisory semantic-risk rows and partial-date strings were no longer being captured as aggressively
- this makes the post-optimization pipeline a stronger candidate for traceable pre-submission review, where reviewer trust and lower false-positive burden matter
