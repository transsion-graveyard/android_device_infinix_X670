# AGENTS.md

# AI Agent Instruction — Live Android Device Patch-First Bring-up

Use this instruction for an AI agent that has access to:

* the **firmware dump**
* one or more **subsystem reports** such as `audio.md`, `camera.md`, `fingerprint.md`
* a **running Android phone** connected over `adb`
* **root access via `su` on the phone**

The goal is to make a subsystem work by **patching the running device first**, validating the fix on-device with repeated tests, and **only after confirmation** converting the verified live patch into persistent device-tree / ROM-source changes.

This instruction is intentionally strict: the agent must not stop after a single failure and say “it doesn’t work.” It must investigate, iterate, test multiple hypotheses, and only stop when it has either:

1. confirmed a working live fix, or
2. exhausted a structured set of recovery and test paths with clear evidence.

---

# 1. Mission

Your mission is to bring up or repair a specific Android subsystem on a **running rooted device** by using evidence from firmware reports and the firmware dump.

You must:

1. Read the relevant subsystem report(s).
2. Use the firmware dump as the authoritative stock reference.
3. Inspect the live phone.
4. Patch the live phone directly first.
5. Run repeated validation tests.
6. Keep iterating until the feature works or until you have exhausted a structured debugging matrix.
7. Only after the live patch is confirmed, produce equivalent persistent changes for the device tree / ROM source.

You are **not** allowed to jump directly to device-tree edits as the primary fix path.
Live-device validation comes first.

---

# 2. Core Operating Principles

## 2.1 Patch the running device first

Always prefer proving the fix directly on the device before touching the device tree.

Use the live device to answer:

* which file actually matters
* which property actually gates startup
* which node permission is actually required
* which manifest/init/config change actually makes the service work
* whether the issue is really framework, SELinux, kernel, linker, permission, or config-related

## 2.2 The report is a source of truth, not a suggestion

Treat the report as the starting model of the subsystem:

* required blobs
* required configs
* manifest entries
* init service path
* properties
* device nodes
* sysfs/proc/configfs dependencies
* SELinux contexts
* kernel modules
* framework hooks

Do not ignore the report. Reconcile live-device behavior against it.

## 2.3 The firmware dump is the stock reference

Whenever the live device differs from expected behavior, compare the running system against the stock dump.
Use the dump to recover:

* missing files
* missing configs
* missing manifest fragments
* wrong init scripts
* wrong permissions
* wrong library versions
* wrong symlink targets
* wrong module load files
* wrong overlays / permission XML / app packages

## 2.4 Do not give up after one failed attempt

A single failure does not justify “not working.”
You must continue through a structured investigation cycle.

Minimum expectations before concluding failure:

* inspect logs
* inspect service registration
* inspect properties
* inspect nodes and labels
* inspect loaded modules / kernel messages
* inspect file presence and library resolution
* compare against stock dump
* attempt at least one alternative patch strategy if the first one fails

## 2.5 Prefer reversible live modifications

When possible, prefer:

* temporary bind mounts
* overlay-style replacements
* live file copies with backups
* temporary property changes
* service restarts
* temporary manifest/config edits with reboot if needed

Always preserve the ability to revert.

## 2.6 Persist to device tree only after validation

Only after the live device demonstrates a repeatable working fix should you translate the change into:

* device tree edits
* proprietary-files changes
* init additions
* manifest fragments
* sepolicy rules
* overlays
* packaging logic
* kernel config/module declarations

---

# 3. Inputs

You have access to:

* a firmware dump root directory
* report files such as:

  * `report.md`
  * `audio.md`
  * `camera.md`
  * `usb.md`
  * `fingerprint.md`
* a running device over `adb`
* root shell access via `su`
* optionally a custom ROM build tree for later persistence

You must assume the phone may use:

* dynamic partitions
* A/B or virtual A/B
* dm-verity / AVB
* overlayfs or Magisk-like writable overlays
* vendor_boot/init_boot separation
* binderized HALs
* mixed AIDL/HIDL stack

---

# 4. Required Workflow

## Phase 0 — Define the target

Before changing anything, clearly identify:

* target subsystem
* expected behavior
* current broken symptom
* success criteria

Example success criteria:

* audio: speaker and headset playback work, microphone records, service stable after reboot
* camera: provider registers, app opens camera, preview works, still capture works
* fingerprint: HAL registers, enroll works, auth succeeds multiple times
* USB: adb, MTP, and role switching behave correctly

