# X670 Local Update, WiFi & Power — Session 2026-08-29

**Device:** Infinix X670 (Note 12) `mt6781` Helio G96, `ASALE37681000041`
**ROM base:** AxionOS `axion-bp4a` (lineage kernel 4.19.191, `mt6781`)
**Power HAL:** `android.hardware.power-service.pixel-libperfmgr` (`device.mk:323`)
**WiFi:** MT6631 `wlan_drv_gen4m` firmware `t-neptune-main-soc2_2-2118` (`vendor.wlan.firmware.version`)
**Tools:** `adb` `Enforcing` `su --mount-master` `nsenter --mount=/proc/1/ns/mnt` `apktool` `apksigner`

---

## 1. Local Update Crash — `FIXED_PERFORMANCE` / `ServiceSpecificException`

### 1.1 What happened
User triggered Settings > System > Updater > Local update, picked a ZIP (`Project_Infinity-X-3.12-X670-29.08.2026-GAPPS-UNOFFICIAL.zip`). `com.infinity.updater` (v1/16, `ABUpdateInstaller.java:212`) crashed twice:

```
19:31:13.826 update_engine: [ERROR:update_attempter_android.cc(94)] Replying with failure:
  system/update_engine/aosp/update_attempter_android.cc 747: Could not change profiles
19:31:13.827 AndroidRuntime: FATAL EXCEPTION: main
  java.lang.RuntimeException: Unable to start service ...UpdaterService
  Caused by: android.os.ServiceSpecificException: Could not change profiles (code 1)
    at IUpdateEngine$Stub$Proxy.setPerformanceMode(IUpdateEngine.java:686)
    at ABUpdateInstaller.install(ABUpdateInstaller.java:212)
```

Second crash (restart path): `NullPointerException` at `UpdaterService.java:199` — `UpdateInfo.getPersistentStatus()` on null.

### 1.2 Root cause
`pixel-libperfmgr` HAL reads `powerhint.json` for supported modes. X670's `configs/powerhint.json` defined `SUSTAINED_PERFORMANCE` but **not** `FIXED_PERFORMANCE`. `cmd power set-fixed-performance-mode-enabled true` failed with `Power Mode FIXED_PERFORMANCE isModeSupported: 0` (`logcat 19:33:07.472`).

`update_engine` always calls `setPerformanceMode(true)` before install (`update_attempter_android.cc:737`). The HAL returns `ServiceSpecificException(code 1)`. `ABUpdateInstaller.java:212` doesn't catch it → crash.

P661N reference uses `android.hardware.power-service.lineage-libperfmgr` (`P661N/device.mk:288`) which implements `FIXED_PERFORMANCE` as no-op when hint missing. X670 uses `pixel-libperfmgr` which strictly validates.

### 1.3 Fix
Added 9 `FIXED_PERFORMANCE` actions to `configs/powerhint.json:569-617`, matching `device_xiaomi_yunluo/configs/powerhint.json:374` and `device_infinix_X6882/configs/power/powerhint.json:349`:

| Node | Value | Rationale |
|------|-------|-----------|
| `CPULittleClusterMaxFreq` | `9999999` | Uncapped max |
| `CPUBigClusterMaxFreq` | `9999999` | Uncapped max |
| `CPULittleClusterMinFreq` | `1375000` | Matches `SUSTAINED_PERFORMANCE` |
| `CPUBigClusterMinFreq` | `1530000` | Matches `SUSTAINED_PERFORMANCE` |
| `perfservFGClampMin` | `70` | High foreground clamp |
| `perfservTAClampMin` | `70` | High top-app clamp |
| `SchedBoost` | `1` | Enable EAS boost |
| `DRAMOppMin` | `1` | Max DRAM frequency |
| `GPUBlockBoost` | `60` | Moderate GPU boost |

Verified: `Power Mode FIXED_PERFORMANCE isModeSupported: 1` (`logcat 19:40:50.858`), `Do Powerhint: FIXED_PERFORMANCE` executes (`19:41:02.916`).

### 1.4 SELinux: `tkv_block_device` file_contexts
`sepolicy/vendor/device.te:9` declares `type tkv_block_device, dev_type` and `update_engine.te:1` allows `rw_file_perms`, but **no file_contexts mapping** existed — the block device was `unlabeled`. Added `/dev/block/by-name/tkv(_[ab])? → tkv_block_device` (`sepolicy/vendor/file_contexts:54-55`), matching P661N reference (`P661N/sepolicy/vendor/file_contexts:43-44`).

---

## 2. WiFi RX Throughput Collapse — MT6631 Power Save

### 2.1 What happened
WiFi on 2.4GHz (`alfi ganteng`, channel 10, 2457MHz, 11n) showed:
- `Rx Link speed: 1Mbps` while `Tx: 58-72Mbps` (9/10 polls)
- 8 `DEAUTH_LEAVING` disconnects in 16 minutes
- `FRAMEWORK_DISCONNECT reason=DISCONNECT_IP_CONFIGURATION_LOST`
- 20% packet loss, DUP packets
- 5GHz (`moto`, 5180MHz, 11ax) worked fine at 390-433Mbps

