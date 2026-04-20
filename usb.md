# USB Firmware Analysis Report

## 1. Document Control
| Field | Value |
|---|---|
| Service / Subsystem | USB |
| Device Codename | X670-GL / X670 (weak inference from dump path) |
| Marketing Name | Infinix Note 12 (weak inference from dump path) |
| SoC / Platform | MediaTek MT6781 |
| Board / Hardware Variant | Infinix X670-GL; MTK `musb-hdrc` gadget stack |
| Firmware Build ID | `ro.vendor.build.fingerprint=Infinix/X670-GL/Infinix-X670:12/SP1A.210812.016/240224V150:user/release-keys`; `ro.system.build.fingerprint=Infinix/TSSI/FULL-64:13/TP1A.220624.014/240224V142:user/release-keys` |
| Android Version | mixed: vendor 12 / framework 13 (API 33) |
| Vendor Security Patch Level | 2024-02-05 |
| Kernel Version | not directly inspected |
| Report Version | 1.0 |
| Author | OpenCode |
| Date | 2026-04-20 |
| Analysis Scope | stock firmware dump / extracted partitions |
| Confidence Level | Medium |
| Status | Draft |

---

## 2. Executive Summary

### 2.1 What this service does
**Confirmed:** this device exposes Android USB gadget and host support through a vendor USB HAL, a framework-side USB gadget daemon, configfs/functionfs, and a large vendor init state machine. It covers normal USB modes (`adb`, `mtp`, `ptp`, `rndis`, `accessory`, `midi`, `audio_source`) plus vendor-specific modem/rawbulk and factory modes.

### 2.2 Stock implementation summary
**Confirmed:** the stock implementation is split across:
- `/vendor/bin/hw/android.hardware.usb@1.2-service-mediatekv2`, a vendor HIDL HAL that registers `android.hardware.usb::IUsb/default` and `android.hardware.usb.gadget::IUsbGadget/default`.
- `/system/bin/usbd`, a source-built AOSP daemon that drives USB gadget function switching and talks to the gadget HAL.
- `vendor/etc/init/hw/init.mt6781.usb.rc`, which builds the configfs gadget tree under `/config/usb_gadget/g1`, mounts FunctionFS, sets MTK-specific properties, and wires many composite USB modes.
- Standard AOSP USB init files in `/system/etc/init/hw/init.usb.rc` and `/system/etc/init/hw/init.usb.configfs.rc`.

### 2.3 Bring-up significance
- **Bring-up Priority:** Major
- **Expected ROM impact if broken:** no adb/MTP/USB host enumeration, broken accessory/audio/RNDIS/factory USB modes, but the device can still boot
- **AOSP dependency type:** mixed
- **Treble relevance:** yes

### 2.4 Final recommendation summary
- **Recommended implementation path:** reuse stock vendor blobs and stock USB init/SELinux glue
- **Major blockers:** vendor HAL registration, configfs/functionfs setup, type-c / role-switch sysfs availability, SELinux, ueventd permissions
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
USB gadget HAL, `usbd`, AOSP USB init, MTK vendor USB init, VINTF, feature XMLs, USB audio policy, SELinux, properties, ueventd permissions, sysfs/proc/configfs paths, and kernel-facing USB nodes.

### 3.2 Explicitly excluded
Camera, fingerprint, sensors, radio, and unrelated vendor services except where USB depends on them (for example rawbulk modem USB and USB audio).

### 3.3 Adjacent subsystems
`adbd`, Type-C / role-switch logic, USB audio, RNDIS, mass-storage, accessory mode, modem rawbulk, factory/testmode paths, SELinux, kernel gadget/function drivers.

---

## 4. Source Evidence

### 4.1 Firmware source
- Firmware package: extracted stock partition tree
- Region / carrier: not directly identified
- Extraction method: static filesystem analysis only
- Image formats observed: ELF, rc, XML, prop, ogg, CIL
- Integrity notes: no runtime logs; conclusions are static only

### 4.2 Partitions examined

| Partition | Mount Path | Relevant to Service | Notes |
|---|---|---:|---|
| boot / init_boot / vendor_boot | boot images | no | not directly inspected |
| vendor | `/vendor` | yes | vendor HAL, vendor init, vendor properties, vendor SELinux, manifest |
| system | `/system` | yes | `usbd`, generic USB init, framework libs, permissions, SELinux |
| system_ext | `/system_ext` | yes | USB audio policy config |
| product | `/product` | yes | `usb_effect.ogg` only; optional |
| odm | `/odm` | low | only `persist.sys.usb.config=none` found in build prop |
| vendor_dlkm | `/vendor_dlkm` | low | only `persist.sys.usb.config=none` found in build prop |
| odm_dlkm | `/odm_dlkm` | low | only `persist.sys.usb.config=none` found in build prop |
| system_dlkm | `/system_dlkm` | no | no USB-specific evidence found |

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
- sysfs/proc/configfs references

### 4.4 Confidence grading rules
- **Confirmed:** direct evidence from files or strings
- **Strong inference:** multiple converging clues
- **Weak inference:** plausible but not runtime-validated

---

## 5. Service Identity and AOSP Contract

### 5.1 Android-facing role
Android expects a USB stack that can expose gadget functions to the host, manage role switching, and advertise USB host/accessory features to apps. On this device that includes normal phone USB modes, adb over FunctionFS, USB host access, and MTK-specific factory/rawbulk paths.

### 5.2 Interface model
- **Interface type:** mixed
- **Framework entry points:** `android.hardware.usb::IUsb`, `android.hardware.usb.gadget::IUsbGadget`, `usbd`
- **Expected service names:** `android.hardware.usb.IUsb/default`, `android.hardware.usb.gadget::IUsbGadget/default`, `usbd`
- **Expected instances:** `default`
- **Binder domain:** mixed (`hwbinder` for HAL, framework property/service control through init)

### 5.3 HAL / service contract summary
**Confirmed:** the vendor HAL binary registers both USB HAL families. Strings show `registerAsService` for `android.hardware.usb@1.3::IUsb` and `android.hardware.usb.gadget@1.1::IUsbGadget`; VINTF declares `android.hardware.usb` version `1.3` and `android.hardware.usb.gadget` version `1.1` with `default` instances.

**Confirmed:** the framework-side `usbd` daemon is AOSP source-built (`system/core/usbd/usbd.cpp` string), links only the gadget HIDL shim, and contains control-flow strings for `persist.sys.usb.config`, `sys.usb.config`, `sys.usb.controller`, `vendor.usb.config`, `setCurrentUsbFunctions`, `Usb HAL not found`, and `Error while invoking usb hal`.

**Strong inference:** the device uses `usbd` as the policy/bridge daemon for user-facing USB function switching, while the vendor HAL owns the low-level role-switch and configfs binding.

### 5.4 Compatibility and Treble notes
- VINTF manifest needed: yes
- Compatibility matrix implications: system matrices reference both `android.hardware.usb` and `android.hardware.usb.gadget` across multiple FCM levels
- Lazy service behavior: not shown; the HAL is a normal init service, not a lazy one
- Passthrough vs binderized: binderized / `hwbinder`
- Same-process HAL/SP-HAL concerns: no direct evidence

---

## 6. Filesystem Inventory

### 6.1 Executables and daemons

| Path | Binary Name | Purpose | Arch | SELinux Label | Trigger / Service Name | Confidence | Notes |
|---|---|---|---|---|---|---|---|---|
| `vendor/bin/hw/android.hardware.usb@1.2-service-mediatekv2` | `android.hardware.usb@1.2-service-mediatekv2` | vendor USB HAL for device + gadget role switch | ELF 64-bit ARM64 PIE, Android 31 | `u:object_r:mtk_hal_usb_exec:s0` | `vendor.usb-hal-1-2` / `class hal` | Confirmed | `[extract proprietary unchanged]`; HIDL `IUsb` + `IUsbGadget` service binary |
| `system/bin/usbd` | `usbd` | framework USB gadget daemon / function-switch broker | ELF 64-bit ARM64 PIE, Android 33 | `u:object_r:usbd_exec:s0` -> `usbd` domain | `service usbd` / `class late_start` / `oneshot` | Confirmed | `[source-build]`; system-side client of USB gadget HAL |
| `system/bin/adbd` | `adbd` | adb daemon started by USB property triggers | not inspected here | generic AOSP service | `service adbd` / `class core` / `disabled` | Strong inference | standard dependency of `sys.usb.config=adb` paths |