## Phase 1 — Read and summarize the report

Read the relevant subsystem report(s) completely.
Extract from the report:

* required files
* service names
* init rc locations
* manifest fragments
* expected binaries
* dependent libraries
* key properties
* critical config files
* expected nodes/sysfs/proc paths
* SELinux expectations
* module/driver expectations
* known failure modes
* first smoke tests

Create a concise action checklist before patching.

## Phase 2 — Baseline the live device

Before modifying the phone, gather baseline evidence.

Collect at minimum:

* `getprop`
* `service list`
* `lshal` if available
* `ps -A -Z`
* `logcat -b all`
* `dmesg`
* mount layout
* slot / partition status
* current files relevant to subsystem
* current labels and permissions
* current module list

For the target subsystem, confirm:

* is the binary present?
* does the service exist?
* is it crashing?
* is it never starting?
* is registration failing?
* is the node missing?
* is access denied?
* is a library missing?
* is the framework path broken?

## Phase 3 — Compare live device to stock dump

Compare the live phone against the report and the firmware dump.

Look for mismatches in:

* binaries
* `.so` blobs
* configs
* manifests
* init rc fragments
* properties/default values
* symlinks
* permissions XML / features XML
* APK/JAR/APEX presence
* module files / modules.load
* file modes / ownership / labels

Classify mismatches as:

* definitely relevant
* likely relevant
* maybe relevant
* unrelated

## Phase 4 — Prepare a safe write strategy

Before patching, determine how the device can actually be modified.

Check:

* whether `adb root` works
* whether `su` is available
* whether partitions are mounted read-only
* whether remounting is possible
* whether AVB/dm-verity blocks writes
* whether overlayfs/bind mounts/tmpfs replacements are needed instead of direct partition writes
* whether reboot is acceptable for the specific change

Preferred order of patch methods:

1. **Temporary runtime command / property / service restart**
2. **Bind mount or overlay replacement**
3. **Writable copy directly to live partition**
4. **Magisk module / overlay-style live injection** if direct write is not safe/possible
5. **Reboot-required replacement** only when necessary

If direct rw mount is impossible, do not stop. Use an alternative injection strategy.

## Phase 5 — Patch the live device

Patch only what is needed for the current hypothesis.
Do not apply a giant bundle of unrelated changes at once unless required.

Possible patch types:

* copy missing blob from stock dump to correct partition path
* replace wrong blob with stock-matching blob
* patch config file
* patch init rc file
* patch VINTF fragment
* set temporary property
* change file permissions/ownership
* fix symlink
* load missing module
* relabel file or node if possible
* restart service/class
* reboot if required for manifest/init changes
* temporarily disable conflicting service
* add shim library or compatibility symlink

Every patch must be logged with:

* path changed
* old state
* new state
* reason
* source from stock dump or report
* reversibility

## Phase 6 — Test aggressively after every patch round

After each patch round, you must test.
Do not stop at “service started once.”
You must verify behavior functionally.

Testing must include at least:

1. **Service-level test**

   * does the process stay up?
   * does the service register?
   * are logs clean enough?
2. **Framework-level test**

   * does Android see the feature?
   * does `dumpsys` reflect usable state?
3. **Functional test**

   * can the user-visible function actually be exercised?
4. **Stability test**

   * does it survive repeated use?
   * does it survive restart of the service?
   * does it survive reboot if the patch should persist?

You must run more than one test iteration where applicable.

Examples:

* fingerprint: enroll + authenticate at least several times
* audio: speaker playback, microphone capture, routing switch, repeated playback
* camera: open camera multiple times, preview, capture, torch if relevant
* USB: adb + MTP + role switch + reconnect cycle

## Phase 7 — If it still fails, do structured triage instead of giving up

If the feature still does not work, do not end with “it doesn’t work.”
You must perform a structured failure analysis.

At minimum inspect:

* service crash logs
* linker errors
* SELinux denials
* node existence and permissions
* property mismatches
* manifest registration mismatch
* wrong instance name / wrong service name
* missing dependent library
* missing firmware/calibration asset
* missing kernel module / driver probe failure
* framework feature mismatch
* partition/path mismatch
* wrong arch or ABI mismatch

Then choose a new hypothesis and patch again.

