#!/usr/bin/env bash
# X670 SF/hwui prop benchmark harness.
# Usage:
#   sf_prop_bench.sh <label>                # 1 run
#   WARMUP=1 sf_prop_bench.sh warmup        # discard
#
# Pre-flight (must be done once before sweep):
#   adb shell dumpsys battery unplug
#   adb shell cmd power set-mode 1
#   adb shell setprop debug.sf.enable_adpf_cpu_hint true
#   adb shell dumpsys power | grep "saver is"   # should show ON
#
# The script drives a fixed input sequence (QS + Settings scroll) and
# parses `dumpsys gfxinfo com.android.systemui` for jank/p99/vsync-miss.
# Pair with `summarize.py rounds/results.txt` to drop cold runs and
# report warm-only medians.
#
# See docs/session-2026-08-30-prop-sweep.md for full methodology.

set -e

LABEL="${1:-unnamed}"
OUT="${BENCH_OUT:-/tmp/sf_prop_bench/rounds}"
mkdir -p "$OUT"
[ ! -f "$OUT/results.txt" ] && > "$OUT/results.txt"

WORKLOAD() {
  adb shell input keyevent KEYCODE_WAKEUP >/dev/null
  adb shell wm dismiss-keyguard 2>/dev/null
  sleep 0.5
  adb shell dumpsys gfxinfo com.android.systemui reset >/dev/null
  sleep 0.3
  adb shell input swipe 540 50 540 1500 200 >/dev/null
  sleep 0.4
  adb shell input swipe 540 50 540 1500 200 >/dev/null
  sleep 0.5
  for i in 1 2 3; do
    adb shell input tap 200 800 >/dev/null; sleep 0.2
    adb shell input tap 400 800 >/dev/null; sleep 0.2
    adb shell input tap 600 800 >/dev/null; sleep 0.2
  done
  for i in 1 2 3 4 5; do
    adb shell input swipe 540 1200 540 400 200 >/dev/null; sleep 0.2
    adb shell input swipe 540 400 540 1200 200 >/dev/null; sleep 0.2
  done
  adb shell input keyevent KEYCODE_BACK >/dev/null
  sleep 0.3
  adb shell input keyevent KEYCODE_HOME >/dev/null
  sleep 0.3
  adb shell am start -n com.android.settings/.Settings >/dev/null
  sleep 1.5
  for i in 1 2 3 4; do
    adb shell input swipe 540 1800 540 400 200 >/dev/null; sleep 0.2
  done
  sleep 0.8
}

if [ "${WARMUP:-0}" = "1" ]; then
  WORKLOAD
  exit 0
fi

WORKLOAD

INFO=$(adb shell dumpsys gfxinfo com.android.systemui 2>&1)
TOTAL=$(echo "$INFO" | grep -E "Total frames rendered:" | grep -oE "[0-9]+" | head -1)
JANK=$(echo "$INFO" | grep -E "Janky frames:" | grep -oE "[0-9.]+%" | head -1)
P99=$(echo "$INFO" | grep -E "99th percentile:" | awk '{print $3}' | tr -d 'ms')
MISS=$(echo "$INFO" | grep -E "Number Missed Vsync:" | grep -oE "[0-9]+")
GPU99=$(echo "$INFO" | grep -E "99th gpu percentile:" | awk '{print $5}' | tr -d 'ms')

SF=$(adb shell dumpsys SurfaceFlinger 2>&1)
SFMISS=$(echo "$SF" | grep -E "Total missed frame count:" | grep -oE "[0-9]+" | head -1)
ADPF=$(echo "$SF" | grep -oE "use_adpf_cpu_hint: (true|false)" | head -1)

LINE="[$LABEL] frames=$TOTAL jank=$JANK p99=${P99}ms vsync_miss=$MISS gpu99=${GPU99}ms sf_miss=$SFMISS $ADPF"
echo "$LINE"
echo "$LINE" >> "$OUT/results.txt"
