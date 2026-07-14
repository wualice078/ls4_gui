#!/usr/bin/env python3
"""Generate simulated webcam snapshots for LS4 camera panels."""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

_DEFAULT_HOME = Path(__file__).resolve().parents[2] / "observer-home"
OBSERVER_HOME = Path(os.getenv("LS4_OBSERVER_HOME", str(_DEFAULT_HOME)))
SIM_DIR = Path(os.getenv("LS4_SIM_DIR", str(OBSERVER_HOME / "sim")))
STATE_FILE = Path(os.getenv("LS4_SIM_STATE_FILE", str(SIM_DIR / "state.json")))
WEBCAM_DIR = Path(os.getenv("LS4_SIM_WEBCAM_DIR", str(SIM_DIR / "webcams")))


def _load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {
        "webcams": {
            "oil_pump": {"pump_on": True},
            "tcs": {"servos_up": True},
        },
        "pdu_outlets": {"8": False},
    }


def _svg(title: str, subtitle: str, accent: str) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="800" height="450" viewBox="0 0 800 450">
  <rect width="800" height="450" fill="#111827"/>
  <rect x="30" y="30" width="740" height="390" rx="12" fill="#1f2937" stroke="#374151"/>
  <text x="400" y="110" fill="#f9fafb" font-family="sans-serif" font-size="34" text-anchor="middle">{title}</text>
  <text x="400" y="170" fill="{accent}" font-family="sans-serif" font-size="24" text-anchor="middle">{subtitle}</text>
  <text x="400" y="390" fill="#9ca3af" font-family="sans-serif" font-size="16" text-anchor="middle">Simulated snapshot · {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}</text>
</svg>"""


def _write_image(path: Path, svg: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(svg)
    return path


def capture_tcs(state: dict, output: Path | None) -> Path:
    servos_up = state.get("webcams", {}).get("tcs", {}).get("servos_up", True)
    subtitle = "Servos UP (safe to proceed)" if servos_up else "Servos DOWN (contact LO)"
    accent = "#22c55e" if servos_up else "#ef4444"
    path = output or WEBCAM_DIR / "tcs_latest.svg"
    return _write_image(path, _svg("TCS Servos", subtitle, accent))


def capture_oil_pump(state: dict, output: Path | None) -> Path:
    pump_on = state.get("webcams", {}).get("oil_pump", {}).get("pump_on", True)
    subtitle = "Oil pump ON · pressure OK" if pump_on else "Oil pump OFF · do not proceed"
    accent = "#22c55e" if pump_on else "#ef4444"
    path = output or WEBCAM_DIR / "oil_pump_latest.svg"
    return _write_image(path, _svg("Oil Pump Manometer", subtitle, accent))


def capture_flux_cam(state: dict, output: Path | None) -> Path:
    light_on = state.get("pdu_outlets", {}).get("8", False)
    subtitle = "Flux meter light ON" if light_on else "Flux meter light OFF"
    accent = "#38bdf8" if light_on else "#94a3b8"
    path = output or WEBCAM_DIR / "flux_meter_latest.svg"
    return _write_image(path, _svg("Flux Meter Camera", subtitle, accent))


def capture_dome(state: dict, output: Path | None) -> Path:
    dome_open = state.get("dome", {}).get("state") == "open"
    subtitle = "Dome OPEN · nuc cam1" if dome_open else "Dome CLOSED · nuc cam1"
    accent = "#22c55e" if dome_open else "#f59e0b"
    path = output or WEBCAM_DIR / "dome_latest.svg"
    return _write_image(path, _svg("Dome Camera (cam1)", subtitle, accent))


def capture_aux(state: dict, output: Path | None) -> Path:
    path = output or WEBCAM_DIR / "aux_latest.svg"
    return _write_image(path, _svg("Secondary Dome (cam2)", "nuc snapshots · cam2", "#38bdf8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--camera", choices=["tcs", "oil_pump", "flux", "dome", "aux"], default="tcs")
    parser.add_argument("-o", "--output")
    args = parser.parse_args()

    state = _load_state()
    output = Path(args.output) if args.output else None

    if args.camera == "tcs":
        path = capture_tcs(state, output)
    elif args.camera == "oil_pump":
        path = capture_oil_pump(state, output)
    elif args.camera == "dome":
        path = capture_dome(state, output)
    elif args.camera == "aux":
        path = capture_aux(state, output)
    else:
        path = capture_flux_cam(state, output)

    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
