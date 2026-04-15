# System Architecture

## 5.1 Architectural Overview

The prototype follows a modular pipeline architecture for preparing spreadsheet-based VAT records prior to submission-related activities. This structure reflects the practical workflow of small-business record preparation, where data is first loaded from a spreadsheet source, then checked for quality problems, examined for unusual transactions, reviewed by a human user, and finally exported as a set of supporting output files. The overall flow can therefore be described as Data Ingestion, Data Validation, Anomaly Detection, Human Review, and Export.

The design is centred on transparency, traceability, and support for human review. Each stage has a clearly defined role and produces outputs that can be inspected before the next stage is reached. This is important in the financial reporting context because the prototype is intended to assist record preparation rather than replace human judgement. For that reason, the system does not automatically alter financial records in response to detected issues or suspicious patterns.

## 5.2 Layered Component Design

The system is divided into a small number of focused components, each responsible for one stage of the processing workflow. The ingestion component in `ingestion/loader.py` reads spreadsheet data and prepares it in a consistent tabular form. The validation component in `validation/validator.py` examines the dataset for basic quality issues. The anomaly detection component in `anomaly/anomaly_detector.py` applies a simple statistical screening method to identify unusual transactions. The review component is represented by `review/review_manager.py` together with the browser-based workstation in `gui.py`, and the export component in `export/exporter.py` writes the final output files required for inspection and traceability.

These components interact sequentially, with the output of one stage becoming the input to the next stage. This sequential arrangement keeps the architecture easy to follow and supports clear separation of responsibilities. It also makes the prototype suitable for academic presentation because each module can be described independently while still forming part of a coherent end-to-end system for VAT record preparation.

## 5.3 Validation Engine Design

The validation engine, implemented in `validation/validator.py`, is responsible for identifying basic data quality problems within the spreadsheet records. It performs a set of straightforward checks that are appropriate for a lightweight research prototype: detection of missing values, identification of duplicate rows, recognition of invalid date formats, and detection of invalid numeric values. These checks are intended to highlight common spreadsheet errors that may affect the reliability of VAT records.

An important design decision is that the validation layer only reports issues and does not automatically correct them. This supports the wider aim of maintaining user control over financial data. In practice, the validation stage acts as an early screening layer that produces structured findings which can be examined later in the review process, rather than attempting to repair the dataset without user knowledge.

## 5.4 Anomaly Detection Design

The anomaly detection module, implemented in `anomaly/anomaly_detector.py`, provides a second analytical layer that focuses on unusual transaction values rather than structural data quality problems. The prototype uses a simple statistical outlier detection approach, such as an interquartile range based method, to identify records whose values differ notably from the rest of the dataset. This allows the system to flag transactions that may deserve closer inspection even when they are not technically invalid.

The purpose of this stage is decision support rather than automatic correction. A flagged transaction is not assumed to be wrong; instead, it is treated as a candidate for further human review. This distinction is especially important in financial contexts, where unusually large or small values may be legitimate business events. The anomaly module therefore contributes a prioritised set of suspicious records for later examination rather than enforcing automated decisions.

## 5.5 Human Review Workflow

The review process is represented through `review/review_manager.py` together with the local browser-based Review Centre in `gui.py` and reflects a human-in-the-loop workflow. In this design, issues identified during validation and records flagged by anomaly detection are brought together into a review queue where the user can inspect a selected finding, view its surrounding record context, and record a decision such as confirm, reject, ignore, or leave pending. This stage demonstrates that the final interpretation of detected problems remains a human responsibility rather than a purely automated system action.

Human oversight is particularly important for financial data preparation because bookkeeping records can contain exceptions, unusual transactions, or contextual details that cannot be fully understood by simple automated rules. By including a distinct review layer, the prototype reinforces the principle that analytical methods should support the user judgement instead of replacing it. This makes the system more appropriate for a VAT preparation setting, where accountability and interpretability are essential. The dual-pane review workstation is intended to reduce review friction by separating the queue of pending findings from the evidence and explanation shown for the currently selected item.

Alongside the Review Centre, the browser interface also provides a Visual Insights dashboard view. This view presents run-level KPI cards, chart-based summaries, and a priority findings table so that a user can quickly understand the scale and distribution of the current review workload before drilling down into individual findings. In architectural terms, this dashboard does not introduce a new processing layer; it is a presentation layer built on the same exported issue and review data.

## 5.6 Export and Output Artifacts

The export module in `export/exporter.py` is responsible for producing the final output artefacts generated by the prototype. These include `dataset_snapshot.csv`, `prepared_canonical_records.csv`, `issue_report.csv`, `review_log.csv`, and `review_history.csv`. Together, these files provide a practical summary of the preparation process: the spreadsheet data is preserved in a reusable form, detected issues are listed for inspection, and review decisions are recorded separately with a saved history.

This output design supports traceability by ensuring that the user can see what was identified by the system and how those findings were handled during review. Rather than hiding intermediate decisions, the prototype makes them visible through explicit reports. The `issue_report.csv` output now carries explanation-oriented metadata such as trigger reason, trigger rule, fields to check, and suggested action, while the review outputs capture both the latest state and the change history. These same exported fields also power the Visual Insights dashboard, which means the dashboard remains traceable back to the underlying review artefacts rather than relying on a separate analytics store.

## 5.7 System Execution Flow

The end-to-end execution of the prototype is coordinated in `main.py` and `pipeline.py`. These files act as the orchestration layer that links the separate modules into a complete processing pipeline. The sequence begins by loading spreadsheet data, after which validation checks are performed. The resulting dataset is then passed to the anomaly detection stage, and the combined findings are exported into a review-ready set of artefacts. In the browser-based route, these findings are then presented through the Review Centre so the user can inspect the relevant row, understand why it was flagged, and save a decision. Finally, the supporting reports remain available as output files for later inspection.

This pipeline structure keeps the prototype simple and easy to understand. Each stage performs one clear role, and the order of execution mirrors the intended business process of preparing spreadsheet VAT records for inspection. As a result, the system is not only practical to demonstrate but also straightforward to explain in a university dissertation, since the architectural flow directly reflects the functional purpose of the prototype.

## 5.8 GUI Shell Boundary

The browser interface in `gui.py` is intentionally larger than the core
pipeline modules because it serves as the presentation shell for several user
journeys at once: upload and run, review centre, visual insights, AI
assistance, and downloads. That size does not mean the GUI owns the business
logic. The actual review rules, review queue behaviour, explanations, and
output generation remain in the shared core modules.

This boundary is deliberate. The project is a local-first research prototype
rather than a split frontend/backend web application, so the main requirement
is consistency across source run, packaged demo, and Docker delivery. Keeping
`gui.py` as one shell avoids duplicating workflow logic across multiple UI
layers and makes the dissertation story easier to defend: the interface is the
presentation layer, while the core modules remain the system of record.

For a more detailed justification of the GUI structure, see
[docs/gui_architecture.md](docs/gui_architecture.md).
