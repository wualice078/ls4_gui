"""Hardware and subsystem control layer for mountain + VM simulation."""

from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from config import (
    AWS_SERVER_URL,
    DOME_TRANSITION_SECONDS,
    ENABLE_SCHEDULER_PAUSE,
    LS4_DATA_DIR,
    MOSAIC_PREVIEW_DIR,
    OBSERVER_HOME,
    OPERATOR_PDU_OUTLETS,
    PDU_OUTLET_LABELS,
    SIMULATE,
    USE_MOUNTAIN_STACK,
)
from services import mountain
from services.mosaic_preview import fits_to_png
from sim.state import SimState


@dataclass
class ActionResult:
    ok: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)


class ControlService:
    def __init__(self) -> None:
        state_file = OBSERVER_HOME / "sim" / "state.json"
        self._sim = SimState(state_file, dome_transition_seconds=DOME_TRANSITION_SECONDS)
        self._last_webcam_fetch: dict[str, float] = {}
        self._latest_mosaic_preview: Path | None = None
        self._latest_mosaic_fits: Path | None = None

    def status(self) -> dict[str, Any]:
        snap = self._sim.snapshot()
        return {
            "simulate": SIMULATE,
            "observer_home": str(OBSERVER_HOME),
            "mountain_stack": USE_MOUNTAIN_STACK and mountain.observer_home_ready(),
            "dome": self._sim.dome_status(),
            "scheduler": snap["scheduler"],
            "telescope_services": snap["telescope_services"],
            "pdu_outlets": self._operator_pdu_status(snap["pdu_outlets"]),
            "pdu_outlet_labels": {str(k): v for k, v in PDU_OUTLET_LABELS.items()},
            "scheduler_pause_enabled": ENABLE_SCHEDULER_PAUSE,
            "aws_server_url": AWS_SERVER_URL,
            "latest_mosaic": self._latest_mosaic_fits.name if self._latest_mosaic_fits else None,
        }

    def open_dome(self) -> ActionResult:
        ok, message = self._sim.request_dome("open")
        if USE_MOUNTAIN_STACK and mountain.observer_home_ready():
            stack_ok, stack_msg = mountain.run_opendome_raw()
            if stack_ok:
                message = f"{message} [{stack_msg}]"
            else:
                message = f"{message} (mountain stack note: {stack_msg[:200]})"
        return ActionResult(ok, message, {"status": self.status()})

    def close_dome(self) -> ActionResult:
        ok, message = self._sim.request_dome("closed")
        if USE_MOUNTAIN_STACK and mountain.observer_home_ready():
            stack_ok, stack_msg = mountain.run_closedome()
            if stack_ok:
                message = f"{message} [{stack_msg}]"
            else:
                message = f"{message} (mountain stack note: {stack_msg[:200]})"
        return ActionResult(ok, message, {"status": self.status()})

    def telescope_start(self) -> ActionResult:
        if USE_MOUNTAIN_STACK and mountain.observer_home_ready():
            ok, message = mountain.run_start_questctl()
            if ok:
                self._sim.set_telescope_services("running")
            return ActionResult(ok, message, {"status": self.status()})

        self._sim.set_telescope_services("running")
        return ActionResult(True, "Telescope services started (simulated).", {"status": self.status()})

    def telescope_stop(self) -> ActionResult:
        if USE_MOUNTAIN_STACK and mountain.observer_home_ready():
            ok, message = mountain.run_stop_questctl()
            self._sim.set_telescope_services("stopped")
            return ActionResult(ok, message, {"status": self.status()})

        self._sim.set_telescope_services("stopped")
        return ActionResult(True, "Telescope services stopped (simulated).", {"status": self.status()})

    def stow_telescope(self) -> ActionResult:
        if USE_MOUNTAIN_STACK and mountain.observer_home_ready():
            ok, message = mountain.run_stow_telescope()
            return ActionResult(ok, message, {"status": self.status()})

        return ActionResult(True, "Telescope stowed (simulated).", {"status": self.status()})

    @staticmethod
    def _operator_pdu_status(all_outlets: dict[str, str]) -> dict[str, str]:
        return {
            str(outlet): all_outlets[str(outlet)]
            for outlet in OPERATOR_PDU_OUTLETS
            if str(outlet) in all_outlets
        }

    def set_pdu_outlet(self, outlet: int, powered: bool) -> ActionResult:
        if outlet not in OPERATOR_PDU_OUTLETS:
            return ActionResult(
                False,
                f"Outlet {outlet} is not operator-controllable.",
                {"status": self.status()},
            )

        ok, message = mountain.run_pdu(outlet, powered)
        if ok:
            self._sim.set_pdu_outlet(outlet, powered)
        return ActionResult(ok, message, {"status": self.status()})

    def scheduler_start(self) -> ActionResult:
        if USE_MOUNTAIN_STACK and mountain.observer_home_ready():
            ok, message = mountain.run_obs_control("start")
            if ok:
                self._sim.set_scheduler("running")
            return ActionResult(ok, message, {"status": self.status()})

        self._sim.set_scheduler("running")
        return ActionResult(True, "Observing started (simulated).", {"status": self.status()})

    def scheduler_stop(self) -> ActionResult:
        if USE_MOUNTAIN_STACK and mountain.observer_home_ready():
            ok, message = mountain.run_obs_control("stop")
            if ok:
                self._sim.set_scheduler("stopped")
            return ActionResult(ok, message, {"status": self.status()})

        self._sim.set_scheduler("stopped")
        return ActionResult(True, "Observing stopped (simulated).", {"status": self.status()})

    def scheduler_pause(self) -> ActionResult:
        if not ENABLE_SCHEDULER_PAUSE:
            return ActionResult(
                False,
                "Pause is disabled; use stop instead.",
                {"status": self.status()},
            )

        if USE_MOUNTAIN_STACK and mountain.observer_home_ready():
            ok, message = mountain.run_obs_control("pause")
            if ok:
                self._sim.set_scheduler("paused")
            return ActionResult(ok, message, {"status": self.status()})

        self._sim.set_scheduler("paused")
        return ActionResult(True, "Observing paused (simulated).", {"status": self.status()})

    def fetch_webcam(self, camera: str) -> ActionResult:
        allowed = {"oil_pump", "tcs", "flux_meter"}
        if camera not in allowed:
            return ActionResult(False, f"Unknown camera: {camera}")

        if camera == "flux_meter":
            ok, message, _path = mountain.refresh_flux_meter()
        else:
            ok, message, _path = mountain.refresh_webcam(camera)

        now = time.time()
        self._last_webcam_fetch[camera] = now
        if ok:
            self._sim.mark_webcam_refresh(camera)
        return ActionResult(
            ok,
            message,
            {"camera": camera, "fetched_at": now, "status": self.status()},
        )

    def webcam_image_path(self, camera: str) -> Path | None:
        mapping = {
            "oil_pump": OBSERVER_HOME / "sim" / "webcams" / "oil_pump_latest.svg",
            "tcs": OBSERVER_HOME / "sim" / "webcams" / "tcs_latest.svg",
            "flux_meter": self._flux_meter_image_path(),
        }
        path = mapping.get(camera)
        if path and path.exists():
            return path
        self.fetch_webcam(camera)
        path = mapping.get(camera)
        return path if path and path.exists() else None

    def _flux_meter_image_path(self) -> Path:
        snapshot = mountain.latest_flux_meter_snapshot()
        if snapshot is not None:
            return snapshot
        return OBSERVER_HOME / "snapshots" / "flux_meter_latest.svg"

    def generate_mosaic(self, prefix: str) -> ActionResult:
        prefix = prefix.strip()
        if not prefix:
            return ActionResult(False, "Exposure prefix is required.", {"status": self.status()})

        data_dir = self._data_dir_for_today()
        fits_path: Path | None = None
        message = ""
        ok = False

        if USE_MOUNTAIN_STACK and mountain.observer_home_ready() and data_dir.exists():
            ok, message, fits_path = mountain.run_make_mosaic(prefix, data_dir)

        if fits_path is None:
            sim_ok, sim_message, sim_path = self._simulate_mosaic(prefix)
            ok = sim_ok
            if message:
                message = f"{message} Using simulated preview: {sim_message}"
            else:
                message = sim_message
            fits_path = sim_path

        preview = self._ensure_mosaic_preview(fits_path, prefix)
        self._latest_mosaic_fits = fits_path
        self._latest_mosaic_preview = preview
        return ActionResult(
            ok,
            message,
            {
                "prefix": prefix,
                "mosaic_file": fits_path.name if fits_path else None,
                "preview_ready": preview is not None and preview.exists(),
                "status": self.status(),
            },
        )

    def mosaic_preview_path(self) -> Path | None:
        if self._latest_mosaic_preview and self._latest_mosaic_preview.exists():
            return self._latest_mosaic_preview
        candidates = sorted(
            MOSAIC_PREVIEW_DIR.glob("mosaic_preview.*"),
            key=lambda path: path.stat().st_mtime,
        )
        if candidates:
            self._latest_mosaic_preview = candidates[-1]
            return candidates[-1]
        return None

    def _data_dir_for_today(self) -> Path:
        if LS4_DATA_DIR.exists():
            dated_dirs = sorted(
                [path for path in LS4_DATA_DIR.iterdir() if path.is_dir()],
                key=lambda path: path.name,
            )
            if dated_dirs:
                return dated_dirs[-1]
        return LS4_DATA_DIR

    def _simulate_mosaic(self, prefix: str) -> tuple[bool, str, Path | None]:
        script = Path(__file__).resolve().parents[1] / "sim" / "generate_mosaic.py"
        python = Path(os.environ.get("LS4_GUI_PYTHON", "/home/ls4/ls4_venv/bin/python"))
        output = MOSAIC_PREVIEW_DIR / "mosaic_latest.svg"
        result = subprocess.run(
            [str(python), str(script), prefix, "-o", str(output)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            output_text = (result.stdout or "") + (result.stderr or "")
            return False, output_text.strip() or "Simulated mosaic generation failed", None
        return True, f"Mosaic generated for {prefix} (simulated).", output

    def _ensure_mosaic_preview(self, fits_path: Path | None, prefix: str) -> Path | None:
        MOSAIC_PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
        if fits_path and fits_path.exists() and fits_path.suffix.lower() == ".fits":
            png_path = MOSAIC_PREVIEW_DIR / "mosaic_preview.png"
            if fits_to_png(fits_path, png_path):
                return png_path

        if fits_path and fits_path.exists():
            preview = MOSAIC_PREVIEW_DIR / f"mosaic_preview{fits_path.suffix}"
            preview.write_bytes(fits_path.read_bytes())
            return preview

        simulated = MOSAIC_PREVIEW_DIR / "mosaic_latest.svg"
        if simulated.exists():
            preview = MOSAIC_PREVIEW_DIR / "mosaic_preview.svg"
            preview.write_text(simulated.read_text())
            return preview

        ok, _, path = self._simulate_mosaic(prefix)
        if ok and path:
            preview = MOSAIC_PREVIEW_DIR / "mosaic_preview.svg"
            preview.write_text(path.read_text())
            return preview
        return None

    def webcam_last_fetch(self, camera: str) -> float | None:
        return self._last_webcam_fetch.get(camera)