### 6.2 Shared libraries / proprietary blobs

| Path | Library | Role | Loaded By | Key Dependencies | Namespace Risk | Confidence | Notes |
|---|---|---|---|---|---|---|---|---|
| `vendor/lib64/android.hardware.usb@1.0.so`, `@1.1.so`, `@1.2.so`, `@1.3.so` | USB HAL interface libs | HIDL USB interface support | vendor HAL binary | `libbase.so`, `libhidlbase.so`, `libhardware.so`, `liblog.so`, `libutils.so` (via HAL binary) | low | Confirmed | `[extract proprietary unchanged]`; vendor-shipped interface stack |
| `vendor/lib64/android.hardware.usb.gadget@1.0.so`, `@1.1.so` | USB gadget interface libs | HIDL gadget support | vendor HAL binary | same as above (via HAL binary) | low | Confirmed | `[extract proprietary unchanged]` |
| `system/lib64/android.hardware.usb.gadget@1.0.so` | gadget shim | framework-side gadget HIDL helper | `usbd` | `libbase.so`, `libhidlbase.so`, `libhardware.so`, `liblog.so`, `libutils.so` | low | Confirmed | `[source-build]` |
| `system/lib/libusbhost.so`, `system/lib64/libusbhost.so` | USB host helper | framework USB host enumeration / accessory helper | framework components | standard system libs | low | Confirmed | `[source-build]` |
| `system/lib/libusb1.0.so` | USB host/libusb helper | user-space USB host access | framework components | standard system libs | low | Confirmed | `[source-build]` |

### 6.3 Config files

| Path | Format | Consumed By | Critical Keys | Overlayable | Confidence | Notes |
|---|---|---|---|---|---|---|---|
| `vendor/etc/init/hw/init.mt6781.usb.rc` | rc | init | configfs tree, function creation, `sys.usb.config` routes, MTK vendor props | no | Confirmed | `[extract proprietary unchanged]`; main USB bring-up script |
| `vendor/etc/init/android.hardware.usb@1.2-service-mediatekv2.rc` | rc | init | service `vendor.usb-hal-1-2`, `class hal`, group list | no | Confirmed | `[extract proprietary unchanged]` |
| `vendor/etc/vintf/manifest/android.hardware.usb@1.2-service-mediatekv2.xml` | XML | VINTF/hwservicemanager | `android.hardware.usb` 1.3, `android.hardware.usb.gadget` 1.1 | no | Confirmed | `[extract proprietary unchanged]` |
| `system/etc/init/hw/init.usb.rc` | rc | init | generic `adbd`, fallback configfs-less USB, Type-C properties | no | Confirmed | `[source-build]` |
| `system/etc/init/hw/init.usb.configfs.rc` | rc | init | generic configfs gadget routes | no | Confirmed | `[source-build]` |
| `system/etc/init/usbd.rc` | rc | init | `usbd` daemon definition | no | Confirmed | `[source-build]` |
| `vendor/etc/permissions/android.hardware.usb.host.xml` | XML | PackageManager | feature `android.hardware.usb.host` | yes | Confirmed | `[extract proprietary unchanged]` |
| `vendor/etc/permissions/android.hardware.usb.accessory.xml` | XML | PackageManager | feature `android.hardware.usb.accessory` | yes | Confirmed | `[extract proprietary unchanged]` |
| `system/etc/permissions/com.android.future.usb.accessory.xml` | XML | PackageManager | library `com.android.future.usb.accessory.jar` | yes | Confirmed | `[source-build]` |
| `system_ext/etc/usb_audio_policy_configuration.xml` | XML | AudioPolicy | USB audio routes and ports | yes | Confirmed | `[source-build]` |
| `vendor/etc/usb_audio_policy_configuration.xml` | XML | AudioPolicy | USB audio routes and ports | yes | Confirmed | `[extract proprietary unchanged]` |
| `vendor/etc/usb_audio_accessory_only_policy_configuration.xml` | XML | AudioPolicy | accessory-only USB audio route | yes | Confirmed | `[extract proprietary unchanged]` |

### 6.4 APK / JAR / APEX / framework packages

| Path / Package | Type | Purpose | Privileged | Permissions / Features | Confidence | Notes |
|---|---|---|---|---|---|---|---|
| `system/framework/com.android.future.usb.accessory.jar` | JAR | legacy USB accessory API | no | `com.android.future.usb.accessory` library declaration | Confirmed | `[source-build]`; exposed by `com.android.future.usb.accessory.xml` |
| `vendor/etc/permissions/android.hardware.usb.host.xml` | feature XML | host mode capability flag | no | `android.hardware.usb.host` | Confirmed | framework-visible capability gate |
| `vendor/etc/permissions/android.hardware.usb.accessory.xml` | feature XML | accessory mode capability flag | no | `android.hardware.usb.accessory` | Confirmed | framework-visible capability gate |

### 6.5 Firmware assets / DSP / microcode / calibration

| Path | Asset Type | Loaded By | Hardware Target | Required for Bring-up | Confidence | Notes |
|---|---|---|---|---|---|---|---|
| `product/media/audio/ui/usb_effect.ogg` | UI sound | framework/audio UI | USB connect/disconnect effect | no | Confirmed | optional polish only |

---

## 7. Init Integration

### 7.1 Relevant init fragments
- `vendor/etc/init/hw/init.mt6781.rc` (imports `${ro.vendor.rc}init.mt6781.usb.rc`)
- `vendor/etc/init/hw/init.mt6781.usb.rc`
- `vendor/etc/init/android.hardware.usb@1.2-service-mediatekv2.rc`
- `system/etc/init/hw/init.rc` (imports `/system/etc/init/hw/init.usb.rc` and `/system/etc/init/hw/init.usb.configfs.rc`)
- `system/etc/init/hw/init.usb.rc`
- `system/etc/init/hw/init.usb.configfs.rc`
- `system/etc/init/usbd.rc`

### 7.2 Service definitions

| RC File | Service Name | Command | Class | User/Group | Capabilities | Disabled/Oneshot | Interface Declaration | Confidence | Notes |
|---|---|---|---|---|---|---|---|---|---|
| `vendor/etc/init/android.hardware.usb@1.2-service-mediatekv2.rc` | `vendor.usb-hal-1-2` | `/vendor/bin/hw/android.hardware.usb@1.2-service-mediatekv2` | `hal` | `root` / `root system shell mtp` | none shown | enabled | HIDL `IUsb` + `IUsbGadget` via binary | Confirmed | vendor USB HAL service |
| `system/etc/init/usbd.rc` | `usbd` | `/system/bin/usbd` | `late_start` | `root` / `root usb system` | none shown | `oneshot` | service_manager / hwservice client | Confirmed | framework USB gadget broker |

### 7.3 Trigger paths
- **Confirmed:** `vendor/etc/init/hw/init.mt6781.rc` imports the device USB rc file during boot.
- **Confirmed:** `early-init` writes `/sys/module/musb_hdrc/parameters/kernel_init_done 1`.
- **Confirmed:** `post-fs` creates `/dev/usb-ffs`, `/dev/usb-ffs/adb`, and the full `/config/usb_gadget/g1` tree, then mounts `functionfs` for `adb`, `mtp`, and `ptp`.
- **Confirmed:** `on boot` sets `sys.usb.configfs=1`, `vendor.usb.controller="musb-hdrc"`, and initializes vendor USB state props.
- **Confirmed:** `on charger` builds a HID-only gadget and sets `sys.usb.config=hid`.
- **Confirmed:** `vendor.usb.config=*` is bridged to `sys.usb.config=*`.
- **Confirmed:** the vendor rc owns the real `sys.usb.config` state machine for `adb`, `mtp`, `ptp`, `rndis`, `accessory`, `audio_source`, `midi`, `via_bypass`, `mass_storage`, `bicr`, and combined variants.
- **Confirmed:** generic system rc files start `adbd` when `sys.usb.config` is `adb`, `mtp,adb`, `ptp,adb`, `accessory,adb`, `audio_source,adb`, `midi,adb`, `rndis,adb`, and similar.

