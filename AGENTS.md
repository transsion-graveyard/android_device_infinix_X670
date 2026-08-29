# AGENTS.md — device/infinix/X670 (Infinix X670, mt6781 Helio G96)

## What this is
- Lineage/Axion device tree for **Infinix X670 (Note 12)**. SoC `mt6781` (`BoardConfig.mk:52`), platform Helio G96 (`infinity_X670.mk:49`).
- Repo **must** live at `device/infinix/X670` inside a full Android tree — paths are hard-coded as `device/infinix/X670` (`BoardConfig.mk:11`, `infinity_X670.mk:12`).
- No standalone build/test/lint. All verification is a full Android tree build.

## Product / lunch targets
- `PRODUCT_NAME := infinity_X670`, `PRODUCT_DEVICE := X670` (`infinity_X670.mk:17-18`).
- `AndroidProducts.mk:10-12` exposes: `infinity_X670-user`, `infinity_X670-userdebug`, `infinity_X670-eng`.
- Product makefile: `infinity_X670.mk:1` (`device/infinix/X670/device.mk` + `vendor/infinity/config/common_full_phone.mk`).
- Current branch `axion-bp4a` expects AxionOS `axion_sdk` tree; GMS `WITH_GMS := true` (`infinity_X670.mk:29`).

## Tree dependencies (missing = build break)
- Kernel prebuilt: `device/infinix/X670-kernel/Image.gz + dtb` (`BoardConfig.mk:79-84`, `KERNEL_PATH := device/infinix/X670-kernel:12`). `TARGET_NO_KERNEL_OVERRIDE := true` (`BoardConfig.mk:74`) — kernel is not built from source.
- Proprietary vendor: `vendor/infinix/X670/X670-vendor.mk` (`device.mk:414`), `BoardConfigVendor.mk` (`BoardConfig.mk:201`). Generate via extraction (below).
- Soong namespaces: `hardware/mediatek`, `hardware/mediatek/libmtkperf_client`, `hardware/google/interfaces`, `hardware/google/pixel` (`device.mk:35-40`).
- SEPolicy base: `device/mediatek/sepolicy_vndr/SEPolicy.mk` (`BoardConfig.mk:163`).
- Optional compat: `hardware/lineage/compat/vndk/v32/...` — `vendorsetup.sh:55` conditionally patches `vndk/` if lineage compat provides `libbinder-v32.so`.
- Requires `vendor/infinity/config/BoardConfigReservedSize.mk` when `WITH_GMS != true` (`BoardConfig.mk:117`).

## Build
```bash
source build/envsetup.sh
lunch infinity_X670-userdebug   # or -user / -eng
m -j$(nproc)                    # full ROM; output at out/target/product/X670/
# Valid artifacts for upload-release: lineage-*-UNOFFICIAL-*.zip + boot.img/vbmeta*.img (upload-release.sh:23-24,58-62)
```
- Partition FS depends on `WITH_GMS`: non-GMS `SSI ext4 + vendor erofs`, GMS `all erofs` (`BoardConfig.mk:91-103`). Wrong flag = OTA/image mismatch.
- AVB test keys only (`BoardConfig.mk:142-160`). Release signing needs key replacement.

## Vendor blobs — do not hand-edit generated makefiles
- Source of truth: `proprietary-files.txt` (main) + `proprietary-firmware.txt` (with `add_firmware_proprietary_file=True`, `extract-files.py:172`).
- Extraction: `python3 extract-files.py` (shebang `PYTHONPATH=../../../tools/extract-utils`, `extract-files.py:1`) — pulls from connected device or `vendor/infinix/X670` dump. Blob fixups in `extract-files.py:50-164` (patchelf `0_17_2:43`, shims, soname rewrites).
- Regenerate makefiles: `python3 setup-makefiles.py` (one-liner that calls `extract-files.py --regenerate_makefiles`, `setup-makefiles.py:1`).
- `BUILD_BROKEN_ELF_PREBUILT_PRODUCT_COPY_FILES := true` required (`BoardConfig.mk:9`).

## `vendorsetup.sh` side-effects — runs on every `lunch`/`source envsetup.sh`
- Idempotent `apply_patch` helper (`vendorsetup.sh:9-32`) — checks `apply --check` and `apply --reverse --check` before applying.
- `patches/0001-ax_deviceinfo-use-power-profile...` → `axion_sdk` if present (`vendorsetup.sh:35-48`); unshallows shallow clone first.
- `patches/0001-libfs_avb...fenrir...` + `0002-fastbootd...` → `system/core` (`vendorsetup.sh:51-52`).
- `patches/0003-vndk-drop-libbinder-v32...` → this repo itself if `hardware/lineage/compat/vndk/v32/.../libbinder-v32.so` exists (`vendorsetup.sh:55-57`).
- Clones/updates `fuck-bpf` (`https://github.com/ardiandideyashidiq/fuck-bpf`) to top-level `fuck-bpf/` and runs `python3 fuck-bpf/apply.py --mb` (`vendorsetup.sh:60-76`). Requires network; fails silently if offline. Re-run `lunch` after cleaning it.

