# X670 Hotspot DNS Root-Cause and Minimal Fix Design

## Goal
Fix Wi-Fi hotspot on X670 without broad prop churn or speculative refactors.

Current evidence points to this failure chain:
- hotspot starts normally on `ap0`
- tethering reaches upstream selection on `ccmni0`
- `netd` fails while pushing DNS forwarders to `dnsmasq`
- tethering aborts and tears `ap0` down

This design covers two linked tracks:
1. continue live root-cause investigation until the `dnsmasq` failure mode is proven
2. apply the smallest tree-side fix that matches the proven root cause

## Current Baseline

Already verified on device:
- `persist.radio.multisim.config=dsds`
- `persist.vendor.radio.msimmode=dsds`
- `telephony.active_modems.max_count=2`
- `wifi.tethering.interface=ap0`
- `Private DNS` control test did not change the hotspot failure
- BPF/offload starts successfully and is not the first failure

Already changed in-tree:
- `overlay/TetheringConfigTarget/res/values/config.xml`
  - Wi-Fi tether regex now matches stock-style `ap\\d` only

## Approach Options

### Option 1: Runtime-first, tree-second
Keep tracing the live device until the exact `dnsmasq` failure point is known, then patch only the tree surface that explains that failure.

Trade-offs:
- highest confidence
- least churn
- slower if the answer is hidden in vendor runtime packaging

### Option 2: Tree-first stock parity
Compare tethering-related tree pieces against stock firmware first, then patch any mismatch in init, SELinux, overlays, or packaged binaries.

Trade-offs:
- faster if there is obvious drift
- higher risk of changing unrelated networking behavior
- easier to overfit to stock without proving the failure mode

### Option 3: Parallel track
Continue runtime tracing while also preparing a narrow stock-parity patch set for tethering startup and DNS handoff.

Trade-offs:
- best momentum
- more coordination
- still limited to tethering/DNS surfaces, not broad system changes

Recommendation:
- Option 1 with a narrow stock-parity comparison only for the tethering startup path.

## Investigation Scope

Continue live tracing with these questions:
- does `dnsmasq` spawn at all during hotspot bring-up
- if it spawns, does it exit immediately
- if it exits, what argument or environment mismatch causes the exit
- if it does not spawn, what `netd` path is failing before exec
- whether the failure depends on the upstream cellular DNS state or is independent of it

Diagnostics to rely on:
- `logcat` around the hotspot toggle
- `dumpsys tethering`
- `dumpsys dnsresolver`
- `ps` / process presence for `netd`, `dnsmasq`, `hostapd`
- SELinux denials, only if they appear

Explicit non-goals for this phase:
- do not change telephony props
- do not widen hotspot regexes again
- do not touch BPF/offload unless the logs show it is the first failing boundary

## Minimal Tree-Fix Boundary

If the runtime investigation proves a tree-side mismatch, limit the fix to one of these surfaces only:
- tethering overlay resources
- init/service wiring for `netd`, `dnsmasq`, or `hostapd`
- SELinux or file-context gaps that directly block tethering startup
- packaging of stock-compatible tethering runtime pieces, if the binary or service path is missing from the tree

Do not expand scope to:
- general telephony behavior
- SIM slot counting
- unrelated Wi-Fi feature flags
- broad vendor prop rewrites

## Verification

A fix is only valid if these conditions hold:
- hotspot starts on `ap0`
- `netd` no longer reports `Failed to send update command to dnsmasq`
- no `Remote I/O error (code 121)` during DNS forwarder setup
- `ap0` remains up long enough to hand out DHCP
- the fix does not reintroduce the earlier SIM3 / `SystemUI` crash state
- DSDS props remain unchanged and stable

If hotspot still fails after the narrow fix:
- return to live tracing
- do not layer additional changes blindly
- reassess whether the failure is in `netd` runtime behavior or vendor tethering packaging

## Why This Scope

The device already has the stock DSDS radio baseline and the hotspot interface naming aligned to stock.
The remaining failure is concentrated at the DNS forwarder handoff, so the design intentionally keeps the fix surface small and tethering-specific.

