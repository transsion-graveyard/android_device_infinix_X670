# Stock Report Guide

Use this guide to analyze a subsystem on stock firmware before changing ROM source.

## 1. Goal

Answer these questions:
- What is the target node, service, or feature?
- Is it present on stock?
- Which file, rule, or label makes it work?
- What is the minimum persistent change needed on the ROM side?

## 2. Evidence Areas

Check each layer in order.

### 2.1 Node

Inspect:
- `/dev/*` device nodes
- `/sys/*` sysfs paths
- `/proc/*` procfs paths

Capture:
- path
- type
- owner/group
- mode
- SELinux label
- symlink target, if any

Useful commands:
```bash
ls -lZ /dev/<node>
ls -lZ /sys/class/<path>
stat /dev/<node>
readlink -f /dev/<node>
```

### 2.2 Init

Inspect:
- `*.rc`
- `ueventd*.rc`
- service declarations
- `on fs`, `on post-fs-data`, `class start`, `late_start`

Capture:
- service name
- binary path
- trigger
- user/group
- socket or interface declaration
- chmod/chown actions

Useful commands:
```bash
grep -Rni "<keyword>" vendor/etc/init rootdir/etc/init
grep -Rni "<keyword>" rootdir/etc/ueventd*.rc vendor/etc/ueventd*.rc
```

### 2.3 Permissions

Inspect:
- file mode
- ownership
- group membership
- required supplemental groups
- runtime chmod/chown from init

Capture:
- expected mode
- actual mode
- whether the service domain can access the node

### 2.4 Config

Inspect:
- XML config files
- feature/permission XML
- property files
- manifest fragments
- compatibility matrices

Capture:
- exact file path
- key package/interface names
- version and instance
- whether the config is copied by build rules

### 2.5 SELinux

Inspect:
- `file_contexts`
- `hwservice_contexts`
- `service_contexts`
- `*.te`
- AVC denials in logcat and dmesg

Capture:
- node label
- process domain
- service label
- allow rules or missing rules
- AVC denial text

Useful commands:
```bash
ls -lZ /dev/<node>
logcat -b all -d | grep -Ei "avc: denied|<keyword>"
dmesg | grep -Ei "avc: denied|<keyword>"
```

## 3. Stock Comparison Checklist

For each relevant artifact, compare live vs stock:
- binary exists
- config exists
- init rc exists
- manifest fragment exists
- feature XML exists
- node exists
- node label matches
- node permissions match
- SELinux rules match
- service actually registers

## 4. Failure Classification

Classify the blocker:
- missing node
- wrong node name
- wrong mode/owner
- wrong SELinux label
- missing init rule
- missing manifest entry
- missing config file
- service crash
- HAL registration failure
- kernel/driver failure

## 5. Runtime Verification

Do not stop at file presence.

Verify:
- service registers
- logs are clean enough
- framework sees the feature
- functional test works
- repeat test works
- reboot test works when applicable

## 6. Report Template

Fill this in for each subsystem.

```md
## Target
- subsystem:
- expected behavior:
- current symptom:

## Stock Findings
- node:
- init:
- config:
- permissions:
- SELinux:

## Live Findings
- node:
- init:
- config:
- permissions:
- SELinux:

## Root Cause
-

## Minimal Fix
-

## Verification
-
```

## 7. Rule of Thumb

If the node is wrong, fix node wiring first.
If the service is missing, fix init/manifest first.
If access is denied, fix permissions or SELinux next.
If the HAL starts but no sensor appears, inspect config and vendor extension paths.
