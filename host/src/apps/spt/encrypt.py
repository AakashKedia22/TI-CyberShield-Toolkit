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
Module that deals with encrypting binaries.
"""
from pathlib import Path


def encrypt_args(subparsers):
    """Define arguments for encrypt sub-command"""
    encrypt_parser = subparsers.add_parser(
        "encrypt",
        help="encrypt a binary with the given symmetric key",
        description="encrypt a binary with the given symmetric key",
    )
    encrypt_parser.add_argument("-i", "--input", required=True,
                                help="Input binary file")
    encrypt_parser.add_argument("-o", "--output", required=True,
                                help="Output encrypted file")
    encrypt_parser.add_argument("-k", "--key", required=True,
                                help="Encryption key file")
    encrypt_parser.add_argument("--encryption-mode",
                                choices=["sbl_enc", "tifs_enc", "fw_enc"],
                                default="sbl_enc",
                                help="Encryption mode (default: sbl_enc)")
    encrypt_parser.add_argument("--kd-salt",
                                help="Key derivation salt file")
    encrypt_parser.add_argument("-s", "--session", default="Development",
                                help="Session name (default: Development)")
    encrypt_parser.add_argument("-p", "--password", default="develop123#",
                                help="Session password")


def encrypt_binary_command(args):
    """
    Execute the encrypt binary command using the core API.

    Args:
        args: Parsed command line arguments with input, output, key,
              encryption_mode, kd_salt, session, password
    """
    from apps.tifs.core.types import (
        EncryptionConfig, ExtendedAttributes, SessionInfo,
        EncryptionAlgorithm, PaddingMode,
    )
    from apps.tifs.core.api import encrypt_binary

    # Determine padding mode from encryption mode
    encryption_mode = getattr(args, 'encryption_mode', 'sbl_enc')
    if encryption_mode == 'fw_enc':
        padding = PaddingMode.FF
    else:
        padding = PaddingMode.ZERO

    encryption = EncryptionConfig(
        enabled=True,
        algorithm=EncryptionAlgorithm.AES_256_CBC,
        key_file=Path(args.key),
        iv_salt=Path(args.kd_salt) if getattr(args, 'kd_salt', None) else None,
        padding_mode=padding,
    )

    session = SessionInfo(
        session_name=getattr(args, 'session', 'Development'),
        session_password=getattr(args, 'password', 'develop123#'),
        is_development=(getattr(args, 'session', 'Development') == 'Development'),
    )

    # Determine device from args if available, default to f29h85x
    device = getattr(args, 'device', 'f29h85x')
    if device is None:
        device = 'f29h85x'

    extended = ExtendedAttributes(attributes={
        'soc_id': device.lower(),
        'device_family': 'asm',
        'encryption_mode': encryption_mode,
    })

    image_path = Path(args.input)
    output_path = Path(args.output)

    result = encrypt_binary(
        image_path=image_path,
        output_path=output_path,
        encryption=encryption,
        session=session,
        extended=extended,
    )

    if result.success:
        print(f"Encryption successful: {result.output_path}")
        if result.metadata.get('iv'):
            print(f"  IV: {result.metadata['iv']}")
        if result.metadata.get('r_string'):
            print(f"  R-string: {result.metadata['r_string']}")
        if result.metadata.get('salt'):
            print(f"  Salt: {result.metadata['salt']}")
    else:
        print(f"Encryption failed: {result.message}")
