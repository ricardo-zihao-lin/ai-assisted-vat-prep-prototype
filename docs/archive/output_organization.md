# Output Organization Note

This note records the intended output split that was discussed during the
repository cleanup.

The layout is useful as a target for the dissertation evidence structure, but
it should be read as a planning note unless the current scripts and folders are
explicitly updated to match it.

## Directory Roles

- `output/runs/`
  - transient run artefacts
  - regenerated pipeline outputs
  - dataset-level comparison files
  - per-run realism dataset exports

- `output/evidence/`
  - dissertation-facing tables
  - summaries that are cited in the write-up
  - curated figures
  - comparison summaries and assertion summaries

- `output/archive/`
  - reserved for old snapshots or deprecated exports
  - not used as the default destination by the current scripts

## Intended Evaluation Layout

The target layout places evaluation evidence under:

- `output/evidence/evaluation/`

The transient data used to produce that evidence is written under:

- `output/runs/evaluation/`

The legacy root-level files may still be present for compatibility, but the
structured layout above is the preferred long-term direction.

## What To Cite In The Dissertation

Use the files under `output/evidence/evaluation/` as the primary citations:

- `synthetic_evaluation_summary.csv`
- `evaluation_assertion_summary.csv`
- `evaluation_assertion_results_table.csv`
- `evaluation_results_overview.csv`
- `figures/evaluation_evidence_chart.png`
- `usefulness_validation_pack/usefulness_comparison_summary.csv`
- `usefulness_validation_pack/usefulness_comparison_results.csv`

Use `output/runs/` only when describing the generation process or transient
execution artefacts.
