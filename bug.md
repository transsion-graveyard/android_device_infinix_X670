# Custom ROM Bring Up Checklist

> Mark anything as:
>   [ ] Not tested
>   [x] Working
>   [-] Not present on this device
>   [!} Bug / partial / broken

## 1) Boot / basic system
  [x] Clean flash completes without errors
  [x] First boot succeeds
  [x] Boot time is reasonable
  [x] No bootloop after first setup
  [x] Reboot works
  [x] Power off works
  [x] Warm reboot works
  [x] Recovery boots
  [x] Fastboot / bootloader mode works
  [x] ADB works in system
  [x] ADB works in recovery
  [x] Device can boot again after charging while powered off
  [x] No random reboots / kernel panics
  [!] No major spam in logcat / dmesg for core services

## 2) Setup wizard / provisioning
  [x] Setup wizard completes
  [x] Language selection works
  [x] Wi Fi setup during first boot works
  [ ] Google account sign in works (if GApps included)
  [z] Date / time auto sync works
  [ ] Restore flow works (if applicable)
  [z] Device encryption state survives setup
  [z] Lock screen can be configured during setup

## 3) UI / display / graphics
  [x] Display turns on reliably
  [z] Brightness slider works
  [z] Auto brightness works
  [-] Refresh rate switching works
  [ ] Color modes work
  [x] Night Light / reading mode works
  [ ] Always on display works (if supported)
  [ ] Ambient display / tap to wake works
  [ ] Rotation works
  [ ] GPU acceleration feels normal
  [x] No black screen / flicker / artifacting
  [ ] Screen recorder works
  [x] Screenshot works
  [ ] E ternal display out works (USB C / HDMI / wireless), if supported
  [ ] DRM protected content behavior is as e pected

## 4) Touch / input / haptics / buttons
  [x] Touchscreen works across whole panel
  [x] Multi touch works
  [z] Touch latency feels normal
  [z] Edge touch rejection behaves correctly
  [z] Gesture navigation works
  [z] 3 button navigation works
  [z] Back gesture works on both sides
  [x] Hardware keys work (power / volume / others)
  [z] Double tap to wake works
  [z] Double tap to sleep works
  [ ] Glove / high sensitivity mode works, if supported
  [z] Vibration works
  [z] Haptic feedback strength is correct
  [-] Fingerprint on display touch area wakes properly, if applicable

## 5) Lockscreen / biometrics / security
  [z] PIN works
  [z] Pattern works
  [z] Password works
  [z] Lock / unlock is stable
  [z] Smart lock / e tend unlock works, if used
  [z] Fingerprint enrollment works
  [z] Fingerprint unlock works from screen off
  [z] Fingerprint unlock works from AOD / lock screen
  [z] Fingerprint app authentication works
  [z] Multiple fingerprints can be added
  [z] Failed attempt behavior is correct
  [z] Face unlock works, if present
  [z] BiometricPrompt works in apps
  [z] Keystore backed auth works
  [z] Lockout / fallback to credential works
  [x] SELinu  is enforcing
  [x] File based encryption is working
  [x] Verified Boot / AVB state is understood and e pected
  [ ] Safety/security warnings shown to user are correct for bootloader state

## 6) Telephony / SIM / IMS
  [x] Physical SIM detected
  [ ] Dual SIM works, if supported
  [-] eSIM detected and can be provisioned, if supported
  [x] Network registers on carrier
  [!] Signal bars update correctly
  [ ] Outgoing calls work
  [ ] Incoming calls work
  [ ] Earpiece audio works during calls
  [ ] Mic works during calls
  [ ] Speakerphone works during calls
  [ ] Call waiting works
  [ ] Caller ID works
  [ ] DTMF tones work
  [ ] SMS send works
  [ ] SMS receive works
  [ ] MMS send works
  [ ] MMS receive works
  [x] Mobile data works
  [ ] 2G/3G/4G/5G modes switch correctly as supported
  [ ] VoLTE works
  [ ] VoWiFi / Wi Fi Calling works
  [ ] IMS registers correctly
  [ ] Carrier video calling works, if e pected
  [ ] APNs are correct
  [ ] Airplane mode works
  [ ] Emergency dialing flow behaves correctly

## 7) Wi Fi / hotspot / network
  [x] Wi Fi toggles on/off
  [ ] 2.4 GHz networks connect
  [ ] 5 GHz networks connect
  [-] 6 GHz / Wi Fi 6E / Wi Fi 7 connect, if supported
  [ ] Hidden SSID connect works
  [ ] WPA2 works
  [ ] WPA3 works
  [ ] Captive portal detection works
  [ ] MAC randomization behaves correctly
  [ ] Wi Fi reconnect after reboot works
  [ ] Wi Fi reconnect after sleep works
  [ ] Throughput is normal
  [ ] Hotspot / tethering works
  [ ] USB tethering works
  [ ] Bluetooth tethering works
  [ ] Wi Fi Direct works, if supported
  [ ] Wi Fi Aware works, if supported
  [ ] Passpoint works, if supported
  [ ] Per app VPN works
  [ ] Private DNS works

