#!/usr/bin/env python3
# Copyright (C) 2026 Texas Instruments Incorporated
#
# All rights reserved not granted herein.
# Limited License.
#
# Texas Instruments Incorporated grants a world-wide, royalty-free,
# non-exclusive license under copyrights and patents it now or hereafter
# owns or controls to make, have made, use, import, offer to sell and sell ("Utilize")
# this software subject to the terms herein.  With respect to the foregoing patent
# license, such license is granted  solely to the extent that any such patent is necessary
# to Utilize the software alone.  The patent license shall not apply to any combinations which
# include this software, other than combinations with devices manufactured by or for TI ("TI Devices").
# No hardware patent is licensed hereunder.
#
# Redistributions must preserve existing copyright notices and reproduce this license (including the
# above copyright notice and the disclaimer and (if applicable) source code license limitations below)
# in the documentation and/or other materials provided with the distribution
#
# Redistribution and use in binary form, without modification, are permitted provided that the following
# conditions are met:
#
#    * No reverse engineering, decompilation, or disassembly of this software is permitted with respect to any
#     software provided in binary form.
#    * any redistribution and use are licensed by TI for use only with TI Devices.
#    * Nothing shall obligate TI to provide you with source code for the software licensed and provided to you in object code.
#
# If software source code is provided to you, modification and redistribution of the source code are permitted
# provided that the following conditions are met:
#
#   * any redistribution and use of the source code, including any resulting derivative works, are licensed by
#     TI for use only with TI Devices.
#   * any redistribution and use of any object code compiled from the source code and any resulting derivative
#     works, are licensed by TI for use only with TI Devices.
#
# Neither the name of Texas Instruments Incorporated nor the names of its suppliers may be used to endorse or
# promote products derived from this software without specific prior written permission.
#
# DISCLAIMER.
#
# THIS SOFTWARE IS PROVIDED BY TI AND TI'S LICENSORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING,
# BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL TI AND TI'S LICENSORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA,
# OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

"""
Device Utilities Module

Centralized utilities for device-specific operations including path resolution,
device family inference, and output directory management.
"""

import os
import pathlib
from typing import Optional, Dict


DEVICE_FAMILY_MAP = {
    "f29h85x": "asm",
    "am62px": "sitara",
    "j722s": "jacinto",
}


def infer_device_family(device_name: str) -> str:
    """
    Infer device family from device name using configuration map.

    Args:
        device_name (str): Device name (e.g., "f29h85x", "am62px")

    Returns:
        str: Device family ("asm", "sitara", "jacinto", or "asm" as default)

    Examples:
        >>> infer_device_family("f29h85x")
        'asm'
        >>> infer_device_family("am62px")
        'sitara'
        >>> infer_device_family("j722s")
        'jacinto'
    """
    if not device_name:
        return "asm"

    device_lower = device_name.lower()

    if device_lower in DEVICE_FAMILY_MAP:
        return DEVICE_FAMILY_MAP[device_lower]

    for prefix, family in DEVICE_FAMILY_MAP.items():
        if device_lower.startswith(prefix):
            return family

    return "asm"


def get_device_prebuilt_dir(device_name: Optional[str] = None, device_family: Optional[str] = None) -> pathlib.Path:
    """
    Get the prebuilt images directory for a specific device.

    Args:
        device_name (str): Device name (required)
        device_family (str, optional): Device family. If not provided, will be inferred from device_name.

    Returns:
        pathlib.Path: Path to the prebuilt images directory

    Raises:
        ValueError: If device_name is not provided

    Examples:
        >>> get_device_prebuilt_dir("f29h85x")
        PosixPath('/path/to/tisecprov/host/bin/asm/f29h85x')

        >>> get_device_prebuilt_dir("am62px", "sitara")
        PosixPath('/path/to/tisecprov/host/bin/sitara/am62px')
    """
    import sys
    from common.platform_utils import get_prebuilt_images_dir

    if device_name is None:
        raise ValueError("device_name is required. Please provide a valid device name.")

    if device_family is None:
        device_family = infer_device_family(device_name)

    return get_prebuilt_images_dir(device_family, device_name)


def get_device_output_dir(device_name: Optional[str], output_type: str, create: bool = True) -> str:
    """
    Get device-specific output directory path.

    Args:
        device_name (str): Device name (required, e.g., "f29h85x")
        output_type (str): Type of output directory:
            - "certificates": General certificates directory
            - "signedImages": Signed binary images directory
            - "rot_cert": Root of Trust certificates
            - "debug_cert": Debug certificates
            - "seccfg": Security configuration files
            - "custom_signed": Custom signed binaries
            - "code": Code provisioning files
        create (bool): Whether to create the directory if it doesn't exist (default: True)

    Returns:
        str: Full path to the output directory

    Raises:
        ValueError: If device_name is not provided

    Examples:
        >>> get_device_output_dir("f29h85x", "certificates")
        '/home/user/ti/f29h85x/certificates'

        >>> get_device_output_dir("am62px", "signedImages")
        '/home/user/ti/am62px/signedImages'
    """
    if device_name is None:
        raise ValueError("device_name is required. Please provide a valid device name.")

    home_dir = os.path.expanduser("~")
    output_dir = os.path.join(home_dir, "ti", device_name, output_type)

    if create:
        os.makedirs(output_dir, exist_ok=True)

    return output_dir


def get_device_file_pattern(device_name: str, file_type: str, **kwargs) -> str:
    """
    Get device-specific file name pattern.

    Args:
        device_name (str): Device name (e.g., "f29h85x")
        file_type (str): Type of file:
            - "otp_keywriter": OTP keywriter binary
            - "tifs_cp": TIFS code provisioning binary
            - "tifs_release": TIFS release binary
            - "uart_sbl": UART SBL binary
            - "jtag_kernel": JTAG kernel binary
        **kwargs: Additional parameters (e.g., variant="fs" or variant="se")

    Returns:
        str: File name pattern

    Examples:
        >>> get_device_file_pattern("f29h85x", "otp_keywriter", variant="fs")
        'otp_kw_f29h85x_hs_fs.hsmimage.bin'

        >>> get_device_file_pattern("f29h85x", "tifs_cp")
        'tifs_f29h85x_hs_se_code_provisioning.release.bin'
    """
    variant = kwargs.get("variant", "fs")

    patterns: Dict[str, str] = {
        "otp_keywriter": f"otp_kw_{device_name}_hs_{variant}.hsmimage.bin",
        "tifs_cp": f"tifs_{device_name}_hs_se_code_provisioning.release.bin",
        "tifs_release": f"tifs_{device_name}_hs_se.release.bin",
        "uart_sbl": "ram_based_uart_sbl.bin",
        "jtag_kernel": "secure_ram_based_jtag_kernel.out",
        "uart_flash_programmer": "uart_flash_programmer",
        "uart_flash_programmer_exe": "uart_flash_programmer.exe",
    }

    return patterns.get(file_type, "")


def validate_device_paths(device_name: str, device_family: Optional[str] = None) -> tuple[bool, str]:
    """
    Validate that device paths exist.

    Args:
        device_name (str): Device name
        device_family (str, optional): Device family

    Returns:
        tuple[bool, str]: (is_valid, error_message)
    """
    try:
        prebuilt_dir = get_device_prebuilt_dir(device_name, device_family)
        if not prebuilt_dir.exists():
            return False, f"Prebuilt directory does not exist: {prebuilt_dir}"
        return True, ""
    except Exception as e:
        return False, f"Error validating device paths: {str(e)}"
