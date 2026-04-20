# Audio Firmware Analysis Report

## 1. Document Control
| Field | Value |
|---|---|
| Service / Subsystem | Audio |
| Device Codename | X670 (weak inference from dump path) |
| Marketing Name | Infinix Note 12 (weak inference from dump path) |
| SoC / Platform | MediaTek MT6781 |
| Board / Hardware Variant | MTK audio stack, primary device `mt6781mt6366` |
| Firmware Build ID | `ro.vendor.build.fingerprint=Infinix/X670-GL/Infinix-X670:12/SP1A.210812.016/240224V150:user/release-keys`; `ro.system.build.fingerprint=Infinix/TSSI/FULL-64:13/TP1A.220624.014/240224V142:user/release-keys` |
| Android Version | vendor 12 / framework 13 |
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
Audio on this device covers playback, capture, routing, effects, Bluetooth audio, USB audio, remote submix, sound trigger, and vendor tuning/DSP features. It is the user-facing Android audio contract behind `AudioFlinger`, `AudioPolicyService`, `AAudio`, voice capture, and device-specific enhancement layers.

### 2.2 Stock implementation summary
**Confirmed:** the stock stack is split across:
- `/system/bin/audioserver` for framework audio services.
- `/vendor/bin/hw/android.hardware.audio.service.mediatek` for the vendor HIDL HAL wrapper.
- `vendor/lib64/hw/android.hardware.audio@7.0-impl-mediatek.so` and `vendor/lib64/hw/audio.primary.mt6781.so` for the actual primary device implementation.
- `vendor/lib64/hw/android.hardware.audio.effect@7.0-impl.so`, `vendor/lib64/hw/audio.bluetooth.default.so`, `vendor/lib64/hw/audio.usb.default.so`, and `vendor/lib64/hw/audio.r_submix.mt6781.so` for ancillary routes.
- `vendor/etc/audio_policy_configuration.xml`, `vendor/etc/audio_effects.xml`, `vendor/etc/audio_device.xml`, `vendor/etc/audio_param/*`, and `vendor/etc/dts/*` for policy and tuning.

### 2.3 Bring-up significance
- Bring-up Priority: Blocker
- Expected ROM impact if broken: no audio output, no mic capture, broken calls/voice chat, broken BT/USB audio, possible CTS/VTS failures
- AOSP dependency type: mixed
- Treble relevance: yes

### 2.4 Final recommendation summary
- Recommended implementation path: keep stock vendor audio blobs and reproduce the stock init/policy/SELinux glue
- Major blockers: vendor primary HAL, audio policy routing, smart-PA/DTS/Bessound tuning assets, SELinux, device node permissions
- Likely required actions:
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
Framework audio services, vendor audio HAL wrapper, primary device HAL, audio effects HAL, Bluetooth/USB/remote-submix audio modules, sound trigger HAL, tuning assets, init rc, VINTF, SELinux, permissions/features, properties, and kernel-facing audio nodes.

### 3.2 Explicitly excluded
Camera, fingerprint, sensors, radio, and unrelated vendor services except where they directly interact with audio (for example USB accessory audio and sound trigger).

### 3.3 Adjacent subsystems
Bluetooth audio, USB gadget/audio accessory, telephony voice paths, sound trigger / hotword, DTS/Bessound/SmartPA enhancement, SELinux, and kernel ALSA/audio driver plumbing.

---

## 4. Source Evidence

### 4.1 Firmware source
- Firmware package: extracted stock partition tree
- Region / carrier: not directly identified
- Extraction method: static filesystem analysis only
- Image formats observed: ELF, rc, XML, prop, binary presets, CIL, OGG
- Integrity notes: no runtime logs; conclusions are static only

### 4.2 Partitions examined

| Partition | Mount Path | Relevant to Service | Notes |
|---|---|---:|---|
| boot / init_boot / vendor_boot | boot images | no | not directly inspected |
| vendor | `/vendor` | yes | vendor HAL, tuning, configs, SELinux, properties, manifest |
| system | `/system` | yes | `audioserver`, framework policy, SELinux, properties |
| system_ext | `/system_ext` | yes | property context for `vendor.af.audioserver.restart` |
| product | `/product` | low | `usb_effect.ogg` only |
| odm | `/odm` | low | no audio-specific evidence found |
| vendor_dlkm | `/vendor_dlkm` | low | no audio-specific evidence found |
| odm_dlkm | `/odm_dlkm` | low | no audio-specific evidence found |
| system_dlkm | `/system_dlkm` | low | no audio-specific evidence found |

### 4.3 Evidence types used
- file paths
- init rc fragments
- VINTF XML
- build/property files
- binary strings
- `readelf` output
- ELF file typing
- config XML
- SELinux labels/contexts
- sysfs/proc/dev references

### 4.4 Confidence grading rules
- Confirmed: direct evidence from files or strings
- Strong inference: multiple converging clues
- Weak inference: plausible but not runtime-validated

---

## 5. Service Identity and AOSP Contract

### 5.1 Android-facing role
Android expects audio playback/capture, policy routing, effect loading, and device access through the framework audio stack. On this device, that includes speaker/receiver/headset routing, Bluetooth A2DP/SCO, USB audio, remote submix, AAudio low-latency paths, and vendor-specific tuning/effects.

### 5.2 Interface model
- Interface type: mixed
- Framework entry points: `media.audio_flinger`, `media.audio_policy`, `media.aaudio`, `media.sound_trigger_hw`
- Expected service names: `audioserver`, `android.hardware.audio::IDevicesFactory/default`, `android.hardware.audio.effect::IEffectsFactory/default`, `android.hardware.soundtrigger::ISoundTriggerHw/default`
- Expected instances: `default`
- Binder domain: mixed (`binder` for framework services, `hwbinder` for HALs)

### 5.3 HAL / service contract summary
**Confirmed:** the vendor audio HAL service binary registers HIDL audio, audio effect, Bluetooth audio, vendor audio, and sound trigger interfaces. `vendor/bin/hw/android.hardware.audio.service.mediatek` links `android.hardware.audio@6.0.so`, `@7.0.so`, `android.hardware.audio.effect@6.0.so`, `@7.0.so`, `android.hardware.bluetooth.audio@2.0.so`, `@2.1.so`, `vendor.mediatek.hardware.bluetooth.audio@2.1.so`, `@2.2.so`, `android.hardware.soundtrigger@2.3.so`, `vendor.mediatek.hardware.audio@6.1.so`, and `@7.1.so`.

**Confirmed:** the framework-side `audioserver` is the AOSP/system daemon that exports `media.audio_flinger`, `media.audio_policy`, `media.aaudio`, and `media.sound_trigger_hw` service names.

**Strong inference:** this build is HIDL-first for the vendor HAL contract. Platform SELinux also reserves `android.hardware.audio.core.IConfig/default` and `android.hardware.audio.core.IModule/default`, but no matching stock vendor daemon or manifest entry was found here.

### 5.4 Compatibility and Treble notes
- VINTF manifest needed: yes
- Compatibility matrix implications: framework matrix includes `android.hardware.audio` 6.0 and 7.0-1, `android.hardware.audio.effect` 6.0 and 7.0, and `android.hardware.soundtrigger` 2.3
- Lazy service behavior: no evidence of lazy HIDL service; vendor service is normal init-managed daemon
- Passthrough vs binderized: binderized / `hwbinder`
- Same-process HAL/SP-HAL concerns: none directly evidenced

---

## 6. Filesystem Inventory

### 6.1 Executables and daemons

| Path | Binary Name | Purpose | Arch | SELinux Label | Trigger / Service Name | Confidence | Notes |
|---|---|---|---|---|---|---|---|---|
| `system/bin/audioserver` | `audioserver` | framework audio daemon | ELF 64-bit ARM64 PIE, Android 33 | `u:object_r:audioserver_exec:s0` | `service audioserver` / `class core` | Confirmed | source-built AOSP daemon |
| `vendor/bin/hw/android.hardware.audio.service.mediatek` | `android.hardware.audio.service.mediatek` | vendor audio HAL wrapper | ELF 32-bit ARM PIE, Android 31 | not directly inspected | `service vendor.audio-hal` / `class hal` | Confirmed | proprietary vendor daemon |
| `vendor/bin/audiocmdservice_atci` | `audiocmdservice_atci` | audio engineering/debug daemon | ELF 64-bit ARM64 PIE, Android 31 | `u:object_r:audiocmdservice_atci_exec:s0` | `service audio-daemon` / `class main` / `disabled` | Confirmed | debug/ATCI path |
| `vendor/bin/tran_tinymix` | `tran_tinymix` | vendor mixer helper | not inspected | not inspected | `service tran_tinymix` / `class main` / `oneshot` | Strong inference | debug/tuning helper |