### 7.4 Init writes and side effects
- `write /sys/module/musb_hdrc/parameters/kernel_init_done 1`
- `setprop vendor.usb.vid "0x0E8D"`
- `setprop sys.usb.configfs 1`
- `setprop vendor.usb.controller "musb-hdrc"`
- `setprop vendor.usb.acm_cnt 0`
- `setprop vendor.usb.acm_port0 ""`
- `setprop vendor.usb.acm_port1 ""`
- `setprop vendor.usb.acm_enable 0`
- `write /sys/class/android_usb/android0/f_mtp/cpu_mask 0xF0`
- `write /sys/module/usb_f_mtp/parameters/mtp_rx_cont 1`
- `chmod/chown` on `/sys/class/typec/port0/*`, `/sys/class/android_usb/android0/iSerial`, `/sys/class/usb_rawbulk/*`, `/dev/ttyGS0-3`
- `mount functionfs` for `adb`, `mtp`, `ptp`
- `write /config/usb_gadget/g1/*` for IDs, strings, functions, and UDC binding
- `write /proc/mtk_usb/testmode` and `/proc/sys/kernel/printk` for debug paths

### 7.5 Boot ordering notes
The gadget tree is created very early, before the USB HAL and `usbd` are useful. `sys.usb.configfs=1` is set on boot, so the device is intended to use configfs mode all the time; the generic non-configfs fallback in `init.usb.rc` is mostly a safety net.

---

## 8. VINTF / Manifest Analysis

### 8.1 Manifest sources
- `vendor/etc/vintf/manifest/android.hardware.usb@1.2-service-mediatekv2.xml`
- `system/etc/vintf/compatibility_matrix.3.xml`
- `system/etc/vintf/compatibility_matrix.4.xml`
- `system/etc/vintf/compatibility_matrix.5.xml`
- `system/etc/vintf/compatibility_matrix.6.xml`
- `system/etc/vintf/compatibility_matrix.7.xml`

### 8.2 HAL declarations

| Manifest File | Format | Package | Interface | Version | Instance / FQName | Transport | Optional? | Confidence | Notes |
|---|---|---|---|---|---|---|---|---|---|
| `vendor/etc/vintf/manifest/android.hardware.usb@1.2-service-mediatekv2.xml` | hidl | `android.hardware.usb` | `IUsb` | 1.3 | `default` | `hwbinder` | no | Confirmed | vendor USB HAL |
| `vendor/etc/vintf/manifest/android.hardware.usb@1.2-service-mediatekv2.xml` | hidl | `android.hardware.usb.gadget` | `IUsbGadget` | 1.1 | `default` | `hwbinder` | no | Confirmed | vendor USB gadget HAL |

### 8.3 Compatibility observations
- FCM / target-level clues: framework is Android 13 (`ro.build.version.sdk=33`), vendor image is Android 12
- Deprecated interface risk: HIDL-only USB stack, no AIDL USB HAL evidence here
- Multiple instances or vendor forks: only `default` instances are declared, but vendor-specific property/state handling is extensive
- Need to copy stock manifest fragment: yes

### 8.4 Registration path
The vendor HAL binary itself registers the HIDL instances. `hwservicemanager` sees the `hal_usb_hwservice` / `hal_usb_gadget_hwservice` names, while init launches the executable from the vendor rc file.

---

## 9. Binary Analysis

### 9.1 Main binary inventory
- `vendor/bin/hw/android.hardware.usb@1.2-service-mediatekv2` is a 64-bit PIE ARM64 binary for Android 31. `readelf -d` shows it depends on `android.hardware.usb@1.0.so`, `@1.1.so`, `@1.2.so`, `@1.3.so`, `android.hardware.usb.gadget@1.0.so`, `@1.1.so`, `libbase.so`, `libcutils.so`, `libhardware.so`, `libhidlbase.so`, `liblog.so`, `libutils.so`, `libc++.so`, `libc.so`, `libm.so`, and `libdl.so`.
- `strings` show `registerAsService`, `IUsbCallback`, `IUsbGadget`, `typec`, `usb_role_switch`, `/sys/class/typec/`, `/sys/class/usb_role/`, `/config/usb_gadget/g1/UDC`, `vendor.usb.config`, `vendor.usb.ffs.mtp.ready`, `vendor.usb.ffs.ptp.ready`, `not suport typec interface`, `No device in /sys/class/typec`, `Failed to open /sys/class/typec`, `Role switch failed while wrting to file`, and `Error while invoking usb hal`.
- `[extract proprietary unchanged]`

- `system/bin/usbd` is a 64-bit PIE ARM64 binary for Android 33. `readelf -d` shows it depends on `android.hardware.usb.gadget@1.0.so`, `libbase.so`, `libhidlbase.so`, `liblog.so`, `libutils.so`, `libhardware.so`, `libc++.so`, `libc.so`, `libm.so`, and `libdl.so`.
- `strings` show `system/core/usbd/usbd.cpp`, `persist.sys.usb.config`, `setCurrentUsbFunctions`, `Usb HAL not found`, `Error while invoking usb hal`, `Signal MTP to enable default functions`, `vendor.usb.config`, `sys.usb.controller`, `/sys/class/typec`, `/sys/class/usb_role/`, and `hal_usb_gadget_client`-style control flow.
- `[source-build]`

### 9.2 Dependency table

| Binary / Library | DT_NEEDED | Suspected `dlopen()` Targets | Cross-Partition Dependencies | Missing Symbol Risk | Confidence | Notes |
|---|---|---|---|---|---|---|---|---|
| `vendor/bin/hw/android.hardware.usb@1.2-service-mediatekv2` | `android.hardware.usb@1.0.so`, `@1.1.so`, `@1.2.so`, `@1.3.so`, `android.hardware.usb.gadget@1.0.so`, `@1.1.so`, `libbase.so`, `libcutils.so`, `libhardware.so`, `libhidlbase.so`, `liblog.so`, `libutils.so`, `libc++.so`, `libc.so`, `libm.so`, `libdl.so` | none evidenced | vendor USB HAL libs, configfs/functionfs sysfs | high | Confirmed | vendor HAL is tightly coupled to stock vendor USB libraries |
| `system/bin/usbd` | `android.hardware.usb.gadget@1.0.so`, `libbase.so`, `libhidlbase.so`, `liblog.so`, `libutils.so`, `libhardware.so`, `libc++.so`, `libc.so`, `libm.so`, `libdl.so` | none evidenced | vendor HAL registration via HIDL, system init rc, property service | medium | Confirmed | framework daemon is mostly system-side |

### 9.3 Linker namespace / VNDK analysis
- Uses public VNDK only: unknown
- Uses private platform libs: no direct evidence for the vendor HAL binary beyond the expected vendor/system split
- Requires shim library: no evidence
- SP-HAL concerns: none directly evidenced
- Namespace risk summary: the vendor HAL depends on multiple USB HIDL libs that must stay present in vendor/system partitions; `usbd` depends on the system gadget shim only

