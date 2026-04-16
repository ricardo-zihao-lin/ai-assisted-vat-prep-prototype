# Dataset Audit Recommendations

## Purpose

This note classifies the current repository datasets by evaluation value so the
project can make defensible claims in the dissertation, README, and viva.

The goal is not to keep every file. The goal is to keep the files that support
clear claims and to demote or remove files that weaken the evaluation story.

## Recommendation Summary

| Path | Recommendation | Main use | Reason |
| --- | --- | --- | --- |
| `data/evaluation/deterministic_validation_case.csv` | Keep | Controlled rule correctness | Small, explicit, and suitable for assertion-based checks |
| `data/evaluation/review_support_case.csv` | Keep | Explanation and review-support evaluation | Supports human-review usefulness claims |
| `data/evaluation/decision_logging_case.csv` | Keep | Workflow and decision logging | Directly aligned with the prototype purpose |
| `data/evaluation/expected_issue_assertions.csv` | Keep | Ground-truth expectations | Strongest file for deterministic evaluation evidence |
| `data/evaluation/review_usefulness_comparison_template.csv` | Keep | Before/after comparison framing | Useful for dissertation tables and README examples |
| `data/demo/sample_data.csv` | Keep but demote | Demo only | Too small to support realism or robustness claims |
| `data/demo/synthetic_eval_case_a.csv` | Keep but demote | Extra smoke test | Small and synthetic; not strong evidence |
| `data/demo/synthetic_eval_case_b.csv` | Keep but demote | Extra smoke test | Small and synthetic; not strong evidence |
| `data/realism/uci_online_retail_like_seed.csv` | Keep but demote | Input substrate for synthetic realism generation | Useful as provenance for synthetic generation, not as evaluation evidence alone |
| `data/realism/monthly_direction_calibration.csv` | Keep but demote | Generation support | Proxy calibration only; supports reproducibility, not realism proof |
| `data/supplemental/realism/synthetic_vat_realism_dataset.csv` | Keep but demote | Supplemental synthetic realism demo | Better than toy data, but still too small and synthetic for main realism evidence |
| `data/supplemental/realism/synthetic_vat_realism_summary.csv` | Keep but demote | Metadata/supporting summary | Useful supporting file, not a core evaluation dataset |
| `data/supplemental/realism/synthetic_vat_realism_metadata.json` | Keep but demote | Provenance metadata | Useful for reproducibility only |
| `data/public_raw/dft_mar_2025.csv` | Keep | Public-source robustness input | Large open dataset with transaction-style rows and structural variation |
| `data/public_raw/hmrc_jan_2026.csv` | Keep | Public-source robustness input | Medium-sized open dataset with transaction-style rows |
| `data/public_raw/dwp_epcs_july_2025.csv` | Keep but demote | Minor public-source edge case | Small and structurally mixed; weak as a main evaluation input |
| `data/public_adapted/dft_mar_2025_adapted.csv` | Keep | Canonical-format robustness test | 3,131 rows in prototype schema; useful for pipeline robustness |
| `data/public_adapted/hmrc_jan_2026_adapted.csv` | Keep | Canonical-format robustness test | 1,022 rows in prototype schema; useful for pipeline robustness |
| `data/public_adapted/dwp_epcs_july_2025_adapted.csv` | Delete candidate | Very weak adapted input | Only 5 rows and almost no variation |
| `data/public_adapted/dft_mar_2025_issue_report.csv` | Keep | Derived evaluation artefact | Useful as evidence of prototype outputs on a larger open dataset |
| `data/public_adapted/hmrc_jan_2026_issue_report.csv` | Keep | Derived evaluation artefact | Useful as evidence of prototype outputs on a medium open dataset |
| `data/public_adapted/dft_mar_2025_review_summary.csv` | Keep | Derived evaluation artefact | Good summary evidence for documentation |
| `data/public_adapted/hmrc_jan_2026_review_summary.csv` | Keep | Derived evaluation artefact | Good summary evidence for documentation |
| `data/public_adapted/dft_mar_2025.csv` | Delete candidate | Redundant copy of raw input | Duplicates `data/public_raw/dft_mar_2025.csv` |
| `data/public_adapted/hmrc_jan_2026.csv` | Delete candidate | Redundant copy of raw input | Duplicates `data/public_raw/hmrc_jan_2026.csv` |
| `data/public_adapted/dwp_epcs_july_2025.csv` | Delete candidate | Redundant copy of raw input | Duplicates `data/public_raw/dwp_epcs_july_2025.csv` |
| `data/public_adapted/test_inputs/*` | Removed | Former convenience duplicates | The folder was removed to keep one authoritative copy of each runnable dataset |

