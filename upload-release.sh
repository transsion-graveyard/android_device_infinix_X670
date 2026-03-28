#!/usr/bin/env bash
set -e

# ======================
# CONFIG
# ======================
REPO="transsion-graveyard/android_device_infinix_X670"
OUT_DIR="/home/inscrutable/android_development/los_22_2/out/target/product/X670"

export GITHUB_TOKEN=$(gh auth token)

# ======================
# VALIDATE REPO
# ======================
gh repo view "$REPO" >/dev/null 2>&1 || {
    echo "Invalid GitHub repo: $REPO"
    exit 1
}

# ======================
# FIND ARTIFACTS
# ======================
ZIP=$(ls -t "$OUT_DIR"/lineage-*-UNOFFICIAL-*.zip 2>/dev/null | head -n 1)
BOOT_IMG="$OUT_DIR/boot.img"

[[ -z "$ZIP" ]] && { echo "ROM zip not found"; exit 1; }
[[ ! -f "$BOOT_IMG" ]] && { echo "boot.img not found"; exit 1; }

# ======================
# TAG (SAFE UNIQUE)
# ======================
TAG=$(basename "$ZIP" .zip)-$(date +%Y%m%d-%H%M)

echo "ZIP: $ZIP"
echo "BOOT: $BOOT_IMG"
echo "TAG: $TAG"

# ======================
# CREATE RELEASE (IF NOT EXISTS)
# ======================
echo "Checking release..."

if gh release view "$TAG" --repo "$REPO" >/dev/null 2>&1; then
    echo "Release already exists"
else
    echo "Creating release..."
    gh release create "$TAG" \
        --repo "$REPO" \
        --title "$TAG" \
        --notes "LineageOS build for X670"
fi

# ======================
# UPLOAD USING GH CLI (NO CURL)
# ======================
echo "Uploading ROM ZIP..."
GH_PROGRESS=1 gh release upload "$TAG" "$ZIP" --repo "$REPO" --clobber || true

echo "Uploading boot.img..."
GH_PROGRESS=1 gh release upload "$TAG" "$BOOT_IMG" --repo "$REPO" --clobber || true

echo "Done"