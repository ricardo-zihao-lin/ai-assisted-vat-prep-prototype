# Realism Dataset Support

## Purpose

This document defines the supplemental realism-dataset layer used to support
evaluation without drifting away from the project's main purpose.

The main purpose of the prototype remains:

- controlled rule validation
- explainability and usefulness comparison
- human-in-the-loop review support

The realism dataset is **not** the main proof of correctness or usefulness.
It is a secondary layer that helps demonstrate that the prototype can also run
on a more realistic public transaction substrate.

## Main Design Principle

The controlled evaluation datasets in `data/evaluation/` remain the primary
evidence for:

- deterministic rule correctness
- assertion-based validation
- usefulness comparison against a raw issue list

The realism dataset exists only to add:

- public-source plausibility
- transaction-level variety
- repeatable synthetic VAT shaping

## Implemented Route

The repository now includes:

- `data/realism/uci_online_retail_like_seed.csv`
- `data/realism/monthly_direction_calibration.csv`
- `scripts/generate_realism_vat_dataset.py`

The script works in a way that mirrors the proposed route:

1. Start from a UCI-style retail transaction substrate.
2. Apply explicit VAT treatment rules.
3. Treat cancellations as negative reversal rows.
4. Shape monthly behaviour using a calibration table.
5. Output a reproducible synthetic VAT transaction dataset plus summary files.

## Why A Bundled Seed Dataset Is Included

The repository ships with a small UCI-style seed file so the realism workflow
can be run immediately and repeatedly during dissertation preparation.

This avoids making the core verification chain depend on large external data
downloads or unstable external URLs. The script still accepts a larger
transaction substrate later, including a real UCI Online Retail export,
provided the same basic columns are available.

## Current VAT Generation Logic

The implemented synthetic VAT logic is deliberately explicit and simple:

- non-UK countries in the configured list are treated as zero-rated exports
- selected description keywords map to zero-rated, reduced-rate, or exempt
  proxy treatments
- all other rows default to standard-rated goods
- cancellations are detected through `InvoiceNo` starting with `C` or negative
  quantity values
- the base transaction amount is `abs(quantity) * unit_price`
- reversals are represented with negative signed values
- VAT and gross amounts are derived from the synthetic VAT rate

This logic is transparent and reproducible. It should be described as a
synthetic VAT treatment layer, not as ground-truth legal VAT classification.

## Calibration Layer

The bundled `monthly_direction_calibration.csv` is a proxy calibration table.
It is designed to capture the **shape** of monthly direction changes rather
than any absolute tax truth.

This keeps the realism dataset aligned with the intended use:

- demonstrate reproducible directional shaping
- avoid claiming direct official VAT truth

For a dissertation extension, this proxy table can be replaced with a
calibration file derived from public aggregate indicators such as the ONS
Retail Sales Index direction by month or broad retail grouping.

Official source options:

- [UCI Online Retail dataset](https://archive.ics.uci.edu/dataset/352/online%2Bretail)
- [ONS Retail sales index dataset](https://www.ons.gov.uk/datasets/retail-sales-index)

These sources should be treated as:

- transaction substrate input
- public directional calibration reference

not as direct line-level VAT ground truth.

## Command

Run:

```powershell
venv\Scripts\python.exe scripts\generate_realism_vat_dataset.py
```

Outputs are written to:

- `output/runs/realism_dataset/synthetic_vat_realism_dataset.csv`
- `output/runs/realism_dataset/synthetic_vat_realism_summary.csv`
- `output/runs/realism_dataset/synthetic_vat_realism_metadata.json`

## Validation Use

The recommended use of the realism dataset is:

1. generate the synthetic VAT dataset
2. run the main prototype on the generated CSV
3. inspect whether the pipeline still produces coherent issue outputs and
   review summaries
4. cite this as a realism supplement, not as the primary usefulness proof

## Important Boundary

The realism dataset should not replace the controlled comparison datasets in
`data/evaluation/`.

The correct evaluation story is:

- controlled datasets prove the rules and usefulness comparison
- the realism dataset shows that the prototype can also operate on a more
  public, transaction-like, reproducible synthetic data source
