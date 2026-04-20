# Fingerprint Firmware Analysis Report

## 1. Document Control
- **Service / Subsystem:** fingerprint
- **Device Codename:** X670-GL
- **Marketing Name:** Infinix X670
- **SoC / Platform:** MT6781 / MediaTek
- **Board / Hardware Variant:** Infinix-X670
- **Firmware Build ID:** vendor `240224V150`; system/product `240224V556`
- **Android Version:** mixed 12 vendor + 13 framework image
- **Vendor Security Patch Level:** 2024-02-05
- **Kernel Version:** not present in this dump
- **Report Version:** 1.0
- **Author:** OpenCode
- **Date:** 2026-04-20
- **Analysis Scope:** stock firmware dump / extracted partitions
- **Confidence Level:** Medium
- **Status:** Final

---

## 2. Executive Summary

### 2.1 What this service does
This is the device fingerprint authentication stack. Android uses it for enrollment, unlock, app auth, and vendor fingerprint extras. The stock device advertises `ro.fingerprint_support=1` and `ro.side_fingerprint_support=1`, so this is a side-mounted fingerprint implementation.

### 2.2 Stock implementation summary
**Confirmed:** the primary Android-facing HAL is HIDL `android.hardware.biometrics.fingerprint@2.1::IBiometricsFingerprint/default` over `hwbinder`.

**Confirmed:** the main daemon is `/vendor/bin/hw/android.hardware.biometrics.fingerprint@2.1-service`, started by init as `vendor.fps_hal` in `class late_start`.

**Strong inference:** the daemon is a Mediatek/Transsion wrapper that dynamically selects vendor-specific fingerprint backends by probing `/sys/kernel/tran_fp/vendor_name` and then loading a matching HAL blob such as `fpsensor_fingerprint.default.so`.

**Confirmed:** the dump also ships a second vendor HIDL service, `vendor.fpsensor.hardware.fpsensorhidlsvc@2.0::IFpsensorHidlSvc/default`, implemented by `vendor.fpsensor.hardware.fpsensorhidlsvc@2.0.so` and `libfp_ext_svc2.so`.

### 2.3 Bring-up significance
- **Bring-up Priority:** Major
- **Expected ROM impact if broken:** fingerprint enrollment, unlock, and vendor fingerprint actions fail; phone still boots
- **AOSP dependency type:** mixed
- **Treble relevance:** yes

### 2.4 Final recommendation summary
- **Recommended implementation path:** reuse stock blobs
- **Major blockers:** kernel node availability, SELinux, and preserving the vendor extension path
- **Likely required actions:**
  - proprietary blobs
  - init changes
  - manifest/VINTF changes
  - sepolicy work
  - kernel config/module work
  - overlays
  - framework patching
  - app integration

---

## 3. Scope Definition

### 3.1 Included in this report
- Stock fingerprint HIDL HAL
- Vendor `fpsensor` extension HAL
- init rc fragments
- VINTF manifest entries
- SELinux labels, transitions, and allow rules
- fingerprint-related properties
- device nodes and sysfs paths visible from the dump
- related proprietary libraries and helper blobs

### 3.2 Explicitly excluded
- Face authentication
- Gatekeeper / Weaver / Keymaster except where directly referenced by fingerprint blobs
- Camera-based under-display fingerprint logic not evidenced here
- Runtime enrollment/auth logs, because none were provided

### 3.3 Adjacent subsystems
- `biometric` framework service in `system_server`
- `system_server` / Settings biometric UI
- TEE / Trustonic client library path
- sensor node setup in `init.sensor_1_0.rc`
- vendor power hint helper

---

## 4. Source Evidence

### 4.1 Firmware source
- Firmware package: extracted Infinix X670-GL stock partitions
- Region / carrier: not explicitly identified
- Extraction method: partition tree / dump already unpacked in workspace
- Image formats observed: unpacked filesystem trees, ELF binaries, XML, rc, prop, CIL
- Integrity notes: no runtime logs; analysis is static only

### 4.2 Partitions examined

| Partition | Mount Path | Relevant to Service | Notes |
|---|---|---:|---|
| boot | `boot` | no | not directly used as evidence |
| init_boot | `init_boot` | no | not directly used as evidence |
| vendor_boot | `vendor_boot` | no | not directly used as evidence |
| vendor | `/vendor` | yes | main HAL, libs, init, SELinux, properties |
| odm | `/odm` | no | no fingerprint evidence found |
| system | `/system` | yes | compatibility matrices, system policy, permissions |
| system_ext | `/system_ext` | yes | framework policy / service types |
| product | `/product` | yes | fingerprint capability props |
| vendor_dlkm | `/vendor_dlkm` | no | no fingerprint evidence found |
| odm_dlkm | `/odm_dlkm` | no | no fingerprint evidence found |
| system_dlkm | `/system_dlkm` | no | no fingerprint evidence found |

### 4.3 Evidence types used
- file paths
- init rc fragments
- VINTF XML
- build/property files
- binary strings
- `readelf` output
- ELF file typing
- SELinux labels/contexts
- config XML

### 4.4 Confidence grading rules
- **Confirmed:** direct evidence from files or logs
- **Strong inference:** multiple converging clues
- **Weak inference:** plausible but not yet runtime-validated

---

## 5. Service Identity and AOSP Contract

