@echo off
setlocal

set "PROJECT_DIR=%~dp0"
set "VENV_PYTHON=%PROJECT_DIR%venv\Scripts\python.exe"

if exist "%VENV_PYTHON%" (
    "%VENV_PYTHON%" "%PROJECT_DIR%main.py"
) else (
    python "%PROJECT_DIR%main.py"
)

endlocal