### 6.2 Shared libraries / proprietary blobs

| Path | Library | Role | Loaded By | Key Dependencies | Namespace Risk | Confidence | Notes |
|---|---|---|---|---|---|---|---|---|
| `vendor/lib64/hw/audio.primary.mt6781.so` | `audio.primary.mt6781.so` | primary ALSA HAL | vendor audio HAL wrapper | `libtinyalsa.so`, `libalsautils.so`, `libaudioutils.so`, `libaudiotoolkit_vendor.so`, `vendor.mediatek.hardware.audio@7.1.so`, `vendor.mediatek.hardware.mtkpower@1.0.so` | high | Confirmed | core playback/capture path |
| `vendor/lib64/hw/android.hardware.audio@7.0-impl-mediatek.so` | `android.hardware.audio@7.0-impl-mediatek.so` | HIDL devices factory impl | vendor audio HAL wrapper | `libaudiofoundation.so`, `android.hardware.audio@7.0.so`, `android.hardware.audio.common@7.0.so`, `vendor.mediatek.hardware.audio@7.1.so` | high | Confirmed | exports `HIDL_FETCH_IDevicesFactory` |
| `vendor/lib64/hw/android.hardware.audio.effect@7.0-impl.so` | `android.hardware.audio.effect@7.0-impl.so` | HIDL effects factory impl | vendor audio HAL wrapper | `libeffects.so`, `android.hardware.audio.effect@7.0.so` | medium | Confirmed | standard effect HAL |
| `vendor/lib64/hw/audio.bluetooth.default.so` | `audio.bluetooth.default.so` | Bluetooth audio module | audio HAL stack | `vendor.mediatek.hardware.bluetooth.audio@2.1.so`, `@2.2.so`, `libbluetooth_audio_session_mediatek.so` | medium | Confirmed | A2DP/SCO/LE audio |
| `vendor/lib64/hw/audio.usb.default.so` | `audio.usb.default.so` | USB audio module | audio HAL stack | `libaudioutils.so`, `libtinyalsa.so`, `libalsautils.so` | medium | Confirmed | USB accessory/device audio |
| `vendor/lib64/hw/audio.r_submix.mt6781.so` | `audio.r_submix.mt6781.so` | remote submix / cast audio | audio HAL stack | `libmedia_helper.so`, `libnbaio_mono.so` | medium | Confirmed | WiFi display / remote audio |
| `vendor/lib64/hw/android.hardware.soundtrigger@2.3-impl.so` | `android.hardware.soundtrigger@2.3-impl.so` | sound trigger HAL impl | vendor audio HAL wrapper | `android.hardware.soundtrigger@2.0-2.3.so`, `android.hidl.memory@1.0.so`, `libhidlmemory.so` | medium | Confirmed | hotword / voice wake |
| `vendor/lib64/libaudioloudc.so` | `libaudioloudc.so` | Bessound DSP helper | audio effects/tuning stack | `libbessound_hd_mtk_vendor.so`, `libaudiocompensationfilterc.so` | medium | Confirmed | playback enhancement |
| `vendor/lib64/libbessound_hd_mtk_vendor.so` | `libbessound_hd_mtk_vendor.so` | Bessound vendor DSP lib | `libaudioloudc.so` | `libmtk_drvb.so` | medium | Confirmed | speaker/volume enhancement |
| `vendor/lib64/lib_speech_enh.so` | `lib_speech_enh.so` | speech enhancement wrapper | voice/record tuning | `libMtkSpeechEnh.so`, `libaudio_param_parser-vnd.so`, `libaudioutils.so` | medium | Confirmed | DMNR/AEC/voice tuning |
| `vendor/lib64/libMtkSpeechEnh.so` | `libMtkSpeechEnh.so` | speech enhancement core | `lib_speech_enh.so` | none visible beyond libc/log | medium | Confirmed | heavy voice DSP logic |
| `vendor/lib64/soundfx/libaudiopreprocessing_mtk.so` | `libaudiopreprocessing_mtk.so` | AEC/NS/AGC pre-processing | audio effects HAL | none special beyond libc/log | low | Confirmed | audio_effects.xml `pre_processing` |
| `vendor/lib64/soundfx/libdtsaudio.so` | `libdtsaudio.so` | DTS audio effect | audio effects HAL | `libdts-eagle-shared.so`, `libsqlite.so`, `libcrypto.so` | medium | Confirmed | stock DTS effect |
| `vendor/lib64/libdts-eagle-shared.so` | `libdts-eagle-shared.so` | DTS math / policy core | `libdtsaudio.so` | none special | medium | Confirmed | license/config driven |
| `vendor/lib64/libdtsdsec.so` | `libdtsdsec.so` | DTS security/license helper | `libdtsaudio.so` | none special | medium | Confirmed | license path and config path |
| `vendor/lib64/libaudioprimarydevicehalifclient.so` | `libaudioprimarydevicehalifclient.so` | MTK primary device HIDL client | `audiocmdservice_atci` / HAL glue | `android.hardware.audio@7.0.so`, `libhwbinder.so`, `libhidlbase.so` | medium | Confirmed | client bridge to primary device HAL |
| `vendor/lib64/libaudiocompensationfilterc.so` | `libaudiocompensationfilterc.so` | compensation filter helper | `audiocmdservice_atci` / effect stack | `libaudiocustparam_vendor.so`, `libnvram.so` | medium | Confirmed | speaker tuning helper |

### 6.3 Config files

| Path | Format | Consumed By | Critical Keys | Overlayable | Confidence | Notes |
|---|---|---|---|---|---|---|
| `system/bin/audioserver` | binary | framework audio daemon | service registration strings | no | Confirmed | main framework daemon |
| `system/etc/init/audioserver.rc` | rc | init | service `audioserver`, restart hooks, `sys.audio.restart.hal`, `vendor.af.audioserver.restart` | no | Confirmed | core boot integration |
| `vendor/etc/init/android.hardware.audio.service.mediatek.rc` | rc | init | service `vendor.audio-hal`, `post-fs-data` mkdir, restart audioserver | no | Confirmed | main vendor audio daemon |
| `vendor/etc/vintf/manifest.xml` | XML | VINTF/hwservicemanager | audio, effect, soundtrigger, bluetooth audio HAL entries | no | Confirmed | device manifest |
| `vendor/etc/audio_policy_configuration.xml` | XML | AudioPolicy | primary, bluetooth, USB, remote submix includes | yes | Confirmed | active routing policy |
| `vendor/etc/audio_policy_volumes.xml` | XML | AudioPolicy | stream/device volume curves | yes | Confirmed | stock volume tables |
| `vendor/etc/audio_effects.xml` | XML | AudioEffect | `pre_processing`, `dtsaudio`, effect UUIDs | yes | Confirmed | effect loading contract |
| `vendor/etc/audio_device.xml` | XML | primary HAL tuning | card name `mt6781mt6366`, mixer controls | no | Confirmed | hardware mixer map |
| `vendor/etc/audio_param/*` | XML / bin | vendor DSP helpers | voice, record, playback, USB, SmartPA, presets | no | Confirmed | large tuning set |
| `vendor/etc/dts/*` | cfg/bin/lic | DTS helper libs | license, current profiles, `customer.cfg` | no | Confirmed | DTS enhancement assets |
| `vendor/etc/permissions/handheld_core_hardware.xml` | permissions XML | PackageManager | `android.hardware.audio.output`, `android.hardware.microphone` | yes | Confirmed | core handheld features |
| `vendor/etc/permissions/android.hardware.audio.low_latency.xml` | permissions XML | PackageManager | `android.hardware.audio.low_latency` | yes | Confirmed | low-latency feature flag |
| `vendor/etc/permissions/android.hardware.microphone.xml` | permissions XML | PackageManager | `android.hardware.microphone` | yes | Confirmed | mic feature flag |
| `system/etc/permissions/platform.xml` | permissions XML | PackageManager | audioserver permissions | no | Confirmed | grants service permissions |
| `vendor/build.prop` | prop | runtime property service | `aaudio.mmap_policy`, `aaudio.mmap_exclusive_policy`, `ro.vendor.tran_audio_game_mode.support`, `ro.vendor.mtk_audio_alac_support` | no | Confirmed | audio policy tuning |
| `system/build.prop` | prop | runtime property service | `ro.audio.silent`, `ro.audio.usb.period_us`, `ro.camera.sound.forced` | no | Confirmed | framework-side audio tuning |
| `system_ext/etc/selinux/system_ext_property_contexts` | property contexts | SELinux/property | `vendor.af.audioserver.restart` | no | Confirmed | audio restart property |

### 6.4 APK / JAR / APEX / framework packages