### 5.1 Android-facing role
Android framework expects a fingerprint HAL that can enroll, authenticate, enumerate, remove, and report hardware callbacks. On this device, the stock path is the classic HIDL fingerprint HAL, not AIDL.

### 5.2 Interface model
- **Interface type:** mixed
- **Framework entry points:** `android.hardware.biometrics.fingerprint@2.1::IBiometricsFingerprint`
- **Expected service names:** `vendor.fps_hal`, `android.hardware.biometrics.fingerprint@2.1-service`
- **Expected instances:** `default`
- **Binder domain:** mixed, but primary HAL uses `hwbinder`

### 5.3 HAL / service contract summary
- **Confirmed:** stock VINTF declares `android.hardware.biometrics.fingerprint` version `2.1`, interface `IBiometricsFingerprint`, instance `default`, transport `hwbinder`.
- **Confirmed:** the framework feature XML exposes `android.hardware.fingerprint`.
- **Confirmed:** the device also declares a vendor extension HAL `vendor.fpsensor.hardware.fpsensorhidlsvc` version `2.0`, interface `IFpsensorHidlSvc`, instance `default`.
- **Strong inference:** the vendor extension is used for raw image capture, finger-detect, image quality, and property control flows that are not part of the standard Android HAL.

### 5.4 Compatibility and Treble notes
- VINTF manifest needed: yes
- Compatibility matrix implications: Android 13 compatibility matrix still allows HIDL fingerprint 2.1-3; this device ships HIDL 2.1
- Lazy service behavior: no evidence of lazy registration; init starts the daemon
- Passthrough vs binderized: binderized HIDL
- Same-process HAL/SP-HAL concerns: none directly evidenced, but vendor blob bridge implies proprietary user-space stack

---

## 6. Filesystem Inventory

### 6.1 Executables and daemons

| Path | Binary Name | Purpose | Arch | SELinux Label | Trigger / Service Name | Confidence | Notes |
|---|---|---|---|---|---|---|---|---|
| `/vendor/bin/hw/android.hardware.biometrics.fingerprint@2.1-service` | `android.hardware.biometrics.fingerprint@2.1-service` | main fingerprint HAL daemon | ELF 64-bit ARM64 PIE | `hal_fingerprint_default_exec` via `vendor_file_contexts` for the mediatek-suffixed path | `vendor.fps_hal` | Confirmed | `class late_start`; init rc does not declare interface explicitly |

### 6.2 Shared libraries / proprietary blobs

| Path | Library | Role | Loaded By | Key Dependencies | Namespace Risk | Confidence | Notes |
|---|---|---|---|---|---|---|---|---|
| `/vendor/lib64/android.hardware.biometrics.fingerprint@2.1.so` | `android.hardware.biometrics.fingerprint@2.1.so` | HIDL wrapper / service implementation | main daemon | `libhidlbase.so`, `liblog.so`, `libutils.so`, `libcutils.so`, `libc++.so`, `libc.so`, `libm.so`, `libdl.so` | low | Confirmed | contains `IBiometricsFingerprint` symbols and vendor vendor-selection strings |
| `/vendor/lib64/hw/fpsensor_fingerprint.default.so` | `fpsensor_fingerprint.default.so` | vendor fingerprint backend | main daemon / wrapper | `libMcClient.so`, `liblog.so`, `libc++.so`, `libc.so`, `libm.so`, `libdl.so` | medium | Confirmed | 32-bit twin also present |
| `/vendor/lib64/vendor.fpsensor.hardware.fpsensorhidlsvc@2.0.so` | `vendor.fpsensor.hardware.fpsensorhidlsvc@2.0.so` | vendor extension HIDL service | `libfp_ext_svc2.so` | `libhidlbase.so`, `liblog.so`, `libutils.so`, `libcutils.so`, `libc++.so`, `libc.so`, `libm.so`, `libdl.so` | low | Confirmed | exports `IFpsensorHidlSvc` service functions |
| `/vendor/lib64/libfp_ext_svc2.so` | `libfp_ext_svc2.so` | helper bridge for `fpsensorhidlsvc` | `vendor.fpsensor.hardware.fpsensorhidlsvc@2.0.so` | `libbinder.so`, `libhwbinder.so`, `libhidlbase.so`, `libhidltransport.so`, `vendor.fpsensor.hardware.fpsensorhidlsvc@2.0.so` | medium | Confirmed | contains `capture_raw_img`, `get_img_quality`, `finger_detect_async`, `ext_cmd`, `svc_ctrl` |
| `/vendor/lib64/libMcClient.so` | `libMcClient.so` | Trustonic/Mobicore client | `fpsensor_fingerprint.default.so` | `liblog.so`, `libc++.so`, `libc.so`, `libm.so`, `libdl.so` | medium | Confirmed | strings show `/dev/mobicore-user` |
| `/vendor/lib64/vendor.mediatek.hardware.mtkpower@1.0.so` | `vendor.mediatek.hardware.mtkpower@1.0.so` | MTK power hint helper | main daemon | `libhidlbase.so`, `liblog.so`, `libutils.so`, `libcutils.so`, `libc++.so`, `libc.so`, `libm.so`, `libdl.so` | low | Confirmed | may be used for perf/power boost around fingerprint use |

### 6.3 Config files

