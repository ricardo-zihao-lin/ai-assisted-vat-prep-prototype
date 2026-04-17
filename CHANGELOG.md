# Changelog

All notable changes to this undergraduate Final Year Project prototype are documented in this file.

The project follows pre-`1.0.0` semantic versioning to reflect an academic prototype that is still evolving, while still exposing clear milestone-based releases for supervisors, assessors, and demo users.

## [0.3.0] - 2026-04-17

### Added

- Delivery-oriented GUI refinements, including a reorganized Downloads tab with recommended exports, advanced exports, and plain-language guidance.
- Controlled VAT evaluation testbed generation and supporting evaluation artefacts for dissertation-aligned assessment.
- Contextual anomaly detection support to broaden review-signal coverage beyond basic deterministic validation.

### Changed

- Refined the review dashboard and exporter outputs to better support review summaries, auditability, and downstream explanation.
- Improved the Downloads experience so exported artefacts are presented as user tasks rather than a flat technical file list.
- Tightened the optimization-phase evaluation story by documenting precision and recall improvements against the poisoned testbed.
- Consolidated the current project state into a presentable dissertation demo milestone suitable for packaging and assessor walkthroughs.

### Fixed

- Optional VAT code validation handling to reduce avoidable false positives.
- Export and validation behavior around explanation-oriented outputs and review summary generation.

### Release focus

- Mature demo build for dissertation review.
- Stronger evaluation narrative and more defensible review workflow presentation.
- Cleaner user-facing downloads experience for assessors and demo users.

## [0.2.0] - 2026-04-15

### Added

- A local browser UI for interactive prototype demonstration.
- Review workflow improvements and a Visual Insights dashboard for run-level KPI and chart-based inspection.
- Review summaries and aligned export artefacts to complement issue, log, and history outputs.
- Public raw and adapted evaluation datasets to broaden prototype robustness testing.

### Changed

- Aligned the VAT review workflow with clearer export outputs and a more presentation-ready GUI structure.
- Updated documentation to reflect the prototype workflow, review artefacts, and AI suggestion path.

### Release focus

- First clearly demoable local review release.
- Clearer end-to-end flow from upload to review and exported artefacts.
- Stronger product shape for supervisors and assessors to inspect in the browser.

## [0.1.0] - 2026-03-22

### Added

- Initial dissertation-aligned VAT review prototype structure.
- Synthetic evaluation workflow and issue-chart support for early testing.
- Early anomaly-analysis support for controlled cases.

### Changed

- Refactored orchestration into a reusable pipeline entry point for source runs and dissertation evaluation.

### Release focus

- First runnable prototype baseline.
- Established the core architecture for ingestion, validation, anomaly screening, review, and export.
- Created the initial platform for later GUI, dashboard, and packaging improvements.