| Path / Package | Type | Purpose | Privileged | Permissions / Features | Confidence | Notes |
|---|---|---|---|---|---|---|
| `system/framework/com.android.future.usb.accessory.jar` | JAR | legacy accessory API | no | USB accessory library | Confirmed | framework API, not core audio |
| `system/etc/permissions/platform.xml` | permissions | audioserver grants | yes | audio, surfaceflinger, wakelock, app-ops perms | Confirmed | service permissions |
| `vendor/etc/permissions/handheld_core_hardware.xml` | feature XML | handheld audio/mic features | n/a | audio output, microphone | Confirmed | framework-visible features |
| `vendor/etc/permissions/android.hardware.audio.low_latency.xml` | feature XML | low-latency audio | n/a | `android.hardware.audio.low_latency` | Confirmed | CDD-sensitive flag |

### 6.5 Firmware assets / DSP / microcode / calibration

| Path | Asset Type | Loaded By | Hardware Target | Required for Bring-up | Confidence | Notes |
|---|---|---|---|---|---|---|
| `vendor/etc/audio_param/*` | tuning XML/bin | MTK audio libs | playback/record/voice/USB/SmartPA | yes for stock parity | Confirmed | large vendor tuning set |
| `vendor/etc/audio_param/preset_*.bin` | preset blobs | `libfsmaudio.so` | speaker/voice/record paths | yes for stock parity | Confirmed | preset selection by mode |
| `vendor/etc/dts/dts-eagle.lic` | license | `libdtsdsec.so` | DTS enhancement | yes if DTS kept | Confirmed | license file |
| `vendor/etc/dts/customer.cfg` | config | `libdtsdsec.so` | DTS enhancement | yes if DTS kept | Confirmed | DTS route/profile config |
| `vendor/etc/dts/current_*` and `music_*` / `movie_*` / `games_*` | profile assets | DTS stack | speaker/bluetooth/USB accessory | no for base audio | Confirmed | enhancement only |
| `product/media/audio/ui/usb_effect.ogg` | UI sound | framework audio UI | USB connect/disconnect | no | Confirmed | polish only |

---

## 7. Init Integration

### 7.1 Relevant init fragments
- `system/etc/init/audioserver.rc`
- `system/etc/init/hw/init.zygote32.rc`
- `system/etc/init/hw/init.zygote64_32.rc`
- `system/etc/init/servicemanager.rc`
- `vendor/etc/init/android.hardware.audio.service.mediatek.rc`
- `vendor/etc/init/hw/init.mt6781.rc`
- `vendor/etc/init/hw/multi_init.rc`
- `vendor/etc/init/hw/meta_init.rc`
- `vendor/etc/init/audiocmdservice_atci.rc`
- `vendor/etc/init/dts.rc`
- `vendor/etc/init/tran_tinymix.rc`

### 7.2 Service definitions

| RC File | Service Name | Command | Class | User/Group | Capabilities | Disabled/Oneshot | Interface Declaration | Confidence | Notes |
|---|---|---|---|---|---|---|---|---|---|
| `system/etc/init/audioserver.rc` | `audioserver` | `/system/bin/audioserver` | `core` | `audioserver` / `audio camera drmrpc media mediadrm net_bt net_bt_admin net_bw_acct wakelock log` | `BLOCK_SUSPEND` | enabled | framework service names in binary | Confirmed | restart hub for HALs |
| `vendor/etc/init/android.hardware.audio.service.mediatek.rc` | `vendor.audio-hal` | `/vendor/bin/hw/android.hardware.audio.service.mediatek` | `hal` | `audioserver` / `audio camera drmrpc inet media mediadrm net_bt net_bt_admin net_bw_acct wakelock context_hub system sdcard_rw` | `BLOCK_SUSPEND SYS_NICE` | enabled | HIDL audio/effect/bluetooth/soundtrigger | Confirmed | main vendor HAL |
| `vendor/etc/init/audiocmdservice_atci.rc` | `audio-daemon` | `/vendor/bin/audiocmdservice_atci` | `main` | `system` / `system audio` | none | disabled / oneshot | socket `atci-audio` | Confirmed | engineering helper |
| `vendor/etc/init/tran_tinymix.rc` | `tran_tinymix` | `/vendor/bin/tran_tinymix` | `main` | `system` / `system audio` | none | oneshot | none shown | Strong inference | tuning helper |

### 7.3 Trigger paths
- Confirmed: `audioserver` starts as a normal `class core` service.
- Confirmed: `audioserver` is restarted on zygote restarts in both zygote rc files.
- Confirmed: `audioserver` is restarted from `servicemanager.rc` on servicemanager restart.
- Confirmed: `vendor.audio-hal` is started by init from `class hal` and is imported by both `vendor/etc/init/hw/multi_init.rc` and `vendor/etc/init/hw/meta_init.rc`.
- Confirmed: `on post-fs-data` in `vendor/etc/init/android.hardware.audio.service.mediatek.rc` creates `/data/vendor/audiohal`.
- Confirmed: `on property:vts.native_server.on=1/0` in `audioserver.rc` stops/starts `audioserver`.
- Confirmed: `on property:vold.decrypt=trigger_reset_main` restarts `audioserver`.
- Confirmed: `on property:init.svc.audioserver=stopped/running` restarts the vendor audio HAL and related legacy aliases.
- Confirmed: `on property:sys.audio.restart.hal=1` forces HAL restart and resets the property.
- Confirmed: `on property:vendor.af.audioserver.restart=0/1` stops/starts `audioserver`.

### 7.4 Init writes and side effects
- `mkdir /data/misc/audioserver 0700 audioserver audioserver`
- `mkdir /dev/socket/audioserver 0775 audioserver audioserver`
- `mkdir /data/vendor/audiohal 0771 system audio`
- `mkdir /mnt/vendor/nvdata/media 0771 media audio`
- `mkdir /data/vendor/audio 0770 audio audio`
- `mkdir /data/vendor/audio/dts 0771 media audio`
- `copy /vendor/etc/dts/dts_audio_settings /data/vendor/audio/dts/dts_audio_settings`
- `setprop ro.vendor.dts.licensepath "/vendor/etc/dts/"`
- `setprop ro.vendor.dts.cfgpath "/vendor/etc/dts/"`
- `write /sys/module/musb_hdrc/parameters/kernel_init_done 1` is USB-specific and only relevant if USB audio accessory paths are being brought up.
- `chown audioserver audio /sys/bus/platform/devices/rt5509_param.0/prop_param`
- `chown audioserver audio /sys/bus/platform/devices/rt5509_param.1/prop_param`
- `chown audioserver audio /sys/bus/platform/devices/mt6660-param.0/prop_params`

### 7.5 Boot ordering notes
The framework daemon is available at normal boot class start. The vendor HAL is brought up by init and should be present before the framework starts routing audio. A clean bring-up usually needs both services up before testing playback, recording, or Bluetooth audio.

---

## 8. VINTF / Manifest Analysis

### 8.1 Manifest sources
- `vendor/etc/vintf/manifest.xml`
- `system/etc/vintf/compatibility_matrix.3.xml`
- `system/etc/vintf/compatibility_matrix.4.xml`
- `system/etc/vintf/compatibility_matrix.5.xml`
- `system/etc/vintf/compatibility_matrix.6.xml`
- `system/etc/vintf/compatibility_matrix.7.xml`

### 8.2 HAL declarations

| Manifest File | Format | Package | Interface | Version | Instance / FQName | Transport | Optional? | Confidence | Notes |
|---|---|---|---|---|---|---|---|---|---|
| `vendor/etc/vintf/manifest.xml` | hidl | `android.hardware.audio` | `IDevicesFactory` | 7.0 | `default` / `@7.0::IDevicesFactory/default` | `hwbinder` | no | Confirmed | main audio HAL |
| `vendor/etc/vintf/manifest.xml` | hidl | `android.hardware.audio.effect` | `IEffectsFactory` | 7.0 | `default` / `@7.0::IEffectsFactory/default` | `hwbinder` | no | Confirmed | effects HAL |
| `vendor/etc/vintf/manifest.xml` | hidl | `android.hardware.bluetooth.audio` | `IBluetoothAudioProvidersFactory` | 2.1 | `default` | `hwbinder` | no | Confirmed | framework BT audio |
| `vendor/etc/vintf/manifest.xml` | hidl | `vendor.mediatek.hardware.bluetooth.audio` | `IBluetoothAudioProvidersFactory` | 2.2 | `default` | `hwbinder` | no | Confirmed | vendor BT audio extension |
| `vendor/etc/vintf/manifest.xml` | hidl | `android.hardware.soundtrigger` | `ISoundTriggerHw` | 2.3 | `default` / `@2.3::ISoundTriggerHw/default` | `hwbinder` | no | Confirmed | hotword/sound trigger |