| Path | Format | Consumed By | Critical Keys | Overlayable | Confidence | Notes |
|---|---|---|---|---|---|---|---|
| `/vendor/etc/init/android.hardware.biometrics.fingerprint@2.1-service.rc` | init rc | init | service name, `class late_start`, user/group | patch/copy | Confirmed | starts the main daemon |
| `/vendor/etc/init/vendor.fpsensor.rc` | init rc | init | `/dev/fpsensor` ownership/mode | patch/copy | Confirmed | fixes node perms on `on fs` |
| `/vendor/etc/init/hw/init.sensor_1_0.rc` | init rc | init / sensor daemon path | `/dev/biometric`, `/dev/m_bio_misc`, `/sys/class/sensor/m_bio_misc/*` | patch/copy | Confirmed | adjacent but relevant to the fingerprint node surface |
| `/vendor/etc/vintf/manifest/android.hardware.biometrics.fingerprint@2.1-service.xml` | XML | VINTF | HIDL name/version/interface/instance | copy | Confirmed | device HAL declaration |
| `/vendor/etc/vintf/manifest.xml` | XML | VINTF | `vendor.fpsensor.hardware.fpsensorhidlsvc` | copy | Confirmed | vendor extension declaration |
| `/vendor/etc/permissions/android.hardware.fingerprint.xml` | XML | framework feature scanner | `android.hardware.fingerprint` | copy | Confirmed | feature flag required by apps/framework |

### 6.4 APK / JAR / APEX / framework packages

| Path / Package | Type | Purpose | Privileged | Permissions / Features | Confidence | Notes |
|---|---|---|---|---|---|---|---|
| `android.hardware.fingerprint.xml` | permissions XML | declares fingerprint feature | no | `android.hardware.fingerprint` | Confirmed | not an app, but framework-visible contract |
| `privapp-permissions-platform.xml` | privapp XML | generic biometric CTS perms | yes | `USE_BIOMETRIC`, `TEST_BIOMETRIC` | Confirmed | not fingerprint-specific logic |

### 6.5 Firmware assets / DSP / microcode / calibration

| Path | Asset Type | Loaded By | Hardware Target | Required for Bring-up | Confidence | Notes |
|---|---|---|---|---|---|---|---|
| none found in this dump | n/a | n/a | n/a | unknown | Confirmed | no fingerprint firmware blob was identified in the partition tree |

---

## 7. Init Integration

### 7.1 Relevant init fragments
- `/vendor/etc/init/android.hardware.biometrics.fingerprint@2.1-service.rc`
- `/vendor/etc/init/vendor.fpsensor.rc`
- `/vendor/etc/init/hw/init.sensor_1_0.rc`

### 7.2 Service definitions

| RC File | Service Name | Command | Class | User/Group | Capabilities | Disabled/Oneshot | Interface Declaration | Confidence | Notes |
|---|---|---|---|---|---|---|---|---|---|
| `android.hardware.biometrics.fingerprint@2.1-service.rc` | `vendor.fps_hal` | `/vendor/bin/hw/android.hardware.biometrics.fingerprint@2.1-service` | `late_start` | `system` / `system input uhid` | none shown | enabled | not declared in rc | Confirmed | comment explains late start avoids `/data` race |

### 7.3 Trigger paths
- class start: yes, via `class late_start`
- property trigger: not seen for the main HAL
- hwservicemanager lookup: yes, via HIDL registration path in the binary
- servicemanager lookup: not primary path for the main HAL
- lazy start: no evidence
- `post-fs-data`: used by `init.sensor_1_0.rc`
- `boot`: no explicit boot trigger in the HAL rc
- `late_start`: yes
- recovery path: not evidenced

### 7.4 Init writes and side effects
- `chmod 664 /dev/fpsensor`
- `chown system root /dev/fpsensor`
- `chmod/chown` of `/dev/biometric` and `/dev/m_bio_misc`
- `chmod/chown` of `/sys/class/sensor/m_bio_misc/bioactive`, `biodelay`, `biobatch`, `bioflush`

### 7.5 Boot ordering notes
The main HAL is deliberately delayed until `late_start` because the stock tree notes a `/data` race if it starts too early. This suggests the daemon or its backend reads calibration or state from data-backed storage.

---

## 8. VINTF / Manifest Analysis

### 8.1 Manifest sources
- `/vendor/etc/vintf/manifest/android.hardware.biometrics.fingerprint@2.1-service.xml`
- `/vendor/etc/vintf/manifest.xml`
- `/system/system/etc/vintf/compatibility_matrix.device.xml`
- `/system/system/etc/vintf/compatibility_matrix.3.xml`
- `/system/system/etc/vintf/compatibility_matrix.4.xml`
- `/system/system/etc/vintf/compatibility_matrix.5.xml`
- `/system/system/etc/vintf/compatibility_matrix.6.xml`
- `/system/system/etc/vintf/compatibility_matrix.7.xml`

### 8.2 HAL declarations

