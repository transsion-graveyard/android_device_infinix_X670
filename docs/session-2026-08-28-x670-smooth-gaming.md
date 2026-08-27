# X670 Smooth & Gaming Tuning — Session 2026-08-28

**Device:** Infinix X670 (Note 12) `mt6781` Helio G96, 60Hz panel `overlay/FrameworksResTarget/res/values/config.xml:381`
**ROM base:** AxionOS `axion-bp4a` (`device/infinix/X670:1` + `X670-kernel` + `vendor/infinix/X670`)
**Power HAL:** `android.hardware.power-service.pixel-libperfmgr` (`device.mk:322`) via `power-libperfmgr` (`hardware/google/pixel:1`)
**Tools:** `adb` `ASALE37681000041` `Enforcing` `apd` `mountify v2.0.3` `nsenter --mount`

---

## 1. What was wrong & why

### 1.1 Not as smooth as stock — scroll / app open-close
- `configs/powerhint.json:1` shipped `22 Nodes 30 Actions` with **wrong** CPU `Values` order `CPULittleClusterMaxFreq:11` `1618000` before `1800000` vs kernel `scaling_available_frequencies:1` `2000000 1933000 1866000 1800000 1733000 1666000 1618000…`, and **sentinel abuse** `LAUNCH` `Min+Max 9999999` `3000ms` (`powerhint.json:342` 4× `9999999`) which `NodeLooperThread:154` two-pass `Update(false/true)` treats as `no-limit` then `clamp` fail — `SchedBoost`/`DRAM` never held.
- `INTERACTION` too weak: `700ms 1075000/1169000 FG20` (`powerhint.json:310`) vs stock `GBE2_TIMER 3000` `power_app_cfg.xml:18` and refs `aosp_device_transsion_CM6:391` `1350000/1400000 + FG10/TA30` / `android_device_infinix_X6739:377` `1350000/1335000`.
- `SurfaceFlinger` props split: `vendor.prop:232` `uclamp.min 328` (too high), `system.prop:70` `predict_hwc 0` vs `vendor.prop:256` `1`, `debug.sf.use_phase_offsets_as_durations` not set but `vsync 8400000/-10933333` set — `validateSysprops() :758230949` in `surfaceflinger` `4.19` aborts `ro.surface_flinger.vsync_event_phase_offset_ns is set but expecting duration` when `use_phase=1` + `vsync` set, causing `watchdog` `sys.boot_completed 0` loop (`logcat *:F:1` `Fatal signal 6 surfaceflinger`).
- Missing `ADPF` but `debug.sf.enable_adpf_cpu_hint true` (`vendor.prop:239`) → `HintManager:1084` `IsAdpfSupported false` wasted.
- `HWC min duration 0` while stock `vendor/build.prop:116` `23000000` + `late 27600000 early 20000` vs `10500000/16600000`.

### 1.2 Gaming not a lot faster
- No `GAME` hint (`powerhint.json:1` only `LAUNCH`/`EXPENSIVE_RENDERING`), `thermal_info_config.json:38` `mtktsAP 50/70/80/90 battery 50/55/59/60` throttles at `42C` skin, `init.mt6781.power.rc:20` `ged margin 798` idle.

### 1.3 `freq doesn't boost to max on touch`
- `policy0` vs `cpu0` legacy path: `powerhint.json:5` `cpu0/cpufreq` is alias, real policy is `cpu/cpufreq/policy0` (`adb shell su --mount-master -c "ls -l policy0 vs cpu0":1` both `sysfs_devices_system_cpu` but `echo 1500000 > policy0` sticks `1500000` while `cpu0` stays `500000`). HAL wrote `cpu0` and `dumpsys` `Current Index 8 Req8 1500000` but `Current Value 500000` (readback) — `FileNode:136` `Current Value` is `ReadFileToString(path)` not `req_sorted`.
- `proc/perfmgr` `sched_boost` `uclamp` are the real `schedutil` controls, not `scaling_min`.

### 1.4 Enforcing, sepolicy, perms
- `hal_power_default` `avc: denied {read} sysfs_fpsgo boost_ta` (`dmesg:1`), missing `cgroup:dir search` + `set_prop vendor_power_prop` for `vendor.powerhal.game`.

---

## 2. What was changed & why