### 8.3 Compatibility observations
- FCM / target-level clues: framework matrix is level 7; vendor build is Android 12, framework is Android 13
- Deprecated interface risk: vendor stack is HIDL-first
- Multiple instances or vendor forks: no vendor forked audio instances beyond Bluetooth vendor extension
- Need to copy stock manifest fragment: yes

### 8.4 Registration path
The vendor HAL binary registers the HIDL services directly. Init launches the wrapper binary from `vendor/etc/init/android.hardware.audio.service.mediatek.rc`, and `hwservicemanager` binds to the `default` instances named in the vendor manifest.

---

## 9. Binary Analysis

### 9.1 Main binary inventory
- `audioserver` is a 64-bit PIE ARM64 executable for Android 33. `readelf -d` shows `libaaudioservice.so`, `libaudioclient.so`, `libaudioflinger.so`, `libaudiopolicyservice.so`, `libaudioprocessing.so`, `libbinder.so`, `libmedia.so`, `libmedialogservice.so`, `libmediautils.so`, `libnbaio.so`, `libnblog.so`, and `libvibrator.so`.
- `strings` on `audioserver` show `media.aaudio`, `media.audio_policy`, `media.audio_flinger`, `AudioFlinger`, `AudioPolicyService`, `AAudioService`, and `audio.maxmem`.
- `android.hardware.audio.service.mediatek` is a 32-bit PIE ARM executable for Android 31. It depends on `libaudiofoundation.so`, HIDL base/transport libs, audio 6.0/7.0 interface libs, audio effect libs, Bluetooth audio libs, vendor Mediatek audio libs, and soundtrigger 2.3.
- `strings` on `android.hardware.audio.service.mediatek` show `Start audiohalservice`, `Audio Core API`, `Audio Effect API`, `Bluetooth Audio API`, `Vendor Bluetooth Audio API`, `android.hardware.audio@6.0::IDevicesFactory`, `android.hardware.audio@7.0::IDevicesFactory`, `android.hardware.audio.effect@6.0::IEffectsFactory`, `android.hardware.audio.effect@7.0::IEffectsFactory`, and `android.hardware.soundtrigger@2.3::ISoundTriggerHw`.
- `audio.primary.mt6781.so` is a 64-bit vendor primary HAL module with ALSA/tinyalsa, MTK power, ladder, and AAudio/MMAP support.
- `audio.bluetooth.default.so` binds to vendor Mediatek Bluetooth audio providers and sessions.
- `audio.usb.default.so` is the USB audio HAL module.
- `audio.r_submix.mt6781.so` is the remote submix / cast audio module.
- `android.hardware.audio.effect@7.0-impl.so` is the standard effects HAL implementation, including AEC and AGC class implementations in strings.
- `android.hardware.soundtrigger@2.3-impl.so` implements the sound trigger HIDL contract and explicitly logs `couldn't load sound trigger module`.

### 9.2 Dependency table

| Binary / Library | DT_NEEDED | Suspected `dlopen()` Targets | Cross-Partition Dependencies | Missing Symbol Risk | Confidence | Notes |
|---|---|---|---|---|---|---|---|
| `system/bin/audioserver` | `libaaudioservice.so`, `libaudioflinger.so`, `libaudiopolicyservice.so`, `libaudioprocessing.so`, `libbinder.so`, `libmedia.so`, `libmediautils.so`, `libnbaio.so`, `libnblog.so`, `libvibrator.so` | none evidenced | system audio framework libs | high if framework libs mismatch | Confirmed | core framework daemon |
| `vendor/bin/hw/android.hardware.audio.service.mediatek` | audio 6.0/7.0, effect 6.0/7.0, Bluetooth audio 2.0/2.1/vendor 2.1/2.2, soundtrigger 2.3, vendor audio 6.1/7.1 | likely `audio.primary.mt6781.so`, effect impls, soundtrigger impl | vendor audio HAL libs, vendor SELinux, audio policy, device nodes | high | Confirmed | vendor wrapper daemon |
| `vendor/lib64/hw/android.hardware.audio@7.0-impl-mediatek.so` | audio 7.0 libs, audio common 7.0 libs, vendor audio 7.1, `libmedia_helper.so` | none evidenced | `audio.primary.mt6781.so` and vendor audio libs | high | Confirmed | main primary device impl |
| `vendor/lib64/hw/audio.primary.mt6781.so` | `libtinyalsa.so`, `libalsautils.so`, `libaudioutils.so`, `libaudiotoolkit_vendor.so`, `libladder.so`, `libbwc.so`, `libaedv.so`, `vendor.mediatek.hardware.audio@7.1.so` | none evidenced | kernel ALSA card/control nodes, SmartPA sysfs, audio param files | high | Confirmed | core hardware path |
| `vendor/lib64/hw/android.hardware.audio.effect@7.0-impl.so` | `libeffects.so`, `libfmq.so`, `libhidlmemory.so`, audio common/effect libs | `libaudiopreprocessing_mtk.so`, `libdtsaudio.so` via config | soundfx libs | medium | Confirmed | standard effect HAL |
| `vendor/lib64/hw/audio.bluetooth.default.so` | vendor BT audio libs, `libbluetooth_audio_session_mediatek.so`, `libaudioutils.so`, `libfmq.so` | none evidenced | Bluetooth stack and vendor BT audio HIDL | high | Confirmed | A2DP/SCO/LE routes |
| `vendor/lib64/hw/audio.usb.default.so` | `libaudioutils.so`, `libtinyalsa.so`, `libalsautils.so` | none evidenced | ALSA USB card/audio class nodes | medium | Confirmed | USB audio accessory/device |
| `vendor/lib64/hw/audio.r_submix.mt6781.so` | `libmedia_helper.so`, `libnbaio_mono.so` | none evidenced | system cast/remote submix policy | medium | Confirmed | WiFi display / cast |
| `vendor/lib64/hw/android.hardware.soundtrigger@2.3-impl.so` | soundtrigger 2.0-2.3 libs, `libhidlmemory.so`, `android.hidl.memory@1.0.so` | none evidenced | sound trigger sysfs/firmware if any, vendor HAL | medium | Confirmed | hotword pipeline |
| `vendor/lib64/libaudioloudc.so` | `libbessound_hd_mtk_vendor.so`, `libaudiocompensationfilterc.so` | none evidenced | audio_param directory, vendor tuning props | medium | Confirmed | loudness/enhancement |
| `vendor/lib64/lib_speech_enh.so` | `libMtkSpeechEnh.so`, `libaudio_param_parser-vnd.so`, `libaudioutils.so` | none evidenced | `vendor/etc/audio_param/*` | medium | Confirmed | speech/voice enhancement |
| `vendor/lib64/soundfx/libdtsaudio.so` | `libdts-eagle-shared.so`, `libsqlite.so`, `libcrypto.so` | none evidenced | `vendor/etc/dts/*`, license and cfg | medium | Confirmed | DTS effect |

### 9.3 Linker namespace / VNDK analysis
- Uses public VNDK only: no
- Uses private platform libs: likely yes on vendor side, but not directly proven beyond vendor blob dependencies
- Requires shim library: no evidence
- SP-HAL concerns: none directly evidenced
- Namespace risk summary: high; keep vendor audio blob set intact

### 9.4 Important strings and symbols
- `audioserver`: `media.aaudio`, `media.audio_flinger`, `media.audio_policy`, `audio.maxmem`
- `android.hardware.audio.service.mediatek`: `Start audiohalservice`, `Audio Core API`, `Audio Effect API`, `Bluetooth Audio API`, `Vendor Bluetooth Audio API`, `persist.vendor.audio.service.hwbinder.size_kbyte`
- `audio.primary.mt6781.so`: `AudioALSAHardwareResourceManager`, `AudioUSBCenter`, `AudioSmartPaController`, `AAudio`, `USB audio HW HAL`, `modules.usbaudio.audio_hal`, `audio.primary.mt6781.so`
- `audio.bluetooth.default.so`: `A2DP_SOFTWARE_ENCODING_DATAPATH`, `A2DP_HARDWARE_OFFLOAD_DATAPATH`, `BluetoothAudioPort`, `BluetoothAudioSession`
- `audio.usb.default.so`: `USB audio module`, `modules.usbaudio.audio_hal`
- `audio.r_submix.mt6781.so`: `Wifi Display audio HAL`, `r_submix_streamin`, `r_submix_streamout`, `vendor.r_submix.log`
- `libdtsaudio.so`: `ro.vendor.dts.licensepath`, `ro.vendor.dts.cfgpath`, `/vendor/etc/dts/`, `current_speaker48k`, `current_usb48k`, `current_bluetooth44k`, `dts_audio_processing`
- `lib_speech_enh.so`: `dmnr_para`, `speech_mode_para`, `record_mode_para`, `voip`, `aec`, `dmnr`
- `libfsmaudio.so`: `preset_music.bin`, `preset_voice.bin`, `preset_voip.bin`, `preset_default.bin`, `preset_alarm.bin`, `preset_notification.bin`

