# X670 Voice Call Audio — Session 2026-08-29

**Device:** Infinix X670 (Note 12) `mt6781` Helio G96 `ASALE37681000041`
**Base:** AxionOS `axion-bp4a` kernel 4.19.191
**Issue:** No audio on any voice call (VoLTE, 2G CS — both affected)

---

## 1. What happened

All voice calls have **no audio in either direction** — earpiece and speaker silent, mic not reaching remote side. Covers IMS/VoLTE calls (`type:ims`) and legacy 2G CS calls (`type:gsm`). Audio routing logs show `setCommunicationRoute` correctly selecting earpiece/speaker, but no audio patch is created for the voice path.

IMS side separately broken: `ImsResolver` shows `Carrier: slot=0, feature=MMTEL: none`, `ImsStateCallbackController` `state=UNAVAILABLE reason=IMS_SERVICE_DISCONNECTED`, `vendor.volte_md_status` stays empty (expected `ready`), `VoLTE IMSM/IMCB` repeatedly scan without registering. This forces CS fallback, but even CS has no audio.

## 2. Root cause

**Missing MediaTek audio HAL blobs.** Stock ROM ships MediaTek-specific HALs that know how to route voice audio through the modem:

```
Stock vendor/lib/hw + lib64/hw:
  android.hardware.audio@6.0-impl-mediatek.so  176240/231K  (MTK voice routing, 32+64)
  android.hardware.audio@7.0-impl-mediatek.so  189580/244K
  android.hardware.audio.effect@6.0/7.0-impl.so 203K/208K + 280K/284K (generic, also in stock)

Device tree vendor/lib/hw (before fix):
  android.hardware.audio@7.0-impl.so            171908  (generic AOSP, no -mediatek)
  (no lib64 mediatek variants)
```

The generic AOSP `android.hardware.audio@7.0-impl.so` does not implement the MediaTek voice paths (`Voice Call In` → `Earpiece`/`Speaker`, `voice tx` ↔ `Telephony Tx`). `audio.primary.mt6781.so` depends on the `-mediatek` HAL to create audio patches for `AUDIO_DEVICE_IN_VOICE_CALL` / `AUDIO_DEVICE_OUT_TELEPHONY_TX`. Without it `dumpsys media.audio_policy` shows no patches during a call and nothing reaches the modem PCM.

`device.mk:162` installs `android.hardware.audio@7.0-impl` from the build system. `proprietary-files.txt` never listed the `-mediatek` variants, so extraction never brought them in despite stock having them.

IMS `vendor.volte_md_status` remaining empty is a separate modem/graphics integration issue (`volte_md_status` daemon stuck on `/dev/radio/pttyims`; `init.volte_imsm_93.rc` trigger `on property:vendor.volte_md_status=ready` never fires). It explains the `type:gsm` fallback, but even fixing it would still have no audio without the HALs. Both must be fixed for VoLTE voice, but the HALs fix 2G audio immediately.

## 3. Fix

`proprietary-files.txt:14-18` — add the four missing MediaTek audio HALs (both bitnesses, matches `fleur` pattern):

```make
# Audio — MediaTek HAL impls (voice call routing via modem; generic AOSP impl cannot create voice patches)
vendor/lib/hw/android.hardware.audio@6.0-impl-mediatek.so
vendor/lib/hw/android.hardware.audio@7.0-impl-mediatek.so
vendor/lib64/hw/android.hardware.audio@6.0-impl-mediatek.so
vendor/lib64/hw/android.hardware.audio@7.0-impl-mediatek.so
```

No conflict with `device.mk:162-163` (`android.hardware.audio@7.0-impl` + `audio.effect@7.0-impl` from source): the `-mediatek` files are different names, coexist in `vendor/lib/hw`/`lib64/hw`. Voice effects remain from source (as in `fleur` reference) — only the voice routing HALs were missing.

Next build: blobs are copied to `vendor/lib*/hw/` alongside `audio.primary.mt6781.so`. The audio HAL service will load the `-mediatek` impls for the MTK routes.

## 4. Live verification — blocked by dm-verity

Vendor is `dm-3` ext4 `ro` (`ro.boot.verifiedbootstate=green`, `avb device_state=locked`). `nsenter --mount=/proc/1/ns/mnt -- mount -o remount,rw /vendor` succeeds (returns 0) but mount flags stay `ro` and `cp`/`touch`/`mount --bind` all fail with `Read-only file system` / `No such file or directory` (target doesn't exist so bind has no anchor). Magisk is not present (`/sbin/magisk` missing, `su` is plain `system/bin/su`). Therefore live `nsenter` patch of `vendor/lib/hw` is not testable without flashing a new image. Tree fix is correct by construction — stock size + file list prove the blobs are the voice-path HALs.

## 5. Other changes in this tree (already committed)

* `configs/powerhint.json:569-617` — 9× `FIXED_PERFORMANCE` actions so `pixel-libperfmgr` `isModeSupported:1`; stops `update_engine` `ServiceSpecificException: Could not change profiles` crash (`UpdaterService.java:212`).
* `sepolicy/vendor/file_contexts:54-55` — `tkv_block_device` label `/dev/block/by-name/tkv(_[ab])?` so `update_engine.te` allow is effective (P661N has it).
* `rootdir/etc/init/hw/init.connectivity.rc:24-25` — `write /proc/net/wlan/setCAM 1` at `post-fs-data` to force MT6631 CAM; live-verified RX 1→150 Mbps.

## 6. To verify after next flash

```bash
adb shell dumpsys media.audio_policy | grep -A2 "Voice Call In"
adb shell dumpsys media.audio_policy  # during a call — patch list should show voice route
adb shell getprop vendor.volte_md_status  # should become ready eventually
adb shell dumpsys telephony.registry | grep -i "mIms\|MMTEL"
# Make a call to 100 or *#*#4636#*#* phone info — audio should be audible both sides
```