### 9.4 Important strings and symbols
- `android.hardware.usb@1.3.so`, `android.hardware.usb.gadget@1.1.so`
- `registerAsService`, `IUsb`, `IUsbGadget`, `IUsbCallback`
- `/config/usb_gadget/g1/UDC`
- `/sys/class/typec/`, `/sys/class/usb_role/`, `/sys/class/android_usb/android0/`
- `/dev/usb-ffs/adb`, `/dev/usb-ffs/mtp`, `/dev/usb-ffs/ptp`
- `vendor.usb.config`, `sys.usb.config`, `sys.usb.configfs`, `sys.usb.controller`, `sys.usb.state`
- `vendor.usb.ffs.mtp.ready`, `vendor.usb.ffs.ptp.ready`, `vendor.usb.acm_enable`, `vendor.usb.acm_cnt`
- `Usb HAL not found`, `Error while invoking usb hal`, `not suport typec interface`, `No device in /sys/class/typec`

### 9.5 Binary-level conclusions
This is a classic mixed USB stack: a vendor HIDL HAL owns the low-level gadget and type-c plumbing, while the AOSP `usbd` daemon handles higher-level function switching. The device is not relying on a pure AOSP generic USB implementation.

---

## 10. Device Nodes, Sysfs, Procfs, and IO Surface

### 10.1 Device nodes

| Path | Type | Created By | Ownership / Mode | SELinux Label | Consumer | Evidence | Required | Confidence | Notes |
|---|---|---|---|---|---|---|---|---|---|
| `/dev/bus/usb/*` | USB device nodes | kernel + ueventd | `0660 root usb` | not inspected | host-mode clients | `ueventd.rc` | yes | Confirmed | host enumeration access |
| `/dev/mtp_usb` | MTP node | kernel + ueventd | `0660 root mtp` | not inspected | MTP stack | `ueventd.rc` | yes | Confirmed | MTP function path |
| `/dev/usb_accessory` | accessory node | kernel + ueventd | `0660 root usb` | not inspected | accessory mode | `ueventd.rc` | yes | Confirmed | accessory app path |
| `/dev/usb-ffs/adb` | FunctionFS mount | init | `0770 shell shell` | not inspected | adbd | `init.mt6781.usb.rc` | yes | Confirmed | adb over FunctionFS |
| `/dev/usb-ffs/mtp` | FunctionFS mount | init | `0770 mtp mtp` | not inspected | MTP | `init.mt6781.usb.rc` | yes | Confirmed | MTP over FunctionFS |
| `/dev/usb-ffs/ptp` | FunctionFS mount | init | `0770 mtp mtp` | not inspected | PTP | `init.mt6781.usb.rc` | yes | Confirmed | PTP over FunctionFS |
| `/dev/ttyGS0`..`/dev/ttyGS3` | gadget serial TTYs | kernel + ueventd | `0660 system radio` | not inspected | ACM / modem-style vendor modes | `init.mt6781.usb.rc` | yes | Confirmed | vendor ACM stack |

### 10.2 Sysfs / procfs / configfs paths

| Path | Purpose | Read/Write | Referenced By | Required | Confidence | Notes |
|---|---|---|---|---|---|---|
| `/config/usb_gadget/g1/*` | configfs gadget tree | R/W | vendor init, generic init, vendor HAL strings | yes | Confirmed | central USB gadget surface |
| `/config/usb_gadget/g1/UDC` | binds gadget to controller | write | vendor init, generic init, HAL strings | yes | Confirmed | set to `musb-hdrc` via vendor props |
| `/config/usb_gadget/g1/functions/*` | gadget function instances | R/W | vendor init | yes | Confirmed | `ffs.adb`, `ffs.mtp`, `ffs.ptp`, `rndis.gs4`, `midi.gs5`, `acm.gs0-3`, `mass_storage.usb0`, `hid.gs0`, `accessory.gs2`, `audio_source.gs3`, `via_*` |
| `/config/usb_gadget/g1/configs/b.1/*` | composite gadget config | R/W | vendor init, system init | yes | Confirmed | function symlinks and configuration strings |
| `/sys/class/typec/port0/{power_role,data_role,port_type}` | Type-C role control | R/W | vendor HAL init rc, vendor HAL strings | yes | Confirmed | boot-time chmod/chown performed |
| `/sys/class/typec` / `/sys/class/typec/port0` | Type-C role status | R/W | vendor HAL / `usbd` strings | yes | Confirmed | `No device in /sys/class/typec` indicates hard dependency |
| `/sys/class/usb_role/` | USB role switch class | R/W | vendor HAL / `usbd` strings | yes | Strong inference | fallback/alternate role-switch path |
| `/sys/class/android_usb/android0/*` | legacy gadget control | R/W | vendor init | yes | Confirmed | `iSerial`, `f_mtp/cpu_mask`, etc |
| `/sys/class/usb_rawbulk/*/enable` | modem/rawbulk enable flags | R/W | vendor init | no for base USB | Confirmed | vendor modem USB modes |
| `/sys/devices/platform/mt_usb/saving` | MTK power/saving switch | write | vendor init | no for base USB | Confirmed | toggled for some composite modes |
| `/sys/module/musb_hdrc/parameters/kernel_init_done` | controller init flag | write | vendor init | yes | Confirmed | early-init write |
| `/sys/module/usb_f_mtp/parameters/mtp_rx_cont` | MTP behavior | write | vendor init | yes for MTP | Confirmed | MTP tuning |
| `/proc/mtk_usb/testmode` | USB test mode | write | vendor init | no | Confirmed | debug/factory only |
| `/proc/sys/kernel/printk` | kernel printk level | write | vendor init | no | Confirmed | debug path |

### 10.3 IOCTL / netlink / socket / binder clues
- `usbd` is a `hal_usb_gadget_client` in SELinux and finds `hal_usb_gadget_hwservice` over `hwservice_manager`.
- `usbd` and the vendor HAL both use HIDL binder/hwbinder registration and callbacks.
- Strings show `uevent_open_socket`, `uevent_init`, `DEVTYPE=typec_`, and `DEVTYPE=usb_role_switch`, so both components watch uevents and role-switch events.

### 10.4 Runtime path expectations
Working ROM must have `/config/usb_gadget/g1`, FunctionFS mounts for adb/MTP/PTP, valid Type-C or usb-role sysfs, and `musb_hdrc`/`mt_usb` controller nodes. Without those paths the vendor HAL cannot bind USB functions.

---

## 11. Ueventd and Permissions

### 11.1 `ueventd.rc` entries
- `/dev/bus/usb/*            0660   root       usb`
- `/dev/mtp_usb              0660   root       mtp`
- `/dev/usb_accessory        0660   root       usb`
- `/sys/devices/virtual/usb_composite/*   enable  0664  root   system`

### 11.2 Node permission model

| Node / Path | Owner | Group | Mode | Source File | Confidence | Notes |
|---|---|---|---|---|---|---|---|
| `/dev/bus/usb/*` | root | usb | 0660 | `system/etc/ueventd.rc` | Confirmed | host USB access |
| `/dev/mtp_usb` | root | mtp | 0660 | `system/etc/ueventd.rc` | Confirmed | MTP access |
| `/dev/usb_accessory` | root | usb | 0660 | `system/etc/ueventd.rc` | Confirmed | accessory access |
| `/sys/devices/virtual/usb_composite/*/enable` | root | system | 0664 | `system/etc/ueventd.rc` | Confirmed | legacy composite enable node |
| `/sys/class/typec/port0/*` | root | system | 0664 | `vendor/etc/init/android.hardware.usb@1.2-service-mediatekv2.rc` | Confirmed | HAL needs write access |
| `/dev/usb-ffs/adb` | shell | shell | 0770 | `vendor/etc/init/hw/init.mt6781.usb.rc` | Confirmed | FunctionFS mount |
| `/dev/usb-ffs/mtp`, `/dev/usb-ffs/ptp` | mtp | mtp | 0770 | `vendor/etc/init/hw/init.mt6781.usb.rc` | Confirmed | FunctionFS mounts |

### 11.3 Boot-created paths and symlinks
- `/dev/usb-ffs` and `/dev/usb-ffs/adb`
- `/config/usb_gadget/g1`
- `/config/usb_gadget/g1/strings/0x409`
- `/config/usb_gadget/g1/functions/*`
- `/config/usb_gadget/g1/configs/b.1/*`
- `/config/usb_gadget/g1/os_desc/b.1`
- permissions on `/sys/class/android_usb/android0/iSerial`
- `chmod a+x config/usb_gadget/g1` and `config/usb_gadget/g1/strings/0x409`