### 9.5 Binary-level conclusions
**Confirmed:** this is not a minimal audio shim. It is a full MTK/Transsion audio stack with ALSA primary HAL, secondary modules, enhancement DSP, sound trigger, and several vendor tuning libraries. **Strong inference:** first bring-up is safest only if the stock vendor audio blob set and the matching policy/config files are preserved.

---

## 10. Device Nodes, Sysfs, Procfs, and IO Surface

### 10.1 Device nodes

| Path | Type | Created By | Ownership / Mode | SELinux Label | Consumer | Evidence | Required | Confidence | Notes |
|---|---|---|---|---|---|---|---|---|---|
| `/dev/snd/*` | ALSA nodes | kernel / ueventd | `0660 system audio` | not inspected | primary/USB/BT HALs | `system/etc/ueventd.rc` | yes | Confirmed | main audio device class |
| `/dev/audio_ipi` | vendor device | kernel / ueventd | `0640 media media` | not inspected | MTK audio HAL | `vendor/init/hw/init.mt6781.rc` | yes | Confirmed | DSP/IPI path |
| `/dev/audio_scp` | vendor device | kernel / ueventd | `0640 media media` | not inspected | MTK audio HAL | `vendor/init/hw/init.mt6781.rc` | yes | Confirmed | SmartPA/SCP path |
| `/dev/socket/audioserver` | socket | init | `0775 audioserver audioserver` | `audioserver_socket`-style context not directly checked | audioserver internals | `audioserver.rc` | yes | Confirmed | framework daemon socket |
| `/dev/offloadservice` | vendor device | kernel / ueventd | `0640 media media` | not inspected | offload / audio tuning | `vendor/init/hw/init.mt6781.rc` | low | Confirmed | likely enhancement/offload path |

### 10.2 Sysfs / procfs / configfs paths

| Path | Purpose | Read/Write | Referenced By | Required | Confidence | Notes |
|---|---|---|---|---|---|---|
| `/sys/bus/platform/devices/rt5509_param.0/prop_param` | SmartPA property | write/chown | init and audioserver | yes for stock speaker tuning | Confirmed | speaker amp tuning |
| `/sys/bus/platform/devices/rt5509_param.1/prop_param` | SmartPA property | write/chown | init and audioserver | yes for stock speaker tuning | Confirmed | speaker amp tuning |
| `/sys/bus/platform/devices/mt6660-param.0/prop_params` | SmartPA property | write/chown | init and audioserver | yes for stock speaker tuning | Confirmed | speaker amp tuning |
| `/data/misc/audioserver` | framework data dir | write | init | yes | Confirmed | audioserver state/cache |
| `/data/vendor/audiohal` | vendor HAL data dir | write | init | yes | Confirmed | vendor HAL runtime data |
| `/data/vendor/audio/dts/*` | DTS runtime settings | read/write | `dts.rc` and DTS libs | yes if DTS kept | Confirmed | DTS settings cache |
| `/mnt/vendor/nvdata/media` | vendor media/audio nvdata | write | init | likely | Confirmed | vendor storage path |
| `/config/usb_gadget/g1/*` | USB audio accessory routing | write | USB init | no for base audio | Strong inference | only for USB audio accessory mode |

### 10.3 IOCTL / netlink / socket / binder clues
- `audioserver` uses binder service names `media.audio_flinger`, `media.audio_policy`, `media.aaudio`, and `media.sound_trigger_hw`.
- `vendor.audio-hal` is HIDL/hwbinder-based and exposes the audio/effect/soundtrigger factories.
- `audiocmdservice_atci` uses a Unix stream socket `atci-audio` and binder access to the vendor HAL.

### 10.4 Runtime path expectations
Working audio requires `/dev/snd/*`, `/dev/audio_ipi`, `/dev/audio_scp`, the SmartPA sysfs nodes above, `/data/misc/audioserver`, `/data/vendor/audiohal`, and the vendor audio_param/DTS assets if stock tuning is preserved.

---

## 11. Ueventd and Permissions

### 11.1 `ueventd.rc` entries
- `system/etc/ueventd.rc`: `/dev/snd/* 0660 system audio`
- `vendor/etc/ueventd.rc`: `/dev/ccci_pcm_rx`, `/dev/ccci_pcm_tx`, `/dev/ccci_aud`, `/dev/ccci2_aud`, `/dev/ccci3_aud`, `/dev/ccci_raw_audio`, `/dev/ccci3_raw_audio`, `/dev/eemcs_aud` all `0660 audio audio`

### 11.2 Node permission model

| Node / Path | Owner | Group | Mode | Source File | Confidence | Notes |
|---|---|---|---|---|---|---|
| `/dev/snd/*` | system | audio | 0660 | `system/etc/ueventd.rc` | Confirmed | core ALSA access |
| `/dev/audio_ipi` | media | media | 0640 | `vendor/etc/init/hw/init.mt6781.rc` | Confirmed | vendor DSP path |
| `/dev/audio_scp` | media | media | 0640 | `vendor/etc/init/hw/init.mt6781.rc` | Confirmed | vendor DSP path |
| `/sys/bus/platform/devices/rt5509_param.*` | audioserver | audio | chown | `vendor/etc/init/hw/init.mt6781.rc` | Confirmed | speaker amp tuning |
| `/sys/bus/platform/devices/mt6660-param.0/prop_params` | audioserver | audio | chown | `vendor/etc/init/hw/init.mt6781.rc` | Confirmed | speaker amp tuning |
| `/data/misc/audioserver` | audioserver | audioserver | 0700 | `audioserver.rc` | Confirmed | daemon private data |
| `/data/vendor/audiohal` | system | audio | 0771 | `android.hardware.audio.service.mediatek.rc` | Confirmed | vendor HAL data |

### 11.3 Boot-created paths and symlinks
- `/dev/socket/audioserver` is created on init.
- `/data/vendor/audio` and `/data/vendor/audio/dts` are created by `dts.rc`.

### 11.4 Risk summary
If these permissions are not reproduced, the stack usually fails in one of two ways: `audioserver` cannot access ALSA/sysfs nodes, or the vendor HAL cannot touch the SmartPA / DSP control surfaces. Both failures commonly look like “service started but no audio.”

---

## 12. SELinux Analysis

### 12.1 Process domains

| Process / Service | Executable Label | Domain | Starts From | Confidence | Notes |
|---|---|---|---|---|---|
| `audioserver` | `u:object_r:audioserver_exec:s0` | `audioserver` | `audioserver.rc` | Confirmed | framework audio domain |
| `vendor.audio-hal` | not directly inspected | `hal_audio_default` / vendor audio domain | vendor init rc | Strong inference | vendor HIDL audio wrapper |
| `audio-daemon` | `u:object_r:audiocmdservice_atci_exec:s0` | `audiocmdservice_atci` | vendor init rc | Confirmed | engineering helper |

### 12.2 File and node labels

| Path / Node | Expected Label | Used By | Confidence | Notes |
|---|---|---|---|---|
| `/system/bin/audioserver` | `u:object_r:audioserver_exec:s0` | audioserver | Confirmed | platform file context |
| `/data/misc/audioserver(/.*)?` | `u:object_r:audioserver_data_file:s0` | audioserver | Confirmed | platform file context |
| `/data/voipdump(/.*)?` | `u:object_r:audioserver_data_file:s0` | audioserver / debugging | Confirmed | vendor file context |
| `/vendor/bin/audiocmdservice_atci` | `u:object_r:audiocmdservice_atci_exec:s0` | audio-daemon | Confirmed | vendor file context |

### 12.3 Service and property contexts

