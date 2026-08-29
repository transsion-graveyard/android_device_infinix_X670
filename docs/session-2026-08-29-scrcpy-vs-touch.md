# Scrcpy vs touch stutter — SurfaceFlinger and input path — Session 2026-08-29

**Device:** Infinix X670 (Note 12) `mt6781` Helio G96, 60 Hz
`overlay/FrameworksResTarget/res/values/config.xml:381`
**ROM base:** AxionOS `axion-bp4a` (`device/infinix/X670:1` + `X670-kernel` +
`vendor/infinix/X670`)
**Power HAL:** `android.hardware.power-service.pixel-libperfmgr`
(`device.mk:322`) via `power-libperfmgr` (`hardware/google/pixel:1`)
**Tools:** `adb` `ASALE37681000041` `Enforcing` `debug-ux/capture.sh:1`
`debug-ux/perfetto_config.pbtx:1` `trace.perfetto-trace`

---

## 1. What you see and why it matters

You report scrolling is smooth over `scrcpy` but stutters on the physical
touchscreen. `scrcpy` injects via `InputManager` at the framework level, not
through the kernel touch driver. That path bypasses `mtk-tpd` `/dev/input/event3`
`dumpsys input:156` `TOUCH_MT`, `tchbst` `/proc/perfmgr/tchbst/user/usrtch:15`,
and part of `InputFlinger`. Physical goes `FTS driver` → `dmesg FTS touch down`
→ `/dev/input/event3` → `InputReader` `TouchInputMapper DIRECT` → `InputDispatcher`
→ app + `PowerHAL INTERACTION` + `tchbst`. Your goal is to decide if the stall
is in the input path or in `SurfaceFlinger/HWC`.

---

## 2. How to tell input vs composition apart

Collect the same set both ways and compare.

### 2.1 Perfetto system trace

`debug-ux/perfetto_config.pbtx:1` already packs `linux.ftrace`
`sched_switch/waking/cpu_frequency/irq/binder`, `track_event gfx/view`,
`android.surfaceflinger.frametimeline:75`, `process_stats`, `sys_stats`. Do not use
legacy `atrace_categories`.

```bash
# inject (scrcpy-like, bypasses driver)
SIMULATE=scroll bash debug-ux/capture.sh 15 inject-scroll
# physical (you scroll 15 s with finger)
bash debug-ux/capture.sh 15 physical-touch
# open both trace.perfetto-trace in https://ui.perfetto.dev
```

Look at `VSYNC` alignment, `FrameTimeline` jank, `inputevent` intervals,
`cpu_frequency`, `irq_handler_entry`.

### 2.2 Winscope / FrameTimeline

Add to `perfetto_config.pbtx:1` when needed:

```
data_sources { config { name: "android.surfaceflinger.layers" } }
data_sources { config { name: "android.surfaceflinger.transactions" } }
data_sources { config { name: "android.input.inputevent" } }
```

`adb shell dumpsys SurfaceFlinger --latency <surface>` and
`dumpsys SurfaceFlinger` `HWC missed` vs `GPU missed` tell you if composition
fell back to GPU.

### 2.3 Quick checks

```bash
adb shell getprop | grep -E "surface_flinger|debug.sf|vendor.powerhal"
adb shell dumpsys SurfaceFlinger | grep -E "phase|duration|HWC min|missed"
adb shell dumpsys thermalservice
adb shell cat /sys/devices/system/cpu/cpufreq/policy0/scaling_cur_freq
adb shell su -c 'cat /proc/perfmgr/boost_ctrl/eas_ctrl/perfserv_fg_uclamp_min'
adb shell su -c 'cat /proc/perfmgr/tchbst/user/usrtch'
adb shell dmesg | grep -iE "FTS|tchbst|avc.*denied"
```

---

## 3. What the live device showed

### 3.1 Baseline is sane but noisy

- `getprop` `debug.sf.use_phase_offsets_as_durations 0` `ro.surface_flinger.vsync 8400000/-10933333`
  `debug.sf.hwc.min.duration 23000000` `uclamp.min 128` — the `2026-08-28` fix is
  active. `dumpsys SurfaceFlinger:84` `app 8.4ms SF -10.9ms HWC 23ms 60 Hz`
  `missed 1686 HWC / 774 GPU` since boot.
- `powerhint.json:5,54` `policy0/policy6` correct (not `cpu0` alias). `INTERACTION`
  `1000 ms 1275000/1308000 FG30` triggers `fg 0→30` on `input swipe 540 1800→400`
  `freq 774000→2000000` `dumpsys thermalservice Status 0 CPU 60.4C mtktsAP 42.6C`.
- `tchbst` `enable 1 eas 100 active 300000` `touch_event 2` never increments on
  `input swipe` (expected — inject bypasses driver) but also stays `2` on
  `sendevent /dev/input/event3` `Permission denied` even with `su`.

### 3.2 The stall