| Manifest File | Format | Package | Interface | Version | Instance / FQName | Transport | Optional? | Confidence | Notes |
|---|---|---|---|---|---|---|---|---|---|
| `/vendor/etc/vintf/manifest/android.hardware.biometrics.fingerprint@2.1-service.xml` | HIDL | `android.hardware.biometrics.fingerprint` | `IBiometricsFingerprint` | `2.1` | `default` / `@2.1::IBiometricsFingerprint/default` | hwbinder | no | Confirmed | main Android fingerprint contract |
| `/vendor/etc/vintf/manifest.xml` | HIDL | `vendor.fpsensor.hardware.fpsensorhidlsvc` | `IFpsensorHidlSvc` | `2.0` | `default` / `@2.0::IFpsensorHidlSvc/default` | hwbinder | no | Confirmed | vendor extension contract |
| `/system/system/etc/vintf/compatibility_matrix.device.xml` | HIDL | `vendor.fpsensor.hardware.fpsensorhidlsvc` | `IFpsensorHidlSvc` | `2.0` | `default` | hwbinder | yes | Confirmed | device matrix marks it optional |
| `/system/system/etc/vintf/compatibility_matrix.7.xml` | HIDL + AIDL | `android.hardware.biometrics.fingerprint` | `IBiometricsFingerprint` / `IFingerprint` | `2.1-3` / `2` | `default` | hwbinder / binder | yes | Confirmed | framework accepts both generations, stock ships HIDL |

### 8.3 Compatibility observations
- FCM / target-level clues: Android 13 framework matrix still carries HIDL fingerprint compatibility and optional AIDL fingerprint support
- Deprecated interface risk: low for this stock image, because HIDL 2.1 is still declared
- Multiple instances or vendor forks: yes, there are optional vendor fingerprint forks for cdfinger, focaltech, fpsensor, fptool, goodix, mediatek, and silead in the device matrix
- Need to copy stock manifest fragment: yes

### 8.4 Registration path
The main daemon registers `IBiometricsFingerprint/default` through the HIDL library. Init does not expose the interface directly; the binary self-registers after `late_start`. The vendor extension service registers `IFpsensorHidlSvc/default` through its own HIDL service library.

---

## 9. Binary Analysis

### 9.1 Main binary inventory

- `/vendor/bin/hw/android.hardware.biometrics.fingerprint@2.1-service`
  - ELF 64-bit LSB PIE, ARM64, stripped
  - NEEDED: `libcutils.so`, `liblog.so`, `libhidlbase.so`, `libhardware.so`, `libutils.so`, `vendor.mediatek.hardware.mtkpower@1.0.so`, `android.hardware.biometrics.fingerprint@2.1.so`, `libc++.so`, `libc.so`, `libm.so`, `libdl.so`
  - strings: `IBiometricsFingerprint`, `registerAsService`, `/sys/kernel/tran_fp/vendor_name`, `/dev/fpsensor`, `load_extsvc2_for_non_fpsensor`, `goodix`, `silead`, `fpc`, `focal_fingerprint`, `cdfinger`, `fpsensor_fingerprint`, `uinput-fpsensor`

- `/vendor/lib64/android.hardware.biometrics.fingerprint@2.1.so`
  - ELF 64-bit shared object, ARM64, stripped
  - NEEDED: `libhidlbase.so`, `liblog.so`, `libutils.so`, `libcutils.so`, `libc++.so`, `libc.so`, `libm.so`, `libdl.so`
  - exports HIDL `IBiometricsFingerprint` / client callback symbols

- `/vendor/lib64/hw/fpsensor_fingerprint.default.so`
  - ELF 32-bit shared object, ARM, stripped
  - NEEDED: `libMcClient.so`, `liblog.so`, `libc++.so`, `libc.so`, `libm.so`, `libdl.so`
  - strings: `/dev/fpsensor`, `/sys/kernel/tran_fp/vendor_name`, `goodix`, `silead`, `fpc`, `focaltech`, `cdfinger`, `sunwave`, `oxifp`, `fpsensor_fingerprint`

- `/vendor/lib64/vendor.fpsensor.hardware.fpsensorhidlsvc@2.0.so`
  - ELF 64-bit shared object, ARM64, stripped
  - NEEDED: `libhidlbase.so`, `liblog.so`, `libutils.so`, `libcutils.so`, `libc++.so`, `libc.so`, `libm.so`, `libdl.so`
  - strings: `IFpsensorHidlSvc`, `capture_raw_img`, `get_img_quality`, `finger_detect_async`, `ext_cmd`, `svc_ctrl`, `set_property`, `registerAsService`

- `/vendor/lib64/libfp_ext_svc2.so`
  - ELF 64-bit shared object, ARM64, stripped
  - NEEDED: `libbinder.so`, `libhwbinder.so`, `libhidlbase.so`, `libhidltransport.so`, `libcutils.so`, `liblog.so`, `libutils.so`, `vendor.fpsensor.hardware.fpsensorhidlsvc@2.0.so`, `libc.so`, `libm.so`, `libdl.so`, `libc++.so`
  - strings: `add svc2 HIDL service succeed!`, `Couldn't register svc2 HIDL service!`, `FP_SERVICE_CONTROL_CMD_SET_SVC_CB_PURPOSE`, `uinput-fpsensor`, `/dev/uinput`, `onFingerDetected`, `onCommonPassiveRsp`, `onRawImageCaptured`

### 9.2 Dependency table

