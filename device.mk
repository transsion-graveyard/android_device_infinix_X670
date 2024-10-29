#
# Copyright (C) 2025 The LineageOS Project
#
# SPDX-License-Identifier: Apache-2.0
#

# Virtual A/B
$(call inherit-product, $(SRC_TARGET_DIR)/product/virtual_ab_ota.mk)

# Dynamic partitions
PRODUCT_USE_DYNAMIC_PARTITIONS := true

# Soong namespaces
PRODUCT_SOONG_NAMESPACES += \
    $(LOCAL_PATH)

# Shipping API Level
PRODUCT_SHIPPING_API_LEVEL := 30

# Project ID Quota
$(call inherit-product, $(SRC_TARGET_DIR)/product/emulated_storage.mk)

# Dalvik configs
$(call inherit-product, frameworks/native/build/phone-xhdpi-6144-dalvik-heap.mk)

# AB OTA Configuration
AB_OTA_UPDATER := true
AB_OTA_PARTITIONS := \
    boot \
    system \
    system_ext \
    vendor \
    product \
    vbmeta \
    vbmeta_system \
    vbmeta_vendor

PRODUCT_PACKAGES += \
    update_engine \
    update_engine_sideload \
    update_verifier \
    otapreopt_script \
    checkpoint_gc

AB_OTA_POSTINSTALL_CONFIG += \
    RUN_POSTINSTALL_system=true \
    POSTINSTALL_PATH_system=system/bin/otapreopt_script \
    FILESYSTEM_TYPE_system=$(BOARD_SYSTEMIMAGE_FILE_SYSTEM_TYPE) \
    POSTINSTALL_OPTIONAL_system=true

AB_OTA_POSTINSTALL_CONFIG += \
    RUN_POSTINSTALL_vendor=true \
    POSTINSTALL_PATH_vendor=bin/checkpoint_gc \
    FILESYSTEM_TYPE_vendor=$(BOARD_VENDORIMAGE_FILE_SYSTEM_TYPE) \
    POSTINSTALL_OPTIONAL_vendor=true


# Init scripts
PRODUCT_PACKAGES += \
    init.cgroup.rc \
    init_connectivity.rc \
    init.connectivity.rc \
    init.connectivity.common.rc \
    init.mt6781.rc \
    init.mt6781.usb.rc \
    init.project.rc \
    init.modem.rc \
    init.sensor_1_0.rc \
    ueventd.mt6781.rc \
    init.recovery.usb.rc \
    fstab.mt6781 \
    fstab.mt6781.ramdisk

# Inherit our proprietary vendor
$(call inherit-product, vendor/xiaomi/viva/viva-vendor.mk)