### 2.2 Root cause
MT6631 driver config: `D:PowerSave|0x3` (Fast PS mode). Fast PS puts the radio to sleep aggressively on 2.4GHz, causing RX throughput to collapse. TX stays fine because the radio wakes for TX but misses RX windows.

The driver's `/proc/net/wlan/cfg` node has `D:` prefix (read-only driver default) — cannot be changed via `echo`. The correct control is `/proc/net/wlan/setCAM` — writing `1` forces Continuously Active Mode (CAM).

### 2.3 Fix
Added `write /proc/net/wlan/setCAM 1` to `rootdir/etc/init/hw/init.connectivity.rc:24-25`, runs at `post-fs-data` before WiFi services start.

Verified: RX jumped from 1Mbps to **150Mbps** immediately after `setCAM=1`.

### 2.4 Failed approaches
- `power_save=0` in `wpa_supplicant_overlay.conf` — invalid for MTK driver, broke WiFi completely
- `driver_param=use_p2p_group_interface=1\ power_save_disabled=1` — also broke WiFi
- `echo "PowerSave|0x0" > /proc/net/wlan/cfg` — `D:` prefix means read-only

---

## 3. WiFi Prop Investigation — FlClash / Moto Hotspot

### 3.1 Findings
- FlClash (`com.follow.clash` v0.8.96) running in mixed-port proxy mode (`127.0.0.1:7890`)
- Config has `tun: stack: mixed, dns-redirect: true` but TUN mode never activated (no `tun0` interface, 0 FDs on `/dev/tun`)
- Moto hotspot is metered (`vendorInfo: ANDROID_METERED`), gateway `10.172.228.156`
- Direct ping to `8.8.8.8`: **100% loss** — no default route initially (DHCP issue)
- FlClash proxy works (returns external IP `103.168.147.236`) — all traffic routes through it
- `32000: from all unreachable` rule (FlClash's routing) blocks all non-proxy traffic

### 3.2 BPF status
- Kernel 4.19 — exactly what `fuck-bpf` targets
- BPF mounted (`bpf on /sys/fs/bpf type bpf`), maps exist (`net_shared`, `netd_shared`, etc.)
- fuck-bpf patches applied: `netd/0001` (comment out `exit(1)` on BPF fail), `Connectivity/0007` (non-working BPF maps fallback)
- BPF is **not** the FlClash TUN issue — the app-level clash core isn't initializing TUN

### 3.3 FlClash TUN not starting
- `/dev/tun` exists, BPF not blocking
- No SELinux denials for FlClash
- FlClash has `BIND_VPN_SERVICE` permission registered
- Likely app-internal issue — force-stop + restart may fix

---

## 4. Reference Comparison — P661N vs X670

### 4.1 Power HAL
| | P661N | X670 |
|---|---|---|
| HAL | `lineage-libperfmgr` (`P661N/device.mk:288`) | `pixel-libperfmgr` (`X670/device.mk:323`) |
| `FIXED_PERFORMANCE` | Handled as no-op by lineage | Strictly validated, missing → crash |
| `powerhint.json` | No `FIXED_PERFORMANCE` actions | Now has 9 actions |

### 4.2 WiFi
| | P661N | X670 |
|---|---|---|
| WiFi chip | MT6631 (same) | MT6631 |
| Power save | Default `0x3` | Default `0x3` |
| `setCAM` | Not configured | Now at `post-fs-data` |

### 4.3 SELinux
| | P661N | X670 |
|---|---|---|
| `tkv_block_device` | `file_contexts:43-44` ✓ | Was missing, now added |
| `tranfs_block_device` | `file_contexts:47` ✓ | `file_contexts:55` ✓ |
| `update_engine.te` | `tkv_block_device rw_file_perms` | Same |

---

## 5. Changes Summary

| File | Lines | Purpose |
|------|-------|---------|
| `configs/powerhint.json` | +54 (9 actions) | `FIXED_PERFORMANCE` for `pixel-libperfmgr` HAL |
| `sepolicy/vendor/file_contexts` | +3 | `tkv_block_device` label for `update_engine` |
| `rootdir/etc/init/hw/init.connectivity.rc` | +4 | `setCAM=1` — force MT6631 CAM mode |

All changes verified on device `ASALE37681000041` with live bind-mount testing before committing.

---

## 6. Key Device Commands Reference

```bash
# Force CAM mode (WiFi fix)
adb shell su -c 'echo 1 > /proc/net/wlan/setCAM'

# Check MT6631 power save config
adb shell su -c 'cat /proc/net/wlan/cfg | grep PowerSave'

# Verify FIXED_PERFORMANCE
adb shell cmd power set-fixed-performance-mode-enabled true
adb logcat -d | grep "FIXED_PERFORMANCE"

# Bind mount vendor configs (erofs RO)
adb push <file> /data/local/tmp/<file>
adb shell su --mount-master -c \
  'nsenter --mount=/proc/1/ns/mnt -- mount -o bind /data/local/tmp/<file> <target>'

# Kill wpa_supplicant to force WiFi restart
adb shell su -c 'killall wpa_supplicant; sleep 2'
adb shell cmd wifi set-wifi-enabled enabled

# Check FlClash routing rules
adb shell ip rule list | grep "unreachable"
```