| Binary / Library | DT_NEEDED | Suspected `dlopen()` Targets | Cross-Partition Dependencies | Missing Symbol Risk | Confidence | Notes |
|---|---|---|---|---|---|---|---|
| main daemon | see above | `android.hardware.biometrics.fingerprint@2.1.so`, likely vendor backend blobs | vendor + system + vendor SELinux + product props | medium | Confirmed | wrapper daemon depends on both standard HAL and MTK power helper |
| `android.hardware.biometrics.fingerprint@2.1.so` | see above | vendor backend modules such as `fpsensor_fingerprint.default.so`, `libfp_ext_svc2.so` | vendor + sysfs + SELinux | medium | Strong inference | strings show dynamic vendor selection and multiple sensor families |
| `fpsensor_fingerprint.default.so` | see above | Trustonic/Mobicore helper path | TEE / mobicore device node | medium | Confirmed | likely actual vendor backend logic |
| `vendor.fpsensor.hardware.fpsensorhidlsvc@2.0.so` | see above | `libfp_ext_svc2.so` | vendor extension service + HIDL transport | low | Confirmed | vendor extension service implementation |
| `libfp_ext_svc2.so` | see above | none visible | binder/hwbinder + vendor service | medium | Confirmed | bridge for extra fp control calls |

### 9.3 Linker namespace / VNDK analysis
- Uses public VNDK only: no
- Uses private platform libs: unknown from static evidence, but only vendor-facing NEEDED libs were observed
- Requires shim library: no direct evidence
- SP-HAL concerns: none obvious
- Namespace risk summary: moderate, because the fingerprint stack is a proprietary wrapper over multiple vendor blobs and a Trustonic client library

### 9.4 Important strings and symbols
- `IBiometricsFingerprint::registerAsService`
- `android.hardware.biometrics.fingerprint@2.1::IBiometricsFingerprint`
- `/sys/kernel/tran_fp/vendor_name`
- `/dev/fpsensor`
- `/dev/biometric`
- `/dev/m_bio_misc`
- `/dev/uinput`
- `uinput-fpsensor`
- `load_extsvc2_for_non_fpsensor`
- `vendor.fpsensor.hardware.fpsensorhidlsvc@2.0::IFpsensorHidlSvc`
- `capture_raw_img`, `get_img_quality`, `finger_detect_async`, `svc_ctrl`, `set_property`

### 9.5 Binary-level conclusions
- The stock fingerprint stack is not a simple single HAL implementation.
- It is a wrapper + vendor-backend design with a separate vendor extension service.
- It supports multiple fingerprint silicon families by name, but the exact active vendor on this device is not proven by static evidence alone.

---

## 10. Device Nodes, Sysfs, Procfs, and IO Surface

### 10.1 Device nodes

| Path | Type | Created By | Ownership / Mode | SELinux Label | Consumer | Evidence | Required | Confidence | Notes |
|---|---|---|---|---|---|---|---|---|---|
| `/dev/fpsensor` | char device | kernel / ueventd | `system:root 0664` via init rc | `fpsensor_fp_device` | main HAL / helper blob | rc + file_contexts + sepolicy | yes | Confirmed | core node for this stack |
| `/dev/biometric` | char device | kernel / ueventd | `system:system 0660` via `init.sensor_1_0.rc` | `biometric_device` | sensor/fingerprint adjacent path | rc + file_contexts | likely | Strong inference | likely shared biometric sensor node |
| `/dev/m_bio_misc` | char device | kernel / ueventd | `system:system 0660` via `init.sensor_1_0.rc` | `m_bio_misc_device` | sensor/fingerprint adjacent path | rc + file_contexts | likely | Strong inference | used by biometric misc sysfs path |
| `/dev/goodix_fp` | char device | kernel / ueventd | label only | `gf_device` | vendor variants | strings + file_contexts | unknown | Weak inference | not proven active on this unit |
| `/dev/silead_fp` | char device | kernel / ueventd | label only | `silead_fpd_device` | vendor variants | file_contexts + sepolicy | unknown | Weak inference | sepolicy allows access |

### 10.2 Sysfs / procfs / configfs paths

| Path | Purpose | Read/Write | Referenced By | Required | Confidence | Notes |
|---|---|---|---|---|---|---|
| `/sys/kernel/tran_fp/vendor_name` | identify active fingerprint vendor | read | main HAL strings | yes | Confirmed | used to pick backend module |
| `/sys/class/sensor/m_bio_misc/bioactive` | biometric sensor control | rw via init perms | `init.sensor_1_0.rc` | likely | Confirmed | shared sensor path |
| `/sys/class/sensor/m_bio_misc/biodelay` | biometric sensor control | rw via init perms | `init.sensor_1_0.rc` | likely | Confirmed | shared sensor path |
| `/sys/class/sensor/m_bio_misc/biobatch` | biometric sensor control | rw via init perms | `init.sensor_1_0.rc` | likely | Confirmed | shared sensor path |
| `/sys/class/sensor/m_bio_misc/bioflush` | biometric sensor control | rw via init perms | `init.sensor_1_0.rc` | likely | Confirmed | shared sensor path |
| `/sys/class/sensor/m_bio_misc/*` | overall biometric misc interface | rw | `init.sensor_1_0.rc` | likely | Strong inference | names imply a shared biometric sensor framework |
| `/dev/uinput` | virtual input | rw | `libfp_ext_svc2.so` strings | maybe | Strong inference | appears to synthesize input/events |

### 10.3 IOCTL / netlink / socket / binder clues
- `libfp_ext_svc2.so` exposes HIDL methods that likely map to vendor IOCTLs on `/dev/fpsensor`
- strings show `uinput-fpsensor`, `FPSENSOR_IOC_INIT`, and `FPSENSOR_IOC_ENABLE_IRQ`
- `fpsensor_fingerprint.default.so` appears to talk to `libMcClient.so` and a TEE / mobicore channel

