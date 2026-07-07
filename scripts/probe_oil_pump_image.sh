#!/usr/bin/env bash
# Read-only probe for oil pump / manometer image sources on the mountain.
# Run as observer (or ls4) after SSH. Paste output back for GUI wiring.
set -u

echo "=== Oil pump image probe ==="
echo "User: $(whoami)  Host: $(hostname -s 2>/dev/null || hostname)"
echo

KENNETH="${LS4_KENNETH_DIR:-/home/ls4/kenneth}"
echo "--- 1. Image files the GUI already looks for ---"
echo "Directory: ${KENNETH}"
for pattern in '*oil*pump*.jpg' '*oil*pump*.png' '*manometer*.jpg' '*pressure*.jpg' 'TCScam*.jpg'; do
  echo "  pattern ${pattern}:"
  ls -lt ${KENNETH}/${pattern} 2>/dev/null | head -3 || echo "    (none)"
done
echo

echo "--- 2. Pressure scripts in kenneth ---"
for f in read_pressure.py record_pressure.sh vmonitor.py; do
  if [[ -f "${KENNETH}/${f}" ]]; then
    echo "FOUND ${KENNETH}/${f}"
    ls -la "${KENNETH}/${f}"
  else
    echo "missing ${KENNETH}/${f}"
  fi
done
echo

echo "--- 3. read_pressure.py header / help ---"
if [[ -f "${KENNETH}/read_pressure.py" ]]; then
  head -40 "${KENNETH}/read_pressure.py"
  echo "--- trying --help ---"
  python3 "${KENNETH}/read_pressure.py" --help 2>&1 | head -20 || true
fi
echo

echo "--- 4. record_pressure.sh ---"
if [[ -f "${KENNETH}/record_pressure.sh" ]]; then
  cat "${KENNETH}/record_pressure.sh"
fi
echo

echo "--- 5. util_log.jpg / util_log.pdf (quest pressure plot) ---"
for dir in "${KENNETH}" /home/ls4/status /home/observer/status /tmp; do
  echo "  ${dir}:"
  ls -lt "${dir}"/util_log.jpg "${dir}"/util_log.pdf 2>/dev/null | head -2 || echo "    (none)"
done
echo

echo "--- 6. Any recent jpg/png under kenneth ---"
find "${KENNETH}" -maxdepth 2 \( -name '*.jpg' -o -name '*.png' -o -name '*.jpeg' \) -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -15 | cut -d' ' -f2- || echo "(none or no permission)"
echo

echo "--- 7. gui_ls4 folder (if present) ---"
if [[ -d "${KENNETH}/gui_ls4" ]]; then
  ls -la "${KENNETH}/gui_ls4" | head -20
  grep -r -i -l 'oil\|pump\|manometer\|pressure\|webcam' "${KENNETH}/gui_ls4" 2>/dev/null | head -15 || true
else
  echo "(no gui_ls4/)"
fi
echo

echo "--- 8. Observer howto mentions ---"
for f in /home/observer/howtoobserve.txt /home/observer/howtoobserve /home/observer/README*; do
  [[ -e "$f" ]] || continue
  echo "FILE: $f"
  grep -i -n 'oil\|pump\|manometer\|pressure\|webcam' "$f" 2>/dev/null | head -20 || true
done
echo

echo "--- 9. GUI sim cache (if Flask ran in simulate mode) ---"
SIM="${LS4_SIM_WEBCAM_DIR:-/home/observer/sim/webcams}"
ls -la "${SIM}"/oil_pump* 2>/dev/null || echo "  (no ${SIM}/oil_pump*)"
echo

echo "--- 10. Can observer read kenneth? ---"
ls -la "${KENNETH}/pdu_api.py" 2>/dev/null || echo "cannot read ${KENNETH}"
echo
echo "Done. Paste this output to wire LS4_OIL_PUMP_IMAGE_DIR or a capture script."