| Context Type | Name | Context Label | Role | Confidence | Notes |
|---|---|---|---|---|---|
| service_contexts | `media.aaudio` | `u:object_r:audioserver_service:s0` | audioserver service | Confirmed | framework audio service |
| service_contexts | `media.audio_flinger` | `u:object_r:audioserver_service:s0` | audioserver service | Confirmed | framework audio service |
| service_contexts | `media.audio_policy` | `u:object_r:audioserver_service:s0` | audioserver service | Confirmed | framework audio service |
| service_contexts | `media.sound_trigger_hw` | `u:object_r:audioserver_service:s0` | audioserver service | Confirmed | sound trigger binder name |
| service_contexts | `soundtrigger_middleware` | `u:object_r:soundtrigger_middleware_service:s0` | middleware | Confirmed | platform service label |
| hwservice_contexts | `android.hardware.audio::IDevicesFactory` | `u:object_r:hal_audio_hwservice:s0` | HIDL audio HAL | Confirmed | vendor audio factory |
| hwservice_contexts | `android.hardware.audio.effect::IEffectsFactory` | `u:object_r:hal_audio_hwservice:s0` | HIDL audio effect HAL | Confirmed | vendor effects factory |
| hwservice_contexts | `android.hardware.soundtrigger::ISoundTriggerHw` | `u:object_r:hal_audio_hwservice:s0` | HIDL soundtrigger HAL | Confirmed | hotword factory |
| service_contexts | `android.hardware.audio.core.IConfig/default` | `u:object_r:hal_audio_service:s0` | AIDL audio core label | Strong inference | no matching stock daemon found here |
| service_contexts | `android.hardware.audio.core.IModule/default` | `u:object_r:hal_audio_service:s0` | AIDL audio core label | Strong inference | no matching stock daemon found here |
| property_contexts | `vendor.streamout.` | `u:object_r:vendor_mtk_audiohal_prop:s0` | vendor tuning | Confirmed | vendor audio prop family |
| property_contexts | `vendor.streamin.` | `u:object_r:vendor_mtk_audiohal_prop:s0` | vendor tuning | Confirmed | vendor audio prop family |
| property_contexts | `vendor.a2dp.` | `u:object_r:vendor_mtk_audiohal_prop:s0` | vendor tuning | Confirmed | vendor audio prop family |
| property_contexts | `vendor.audiohal.` | `u:object_r:vendor_mtk_audiohal_prop:s0` | vendor tuning | Confirmed | vendor audio prop family |
| property_contexts | `persist.vendor.audiohal.` | `u:object_r:vendor_mtk_audiohal_prop:s0` | vendor tuning | Confirmed | vendor audio prop family |
| property_contexts | `persist.vendor.vow.` | `u:object_r:vendor_mtk_audiohal_prop:s0` | voice wake | Confirmed | vendor voice feature |
| property_contexts | `vendor.af.audioserver.restart` | `u:object_r:system_mtk_audio_prop:s0` | restart control | Confirmed | system_ext property context |

### 12.4 Enforcing-mode risks
The first likely denials are file/node access for `/dev/snd/*`, `/dev/audio_ipi`, `/dev/audio_scp`, and the SmartPA sysfs nodes. Secondary failures are service registration denials for `audioserver_service` or `hal_audio_hwservice` if the labels do not match the stock policy.

### 12.5 SELinux action items
- Keep `audioserver` in the `audioserver` domain with access to its data directory and service names.
- Preserve `hal_audio_hwservice` mappings for audio and effects.
- Preserve `vendor_mtk_audiohal_prop` mappings for `vendor.streamout.*`, `vendor.streamin.*`, `vendor.a2dp.*`, `vendor.audiohal.*`, `persist.vendor.audiohal.*`, and `persist.vendor.vow.*`.
- Preserve `system_mtk_audio_prop` for `vendor.af.audioserver.restart`.

---

## 13. Property Contract

### 13.1 Property inventory

| Property | Category | Default / Observed Value | Producer | Consumer | Trigger Role | Required | Confidence | Notes |
|---|---|---|---|---|---|---|---|---|
| `aaudio.mmap_policy` | capability toggle | `2` | vendor build.prop | `audioserver` / AAudio | performance | yes | Confirmed | low-latency MMAP policy |
| `aaudio.mmap_exclusive_policy` | capability toggle | `2` | vendor build.prop | `audioserver` / AAudio | performance | yes | Confirmed | exclusive MMAP policy |
| `ro.audio.silent` | behavior | `0` | system build.prop | framework audio | startup | yes | Confirmed | normal audible device |
| `ro.audio.usb.period_us` | transport/performance | `16000` | system build.prop | USB audio policy/HAL | tuning | yes | Confirmed | USB latency tuning |
| `ro.vendor.tran_audio_game_mode.support` | feature flag | `1` | vendor build.prop | vendor audio tuning | capability | no for base audio | Confirmed | enhancement only |
| `ro.vendor.mtk_audio_alac_support` | capability | `1` | vendor build.prop | vendor audio stack | capability | no for base audio | Confirmed | decoder support |
| `ro.vendor.mtk_audio_ape_support` | capability | `1` | vendor build.prop | vendor audio stack | capability | no for base audio | Confirmed | decoder support |
| `ro.vendor.mtk_audio_tuning_tool_ver` | debug/version | `V2.2` | vendor build.prop | vendor tuning tools | diagnostics | no | Confirmed | tooling version |
| `vendor.af.audioserver.restart` | startup gating | not set by default | external/debug | `audioserver.rc` | restart control | no | Confirmed | property-triggered restart |
| `persist.vendor.audiohal.*` | vendor tuning | family only | vendor property service | vendor audio HAL | tuning | yes for stock parity | Confirmed | mapped to MTK audio prop type |
| `persist.vendor.vow.*` | voice wake | family only | vendor property service | vendor audio HAL | tuning | only if VOW used | Confirmed | voice wake properties |

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
- `ro.audio.silent=0` only says the device is not globally muted; it does not prove routing or effect loading works.
- `aaudio.mmap_policy=2` only says the stack is configured for MMAP; it does not prove the kernel path is usable.
- `ro.vendor.tran_audio_game_mode.support=1` is enhancement-only and should not be used as a base bring-up indicator.

### 13.4 Minimal property set
The minimum properties that should be preserved for first bring-up are `aaudio.mmap_policy`, `aaudio.mmap_exclusive_policy`, `ro.audio.silent`, and `ro.audio.usb.period_us`, plus the vendor `persist.vendor.audiohal.*` namespace if the vendor HAL expects it at runtime.

---

## 14. Configuration Surface

### 14.1 Config file analysis
- `audio_policy_configuration.xml` controls core audio routes and module composition. The `primary` module defines speaker, earpiece, headset, BT SCO, USB, and voice-call paths.
- `audio_effects.xml` controls which audio effects are loaded and which pre/post-processing chains are applied. This file is where `libaudiopreprocessing_mtk.so` and `libdtsaudio.so` become relevant.
- `audio_device.xml` maps ALSA card/control names to mixer routes. The `card name="mt6781mt6366"` value must match the kernel ALSA card.
- `audio_param/*` contains the bulk of vendor tuning. The file names show per-domain presets for playback, recording, VoIP, USB, SmartPA, and speech enhancement.
- `dts/*` contains DTS licensing and profile configuration. This is required if the stock DTS effect remains enabled.

### 14.2 Critical configuration table

| Config File | Critical Fields / Keys | Must Match Hardware | Safe to Modify | Source / Blob / Overlay | Confidence | Notes |
|---|---|---|---|---|---|---|---|
| `vendor/etc/audio_policy_configuration.xml` | module names, device ports, routes | yes | limited | source/device tree | Confirmed | active policy |
| `vendor/etc/audio_effects.xml` | `pre_processing`, `dtsaudio`, UUIDs | yes | limited | source/device tree | Confirmed | effect loading |
| `vendor/etc/audio_device.xml` | `card name="mt6781mt6366"`, kctls | yes | no for first pass | vendor blob/config | Confirmed | primary mixer map |
| `vendor/etc/audio_param/*` | preset and per-mode tuning | yes | no for stock parity | vendor blob set | Confirmed | huge tuning surface |
| `vendor/etc/dts/customer.cfg` | DTS route/profile config | yes | no for stock parity | vendor blob set | Confirmed | DTS control path |
| `vendor/etc/dts/dts-eagle.lic` | license path / validation | yes | no | vendor blob set | Confirmed | mandatory for DTS |
| `system/etc/init/audioserver.rc` | service names and restart hooks | yes | yes | source tree | Confirmed | framework integration |
| `vendor/etc/init/android.hardware.audio.service.mediatek.rc` | service name, class, UID/GID | yes | yes | source tree | Confirmed | vendor init integration |

### 14.3 Config-level failure modes
- Wrong ALSA card name in `audio_device.xml` results in silent playback or open failures.
- Wrong route names in `audio_policy_configuration.xml` produce devices that appear in policy but never route.
- Missing `dtsaudio` or `pre_processing` libraries usually breaks effect loading or voice preprocessing, not basic boot.

---

## 15. Kernel Coupling

### 15.1 Driver / module overview
This subsystem depends on built-in ALSA/audio drivers plus vendor-specific device nodes and likely Mediatek audio DSP / SmartPA support. The user-space stack also expects USB audio, Bluetooth audio, and sound trigger kernel plumbing to exist.

### 15.2 Kernel module table

