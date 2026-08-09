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

# ── axion_sdk (optional) ──
AXION_PATCH="$d/patches/0001-ax_deviceinfo-use-power-profile-for-battery-capacity.patch"

if [ -f "$AXION_PATCH" ]; then
    if [ -d "$root/axion_sdk" ]; then
        if [ -f "$(git -C "$root/axion_sdk" rev-parse --git-dir 2>/dev/null)/shallow" ]; then
            echo "- Unshallowing axion_sdk"
            git -C "$root/axion_sdk" fetch --unshallow
        fi
        git -C "$root/axion_sdk" revert --abort 2>/dev/null || true
        apply_patch "$AXION_PATCH" "$root/axion_sdk"
    else
        echo "[patch] ax_deviceinfo... SKIPPED (target dir not found)"
    fi
fi

# ── system/core (fenrir) ──
apply_patch "$d/patches/0001-libfs_avb-Allow-LKs-patched-with-fenrir-to-boot-on-A.patch" "$root/system/core" || true
apply_patch "$d/patches/0002-fastbootd-Always-return-false-for-GetDeviceLockStatu.patch" "$root/system/core" || true

# ── vndk: drop device-local libbinder-v32 if lineage compat provides it ──
if [ -f "$root/hardware/lineage/compat/vndk/v32/arm64/libbinder-v32.so" ]; then
    apply_patch "$d/patches/0003-vndk-drop-libbinder-v32-prebuilt.patch" "$d"
fi

# ── fuck-bpf ──
FUCK_BPF_DIR="$root/fuck-bpf"
if [ ! -d "$FUCK_BPF_DIR" ]; then
    echo "[fuck-bpf] cloning..."
    git clone https://github.com/ardiandideyashidiq/fuck-bpf "$FUCK_BPF_DIR"
elif [ -d "$FUCK_BPF_DIR/.git" ]; then
    echo "[fuck-bpf] updating..."
    git -C "$FUCK_BPF_DIR" pull --ff-only 2>/dev/null || echo "[fuck-bpf] update skipped (offline or dirty)"
fi

if [ -f "$FUCK_BPF_DIR/apply.py" ]; then
    echo "[fuck-bpf] applying patches..."
    if python3 "$FUCK_BPF_DIR/apply.py" --mb; then
        echo "[fuck-bpf] done"
    else
        echo "[fuck-bpf] FAILED!!!"
    fi
fi
