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
Extended OTP data construction.

Pure function that constructs the padded hex string for the full OTP
region. Uses DeviceConfig.otp_details instead of importing from devices.py.
"""

import re

from tisecprov.device_config import DeviceConfig


def construct_ext_otp_hex(
    ext_otp_data: str,
    start_index: int,
    data_size: int,
    device_config: DeviceConfig,
) -> str:
    """Construct padded hex string for the full OTP region.

    Args:
        ext_otp_data: hex string (with or without '0x' prefix)
        start_index: bit offset into the eFuse array
        data_size: size of data in bits
        device_config: device configuration with otp_details

    Returns:
        Padded hex string covering the full OTP region.

    Raises:
        ValueError: on invalid input parameters.
    """
    if device_config.otp_details is None:
        raise ValueError(
            f"Device '{device_config.device_name}' has no otp_details configured"
        )

    otp = device_config.otp_details
    max_ext_otp_size = otp["MAX_EXT_OTP_SIZE"]
    min_ext_prog_bits = otp["MIN_EXT_PROG_BITS"]

    if not ext_otp_data:
        raise ValueError("ext_otp_data cannot be empty")

    if start_index < 0:
        raise ValueError("start_index must be a non-negative integer")

    if start_index > (max_ext_otp_size - min_ext_prog_bits):
        raise ValueError(
            f"start_index too large: max allowed is "
            f"{max_ext_otp_size - min_ext_prog_bits}"
        )

    if data_size <= 0:
        raise ValueError("data_size must be a positive integer")

    if data_size > max_ext_otp_size:
        raise ValueError(
            f"data_size too large: max allowed is {max_ext_otp_size}"
        )

    if (start_index + data_size) > max_ext_otp_size:
        raise ValueError(
            f"start_index + data_size ({start_index + data_size}) "
            f"exceeds MAX_EXT_OTP_SIZE ({max_ext_otp_size})"
        )

    if (start_index % min_ext_prog_bits) != 0:
        raise ValueError(
            f"start_index ({start_index}) must be a multiple of "
            f"MIN_EXT_PROG_BITS ({min_ext_prog_bits})"
        )

    if (data_size % min_ext_prog_bits) != 0:
        raise ValueError(
            f"data_size ({data_size}) must be a multiple of "
            f"MIN_EXT_PROG_BITS ({min_ext_prog_bits})"
        )

    # Strip 0x prefix
    cleaned = ext_otp_data.replace("0x", "")

    if not re.match(r"^[0-9a-fA-F]+$", cleaned):
        raise ValueError("ext_otp_data is not a valid hexadecimal number")

    if data_size < (len(cleaned) * 4):
        raise ValueError(
            f"data_size ({data_size}) is less than the input data size "
            f"({len(cleaned) * 4} bits)"
        )

    # Pad to match data_size
    otp_octets = data_size // 4
    cleaned = cleaned.rjust(otp_octets, "0")

    # Build final padded string covering the full OTP region
    leading_zero_octets = start_index // 4
    trailing_zero_octets = (max_ext_otp_size // 4) - leading_zero_octets - otp_octets

    leading = "0" * leading_zero_octets
    trailing = "0" * trailing_zero_octets

    if start_index > 0:
        return f"{leading}{cleaned}{trailing}"
    else:
        return f"{cleaned}{trailing}"
