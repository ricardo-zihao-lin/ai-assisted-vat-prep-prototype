# Defense Directory Guide

This page is a one-page navigation guide for dissertation review and viva
demonstration. It is intentionally selective: the goal is not to list every
file, but to show a reviewer where to look first.

## 1-Minute Overview

If a reviewer only opens a few files, the best sequence is:

1. [README.md](../README.md)
2. [architecture.md](../architecture.md)
3. [docs/domain/project_direction.md](domain/project_direction.md)
4. [docs/evaluation/evaluation_results.md](evaluation/evaluation_results.md)
5. [docs/evaluation/evaluation_test_pack.md](evaluation/evaluation_test_pack.md)

That sequence answers the five most important questions:

- what the project is
- what it is not
- how the system is structured
- what evidence exists
- how that evidence was produced

## Best File Entry Points

### Project entry

- [README.md](../README.md)
  - best starting point for repository purpose, quick start, and structure
- [docs/README.md](README.md)
  - best starting point for the documentation tree

### Architecture and scope

- [architecture.md](../architecture.md)
  - best file for dissertation architecture discussion
- [docs/domain/project_direction.md](domain/project_direction.md)
  - best file for system boundary and intended use
- [docs/architecture/gui_architecture.md](architecture/gui_architecture.md)
  - best file for explaining why `gui.py` remains a shell

### Evaluation and evidence

- [docs/evaluation/evaluation_plan.md](evaluation/evaluation_plan.md)
  - explains what the evaluation is trying to prove
- [docs/evaluation/evaluation_test_pack.md](evaluation/evaluation_test_pack.md)
  - explains the prepared datasets and scenario roles
- [docs/evaluation/evaluation_results.md](evaluation/evaluation_results.md)
  - explains what was actually achieved
- [docs/evaluation/usefulness_validation_support.md](evaluation/usefulness_validation_support.md)
  - explains the raw issue list vs enhanced output comparison support
- [docs/evaluation/realism_dataset_support.md](evaluation/realism_dataset_support.md)
  - explains the supplementary realism dataset layer

### Domain logic

- [docs/domain/VAT_review_rules.md](domain/VAT_review_rules.md)
  - best file for the rule catalogue and interpretation intent
- [docs/domain/VAT_review_workflow.md](domain/VAT_review_workflow.md)
  - best file for the review process and user role

## Best Code Entry Points

If the reviewer wants to inspect the code rather than only the docs, the best
order is:

1. [main.py](../main.py)
2. [pipeline.py](../pipeline.py)
3. [validation/validator.py](../validation/validator.py)
4. [anomaly/anomaly_detector.py](../anomaly/anomaly_detector.py)
5. [review/issue_interpreter.py](../review/issue_interpreter.py)
6. [review/review_manager.py](../review/review_manager.py)
7. [export/exporter.py](../export/exporter.py)
8. [gui.py](../gui.py)
9. [ui/rendering.py](../ui/rendering.py)

What each one shows:

- `main.py`
  - the thin source-run entry used for reproduction
- `pipeline.py`
  - the shared orchestration flow
- `validation/validator.py`
  - deterministic checking
- `anomaly/anomaly_detector.py`
  - statistical screening
- `review/issue_interpreter.py`
  - structured interpretation of findings
- `review/review_manager.py`
  - review queue and decision persistence
- `export/exporter.py`
  - output artefacts and diagnostics
- `gui.py`
  - the thin browser shell
- `ui/rendering.py`
  - extracted GUI rendering helpers

## Best Evidence Outputs

The strongest output artefacts for a dissertation reviewer are under:

- `output/evidence/evaluation/`

The most important files there are:

- `evaluation_assertion_results.csv`
- `evaluation_assertion_summary.csv`
- `evaluation_assertion_results_table.csv`
- `evaluation_results_overview.csv`
- `figures/evaluation_evidence_chart.png`
- `usefulness_validation_pack/usefulness_comparison_summary.csv`

These are the outputs most worth citing in a report or slide deck because they
support:

- rule-implementation correctness
- pass/fail style evaluation
- usefulness comparison evidence
- figure-ready summary views

## Best Reproduction Commands

If a reviewer wants to reproduce the main evidence quickly:

### Run the test suite

```bat
venv\Scripts\python.exe -m pytest
```

### Run the assertion-based evaluation

```bat
venv\Scripts\python.exe scripts\run_synthetic_evaluation.py
```

### Build usefulness comparison outputs

```bat
venv\Scripts\python.exe scripts\build_usefulness_validation_pack.py
```

### Rebuild the evaluation tables and chart

```bat
venv\Scripts\python.exe scripts\build_evaluation_results_table.py
venv\Scripts\python.exe scripts\build_evaluation_issue_chart.py
```

### Run the shared pipeline on the sample input

```bat
venv\Scripts\python.exe main.py --input data\sample_data.csv --output-dir output\runs\source\sample_check
```

## What A Reviewer Can Ignore First

These are useful, but not the best first stop during a viva:

- `docs/archive/`
- `archive/`
- `data/public_raw/`
- `data/public_adapted/`
- `tools/`
- `packaging/`
- `build/`
- `dist/`

They support delivery, earlier planning, or local housekeeping, but they are
not the core dissertation argument.

## Recommended Viva Walkthrough

If you want a reviewer-friendly walkthrough order, use this:

1. [README.md](../README.md)
2. [docs/domain/project_direction.md](domain/project_direction.md)
3. [architecture.md](../architecture.md)
4. [docs/evaluation/evaluation_results.md](evaluation/evaluation_results.md)
5. `output/evidence/evaluation/`
6. [main.py](../main.py)
7. [pipeline.py](../pipeline.py)
8. [gui.py](../gui.py)

That gives a clean path from:

- purpose
- boundary
- architecture
- evidence
- implementation

without forcing the reviewer to dig through the whole repository alone.
