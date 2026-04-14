#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="$SCRIPT_DIR/.venv-mac"
STAMP_FILE="$VENV_DIR/.requirements-installed"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "python3 was not found. Install Python 3 first, then run this script again."
  exit 1
fi

if [ ! -x "$VENV_DIR/bin/python" ]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

if [ ! -f "$STAMP_FILE" ] || [ requirements.txt -nt "$STAMP_FILE" ]; then
  "$VENV_DIR/bin/python" -m pip install --upgrade pip
  "$VENV_DIR/bin/python" -m pip install -r requirements.txt
  touch "$STAMP_FILE"
fi

exec "$VENV_DIR/bin/python" gui.py --host 127.0.0.1 --port 7860
