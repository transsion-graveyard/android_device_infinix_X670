# AGENTS.md

## What this is

LineageOS/AxionOS device tree for the Infinix X670 (Note 12), MediaTek Helio G96 (mt6781).
It is NOT standalone: it only builds inside a full Android source tree (current ROM base: AxionOS, branch `axion-bp4a`) and depends on sibling repos that must be linked into that tree:

| In-tree path | Source |
|---|---|
| `device/infinix/X670` | this repo |
| `device/infinix/X670-kernel` | sibling `android_device_infinix_X670-kernel` |
| `vendor/infinix/X670` | sibling `android_vendor_infinix_X670` |

Under the parent dir also live `stock-report/`, `boot/ramdisk`, `log/`, and `Infinix-Note-12-X670-13-11/` (stock firmware) — on-device evidence/diagnostics, not build inputs.

## Build

- Lunch: `lunch lineage_X670-userdebug`. There is no standalone lint/test; the only verification is a full `m` build in the parent source tree.
- Kernel is a PREBUILT, never built from source: `BoardConfig.mk` sets `TARGET_NO_KERNEL_OVERRIDE := true`, copies `Image.gz` as the kernel and uses `BOARD_PREBUILT_DTBIMAGE_DIR` for DTB; `TARGET_KERNEL_SOURCE` points at `kernel-headers/` only to satisfy Soong. To change the kernel, replace `Image.gz`/`dtb/` in the sibling kernel repo.
- `WITH_GMS := true` (in `lineage_X670.mk`) flips filesystem types: with GMS all partitions build erofs; without GMS, SSI partitions are ext4 and vendor erofs (`BoardConfig.mk`).
- Blob extraction (LineageOS extract-utils): `./extract-files.py` (needs the `tools/extract-utils` PYTHONPATH from the source tree); `setup-makefiles.py` just re-runs it with `--regenerate_makefiles`. Blob lists: `proprietary-files.txt` (~1400 entries) and `proprietary-firmware.txt`.

## vendorsetup.sh has side effects OUTSIDE this tree

It patches other repos and is required for the tree to build/boot. Applies are idempotent and non-fatal:
- `patches/0001-libfs_avb-*.patch` + `0002-fastbootd-*.patch` → `system/core` (allow LKs patched with "fenrir" to boot; make fastbootd always report unlocked; wired via Soong config `fastbootd.bypass_lock_state`).
- `patches/0001-ax_deviceinfo-*.patch` → `axion_sdk` (battery capacity from PowerProfile).
- `patches/0003-vndk-drop-libbinder-v32-prebuilt.patch` → drops the in-tree `libbinder-v32` prebuilt when `hardware/lineage/compat` provides one (avoids a duplicate-module build error).
- Clones `https://github.com/ardiandideyashidiq/fuck-bpf` and runs `apply.py --mb`.

## Device quirks / shims

- The only in-tree shim is `libjni_shim` (`libshims/engineering_mode/libjni_shim.c`), stubbing `SurfaceComposerClient::getInternalDisplayToken`. The other shims referenced by `extract-files.py` (`libbase_shim`, `libbinder_shim`, `libhidlbase_shim`, `libprocessgroup_shim`, `libcamera_metadata_shim`) are defined in `vendor/infinix/X670`.
- `vndk/` ships arm64 prebuilts `libbinder-v32` and `libssl-v33` as `cc_prebuilt_library_shared`; `device.mk` also pulls the v32/v34 vendor libs.
- SELinux lives in `sepolicy/{vendor,private,public}`; `BoardConfig.mk` includes `device/mediatek/sepolicy_vndr/SEPolicy.mk`. See the android-selinux-repair skill for AVC/build triage.
- Overlays in `overlay/` are RROs (`PRODUCT_ENFORCE_RRO_TARGETS := *`); `TetheringConfigTarget` is `product_specific`, `FrameworksResTarget` is `vendor: true`.
- Audio is a 64-bit-only HAL (`android.hardware.audio@7.0-impl:64`); Dolby via `vendor/sony/dolby`, IMS via `vendor/mediatek/ims`, GMS branding via `AXION_*`/`ro.lunaris` props.

## Active project context

`docs/superpowers/specs/2026-05-17-x670-hotspot-dns-rootcause-design.md` documents a live hotspot/DNS root-cause investigation. Current non-goals (do not "fix"):
- don't widen `config_tether_wifi_regexs` again (overlay currently carries `wlan\d` + `ap\d`; the doc's stock-parity direction was `ap\d` only) without fresh runtime evidence
- don't change telephony/DSDS props (`persist.radio.multisim.config=dsds`, etc. — the verified stock baseline)
- don't touch BPF/offload unless logs prove it fails first

## Conventions

- Commit subjects are terse lowercase ("fix prop", "sepol", "drop rkpd..."). Current work branch: `axion-bp4a` (also `lineage-22.2`, `lineage-23.2`, `lineage-23.2-infinity`).
- Release: `upload-release.sh` uploads the ROM zip + `boot/vbmeta*.img` to GitHub releases on `transsion-graveyard/rdndds_android_device_infinix_X670`. `OUT_DIR` is hardcoded to the build host `/home/inscrutable/android_development/los_22_2/out/target/product/X670`.
