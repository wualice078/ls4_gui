#!/usr/bin/env python3
"""Render oil pump vacuum gauge reading as an SVG for the LS4 GUI."""

from __future__ import annotations

import argparse
import os
import subprocess
import time
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_HOME = _REPO_ROOT.parent / "observer-home"
OBSERVER_HOME = Path(os.getenv("LS4_OBSERVER_HOME", str(_DEFAULT_HOME)))
KENNETH_DIR = Path(os.getenv("LS4_KENNETH_DIR", "/home/ls4/kenneth"))
SIM_WEBCAM_DIR = Path(os.getenv("LS4_SIM_WEBCAM_DIR", str(OBSERVER_HOME / "sim" / "webcams")))
READ_PRESSURE_SCRIPT = Path(
    os.getenv("LS4_READ_PRESSURE_SCRIPT", str(KENNETH_DIR / "read_pressure.py"))
)
PRESSURE_LOG_FILE = Path(os.getenv("LS4_PRESSURE_LOG_FILE", str(KENNETH_DIR / "pressure_log.txt")))
DEFAULT_OUTPUT = SIM_WEBCAM_DIR / "oil_pump_latest.svg"
GUI_PYTHON = os.getenv("LS4_GUI_PYTHON", "python3")


def _read_live() -> tuple[str | None, str]:
    if not READ_PRESSURE_SCRIPT.exists():
        return None, f"Script missing: {READ_PRESSURE_SCRIPT}"

    result = subprocess.run(
        [GUI_PYTHON, str(READ_PRESSURE_SCRIPT), "-p"],
        capture_output=True,
        text=True,
        timeout=15,
        cwd=KENNETH_DIR,
    )
    if result.returncode == 0:
        value = (result.stdout or "").strip().splitlines()[0].strip()
        if value:
            return value, "live gauge"

    detail = ((result.stderr or "") + (result.stdout or "")).strip()
    return None, detail or "gauge read failed"


def _read_log() -> tuple[str | None, str]:
    if not PRESSURE_LOG_FILE.exists():
        return None, f"No log at {PRESSURE_LOG_FILE}"

    lines = [line for line in PRESSURE_LOG_FILE.read_text().splitlines() if line.strip()]
    if not lines:
        return None, "pressure log is empty"

    last = lines[-1]
    if "\t" in last:
        timestamp, value = last.split("\t", 1)
        return value.strip(), f"log @ {timestamp.strip()}"

    parts = last.split()
    if len(parts) >= 2:
        return parts[-1], f"log @ {' '.join(parts[:-1])}"
    return last.strip(), "log"


def _svg(pressure: str, source: str, live: bool) -> str:
    accent = "#22c55e" if live else "#f59e0b"
    subtitle = f"{pressure} · {source}"
    stamp = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="800" height="450" viewBox="0 0 800 450">
  <rect width="800" height="450" fill="#111827"/>
  <rect x="30" y="30" width="740" height="390" rx="12" fill="#1f2937" stroke="#374151"/>
  <text x="400" y="100" fill="#f9fafb" font-family="sans-serif" font-size="34" text-anchor="middle">Oil Pump Vacuum Gauge</text>
  <text x="400" y="165" fill="#e2e8f0" font-family="sans-serif" font-size="42" text-anchor="middle">{pressure}</text>
  <text x="400" y="220" fill="{accent}" font-family="sans-serif" font-size="22" text-anchor="middle">{subtitle}</text>
  <text x="400" y="390" fill="#9ca3af" font-family="sans-serif" font-size="16" text-anchor="middle">Convectron 475 · {stamp}</text>
</svg>"""


def _error_svg(message: str) -> str:
    stamp = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    safe = message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")[:200]
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="800" height="450" viewBox="0 0 800 450">
  <rect width="800" height="450" fill="#111827"/>
  <rect x="30" y="30" width="740" height="390" rx="12" fill="#1f2937" stroke="#374151"/>
  <text x="400" y="110" fill="#f9fafb" font-family="sans-serif" font-size="34" text-anchor="middle">Oil Pump Vacuum Gauge</text>
  <text x="400" y="175" fill="#ef4444" font-family="sans-serif" font-size="24" text-anchor="middle">No reading available</text>
  <text x="400" y="230" fill="#94a3b8" font-family="sans-serif" font-size="18" text-anchor="middle">{safe}</text>
  <text x="400" y="390" fill="#9ca3af" font-family="sans-serif" font-size="16" text-anchor="middle">{stamp}</text>
</svg>"""


def render(output: Path) -> tuple[Path, bool, str]:
    value, source = _read_live()
    live = value is not None
    if value is None:
        value, source = _read_log()

    output.parent.mkdir(parents=True, exist_ok=True)
    if value is None:
        output.write_text(_error_svg(source))
        return output, False, source

    output.write_text(_svg(value, source, live))
    note = "live reading" if live else "stale log reading"
    return output, True, f"Oil pump pressure rendered ({note})."


def main() -> int:
    parser = argparse.ArgumentParser(description="Render oil pump pressure gauge for LS4 GUI")
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    path, ok, message = render(args.output)
    print(path)
    if not ok:
        print(message, file=os.sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