| Module / Driver | File Path / Config | Built-in or LKM | Probe Dependency | Firmware Request | User-space Consumer | Required | Confidence | Notes |
|---|---|---|---|---|---|---|---|---|
| ALSA sound card | kernel / `/dev/snd/*` | built-in or module | kernel boot | none shown | `audio.primary.mt6781.so`, USB/BT HALs | yes | Confirmed | base audio I/O |
| `audio_ipi` | `/dev/audio_ipi` | unknown | vendor HAL | none shown | primary HAL | yes | Confirmed | MTK DSP path |
| `audio_scp` | `/dev/audio_scp` | unknown | vendor HAL | none shown | primary HAL / SmartPA | yes | Confirmed | MTK SCP path |
| SmartPA controls | `/sys/bus/platform/devices/rt5509_param.*`, `mt6660-param.0` | unknown | device probe | none shown | audioserver / vendor HAL | yes | Confirmed | speaker amp tuning |
| USB audio | USB ALSA nodes | unknown | USB attach | none shown | `audio.usb.default.so` | yes for USB audio | Strong inference | accessory/device mode |
| Bluetooth audio | Bluetooth stack | built-in | BT stack | none shown | `audio.bluetooth.default.so` | yes for BT audio | Strong inference | A2DP/SCO/LE |
| Sound trigger | vendor audio trigger driver | unknown | vendor HAL | none shown | `android.hardware.soundtrigger@2.3-impl.so` | likely | Strong inference | hotword path |

### 15.3 Module load order
No explicit `modules.load` evidence was found for audio-specific modules in the inspected tree. The practical order is: kernel nodes first, then init permissions, then `vendor.audio-hal`, then `audioserver` and policy clients.

### 15.4 Device tree / DTBO / board config clues
The `audio.primary.mt6781.so` strings show `mt6781mt6366`, `AudioSmartPaController`, and `AudioUSBCenter`, which strongly suggest board-specific audio codec/amp configuration, but no DTBO or DTS source was inspected here.

### 15.5 Kernel bring-up requirements
Minimum kernel support appears to be:
- ALSA sound card and `/dev/snd/*`
- MTK audio IPI / SCP device nodes
- SmartPA sysfs nodes for the speaker amps
- USB audio support
- Bluetooth audio plumbing
- any sound-trigger hardware support needed by the vendor soundtrigger impl

---

## 16. Framework / App / Overlay Integration

### 16.1 Framework dependencies
`AudioFlinger`, `AudioPolicyService`, `AAudioService`, `sound trigger hardware`, Bluetooth audio routing, and USB accessory/audio policy all interact with this subsystem. The `audioserver` binary is the main framework integration point.

### 16.2 Permissions / features / sysconfig

| File | Type | Declares | Needed for Bring-up | Confidence | Notes |
|---|---|---|---|---|---|---|
| `vendor/etc/permissions/handheld_core_hardware.xml` | permissions XML | `android.hardware.audio.output`, `android.hardware.microphone` | yes | Confirmed | core handheld features |
| `vendor/etc/permissions/android.hardware.audio.low_latency.xml` | feature XML | `android.hardware.audio.low_latency` | yes if CTS expects it | Confirmed | low-latency flag |
| `vendor/etc/permissions/android.hardware.microphone.xml` | feature XML | `android.hardware.microphone` | yes | Confirmed | mic capability |
| `system/etc/permissions/platform.xml` | permissions XML | audioserver grants | yes | Confirmed | service permissions |
| `system_ext/etc/selinux/system_ext_property_contexts` | property context | `vendor.af.audioserver.restart` | no | Confirmed | restart control |
| `vendor/etc/sysconfig/*` | sysconfig | none directly audio-specific found | no | Weak inference | not central here |

### 16.3 APK/UI dependencies
- No dedicated audio app APK was identified as required for base bring-up.
- `vendor/etc/dts` implies a vendor DTS app or UI may exist elsewhere, but the package was not directly identified in this dump.

### 16.4 Framework integration risks
- The framework may advertise audio features even if the HAL or tuning assets are missing.
- AAudio can look healthy while MMAP or low-latency capture still fails.
- `audio_policy_configuration.xml` may parse successfully while route names do not actually match the HAL's available devices.

---

## 17. Packaging and ROM Integration Decision

### 17.1 File-by-file disposition
- Source-build: `system/bin/audioserver`, `system/etc/init/audioserver.rc`, `system/etc/permissions/platform.xml`, `system/etc/selinux/*` audio labels, `vendor/etc/audio_policy_configuration.xml` if reproduced in device tree, `vendor/etc/audio_effects.xml` if kept as device config.
- Extract proprietary unchanged: `vendor/bin/hw/android.hardware.audio.service.mediatek`, `audio.primary.mt6781.so`, `android.hardware.audio@7.0-impl-mediatek.so`, `audio.bluetooth.default.so`, `audio.usb.default.so`, `audio.r_submix.mt6781.so`, `android.hardware.soundtrigger@2.3-impl.so`, `libaudioloudc.so`, `libbessound_hd_mtk_vendor.so`, `lib_speech_enh.so`, `libMtkSpeechEnh.so`, DTS blobs, audio_param assets.
- Optional/debug only: `audiocmdservice_atci`, `tran_tinymix`, `audio_em.xml`, `usb_effect.ogg`.
- Replace with open-source alternative: possible later for some effects, preprocessing, and USB/BT policy glue, but not for the primary MTK HAL.
- Patch/shim required: only if you choose to drop or replace vendor enhancement chains.

### 17.2 Packaging matrix

| Artifact | Action | Destination Partition | Build Integration Method | Shim Needed | Confidence | Notes |
|---|---|---|---|---|---|---|
| `audioserver` | source-build | system | `PRODUCT_PACKAGES` | no | High | AOSP service |
| `android.hardware.audio.service.mediatek` | extract proprietary unchanged | vendor | proprietary-files | no | High | main vendor daemon |
| `audio.primary.mt6781.so` | extract proprietary unchanged | vendor | proprietary-files | no | High | core HAL |
| `android.hardware.audio@7.0-impl-mediatek.so` | extract proprietary unchanged | vendor | proprietary-files | no | High | factory impl |
| `audio.bluetooth.default.so` | extract proprietary unchanged | vendor | proprietary-files | no | High | BT audio routing |
| `audio.usb.default.so` | extract proprietary unchanged | vendor | proprietary-files | no | High | USB audio |
| `audio.r_submix.mt6781.so` | extract proprietary unchanged | vendor | proprietary-files | no | High | remote submix |
| `libaudioloudc.so` / `libbessound_hd_mtk_vendor.so` | extract proprietary unchanged | vendor | proprietary-files | no | High | enhancement chain |
| `lib_speech_enh.so` / `libMtkSpeechEnh.so` | extract proprietary unchanged | vendor | proprietary-files | no | High | voice tuning |
| `libdtsaudio.so` / `libdts-eagle-shared.so` / `libdtsdsec.so` | extract proprietary unchanged | vendor | proprietary-files | no | High | DTS |

### 17.3 Open-source replacement opportunities
- AOSP `audioserver` and the standard framework audio policy/effect scaffolding can stay source-built.
- USB audio policy and remote submix policy can likely be maintained as source config.
- Basic AOSP effects can replace some vendor enhancement features later, but not the primary HAL.

### 17.4 Non-negotiable proprietary set
- Vendor primary audio HAL and its implementation library chain
- SmartPA and device-specific tuning assets
- Voice enhancement / DMNR / Bessound / DTS blobs if stock feature parity matters
- Bluetooth vendor audio extension blobs

---

## 18. Validation Plan

### 18.1 First smoke tests
- `service list | grep -E 'audio|sound_trigger'`
- `lshal | grep -E 'android.hardware.audio|soundtrigger|bluetooth.audio'`
- `dumpsys media.audio_flinger`
- `dumpsys media.audio_policy`
- `dumpsys audio`
- Play a system sound and verify speaker output.
- Record from the main microphone and verify PCM capture.
- Plug/unplug a wired headset and verify route changes.
- Pair Bluetooth audio and verify A2DP playback.

### 18.2 Deep validation tests
- USB audio accessory and USB headset tests.
- Voice call / VoIP path test.
- Sound trigger / hotword enrollment and detection.
- MMAP low-latency AAudio test.
- Effect loading test for AEC/NS/AGC and DTS if enabled.
- Long playback + thermal + speaker protection behavior.

### 18.3 Recommended shell commands
- `getprop | grep -E 'audio|aaudio|dts|vow|audiohal'`
- `logcat -b all | grep -E 'audioserver|AudioFlinger|AudioPolicy|soundtrigger|audiohal|dts|bessound'`
- `ls -lZ /dev/snd`
- `ls -lZ /data/misc/audioserver /data/vendor/audiohal /data/vendor/audio`
- `ps -AZ | grep -E 'audioserver|audio-daemon|vendor.audio-hal'`
- `dumpsys media.audio_flinger`
- `dumpsys media.audio_policy`
- `lshal`

