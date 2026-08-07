#!/usr/bin/env bash
#
# Whole-device UX performance capture for the X670 (mt6781) ROM.
#
# Collects, in one run:
#   - a perfetto trace (frame timeline, ftrace sched/freq/binder, cpu load, logcat)
#   - dumpsys gfxinfo summary + framestats for the foreground app
#   - dumpsys activity/window/SurfaceFlinger/cpuinfo/meminfo/power/thermal snapshots
#   - optional synchronized screenrecord (VIDEO=1)
#
# Usage:
#   ./capture.sh [duration_seconds] [tag]
#   VIDEO=1 ./capture.sh 90 myscenario
#   SIMULATE=scroll ./capture.sh 60    # auto-scroll (fling up/down) the whole time
#   SIMULATE=ux ./capture.sh 60        # scroll + recents + quick settings + home
#   EXTRA_PKGS="com.android.settings com.android.systemui" ./capture.sh
#
# SIMULATE= none|scroll|ux   (default: none -> drive the UI manually)
# Output: ./out/<tag>/
set -euo pipefail

DEBUG_UX_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="${DEBUG_UX_DIR}/out"
DEV_DIR=/data/local/tmp
REMOTE_CFG="${DEV_DIR}/ux_perfetto.pbtx"
REMOTE_TRACE="${DEV_DIR}/ux_trace.pb"
DURATION="${1:-60}"
TAG="${2:-$(date +%Y%m%d-%H%M%S)}"
VIDEO="${VIDEO:-0}"
EXTRA_PKGS="${EXTRA_PKGS:-}"
SIMULATE="${SIMULATE:-none}"

RUN_DIR="${OUT_DIR}/${TAG}"
mkdir -p "${RUN_DIR}"

command -v adb >/dev/null 2>&1 || { echo "FATAL: adb not found"; exit 1; }
adb wait-for-device

log() { printf '[capture] %s\n' "$*"; }

WM_SIZE="$(adb shell wm size 2>/dev/null | sed -n 's/Physical size: //p' | head -1)"
if [[ "${WM_SIZE}" =~ ^([0-9]+)x([0-9]+)$ ]]; then
  SCR_W="${BASH_REMATCH[1]}"
  SCR_H="${BASH_REMATCH[2]}"
else
  SCR_W=1080
  SCR_H=2400
fi

swipe() {
  adb shell input swipe "$1" "$2" "$3" "$4" "$5" >/dev/null 2>&1 || true
}

simulate_scroll() {
  local dur="$1" x=$((SCR_W / 2)) y0=$((SCR_H * 3 / 4)) y1=$((SCR_H / 4))
  local end=$((SECONDS + dur))
  while ((SECONDS < end)); do
    swipe "$x" "$y0" "$x" "$y1" 120
    swipe "$x" "$y1" "$x" "$y0" 120
  done
}

simulate_ux() {
  local dur="$1" x=$((SCR_W / 2)) y0=$((SCR_H * 3 / 4)) y1=$((SCR_H / 4))
  local end=$((SECONDS + dur))
  while ((SECONDS < end)); do
    swipe "$x" "$y0" "$x" "$y1" 120
    adb shell input keyevent KEYCODE_APP_SWITCH >/dev/null 2>&1 || true
    sleep 0.3
    adb shell input keyevent KEYCODE_APP_SWITCH >/dev/null 2>&1 || true
    swipe "$x" 20 "$x" "$((SCR_H - 200))" 150
    sleep 0.5
    adb shell input keyevent KEYCODE_HOME >/dev/null 2>&1 || true
    sleep 0.3
  done
}

log "tag=${TAG} duration=${DURATION}s video=${VIDEO} simulate=${SIMULATE} extra_pkgs='${EXTRA_PKGS}' screen=${SCR_W}x${SCR_H}"

log "[1/6] push perfetto config"
sed "s/__DURATION_MS__/$((DURATION * 1000))/" "${DEBUG_UX_DIR}/perfetto_config.pbtx" > "${RUN_DIR}/perfetto_config.pbtx"
adb push "${RUN_DIR}/perfetto_config.pbtx" "${REMOTE_CFG}" >/dev/null

log "[2/6] reset gfxinfo stats"
adb shell dumpsys gfxinfo reset >/dev/null 2>&1 || true