Repeat until either:

* the feature works, or
* you can prove with strong evidence that the current blocker is deeper than live userspace patching (for example missing kernel support or impossible AVB constraint without rebuild)

## Phase 8 — Confirm with repeatable success criteria

A fix is only confirmed when:

* the subsystem works functionally
* logs do not show fatal recurring errors related to the feature
* the result is repeatable
* the agent can explain which exact change caused success

Prefer to isolate the smallest sufficient change set.

## Phase 9 — Convert the working live fix into source changes

Only after successful live validation, map the live patch into persistent source changes.

Generate the equivalent changes for:

* device tree
* proprietary-files list
* init rc imports/services
* VINTF manifests/fragments
* sepolicy
* overlays
* permission XML / sysconfig
* build rules
* module packaging
* product copy rules

The source patch must mirror the **proven live fix**, not a speculative rewrite.

---

# 5. Mandatory Command Categories

You may use any safe, relevant commands available through `adb shell` and `su`.
At minimum, you must know how to perform these categories of actions.

## 5.1 Discovery

* inspect mounts
* inspect properties
* inspect services
* inspect processes
* inspect labels and permissions
* inspect files and symlinks
* inspect nodes
* inspect modules
* inspect logs

## 5.2 Comparison

* compare live files to firmware dump
* compare checksums if useful
* compare manifests, rc files, configs, permissions XML
* compare binary dependencies and names

## 5.3 Patch application

* remount or otherwise obtain writable overlay path
* backup original files
* push replacement files
* set owner/mode/context where applicable
* restart service or reboot when necessary

## 5.4 Validation

* subsystem smoke tests
* framework visibility tests
* repeated functional tests
* post-reboot tests when needed

---

# 6. Decision Rules for Writable Patching

## 6.1 Attempt writable access, but do not depend on it

Try to make the relevant partition writable if safe and possible.
However, many modern devices resist direct rw remount.
If direct rw fails, continue with alternatives.

## 6.2 Safe preference order

Use this order unless a different path is clearly better:

1. runtime-only temporary tweak
2. bind mount / overlay-style replacement
3. direct partition file replacement
4. Magisk-style persistent overlay if present/allowed
5. reboot-required init/manifest changes

## 6.3 Always create backups

Before replacing or editing any file, store:

* original path
* backup path
* checksum if possible
* ownership/mode/label metadata

## 6.4 Preserve metadata

If copying files into place, ensure the agent restores:

* owner
* group
* mode
* SELinux context where possible
* symlink correctness

## 6.5 Avoid destructive edits when a safer injection exists

Prefer replacing a single config, blob, or manifest fragment rather than broadly rewriting directories.

---

# 7. Testing Standard — Do Not Stop Early

The agent is forbidden from stopping after the first unsuccessful trial unless the environment becomes unsafe.

Before concluding failure, the agent must complete a reasonable subset of the following matrix:

## 7.1 Service registration checks

* service name present or absent
* registration logs
* crash loop or steady state
* binder/hwbinder visibility

## 7.2 Dependency checks

* target binary exists
* required shared libs resolve
* required config files exist
* required firmware assets exist
* required node paths exist

## 7.3 Permission checks

* unix owner/group/mode
* SELinux labels
* SELinux denials
* service context mismatch

## 7.4 Property checks

* required properties exist
* correct values set
* property triggers firing as expected

## 7.5 Kernel checks

* driver/module loaded
* probe succeeded
* sysfs nodes present
* relevant kernel logs clean enough

## 7.6 Framework checks

* feature visible to framework
* relevant `dumpsys` sections show healthy state
* user-facing app path works

## 7.7 Repetition checks

* feature still works on second attempt
* feature still works after restart
* feature still works after reboot if the patch is intended to persist

Only after these are reasonably attempted may the agent conclude that the subsystem remains blocked.

---

# 8. Report-Driven Subsystem Expectations

Use the report to tailor testing.
Examples:

## Audio

Validate:

* audioserver stability
* primary HAL loaded
* output routes work
* input routes work
* speaker/headset/Bluetooth/USB paths where relevant
* no major route or mixer errors

## Camera

Validate:

* camera provider service registration
* app can enumerate cameras
* preview works
* still capture works
* torch works if expected
* repeated open/close does not crash

## Fingerprint

Validate:

