#!/usr/bin/env bash
# Run on the mountain as `observer` to discover paths for ls4_gui .env settings.
# Usage: bash scripts/discover_mountain_paths.sh

set -u

echo "=== LS4 GUI mountain path discovery ==="
echo "User: $(whoami)  Host: $(hostname -s 2>/dev/null || hostname)"
echo

echo "--- Observer environment ---"
echo "LS4_ROOT=${LS4_ROOT:-unset}"
echo "OBSERVER_HOME=${HOME}"
ls -la "${HOME}/.tcshrc" "${HOME}/bin/obs_control_script" "${HOME}/bin/start_questctl" "${HOME}/bin/opendome_raw" 2>/dev/null || true
which mos 2>/dev/null || echo "mos: not in PATH"
echo

echo "--- Data / exposures (/data/observer) ---"
DATA_DIR="${LS4_DATA_DIR:-/data/observer}"
echo "LS4_DATA_DIR candidate: ${DATA_DIR}"
if [[ -d "${DATA_DIR}" ]]; then
  echo "Top-level night folders:"
  ls -lt "${DATA_DIR}" 2>/dev/null | head -8
  latest="$(ls -1 "${DATA_DIR}" 2>/dev/null | sort | tail -1)"
  if [[ -n "${latest}" && -d "${DATA_DIR}/${latest}" ]]; then
    echo
    echo "Sample files in newest folder ${latest}:"
    ls -lt "${DATA_DIR}/${latest}" 2>/dev/null | head -12
    echo
    echo "Existing mosaics in ${latest}:"
    ls -lt "${DATA_DIR}/${latest}"/mos_* 2>/dev/null | head -5 || echo "(none found)"
    echo
    echo "Example exposure prefix (first filename, strip after chip id if present):"
    sample="$(ls -1 "${DATA_DIR}/${latest}" 2>/dev/null | grep -v '^mos_' | head -1)"
    echo "  sample file: ${sample:-none}"
  fi
else
  echo "Directory not found."
fi
echo

echo "--- Kenneth tools (/home/ls4/kenneth) ---"
KENNETH="/home/ls4/kenneth"
ls -la "${KENNETH}/pdu_api.py" 2>/dev/null || echo "pdu_api.py: missing"
echo "TCS images:"
ls -lt "${KENNETH}"/TCScam*.jpg 2>/dev/null | head -3 || echo "(none)"
echo "Oil pump / pressure images:"
ls -lt "${KENNETH}"/*oil* "${KENNETH}"/*pressure* "${KENNETH}"/*manometer* 2>/dev/null | head -5 || echo "(none)"
ls -la "${KENNETH}/read_pressure.py" "${KENNETH}/record_pressure.sh" 2>/dev/null || true
echo "gui_ls4 (if present):"
ls -la "${KENNETH}/gui_ls4" 2>/dev/null | head -10 || echo "(none)"
echo

echo "--- Flux meter snapshots ---"
for dir in /home/ls4/snapshots "${HOME}/snapshots" /data/observer/snapshots; do
  echo "Checking ${dir}:"
  ls -lt "${dir}"/*_cam3.jpg 2>/dev/null | head -3 || echo "  (no *_cam3.jpg)"
done
echo

echo "--- Suggested .env lines (edit after reviewing output above) ---"
cat <<EOF
LS4_OBSERVER_HOME=${HOME}
LS4_KENNETH_DIR=${KENNETH}
LS4_DATA_DIR=${DATA_DIR}
LS4_FLUX_METER_SNAPSHOT_DIR=/home/ls4/snapshots
LS4_TCS_WEBCAM_DIR=${KENNETH}
LS4_OIL_PUMP_IMAGE_DIR=${KENNETH}
LS4_GUI_SIMULATE=false
EOF

echo
echo "For real start_questctl / opendome / mosaic tests, set LS4_GUI_SIMULATE=false."
echo "For FITS mosaic previews in the browser, install: pip install astropy pillow"