### 10.4 Runtime path expectations
Working ROM must have:
- `/dev/fpsensor`
- `/sys/kernel/tran_fp/vendor_name`
- `/dev/biometric`
- `/dev/m_bio_misc`
- correct SELinux labels for the above
- the vendor HIDL service(s) present and registered

---

## 11. Ueventd and Permissions

### 11.1 `ueventd.rc` entries
- No explicit `ueventd.rc` entry for fingerprint nodes was found in this dump.

### 11.2 Node permission model

| Node / Path | Owner | Group | Mode | Source File | Confidence | Notes |
|---|---|---|---|---|---|---|---|
| `/dev/fpsensor` | `system` | `root` | `0664` | `vendor/etc/init/vendor.fpsensor.rc` | Confirmed | init fixes permissions on `fs` |
| `/dev/biometric` | `system` | `system` | `0660` | `vendor/etc/init/hw/init.sensor_1_0.rc` | Confirmed | shared sensor path |
| `/dev/m_bio_misc` | `system` | `system` | `0660` | `vendor/etc/init/hw/init.sensor_1_0.rc` | Confirmed | shared sensor path |
| `/sys/class/sensor/m_bio_misc/*` | `system` | `system` | `0660` | `vendor/etc/init/hw/init.sensor_1_0.rc` | Confirmed | biometric misc sysfs controls |

### 11.3 Boot-created paths and symlinks
- No explicit symlink evidence was found for fingerprint nodes
- The init rc only adjusts ownership and permissions

### 11.4 Risk summary
If these permissions are not replicated, the daemon can start but fail to open the device node or sysfs controls, causing a silent fingerprint failure with no obvious boot breakage.

---

## 12. SELinux Analysis

### 12.1 Process domains

| Process / Service | Executable Label | Domain | Starts From | Confidence | Notes |
|---|---|---|---|---|---|
| `vendor.fps_hal` | `hal_fingerprint_default_exec` | `hal_fingerprint_default` | init `late_start` | Confirmed | transition defined in `vendor_sepolicy.cil` |
| `vendor.fpsensor.hardware.fpsensorhidlsvc@2.0` | not separately labeled in this dump | vendor HIDL service domain not explicitly named here | init / HIDL registration | Confirmed | service label is `fp_ext_svc2_service` |

### 12.2 File and node labels

| Path / Node | Expected Label | Used By | Confidence | Notes |
|---|---|---|---|---|
| `/vendor/bin/hw/android.hardware.biometrics.fingerprint@2.1-service-mediatek` | `hal_fingerprint_default_exec` | init / SELinux | Confirmed | file_contexts names a mediatek-suffixed path; init rc launches the unsuffixed binary present in the dump |
| `/dev/fpsensor` | `fpsensor_fp_device` | HAL blobs / init | Confirmed | core fingerprint node |
| `/dev/biometric` | `biometric_device` | sensor path | Confirmed | adjacent biometric device node |
| `/dev/m_bio_misc` | `m_bio_misc_device` | sensor path | Confirmed | adjacent biometric misc node |
| `/sys/kernel/tran_fp(/.*)?` | `sysfs_fp_name_path` | HAL blobs | Confirmed | vendor name selection path |
| `/dev/silead_fp` | `silead_fpd_device` | vendor variants | Confirmed | allowed in policy |
| `vendor.fpsensor.hardware.fpsensorhidlsvc::IFpsensorHidlSvc` | `fp_ext_svc2_service` | extension service | Confirmed | hwservice context |

### 12.3 Service and property contexts

| Context Type | Name | Context Label | Role | Confidence | Notes |
|---|---|---|---|---|---|---|
| hwservice_contexts | `vendor.fpsensor.hardware.fpsensorhidlsvc::IFpsensorHidlSvc` | `u:object_r:fp_ext_svc2_service:s0` | vendor extension HIDL service | Confirmed | active declaration |
| hwservice_contexts | `vendor.mediatek.hardware.biometrics.fingerprint::ITranBiometricsFingerprint` | `u:object_r:hal_fingerprint_hwservice:s0` | dormant/alternate fingerprint HAL | Confirmed | no matching binary found in dump |
| hwservice_contexts | `vendor.silead.hardware.fingerprintext::ISileadFingerprint` | `u:object_r:hal_fingerprint_hwservice:s0` | alternate fingerprint HAL | Confirmed | dormant in this dump |
| service_contexts | `com.goodix.FingerprintService` | `u:object_r:goodix_fingerprint_service:s0` | commented-out legacy service | Confirmed | not active |
| property_contexts | `persist.vendor.goodix.dump_data` and related keys | `u:object_r:vendor_fingerprint_prop:s0` | vendor debug/calibration props | Confirmed | vendor namespace only |
| property_contexts | `vendor.silead.fp.ext.` | `u:object_r:vendor_silead_fp_prop:s0` | Silead extension props | Confirmed | vendor namespace only |

### 12.4 Enforcing-mode risks
- wrong file label on the daemon binary
- missing access to `/dev/fpsensor`
- missing access to `/sys/kernel/tran_fp/vendor_name`
- missing access to `uhid_device` or `silead_fpd_device`
- failure to register `fp_ext_svc2_service`

### 12.5 SELinux action items
- keep `hal_fingerprint_default` transition and entrypoint rules
- keep `fpsensor_fp_device`, `biometric_device`, `m_bio_misc_device`, and `sysfs_fp_name_path` labels
- keep `fp_ext_svc2_service` hwservice context
- preserve the allow rules for `uhid_device` and the vendor-specific fingerprint device types