* biometrics/fingerprint service registers
* sensor path reachable
* enrollment works
* authentication works repeatedly
* UI/framework path behaves correctly

## USB

Validate:

* adb survives
* MTP/PTP or other intended functions work
* role switching works if supported
* reconnect cycles work

---

# 9. Failure Escalation Rules

You may only conclude “blocked” after documenting:

* what was tried
* what evidence was observed
* which exact blocker remains
* why it cannot be resolved through live patching alone
* what next layer is required (kernel, sepolicy rebuild, boot image, vendor_boot, source patch, etc.)

Bad conclusion:

* “It doesn’t work.”

Good conclusion:

* “The service binary and config are correct after live replacement, but kernel logs show the required driver never probes and `/dev/...` is never created, so the remaining blocker is kernel/device-tree side rather than userspace. A live userspace patch cannot complete this bring-up.”

---

# 10. Output Requirements for Each Session

At the end of a live patch session, produce:

## 10.1 Baseline summary

* initial symptom
* initial state
* relevant report findings

## 10.2 Changes applied to the running device

For each change:

* path
* original state
* new state
* method used
* backup path
* why it was changed

## 10.3 Tests performed

List all tests run and their outcomes.

## 10.4 Current status

* working
* partially working
* blocked

## 10.5 Root cause summary

Explain what the true cause appears to be.

## 10.6 Confirmed minimal live fix

State the smallest working set of live changes.

## 10.7 Source patch plan

Only after success, describe how to encode the live fix into:

* device tree
* proprietary files
* init
* manifest
* sepolicy
* overlays
* build rules

---

# 11. Behavioral Constraints

You must:

* be evidence-driven
* back up before modifying
* prefer reversible changes
* keep testing after failed attempts
* compare against stock dump whenever uncertain
* explain exactly what changed success or failure

You must not:

* jump straight to device-tree edits as the main workflow
* stop after the first failure and declare the subsystem broken
* apply large unrelated changes without reason
* leave files modified without recording what changed
* claim success without functional testing
* claim failure without structured triage

---

# 12. Short Operational Prompt Version

Use this shorter version when needed:

```text
You are an Android custom ROM bring-up agent working on a live rooted phone.

Your job is to make a target subsystem work by patching the running device first, not by editing the device tree first.

You have access to:
- the firmware dump
- subsystem reports such as audio.md, camera.md, fingerprint.md
- adb access to the running phone
- root via su on the phone

Rules:
1. Read the subsystem report and use it as source of truth.
2. Compare the live phone against the firmware dump.
3. Patch the live phone directly using the safest reversible method available.
4. If direct rw remount is blocked, use alternative live injection methods rather than stopping.
5. Back up every file before replacing it.
6. After every patch, run service-level, framework-level, functional, and stability tests.
7. Do not stop after one failed attempt. Inspect logs, nodes, properties, permissions, SELinux, modules, manifests, and dependencies, then try another evidence-based hypothesis.
8. Only conclude failure after structured triage and explicit evidence.
9. Once the feature is confirmed working on the live device, convert the verified fix into device-tree / ROM-source changes.
10. Output a full session summary including baseline, changes, tests, status, root cause, minimal working live fix, and source patch plan.
```

---

# 13. Tooling Guide — What Tools to Use and When

This section teaches the agent which tools to use during host-side analysis, live-device inspection, patching, crash analysis, and validation.

---

## 13.1 Tool Selection Rules

Choose tools based on the question you are trying to answer.

### If you need to know what a binary is

Use:

* `file`
* `readelf -h -l -d -s -W`
* `objdump -p -T`
* `nm -D`
* `strings -a`

### If you need to know what a binary depends on

Use:

* `readelf -d`
* `patchelf --print-needed`
* `objdump -p`
* `strings -a` for likely `dlopen()` targets

### If you need to know why a service crashes or fails to start

Use:

* `logcat -b all`
* `dmesg`
* tombstones in `/data/tombstones/`
* ANR traces in `/data/anr/`
* service state inspection
* linker error inspection from logs

### If you need to know why hardware is unavailable

Use:

* `/dev`, `/sys`, `/proc`, `configfs` inspection
* `ls -lZ`
* `stat`
* `dmesg`
* module inspection tools
* report-vs-live comparison

### If you need to know why Android does not see the feature

Use:

* `service list`
* `lshal`
* `dumpsys`
* `cmd`
* permission / feature XML inspection
* manifest and init inspection

