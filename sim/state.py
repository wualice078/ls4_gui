"""Persistent simulated hardware state for the VM mountain replica."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any

STATE_VERSION = 1

try:
    from config import OPERATOR_PDU_OUTLETS
except ImportError:  # standalone scripts
    OPERATOR_PDU_OUTLETS = (1, 2, 3, 4, 8)


class SimState:
    def __init__(self, state_file: Path, dome_transition_seconds: int = 90) -> None:
        self.state_file = state_file
        self.dome_transition_seconds = dome_transition_seconds
        self._lock = threading.Lock()
        self._memory_state: dict[str, Any] | None = None
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            if not self.state_file.exists():
                self._write(self._default_state())
        except OSError:
            self._memory_state = self._default_state()

    def _default_state(self) -> dict[str, Any]:
        return {
            "version": STATE_VERSION,
            "dome": "closed",
            "dome_target": "closed",
            "dome_transition_ends_at": None,
            "scheduler": "stopped",
            "telescope_services": "stopped",
            "pdu_outlets": {str(i): False for i in range(1, 9)},
            "webcams": {
                "oil_pump": {"pump_on": True, "updated_at": None},
                "tcs": {"servos_up": True, "updated_at": None},
            },
            "questctl_running": False,
        }

    def _read(self) -> dict[str, Any]:
        if self._memory_state is not None:
            return dict(self._memory_state)
        try:
            return json.loads(self.state_file.read_text())
        except (OSError, json.JSONDecodeError):
            return self._default_state()

    def _write(self, state: dict[str, Any]) -> None:
        try:
            self.state_file.write_text(json.dumps(state, indent=2, sort_keys=True))
            self._memory_state = None
        except OSError:
            self._memory_state = dict(state)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            state = self._refresh_dome(self._read())
            self._write(state)
            return {
                "dome": state["dome"],
                "scheduler": state["scheduler"],
                "telescope_services": state["telescope_services"],
                "pdu_outlets": {
                    outlet: "on" if powered else "off"
                    for outlet, powered in state["pdu_outlets"].items()
                },
                "questctl_running": state["questctl_running"],
            }

    def _refresh_dome(self, state: dict[str, Any]) -> dict[str, Any]:
        ends_at = state.get("dome_transition_ends_at")
        if ends_at is None:
            return state
        if time.time() >= ends_at:
            state["dome"] = state["dome_target"]
            state["dome_transition_ends_at"] = None
        return state

    def dome_status(self) -> str:
        with self._lock:
            state = self._refresh_dome(self._read())
            self._write(state)
            dome = state["dome"]
            if state.get("dome_transition_ends_at") is not None:
                if state["dome_target"] == "open":
                    return "opening"
                if state["dome_target"] == "closed":
                    return "closing"
            return dome

    def request_dome(self, target: str) -> tuple[bool, str]:
        if target not in {"open", "closed"}:
            return False, f"Unknown dome target: {target}"

        with self._lock:
            state = self._refresh_dome(self._read())
            current = state["dome"]
            if state.get("dome_transition_ends_at") is not None:
                return False, f"Dome is already {self.dome_status()}."
            if current == target:
                return True, f"Dome is already {target}."

            state["dome_target"] = target
            state["dome_transition_ends_at"] = time.time() + self.dome_transition_seconds
            if target == "open":
                state["dome"] = "opening"
                message = (
                    f"Dome opening (simulated, ~{self.dome_transition_seconds}s)."
                )
            else:
                state["dome"] = "closing"
                message = (
                    f"Dome closing (simulated, ~{self.dome_transition_seconds}s)."
                )
            self._write(state)
            return True, message

    def set_scheduler(self, state_name: str) -> None:
        with self._lock:
            state = self._read()
            state["scheduler"] = state_name
            self._write(state)

    def set_telescope_services(self, state_name: str) -> None:
        with self._lock:
            state = self._read()
            state["telescope_services"] = state_name
            state["questctl_running"] = state_name == "running"
            self._write(state)

    def set_pdu_outlet(self, outlet: int, powered: bool) -> tuple[bool, str]:
        if outlet not in OPERATOR_PDU_OUTLETS:
            return False, f"Outlet {outlet} is not operator-controllable."

        with self._lock:
            state = self._read()
            key = str(outlet)
            if key not in state["pdu_outlets"]:
                return False, f"Invalid PDU outlet: {outlet}"
            state["pdu_outlets"][key] = powered
            self._write(state)
            label = "on" if powered else "off"
            return True, f"PDU outlet {outlet} turned {label} (simulated)."

    def pdu_outlets(self) -> dict[str, bool]:
        with self._lock:
            return dict(self._read()["pdu_outlets"])

    def mark_webcam_refresh(self, camera: str) -> None:
        with self._lock:
            state = self._read()
            if camera in state["webcams"]:
                state["webcams"][camera]["updated_at"] = time.time()
                self._write(state)
