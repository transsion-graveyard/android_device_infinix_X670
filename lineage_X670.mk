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