### 11.4 Risk summary
If these permissions are not replicated, adb can fail to mount FunctionFS, MTP cannot talk to the gadget, and the HAL may be unable to switch Type-C roles or bind the UDC. The result is often a silent USB failure rather than a boot failure.

---

## 12. SELinux Analysis

### 12.1 Process domains

| Process / Service | Executable Label | Domain | Starts From | Confidence | Notes |
|---|---|---|---|---|---|---|
| `vendor.usb-hal-1-2` | `u:object_r:mtk_hal_usb_exec:s0` | `mtk_hal_usb` | init via vendor rc | Confirmed | vendor-specific USB HAL domain |
| `usbd` | `u:object_r:usbd_exec:s0` | `usbd` | init via system rc | Confirmed | AOSP USB gadget daemon |

### 12.2 File and node labels

| Path / Node | Expected Label | Used By | Confidence | Notes |
|---|---|---|---|---|
| `/system/bin/usbd` | `u:object_r:usbd_exec:s0` | init | Confirmed | `plat_file_contexts` entry |
| `/vendor/bin/hw/android.hardware.usb@1.2-service-mediatekv2` | `u:object_r:mtk_hal_usb_exec:s0` | init | Confirmed | `vendor_file_contexts` wildcard for mediatek USB service |
| `/sys/class/typec/port0/*` | `sysfs` type | vendor HAL | Strong inference | boot rc explicitly chowns/chmods these nodes |
| `/config/usb_gadget/g1/*` | `configfs` | vendor HAL / `usbd` | Confirmed | `hal_usb_gadget_server` has configfs allow rules |

### 12.3 Service and property contexts

| Context Type | Name | Context Label | Role | Confidence | Notes |
|---|---|---|---|---|---|---|
| service_contexts | `android.hardware.usb.IUsb/default` | `u:object_r:hal_usb_service:s0` | framework-visible HIDL service | Confirmed | `plat_service_contexts` |
| hwservice_contexts | `android.hardware.usb::IUsb` | `u:object_r:hal_usb_hwservice:s0` | HIDL HW service | Confirmed | `plat_hwservice_contexts` |
| hwservice_contexts | `android.hardware.usb.gadget::IUsbGadget` | `u:object_r:hal_usb_gadget_hwservice:s0` | HIDL HW service | Confirmed | `plat_hwservice_contexts` |
| property_contexts | `sys.usb.config`, `sys.usb.configfs`, `sys.usb.controller`, `sys.usb.state` | `u:object_r:usb_control_prop:s0` | generic USB control | Confirmed | `plat_property_contexts` |
| property_contexts | `sys.usb.ffs.ready`, `sys.usb.ffs.mtp.ready` | `u:object_r:ffs_control_prop:s0` | FFS ready flags | Confirmed | `plat_property_contexts` |
| property_contexts | `sys.usb.ffs.aio_compat`, `sys.usb.ffs.max_read`, `sys.usb.ffs.max_write` | `u:object_r:ffs_config_prop:s0` | FFS tuning | Confirmed | `plat_property_contexts` |
| property_contexts | `vendor.usb.*`, `persist.vendor.usb.*`, `ro.vendor.usb.*` | `u:object_r:vendor_mtk_usb_prop:s0` | MTK vendor USB props | Confirmed | `vendor_property_contexts` |

### 12.4 Enforcing-mode risks
First failures are likely SELinux denials on `configfs`, `functionfs`, Type-C sysfs nodes, or `vendor.usb.*` property writes. If `mtk_hal_usb` loses access to `sysfs_usb_nonplat` or `usb_control_prop`, USB state changes break even if the daemon starts.

### 12.5 SELinux action items
- Keep `mtk_hal_usb_exec` -> `mtk_hal_usb` transition
- Keep `usbd_exec` -> `usbd` transition
- Keep `hal_usb_hwservice` and `hal_usb_gadget_hwservice` contexts
- Keep `mtk_hal_usb` allows for `sysfs_usb_nonplat`, `configfs`, `functionfs`, `usb_control_prop`, and `vendor_mtk_usb_prop`
- Keep `hal_usb_gadget_client` access for `system_server` and `usbd`

---

## 13. Property Contract

### 13.1 Property inventory

| Property | Category | Default / Observed Value | Producer | Consumer | Trigger Role | Required | Confidence | Notes |
|---|---|---|---|---|---|---|---|---|
| `persist.sys.usb.config` | startup gating | `none` | build props | init / `usbd` | default USB mode | yes | Confirmed | set in `vendor/build.prop`, `odm*.build.prop` |
| `sys.usb.configfs` | transport mode | `1` | init | vendor rc / system rc / `usbd` | selects configfs path | yes | Confirmed | set on boot by vendor rc |
| `vendor.usb.controller` | identification | `musb-hdrc` | init | vendor rc | UDC binding | yes | Confirmed | device controller name |
| `vendor.usb.vid` | identification | `0x0E8D` | init | vendor rc | gadget VID | yes | Confirmed | MTK VID |
| `vendor.usb.pid` | identification | mode-dependent | init | vendor rc | gadget PID | yes | Confirmed | set per USB mode |
| `vendor.usb.acm_cnt` | capability toggle | `0/1/2` | init/vendor | vendor rc | selects ACM layout | no for base USB | Confirmed | affects product IDs and function layout |
| `vendor.usb.acm_port0` / `vendor.usb.acm_port1` | capability toggle | empty string | init/vendor | vendor rc | selects ACM function names | no for base USB | Confirmed | vendor modem modes |
| `vendor.usb.acm_enable` | capability toggle | `0/1` | init/vendor | vendor rc | enables ACM composition | no for base USB | Confirmed | gates extra ACM symlinks |
| `sys.usb.state` | status | set to current config | init | framework/UI | state reporting | yes | Confirmed | set after gadget bind |
| `sys.usb.ffs.ready` | startup gating | `0/1` | adbd / system init | vendor rc / system rc | adb readiness | yes for adb | Confirmed | adb FunctionFS gate |
| `vendor.usb.ffs.mtp.ready` | startup gating | `0/1` | mtpd / vendor flow | vendor rc | MTP readiness | yes for MTP | Confirmed | vendor-specific MTP gate |
| `vendor.usb.ffs.ptp.ready` | startup gating | `0/1` | ptp flow | vendor rc | PTP readiness | yes for PTP | Confirmed | vendor-specific PTP gate |
| `vendor.usb.config` | transport mode bridge | wildcard | vendor process | init | forwards to `sys.usb.config` | yes | Confirmed | `on property:vendor.usb.config=*` bridge |
| `vendor.usb.test` | diagnostics | wildcard | vendor process | init | test mode selection | no | Confirmed | forces `sys.usb.config none` then test config |
| `vendor.usb.testmode` | diagnostics | `0..3` | vendor process | init | writes `/proc/mtk_usb/testmode` | no | Confirmed | factory/debug only |
| `vendor.usb.printk` | diagnostics | wildcard | vendor process | init | writes kernel printk level | no | Confirmed | debug only |
| `ro.sys.usb.charging.only` | capability flag | `yes` | build props | framework/vendor | policy hint | no | Confirmed | `system/build.prop` |
| `ro.sys.usb.storage.type` | capability flag | `mtp` | build props | framework/vendor | policy hint | no | Confirmed | `system/build.prop` |
| `ro.sys.usb.bicr` | capability flag | `no` | build props | framework/vendor | policy hint | no | Confirmed | BICR support flag |
| `ro.sys.usb.mtp.whql.enable` | capability flag | `0` | build props | framework/vendor | policy hint | no | Confirmed | WHQL flag |
| `ro.vendor.usb.kpoc_adb` | capability flag | `0` | build props | vendor USB stack | KPOC/charger behavior | no | Confirmed | vendor boot mode hint |