## 8) Bluetooth / wearables / accessories
  [x] Bluetooth toggles on/off
  [x] Device scanning works
  [x] Pairing works
  [ ] Unpairing works
  [x] Reconnect works after reboot
  [ ] BLE scanning works
  [ ] BLE connection works
  [ ] File transfer works, if used
  [x] Audio to TWS earbuds works
  [ ] Audio to speaker works
  [ ] Car Bluetooth works
  [ ] Call audio over Bluetooth works
  [ ] Media controls over Bluetooth work
  [ ] Metadata / track info displays correctly
  [ ] Multiple paired devices behave correctly
  [ ] Smartwatch pairing works
  [ ] Nearby device permission behavior is correct

## 9) NFC / wallet / payments
  [-] NFC toggles on/off
  [-] Tag reading works
  [-] NDEF read works
  [-] NDEF write works
  [ ] Android Beam replacement / sharing equivalent works, if used
  [ ] Host card emulation works, if supported
  [ ] Contactless payment/wallet behavior is as e pected
  [ ] Transit / access card apps detect NFC correctly
  [ ] Reader mode works

## 10) GPS / GNSS / location
  [x] Location toggle works
  [ ] GPS gets first fi 
  [ ] Cold start lock works
  [ ] Warm start lock works
  [ ] Accuracy is reasonable outdoors
  [ ] Speed / heading update correctly
  [ ] Multiple constellations show up, if supported
  [ ] Network based location works
  [ ] Indoor coarse location behaves normally
  [ ] Location permission prompts work
  [ ] Background location behavior is correct
  [ ] Emergency / high priority location behavior is sane

## 11) Sensors
  [x] Accelerometer works
  [x] Gyroscope works
  [x] Magnetometer / compass works
  [x] Pro imity sensor works
  [x] Light sensor works
  [-] Barometer works, if present
  [-] Hall sensor works, if present
  [x] Step counter works, if present
  [x] Step detector works, if present
  [x] Significant motion works, if present
  [ ] Sensor calibration is stable
  [ ] Sensor values survive suspend/resume
  [ ] No stuck sensor readings
  [ ] Auto rotate and pro imity in call both behave correctly

## 12) Audio
  [x] Main speaker works
  [ ] Earpiece works
  [ ] Stereo channels are correct
  [ ] Loudspeaker volume range is normal
  [ ] Headphone audio works via 3.5 mm jack, if present
  [ ] USB audio works
  [x] Bluetooth audio works
  [x] Mic records properly
  [ ] Secondary / noise cancel mic works
  [x] Voice recorder works
  [ ] Video recording audio works
  [ ] In call audio routing works
  [ ] Alarm sound works
  [ ] Notification sound works
  [x] Media playback works
  [ ] Low latency / gaming audio feels normal
  [ ] No popping / crackling / distortion
  [ ] Audio effects / equalizer / Dolby / spatial audio work, if included

## 13) Camera / flashlight
  [x] Camera app opens
  [x] Rear main camera works
  [x] Front camera works
  [ ] Ultrawide camera works, if present
  [ ] Telephoto camera works, if present
  [ ] Macro camera works, if present
  [x] Flashlight toggle works
  [ ] Flash works in camera
  [x] Photo capture works
  [ ] HDR works
  [ ] Portrait mode works
  [ ] Night mode works
  [ ] Panorama works
  [ ] Video recording works
  [ ] 60 fps recording works, if supported
  [ ] 4K recording works, if supported
  [ ] Slow motion works, if supported
  [ ] Stabilization works
  [ ] Autofocus works
  [ ] Tap to focus works
  [ ] E posure control works
  [ ] Zoom works
  [x] Camera switching is stable
  [ ] Third party camera apps work
  [ ] QR scanning works
  [ ] Camera works after suspend/resume
  [ ] Camera works after repeated open/close cycles
  [ ] No green tint / crash / black preview

## 14) Storage / files / SD card
  [ ] Internal storage mounts correctly
  [ ] Correct capacity shown
  [ ] Read / write works
  [ ] MTP file transfer works
  [ ] SAF / file picker works
  [ ] App install works
  [ ] App updates work
  [ ] ADB push / pull works
  [ ] OTG storage works
  [ ] microSD detected, if present
  [ ] microSD read/write works
  [ ] Adoptable storage works, if used
  [ ] E FAT / NTFS behavior is as e pected, if supported