### 18.4 Expected success signals
- `audioserver` registers `media.audio_flinger`, `media.audio_policy`, `media.aaudio`, and `media.sound_trigger_hw`.
- `hwservicemanager` shows `android.hardware.audio::IDevicesFactory/default`, `android.hardware.audio.effect::IEffectsFactory/default`, and `android.hardware.soundtrigger::ISoundTriggerHw/default`.
- `dumpsys media.audio_policy` lists the primary, Bluetooth, USB, and remote-submix modules.

---

## 19. Failure Modes and Triage

| Failure | Symptom | Most Likely Cause | First Check | Fix Direction | Confidence | Notes |
|---|---|---|---|---|---|---|
| Service not starting | no `audioserver` / vendor HAL process | wrong rc or file context | `ps -AZ`, `logcat` | fix init/service labels | High | boot-time failure |
| HAL registration fails | `lshal` missing audio factories | missing VINTF or `hwservice_contexts` | `lshal`, `logcat` | restore manifest and contexts | High | no HAL discovery |
| Audio starts but silent | app opens stream, no sound | wrong primary HAL / mixer / card name | `dmesg`, `logcat`, `audio_device.xml` | fix `audio.primary.mt6781.so` path and card map | High | common first failure |
| Mic capture dead | no input or zeroed samples | `/dev/snd/*` or capture node permission | `ls -lZ /dev/snd`, SELinux logs | fix ueventd / sepolicy | High | capture path |
| Effects missing | no AEC/DTS/Bessound | missing soundfx blobs or XML | `logcat` effect load logs | restore `libdtsaudio.so`, `libaudiopreprocessing_mtk.so` | Medium | base audio may still work |
| BT audio broken | no A2DP/SCO | missing BT audio modules | `lshal`, `logcat` | restore BT audio libs and policy | Medium | route-specific |
| USB audio broken | headset not detected | missing USB module or policy | `dumpsys media.audio_policy` | restore `audio.usb.default.so` and USB policy | Medium | accessory/device paths |
| SELinux denial | service loops or nodes denied | wrong labels/domains | `dmesg`, `logcat` avc | fix file contexts and allow rules | High | common on first port |
| Sound trigger broken | hotword never loads | missing soundtrigger impl or route | `lshal`, `logcat` | restore soundtrigger impl and manifest | Medium | often overlooked |

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
- Required binaries: `system/bin/audioserver`, `vendor/bin/hw/android.hardware.audio.service.mediatek`, `vendor/lib64/hw/android.hardware.audio@7.0-impl-mediatek.so`, `vendor/lib64/hw/audio.primary.mt6781.so`
- Required libraries: `android.hardware.audio.effect@7.0-impl.so`, `audio.bluetooth.default.so`, `audio.usb.default.so`, `audio.r_submix.mt6781.so`, `android.hardware.soundtrigger@2.3-impl.so`, `libaudioutils.so`, `libtinyalsa.so`, `libalsautils.so`
- Required configs: `vendor/etc/audio_policy_configuration.xml`, `vendor/etc/audio_effects.xml`, `vendor/etc/audio_device.xml`, `vendor/etc/audio_param/*`, `vendor/etc/permissions/handheld_core_hardware.xml`, `vendor/etc/permissions/android.hardware.microphone.xml`, `vendor/etc/permissions/android.hardware.audio.low_latency.xml`
- Required manifest entries: `android.hardware.audio@7.0`, `android.hardware.audio.effect@7.0`, `android.hardware.bluetooth.audio@2.1`, `vendor.mediatek.hardware.bluetooth.audio@2.2`, `android.hardware.soundtrigger@2.3`
- Required init fragments: `system/etc/init/audioserver.rc`, `vendor/etc/init/android.hardware.audio.service.mediatek.rc`
- Required nodes / sysfs / proc paths: `/dev/snd/*`, `/dev/audio_ipi`, `/dev/audio_scp`, SmartPA sysfs nodes, `/data/misc/audioserver`, `/data/vendor/audiohal`
- Required properties: `aaudio.mmap_policy`, `aaudio.mmap_exclusive_policy`, `ro.audio.silent`, `ro.audio.usb.period_us`
- Required SELinux labels/domains: `audioserver`, `hal_audio_hwservice`, `audioserver_exec`, `audioserver_data_file`, `vendor_mtk_audiohal_prop`
- Required kernel support: ALSA sound card, MTK audio IPI/SCP nodes, SmartPA control nodes, USB audio, Bluetooth audio, sound trigger support if hotword is kept

### 21.2 What can be omitted initially
- DTS/Bessound/speech enhancement stack if you only want basic playback and capture
- `audiocmdservice_atci` and `tran_tinymix`
- `audio_em.xml`
- `usb_effect.ogg`
- USB accessory audio if you are not validating that route yet

### 21.3 What can be open-sourced later
- `audioserver`
- standard audio policy and effect XMLs
- USB and remote-submix policy config
- SELinux and property glue in the device tree

### 21.4 Known unknowns
- Exact kernel driver names and module load order were not directly inspected.
- No runtime logs were available.
- The AIDL audio core service contexts exist in platform policy, but no matching stock daemon or manifest entry was observed.

### 21.5 Final verdict
High risk and medium-high difficulty. Basic audio bring-up is realistic if the stock vendor HAL and tuning files are kept intact; replacing the vendor primary path or tuning stack early is likely to break routing, capture, or enhancement features.

---

## 22. Appendix A - Raw Evidence
- `system/etc/init/audioserver.rc`: `service audioserver /system/bin/audioserver`
- `vendor/etc/init/android.hardware.audio.service.mediatek.rc`: `service vendor.audio-hal /vendor/bin/hw/android.hardware.audio.service.mediatek`
- `vendor/etc/vintf/manifest.xml`: `android.hardware.audio` 7.0, `android.hardware.audio.effect` 7.0, `android.hardware.soundtrigger` 2.3
- `system/etc/selinux/plat_hwservice_contexts`: `android.hardware.audio::IDevicesFactory`, `android.hardware.audio.effect::IEffectsFactory`, `android.hardware.soundtrigger::ISoundTriggerHw` mapped to `hal_audio_hwservice`
- `system/etc/selinux/plat_service_contexts`: `media.aaudio`, `media.audio_flinger`, `media.audio_policy`, `media.sound_trigger_hw`
- `vendor/etc/selinux/vendor_property_contexts`: `vendor.streamout.`, `vendor.streamin.`, `vendor.a2dp.`, `vendor.audiohal.`, `persist.vendor.audiohal.`, `persist.vendor.vow.` mapped to `vendor_mtk_audiohal_prop`
- `vendor/etc/audio_effects.xml`: `pre_processing` uses `libaudiopreprocessing_mtk.so`, effect `dtsaudio` uses `libdtsaudio.so`
- `vendor/etc/audio_device.xml`: `card name="mt6781mt6366"`
- `vendor/lib64/hw/audio.primary.mt6781.so`: `AudioSmartPaController`, `AudioUSBCenter`, `modules.usbaudio.audio_hal`
- `vendor/lib64/soundfx/libdtsaudio.so`: `ro.vendor.dts.licensepath`, `ro.vendor.dts.cfgpath`, `/vendor/etc/dts/`, `/data/vendor/audio/dts/`

---

## 23. Appendix B - Commands Used
- `file`
- `readelf -d`
- `strings -a`
- `grep`
- `read`
- `glob`

---

## 24. Appendix C - Confidence Annotations
- Confirmed: service binaries, rc files, manifest entries, config files, permissions, SELinux labels, and most paths were directly observed.
- Strong inference: `audio_proxy_service`/legacy alias handling, some kernel driver coupling, and AIDL audio core relevance.
- Weak inference: exact runtime behavior of optional enhancement chains and any missing kernel module load order.

---

## 25. Live Custom-ROM Reassessment

### 25.1 Current state
- `audioserver` is running.
- `media.audio_flinger`, `media.audio_policy`, and `media.aaudio` are present in `service list`.
- `dumpsys audio` shows active speaker/earpiece routing and normal volume groups.
- `lshal` shows the audio and soundtrigger HALs in the expected namespace.

### 25.2 Log review
- No audio-specific fatal failure stands out in the current logs.
- The `avc: denied` lines that showed up during inspection are mostly shell-query noise or unrelated app/service accesses.
- One unrelated runtime warning remains: `Can't load library: dlopen failed: library "libmagtsync.so" not found`, but it does not currently correlate with audio service failure.

### 25.3 Conclusion
- Audio does not currently look broken on the custom ROM.
- There is no proven audio root cause to fix from the available evidence.

### 25.4 Device-tree recommendation
- No immediate audio device-tree change is proven necessary.
- Keep the stock audio HAL blobs, policy XMLs, DTS assets, and init glue intact unless a concrete playback/capture failure is reproduced.
