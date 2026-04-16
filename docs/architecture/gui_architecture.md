# GUI Architecture Notes

## Purpose

This note explains the current GUI structure so the dissertation can justify
why `gui.py` is intentionally larger than the core pipeline modules.

The current prototype is not organized as a separated frontend/backend web app.
It is a local-first research prototype with one shared Python core and one
presentation shell.

## What `gui.py` Is Responsible For

`gui.py` acts as the browser presentation shell for the prototype. It handles:

- launch configuration and runtime options
- file upload and run initiation
- review queue filtering and record selection
- visual summaries and charts
- save/reload review decisions
- optional AI suggestion orchestration
- rendering the download/export panel

In other words, it is the interaction layer, not the rule engine.

## What `gui.py` Is Not Responsible For

The GUI shell does not own the core business logic. That remains in:

- `pipeline.py`
- `ingestion/`
- `validation/`
- `anomaly/`
- `review/`
- `export/`
- `explanation/`
- `ai/`

The GUI reads and presents outputs from those modules. It does not implement
the actual VAT review rules itself.

## Why The File Is Large

The file is large because the project uses a single Gradio shell that has to
cover several presentation concerns at once:

- upload/run flow
- review centre
- dashboard/visual insights
- AI assistant panel
- downloads and exports
- launch/runtime adaptation for local and demo modes

That size reflects presentation breadth, not core algorithmic complexity.

## Why This Is Acceptable For The Dissertation

For an undergraduate prototype, this structure is defensible because it keeps
the architecture honest:

- one shared Python core
- one browser presentation shell
- thin entry points for source, packaging, Docker, and demo delivery

This reduces duplication and keeps the evaluation, rules, and review logic in
the shared core rather than scattering them across multiple UI-specific
implementations.

## Defense Talking Point

If asked why `gui.py` is not split into a full frontend/backend architecture,
the strongest answer is:

> The project is intentionally a local-first prototype. I kept the business
> logic in the shared Python core and allowed the GUI to remain a single
> presentation shell so the evaluation, review, and export behaviours stay
> consistent across source run, packaged demo, and Docker delivery.

That answer makes the design choice look deliberate rather than unfinished.