`ls -lZ /sys/kernel/ged/hal: custom_boost_gpu_freq -r--r--r-- system`
read-only. `configs/powerhint.json:281` defined `GpuCustomBoostFreq` `0,30,50,70,90,100`
and `GAME 70` `GAME_LOADING 90`. `logcat libperfmgr` spammed:

```
W libperfmgr: Failed to write to node: /sys/kernel/ged/hal/custom_boost_gpu_freq with value: 0, fd: -1
W NodeLooperThrea: avc: denied { dac_override } hal_power_default
```

every `~500 ms` while `INTERACTION` was held. `NodeLooperThread` blocks on that
write, so the next hint is delayed. Physical generates touch moves at `FTS 120 Hz`
→ `Do Powerhint: INTERACTION for 500ms/100ms` more often than scrcpy inject →
more stalls → visible stutter. Scrcpy still janked (`inject-scroll 11192 frames
10.6% Janky High 14014`) but less.

### 3.3 Thermal and SF not the cause

`dumpsys thermalservice` `CPU 60-72C GPU 60-72C` warm but no
`CoolingDevice` throttling; `thermal_info_config.json:38` `58/75 battery 55/60`
not tripped. `HWC` was `23 ms` (> `16.6 ms` vsync) but dropping to `10500000`
via `apd resetprop debug.sf.hwc.min.duration` + `pkill surfaceflinger` gave
`HWC 10500000` `missed 1` and similar `gfxinfo` (`90 frames 15%` vs `30 frames
23%` — sample too small after reset) so `HWC` is not the dominant factor.

---

## 4. What changed

### 4.1 `configs/powerhint.json:1` `25→24 Nodes 58→55 Actions`

Removed the unwritable node and its actions:

- `Nodes: GpuCustomBoostFreq /sys/kernel/ged/hal/custom_boost_gpu_freq:281`
- `Actions: GAME GpuCustom 70:501` `GAME_LOADING GpuCustom 90:547`

`git diff --stat 1 file 26 deletions` `grep -c GpuCustom 3→0` `python -m json.tool ok`.
Remaining `GAME` keeps `GPUBlockBoost 80` `GPUDVFSMargin 45` `TopAppCpuset 0-7`
etc. `GAME` still has `EndHint INTERACTION`.

Why: the kernel exposes `custom_boost_gpu_freq` as `444`, no `chmod` in
`init.mt6781.power.rc:102` can make it writable; writes always fail and spam
`NodeLooperThread`.

### 4.2 Live bind for testing

```bash
adb push configs/powerhint.json /data/local/tmp/powerhint.json
adb shell su -M -c 'chcon u:object_r:vendor_configs_file:s0 /data/local/tmp/powerhint.json; mount -o bind /data/local/tmp/powerhint.json /vendor/etc/powerhint.json'
adb shell su -c 'pkill -f android.hardware.power-service.pixel-libperfmgr'
```

Needs `chcon` — without it `avc: denied { read } hal_power_default shell_data_file`
and `Failed to read JSON config Invalid config` `logcat 14:05:28`.

After bind: `HAL 8668 No AdpfConfig Initialized HintManager`, `logcat -c` then
`input swipe` → `0 Failed to write` (`wc -l 0`), `Do Powerhint: INTERACTION
for 500ms` clean.

---

## 5. Verification — inject vs physical after fix

Both `15 s` `debug-ux/capture.sh:1` with launcher foreground
`mCurrentFocus com.android.launcher3`:

| capture | trace | gfxinfo `com.android.launcher3` | SF `missed` |
| --- | --- | --- | --- |
| `inject-fixed` `SIMULATE=scroll` | `32M` | `1009 frames Janky 79 7.83% Missed 27 High 1310 50th 10ms` | `HWC 23ms missed 1` |
| `physical-launcher` finger | `5.1M` | `1371 frames Janky 117 8.53% Missed 33 High 1903 50th 11ms` | `missed 4` |

Delta `0.70%` jank, `0.09` high-latency per frame — within noise, vs pre-fix
`inject-scroll 10.6% High 14014/11192`. `logcat` after `logcat -c` + swipe is
clean; `dumpsys SurfaceFlinger` `HWC missed 4` not climbing.

Earlier `physical-touch` with `com.supercell.clashofclans` foreground gave
`6 frames 83%` — not comparable; ensure launcher is foreground
`am start -a MAIN -c HOME` before capture.

---

## 6. How to build and keep the fix

```bash
source build/envsetup.sh
lunch infinity_X670-userdebug
m -j$(nproc) # out/target/product/X670/ lineage-*.zip boot.img
```

`umount /vendor/etc/powerhint.json` reverts to `13702 3 GpuCustom` until flash.
Keep the `su -M mount -o bind` above for live testing, or use the
`x670_smooth` APatch module pattern `nsenter --mount=/proc/1/ns/mnt -- mount -o bind`
as in `session-2026-08-28`.

Next: re-run `Winscope` `layers/transactions` + `android.input.inputevent` traces
if any residual jitter remains, and address the remaining
`avc: denied { dac_override } hal_power_default` (`dmesg`) via sepolicy if it
reappears on other `ged` nodes.

