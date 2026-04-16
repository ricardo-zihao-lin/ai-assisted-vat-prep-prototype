@echo off
setlocal

set "ROOT=%~dp0.."
pushd "%ROOT%"

if not exist "venv\Scripts\python.exe" (
    echo Virtual environment not found at venv\Scripts\python.exe
    echo Create it first, then rerun this demo launcher.
    popd
    exit /b 1
)

venv\Scripts\python.exe main.py --input data\demo\dirty_data.csv --output-dir output\gif_demo
set "EXIT_CODE=%ERRORLEVEL%"

popd
exit /b %EXIT_CODE%
