# Technology and Attribution

This document records the main third-party technologies and external technical
dependencies used by the prototype.

It is not a license manifest. Instead, it explains what each component is used
for so that repository readers and dissertation reviewers can understand the
technical stack clearly.

## Core Interface And Runtime

- [Gradio](https://www.gradio.app/)
  - used for the browser-based local UI shell in `gui.py`
  - powers the main interaction route for upload, review, dashboard, and export
- [Python](https://www.python.org/)
  - main implementation language for the shared prototype core

## Data Handling And Analysis

- [pandas](https://pandas.pydata.org/)
  - tabular loading, transformation, validation input handling, and CSV export
- [openpyxl](https://openpyxl.readthedocs.io/)
  - Excel file support for spreadsheet ingestion
- [Matplotlib](https://matplotlib.org/)
  - dissertation-friendly charts and figure generation

## Packaging And Delivery

- [PyInstaller](https://pyinstaller.org/)
  - Windows packaged demo build route
- [Docker](https://www.docker.com/)
  - environment-consistent container demo route

## Optional AI-Related Components

The prototype includes optional provider wrappers under `ai/` for external AI
suggestion support.

These wrappers are intended for:

- compact findings snapshot interpretation
- optional review-support suggestions

They are not the core rule engine and are not required for:

- deterministic validation
- anomaly detection
- assertion-based evaluation
- review logging

## UI Attribution Language

The browser interface can be accurately described as:

- built with Gradio
- backed by the shared Python review pipeline
- using pandas for tabular handling
- using Matplotlib for figure output

## Important Boundary

The technical stack should not be described in a misleading way.

For example:

- Gradio is the UI shell, not the source of business logic
- pandas is the tabular processing library, not the review methodology
- Matplotlib is a charting library, not the evidence itself
- optional AI providers assist interpretation only and do not define findings

## What Is Still Not Explicitly Recorded

The repository currently does **not** include:

- a separate third-party license inventory file
- pinned documentation URLs for every indirect dependency
- a formal NOTICE file

For a dissertation repository this is usually acceptable, but if you want a
stronger public-release posture later, the next upgrade would be a short
`THIRD_PARTY.md` or `NOTICE`-style file that records:

- package name
- repository or homepage
- purpose in this project
- license family
