# Data Sources

This document explains the provenance and status of the datasets included in
this repository.

The repository contains six different kinds of data:

1. public-source raw datasets
2. adapted datasets prepared for the prototype schema
3. controlled evaluation datasets created for testing
4. demo datasets for walkthroughs and packaged delivery
5. supplemental realism data and generated synthetic VAT outputs
6. supplemental low-value edge cases retained for completeness

The key point is that these data categories do **not** carry the same meaning.
Some are public-source records, some are controlled test assets, some are demo
inputs, and some are supplemental synthetic materials retained for provenance
or walkthrough support.

## 1. Public Raw Datasets

Files under `data/public_raw/` are public-source CSV files used as openly
available transaction-style inputs for the prototype.

Current files:

- `data/public_raw/dft_mar_2025.csv`
- `data/public_raw/dwp_epcs_july_2025.csv`
- `data/public_raw/hmrc_jan_2026.csv`

These are intended to represent public transparency or procurement-style
spending data, not VAT return data and not tax ground truth.

### Source references

- `dft_mar_2025.csv`
  - Department for Transport spending-over-GBP 25,000 publication for March 2025
  - GOV.UK publication page:
    [DfT: spending over GBP 25,000, March 2025](https://www.gov.uk/government/publications/dft-spending-over-25000-march-2025)
- `dwp_epcs_july_2025.csv`
  - DWP Government Procurement Card payments over GBP 500, July 2025 return
  - data.gov.uk preview page:
    [DWP Government Procurement Card Payments return for July 2025](https://www.data.gov.uk/dataset/c94529c9-2a1a-469d-a88a-1d52de05484f/dwp_government_procurement_card_payments_over_500/datafile/24b2aead-8f3f-49f1-afd4-55c3fc647256/preview)
- `hmrc_jan_2026.csv`
  - HMRC spend over GBP 25,000 dataset, January 2026 return
  - data.gov.uk dataset page:
    [Spend over GBP 25,000 in HM Revenue & Customs](https://www.data.gov.uk/dataset/008d307b-5434-4218-9b62-2eabdef48778/financial-transactions-data-hmrc)

### Important note

These public raw datasets are used here as:

- open transaction-style input material
- data adaptation examples
- demonstration and robustness inputs

They are **not** used as line-level VAT truth and should not be described as
official VAT ground truth.

## 2. Adapted Public Datasets

Files under `data/public_adapted/` are simplified, schema-aligned derivatives
of the raw public datasets above.

They are produced by:

- `scripts/prepare_public_datasets.py`

The current adaptation process keeps only a small canonical subset:

- `date`
- `description`
- `net_amount`
- `vat_amount`
- `category`

Current adapted files:

- `data/public_adapted/dft_mar_2025_adapted.csv`
- `data/public_adapted/dwp_epcs_july_2025_adapted.csv`
- `data/public_adapted/hmrc_jan_2026_adapted.csv`

Current issue and summary outputs in the same folder:

- `*_issue_report.csv`
- `*_review_summary.csv`

These output files are derived prototype artefacts generated from the adapted
inputs. They are not raw-source files.

### Important note

The adapted files should be described as:

- public-source inputs transformed into the prototype's canonical schema

They should **not** be described as unchanged official source files.

## 3. Controlled Evaluation Datasets

Files under `data/evaluation/` are controlled evaluation datasets created for
the prototype's verification and usefulness-comparison workflow.

Current files include:

- `deterministic_validation_case.csv`
- `review_support_case.csv`
- `decision_logging_case.csv`
- `expected_issue_assertions.csv`
- `review_usefulness_comparison_template.csv`

These files are repository-authored evaluation assets, not public-source
records.

They are used to support:

- deterministic rule verification
- assertion-based evaluation
- usefulness comparison against a raw issue list
- review workflow and decision logging checks

### Important note

These datasets should be described as:

- controlled synthetic or prepared evaluation cases

They are **not** real tax cases and **not** official compliance examples.

## 4. Realism Dataset Inputs And Synthetic Outputs

The realism dataset layer is documented in more detail in:

- [docs/evaluation/realism_dataset_support.md](evaluation/realism_dataset_support.md)

The repository includes:

- `data/realism/uci_online_retail_like_seed.csv`
- `data/realism/monthly_direction_calibration.csv`
- `scripts/generate_realism_vat_dataset.py`

This route is intended to create a reproducible synthetic VAT-like transaction
dataset for supplemental robustness checks.

### Source references

- UCI transaction substrate reference:
  [UCI Online Retail dataset](https://archive.ics.uci.edu/dataset/352/online%2Bretail)
- Public aggregate calibration reference:
  [ONS Retail sales index dataset](https://www.ons.gov.uk/datasets/retail-sales-index)

### Current implementation boundary

The repository currently ships with:

- a small UCI-style seed file
- a proxy monthly direction calibration file
- an explicit synthetic VAT generation script

This means the generated realism dataset should be described as:

- synthetic VAT-like data derived from a UCI-style transaction substrate and a
  proxy calibration layer

It should **not** be described as:

- a real HMRC VAT dataset
- official VAT truth
- legally authoritative transaction classification

Generated realism outputs retained in the repository for demonstration are now
kept under:

- `data/supplemental/realism/`

These are supplemental artefacts, not core evaluation evidence.

## 5. Demo Datasets

Files under `data/demo/` are intentionally small runnable datasets used for:

- quick walkthroughs
- packaged demo input
- smoke-test style manual checks

Current files:

- `data/demo/sample_data.csv`
- `data/demo/synthetic_eval_case_a.csv`
- `data/demo/synthetic_eval_case_b.csv`

These files should be described as demo or smoke-test inputs, not as the main
evaluation evidence for realism or real-world usefulness.

## 6. Supplemental Low-Value Edge Cases

Some files remain in primary folders even though they are weak evidence. For
example:

- `data/public_adapted/dwp_epcs_july_2025_adapted.csv`

This file is kept as a small adapted public-source edge case, but it should be
treated as supplemental only.

## 7. Recommended Citation Language

For dissertation or repository wording, the safest phrasing is:

- `data/public_raw/` contains public-source spending or procurement-style CSV
  datasets used as open transaction-style inputs.
- `data/public_adapted/` contains prototype-adapted versions of selected public
  raw datasets.
- `data/evaluation/` contains controlled repository-authored evaluation cases.
- `data/demo/` contains small walkthrough and smoke-test datasets.
- `data/realism/` plus `data/supplemental/realism/` support a supplemental
  synthetic realism check, not tax ground truth.

## 8. Additional Provenance Notes

The repository currently does **not** store:

- a download timestamp for each public raw file
- the exact original filename used at download time
- a per-file checksum manifest for source provenance

That is acceptable for a prototype repository, but if you want stronger
dissertation-grade provenance later, the next upgrade would be a small manifest
file recording:

- source URL
- access/download date
- original file name
- local repository path
- optional checksum
