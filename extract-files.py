#!/usr/bin/env -S PYTHONPATH=../../../tools/extract-utils python3
#
# SPDX-FileCopyrightText: 2024 The LineageOS Project
# SPDX-License-Identifier: Apache-2.0
#

from extract_utils.file import File
from extract_utils.fixups_blob import (
    BlobFixupCtx,
    blob_fixup,
    blob_fixups_user_type,
)
from extract_utils.fixups_lib import (
    lib_fixup_remove,
    lib_fixups,
    lib_fixups_user_type,
)
from extract_utils.main import (
    ExtractUtils,
    ExtractUtilsModule,
)
from extract_utils.tools import (
    llvm_objdump_path,
)
from extract_utils.utils import (
    run_cmd,
)

namespace_imports = [
    "hardware/mediatek",
    "hardware/mediatek/libmtkperf_client",
    "device/infinix/X670",
]


def fixup_ndk_platform(libname: str) -> tuple[str, str]:
    """
    Replace -ndk_platform with -ndk
    """
    return (libname, libname.replace("-ndk_platform.so", "-ndk.so"))


patchelf_version = "0_17_2"

lib_fixups: lib_fixups_user_type = {
    **lib_fixups,
}


blob_fixups: blob_fixups_user_type = {
    'system/lib64/libem_support_jni.so': blob_fixup()
        .add_needed('libjni_shim.so'),
    ('vendor/bin/hw/android.hardware.usb@1.2-service-mediatekv2', 'vendor/lib64/libgoodixhwfingerprint.so', 'vendor/bin/hw/android.hardware.neuralnetworks@1.3-service-mtk-neuron', 'vendor/lib/libnvram.so', 'vendor/lib64/libnvram.so', 'vendor/lib64/libsysenv.so'): blob_fixup()
        .add_needed('libbase_shim.so'),    
    'vendor/lib64/hw/fingerprint.default.so': blob_fixup()
        .binary_regex_replace(b'fpsensor_fingerprint', b'fingerprint\x00\x00\x00\x00\x00\x00\x00\x00\x00'),
    "vendor/lib64/hw/audio.primary.mt6781.so": blob_fixup()
        .replace_needed("libutils.so", "libutils-v32.so")
        .replace_needed("libalsautils.so", "libalsautils-v32.so"),
    "vendor/etc/init/android.hardware.bluetooth@1.1-service-mediatek.rc": blob_fixup().regex_replace(
        "on property:vts(.|\n)*", ""
    ),
    (
        "vendor/etc/init/android.hardware.neuralnetworks@1.3-service-mtk-neuron.rc",
    ): blob_fixup().regex_replace("start", "enable"),
    (
        "vendor/bin/hw/android.hardware.gnss-service.mediatek",
        "vendor/lib64/hw/android.hardware.gnss-impl-mediatek.so",
    ): blob_fixup().replace_needed(
        *fixup_ndk_platform("android.hardware.gnss-V1-ndk_platform.so")
    ),
    (
        'vendor/lib64/hw/sensors.mediatek.V2.0.so',
        'vendor/lib64/libcodec2_mtk_c2store.so',
        'vendor/lib64/libcodec2_mtk_vdec.so',
        'vendor/lib64/libcodec2_mtk_venc.so',
        'vendor/lib64/libcodec2_vpp_qt_plugin.so',
        'vendor/lib64/libcodec2_vpp_rs_plugin.so'
    ): blob_fixup()
        .replace_needed('libstagefright_foundation.so', 'libstagefright_foundation-v33.so'),
    (
        "vendor/lib64/libwvhidl.so",
        "vendor/lib64/mediadrm/libwvdrmengine.so",
    ): blob_fixup()
        .patchelf_version(patchelf_version)
        .replace_needed("libprotobuf-cpp-lite-3.9.1.so", "libprotobuf-cpp-full-3.9.1.so"),
    (
        "vendor/bin/mnld",
        "vendor/lib64/libaalservice.so",
        "vendor/lib64/libcam.utils.sensorprovider.so",
        "vendor/lib64/hw/android.hardware.sensors@2.X-subhal-mediatek.so",
    ): blob_fixup()
        .patchelf_version(patchelf_version)
        .add_needed("android.hardware.sensors@1.0-convert-shared.so"),
    (
        "vendor/lib64/lib3a.flash.so",
        "vendor/lib64/libaaa_ltm.so",
        "vendor/lib64/lib3a.ae.stat.so",
        "vendor/lib64/lib3a.sensors.color.so",
        "vendor/lib64/lib3a.sensors.flicker.so",
    ): blob_fixup()
        .patchelf_version(patchelf_version)
        .add_needed("liblog.so"),
    ('vendor/lib64/hw/vendor.mediatek.hardware.pq@2.15-impl.so', 'vendor/bin/hw/vendor.mediatek.hardware.pq@2.2-service'): blob_fixup()
        .replace_needed('libhidlbase.so', 'libhidlbase-v32.so')
        .replace_needed('libbinder.so', 'libbinder-v32.so')
        .replace_needed('libutils.so', 'libutils-v32.so')
        .replace_needed('libsensorndkbridge.so', 'android.hardware.sensors@1.0-convert-shared.so'),
    (
        "vendor/lib64/libmtkcam_stdutils.so",
        "vendor/lib64/hw/android.hardware.camera.provider@2.6-impl-mediatek.so",
    ): blob_fixup()
        .patchelf_version(patchelf_version)
        .replace_needed("libutils.so", "libutils-v32.so")
        .add_needed("android.hardware.camera.device@3.6.so")
        .add_needed("libcamera_metadata_shim.so"),
    (
        "vendor/lib64/libmnl.so",
        "vendor/lib64/mt6893/libmnl.so",
    ): blob_fixup()
        .patchelf_version(patchelf_version)
        .add_needed("libcutils.so"),
    "vendor/lib64/librt_extamp_intf.so": blob_fixup()
        .patchelf_version(patchelf_version),
    (
        "vendor/lib/libnvram.so",
        "vendor/lib64/libnvram.so",
        "vendor/lib64/libsysenv.so",
        "vendor/lib64/libtflite_mtk.so",
        "vendor/bin/hw/android.hardware.neuralnetworks@1.3-service-mtk-neuron",
    ): blob_fixup()
        .add_needed('libbase_shim.so'),
    "vendor/lib64/hw/hwcomposer.mt6781.so": blob_fixup()
        .add_needed('libprocessgroup_shim.so'),
    "vendor/lib64/hw/vendor.mediatek.hardware.camera.isphal@1.0-impl.so": blob_fixup()
        .patchelf_version(patchelf_version)
        .replace_needed("libhidlbase.so", "libhidlbase-v32.so")
        .replace_needed("libbinder.so", "libbinder-v32.so")
        .replace_needed("libutils.so", "libutils-v32.so"),
    "vendor/bin/hw/camerahalserver": blob_fixup()
        .patchelf_version(patchelf_version)
        .add_needed("android.hardware.camera.device@3.6.so")
        .add_needed("libhidlbase_shim.so")
        .add_needed("libprocessgroup_shim.so"),
    "vendor/lib64/libmtkcam_featurepolicy.so": blob_fixup()
        .binary_regex_replace(b"\x34\xE8\x87\x40\xB9", b"\x34\x28\x02\x80\x52"),
    'vendor/bin/hw/mtkfusionrild': blob_fixup()
        .add_needed('libutils-v32.so'),
    (
        "vendor/lib64/libtranssion_bodybeauty.so",
        "vendor/lib64/libMegviiHum.so",
    ): blob_fixup()
        .clear_symbol_version('AHardwareBuffer_allocate')
        .clear_symbol_version('AHardwareBuffer_createFromHandle')
        .clear_symbol_version('AHardwareBuffer_describe')
        .clear_symbol_version('AHardwareBuffer_getNativeHandle')
        .clear_symbol_version('AHardwareBuffer_lock')
        .clear_symbol_version('AHardwareBuffer_lockPlanes')
        .clear_symbol_version('AHardwareBuffer_release')
        .clear_symbol_version('AHardwareBuffer_unlock'),
}  # fmt: skip

module = ExtractUtilsModule(
    "X670",
    "infinix",
    blob_fixups=blob_fixups,
    lib_fixups=lib_fixups,
    namespace_imports=namespace_imports,
    add_firmware_proprietary_file=True,
)

if __name__ == "__main__":
    utils = ExtractUtils.device(module)
    utils.run()
