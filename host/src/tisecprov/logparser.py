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

from enum import Enum
from dataclasses import dataclass


@dataclass
class ErrorInfo:
    code: int
    message: str


# error strings are from
# https://software-dl.ti.com/tisci/esd/latest/2_tisci_msgs/security/keywriter.html?highlight=keywriter
class KeyWriterErrorCodes(Enum):
    KEYWR_ERR_DECRYPT_AES256_KEY = ErrorInfo(0, "Error in decrypting random AES256 key")
    KEYWR_ERR_DECRYPT_BMEK = ErrorInfo(1, "Error in decrypting BMEK")
    KEYWR_ERR_DECRYPT_BMPKH = ErrorInfo(2, "Error in decrypting BMPKH")
    KEYWR_ERR_DECRYPT_SMEK = ErrorInfo(3, "Error in decrypting SMEK")
    KEYWR_ERR_DECRYPT_SMPKH = ErrorInfo(4, "Error in decrypting SMPKH")
    KEYWR_ERR_INTERAL_OP = ErrorInfo(5, "Internal operation error")
    KEYWR_ERR_INVALID_EXT_COUNT = ErrorInfo(
        6, "Invalid extension count in x509 certificate"
    )
    KEYWR_ERR_PARSE_CERT = ErrorInfo(7, "Error in parsing certificate")
    KEYWR_ERR_PARSE_FEK = ErrorInfo(
        8, "Error in parsing TI FEK appended to TIFS binary, before encryption"
    )
    KEYWR_ERR_PARSE_SMPK_CERT = ErrorInfo(9, "Error in parsing SMPK signed certificate")
    KEYWR_ERR_PROGR_BMEK = ErrorInfo(10, "Error in programming BMEK into SoC eFuses")
    KEYWR_ERR_PROGR_BMPKH_PART_1 = ErrorInfo(
        11, "Error in programming BMPKH part 1 into SoC eFuses"
    )
    KEYWR_ERR_PROGR_BMPKH_PART_2 = ErrorInfo(
        12, "Error in programming BMPKH part 2 into SoC eFuses"
    )
    KEYWR_ERR_PROGR_KEYCOUNT = ErrorInfo(
        13, "Error in programming key count into SoC eFuses"
    )
    KEYWR_ERR_PROGR_KEYREV = ErrorInfo(
        14, "Error in programming key revision into SoC eFuses"
    )
    KEYWR_ERR_PROGR_SMEK = ErrorInfo(15, "Error in programming SMEK into SoC eFuses")
    KEYWR_ERR_PROGR_SMPKH_PART_1 = ErrorInfo(
        16, "Error in programming SMPKH part 1 into SoC eFuses"
    )
    KEYWR_ERR_PROGR_SMPKH_PART_2 = ErrorInfo(
        17, "Error in programming SMPKH part 2 into SoC eFuses"
    )
    KEYWR_ERR_VALIDATION_CERT = ErrorInfo(18, "Error validating the certificate")
    KEYWR_ERR_VALIDATION_SMPK_CERT = ErrorInfo(
        19, "Error validating the SMPK signed certificate"
    )
    KEYWR_ERR_VALIDATION_BMPK_KEY = ErrorInfo(20, "Error validating BMPK key")
    KEYWR_ERR_VALIDATION_SMPK_KEY = ErrorInfo(21, "Error validating SMPK key")
    KEYWR_ERR_WRITE_PROT_KEYCOUNT = ErrorInfo(
        22, "Error write protecting key count row"
    )
    KEYWR_ERR_WRITE_PROT_KEYREV = ErrorInfo(
        23, "Error write protecting key revision row"
    )
    KEYWR_ERR_IMG_INTEG_SMPK_CERT = ErrorInfo(
        24, "SMPK signed certificate image integrity failed"
    )
    KEYWR_ERR_PROGR_MSV = ErrorInfo(25, "Error in programming MSV into SoC eFuses")
    KEYWR_ERR_PROGR_SWREV = ErrorInfo(26, "Error in programming SWREV into SoC eFuses")
    KEYWR_ERR_PROGR_FW_CFG_REV = ErrorInfo(
        27, "Error in programming FW CFG REV into SoC eFuses"
    )
    KEYWR_ERR_DECRYPT_EXT_OTP = ErrorInfo(
        28, "Error in decrypting EXT OTP extension field"
    )
    KEYWR_ERR_PROGR_EXT_OTP = ErrorInfo(
        29, "Error in programming EXT OTP extension field"
    )
    KEYWR_ERR_PROGR_OVERRIDE = ErrorInfo(
        30, "Error in programming existing field without override specified"
    )
    KEYWR_ERR_JTAG_DISABLE = ErrorInfo(31, "Error in programming JTAG DISABLE field")


def decode_keywriter_errors(error_code: int) -> list[str]:
    """
    Decode a 32-bit error code into a list of error messages.
    Each bit position corresponds to an error in KeyWriterErrorCodes.

    Args:
        error_code: 32-bit integer containing one or more error flags

    Returns:
        List of error message strings corresponding to each set bit
    """
    error_messages = []

    for error in KeyWriterErrorCodes:
        if error_code & (1 << error.value.code):
            error_messages.append(error.value.message)

    return error_messages


def format_keywriter_errors(error_code: int) -> str:
    """
    Format all keywriter errors into a single string.

    Args:
        error_code: 32-bit integer containing one or more error flags

    Returns:
        Formatted string with all error messages
    """
    errors = decode_keywriter_errors(error_code)
    if not errors:
        return "No errors"
    return "\n".join(f"- {error}" for error in errors)
