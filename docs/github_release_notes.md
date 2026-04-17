# GitHub Release Notes

This file contains ready-to-paste release descriptions for the project's milestone tags.

Recommended tag mapping:

- `v0.1.0` -> `5f37fc3`
- `v0.2.0` -> `a0f4c98`
- `v0.3.0` -> current dissertation demo milestone

## v0.3.0 - Packaged Evaluation Demo

This release marks the current dissertation demo milestone for the AI-Assisted VAT Spreadsheet Review Prototype.

It brings together the most presentable state of the project so far: a clearer review workflow, stronger evaluation framing, improved export behavior, and a more approachable Downloads experience for non-technical reviewers.

### Highlights

- Added controlled VAT evaluation testbed generation to support dissertation-aligned assessment.
- Added contextual anomaly detection support to expand review-signal coverage.
- Refined exporter outputs and review dashboard presentation for clearer summaries and auditability.
- Improved the Downloads tab with recommended exports, advanced exports, and a plain-language explanation panel.
- Reduced avoidable false positives by fixing optional VAT-code validation handling.

### Why this release matters

- It is the strongest current version for supervisor review, demonstration, and packaging.
- It presents the project as a coherent review assistant rather than just a collection of CSV outputs.
- It makes the evaluation story easier to defend in an academic setting.

### Included artefacts

- Local browser GUI in `gui.py`
- Shared pipeline in `main.py` and `pipeline.py`
- Review Centre and Visual Insights workflow
- Controlled evaluation support and export artefacts

## v0.2.0 - Local Review Demo

This release marks the point where the project becomes a clearly demoable local browser prototype rather than only a pipeline-oriented codebase.

### Highlights

- Added a local browser UI for interactive prototype demos.
- Added review-centre workflow and Visual Insights dashboard support.
- Added review summaries and aligned export outputs.
- Expanded prototype robustness support with public raw and adapted evaluation datasets.
- Updated documentation to reflect the prototype workflow and AI-assisted explanation path.

### Why this release matters

- It is the first release that a supervisor or assessor can meaningfully click through as a demo.
- It introduces the product-facing workflow shape that defines the later project direction.
- It shifts the project from analysis scripts toward a user-visible review system.

## v0.1.0 - Pipeline Prototype

This release captures the first runnable dissertation-aligned prototype baseline.

### Highlights

- Established the initial VAT review prototype structure.
- Added a reusable pipeline entry point for source runs.
- Added synthetic evaluation workflow and issue-chart support.
- Added early anomaly-analysis support for controlled cases.

### Why this release matters

- It marks the point where the project becomes a working technical prototype rather than only a project idea.
- It establishes the architecture later used by ingestion, validation, anomaly, review, and export modules.
- It provides the baseline from which the browser UI and review workflow later grow.