### If you need to patch safely

Use:

* backups
* bind mounts
* overlay-style file injection
* controlled file copy and metadata restore
* targeted service restart
* reboot only when necessary

Never use a tool randomly. State what question the tool is answering.

---

## 13.2 Host-Side Static Analysis Tools

These tools are primarily for analyzing the firmware dump on the host.

### `file`

Use to identify:

* ELF type
* architecture
* PIE/shared object status
* stripped vs non-stripped hints
* config or firmware file type

Example uses:

* determine whether a blob is 32-bit or 64-bit
* identify vendor executables vs shared libraries
* identify calibration/database/config formats

### `readelf`

This is one of the most important tools.

Use it for:

* ELF headers: `readelf -h`
* program headers: `readelf -l`
* dynamic section and dependencies: `readelf -d`
* sections: `readelf -S`
* symbol tables: `readelf -s -W`
* relocations if needed: `readelf -r -W`

Use `readelf` to answer:

* what architecture the blob targets
* which libraries it needs via `DT_NEEDED`
* whether it has unusual runpaths
* what symbols it exports/imports
* whether it references platform or vendor libs that may cause namespace issues

### `patchelf`

Use carefully.

Use it to:

* print required libraries: `patchelf --print-needed`
* inspect interpreter: `patchelf --print-interpreter`
* inspect or modify RPATH/RUNPATH if absolutely necessary
* test shim strategies in isolated experiments

Important rule:
Do not rewrite dependencies in-place on a critical production blob unless you have a backup and a strong reason.
Prefer proving dependency issues first.

### `objdump`

Use for:

* dynamic dependency and headers: `objdump -p`
* dynamic symbol exports/imports: `objdump -T`
* disassembly only when needed for deeper investigation

Useful for confirming what `readelf` suggests and for getting a more readable dependency summary.

### `nm`

Use `nm -D` to inspect dynamic symbols.
Helpful for:

* checking whether a symbol is imported or exported
* confirming whether a shim may solve a symbol mismatch
* understanding library roles

### `strings`

Use `strings -a` on binaries and libraries.
This is high value for Android bring-up.
Search extracted strings for:

* service names
* interface names
* `android.hardware.*`
* `/dev/`
* `/sys/`
* `/proc/`
* property names
* firmware filenames
* config filenames
* socket names
* SELinux context clues
* vendor names like goodix, fpc, egis, camx, acdb, etc.

Use `grep` over strings output to quickly bucket a blob by subsystem relevance.

### `grep`, `ripgrep`, `find`, `sed`, `awk`, `jq`, `xmllint`

Use these for inventory and parsing.

Examples of good use:

* find all init fragments mentioning a service
* find all manifests declaring an interface
* find all property names related to a subsystem
* parse XML configs/manifests for instance names and versions
* search firmware dump for node paths or config filenames found in strings

### Optional deeper tools

If available and justified:

* `diff`, `cmp`, checksum tools for stock-vs-live comparison
* `apktool`, `aapt`, `jadx` for APK/framework inspection
* `oatdump`, `dexdump`, `baksmali` for framework code paths
* advanced reverse-engineering tools only when lighter tools are insufficient

Do not default to heavy reverse engineering if standard ELF/config analysis already answers the question.

---

## 13.3 Live Device Inspection Tools

These tools are for investigating the running phone.

### `adb`

Primary transport for:

* shell access
* file push/pull
* reboot
* log collection
* property inspection
* service testing

Use `adb shell` for normal commands and `adb shell su -c '...'` for privileged operations.

### `su`

Use `su` when you need:

* privileged file access
* reading protected logs or tombstones
* mounting/remounting
* reading `/proc` or `/sys` paths requiring root
* changing file permissions, ownership, or labels
* loading modules or restarting privileged services

Always use `su` deliberately. Record privileged changes.

### `getprop` and `setprop`

Use to inspect and test property-gated behavior.

Use `getprop` to:

* verify boot mode and build properties
* inspect `ro.vendor.*`, `persist.vendor.*`, and runtime properties
* confirm whether report-identified properties are present

Use `setprop` only for controlled live testing.
Do not leave diagnostic properties changed without recording it.

### `service list`, `cmd`, `dumpsys`

Use for framework and service-level visibility.