## 15) USB / OTG / peripherals
  [x] USB connection detected reliably
  [ ] File transfer mode works
  [ ] Charge only mode works
  [x] USB debugging authorization works
  [ ] OTG works
  [ ] USB keyboard works
  [ ] USB mouse works
  [ ] USB DAC works
  [ ] USB camera works, if supported
  [ ] Host/device role switching works
  [ ] Fast charging negotiates correctly
  [x] PC recognizes device consistently

## 16) Media / codecs / streaming
  [ ] Hardware video decode works
  [ ] Hardware video encode works
  [ ] H.264 playback works
  [ ] HEVC playback works
  [ ] VP9 playback works
  [ ] AV1 playback works, if supported
  [ ] Widevine level is reported as e pected
  [ ] YouTube playback works
  [ ] Local high bitrate playback works
  [ ] Recording and playback sync is correct
  [ ] No codec crashes / OM  / Codec2 issues

## 17) Power / battery / thermals
  [x] Battery percentage is correct
  [ ] Charging animation works
  [ ] Slow / normal / fast charging are detected correctly
  [ ] Battery health info is shown correctly, if supported
  [x] Deep sleep works
  [ ] Idle drain is normal
  [ ] Screen on battery drain is reasonable
  [ ] Thermal throttling works
  [ ] Device does not overheat abnormally
  [ ] Thermal warnings appear correctly
  [ ] Charging while using camera/navigation/gaming is stable

## 18) Sleep / wake / doze
  [x] Screen turns off normally
  [x] Device enters sleep
  [ ] Device wakes with power button
  [ ] Device wakes with fingerprint
  [ ] Device wakes with double tap, if supported
  [ ] Notifications arrive during doze as e pected
  [ ] Alarms fire correctly in idle
  [ ] Wi Fi / mobile data recover after wake
  [ ] Bluetooth recovers after wake

## 19) Apps / permissions / U 
  [ ] Permission prompts show correctly
  [ ] Camera permission works
  [ ] Mic permission works
  [ ] Location permission works
  [ ] Nearby devices permission works
  [ ] Notification permission works
  [ ] Scoped storage behavior is normal
  [ ] Split screen works
  [ ] Picture in picture works
  [ ] Recents screen works
  [ ] App pinning works
  [ ] Clipboard / share sheet work
  [ ] WebView works
  [ ] Play Store works, if included
  [ ] Play Services behave normally, if included
  [ ] Banking / work / auth apps behave as e pected for your bootloader/root state

## 20) Recovery / OTA / partitions
  [ ] Dirty flash update succeeds
  [ ] Clean flash still boots after format data
  [ ] OTA package installs, if your ROM supports OTA
  [ ] Post OTA reboot succeeds
  [ ] Data is preserved after OTA, when e pected
  [ ] Slot switching works on A/B devices
  [ ] Rollback / fallback behavior works if an update fails
  [ ] Recovery sideload works
  [ ] Dynamic partitions behave correctly
  [ ] Vendor / boot / dtbo / vbmeta handling is correct

## 21) Root / modding sanity (if relevant)
  [ ] Magisk boots
  [ ] Modules don’t break boot
  [ ] Zygisk behavior is normal
  [ ] DenyList / root hiding behavior matches e pectations
  [ ] ADB root works on userdebug/eng builds only
  [ ] KernelSU / APatch behavior is stable, if used
  [ ] Root does not break biometrics, NFC, or calls une pectedly

## 22) Final stability checks
  [ ] 10+ reboots without issue
  [ ] 24 hour idle test passes
  [ ] Long call test passes
  [ ] Long camera recording test passes
  [ ] Long GPS navigation test passes
  [ ] Long Bluetooth audio session passes
  [ ] Charging overnight is stable
  [ ] No major memory leaks
  [ ] No severe UI jank
  [ ] No reproducible crash in everyday use

## 23) Validation / compatibility pass
  [x] Feature flags match actual hardware
  [ ] CTS basic pass
  [ ] CTS Verifier smoke pass
  [ ] VTS/HAL sanity pass, if you’re doing device side bring up work
  [ ] Camera ITS pass / major items pass
  [x] SELinu  denials reviewed
  [x] Encryption / Direct Boot behavior reviewed
  [x] Verified Boot / AVB status reviewed
  [x] Logs reviewed for missing services / dead HALs / crashes

## Notes / bugs
  [x] Verified now: recovery adb, rear/front camera stills, audio record/playback, Bluetooth audio.
  [!] Bug 1: audioserver and mediaserver hit repeated AVC denials reading `vendor_default_prop` at boot.
  [!] Bug 2: BluetoothPowerStatsCollector logs controller energy-info errors at boot; looks like non-blocking log spam.
  [-] Bug 3: NFC service/feature is not present on this device; `com.android.nfc` is installed, but no NFC feature/service is exposed.
  [!] Needs vendor blob fi 
  [!] Needs sepolicy fi 
  [ ] Needs kernel fi 
  [ ] Needs overlay/config fi 