---

## 13. Property Contract

### 13.1 Property inventory

| Property | Category | Default / Observed Value | Producer | Consumer | Trigger Role | Required | Confidence | Notes |
|---|---|---|---|---|---|---|---|---|
| `ro.fingerprint_support` | capability toggle | `1` | product build props | framework/UI | feature gating | yes | Confirmed | stock feature flag |
| `ro.side_fingerprint_support` | capability toggle | `1` | product build props | framework/UI | feature gating | yes | Confirmed | indicates side sensor |
| `ro.fingerprint_wakeup_performance_opt` | performance tuning | `1` | product build props | vendor UI/framework | tuning | unknown | Confirmed | likely wake optimization |
| `ro.os_fingerprint_incallrecord_support` | feature toggle | `1` | product build props | vendor UI | UX integration | unknown | Confirmed | call UI integration |
| `ro.os_fingerprint_dismissalarm_support` | feature toggle | `1` | product build props | vendor UI | UX integration | unknown | Confirmed | alarm dismissal |
| `ro.os_fingerprint_reset_password_support` | feature toggle | `1` | product build props | vendor UI | UX integration | unknown | Confirmed | password reset flow |
| `ro.os_fingerprint_answer_call_support` | feature toggle | `1` | product build props | vendor UI | UX integration | unknown | Confirmed | call answer flow |
| `ro.os_fingerprint_take_photo_support` | feature toggle | `1` | product build props | vendor UI | UX integration | unknown | Confirmed | camera shutter mapping |
| `persist.vendor.goodix.dump_data` | debug | unset | vendor / debug tooling | Goodix path | diagnostics | unknown | Confirmed | present in property_contexts only |
| `persist.vendor.sys.fp.fod.location.X_Y` | calibration | unset | vendor / debug tooling | Goodix path | diagnostics | unknown | Confirmed | FOD naming only; not proof of active FOD hardware |
| `persist.vendor.fp.sensorUid` | identification | unset | vendor / debug tooling | vendor ext | diagnostics | unknown | Confirmed | generic fingerprint namespace |
| `persist.vendor.transsion.auto_test` | test/debug | unset | vendor / factory tooling | vendor ext | diagnostics | unknown | Confirmed | Transsion fingerprint namespace |

### 13.2 Property categories
- identification
- capability toggle
- debug
- calibration
- transport mode
- startup gating
- performance tuning
- diagnostics

### 13.3 Dangerous or misleading properties
- `ro.fingerprint_support=1` can make the framework expose fingerprint UI even if the kernel node or SELinux is broken
- `ro.side_fingerprint_support=1` can mislead debugging if the active silicon is actually a different vendor family
- Goodix/FOD properties exist in policy but are not proof of a Goodix sensor on this unit

### 13.4 Minimal property set
Minimum properties that should be preserved for stock-like bring-up:
- `ro.fingerprint_support=1`
- `ro.side_fingerprint_support=1`
- `ro.fingerprint_wakeup_performance_opt=1` if the UI expects wake tuning

---

## 14. Configuration Surface

### 14.1 Config file analysis
- `android.hardware.biometrics.fingerprint@2.1-service.rc` controls daemon startup and boot ordering
- `vendor.fpsensor.rc` controls permissions on `/dev/fpsensor`
- `init.sensor_1_0.rc` controls shared sensor node permissions and likely supports biometric sideband behavior
- `manifest.xml` and the service fragment declare the runtime HAL contract
- `vendor_file_contexts`, `vendor_hwservice_contexts`, and `vendor_property_contexts` define the security and property namespace surfaces

### 14.2 Critical configuration table

| Config File | Critical Fields / Keys | Must Match Hardware | Safe to Modify | Source / Blob / Overlay | Confidence | Notes |
|---|---|---|---|---|---|---|---|
| `vendor/etc/init/android.hardware.biometrics.fingerprint@2.1-service.rc` | service path, `vendor.fps_hal`, `class late_start` | yes | no | stock init rc | Confirmed | startup contract |
| `vendor/etc/init/vendor.fpsensor.rc` | `/dev/fpsensor` mode/owner | yes | no | stock init rc | Confirmed | node access contract |
| `vendor/etc/init/hw/init.sensor_1_0.rc` | `/dev/biometric`, `/dev/m_bio_misc`, `/sys/class/sensor/m_bio_misc/*` | yes | no | stock init rc | Confirmed | adjacent biometric sensor surface |
| `vendor/etc/vintf/manifest/android.hardware.biometrics.fingerprint@2.1-service.xml` | HAL name/version/interface/instance | yes | no | stock manifest | Confirmed | main contract |
| `vendor/etc/vintf/manifest.xml` | `vendor.fpsensor.hardware.fpsensorhidlsvc` | yes | no | stock manifest | Confirmed | vendor extension contract |
| `vendor/etc/permissions/android.hardware.fingerprint.xml` | `android.hardware.fingerprint` feature | yes | yes | stock permissions XML | Confirmed | framework feature gate |
| `product/etc/build.prop` | `ro.fingerprint_support`, `ro.side_fingerprint_support` | yes | yes | product property overlay | Confirmed | UX / framework gating |
| `vendor/etc/selinux/vendor_file_contexts` | node labels | yes | no | stock file_contexts | Confirmed | enforcing-mode critical |

