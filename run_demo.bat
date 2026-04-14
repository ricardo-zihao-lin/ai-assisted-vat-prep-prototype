@echo off
setlocal

set "PROJECT_DIR=%~dp0"
set "VENV_PYTHON=%PROJECT_DIR%venv\Scripts\python.exe"

if exist "%VENV_PYTHON%" (
    "%VENV_PYTHON%" "%PROJECT_DIR%gui.py" --host 127.0.0.1 --port 7860
) else (
    python "%PROJECT_DIR%gui.py" --host 127.0.0.1 --port 7860
)

endlocal
