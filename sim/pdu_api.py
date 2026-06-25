#!/usr/bin/env python3
"""Simulated PDU API matching mountain usage: -p <outlet> power on, -o <outlet> off."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

STATE_FILE = Path(__file__).resolve().parents[2] / "observer-home" / "sim" / "state.json"
OPERATOR_PDU_OUTLETS = (1, 2, 3, 4, 8)


def main() -> int:
    parser = argparse.ArgumentParser(description="Simulated LS4 PDU control")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-p", "--power-on", type=int, metavar="OUTLET")
    group.add_argument("-o", "--power-off", type=int, metavar="OUTLET")
    parser.add_argument("--status", action="store_true", help="Print outlet states")
    args = parser.parse_args()

    state_file = STATE_FILE
    state_file.parent.mkdir(parents=True, exist_ok=True)
    if state_file.exists():
        state = json.loads(state_file.read_text())
    else:
        state = {"pdu_outlets": {str(i): False for i in range(1, 9)}}

    outlets = state.setdefault("pdu_outlets", {str(i): False for i in range(1, 9)})

    if args.status:
        for outlet in sorted(outlets, key=int):
            label = "ON" if outlets[outlet] else "OFF"
            print(f"outlet {outlet}: {label}")
        return 0

    if args.power_on is not None:
        if args.power_on not in OPERATOR_PDU_OUTLETS:
            print(
                f"ERROR: outlet {args.power_on} is not operator-controllable",
                file=sys.stderr,
            )
            return 1
        outlet = str(args.power_on)
        if outlet not in outlets:
            print(f"ERROR: invalid outlet {args.power_on}", file=sys.stderr)
            return 1
        outlets[outlet] = True
        action = "ON"
        chosen = args.power_on
    else:
        if args.power_off not in OPERATOR_PDU_OUTLETS:
            print(
                f"ERROR: outlet {args.power_off} is not operator-controllable",
                file=sys.stderr,
            )
            return 1
        outlet = str(args.power_off)
        if outlet not in outlets:
            print(f"ERROR: invalid outlet {args.power_off}", file=sys.stderr)
            return 1
        outlets[outlet] = False
        action = "OFF"
        chosen = args.power_off

    state["pdu_outlets"] = outlets
    state_file.write_text(json.dumps(state, indent=2, sort_keys=True))
    print(f"PDU outlet {chosen} -> {action} (simulated)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