### 13.2 Property categories
- identification
- capability toggle
- debug
- transport mode
- startup gating
- performance tuning

### 13.3 Dangerous or misleading properties
- `persist.sys.usb.config=none` hides problems until a user tries to enable USB.
- `vendor.usb.config=*` can mask missing direct `sys.usb.config` callers.
- `vendor.usb.testmode` and `vendor.usb.printk` are debug-only and should not be used as functional validation.
- `ro.sys.usb.*` values describe stock policy, not runtime health.

### 13.4 Minimal property set
Preserve `persist.sys.usb.config`, `sys.usb.configfs`, `sys.usb.config`, `sys.usb.state`, `sys.usb.controller`, `sys.usb.ffs.ready`, `vendor.usb.controller`, `vendor.usb.vid`, and the `vendor.usb.acm_*` / `vendor.usb.ffs.*` gates if you want stock feature parity.

---

## 14. Configuration Surface

### 14.1 Config file analysis
- `vendor/etc/init/hw/init.mt6781.usb.rc` is the board-specific USB state machine. It must match the kernel's controller name (`musb-hdrc`), FunctionFS mount points, and vendor-specific USB function names.
- `system/etc/init/hw/init.usb.rc` and `system/etc/init/hw/init.usb.configfs.rc` are AOSP generic backstops. They are safe to rebuild from source, but this device also relies on the vendor rc for MTK-specific composition and property bridging.
- USB audio policy XMLs define audio policy routes for USB accessory/device/headset audio.
- `vendor/etc/vintf/manifest/android.hardware.usb@1.2-service-mediatekv2.xml` must match the HAL implementation and version exactly.

### 14.2 Critical configuration table

| Config File | Critical Fields / Keys | Must Match Hardware | Safe to Modify | Source / Blob / Overlay | Confidence | Notes |
|---|---|---|---|---|---|---|---|
| `vendor/etc/init/hw/init.mt6781.usb.rc` | `/config/usb_gadget/g1`, function names, UDC name, `vendor.usb.*` props | yes | only with care | stock vendor rc | Confirmed | core bring-up file |
| `vendor/etc/init/android.hardware.usb@1.2-service-mediatekv2.rc` | service name, class, user/group | yes | no | stock vendor rc | Confirmed | start rule for vendor HAL |
| `vendor/etc/vintf/manifest/android.hardware.usb@1.2-service-mediatekv2.xml` | HAL names, versions, instances | yes | no | stock vendor manifest fragment | Confirmed | VINTF contract |
| `system/etc/init/hw/init.usb.rc` | adbd and fallback configfs logic | yes | yes | AOSP source | Confirmed | generic baseline |
| `system/etc/init/hw/init.usb.configfs.rc` | config names and symlink targets | yes | yes | AOSP source | Confirmed | generic configfs router |
| `system_ext/etc/usb_audio_policy_configuration.xml` | module name `usb`, device/mix port names | yes | yes | source-build overlay/config | Confirmed | USB audio only |

### 14.3 Config-level failure modes
- Wrong configfs function names: composite mode exists but enumeration fails.
- Wrong UDC/controller name: gadget never binds.
- Missing `ffs.*.ready` gate: adb/MTP/PTP never becomes visible.
- Wrong audio route names: USB audio disappears while basic USB still works.
- Missing vendor property bridge: `vendor.usb.config` changes never affect `sys.usb.config`.

---

## 15. Kernel Coupling

### 15.1 Driver / module overview
This subsystem depends on built-in kernel support plus likely gadget/function modules. Evidence directly references `musb_hdrc`, `mt_usb`, `usb_f_mtp`, `usb_rawbulk`, Type-C/USB role-switch nodes, configfs, and functionfs.

### 15.2 Kernel module table

| Module / Driver | File Path / Config | Built-in or LKM | Probe Dependency | Firmware Request | User-space Consumer | Required | Confidence | Notes |
|---|---|---|---|---|---|---|---|---|
| `musb_hdrc` | `/sys/module/musb_hdrc/parameters/kernel_init_done` | unknown | boot init | none seen | vendor HAL / init | yes | Confirmed | main USB controller path |
| `mt_usb` | `/sys/devices/platform/mt_usb/saving` | unknown | controller init | none seen | vendor init | yes | Confirmed | MTK platform USB helper |
| `usb_f_mtp` | `/sys/module/usb_f_mtp/parameters/mtp_rx_cont` | unknown | MTP mode | none seen | vendor init | yes for MTP | Confirmed | MTP FunctionFS helper |
| `usb_rawbulk` | `/sys/class/usb_rawbulk/*/enable` | unknown | vendor radio mode | none seen | vendor init | no for base USB | Confirmed | modem/rawbulk modes |
| `configfs` | `/config/usb_gadget/g1` | built-in kernel support required | gadget setup | none seen | vendor init / HAL | yes | Confirmed | essential |
| `functionfs` | `/dev/usb-ffs/*` mounts | built-in kernel support required | adb/MTP/PTP | none seen | `adbd` / MTP / PTP | yes | Confirmed | essential |
| Type-C / usb-role switch | `/sys/class/typec/*`, `/sys/class/usb_role/*` | unknown | role switch hw | none seen | vendor HAL / usbd | yes for role switching | Strong inference | vendor strings prove both paths are supported |

### 15.3 Module load order
No `modules.load` evidence was inspected. The init flow assumes the controller and gadget function drivers exist before post-fs and boot property triggers run.

### 15.4 Device tree / DTBO / board config clues
`musb-hdrc` and `mt_usb` strongly point to a board-specific MTK USB controller configuration. No DT/DTBO artifacts were inspected directly.

### 15.5 Kernel bring-up requirements
Minimum kernel support: MTK USB controller (`musb_hdrc`/`mt_usb`), configfs, functionfs, Type-C or usb-role sysfs, and at least adb + MTP gadget functions. Host-mode USB node permissions are also required.

---

## 16. Framework / App / Overlay Integration

### 16.1 Framework dependencies
- USB settings/UI and `UsbManager` family APIs
- `adbd` for adb USB mode
- Audio policy for USB accessory/device/headset audio
- PackageManager feature gating for `android.hardware.usb.host` and `android.hardware.usb.accessory`

### 16.2 Permissions / features / sysconfig

| File | Type | Declares | Needed for Bring-up | Confidence | Notes |
|---|---|---|---|---|---|---|
| `vendor/etc/permissions/android.hardware.usb.host.xml` | permissions XML | `android.hardware.usb.host` | yes | Confirmed | framework host feature flag |
| `vendor/etc/permissions/android.hardware.usb.accessory.xml` | permissions XML | `android.hardware.usb.accessory` | yes | Confirmed | framework accessory feature flag |
| `system/etc/permissions/com.android.future.usb.accessory.xml` | library XML | `com.android.future.usb.accessory` | yes | Confirmed | legacy accessory API |
| `vendor/etc/usb_audio_policy_configuration.xml` | config XML | USB audio routes | no for base USB | Confirmed | needed for USB audio parity |
| `vendor/etc/usb_audio_accessory_only_policy_configuration.xml` | config XML | accessory-only audio routes | no for base USB | Confirmed | accessory audio variant |
| `system_ext/etc/usb_audio_policy_configuration.xml` | config XML | USB audio routes | no for base USB | Confirmed | system_ext duplicate/overlay |

### 16.3 APK/UI dependencies
No USB-specific APK was identified in the dump beyond the legacy accessory framework JAR. Stock UI sounds include `product/media/audio/ui/usb_effect.ogg`.

### 16.4 Framework integration risks
Even if the HAL starts, USB can still look broken if PackageManager does not see the host/accessory feature XMLs, if `adbd` never reaches `sys.usb.ffs.ready=1`, or if audio policy misses USB device/accessory routes.

---

## 17. Packaging and ROM Integration Decision

