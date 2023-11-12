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
    'device/xiaomi/viva',
    'hardware/mediatek',
    'hardware/mediatek/libmtkperf_client',
    'hardware/lineage/compat',
    'hardware/xiaomi'
]

def fixup_ndk_platform(libname: str) -> tuple[str, str]:
    """
    Replace -ndk_platform with -ndk
    """
    return (libname, libname.replace("-ndk_platform.so", "-ndk.so"))

patchelf_version = "0_17_2"

def lib_fixup_vendor_suffix(lib: str, partition: str, *args, **kwargs):
    return f'{lib}_{partition}' if partition == 'vendor' else None


lib_fixups: lib_fixups_user_type = {
    **lib_fixups,
    ('vendor.mediatek.hardware.videotelephony@1.0'): lib_fixup_vendor_suffix
}


blob_fixups: blob_fixups_user_type = {
    "vendor/etc/init/android.hardware.media.c2@1.2-mediatek.rc": blob_fixup().regex_replace(
        "@1.2-mediatek", "@1.2-mediatek-64b"
    ),
    "vendor/etc/init/android.hardware.bluetooth@1.1-service-mediatek.rc": blob_fixup().regex_replace(
        "on property:vts(.|\n)*", ""
    ),
    "vendor/etc/init/android.hardware.neuralnetworks@1.3-service-mtk-neuron.rc": blob_fixup().regex_replace(
        "start", "enable"
    ),
    "vendor/lib64/libgoodixhwfingerprint.so": blob_fixup().replace_needed(
        "libvendor.goodix.hardware.biometrics.fingerprint@2.1.so", "vendor.goodix.hardware.biometrics.fingerprint@2.1.so"
    ),
    (
        "vendor/bin/hw/android.hardware.gnss-service.mediatek",
        "vendor/lib64/hw/android.hardware.gnss-impl-mediatek.so",
    ): blob_fixup().replace_needed(
        *fixup_ndk_platform("android.hardware.gnss-V1-ndk_platform.so")
    ),
    "vendor/bin/hw/android.hardware.media.c2@1.2-mediatek-64b": blob_fixup()
        .patchelf_version(patchelf_version)
        .replace_needed("libavservices_minijail_vendor.so", "libavservices_minijail.so")
        .add_needed("libstagefright_foundation-v33.so"),
}  # fmt: skip

module = ExtractUtilsModule(
    'viva',
    'xiaomi',
    blob_fixups=blob_fixups,
    lib_fixups=lib_fixups,
    namespace_imports=namespace_imports,
)

if __name__ == '__main__':
    utils = ExtractUtils.device(module)
    utils.run()
