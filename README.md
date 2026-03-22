# AI-Assisted Spreadsheet Records Preparation Tool for UK MTD VAT Reporting

## Overview

This project is a research prototype for a UK undergraduate Final Year Project. It supports spreadsheet-based VAT record preparation by:

- loading CSV or Excel spreadsheet data
- checking the data for basic structural and formatting issues
- flagging unusual transaction values using a simple statistical method
- recording review outcomes for flagged items
- exporting traceable reporting artefacts for inspection

The prototype is designed around transparency, traceability, and human-in-the-loop review.

## What The Prototype Does

- reads spreadsheet-style transaction data from a local CSV or Excel file
- validates a small minimum input schema
- reports missing values, duplicate rows, invalid dates, and invalid numeric values
- flags unusual `net_amount` values using a simple IQR-based anomaly check
- records review outcomes as `confirm`, `reject`, or `ignore`
- exports a dataset snapshot, an issue report, and a review log

## What The Prototype Does Not Do

- it does not submit anything to HMRC
- it does not claim to be a production VAT system
- it does not automatically correct source financial records
- it does not silently clean or rewrite the spreadsheet
- it does not replace human judgement

## Minimum Expected Input Columns

Required columns:

- `date`
- `description`
- `net_amount`
- `vat_amount`

Optional column:

- `category`

The loader normalises column headings to lower case with underscores. For example, `Net Amount` becomes `net_amount`.

## Local Demo Setup

This repository is set up for a simple Windows local demo.

### Option 1: Use the batch file

Run:

```bat
run_demo.bat
```

### Option 2: Run directly with the local virtual environment

Run:

```bat
venv\Scripts\python.exe main.py
```

### Option 3: Run the local browser UI

Run:

```bat
venv\Scripts\python.exe gui.py
```

Then open the local address shown in the terminal, usually:

```text
http://127.0.0.1:7860
```

### Local UI scope note

The browser-based UI is a local demonstration wrapper around the existing prototype pipeline.
It does not change the system boundary: spreadsheet ingestion, deterministic validation,
IQR-based anomaly flagging, review handling, and export generation all remain local operations.

When the UI is used, each run writes outputs to a per-run folder under:

```text
output/ui_runs/
```

Each UI run still produces the same three core artefacts:

- `dataset_snapshot.csv`
- `issue_report.csv`
- `review_log.csv`

### Install dependencies

If you need to create or refresh the environment, install the dependencies with:

```bat
venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Current Demo Input

The current demo pipeline reads:

```text
data/sample_data.csv
```

The orchestration is currently defined in:

```text
pipeline.py
```

The thin command-line demo entry point is:

```text
main.py
```

The local browser-based interface entry point is:

```text
gui.py
```

## Output Files

The Export Module writes persistent artefacts to:

```text
output/
```

Current output files:

- `dataset_snapshot.csv`
- `issue_report.csv`
- `review_log.csv`

### Output Meaning

- `dataset_snapshot.csv`: a snapshot of the input dataset loaded for the prototype run; it should not be interpreted as a corrected or final spreadsheet
- `issue_report.csv`: validation findings plus anomaly flags collected to support later human review
- `review_log.csv`: review decisions showing whether each flagged item was confirmed, rejected, or ignored

## Reject Path In The Workflow

If review produces any `reject` decision:

- the Export Module still writes the reporting artefacts
- the pipeline stops after reporting
- the user is expected to correct the source spreadsheet outside the system
- the user then reruns the pipeline on the corrected spreadsheet

This keeps the prototype aligned with a human-in-the-loop workflow. Reported problems are surfaced clearly rather than being automatically fixed.

## Project Structure

- `ingestion/loader.py` - data loading
- `validation/validator.py` - baseline validation
- `anomaly/anomaly_detector.py` - anomaly flagging
- `review/review_manager.py` - review outcome recording
- `export/exporter.py` - output artefact export
- `pipeline.py` - reusable pipeline orchestration
- `main.py` - thin command-line demo entry point
- `gui.py` - local Gradio interface wrapper

## Notes For Dissertation Alignment

This repository should be described as a modest research prototype for spreadsheet record preparation. The current implementation is suitable for demonstrating:

- modular pipeline design
- transparent issue reporting
- basic anomaly screening
- explicit review outcomes
- traceable export artefacts

It should not be described as an automated correction tool, a production bookkeeping platform, or a direct HMRC submission system.
