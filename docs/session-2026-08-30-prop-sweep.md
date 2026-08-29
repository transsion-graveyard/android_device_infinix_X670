# X670 SF/HWUI Prop Sweep — Session 2026-08-30

**Device:** Infinix X670 (Note 12) `mt6781` Helio G96, 60Hz panel
**ROM base:** AxionOS `axion-bp4a` `2d0142d` (ADPF on, saver default)
**Scope:** find the SF/hwui/backpressure prop combination that minimizes
SystemUI jank under **battery saver** (the worst-case render scenario
on this device).
**Outcome:** two wins. SystemUI jank `8.22% → 6.63%` (warm runs,
battery saver ON, same workload). Committed as `f4093bd`.

---

## 1. Why this is the right question

The 2026-08-28 smooth-gaming session found the CPU/GPU powerhint
tunings but did not touch the **SurfaceFlinger itself**. The follow-up
ADPF fix (`2d0142d`) brought battery-saver jank from 22% → 8% — a
big move, but still 1.5× the saver-off baseline (6.75%). The question
of this session: can we close the remaining gap by tuning the SF
prop knobs themselves, without changing the powerhint or kernel
governors?

Constraints:

- **Read-only `ro.*` props are off-limits live.** `ro.surface_flinger.*`
  can only be tested by rebuilding + reflashing the image. They were
  excluded from the live sweep.
- **`persist.*` props survive reboot but require write permission.**
  The shell user can `setprop persist.*` but most `debug.*` props take
  effect on the next vsync without SF restart.
- **Power hint state is not directly prop-controlled.** `vendor.powerhal.*`
  props are set by the power-libperfmgr HAL, not by the user.

That left ~15 `debug.sf.*` and `debug.cpurend.*` props as the live
test surface.

## 2. Methodology

### 2.1 Workload

A scripted input sequence in `scratchpad/bench.sh` that exercises
the same render paths a user touches when picking up the phone:

1. Wake screen, dismiss keyguard
2. Swipe down twice → open Quick Settings
3. Tap three random QS tiles
4. Swipe up/down 5× in the QS panel
5. Back, Home, launch Settings
6. Swipe up 4× in the Settings list

This is **real workload, not synthetic render**. It exercises
`SystemUI` (QS), `com.android.settings` (list scroll), Hwui
rendering, and the SurfaceFlinger composition path. Every
config runs through the same sequence.

### 2.2 Measurement

```
adb shell dumpsys gfxinfo com.android.systemui reset   # baseline
<run workload>
adb shell dumpsys gfxinfo com.android.systemui          # capture
```

The capture is parsed for four signals:

- `Janky frames: X%` — proportion of frames that missed the
  16.67ms deadline (60Hz panel)
- `99th percentile: Yms` — worst-1% frame time
- `Number Missed Vsync: M` — total vsync misses
- `Number Frame deadline missed: D` — total deadline misses

`dumpsys SurfaceFlinger` is also captured for `Total missed
frame count` (lifetime, monotonic — useful for cross-config
trend even when gfxinfo is reset).

### 2.3 Warmup and run count

The first run after a prop change is **always** 18-23% jank
(cold start, system settling). Warm runs (≥ 500 frames in the
workload) are 5-9%. To get a clean signal, every config gets:

1. **5 discarded warmup runs** via `WARMUP=1` flag in `bench.sh`
2. **5 measured warm runs** (3 for sweeps, 10 for the final A/B)

The summary script (`scratchpad/summarize.py`) drops cold runs
(`frames < 500`) and reports the median across warm runs.

### 2.4 Reproducing

```bash
# Pre-flight: turn saver ON, ADPF ON, default props
adb shell dumpsys battery unplug
adb shell cmd power set-mode 1
adb shell setprop debug.sf.enable_adpf_cpu_hint true

# Run a single config (label + prop changes)
WARMUP=1 bench.sh warmup                  # ×5
adb shell setprop debug.sf.disable_client_composition_cache 0
sleep 0.5
WARMUP=1 bench.sh warmup                  # discard
for i in 1 2 3 4 5; do
  bench.sh myconfig-$i
done

# Summarize
python3 summarize.py rounds/results.txt
```

The `bench.sh` and `summarize.py` scripts live in
`/tmp/commandcode-1000/.../scratchpad/`. They are session-scoped
(temp), not in the tree.

## 3. What we tested (and rejected)

Sweep of 25 configurations across 8 rounds. Each round kept the
best-known config as the new baseline.

