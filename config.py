import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _path(name: str, default: str) -> Path:
    return Path(os.getenv(name, default))


# Grafana uses port 5000 on the mountain machine; use a different port here.
HOST = os.getenv("LS4_GUI_HOST", "0.0.0.0")
PORT = int(os.getenv("LS4_GUI_PORT", "8080"))

SECRET_KEY = os.getenv("LS4_GUI_SECRET_KEY", "dev-only-change-me-in-production")

GUI_USERNAME = os.getenv("LS4_GUI_USERNAME", "observer")
GUI_PASSWORD = os.getenv("LS4_GUI_PASSWORD", "changeme")

# When True, hardware actions are mocked. Default true for safe first boot.
SIMULATE = os.getenv("LS4_GUI_SIMULATE", "true").lower() in {"1", "true", "yes"}

# Python interpreter used for subprocess helpers (PDU script, sim tools, etc.).
GUI_PYTHON = os.getenv("LS4_GUI_PYTHON", "python3")

# --- Mountain paths (defaults match ls4-workstn / ls4-nuc layout) ---

OBSERVER_HOME = _path("LS4_OBSERVER_HOME", "/home/observer")
KENNETH_DIR = _path("LS4_KENNETH_DIR", "/home/ls4/kenneth")
LS4_DATA_DIR = _path("LS4_DATA_DIR", "/data/observer")

FLUX_METER_SNAPSHOT_DIR = _path("LS4_FLUX_METER_SNAPSHOT_DIR", "/home/ls4/snapshots")
TCS_WEBCAM_DIR = _path("LS4_TCS_WEBCAM_DIR", str(KENNETH_DIR))
OIL_PUMP_IMAGE_DIR = _path("LS4_OIL_PUMP_IMAGE_DIR", str(KENNETH_DIR))
READ_PRESSURE_SCRIPT = _path("LS4_READ_PRESSURE_SCRIPT", str(KENNETH_DIR / "read_pressure.py"))
PRESSURE_LOG_FILE = _path("LS4_PRESSURE_LOG_FILE", str(KENNETH_DIR / "pressure_log.txt"))

# Sim state, webcam placeholders, and mosaic browser previews.
SIM_DIR = _path("LS4_SIM_DIR", str(OBSERVER_HOME / "sim"))
SIM_STATE_FILE = _path("LS4_SIM_STATE_FILE", str(SIM_DIR / "state.json"))
SIM_WEBCAM_DIR = _path("LS4_SIM_WEBCAM_DIR", str(SIM_DIR / "webcams"))
OIL_PUMP_RENDER_OUTPUT = _path(
    "LS4_OIL_PUMP_RENDER_OUTPUT",
    str(SIM_WEBCAM_DIR / "oil_pump_latest.svg"),
)
MOSAIC_PREVIEW_DIR = _path("LS4_MOSAIC_PREVIEW_DIR", str(SIM_DIR / "mosaics"))

# External scripts invoked on the mountain (override if tools move).
PDU_SCRIPT = _path("LS4_PDU_SCRIPT", str(KENNETH_DIR / "pdu_api.py"))
TCS_WEBCAM_SCRIPT = _path("LS4_TCS_WEBCAM_SCRIPT", str(KENNETH_DIR / "TCS_webcam.py"))
OIL_PUMP_CAPTURE_SCRIPT = _path(
    "LS4_OIL_PUMP_CAPTURE_SCRIPT",
    str(BASE_DIR / "scripts" / "render_oil_pump_pressure.py"),
)

# Observer shell environment used to run start_questctl, opendome_raw, mos, etc.
OBSERVER_BIN_DIR = _path("LS4_OBSERVER_BIN_DIR", str(OBSERVER_HOME / "bin"))
OBSERVER_TCSHRC = _path("LS4_OBSERVER_TCSHRC", str(OBSERVER_HOME / ".tcshrc"))
OBS_CONTROL_SCRIPT = _path("LS4_OBS_CONTROL_SCRIPT", str(OBSERVER_BIN_DIR / "obs_control_script"))

# --- UI / workflow tuning ---

DOME_TRANSITION_SECONDS = int(os.getenv("LS4_DOME_TRANSITION_SECONDS", "90"))
AWS_SERVER_URL = os.getenv("LS4_AWS_SERVER_URL", "http://32.195.133.207/")
WEBCAM_REFRESH_SECONDS = int(os.getenv("LS4_WEBCAM_REFRESH_SECONDS", "30"))

OPERATOR_PDU_OUTLETS = tuple(
    int(x.strip())
    for x in os.getenv("LS4_OPERATOR_PDU_OUTLETS", "1,2,3,4,8").split(",")
    if x.strip()
)

PDU_OUTLET_LABELS = {
    8: "Flux meter light",
}

LOGBOOK_URL = os.getenv(
    "LS4_LOGBOOK_URL",
    "https://docs.google.com/document/d/1TfwjvCbK3iwrGQz7A78CSYDjfwSEA4Grl423T3Ru5Ss/edit",
)

ENABLE_SCHEDULER_PAUSE = os.getenv("LS4_ENABLE_SCHEDULER_PAUSE", "false").lower() in {
    "1",
    "true",
    "yes",
}

DEBUG = os.getenv("LS4_GUI_DEBUG", "false").lower() in {"1", "true", "yes"}