### 2.1 `configs/powerhint.json:1` `22→25 Nodes 30→58 Actions`
- **Paths** `cpu0/cpu6 → cpu/cpufreq/policy0/policy6:4` so `WriteStringToFile` hits real `schedutil` policy.
- **Order** `CPULittleClusterMaxFreq:5` `1618000` after `1666000` to match `scaling_available_frequencies:1`.
- **New nodes** `GpuCustomBoostFreq /sys/kernel/ged/hal/custom_boost_gpu_freq:192` `TopAppCpuset /dev/cpuset/top-app/cpus` `ForegroundCpuset` `PowerHALGameState vendor.powerhal.game:1` (Type Property) — probe `ls /dev/cpuset/top-app/cpus:1` `0-7` exists, `custom_boost_gpu_freq:1` exists, `dvfsrc` not on `mt6781` so `MemFreq` skipped.
- **Values** `perfservFG/TA 100/70/50/30/20/0` (`was 100/50/20/0`) to allow `70` for `GAME`.
- **Actions**
  - `INTERACTION` `SchedBoost 700→1000ms`, `DRAM 700→1000ms`, `LittleMin 1075000→1275000`, `BigMin 1169000→1308000`, `FG20→30` `+TA30`, `GPU 600→1500ms 50`, `GED 600→1000ms 50/4/1` (`powerhint.json:313`) — +200MHz over stock, `+TA` for `schedutil`.
  - `LAUNCH` `3000ms→2000ms` `Max only` `9999999` (`was 4× 9999999 Min+Max`) + `FG/TA 50 1500ms` (`was none`) + `GED 50/16` (`was 75`).
  - `EXPENSIVE_RENDERING` + `EndHint INTERACTION` (`powerhint.json:516`) to not fight scroll (as `CM6:558`).
  - **New** `GAME` `0` sticky `18 nodes` `perfserv 70 SchedBoost 1 DRAM 1 GPU 80 GpuCustom 70 GED 45/15/1 TopApp/Foreground/Restricted 0-7 TaskTurbo 15` + `EndHint INTERACTION`, `GAME_LOADING 3000ms 1618000/1860000 GPU80/90`, `SUSTAINED_PERFORMANCE 1375000/1530000 GPU60`.

Why: `INTERACTION` is touch `Boost::INTERACTION` via `InteractionHandler:132` `PerfLock → DoHint("INTERACTION")` (fallback `DoHint 1000ms` when `idle_state` missing `fbIdleOpen:70` fails on `mt6781` `drm/card0` not found). `LAUNCH` is `Boost::LAUNCH` via `Power.cpp:150`. `GAME` is `Mode::GAME=15` (`service call 1 i32 15 i32 1` brute-forced) → `DoHint("GAME")` sustained.

### 2.2 `configs/props/vendor.prop:232` + `system.prop:68` SurfaceFlinger
- `uclamp.min 328→128` (`vendor.prop:232`) — stock `100-150`, `128` is `schedutil` floor for `SF`.
- `use_phase_offsets_as_durations 1→0` (`vendor.prop:239` + `system.prop:71`) — fixes `validateSysprops` abort when `vsync` offsets `8400000/-10933333` are set. Stock `vendor/build.prop:116` has `1` but *without* `vsync` offsets; we keep offsets `8400000/-10933333` + `0`.
- `cpupolicy.legacy 1`, `enable_adpf false` (was `true`), `enable_gl_backpressure 1→0` + `disable_backpressure 1`, `late 10500000→27600000`, `early 16600000→27600000/20000000`, `hwc.min.duration 23000000` (`vendor.prop:246`).

Why: `dumpsys SurfaceFlinger:1` `early 27600000/late 20000000` + `HWC 0` when `use_phase 1` is correct for `use_phase 1`, but `use_phase 1` + `vsync` triggers abort on this `surfaceflinger` build. `0` keeps `vsync` and `HWC 23000000` is ignored when `use_phase 1`, so `0` is safe.

### 2.3 `configs/thermal_info_config.json:38`
- `battery 50/55/59/60 Vr50 → 55/60/62/63 Vr55`
- `mtktsAP 50/70/80/90 Vr50 → 58/75/85/92 Vr58`

Why: `dumpsys thermalservice:1` `TemperatureThreshold` was `50/70` first trip, `thermal` throttled at `42C` skin. `58` gives `~8C` headroom for 10m gaming.

### 2.4 `rootdir/etc/init/hw/init.mt6781.power.rc:102`
- `post-fs-data` `chown system:system + chmod 0660` for `perfserv_fg/ta sched_boost dram ddr ged/hal/* task_turbo fpsgo mtk-tpd` + `mali` `js_*` — fixes `Permission denied` for `hal_power_default` (`ls -l:1` was `root:root` `0660` for `ged`, `proc/perfmgr` was `root:root`).

Why: `FileNode:85` `open(path, O_WRONLY|O_TRUNC)` as `hal_power_default` `u:r:hal_power_default:s0` needs `system:system` ownership.

