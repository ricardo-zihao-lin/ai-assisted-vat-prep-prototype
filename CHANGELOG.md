# Changelog

All notable changes to this undergraduate Final Year Project prototype are documented in this file.

The project follows pre-`1.0.0` semantic versioning to reflect an academic prototype that is still evolving, while still exposing clear milestone-based releases for supervisors, assessors, and demo users.

## [0.3.0] - 2026-04-17

### Added

- Contextual anomaly detection support to broaden review-signal coverage beyond basic deterministic validation.
- Controlled VAT evaluation testbed generation and supporting evaluation artefacts for dissertation-aligned assessment.
- Plain-language downloads guidance so exported outputs are easier to understand from a non-technical user perspective.

### Changed

- Refined the review dashboard and exporter outputs to better support review summaries, auditability, and downstream explanation.
- Reworked the Downloads tab around recommended exports, advanced exports, and a human-readable overview panel.
- Tightened the optimization-phase evaluation story by documenting precision and recall improvements against the poisoned testbed.

### Fixed

- Optional VAT code validation handling to reduce avoidable false positives.
- Export and validation behavior around explanation-oriented outputs and review summary generation.

### Release focus

- Mature demo build for dissertation review.
- Stronger evaluation narrative and more defensible review workflow presentation.
- Cleaner user-facing downloads experience for assessors and demo users.

## [0.2.0] - 2026-04-14

### Added

- Delivery-oriented entry shells and packaging workflows for source run, local browser GUI, Docker, and Windows demo packaging.
- Review workflow improvements and a Visual Insights dashboard for run-level KPI and chart-based inspection.
- Export review summaries to complement issue, log, and history artefacts.

### Changed

- Aligned the VAT review workflow with clearer export outputs and more presentation-ready GUI structure.
- Reorganized repository documentation and delivery notes to better support project review and demonstration.

### Release focus

- First polished demonstration-oriented release.
- Clearer end-to-end review flow from upload to exported review artefacts.
- Better packaging and delivery story for non-developer reviewers.

## [0.1.0] - 2026-03-22

### Added

- Initial dissertation-aligned VAT review prototype structure.
- Synthetic evaluation workflow and issue-chart support for early testing.
- Reusable pipeline entry point and the first minimal local browser UI for prototype demonstration.

### Changed

- Updated repository documentation to reflect the prototype direction, AI suggestion workflow, and evaluation positioning.

### Release focus

- First runnable prototype baseline.
- Established the core architecture for ingestion, validation, anomaly screening, review, and export.
- Created the initial platform for later GUI, dashboard, and packaging improvements.
