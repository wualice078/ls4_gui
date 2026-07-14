"""Invoke mountain observer commands from the simulated observer home."""

from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path

from config import (
    AUX_CAM_TAG,
    AUX_IMAGE_DIR,
    AUX_REMOTE_DIR,
    AUX_REMOTE_HOST,
    AUX_SSH_KEY,
    AUX_SYNC_ENABLED,
    DOME_CAM_TAG,
    DOME_IMAGE_DIR,
    DOME_REMOTE_DIR,
    DOME_REMOTE_HOST,
    DOME_SSH_KEY,
    DOME_SYNC_ENABLED,
    FLUX_METER_SNAPSHOT_DIR,
    GUI_PYTHON,
    KENNETH_DIR,
    LS4_DATA_DIR,
    OBSERVER_HOME,
    OBSERVER_TCSHRC,
    OBS_CONTROL_SCRIPT,
    OIL_PUMP_CAPTURE_SCRIPT,
    OIL_PUMP_CAM_TAG,
    OIL_PUMP_IMAGE_DIR,
    OIL_PUMP_JUMP_HOST,
    OIL_PUMP_REMOTE_DIR,
    OIL_PUMP_REMOTE_GLOB,
    OIL_PUMP_REMOTE_HOST,
    OIL_PUMP_RENDER_OUTPUT,
    OIL_PUMP_SSH_KEY,
    OIL_PUMP_SYNC_ENABLED,
    PDU_SCRIPT,
    SIM_WEBCAM_DIR,
    TCS_WEBCAM_DIR,
    TCS_WEBCAM_SCRIPT,
)


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

    python = os.environ.get("LS4_GUI_PYTHON", GUI_PYTHON)
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
    shell = f"cd {OBSERVER_HOME}; source {OBSERVER_TCSHRC}; {command}"
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
    pdu = PDU_SCRIPT
    result = subprocess.run(
        [str(Path(os.environ.get("LS4_GUI_PYTHON", GUI_PYTHON))), str(pdu), flag, str(outlet)],
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


def dated_data_dirs() -> list[Path]:
    if not LS4_DATA_DIR.exists():
        return []
    return sorted(
        [path for path in LS4_DATA_DIR.iterdir() if path.is_dir()],
        key=lambda path: path.name,
    )


def find_data_dir_for_prefix(prefix: str) -> Path | None:
    """Find the newest night directory containing exposures for this prefix."""
    prefix = prefix.strip()
    if not prefix:
        return None

    for directory in reversed(dated_data_dirs()):
        matches = list(directory.glob(f"{prefix}*"))
        if matches:
            return directory

    if LS4_DATA_DIR.exists() and list(LS4_DATA_DIR.glob(f"{prefix}*")):
        return LS4_DATA_DIR

    return None


def find_existing_mosaic(prefix: str, data_dir: Path | None = None) -> Path | None:
    """Return an existing mos_*.fits for this prefix if one is already on disk."""
    prefix = prefix.strip()
    search_dirs: list[Path] = []
    if data_dir is not None:
        search_dirs.append(data_dir)
    search_dirs.extend(reversed(dated_data_dirs()))
    if LS4_DATA_DIR.exists():
        search_dirs.append(LS4_DATA_DIR)

    seen: set[Path] = set()
    patterns = (
        f"mos_*{prefix}*.fits",
        f"mos_*{prefix}*.fit",
        "mos_*.fits",
        "mos_*.fit",
    )

    for directory in search_dirs:
        if directory in seen or not directory.exists():
            continue
        seen.add(directory)

        for pattern in patterns[:2]:
            matches = sorted(directory.glob(pattern), key=lambda path: path.stat().st_mtime)
            if matches:
                return matches[-1]

    for directory in search_dirs:
        if directory in seen or not directory.exists():
            continue
        for pattern in patterns[2:]:
            matches = sorted(directory.glob(pattern), key=lambda path: path.stat().st_mtime)
            if matches:
                return matches[-1]

    return None


def run_make_mosaic(prefix: str, data_dir: Path | None = None) -> tuple[bool, str, Path | None]:
    target_dir = data_dir or find_data_dir_for_prefix(prefix) or LS4_DATA_DIR
    if not target_dir.exists():
        return False, f"Data directory not found: {target_dir}", None

    existing = find_existing_mosaic(prefix, target_dir)
    if existing is not None:
        return True, f"Using existing mosaic {existing.name} in {target_dir}.", existing

    result = _tcsh(f"cd {target_dir}; mos {prefix}", timeout=300)
    output = (result.stdout or "") + (result.stderr or "")
    output = output.strip() or f"mos {prefix} finished"

    mosaic = find_existing_mosaic(prefix, target_dir)
    if mosaic is not None:
        return result.returncode == 0, output, mosaic

    return result.returncode == 0, output, None


def latest_flux_meter_snapshot() -> Path | None:
    return _latest_image(FLUX_METER_SNAPSHOT_DIR, "*_cam3.jpg")


def latest_tcs_snapshot() -> Path | None:
    return _latest_image(TCS_WEBCAM_DIR, "TCScam*.jpg")


def latest_dome_snapshot() -> Path | None:
    tagged = _latest_image(DOME_IMAGE_DIR, f"*_{DOME_CAM_TAG}.jpg")
    if tagged is not None:
        return tagged
    for cam_tag in ("cam1", "cam2", "cam3"):
        image = _latest_image(DOME_IMAGE_DIR, f"*_{cam_tag}.jpg")
        if image is not None:
            return image
    return None


def latest_oil_pump_snapshot() -> Path | None:
    image = _latest_image(OIL_PUMP_IMAGE_DIR, "webpump_*.jpg")
    if image is not None:
        return image
    image = _latest_image(OIL_PUMP_IMAGE_DIR, "*oil*pump*.jpg")
    if image is not None:
        return image

    tagged = _latest_image(OIL_PUMP_IMAGE_DIR, f"*_{OIL_PUMP_CAM_TAG}.jpg")
    if tagged is not None:
        return tagged

    for pattern in ("*manometer*.jpg", "*pressure*.jpg", "*.jpg", "*.png"):
        image = _latest_image(OIL_PUMP_IMAGE_DIR, pattern)
        if image is not None:
            return image
    for candidate in (OIL_PUMP_RENDER_OUTPUT, SIM_WEBCAM_DIR / "oil_pump_latest.svg"):
        if candidate.exists():
            return candidate
    return None


def latest_aux_snapshot() -> Path | None:
    tagged = _latest_image(AUX_IMAGE_DIR, f"*_{AUX_CAM_TAG}.jpg")
    if tagged is not None:
        return tagged
    return _latest_image(AUX_IMAGE_DIR, "*.jpg")


def _sync_snapshot_images(
    *,
    enabled: bool,
    remote_host: str,
    remote_dir: Path,
    ssh_key: Path,
    image_dir: Path,
    cam_tag: str,
    label: str,
) -> tuple[bool, str]:
    if not enabled:
        return False, f"{label} remote sync disabled."
    if not remote_host:
        return False, f"{label} remote host not configured."
    if not ssh_key.exists():
        return False, f"{label} SSH key not found: {ssh_key}"

    image_dir.mkdir(parents=True, exist_ok=True)
    include_pattern = f"*_{cam_tag}.jpg"
    ssh_opts = (
        f"ssh -i {ssh_key} "
        "-o BatchMode=yes "
        "-o StrictHostKeyChecking=accept-new"
    )
    result = subprocess.run(
        [
            "rsync",
            "-az",
            "--include",
            "*/",
            "--include",
            include_pattern,
            "--exclude",
            "*",
            "-e",
            ssh_opts,
            f"{remote_host}:{remote_dir}/",
            f"{image_dir}/",
        ],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=OBSERVER_HOME,
    )
    if result.returncode != 0:
        output = ((result.stderr or "") + (result.stdout or "")).strip()
        return False, output or f"{label} snapshot sync failed."

    return True, f"Synchronized {label.lower()} snapshots ({include_pattern})."


def sync_via_jump_host(
    *,
    enabled: bool,
    jump_host: str,
    remote_host: str,
    remote_dir: Path,
    remote_glob: str,
    ssh_key: Path,
    image_dir: Path,
    label: str,
) -> tuple[bool, str]:
    """Pull the newest matching remote file through a jump host (nuc → interlock)."""
    if not enabled:
        return False, f"{label} remote sync disabled."
    if not jump_host or not remote_host:
        return False, f"{label} jump/remote host not configured."
    if not ssh_key.exists():
        return False, f"{label} SSH key not found: {ssh_key}"

    image_dir.mkdir(parents=True, exist_ok=True)
    remote_pattern = f"{remote_dir}/{remote_glob}"
    locate_remote = (
        f"ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new {remote_host} "
        f"{shlex.quote(f'ls -t {remote_pattern} 2>/dev/null | head -1')}"
    )
    locate = subprocess.run(
        [
            "ssh",
            "-i",
            str(ssh_key),
            "-o",
            "BatchMode=yes",
            "-o",
            "StrictHostKeyChecking=accept-new",
            jump_host,
            locate_remote,
        ],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=OBSERVER_HOME,
    )
    if locate.returncode != 0:
        output = ((locate.stderr or "") + (locate.stdout or "")).strip()
        return False, output or f"{label}: failed to locate remote image."

    remote_path = (locate.stdout or "").strip().splitlines()
    if not remote_path or not remote_path[0].strip():
        return False, f"{label}: no files matching {remote_pattern}."
    remote_file = remote_path[0].strip()
    local_file = image_dir / Path(remote_file).name

    pull_remote = (
        f"ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new {remote_host} "
        f"{shlex.quote('cat ' + shlex.quote(remote_file))}"
    )
    pull = subprocess.run(
        [
            "ssh",
            "-i",
            str(ssh_key),
            "-o",
            "BatchMode=yes",
            "-o",
            "StrictHostKeyChecking=accept-new",
            jump_host,
            pull_remote,
        ],
        capture_output=True,
        timeout=60,
        cwd=OBSERVER_HOME,
    )
    if pull.returncode != 0:
        err = (pull.stderr or b"").decode("utf-8", errors="replace").strip()
        return False, err or f"{label}: failed to pull {remote_file}."

    local_file.write_bytes(pull.stdout)
    return True, f"Synchronized {label.lower()} image ({local_file.name})."


def sync_dome_snapshots() -> tuple[bool, str]:
    return _sync_snapshot_images(
        enabled=DOME_SYNC_ENABLED,
        remote_host=DOME_REMOTE_HOST,
        remote_dir=DOME_REMOTE_DIR,
        ssh_key=DOME_SSH_KEY,
        image_dir=DOME_IMAGE_DIR,
        cam_tag=DOME_CAM_TAG,
        label="Dome",
    )


def sync_oil_pump_snapshots() -> tuple[bool, str]:
    return sync_via_jump_host(
        enabled=OIL_PUMP_SYNC_ENABLED,
        jump_host=OIL_PUMP_JUMP_HOST,
        remote_host=OIL_PUMP_REMOTE_HOST,
        remote_dir=OIL_PUMP_REMOTE_DIR,
        remote_glob=OIL_PUMP_REMOTE_GLOB,
        ssh_key=OIL_PUMP_SSH_KEY,
        image_dir=OIL_PUMP_IMAGE_DIR,
        label="Oil pump",
    )


def sync_aux_snapshots() -> tuple[bool, str]:
    return _sync_snapshot_images(
        enabled=AUX_SYNC_ENABLED,
        remote_host=AUX_REMOTE_HOST,
        remote_dir=AUX_REMOTE_DIR,
        ssh_key=AUX_SSH_KEY,
        image_dir=AUX_IMAGE_DIR,
        cam_tag=AUX_CAM_TAG,
        label="Aux",
    )


def refresh_oil_pump() -> tuple[bool, str, Path | None]:
    sync_ok, sync_message = sync_oil_pump_snapshots()
    image = latest_oil_pump_snapshot()
    if image is not None and image.suffix.lower() in {".jpg", ".jpeg", ".png"}:
        if sync_ok:
            return True, f"Oil pump image loaded ({image.name}). {sync_message}", image
        return True, f"Oil pump image loaded ({image.name}).", image

    ok, message, path = _run_capture_script(OIL_PUMP_CAPTURE_SCRIPT, [])
    if path is not None and path.exists():
        return True, message or f"Oil pump pressure rendered ({path.name}).", path

    stale = latest_oil_pump_snapshot()
    if stale is not None:
        if sync_ok:
            return True, f"{message} {sync_message} Showing last rendered gauge ({stale.name}).", stale
        return True, f"{message} Showing last rendered gauge ({stale.name}).", stale

    return False, message or "Oil pump pressure gauge unavailable.", None


def refresh_flux_meter() -> tuple[bool, str, Path | None]:
    snapshot = latest_flux_meter_snapshot()
    if snapshot is not None:
        return True, f"Flux meter snapshot loaded ({snapshot.name}).", snapshot

    return False, f"No flux meter images found in {FLUX_METER_SNAPSHOT_DIR}", None


def refresh_webcam(camera: str) -> tuple[bool, str, Path | None]:
    if camera == "dome":
        sync_ok, sync_message = sync_dome_snapshots()
        image = latest_dome_snapshot()
        if image is not None:
            if sync_ok:
                return True, f"Dome camera loaded ({image.name}). {sync_message}", image
            return True, f"Dome camera loaded ({image.name}).", image
        return False, f"{sync_message} No dome images found in {DOME_IMAGE_DIR}", None

    if camera == "aux":
        sync_ok, sync_message = sync_aux_snapshots()
        image = latest_aux_snapshot()
        if image is not None:
            if sync_ok:
                return True, f"Aux camera loaded ({image.name}). {sync_message}", image
            return True, f"Aux camera loaded ({image.name}).", image
        return False, f"{sync_message} No aux images found in {AUX_IMAGE_DIR}", None

    if camera == "tcs":
        image = latest_tcs_snapshot()
        if image is not None:
            return True, f"TCS webcam loaded ({image.name}).", image
        ok, message, path = _run_capture_script(TCS_WEBCAM_SCRIPT, ["--camera", "tcs"])
        if ok and path is not None:
            return ok, message, path
        return False, message or f"No TCS images found in {TCS_WEBCAM_DIR}", None

    if camera == "oil_pump":
        return refresh_oil_pump()

    return False, f"Unknown camera: {camera}", None


def resolve_webcam_image(camera: str) -> Path | None:
    if camera == "dome":
        return latest_dome_snapshot()
    if camera == "aux":
        return latest_aux_snapshot()
    if camera == "flux_meter":
        return latest_flux_meter_snapshot()
    if camera == "tcs":
        return latest_tcs_snapshot()
    if camera == "oil_pump":
        return latest_oil_pump_snapshot()
    return None


def observer_home_ready() -> bool:
    return OBSERVER_TCSHRC.exists() and OBS_CONTROL_SCRIPT.exists()