### 17.1 File-by-file disposition
- `vendor/bin/hw/android.hardware.usb@1.2-service-mediatekv2`: extract proprietary unchanged
- `vendor/lib64/android.hardware.usb@1.x.so`, `vendor/lib64/android.hardware.usb.gadget@1.x.so`: extract proprietary unchanged
- `vendor/etc/init/hw/init.mt6781.usb.rc`: extract proprietary unchanged
- `vendor/etc/init/android.hardware.usb@1.2-service-mediatekv2.rc`: extract proprietary unchanged
- `vendor/etc/vintf/manifest/android.hardware.usb@1.2-service-mediatekv2.xml`: extract proprietary unchanged
- `system/bin/usbd`: source-build
- `system/etc/init/hw/init.usb.rc`: source-build
- `system/etc/init/hw/init.usb.configfs.rc`: source-build
- `system/etc/init/usbd.rc`: source-build
- `system/lib/libusbhost.so`, `system/lib64/libusbhost.so`, `system/lib/libusb1.0.so`, `system/lib64/android.hardware.usb.gadget@1.0.so`: source-build
- `vendor/etc/permissions/android.hardware.usb.host.xml`, `vendor/etc/permissions/android.hardware.usb.accessory.xml`, `vendor/etc/usb_audio_policy_configuration.xml`, `vendor/etc/usb_audio_accessory_only_policy_configuration.xml`: extract proprietary unchanged
- `system/etc/permissions/com.android.future.usb.accessory.xml`, `system_ext/etc/usb_audio_policy_configuration.xml`: source-build
- `product/media/audio/ui/usb_effect.ogg`: optional/debug only

### 17.2 Packaging matrix

| Artifact | Action | Destination Partition | Build Integration Method | Shim Needed | Confidence | Notes |
|---|---|---|---|---|---|---|
| `android.hardware.usb@1.2-service-mediatekv2` | keep stock | vendor | proprietary-files | no | Confirmed | non-negotiable vendor blob |
| `android.hardware.usb@1.x.so`, `android.hardware.usb.gadget@1.x.so` | keep stock | vendor | proprietary-files | no | Confirmed | vendor HIDL support libs |
| `init.mt6781.usb.rc` | keep stock | vendor | proprietary-files / device tree copy | no | Confirmed | board-specific gadget policy |
| `usbd` | build from source | system | PRODUCT_PACKAGES | no | Confirmed | AOSP daemon |
| generic USB init rc files | build from source | system | source tree | no | Confirmed | AOSP USB glue |
| USB feature XMLs | copy or source-build | vendor/system | PRODUCT_COPY_FILES | no | Confirmed | app-facing feature gate |

### 17.3 Open-source replacement opportunities
- `system/bin/usbd`
- `system/etc/init/hw/init.usb.rc`
- `system/etc/init/hw/init.usb.configfs.rc`
- `system/etc/init/usbd.rc`
- USB feature XMLs and legacy accessory JAR
- USB audio policy XMLs

### 17.4 Non-negotiable proprietary set
- `vendor/bin/hw/android.hardware.usb@1.2-service-mediatekv2`
- `vendor/lib64/android.hardware.usb@1.x.so`
- `vendor/lib64/android.hardware.usb.gadget@1.x.so`
- `vendor/etc/init/hw/init.mt6781.usb.rc`
- `vendor/etc/vintf/manifest/android.hardware.usb@1.2-service-mediatekv2.xml`

---

## 18. Validation Plan

### 18.1 First smoke tests
- Boot to userspace and verify `vendor.usb-hal-1-2` and `usbd` are running
- `getprop sys.usb.configfs`, `getprop sys.usb.state`, `getprop sys.usb.config`
- `setprop sys.usb.config adb` and confirm `adbd` starts and `adb devices` sees the phone
- Switch to `mtp` and confirm host enumeration / file transfer works
- Plug into a host and verify Type-C / role-switch logs do not show `No device in /sys/class/typec` or `Usb HAL not found`
- Confirm `/config/usb_gadget/g1/UDC` is bound to the controller and not `none`

### 18.2 Deep validation tests
- adb only, mtp only, mtp+adb, ptp, accessory, midi, rndis, and vendor rawbulk/factory modes
- USB host enumeration with multiple cables/hubs
- USB audio accessory/device/headset routes
- Type-C host/device role switching on charger and data cables
- Factory/debug modes if the product expects them
- SELinux enforcing boot with all USB modes toggled

### 18.3 Recommended shell commands
- `getprop | grep -E '(^sys\.usb|^vendor\.usb|^persist\.sys\.usb|^ro\.sys\.usb)'`
- `lshal | grep -i usb`
- `service list | grep -i usbd`
- `ps -AZ | grep -E 'usbd|usb|adbd'`
- `logcat -b all | grep -i -E 'usb|typec|gadget|functionfs|adbd'`
- `dmesg | grep -i -E 'usb|typec|musb|mt_usb|configfs|functionfs'`
- `ls -lZ /config/usb_gadget/g1`
- `ls -lZ /sys/class/typec/port0`
- `ls -l /dev/bus/usb /dev/usb_accessory /dev/mtp_usb`

### 18.4 Expected success signals
- HAL registration visible in `lshal`
- `usbd` present in `ps -AZ`
- `adbd` starts only when `sys.usb.config` includes `adb`
- `sys.usb.state` tracks the requested mode
- `/config/usb_gadget/g1/UDC` is bound and host sees a stable USB device

---

## 19. Failure Modes and Triage

| Failure | Symptom | Most Likely Cause | First Check | Fix Direction | Confidence | Notes |
|---|---|---|---|---|---|---|---|
| HAL not starting | no USB modes work, no `vendor.usb-hal-1-2` process | wrong file context or init rc missing | `ps -AZ`, `ls -lZ /vendor/bin/hw/...` | restore `mtk_hal_usb_exec` + init service | High | vendor HAL is mandatory |
| HAL starts but registration fails | `Usb HAL not found`, `Error while invoking usb hal` | `hwservice_contexts` or HIDL version mismatch | `lshal`, `hwservicemanager` logs | fix VINTF and service contexts | High | strings prove this failure path exists |
| adb mode broken | `adb devices` empty | FFS not mounted or `sys.usb.ffs.ready` not set | `mount`, `getprop`, `logcat` | repair FunctionFS and adbd triggers | High | most common bring-up failure |
| MTP broken | host sees no media transfer | missing `usb_f_mtp`, wrong policy, or ready gate not set | `getprop vendor.usb.ffs.mtp.ready`, `dmesg` | fix kernel function or init route | High | vendor rc has explicit gate |
| Type-C role switch broken | cable charges but data/role switching fails | missing `/sys/class/typec/port0` or `/sys/class/usb_role/` | `ls /sys/class/typec/port0` | kernel/SELinux fix | High | vendor HAL strings explicitly depend on these paths |
| Configfs bind fails | gadget exists but not enumerated | wrong UDC/controller name | `cat /config/usb_gadget/g1/UDC` | ensure `musb-hdrc` controller is valid | High | controller name is hardcoded by property |
| Host access broken | OTG devices not visible | `/dev/bus/usb/*` perms or usb group missing | `ls -l /dev/bus/usb` | restore ueventd rule | Medium | affects host mode only |
| Vendor/rawbulk modes broken | modem/factory USB modes fail | missing `usb_rawbulk` nodes or ACM function setup | `ls /sys/class/usb_rawbulk` | keep vendor-specific kernel + rc paths | Medium | not needed for base USB |

---

## 20. Bring-up Checklist

- [ ] All required files identified
- [ ] All critical blobs extracted or replaced
- [ ] Manifest fragment handled
- [ ] Init service declarations handled
- [ ] Properties mapped
- [ ] Device nodes mapped
- [ ] Sysfs/proc/configfs paths mapped
- [ ] Ueventd permissions replicated
- [ ] SELinux labels and domains mapped
- [ ] Required kernel modules/drivers identified
- [ ] Required configs copied or reproduced
- [ ] Framework integration paths mapped
- [ ] Smoke tests defined
- [ ] Failure triage paths documented

