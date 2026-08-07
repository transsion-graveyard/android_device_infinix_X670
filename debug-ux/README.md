# debug-ux: whole-device UX performance capture & analysis (X670 / mt6781)

Tooling for diagnosing **slow-but-smooth** UX (elevated frame times without visible
jank/drops) on the Infinix X670 ROM. Requires a connected, ideally rooted
(userdebug/magisk) device with `perfetto` (SDK 30+; this device: SDK 36, perfetto v51).

## Quick start

```bash
# capture 60s of trace + dumpsys while you reproduce the slowness
./debug-ux/capture.sh 60

# hands-free: auto-scroll for the whole window (scroll up/down flings)
SIMULATE=scroll ./debug-ux/capture.sh 60

# hands-free: scroll + recents + quick settings + home, looped
SIMULATE=ux ./debug-ux/capture.sh 60

# also record video synchronized with the trace
VIDEO=1 SIMULATE=scroll ./debug-ux/capture.sh 90 recents_scroll

# also capture framestats for specific extra packages
EXTRA_PKGS="com.android.systemui" ./debug-ux/capture.sh 60
```

While `capture.sh` prints `=== REPRODUCE THE SLOWNESS NOW ===`, drive the UI
(scroll, open recents, pull QS, etc.). Everything lands in `debug-ux/out/<tag>/`.

## Artifacts

| File | What it tells you |
|---|---|
| `trace.perfetto-trace` | The main event. Open in https://ui.perfetto.dev |
| `ux.mp4` | Screen recording (only with `VIDEO=1`), sync with trace timeline |
| `framestats_<pkg>.txt` | Per-frame timestamps for the foreground app |
| `gfxinfo_summary.txt` | Jank %, percentiles, missed-vsync / slow-ui-thread counts |
| `activity_top.txt`, `activities.txt` | What was on screen / current task |
| `window.txt` | Window layout, focus, input dispatching |
| `surfaceflinger.txt` | Composition / buffer lifecycle |
| `cpuinfo.txt`, `meminfo.txt`, `power.txt`, `thermal.txt` | Load, pressure, power state, throttling |

## Analysis

```bash
# frame-time distribution + where time goes (input/anim/traversals/hwui)
python3 debug-ux/analyze_gfxinfo.py debug-ux/out/TAG/framestats_<pkg>.txt

# jank % / percentiles across all apps
python3 debug-ux/analyze_gfxinfo.py debug-ux/out/TAG/gfxinfo_summary.txt --summary
```

For the trace: open `trace.perfetto-trace` in https://ui.perfetto.dev, then:

1. **SurfaceFlinger → DisplayCompositor / frame timeline** — look for `FrameMissed`
   / `AppDeadlineMissed` / frames crossing the vsync budget. This is the ground
   truth for *which frame was late* and *by how much*.
2. **App main thread + RenderThread tracks** — do the long slices live on the main
   thread (input/traversals/draw) or on RenderThread (`hwui`)? Long main-thread
   slices → app-side work; long RenderThread → shader/GPU/texture upload.
3. **cpu_frequency / cpu_idle / Thermal (HAL)** — during the slow window, are big
   cores clamped low (throttling) or bouncing? Frequency collapse during the same
   window = thermal/power policy, not app code.
4. **Binder tracks** — long `binder_transaction` under the main thread = system
   service calls (e.g. SurfaceFlinger, system_server) blocking the frame.

## Decision tree

| Signature in trace / gfxinfo | Likely culprit | Where to look |
|---|---|---|
| Long main-thread slices, slow traversals/draw | App layout/measure/draw cost | perfetto app track |
| Long RenderThread / `hwui` slices | Shaders, texture upload, GPU driver | perfetto RenderThread |
| `FrameMissed` with short app slices | SurfaceFlinger composition / buffer latency | DisplayCompositor track |
| cpu_frequency pinned low during slow window | Thermal throttle or governor policy | `thermal.txt`, freq track |
| Long binder calls on main thread | System service contention (system_server, SF) | binder tracks, `window.txt` |
| Slow bitmap uploads / missing vsync | Buffer queue backpressure | `gfxinfo_summary.txt`, `surfaceflinger.txt` |

## Notes

- gfxinfo stats are **reset** at capture start, so the dump reflects only the
  recorded window.
- On this ROM `dumpsys gfxinfo <pkg> framestats` does **not** emit per-frame
  `FrameDuration` rows (verified: it only reprints per-window summaries), and
  there is no `cpuinfo` system service. Per-frame timing therefore comes from
  the perfetto frame timeline; `gfxinfo_summary.txt` supplies jank %, percentiles,
  histograms, missed-vsync and slow-ui-thread counts.
- Keep animation scales at defaults — disabling them hides window-animation cost,
  which is part of real UX.
- `perfetto` needs ftrace access: works via `adb shell` on userdebug/eng; if you
  get permission errors, prefix the perfetto invocation with `su -c` (rooted).
- Traces can be large (256 MB buffer). Delete `debug-ux/out/*` when done.