## Key Findings

### 1. The strongest current evidence is controlled evaluation, not realism

The files under `data/evaluation/` are small, but they are aligned with the
prototype's real claims:

- deterministic validation
- explanation-oriented review
- human decision logging

These files should remain the main evidence for rule correctness and review
workflow behaviour.

### 2. The public datasets help with robustness, not VAT truth

The most useful larger datasets currently available are:

- `data/public_raw/dft_mar_2025.csv` with 3,131 rows
- `data/public_raw/hmrc_jan_2026.csv` with 1,022 rows
- adapted versions of both in the prototype schema

These are useful because they show the system can process larger, less toy-like
CSV inputs. However, they do **not** contain true VAT bookkeeping fields such
as invoice tax treatment, recoverability, VAT registration evidence, or ledger
posting context.

They support:

- spreadsheet robustness
- schema adaptation
- issue report generation on larger files

They do not support:

- VAT correctness
- legal tax classification accuracy
- claims about real SME bookkeeping ground truth

### 3. The adapted public datasets are structurally useful but semantically weak

The adapted files are reduced to:

- `date`
- `description`
- `net_amount`
- `vat_amount`
- `category`

This is good for showing the prototype can ingest a canonical schema. It is not
good for proving VAT realism because:

- `vat_amount` is entirely `0.0` in the larger adapted files inspected
- invoice references, supplier/customer identifiers, and document linkage are
  removed
- the source data is public spending transparency data, not SME bookkeeping

The adaptation layer should therefore be described as a robustness input, not a
VAT-realism input.

### 4. The DWP adapted file is too weak to matter

`data/public_adapted/dwp_epcs_july_2025_adapted.csv` contains only 5 rows after
adaptation and only one visible description/category pattern in sample checks.

This file is too small to strengthen the evaluation story. It can be removed
without harming the core argument.

### 5. The current synthetic realism dataset is a useful supplement, not main evidence

`data/supplemental/realism/synthetic_vat_realism_dataset.csv` is a
reproducible synthetic VAT-like dataset derived from a UCI-style retail seed.

It improves the project story because it includes:

- invoice references
- gross amounts
- VAT rates
- VAT treatment labels

However, it is still only 28 rows and is explicitly synthetic. It should be
retained as a supplemental realism artefact, not as the main proof of
real-world usefulness.

### 6. There is substantial duplicate clutter

There are multiple exact or near-exact convenience copies:

- raw public files copied again into `data/public_adapted/`
- convenience copies that were previously duplicated under `data/public_adapted/test_inputs/`
- small demo files duplicated across locations

These copies make the repository look less disciplined and blur provenance.
Cleaning them would strengthen the credibility of the project.

## Best Current Dataset Story

If the repository were described today, the cleanest defensible evaluation
story would be:

1. `data/evaluation/` proves rule behaviour and review workflow logic.
2. `data/public_adapted/dft_mar_2025_adapted.csv` and
   `data/public_adapted/hmrc_jan_2026_adapted.csv` show that the prototype can
   run on larger open transaction-style inputs after schema adaptation.
3. `data/supplemental/realism/synthetic_vat_realism_dataset.csv` is a
   small synthetic realism supplement.
4. The repository does not yet contain a strong medium-scale SME bookkeeping
   dataset or a real anonymised SME export.

## Next Upgrade Priorities

To make the evaluation stand up better in a dissertation or defence, the next
dataset improvements should be:

1. Add one medium-scale synthetic SME bookkeeping export with at least
   1,000 to 3,000 rows and realistic bookkeeping columns.
2. Retain one small anonymised real export if that can be sourced safely.
3. Keep only one authoritative copy of each dataset and one clearly labelled
   convenience/demo folder if still needed.
4. Add a small provenance manifest for public-source files with source URL and
   retrieval date.
