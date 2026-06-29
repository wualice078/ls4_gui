#!/usr/bin/env bash
# Production-style server (no Flask "development server" warning).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="${LS4_GUI_PYTHON:-python3}"
WORKERS="${LS4_GUI_WORKERS:-2}"

cd "$ROOT"
BIND="$("$VENV_PYTHON" -c "from config import HOST, PORT; print(f'{HOST}:{PORT}')")"
exec "$VENV_PYTHON" -m gunicorn -w "$WORKERS" -b "$BIND" app:app