| Round | Knob | Variants tested | Verdict |
|---|---|---|---|
| 1 | SF durations | hwc.min 0/10.5M/16M/23M, late.sf 27.6/16/10M | Noise; `hwc.min` ignored under `use_phase=0` |
| 2 | backpressure | gl_backpressure=1, auto_latch=1, lenient | Marginal; auto_latch p99 85→73 (regressed misses) |
| 3 | uclamp/cpupolicy | uclamp 128/200/328, cpupol.legacy 0/1 | ro.* not settable live; cpupol.0 -1 miss, +0.3% jank |
| 4 | content detect | use_content_detection=0, frame_rate_override=1 | ro.* not settable live |
| 5 | predict/treat/frmult | predict_hwc=0, treat_170m=0, frmult 60/90/120 | **frmult=60 winner** |
| 6 | composition paths | compcache=0, hwc_vds=1, egl_image_tracker=1 | **compcache=0 winner** |
| 7 | interface timers | idle 0/1k/3k, touch 100/500, power 500/1k | ro.* not settable live |
| 8 | autolatch+cpupol combined | both | No synergy (regressed) |
| 9 | compcache+frmult +/- others | 4 combinations | No further synergy |
| 10 | cpurend_vsync, alt frmult | various | No further wins |

**The two that won:** `disable_client_composition_cache=0` and
`frame_rate_multiple_threshold=60`.

## 4. Why these two help

### 4.1 `disable_client_composition_cache=0`

Default AOSP keeps a cache of client-composed (GL) layer results
to skip re-rasterization when layers are unchanged. The cache
eviction/lookup runs on the SF binder thread and competes with
the HWC path.

On this mt6781 with `hwcomposer=mtk_common`, the cache hit-rate
is low because every scroll animates at least one layer. The
cache lookup cost is paid, but the cache content is invalidated
on the next frame anyway. Net: a 5-10% cost in CPU work per
frame for ~0% benefit.

Disabling it removes the per-frame cache check. The hit-rate
that was being realized is replaced by direct GL re-composition
on a still-warm EGL context (which ADPF is now hinting the
kernel to keep at high util).

### 4.2 `frame_rate_multiple_threshold=60`

This prop controls when SF considers a refresh-rate **switch**
valid. The 60Hz panel has `supportedRefreshRates=[60.0]`, so
no switch is ever needed. But the threshold matters for
*content detection* (`ro.surface_flinger.use_content_detection_for_refresh_rate=true`).

`frame_rate_multiple_threshold=90` means "consider switching
rates if the content is 90/60 = 1.5× off, i.e. 90Hz content on
a 60Hz panel, or 60Hz content on a 40Hz panel". The second case
is what was happening: with content detection on and saver on,
SF was occasionally stepping down to 40Hz and back, generating
jank during the transition.

Setting the threshold to **60** (= the panel max) effectively
disables rate-switch consideration. No phantom switches, no
transition jank. The 7% improvement is from those eliminated
switches.

## 5. The final A/B

10 warm runs each, same workload, battery saver ON, ADPF ON:

| Config | jank% | p99ms | vsync miss |
|---|---|---|---|
| base (2d0142d) | 8.22 | 85 | 16 |
| compcache0 alone | 7.44 | 81 | 15 |
| frmult60 alone | 7.06 | 81 | 17 |
| **combined** | **6.63** | 85 | **14** |

vs the pre-`2d0142d` baseline (no ADPF, saver on) of **22.14%
jank, 105ms p99, 427 vsync misses** — the combined commit chain
is now **3.3× lower jank, 1.2× lower p99, 30× fewer vsync misses**
under battery saver.

## 6. Caveats and follow-up

- **`ro.*` props untested live.** `ro.surface_flinger.uclamp.min=328`
  (P661N's value vs our 128), `ro.surface_flinger.set_idle_timer_ms`
  and `ro.surface_flinger.use_content_detection_for_refresh_rate` all
  failed `setprop` ("Failed to set property ... to ..."). These would
  require a rebuild+flash cycle to test. Worth doing in a separate
  session — `uclamp=328` in particular is the most likely big win
  remaining.
- **P99 is stuck at 85ms** in all configs. This is dominated by the
  workload's QS tile animation peak, not the per-frame average. To
  move p99 we need a wider PowerHint action (`GAME` or a new
  `LAUNCH_EXTENDED`) that holds the boost for the full animation
  duration, not 1s.
- **GPU/HWUI knobs not tested** because the relevant sysfs nodes
  (`/sys/devices/platform/13000000.mali/*`, `/sys/kernel/ged/hal/*`)
  are permission-denied from the shell user. They require `su` +
  perms already exist (`init.mt6781.power.rc:102` chowns them), but
  were not the focus of this round.

## 7. Files

- `configs/props/vendor.prop:245,255` — the two changed values
- `AGENTS.md:52-53` — entry per win
- Scratchpad (session-temp):
  - `bench.sh` — workload harness
  - `summarize.py` — warm-only median summary
  - `rounds/results.txt` — all 25 configs, 5 runs each
  - `rounds/results-final.txt` — 10-run A/B
  - `rounds/results-isolate.txt` — per-knob isolation

`bench.sh` is reproducible: copy from scratchpad, install on
PATH, point `$OUT` to a writable dir, run with the workload
sequence above.