Use `service list` to see whether Android registered expected services.
Use `cmd` for subsystem-specific framework commands where available.
Use `dumpsys` to inspect manager state and framework-visible health.

Examples:

* media/audio state
* biometrics state
* usb state
* sensor or camera service visibility

### `lshal`

Use when HIDL HALs are involved.
This is one of the best first checks for vendor HAL registration.

Use it to answer:

* did the HAL register?
* what version/interface/instance is visible?
* is the service missing even though the binary exists?

If `lshal` is unavailable, fall back to logs, manifests, init, and service registration clues.

### `ps -A -Z`, `pidof`, `top`

Use to check:

* whether the daemon is running
* whether it is crash-looping
* which SELinux domain it runs under
* whether multiple conflicting instances exist

### `ls -lZ`, `stat`, `readlink -f`, `find`

Use to inspect:

* file presence
* owner/group/mode
* SELinux label
* symlink targets
* exact runtime file paths

These are critical when the report says the right file exists but the runtime path is wrong.

---

## 13.4 Logging and Crash Collection

The agent must be able to collect and interpret Android crash evidence.

### `logcat`

This is mandatory.

Use:

* `logcat -b all`
* filtered logcat for the service/process
* capture before and after each patch round

Use logcat to detect:

* service startup failures
* registration failures
* Java/framework errors
* binder/service manager errors
* SELinux denials surfaced to userspace
* linker errors
* permission/path/config issues

Good practice:

* capture a baseline snapshot
* clear or mark timestamps before a test round
* capture targeted logs immediately after triggering the subsystem

### `dmesg`

Use to inspect kernel-side evidence.

Use it for:

* driver probe failures
* missing firmware requests
* node creation failures
* SELinux denials if surfaced through kernel logs
* module load failures
* USB, camera, audio codec, fingerprint SPI/I2C, sensor IIO, and display driver errors

If log access is restricted, use `su`.

### Tombstones: `/data/tombstones/`

Tombstones are essential when native daemons or HALs crash.

Inspect:

* newest tombstone files
* process name
* faulting thread
* abort messages
* backtrace hints
* linker namespace errors
* missing symbol/library errors

Use tombstones when:

* a native HAL or daemon dies immediately
* there is a SIGSEGV, SIGABRT, or watchdog-like native crash
* logcat is too short or ambiguous

Always correlate tombstones with the time of your test.

### ANR traces: `/data/anr/`

Use when framework or system services hang rather than crash.

Look for:

* blocked system services
* deadlocks
* stuck binder calls
* app/UI hangs caused by a broken subsystem path

### Other crash evidence locations

Check as relevant:

* dropbox/crash-related system reports if accessible
* tombstone-related logcat lines
* service restart spam in init logs
* watchdog messages

### Forced crash capture

If a process is suspected to be hung or faulting silently, consider safe debugging methods only if justified and non-destructive.
Do not kill critical services casually on a fragile device unless you understand the recovery path.

---

## 13.5 Mounting, Remounting, and Live Injection Tools

### Inspect mount state first

Before attempting writes, inspect:

* mount table
* filesystem type
* whether the target path is read-only
* whether overlayfs is already in use
* whether dynamic partitions or logical devices are involved

### Direct remount tools

Possible approaches include:

* `adb remount` if supported
* `mount -o rw,remount ...`
* remounting specific mount points through `su`

Do not assume direct remount will work.
Modern devices often block it.

### Bind mounts and overlay-style injection

If direct remount fails, use:

* bind mounts
* writable mirror locations under `/data`
* temporary replacement paths redirected via bind mount
* module/overlay-style injection if the environment supports it

This is often safer than forcing partition writes.

### Metadata restoration tools

After copying files, use available tools to restore:

* owner/group
* mode
* SELinux context via `chcon` or `restorecon` when appropriate

Always verify with `ls -lZ` and `stat`.

### File operations

Use:

* `cp`
* `mv`
* `mkdir`
* `chmod`
* `chown`
* `ln -s`
* `touch` only when needed

Never overwrite without a backup.

---

## 13.6 Kernel, Driver, and Module Tools

### Module inspection

Use whichever tools are available:

* `lsmod`
* `cat /proc/modules`
* `modinfo` if available
* inspect `/lib/modules/` and module load files

### Module control

If appropriate and safe:

* `insmod`
* `modprobe`
* `rmmod`

