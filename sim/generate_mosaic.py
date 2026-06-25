#!/usr/bin/env python3
"""Generate a simulated focal-plane mosaic preview for VM testing."""

from __future__ import annotations

import argparse
import time
from pathlib import Path

OBSERVER_HOME = Path(__file__).resolve().parents[2] / "observer-home"
MOSAIC_DIR = OBSERVER_HOME / "sim" / "mosaics"


def _svg(prefix: str) -> str:
    stamp = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="960" height="540" viewBox="0 0 960 540">
  <rect width="960" height="540" fill="#020617"/>
  <text x="480" y="70" fill="#e2e8f0" font-family="sans-serif" font-size="28" text-anchor="middle">Simulated LS4 Mosaic</text>
  <text x="480" y="110" fill="#94a3b8" font-family="sans-serif" font-size="18" text-anchor="middle">prefix: {prefix}</text>
  <g transform="translate(80,140)">
    <rect x="0" y="0" width="380" height="170" fill="#111827" stroke="#334155"/>
    <rect x="400" y="0" width="380" height="170" fill="#111827" stroke="#334155"/>
    <rect x="0" y="190" width="380" height="170" fill="#111827" stroke="#334155"/>
    <rect x="400" y="190" width="380" height="170" fill="#111827" stroke="#334155"/>
    <text x="190" y="95" fill="#64748b" font-family="sans-serif" font-size="16" text-anchor="middle">NW</text>
    <text x="590" y="95" fill="#64748b" font-family="sans-serif" font-size="16" text-anchor="middle">NE</text>
    <text x="190" y="285" fill="#64748b" font-family="sans-serif" font-size="16" text-anchor="middle">SW</text>
    <text x="590" y="285" fill="#64748b" font-family="sans-serif" font-size="16" text-anchor="middle">SE</text>
  </g>
  <text x="480" y="520" fill="#64748b" font-family="sans-serif" font-size="14" text-anchor="middle">{stamp}</text>
</svg>"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("prefix", help="Exposure prefix, e.g. 20260213010625sC")
    parser.add_argument("-o", "--output")
    args = parser.parse_args()

    MOSAIC_DIR.mkdir(parents=True, exist_ok=True)
    output = Path(args.output) if args.output else MOSAIC_DIR / "mosaic_latest.svg"
    output.write_text(_svg(args.prefix))
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
