# Deployment Guide

## 1. Deployment Strategy

This repository uses one shared Python core with multiple thin entry shells:

- `pipeline.py` and related modules keep the business logic
- `main.py` is the source-run shell
- `gui.py` is the shared browser GUI shell
- `build_demo.ps1` and `vat_spreadsheet_demo.spec` package the same GUI for Windows
- `Dockerfile` and `docker-compose.yml` containerise the same GUI service

This keeps deployment stable even while the evaluation layer is still changing.

## 2. Entry Points Summary

### Python / source run

- status: implemented
- purpose: developer use, dissertation reproduction, direct pipeline checks
- current packaging decision: source-run only, not PyPI at this stage

Why not PyPI yet:

- the repository is still a research prototype rather than a finished distributable library
- evaluation outputs and surrounding project structure are still evolving
- source-run is the most honest and maintainable Python entry for the current phase

### Local browser GUI

- status: implemented
- purpose: current main interaction entry
- technology: Gradio shell around the existing Python core

### Docker

- status: implemented
- purpose: environment-consistent demo and server baseline
- scope: same monolithic GUI service, not a frontend/backend split

### Windows packaged demo

- status: implemented
- purpose: main delivery format for teacher/reviewer/demo users
- technology: PyInstaller

### Web demo profile

- status: deployment path documented
- purpose: limited public-facing demo only
- not the default product form

## 3. Developer Source Run

Install dependencies first.

Windows:

```bat
venv\Scripts\python.exe -m pip install -r requirements.txt
```

macOS / Linux:

```bash
python3 -m pip install -r requirements.txt
```

Run the shared pipeline directly:

Windows:

```bat
venv\Scripts\python.exe main.py --input data\sample_data.csv --output-dir output
```

macOS / Linux:

```bash
python3 main.py --input data/sample_data.csv --output-dir output
```

Notes:

- `main.py` remains a thin shell around `run_pipeline(...)`
- it is intended for reproducible source runs, not as the main end-user interface
- you can pass any local CSV/XLS/XLSX file path with `--input`

## 4. Local Browser GUI

Run the main GUI entry directly from source.

Windows:

```bat
venv\Scripts\python.exe gui.py --host 127.0.0.1 --port 7860
```

Convenience launcher:

```bat
run_demo.bat
```

macOS:

```bash
./run_demo_mac.command
```

What the macOS script does:

- creates `.venv-mac/` on first run if needed
- installs `requirements.txt`
- starts the same `gui.py` local service

Useful runtime options:

```bash
python3 gui.py --host 127.0.0.1 --port 7860
python3 gui.py --no-browser
python3 gui.py --mode public-demo --disable-ai --max-file-size 10mb
```

Environment variables supported by `gui.py`:

- `VAT_GUI_HOST`
- `VAT_GUI_PORT`
- `VAT_GUI_OPEN_BROWSER`
- `VAT_GUI_MODE`
- `VAT_GUI_ENABLE_AI`
- `VAT_GUI_MAX_FILE_SIZE`
- `VAT_GUI_ROOT_PATH`
- `VAT_GUI_STRICT_CORS`
- `VAT_GUI_SHARE`

## 5. Windows Packaged Demo

Build from Windows:

```powershell
.\build_demo.ps1
```

If you want to point the build at a specific interpreter:

```powershell
.\build_demo.ps1 -PythonExe python
```

Build outputs:

- `dist\VAT_Spreadsheet_Demo\`
- `dist\VAT_Spreadsheet_Demo_windows_x64.zip`

Package contents:

- `VAT_Spreadsheet_Demo.exe`
- `README_RUN_FIRST.txt`
- bundled sample input `data/sample_data.csv`

Current packaging choices:

- the package uses the existing Gradio GUI entry
- the package only bundles runtime demo files, not the whole evaluation/public-raw dataset tree
- outputs are written locally beside the executable under `output/`

Use the packaged demo:

1. unzip `VAT_Spreadsheet_Demo_windows_x64.zip`
2. open the extracted `VAT_Spreadsheet_Demo` folder
3. double-click `VAT_Spreadsheet_Demo.exe`
4. if the browser does not open automatically, visit the local URL shown in the console

## 6. Docker

Build and run locally:

```bash
docker compose up --build
```

Then open:

```text
http://127.0.0.1:7860
```

What the current Docker setup does:

- builds one container around the existing GUI service
- exposes the GUI on port `7860`
- mounts `./output` to persist run artefacts outside the container

Useful overrides:

```bash
VAT_GUI_PUBLISHED_PORT=7861 docker compose up --build
VAT_GUI_MODE=public_demo VAT_GUI_ENABLE_AI=0 VAT_GUI_MAX_FILE_SIZE=10mb docker compose up --build
```

Current limitation:

- Docker is a deployment shell only
- it does not turn the repository into a separated frontend/backend web app

## 7. Web Demo Profile

The current repository does **not** include a finished hosted public service. What it does include is a stable deployment path for a limited web demo using the same GUI service.

Recommended web demo posture:

- deploy the same container image behind a reverse proxy
- use `VAT_GUI_MODE=public_demo`
- consider `VAT_GUI_ENABLE_AI=0`
- consider `VAT_GUI_MAX_FILE_SIZE=10mb`
- avoid sensitive spreadsheets

Boundary for the web demo profile:

- local-first remains the default product form
- the web version is for demonstration, not the main delivery shape
- full uploaded spreadsheets are not sent to AI by default
- optional AI behaviour still uses a compact findings snapshot only
- high-risk or advanced capabilities can be disabled for public deployment

Example command for a hosted-style launch:

```bash
python3 gui.py --mode public-demo --host 0.0.0.0 --port 7860 --no-browser --disable-ai --max-file-size 10mb
```

## 8. GitHub Delivery Support

The repository now includes two lightweight GitHub Actions workflows.

### Windows package build

File:

```text
.github/workflows/build-windows-demo.yml
```

What it does:

- installs runtime dependencies plus PyInstaller
- runs `build_demo.ps1`
- uploads:
  - `dist/VAT_Spreadsheet_Demo`
  - `dist/VAT_Spreadsheet_Demo_windows_x64.zip`

Artifact name:

```text
vat-spreadsheet-demo-windows
```

### Docker validation

File:

```text
.github/workflows/validate-docker-demo.yml
```

What it does:

- builds the Docker image
- starts a container
- checks that the GUI responds on `http://127.0.0.1:7860/`

## 9. Why This Stays Friendly To Future Evaluation Changes

The evaluation work is still incomplete, so the deployment structure is deliberately insulated from it.

That remains true because:

- deployment shells call the existing pipeline rather than reimplementing stages
- Windows packaging only bundles runtime demo assets instead of evaluation datasets
- Docker runs the same GUI shell instead of a parallel platform-specific implementation
- GitHub workflows validate the delivery paths, not the evaluation logic itself

So if you later change:

- metrics
- exported evaluation tables
- experiment scripts
- public dataset comparison logic
- review/evaluation methodology

you should not need to redesign the deployment entry points again.
