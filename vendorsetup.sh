#!/bin/sh
PATCH="device/infinix/X670/patches/0001-ax_deviceinfo-use-power-profile-for-battery-capacity.patch"
TARGET="axion_sdk/ax_deviceinfo/src/com/android/axion/deviceinfo/DeviceInfoProvider.kt"

if [ ! -f "$TARGET" ] || [ ! -f "$PATCH" ]; then
    return 0 2>/dev/null || exit 0
fi

cd axion_sdk
if [ -f "$(git rev-parse --git-dir)/shallow" ]; then
    echo "- Unshallowing repo"
    git fetch --unshallow
fi
git revert --abort 2>/dev/null || true
echo "- Applying battery capacity fix patch"
git am -3 "../$PATCH" 2>/dev/null || true
croot
