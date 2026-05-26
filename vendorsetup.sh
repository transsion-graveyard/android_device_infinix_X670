#!/bin/sh
cd axion_sdk
if [ -f "$(git rev-parse --git-dir)/shallow" ]; then
    echo "- Unshallowing repo"
    git fetch --unshallow
fi
echo "- Revert DeviceInfoProvider change to fix battery capacity reporting issue
git revert --no-edit 31bd050ea71c8a0990056c8c985ece31f2e5842d
croot