## Power / thermal / SurfaceFlinger — hard-won quirks
- `configs/powerhint.json:5` **must** use `/sys/devices/system/cpu/cpufreq/policy0` and `policy6` — not `cpu0/cpu6`. The latter is an alias; writes don't stick (see `docs/session-2026-08-28-x670-smooth-gaming.md`).
- `CPULittleClusterMaxFreq` Values order must match `scaling_available_frequencies` (`2000000 1933000 ... 500000`). Wrong order = wrong frequency level.
- Do not set `Min+Max 9999999` sentinel together. `NodeLooperThread` treats `9999999` as no-limit; `Min=9999999` breaks boost. Correct: `Max 9999999` only for `LAUNCH` (`docs/session...`).
- `powerhint.json` nodes `GpuCustomBoostFreq` (`/sys/kernel/ged/hal/custom_boost_gpu_freq`), `TopAppCpuset`/`ForegroundCpuset` (`/dev/cpuset/.../cpus`), `PowerHALGameState` (`vendor.powerhal.game`) require `hal_power_default` sepolicy + `init.mt6781.power.rc:102` `chown system:system chmod 0660`.
- `vendor.prop` / `system.prop`: `debug.sf.use_phase_offsets_as_durations` must be `0` when `ro.surface_flinger.vsync_event_phase_offset_ns` and `..._vsync_sf_event_phase_offset_ns` are set (`8400000/-10933333`). `1` + offsets aborts `surfaceflinger` (`validateSysprops`, `watchdog sys.boot_completed 0` loop). See session doc. `hwc.min.duration` is ignored when `use_phase=1`.
- `debug.sf.enable_adpf_cpu_hint=true` (`vendor.prop:241`) — SF build supports ADPF (`dumpsys SurfaceFlinger | grep use_adpf` shows `use_adpf_cpu_hint: true` + `adpf_gpu_sf: true`). Keep on. With it off + battery saver, SystemUI jank is 22% (99p 105ms); with it on, jank drops to 8.9% under saver (close to the 6.75% saver-off baseline). The earlier 2026-08-28 note saying ADPF wasn't compiled in was wrong — verified live.
- Thermal: `configs/thermal_info_config.json:38` trips tuned to `battery 55/60/62/63 mtktsAP 58/75/85/92` (stock throttled at ~42C skin). Verify with `dumpsys thermalservice`.
- PowerHAL is `android.hardware.power-service.pixel-libperfmgr` via `hardware/google/pixel` (`device.mk:322-330`, `configs/powerhint.json`).

## SEPolicy
- Own: `sepolicy/{vendor,private,public}` (`BoardConfig.mk:163-166`). Base is `device/mediatek/sepolicy_vndr`.
- `sepolicy/vendor/hal_power_default.te:1` rules for `hal_power_default` to touch `cgroup`, `sysfs_ged`, `sysfs_fpsgo`, `sysfs_devices_system_cpu`, etc. Missing `cgroup:dir search` or `fpsgo read` = `avc: denied {read} boost_ta` and silent powerhint failure.
- `vendor.powerhal.game` property → `vendor_power_prop` (`property_contexts`), **not** custom `vendor_powerhal_prop`. Needs `set_prop(hal_power_default, vendor_power_prop)`.

## VNDK / shims
- `vndk/Android.bp:1` prebuilts: `libbinder-v32` (`v32/arm64/libbinder-v32.so`), `libssl-v33`. `check_elf_files: false`, `compile_multilib: "64"`.
- Shims: `libshims/engineering_mode/libjni_shim.c` (`Android.bp`), `libbinder_shim`, `libbase_shim` (`device.mk:245-247`), plus `libprocessgroup_shim`, `libhidlbase_shim`, `libcamera_metadata_shim` injected via `extract-files.py` blob_fixups. Prefer patching `extract-files.py` blob_fixups over hand-editing `vendor/`.
- `device.mk:248-254` pins `libtinyxml2-v34`, `libbinder-v32`, `libhidlbase-v32`, `libutils-v32` for vendor blobs.

## Directory map
- `configs/{audio,media,display,wifi,hals.conf,powerhint.json,thermal_info_config.json,props/{system,vendor}.prop,public.libraries.txt,vintf/{manifest,framework_compatibility_matrix}.xml}` — `DEVICE_PATH/configs` (`BoardConfig.mk:13`).
- `rootdir/etc/{fstab.mt6781,ueventd.mt6781.rc,init/hw/init.{mt6781,connectivity,modem,project,...}.rc}` — declared in `rootdir/Android.bp:1`.
- `overlay/{FrameworksResTarget,Settings{,Provider}ResTarget,SystemUIResTarget,TetheringConfigTarget,WifiResTarget}` — `PRODUCT_ENFORCE_RRO_TARGETS := *` (`device.mk:310`).
- `vndk/{v32,v33}/`, `libshims/`, `patches/*.patch`, `extract-files.py`, `proprietary-files.txt`, `vendor_logtag.mk` (log tag props gated on `TARGET_BUILD_VARIANT`).

## Debug tooling (no emulator needed)
- `debug-ux/capture.sh [seconds]` — whole-device perfetto + gfxinfo + dumpsys capture; needs `adb` + rooted `userdebug`. `SIMULATE=scroll|ux VIDEO=1 EXTRA_PKGS=... ./debug-ux/capture.sh 60` (`debug-ux/README.md:9`). Output `debug-ux/out/<tag>/` (gitignored, `.gitignore:4`). Analyze with `python3 debug-ux/analyze_gfxinfo.py` and `https://ui.perfetto.dev`.
- `upload-release.sh:1` — uploads `out/target/product/X670/lineage-*.zip + boot/vbmeta*.img` to `transsion-graveyard/rdndds_android_device_infinix_X670` via `gh`. Hard-coded `OUT_DIR` and `REPO` (`upload-release.sh:7-8`).