log "[3/6] start perfetto (${DURATION}s) in background"
adb shell "rm -f ${REMOTE_TRACE}; (nohup su -c 'perfetto --txt -c ${REMOTE_CFG} -o ${REMOTE_TRACE}' >/dev/null 2>&1 &)"
sleep 2

VIDEO_PID=
if [ "${VIDEO}" = "1" ]; then
  log "    starting screenrecord -> /sdcard/ux.mp4"
  adb shell "rm -f /sdcard/ux.mp4; screenrecord --time-limit ${DURATION} /sdcard/ux.mp4" >/dev/null 2>&1 &
  VIDEO_PID=$!
fi

case "${SIMULATE}" in
  scroll) log "=== SIMULATING SCROLL for ${DURATION}s ==="; simulate_scroll "${DURATION}" ;;
  ux)     log "=== SIMULATING UX (scroll/recents/QS) for ${DURATION}s ==="; simulate_ux "${DURATION}" ;;
  *)      log "=== REPRODUCE THE SLOWNESS NOW (${DURATION}s) ==="; sleep "${DURATION}" ;;
esac

log "[4/6] wait for perfetto to finish"
adb wait-for-device
for _ in $(seq 1 90); do
  if ! adb shell "pgrep -x perfetto >/dev/null" 2>/dev/null; then
    break
  fi
  sleep 1
done

if [ -n "${VIDEO_PID}" ]; then
  wait "${VIDEO_PID}" 2>/dev/null || true
fi

log "[5/6] collect dumpsys snapshots"
adb shell dumpsys activity top        > "${RUN_DIR}/activity_top.txt"        || true
adb shell dumpsys activity activities > "${RUN_DIR}/activities.txt"          || true
adb shell dumpsys window              > "${RUN_DIR}/window.txt"              || true
adb shell dumpsys gfxinfo             > "${RUN_DIR}/gfxinfo_summary.txt"     || true
adb shell dumpsys SurfaceFlinger      > "${RUN_DIR}/surfaceflinger.txt"      || true
adb shell dumpsys cpuinfo             > "${RUN_DIR}/cpuinfo.txt" 2>/dev/null || true
adb shell dumpsys meminfo             > "${RUN_DIR}/meminfo.txt"             || true
adb shell dumpsys power               > "${RUN_DIR}/power.txt"               || true
adb shell dumpsys thermalservice      > "${RUN_DIR}/thermal.txt"             || true

FG_PKG="$(adb shell dumpsys activity activities 2>/dev/null | sed -n 's/.*ActivityRecord{[^}]* \([a-zA-Z0-9._]*\)\/[^ ]*.*/\1/p' | head -1)"
if [ -n "${FG_PKG}" ]; then
  log "    foreground pkg=${FG_PKG}"
  adb shell dumpsys gfxinfo "${FG_PKG}" framestats > "${RUN_DIR}/framestats_${FG_PKG}.txt" || true
  adb shell dumpsys gfxinfo "${FG_PKG}"             > "${RUN_DIR}/gfxinfo_${FG_PKG}.txt"     || true
else
  log "    WARN: could not resolve foreground package from activities dump"
fi
for p in ${EXTRA_PKGS}; do
  log "    extra pkg=${p}"
  adb shell dumpsys gfxinfo "${p}" framestats > "${RUN_DIR}/framestats_${p}.txt" || true
  adb shell dumpsys gfxinfo "${p}"             > "${RUN_DIR}/gfxinfo_${p}.txt"     || true
done

log "[6/6] pull artifacts"
adb shell "su -c 'chmod 644 ${REMOTE_TRACE}' 2>/dev/null" || true
adb pull "${REMOTE_TRACE}" "${RUN_DIR}/trace.perfetto-trace" >/dev/null 2>&1 || log "WARN: trace pull failed (trace may not have completed)"
if [ "${VIDEO}" = "1" ]; then
  adb pull /sdcard/ux.mp4 "${RUN_DIR}/ux.mp4" >/dev/null 2>&1 || log "WARN: video pull failed"
fi

log "cleanup device-side files"
adb shell "rm -f ${REMOTE_TRACE} /sdcard/ux.mp4" || true

log "DONE -> ${RUN_DIR}"
ls -lh "${RUN_DIR}" | sed 's/^/  /'
