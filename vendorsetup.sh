#!/bin/bash

# Copyright (C) 2026 The LineageOS Project
# SPDX-License-Identifier: Apache-2.0

root="${ANDROID_BUILD_TOP:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)}"
d="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

apply_patch() {
    local patch="$1"
    local target_repo="$2"
    local name
    name="$(basename "$patch" .patch)"

    if [ ! -f "$patch" ]; then
        echo "[patch] $name... SKIPPED (file not found)"
        return
    fi

    if git -C "$target_repo" apply --check --ignore-whitespace "$patch" 2>/dev/null; then
        git -C "$target_repo" apply --ignore-whitespace "$patch"
        echo "[patch] $name... applied"
        return
    fi

    if git -C "$target_repo" apply --reverse --check --ignore-whitespace "$patch" 2>/dev/null; then
        echo "[patch] $name... already applied"
        return
    fi

    echo "[patch] $name... FAILED (context mismatch, patch may need rebasing)"
}

# ── axion_sdk ──
AXION_PATCH="$d/patches/0001-ax_deviceinfo-use-power-profile-for-battery-capacity.patch"
AXION_TARGET="$root/axion_sdk/ax_deviceinfo/src/com/android/axion/deviceinfo/DeviceInfoProvider.kt"

if [ -f "$AXION_PATCH" ] && [ -f "$AXION_TARGET" ]; then
    pushd "$root/axion_sdk" > /dev/null || return
    if [ -f "$(git rev-parse --git-dir)/shallow" ]; then
        echo "- Unshallowing axion_sdk"
        git fetch --unshallow
    fi
    git revert --abort 2>/dev/null || true
    apply_patch "$AXION_PATCH" "$root/axion_sdk"
    popd > /dev/null || return
elif [ ! -f "$AXION_PATCH" ]; then
    echo "[patch] ax_deviceinfo... SKIPPED (patch not found)"
fi

# ── system/core (fenrir) ──
apply_patch "$d/patches/0001-libfs_avb-Allow-LKs-patched-with-fenrir-to-boot-on-A.patch" "$root/system/core"
apply_patch "$d/patches/0002-fastbootd-Always-return-false-for-GetDeviceLockStatu.patch" "$root/system/core"
