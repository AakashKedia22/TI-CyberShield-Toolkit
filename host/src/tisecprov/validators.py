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
Pure validation functions for F29-style certificate generation parameters.

Extracted from gen_keywr_cert_helpers.py. Each function returns a value
and raises ValueError on invalid input (no sys.exit, no global mutation).
"""

import re
from typing import Optional

from tisecprov.device_config import DeviceConfig


def validate_device_sr(device_config: DeviceConfig, silicon_revision: str) -> str:
    """Validate silicon revision against device config.

    Returns the validated silicon_revision string.
    Raises ValueError if the revision is not supported for this device.
    """
    if device_config.silicon_revisions is None:
        return silicon_revision
    if silicon_revision not in device_config.silicon_revisions:
        raise ValueError(
            f"Invalid silicon revision '{silicon_revision}' for device "
            f"'{device_config.device_name}'. "
            f"Supported: {device_config.silicon_revisions}"
        )
    return silicon_revision


def validate_msv(msv_str: str, device_config: DeviceConfig) -> int:
    """Parse and validate MSV hex string. Returns integer value."""
    cleaned = msv_str.replace("0x", "")
    if not re.match(r"^[0-9a-fA-F]+$", cleaned):
        raise ValueError(f"MSV is not a valid hexadecimal number: {msv_str}")

    if device_config.otp_details is not None:
        max_octets = device_config.otp_details.get("MAX_MSV_VALUE_SIZE_OCTETS", 6)
        if len(cleaned) > max_octets:
            raise ValueError(
                f"MSV value too large (> {max_octets * 4} bits): {msv_str}"
            )

    return int(cleaned.rjust(8, "0"), 16)


def validate_key_cnt(keycnt_str: str) -> int:
    """Parse and validate key count. Returns integer value (1 or 3)."""
    cleaned = keycnt_str.replace("0x", "")
    if cleaned in ("1", "01"):
        return 1
    elif cleaned in ("2", "02"):
        return 3  # 0x03 is needed for keycount 2
    else:
        raise ValueError(f"Key count must be 1 or 2, got: {keycnt_str}")


def validate_key_rev(keyrev_str: str) -> int:
    """Parse and validate key revision. Returns integer value (1 or 3)."""
    cleaned = keyrev_str.replace("0x", "")
    if cleaned in ("1", "01"):
        return 1
    elif cleaned in ("2", "02"):
        return 3  # 0x03 is needed for key rev 2
    else:
        raise ValueError(f"Key revision must be 1 or 2, got: {keyrev_str}")


def validate_swrev(
    value_str: str,
    max_bits: int,
    byte_length: int = 4,
    field_name: str = "SWREV",
) -> bytes:
    """Validate and convert a software revision value to bytes.

    Unified replacement for parse_validate_swrev_hsmRT/sbl/sec_app/ssu.
    Returns (1 << int(value_str)) - 1 encoded as big-endian bytes.
    """
    try:
        value = int(value_str)
    except ValueError:
        raise ValueError(f"{field_name} is not a valid integer: {value_str}")

    if value > max_bits:
        raise ValueError(
            f"{field_name} value too high ({value} > {max_bits}): {value_str}"
        )

    encoded = (1 << value) - 1
    return encoded.to_bytes(byte_length, byteorder="big")


def validate_extotp_wprp(wprp_str: str) -> str:
    """Validate extended OTP write-protect/read-protect hex string.

    Returns the padded wprp string (doubled for wp||rp).
    """
    cleaned = wprp_str.replace("0x", "")
    if not all(c in "0123456789abcdefABCDEF" for c in cleaned):
        raise ValueError(
            f"EXT OTP WP_RP is not a valid hexadecimal number: {wprp_str}"
        )
    padded = cleaned.zfill(16)
    return f"{padded}{padded}"


def validate_mpk_opt(mpk_opt_str: str, device_config: DeviceConfig) -> int:
    """Parse and validate MPK options hex string. Returns integer value."""
    cleaned = mpk_opt_str.replace("0x", "")
    if not re.match(r"^[0-9a-fA-F]+$", cleaned):
        raise ValueError(
            f"MPK_OPT is not a valid hexadecimal number: {mpk_opt_str}"
        )

    if device_config.otp_details is not None:
        max_octets = device_config.otp_details.get("MAX_MPK_OPT_VALUE_SIZE_OCTETS", 3)
        if len(cleaned) > max_octets:
            raise ValueError(
                f"MPK_OPT value too large (> {max_octets} octets): {mpk_opt_str}"
            )

    return int(cleaned, 16)


def validate_mek_opt(mek_opt_str: str, device_config: DeviceConfig) -> int:
    """Parse and validate MEK options hex string. Returns integer value."""
    cleaned = mek_opt_str.replace("0x", "")
    if not re.match(r"^[0-9a-fA-F]+$", cleaned):
        raise ValueError(
            f"MEK_OPT is not a valid hexadecimal number: {mek_opt_str}"
        )

    if device_config.otp_details is not None:
        max_octets = device_config.otp_details.get("MAX_MEK_OPT_VALUE_SIZE_OCTETS", 2)
        if len(cleaned) > max_octets:
            raise ValueError(
                f"MEK_OPT value too large (> {max_octets} octets): {mek_opt_str}"
            )

    return int(cleaned, 16)