---

## 21. Minimal Source of Truth Summary

### 21.1 Minimal required artifacts
- **Required binaries:** `vendor/bin/hw/android.hardware.usb@1.2-service-mediatekv2`, `system/bin/usbd`
- **Required libraries:** vendor USB HIDL libs (`android.hardware.usb@1.x.so`, `android.hardware.usb.gadget@1.x.so`), `system/lib64/android.hardware.usb.gadget@1.0.so`, `libusbhost.so`, `libusb1.0.so`
- **Required configs:** vendor USB init rc, vendor USB HAL rc, vendor VINTF fragment, AOSP USB init rc files, ueventd USB permissions, USB feature XMLs
- **Required manifest entries:** `android.hardware.usb` 1.3 default, `android.hardware.usb.gadget` 1.1 default
- **Required init fragments:** `init.mt6781.rc` import, `init.mt6781.usb.rc`, `android.hardware.usb@1.2-service-mediatekv2.rc`, `system/init/usbd.rc`, `init.usb.rc`, `init.usb.configfs.rc`
- **Required nodes / sysfs / proc paths:** `/config/usb_gadget/g1`, `/sys/class/typec/port0/*`, `/sys/class/android_usb/android0/*`, `/sys/module/musb_hdrc/parameters/kernel_init_done`, `/sys/module/usb_f_mtp/parameters/mtp_rx_cont`, `/dev/usb-ffs/*`, `/dev/ttyGS0-3`
- **Required properties:** `sys.usb.configfs`, `sys.usb.config`, `sys.usb.state`, `sys.usb.controller`, `sys.usb.ffs.ready`, `vendor.usb.controller`, `vendor.usb.vid`, `vendor.usb.pid`, `vendor.usb.acm_*`, `vendor.usb.ffs.*`, `persist.sys.usb.config`
- **Required SELinux labels/domains:** `mtk_hal_usb_exec` -> `mtk_hal_usb`, `usbd_exec` -> `usbd`, `hal_usb_service`, `hal_usb_hwservice`, `hal_usb_gadget_hwservice`
- **Required kernel support:** `musb_hdrc` / MTK USB controller, configfs, functionfs, Type-C or usb-role sysfs, MTP gadget function, host USB nodes, rawbulk if vendor radio modes matter

### 21.2 What can be omitted initially
- Vendor rawbulk/factory modes (`via_bypass`, `mass_storage`, `bicr`, `acm_gs*`, `gs0gs1`)
- `vendor.usb.testmode` and `vendor.usb.printk`
- `usb_effect.ogg`
- USB audio accessory-only policy if you only need adb + MTP

### 21.3 What can be open-sourced later
- `usbd`
- generic AOSP USB init rc files
- USB feature XMLs
- USB audio policy XMLs
- legacy accessory JAR plumbing

### 21.4 Known unknowns
- Exact runtime SELinux label assignment for the vendor USB HAL is inferred from `vendor_file_contexts` and sepolicy, not runtime logs
- Exact kernel packaging for `musb_hdrc`, `usb_f_mtp`, and `usb_rawbulk` was not inspected

---

## 22. Device Tree Fixes Applied

### Fix Summary

**Problem Identified:** Device tree USB init file was missing USB function handlers.

**Root Cause:** The `init.mt6781.usb.rc` only handled `midi` and `adb` functions. Standard USB modes like MTP, PTP, RNDIS, accessory, and audio_source had no property triggers to switch functions.

### Changes Made

1. **`configs/props/system.prop`** - Added default USB config:
   ```
   persist.sys.usb.config=mtp,adb
   ```

2. **`rootdir/etc/init/hw/init.mt6781.usb.rc`** - Added USB function handlers:
   - `mtp`
   - `mtp,adb`
   - `ptp`
   - `ptp,adb`
   - `rndis`
   - `rndis,adb`
   - `accessory`
   - `accessory,adb`
   - `audio_source`
   - `audio_source,adb`
   - `midi,adb`

### Testing

After rebuild and flash:
1. Boot with USB connected
2. Check `getprop persist.sys.usb.config` - should show `mtp,adb`
3. Verify MTP is enumerated on host
4. Try switching USB modes via settings
- Whether the ROM should preserve all vendor factory/rawbulk modes depends on product requirements

### 21.5 Final verdict
**Moderate-to-high risk.** Base adb/MTP USB bring-up is feasible if you keep the stock vendor HAL, vendor init rc, SELinux, and configfs/functionfs paths intact. Replacing the vendor USB stack would be high risk because the HAL is tightly coupled to MTK-specific typec/role-switch and vendor rawbulk behavior.

---

## 22. Appendix A -- Raw Evidence
- `vendor/etc/vintf/manifest/android.hardware.usb@1.2-service-mediatekv2.xml`
- `vendor/etc/init/android.hardware.usb@1.2-service-mediatekv2.rc`
- `vendor/etc/init/hw/init.mt6781.rc` imports `init.mt6781.usb.rc`
- `vendor/etc/init/hw/init.mt6781.usb.rc` lines 1-919
- `system/etc/init/hw/init.rc` imports `/system/etc/init/hw/init.usb.rc` and `/system/etc/init/hw/init.usb.configfs.rc`
- `system/etc/init/hw/init.usb.rc`
- `system/etc/init/hw/init.usb.configfs.rc`
- `system/etc/init/usbd.rc`
- `system/etc/selinux/plat_hwservice_contexts`
- `system/etc/selinux/plat_service_contexts`
- `system/etc/selinux/plat_property_contexts`
- `vendor/etc/selinux/vendor_property_contexts`
- `vendor/etc/selinux/vendor_file_contexts`
- `system/etc/ueventd.rc`
- `system_ext/etc/usb_audio_policy_configuration.xml`
- `vendor/etc/usb_audio_policy_configuration.xml`
- `vendor/etc/usb_audio_accessory_only_policy_configuration.xml`

### 22.1 Exact strings and snippets
- `not suport typec interface`
- `No device in /sys/class/typec`
- `Failed to open /sys/class/typec`
- `Error while invoking usb hal`
- `Usb HAL not found`
- `setCurrentUsbFunctions: skip first time for usbd`
- `system/core/usbd/usbd.cpp`
- `vendor.usb.config`
- `sys.usb.controller`
- `/config/usb_gadget/g1/UDC`

---

## 23. Appendix B -- Commands Used
- `file ...`
- `readelf -d ...`
- `strings -a ... | rg ...`
- `grep`/`glob` over init, VINTF, properties, SELinux, and permissions files
- direct file reads of rc/xml/prop files

---

## 24. Appendix C -- Confidence Annotations
- Vendor HAL binary and service contract: **Confirmed**
- `usbd` role and source origin: **Confirmed**
- Type-C / usb-role support paths: **Strong inference** for runtime fallback use, **Confirmed** for string presence
- Vendor file context for the HAL: **Confirmed**
- Exact runtime kernel module packaging: **Weak inference**

---

## 25. Live Custom-ROM Reassessment

### 25.1 Current state
- `dumpsys usb` reports `connected=true`, `configured=true`, and `kernel_state=CONFIGURED`.
- `adbd` is active and USB intent broadcasts are firing normally.
- `UsbPortManager` reports `USB HAL HIDL version: 13`.
- The vendor USB HAL logs repeated `uevent_event` changes, which is expected on a live connected device.

### 25.2 Log review
- The only USB warning that stands out is `Ignore missing legacy kernel path in bugreport dump: kernel function list:/sys/class/android_usb/android0/functions`.
- That message is a bugreport/legacy-path fallback, not a live USB failure.

### 25.3 Conclusion
- USB is working on the custom ROM based on the current evidence.
- No USB root-cause fix is proven necessary right now.

### 25.4 Device-tree recommendation
- No immediate USB device-tree change is proven necessary.
- Keep the stock USB HAL, configfs init, and usbd glue intact unless you hit a real regression like lost adb, failed MTP, or role-switch breakage.
