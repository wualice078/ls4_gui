"""Invoke mountain observer commands from the simulated observer home."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from config import FLUX_METER_SNAPSHOT_DIR, KENNETH_DIR, LS4_DATA_DIR, OBSERVER_HOME


def _latest_image(directory: Path, pattern: str) -> Path | None:
    if not directory.exists():
        return None
    images = sorted(
        directory.glob(pattern),
        key=lambda path: path.stat().st_mtime,
    )
    return images[-1] if images else None


def _run_capture_script(script: Path, args: list[str]) -> tuple[bool, str, Path | None]:
    if not script.exists():
        return False, f"Script not found: {script}", None

    python = os.environ.get("LS4_GUI_PYTHON", "/home/ls4/ls4_venv/bin/python")
    result = subprocess.run(
        [python, str(script), *args],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=OBSERVER_HOME,
    )
    if result.returncode != 0:
        output = (result.stdout or "") + (result.stderr or "")
        return False, output.strip() or f"{script.name} failed", None
    image_path = Path((result.stdout or "").strip())
    if image_path.exists():
        return True, f"{script.name} finished.", image_path
    return False, f"{script.name} did not produce an image path.", None


def _tcsh(command: str, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["LS4_ROOT"] = str(OBSERVER_HOME)
    shell = f"cd {OBSERVER_HOME}; source {OBSERVER_HOME}/.tcshrc; {command}"
    return subprocess.run(
        ["tcsh", "-fc", shell],
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
        cwd=OBSERVER_HOME,
    )


def run_obs_control(action: str) -> tuple[bool, str]:
    allowed = {"start", "stop", "pause", "unpause", "new", "cleanup"}
    if action not in allowed:
        return False, f"Unknown scheduler action: {action}"
    result = _tcsh(f"obs_control_script {action}", timeout=180)
    output = (result.stdout or "") + (result.stderr or "")
    output = output.strip() or f"obs_control_script {action} finished"
    return result.returncode == 0, output


def run_start_questctl() -> tuple[bool, str]:
    result = _tcsh("start_questctl", timeout=180)
    output = (result.stdout or "") + (result.stderr or "")
    output = output.strip() or "start_questctl finished"
    return result.returncode == 0, output


def run_stop_questctl() -> tuple[bool, str]:
    result = _tcsh("stop_questctl", timeout=120)
    output = (result.stdout or "") + (result.stderr or "")
    output = output.strip() or "stop_questctl finished"
    return result.returncode == 0, output


def run_opendome_raw() -> tuple[bool, str]:
    result = _tcsh("opendome_raw", timeout=60)
    output = (result.stdout or "") + (result.stderr or "")
    output = output.strip() or "opendome_raw finished"
    return result.returncode == 0, output


def run_closedome() -> tuple[bool, str]:
    result = _tcsh("closedome.csh", timeout=60)
    output = (result.stdout or "") + (result.stderr or "")
    output = output.strip() or "closedome.csh finished"
    return result.returncode == 0, output


def run_pdu(outlet: int, powered: bool) -> tuple[bool, str]:
    flag = "-p" if powered else "-o"
    pdu = KENNETH_DIR / "pdu_api.py"
    result = subprocess.run(
        [str(Path(os.environ.get("LS4_GUI_PYTHON", "/home/ls4/ls4_venv/bin/python"))), str(pdu), flag, str(outlet)],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=OBSERVER_HOME,
    )
    output = (result.stdout or "") + (result.stderr or "")
    return result.returncode == 0, output.strip()


def run_stow_telescope() -> tuple[bool, str]:
    result = _tcsh("stow_telescope", timeout=180)
    output = (result.stdout or "") + (result.stderr or "")
    output = output.strip() or "stow_telescope finished"
    return result.returncode == 0, output


def run_make_mosaic(prefix: str, data_dir: Path | None = None) -> tuple[bool, str, Path | None]:
    target_dir = data_dir or LS4_DATA_DIR
    if not target_dir.exists():
        return False, f"Data directory not found: {target_dir}", None

    result = _tcsh(f"cd {target_dir}; mos {prefix}", timeout=300)
    output = (result.stdout or "") + (result.stderr or "")
    output = output.strip() or f"mos {prefix} finished"

    mosaics = sorted(target_dir.glob("mos_*.fits"), key=lambda path: path.stat().st_mtime)
    if not mosaics:
        return result.returncode == 0, output, None
    return result.returncode == 0, output, mosaics[-1]


def latest_flux_meter_snapshot() -> Path | None:
    if not FLUX_METER_SNAPSHOT_DIR.exists():
        return None
    images = sorted(
        FLUX_METER_SNAPSHOT_DIR.glob("*_cam3.jpg"),
        key=lambda path: path.stat().st_mtime,
    )
    return images[-1] if images else None


def refresh_flux_meter() -> tuple[bool, str, Path | None]:
    snapshot = latest_flux_meter_snapshot()
    if snapshot is not None:
        return True, f"Flux meter snapshot loaded ({snapshot.name}).", snapshot

    return False, f"No flux meter images found in {FLUX_METER_SNAPSHOT_DIR}", None


def refresh_webcam(camera: str) -> tuple[bool, str, Path | None]:
    if camera == "tcs":
        image = _latest_image(KENNETH_DIR, "TCScam*.jpg")
        if image is not None:
            return True, f"TCS webcam loaded ({image.name}).", image
        return _run_capture_script(KENNETH_DIR / "TCS_webcam.py", ["--camera", "tcs"])

    if camera == "oil_pump":
        for pattern in ("*oil*pump*.jpg", "*oil*pump*.png", "*manometer*.jpg", "*pressure*.jpg"):
            image = _latest_image(KENNETH_DIR, pattern)
            if image is not None:
                return True, f"Oil pump image loaded ({image.name}).", image
        return _run_capture_script(KENNETH_DIR / "webpump_capture.py", ["--camera", "oil_pump"])

    return False, f"Unknown camera: {camera}", None


def observer_home_ready() -> bool:
    return (OBSERVER_HOME / ".tcshrc").exists() and (OBSERVER_HOME / "bin" / "obs_control_script").exists()
