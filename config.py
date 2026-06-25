import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# Grafana uses port 5000 on the mountain machine; use a different port here.
# Bind to a private LAN address on the mountain machine; login is required for access.
HOST = os.getenv("LS4_GUI_HOST", "0.0.0.0")
PORT = int(os.getenv("LS4_GUI_PORT", "8080"))

SECRET_KEY = os.getenv("LS4_GUI_SECRET_KEY", "dev-only-change-me-in-production")

# Operator credentials (override in .env on the real machine).
GUI_USERNAME = os.getenv("LS4_GUI_USERNAME", "observer")
GUI_PASSWORD = os.getenv("LS4_GUI_PASSWORD", "changeme")

# When True, hardware actions are mocked for the VM / dry-run testing.
SIMULATE = os.getenv("LS4_GUI_SIMULATE", "true").lower() in {"1", "true", "yes"}

# Simulated observer home that mirrors /home/observer on ls4-workstn.
OBSERVER_HOME = Path(os.getenv("LS4_OBSERVER_HOME", "/home/ls4/code/observer-home"))

KENNETH_DIR = Path(os.getenv("LS4_KENNETH_DIR", str(OBSERVER_HOME / "kenneth")))

# Call real observer scripts (start_questctl, obs_control_script, etc.) when ready.
USE_MOUNTAIN_STACK = os.getenv("LS4_USE_MOUNTAIN_STACK", "true").lower() in {
    "1",
    "true",
    "yes",
}

DOME_TRANSITION_SECONDS = int(os.getenv("LS4_DOME_TRANSITION_SECONDS", "90"))

AWS_SERVER_URL = os.getenv("LS4_AWS_SERVER_URL", "http://32.195.133.207/")

WEBCAM_REFRESH_SECONDS = int(os.getenv("LS4_WEBCAM_REFRESH_SECONDS", "30"))

# Outlets observers may toggle. Outlets 5–7 are infrastructure-only.
OPERATOR_PDU_OUTLETS = tuple(
    int(x.strip())
    for x in os.getenv("LS4_OPERATOR_PDU_OUTLETS", "1,2,3,4,8").split(",")
    if x.strip()
)

PDU_OUTLET_LABELS = {
    8: "Flux meter light",
}

FLUX_METER_SNAPSHOT_DIR = Path(
    os.getenv("LS4_FLUX_METER_SNAPSHOT_DIR", str(OBSERVER_HOME / "snapshots"))
)

LS4_DATA_DIR = Path(os.getenv("LS4_DATA_DIR", "/data/observer"))

LOGBOOK_URL = os.getenv(
    "LS4_LOGBOOK_URL",
    "https://docs.google.com/document/d/1TfwjvCbK3iwrGQz7A78CSYDjfwSEA4Grl423T3Ru5Ss/edit",
)

ENABLE_SCHEDULER_PAUSE = os.getenv("LS4_ENABLE_SCHEDULER_PAUSE", "false").lower() in {
    "1",
    "true",
    "yes",
}

MOSAIC_PREVIEW_DIR = OBSERVER_HOME / "sim" / "mosaics"
