#
# Copyright (C) 2025 The LineageOS Project
#
# SPDX-License-Identifier: Apache-2.0
#

# Inherit from those products. Most specific fist.
$(call inherit-product, $(SRC_TARGET_DIR)/product/core_64_bit_only.mk)
$(call inherit-product, $(SRC_TARGET_DIR)/product/full_base_telephony.mk)

# Inherit from device makefile
$(call inherit-product, device/infinix/X670/device.mk)

# Inherit some common LineageOS Stuff
$(call inherit-product, vendor/lineage/config/common_full_phone.mk)

PRODUCT_NAME := lineage_X670
PRODUCT_DEVICE := X670
PRODUCT_MANUFACTURER := Infinix
PRODUCT_BRAND := Infinix
PRODUCT_MODEL := Infinix X670

PRODUCT_GMS_CLIENTID_BASE := android-transsion

PRODUCT_BUILD_PROP_OVERRIDES += \
    DeviceName=X670 \
    BuildFingerprint=Infinix/X670-GL/Infinix-X670:12/SP1A.210812.016/240224V150:user/release-keys

PERF_ANIM_OVERRIDE := true
WITH_GMS := false

# Time
LINEAGE_VERSION_APPEND_TIME_OF_DAY := true

# AxionOS

# Define rear camera specs (multiple sensors supported)
AXION_CAMERA_REAR_INFO := 50MP  # Example: 50MP + 48MP

# Define front camera specs
AXION_CAMERA_FRONT_INFO := 16MP  # Example: 42MP

# Maintainer name (use "_" for spaces, e.g., "rmp_22" → "rmp 22" in UI)
AXION_MAINTAINER := R

# Processor name (use "_" for spaces)
AXION_PROCESSOR := Mediatek_Helio_G96

AXION_DEBUGGING_ENABLED := true

TARGET_INCLUDES_LOS_PREBUILTS := true