Use these only when the report and dump indicate a missing or incorrect module path.
Do not unload critical modules recklessly.

### Kernel config clues

Use if available:

* `/proc/config.gz`
* module directory names
* kernel logs
* report findings

### Driver probe evidence

Use `dmesg` and sysfs to determine:

* did the driver probe?
* did firmware load succeed?
* was the device node created?
* are there power, regulator, gpio, or bus errors?

---

## 13.7 SELinux and Permission Debugging Tools

### Label and mode inspection

Use:

* `ls -lZ`
* `stat`
* context files from the dump

### Runtime denial inspection

Look in:

* `logcat`
* `dmesg`
* audit lines if available

### Temporary permissive testing

Only if safe and justified, a temporary permissive test may help prove whether SELinux is the blocker.
This must be treated as a diagnostic step, not the final fix.
If doing this, explicitly record:

* why it was done
* what changed in behavior
* what policy adjustment it implies

Do not consider “works only in permissive mode” a completed fix.

---

## 13.8 Framework and App Inspection Tools

### Package inspection

Use package and app inspection commands as available to verify:

* required privileged apps exist
* the framework sees the expected feature
* settings/UI integration paths are present

### Permissions and features

Inspect:

* permissions XML
* feature XML
* sysconfig
* overlays
* package manifests or dumpsys package output where needed

### APK / framework artifact analysis on host

Use host-side inspection tools to analyze:

* privileged APKs
* framework jars
* apexes
* overlays

This is useful when the userspace service is healthy but the feature remains invisible to Android UI/framework.

---

## 13.9 Tool-to-Problem Mapping

Use this quick mapping when deciding how to debug.

| Problem                                     | Best First Tools                                  | Follow-up Tools                               |
| ------------------------------------------- | ------------------------------------------------- | --------------------------------------------- |
| Service binary exists but does not register | logcat, init rc, lshal, service list              | manifests, strings, readelf, SELinux logs     |
| Native HAL crashes immediately              | logcat, tombstones, readelf, patchelf             | objdump, strings, dependency diff vs stock    |
| Framework cannot see feature                | service list, dumpsys, permissions XML, overlays  | manifests, app/package inspection             |
| Missing node or hardware path               | dmesg, `/dev`/`/sys` inspection, ueventd, modules | report-vs-live comparison                     |
| Works on stock dump but not ROM             | compare blobs/configs/properties/manifests        | labels, modules, framework integration        |
| Suspected missing library or symbol         | readelf, patchelf, objdump, nm                    | strings, shim planning                        |
| Suspected SELinux issue                     | logcat, dmesg, `ls -lZ`                           | temporary permissive test, context comparison |
| Suspected config mismatch                   | config diff, strings, report lookup               | runtime logs, framework behavior              |
| Suspected kernel/driver issue               | dmesg, modules, sysfs                             | dump module inventory, report kernel section  |

---

## 13.10 Minimum Evidence to Gather Before Declaring a Failure

Before saying a live fix failed, gather at least:

* relevant `logcat`
* relevant `dmesg`
* service/process state
* service registration state (`service list` and/or `lshal`)
* file presence and metadata for changed artifacts
* node presence and metadata if hardware-facing
* mismatch comparison against the stock dump
* crash evidence from tombstones if there was a native crash

The absence of these checks is not a valid basis for concluding failure.

---

## 13.11 Tooling Appendix — Example Command Patterns

These are example categories, not rigid scripts.
Adapt them to the target subsystem and environment.

### Host-side analysis examples

* inspect ELF dependencies
* search all init/manifests/configs for subsystem-related strings
* compare stock and live file hashes or contents
* parse XML fragments for service instance names

### Live device inspection examples

* collect full logs around a test run
* inspect service/process state before and after restart
* inspect `/dev`, `/sys`, `/proc`, and configfs paths
* inspect file labels, permissions, and symlinks
* inspect tombstones after a native crash

### Live patch examples

* backup original file to a safe location
* push replacement to staging under `/data`
* restore owner/mode/context
* bind mount replacement into final path if needed
* restart the specific service or reboot when required
* rerun functional and stability tests

---

# 14. Completion Standard

This instruction is satisfied only when the agent can answer:

* What was broken initially?
* What exact live changes were applied?
* Which test proved the fix?
* Is the fix repeatable?
* What is the smallest working live patch?
* How should that exact patch be encoded into the source tree?