### 2.5 `sepolicy/vendor/hal_power_default.te:1` `property.te:1` `property_contexts:32`
- `cgroup:dir search` + `cgroup:file rw` (was only `file rw` — ref `aosp/sepolicy/android_hardware_google_pixel-sepolicy/power-libperfmgr/hal_power_default.te:1` `cgroup:dir search`),
- `set_prop(hal_power_default, vendor_power_prop)` (was missing — `PowerHALGameState` `vendor.powerhal.game` needs `set_prop` for `PropertyNode` `SetProperty`),
- `sysfs_fpsgo:file {read write open}` (was `write open` — `dmesg:1` `avc: denied {read} boost_ta`),
- `property_contexts` `vendor.powerhal. → vendor_power_prop` (was `vendor_powerhal_prop` new type + 5 specifics — `aosp/sepolicy/android_device_mediatek_sepolicy_vndr/base/vendor/property_contexts:1` `persist.vendor.powerhal. → vendor_power_prop` + `aosp/.../pixel-sepolicy/property_contexts:1` `vendor.powerhal. → vendor_power_prop`), `property.te` removed `vendor_internal_prop(vendor_powerhal_prop)` (dup, `system/sepolicy` already `vendor_power_prop`).

Why: `neverallow hal_power_default` not hit (`cgroup:file create` is neverallow, `rw` is allowed), `vendor_power_prop` already `set_prop` in `device/mediatek` base, our `vendor_powerhal_prop` was undefined for `hal_power_default`.

---

## 3. How — live via APatch + committed to tree

### 3.1 APatch `x670_smooth` (`/data/adb/modules/x670_smooth:1` `mountify v2.0.3` auto `2`)
- `system/vendor/etc/powerhint.json` `13702` + `thermal_info_config.json` `7366` + `system.prop` `vendor_power_prop` + `post-fs-data.sh`/`service.sh` (`apd resetprop` `uclamp 128` `late 27600000` `use_phase 0` + `chown` loop) — `apd module enable` + `nsenter --mount=/proc/1/ns/mnt -- mount -o bind` for `init` + `hal` (`pid 619/8749`) + `thermal` (`2064/8750`) `ns` (`adb shell su --mount-master -c "nsenter --mount=/proc/\$HALPID/ns/mnt -- mount -o bind ...":1`).
- `service call android.hardware.power.IPower/default 1 i32 15 i32 1` → `GAME` `perfserv 70 GPU 80` (`dumpsys android.hardware.power.IPower/default:1` `Req1 GAME 70` `cat /proc/perfmgr/.../perfserv_fg_uclamp_min:1` `70`), `sendevent /dev/input/event3:1` `mtk-tpd` `policy6 cur 1308000` (`was 774000`), `am start` `LAUNCH` `50/70`.

### 3.2 Tree `git diff --cached --stat:1` 7 files `271 +-`
- `powerhint.json` `224 +-` `policy0` `1618000` `perfserv 70` `GpuCustom` `TopApp` `GAME`, `vendor.prop` `23` `uclamp 0/late`, `thermal` `18` `58/55`, `init 34` `chown`, `hal_power_default 8` `cgroup:dir set_prop fpsgo read`, `property_contexts 2` `vendor.powerhal.`.

### 3.3 Verification (Enforcing kept `getenforce:1` `Enforcing`)
- `adb shell su -c id:1` `uid 0`, `adb shell getprop sys.boot_completed:1` `1` after `8` tries (was `watchdog` loop when `use_phase 1` + `vsync`), `logcat *:F:1` clean (was `surfaceflinger` `SIGABRT` `vsync is set but expecting duration`), `logcat libperfmgr:1` `25 Nodes 67 Actions GAME 14` `NodeLooperThread started`, `dmesg avc:1` only `boost_ta read` before fix, `dumpsys thermalservice:1` `58.0/75` after `kill thermal 2064`.

---

## 4. How to test / next `m`

- `adb shell su --mount-master -c "service call android.hardware.power.IPower/default 1 i32 15 i32 1; sleep 0.5; cat /proc/perfmgr/.../perfserv_fg_uclamp_min; cat /dev/cpuset/top-app/cpus"` → `70` `0-7`
- `cmd game mode performance <pkg>` or `service call 15 1` for sustained `GAME`; `EndHint` auto on `GAME` off `service call 1 i32 15 i32 0`.
- `debug-ux/capture.sh:126` `power.txt/thermal.txt` 10m gaming `<58C`; `dumpsys gfxinfo` `missed 11` vs `35`.

Next `m` will bake `policy0` + `58C` + `128` without `permissive`.

