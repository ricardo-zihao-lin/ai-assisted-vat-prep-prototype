# Archive Notes

This directory is used for conservative repository cleanup.

It has two purposes:

- keep the repository root focused on active project assets
- avoid deleting temporary or external reference material before final
  confirmation

## Structure

- `local_references/`
  - local-only archived material moved out of the repository root
  - intentionally ignored by Git
- other files in `archive/`
  - tracked notes or manifests that explain what was archived and why

## Current Policy

- archive first, delete later only if still confirmed unnecessary
- keep active dissertation evidence in `docs/`, `data/`, `scripts/`, and
  tracked source modules
- keep generated evaluation evidence in `output/` until dissertation tables,
  screenshots, and appendix references are final
