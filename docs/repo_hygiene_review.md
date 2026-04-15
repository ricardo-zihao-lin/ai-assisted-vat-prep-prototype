# Repository Hygiene Review

## Purpose

This note records a conservative repository review after the recent evaluation,
usefulness-validation, and realism-dataset work. The goal is to separate
core project assets from temporary or exploratory material without deleting
anything prematurely.

The guidance here is intentionally cautious:

- do not delete files only because they look old
- do not remove untracked directories without confirming they are outside the
  dissertation workflow
- prefer archiving or ignoring temporary material before deleting it

## Current Repository Groups

### 1. Core source and runtime files

These are part of the working prototype and should remain in the main project.

- `main.py`
- `pipeline.py`
- `gui.py`
- `ingestion/`
- `validation/`
- `anomaly/`
- `review/`
- `export/`
- `ai/`
- `explanation/`
- `vatrules/`

Notes:

- `gui.py` is still a large presentation shell, but it is now explained by the
  architecture documentation and should not be removed or split casually at
  this stage.
- `vatrules/` is currently untracked in Git status, but it contains active code
  rather than disposable output. It should be reviewed deliberately, not
  deleted as clutter.

### 2. Evaluation, realism, and test assets

These support dissertation evidence and should be preserved.

- `data/evaluation/`
- `data/realism/`
- `scripts/run_synthetic_evaluation.py`
- `scripts/build_evaluation_results_table.py`
- `scripts/build_evaluation_issue_chart.py`
- `scripts/build_usefulness_validation_pack.py`
- `scripts/generate_realism_vat_dataset.py`
- `tests/`
- `pytest.ini`
- `requirements-dev.txt`

These files now form part of the project's validation story, so they are not
"extra scripts". They are evidence-supporting assets.

### 3. Documentation to keep as active project docs

The following documentation is now part of the project's main narrative:

- `README.md`
- `architecture.md`
- `docs/evaluation_plan.md`
- `docs/evaluation_test_pack.md`
- `docs/evaluation_results.md`
- `docs/usefulness_validation_support.md`
- `docs/realism_dataset_support.md`
- `docs/gui_architecture.md`
- `docs/VAT_review_rules.md`
- `docs/VAT_review_workflow.md`

Recommended interpretation:

- `evaluation_plan.md` explains intent and scope
- `evaluation_test_pack.md` explains prepared scenarios
- `evaluation_results.md` records what was actually achieved
- `usefulness_validation_support.md` and
  `realism_dataset_support.md` explain the two newer evidence layers
- `gui_architecture.md` helps defend the current presentation-shell structure

### 4. Generated output and run artefacts

The `output/` directory is correctly ignored by Git and should remain outside
the committed source history.

It currently contains both useful evidence outputs and many one-off check runs.
That is acceptable during active development, but it is noisy.

Suggested internal interpretation:

- keep as evidence:
  - `evaluation_assertion_results.csv`
  - `evaluation_assertion_summary.csv`
  - `evaluation_assertion_results_table.csv`
  - `evaluation_results_overview.csv`
  - `evaluation_evidence_chart.png`
  - `usefulness_validation_pack/`
- treat as disposable run directories unless specifically needed for a write-up:
  - `codex_*`
  - `selfcheck_*`
  - `final_check_*`
  - `rerun_*`
  - `realism_check_run*`
  - `techdebt_check_*`
  - `tmp_eval`

No deletion is recommended until the dissertation artefacts and screenshots are
confirmed complete.

### 5. Temporary or external reference material

The following root-level items look like external repositories or temporary
inspection material rather than part of the dissertation system itself:

- `_tmp_deerflow2/`
- `_tmp_pdf2zh_mac/`
- `_tmp_pdfmathtranslate_repo/`
- `_tmp_pdf2zh_home.html`

Current recommendation:

- keep them out of version control
- do not cite them as part of the project
- store them under `archive/local_references/` while cleanup is in progress

They take a non-trivial amount of space and visually dilute the repository, but
they should be removed only after confirming they are not still being used as
reference material.

## Safe Cleanup Priorities

### Safe now

- keep `output/`, `build/`, `dist/`, `venv/`, and `_tmp_*` content ignored
- keep `archive/local_references/` ignored
- keep the newly added evaluation and realism docs
- keep the new tests and scripts
- keep `vatrules/` under review rather than treating it as junk

### Safe after confirmation

- archive or move the `_tmp_*` external-reference directories out of the repo
- prune one-off output run folders once their evidence is no longer needed
- remove root-level temporary HTML snapshots if they are no longer referenced

### Not recommended right now

- deleting `gui.py` fragments or performing a rushed UI refactor
- removing untracked code directories without checking imports and references
- collapsing documentation before the dissertation text is final

## Recommended Documentation Set for Submission

If the repository needs a cleaner final-facing document set, the strongest
subset is:

- `README.md`
- `architecture.md`
- `docs/evaluation_plan.md`
- `docs/evaluation_test_pack.md`
- `docs/evaluation_results.md`
- `docs/usefulness_validation_support.md`
- `docs/realism_dataset_support.md`
- `docs/gui_architecture.md`

This subset is enough to explain:

- project purpose and boundary
- system architecture
- how evaluation was designed
- what technical evidence exists
- how usefulness comparison is supported
- why the realism dataset is supplementary rather than the core proof
- why the GUI remains a shell rather than the source of business logic

## Next Conservative Step

Before any deletion, do one short confirmation pass:

1. confirm whether `vatrules/` is now part of the intended deliverable
2. confirm whether the `_tmp_*` directories are only external references
3. confirm which `output/` artefacts must be retained for screenshots, tables,
   or appendix evidence

Once those three points are confirmed, cleanup can be done with much lower risk.
