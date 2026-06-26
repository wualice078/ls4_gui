#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="${LS4_GUI_PYTHON:-python3}"

cd "$ROOT"
exec "$VENV_PYTHON" app.py
