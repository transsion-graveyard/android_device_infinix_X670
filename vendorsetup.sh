#!/bin/sh
cd axion_sdk
if [ -f "$(git rev-parse --git-dir)/shallow" ]; then
    echo "- Unshallowing repo"
    git fetch --unshallow
fi
# Abort any stale revert state from previous runs
git revert --abort 2>/dev/null || true
echo "- Applying battery capacity fix patch"
git am -3 ../device/infinix/X670/0001-ax_deviceinfo-use-power-profile-for-battery-capacity.patch 2>/dev/null || true
croot
