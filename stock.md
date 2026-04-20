# Stock Analysis Report

Device: Infinix X670-GL
State: stock ROM, locked bootloader, green verified boot
Build: vendor `240224V150`, system/product `240224V556`

## Summary

- Audio: healthy at framework and service level.
- USB: healthy, with adb and MTP/configured gadget state active.
- Fingerprint: HAL and vendor extension register, sensor is visible to framework; stock logs still show Trustonic/TEE noise, but no current structural blocker from service registration.

## Audio

### Stock state
- `audioserver` is running.
- `media.audio_flinger`, `media.audio_policy`, and `media.aaudio` are present in `service list`.
- `dumpsys audio` shows active routes, working volume groups, and normal mode.
- `logcat` shows normal playback activity and no fatal audio HAL errors.

### Nodes / permissions
- Audio policy and tuning are driven by stock vendor configs, not by ad hoc nodes.
- No obvious audio node permission failures appeared in the captured stock logs.

### Config / init
- Stock audio stack is split across `audioserver` and `vendor.audio-hal`.
- Vendor policy files, effects XML, and tuning assets are present in the stock report.

### SELinux
- No audio-specific AVC blocker was identified in the captured stock state.

### Assessment
- Audio is working at the stock service/config level.
- Remaining validation would be real playback and capture tests, but the stock framework state is healthy.

## USB

### Stock state
- `usb` service is present in `service list`.
- `dumpsys usb` reports `connected=true`, `configured=true`, `kernel_state=CONFIGURED`.
- `adbd` is active and `sys.usb.state=adb`.
- USB event logs show gadget enable/configure transitions and MTP chooser activity.

### Nodes / permissions
- Stock USB uses configfs/functionfs and MTK gadget plumbing.
- `sys.usb.controller=musb-hdrc` and `sys.usb.configfs=1` are set.

### Config / init
- `vendor/etc/init/hw/init.mt6781.usb.rc` is the main gadget bring-up script.
- `system/etc/init/hw/init.usb.rc`, `system/etc/init/hw/init.usb.configfs.rc`, and `system/etc/init/usbd.rc` are present in the stock tree.

### SELinux
- Captured USB logs contain unrelated AVC noise from other domains, but no USB-specific failure blocked gadget bring-up.

### Assessment
- USB is working in stock state: adb is alive and the gadget is configured.
- MTP chooser and USB HAL transitions are functioning.

## Fingerprint

### Stock state
- `android.hardware.biometrics.fingerprint@2.1::IBiometricsFingerprint/default` is registered in `lshal`.
- `vendor.fpsensor.hardware.fpsensorhidlsvc@2.0::IFpsensorHidlSvc/default` is registered in `lshal`.
- `dumpsys biometric` shows `Sensors: ID(0), oemStrength: 15, updatedStrength: 15, modality 2`.
- `dumpsys fingerprint` shows `Fingerprint21` with no HAL deaths.

### Nodes / permissions
- Stock fingerprint node contract is `/dev/fpsensor`.
- Stock init policy expects `chmod 664 /dev/fpsensor` and `chown system root /dev/fpsensor`.
- Stock SELinux file contexts label `/dev/fpsensor` as `fpsensor_fp_device`.
- Related biometric nodes `/dev/biometric` and `/dev/m_bio_misc` are also part of the stock tree.

### Config / init
- Main daemon: `/vendor/bin/hw/android.hardware.biometrics.fingerprint@2.1-service` via `vendor.fps_hal`.
- Vendor extension service is declared in `vendor/etc/vintf/manifest.xml`.
- Stock report also notes `init.sensor_1_0.rc` for adjacent biometric sensor permissions.

### SELinux
- Live denial history showed the HAL requires the correct `fpsensor_fp_device` label on the actual node.
- Stock policy includes the needed file context and service labels.

### TEE / Trustonic notes
- Stock logs contain recurring Trustonic noise such as `TeeEndorsementInstaller` warnings and `TCI has not been set up properly` during some fingerprint paths.
- Stock boot logs also show Trustonic TEE is otherwise present and initialized for keymaster / secure world.
- Conclusion: TEE warnings exist on stock and should be treated as baseline noise unless paired with a concrete fingerprint failure.

### Assessment
- Fingerprint is structurally present and registered on stock.
- The live device sees the sensor in framework services, so the stock issue is not a missing HAL.
- Any remaining problem would need a functional enroll/auth test to prove.

## Cross-Subsystem Notes

- The device is a mixed build: vendor 12 with framework 13.
- Verified boot is green and the device is locked.
- Stock logs include unrelated SELinux denials from other apps/services; do not treat those as subsystem blockers unless tied to audio, USB, or fingerprint.

## Recommended Validation Order

1. Audio playback and recording test.
2. USB reconnect test with adb and MTP.
3. Fingerprint enroll/auth test.
4. Post-reboot repeat of the three tests.

## Current Conclusion

- Audio: working.
- USB: working.
- Fingerprint: present and registered; needs functional enrollment/auth verification, but stock wiring is in place.