### 14.3 Config-level failure modes
- wrong route or device-node names in init rc
- missing `late_start` can race `/data`
- missing feature XML can hide fingerprint support from apps even if HAL works
- wrong file label can block daemon startup in enforcing mode

---

## 15. Kernel Coupling

### 15.1 Driver / module overview
No fingerprint kernel module was identified in the partition dump. The user-space stack clearly expects a kernel driver exposing `/dev/fpsensor`, `/sys/kernel/tran_fp/vendor_name`, and related biometric nodes. That strongly suggests either a built-in driver or a kernel module not present in the extracted partitions.

### 15.2 Kernel module table

| Module / Driver | File Path / Config | Built-in or LKM | Probe Dependency | Firmware Request | User-space Consumer | Required | Confidence | Notes |
|---|---|---|---|---|---|---|---|---|
| fingerprint vendor driver | not found | unknown | must create `/dev/fpsensor` and `/sys/kernel/tran_fp/vendor_name` | unknown | fingerprint HAL blobs | yes | Weak inference | exact module name not visible |
| biometric sensor misc driver | not found | unknown | must create `/dev/biometric`, `/dev/m_bio_misc` | unknown | `init.sensor_1_0.rc` / HAL blobs | likely | Strong inference | adjacent shared sensor path |

### 15.3 Module load order
- no `modules.load` evidence found
- no softdeps or module aliases were found
- runtime ordering is therefore unknown from this dump

### 15.4 Device tree / DTBO / board config clues
- no DT/DTBO evidence was inspected in this dump
- board-level fingerprint GPIO/power/reset wiring is not directly visible here

---

## 16. Bring-Up Checklist, Failure Modes, and Verdict

### 16.1 Minimal required artifact summary
Keep these for first boot with fingerprint:
- `/vendor/bin/hw/android.hardware.biometrics.fingerprint@2.1-service`
- `/vendor/lib64/android.hardware.biometrics.fingerprint@2.1.so`
- `/vendor/lib64/hw/fpsensor_fingerprint.default.so`
- `/vendor/lib64/vendor.fpsensor.hardware.fpsensorhidlsvc@2.0.so`
- `/vendor/lib64/libfp_ext_svc2.so`
- `/vendor/lib64/libMcClient.so`
- `/vendor/lib64/vendor.mediatek.hardware.mtkpower@1.0.so`
- `/vendor/etc/init/android.hardware.biometrics.fingerprint@2.1-service.rc`
- `/vendor/etc/init/vendor.fpsensor.rc`
- `/vendor/etc/init/hw/init.sensor_1_0.rc`
- `/vendor/etc/vintf/manifest/android.hardware.biometrics.fingerprint@2.1-service.xml`
- `/vendor/etc/vintf/manifest.xml` fingerprint fragment
- `/vendor/etc/permissions/android.hardware.fingerprint.xml`
- `ro.fingerprint_support=1`
- `ro.side_fingerprint_support=1`
- SELinux labels and allow rules for `/dev/fpsensor`, `/dev/biometric`, `/dev/m_bio_misc`, and `/sys/kernel/tran_fp`

### 16.2 Bring-up checklist
- verify `/dev/fpsensor` exists and is labeled `fpsensor_fp_device`
- verify `/sys/kernel/tran_fp/vendor_name` exists and returns a supported vendor string
- verify `vendor.fps_hal` starts in `late_start`
- verify `IBiometricsFingerprint/default` registers in `lshal`
- verify `vendor.fpsensor.hardware.fpsensorhidlsvc/default` registers if the extension path is needed
- verify `android.hardware.fingerprint` feature is present to the framework
- verify enrollment and unlock in Settings/lockscreen
- verify no SELinux denials on the fingerprint path

### 16.3 Failure-mode table

| Symptom | Likely Cause | Evidence | Mitigation | Confidence |
|---|---|---|---|---|
| HAL service starts but fingerprint UI never appears | missing feature XML or fingerprint props | `android.hardware.fingerprint.xml`, `ro.fingerprint_support` | copy feature XML and props | Confirmed |
| service crashes or never starts | wrong binary label / path mismatch | `vendor_file_contexts` vs init rc path naming | reconcile file_contexts and installed filename | Confirmed |
| service starts but cannot open node | missing `/dev/fpsensor` perms or label | rc + file_contexts + sepolicy | replicate node owner/mode and labels | Confirmed |
| enrollment/authentication fail silently | missing backend blob or wrong vendor selection | wrapper strings, `/sys/kernel/tran_fp/vendor_name` | keep stock blobs and kernel node | Strong inference |
| vendor extension API not available | `fp_ext_svc2_service` missing | `vendor_hwservice_contexts`, `vendor_sepolicy.cil` | ship `libfp_ext_svc2.so` and the HIDL service | Confirmed |
| fingerprint wake features do not work | missing perf / vendor props | `ro.fingerprint_wakeup_performance_opt`, MTK power helper | preserve product props and MTK power blob | Strong inference |

### 16.4 Final verdict on difficulty/risk
- **Difficulty:** medium-high
- **Risk:** medium
- **Why:** the visible Android HAL is straightforward, but the real implementation is a proprietary multi-blob wrapper with vendor extension service, kernel node dependencies, and strict SELinux/init coupling
- **Bottom line:** reuse the stock fingerprint stack first; replacing it is a later project, not a bring-up shortcut
