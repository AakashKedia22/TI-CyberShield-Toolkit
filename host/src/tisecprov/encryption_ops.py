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
Central encryption operations library.

Device-agnostic encryption operations that work with any CryptoInterface backend.
Provides pad_data, encrypt_binary, decrypt_binary, and encrypt_binary_raw functions.
"""

import os
from enum import Enum
from dataclasses import dataclass
from typing import Optional

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes

from tisecprov.crypto_interfaces import CryptoInterface


class PaddingByte(Enum):
    ZERO = 0x00
    FF = 0xFF


@dataclass
class EncryptionResult:
    """Result of an encryption operation."""
    ciphertext: bytes
    iv: bytes
    r_string: Optional[bytes]  # Only for SBL/TIFS modes
    original_size: int
    derived_key_used: bool
    salt: Optional[bytes]


def pad_data(data: bytes, block_size: int = 16,
             pad_byte: int = 0x00, force_pad: bool = False) -> bytes:
    """
    Pad data to a multiple of block_size using the specified pad byte.

    Args:
        data: Data to pad
        block_size: Block size to align to (default 16)
        pad_byte: Byte value used for padding (default 0x00)
        force_pad: If True, always append padding even when already aligned.
                   When data is already block-aligned, a full block of padding
                   is appended. Needed for compatibility with legacy encryption
                   that always pads (e.g. get_encrypted_file_iv_rs).

    Returns:
        Padded data, or original data if already aligned (unless force_pad)
    """
    remainder = len(data) % block_size
    if remainder == 0:
        if force_pad:
            return data + bytes([pad_byte] * block_size)
        return data
    padding_length = block_size - remainder
    return data + bytes([pad_byte] * padding_length)


def encrypt_binary(
    crypto: CryptoInterface,
    plaintext: bytes,
    padding_mode: PaddingByte = PaddingByte.ZERO,
    salt: Optional[bytes] = None,
    include_r_string: bool = False,
    iv: Optional[bytes] = None,
    force_pad: bool = False,
) -> EncryptionResult:
    """
    Encrypt a binary using a CryptoInterface instance.

    Handles padding, optional HKDF key derivation from salt, optional R-string
    (32-byte random suffix for SBL/TIFS modes), and AES-CBC encryption via
    the crypto backend.

    Args:
        crypto: CryptoInterface instance providing key material and AES operations
        plaintext: Raw binary data to encrypt
        padding_mode: Padding byte (ZERO for SBL/TIFS, FF for firmware)
        salt: If provided, derive encryption key via HKDF from the symmetric key
        include_r_string: If True, append 32 random bytes before encryption (SBL/TIFS)
        iv: Optional IV; if None, a random 16-byte IV is generated
        force_pad: If True, always pad even when data is already block-aligned

    Returns:
        EncryptionResult with ciphertext, iv, and metadata
    """
    original_size = len(plaintext)

    # Pad the data
    padded = pad_data(plaintext, block_size=16, pad_byte=padding_mode.value,
                      force_pad=force_pad)

    # Append R-string if requested (SBL/TIFS encryption modes)
    r_string = None
    if include_r_string:
        r_string = os.urandom(32)
        padded = padded + r_string

    # Derive key from salt if provided, otherwise use raw symmetric key
    derived_key_used = salt is not None
    enc_key = None
    if derived_key_used:
        enc_key = crypto.derive_key_hkdf(salt=salt, length=32)
    else:
        enc_key = crypto.get_symmetric_key()

    # Encrypt
    ciphertext, used_iv = crypto.aes_encrypt(padded, key=enc_key, iv=iv)

    return EncryptionResult(
        ciphertext=ciphertext,
        iv=used_iv,
        r_string=r_string,
        original_size=original_size,
        derived_key_used=derived_key_used,
        salt=salt,
    )


def decrypt_binary(
    crypto: CryptoInterface,
    ciphertext: bytes,
    iv: bytes,
    salt: Optional[bytes] = None,
) -> bytes:
    """
    Decrypt a binary using a CryptoInterface instance.

    Args:
        crypto: CryptoInterface instance providing key material and AES operations
        ciphertext: Encrypted data
        iv: Initialization vector used during encryption
        salt: If provided, derive decryption key via HKDF from the symmetric key

    Returns:
        Decrypted plaintext bytes (may include padding and R-string)
    """
    if salt is not None:
        dec_key = crypto.derive_key_hkdf(salt=salt, length=32)
    else:
        dec_key = crypto.get_symmetric_key()

    return crypto.aes_decrypt(ciphertext, key=dec_key, iv=iv)


def encrypt_binary_raw(
    plaintext: bytes,
    key: bytes,
    padding_mode: PaddingByte = PaddingByte.ZERO,
    salt: Optional[bytes] = None,
    include_r_string: bool = False,
    iv: Optional[bytes] = None,
    force_pad: bool = False,
) -> EncryptionResult:
    """
    Convenience encryption function accepting raw key bytes directly.

    For file-based workflows where keys come from files, not crypto sessions.
    Uses the cryptography library directly instead of a CryptoInterface.

    Args:
        plaintext: Raw binary data to encrypt
        key: Raw AES-256 key bytes (32 bytes)
        padding_mode: Padding byte (ZERO for SBL/TIFS, FF for firmware)
        salt: If provided, derive encryption key via HKDF-SHA512
        include_r_string: If True, append 32 random bytes before encryption
        iv: Optional IV; if None, a random 16-byte IV is generated
        force_pad: If True, always pad even when data is already block-aligned

    Returns:
        EncryptionResult with ciphertext, iv, and metadata
    """
    original_size = len(plaintext)

    # Pad the data
    padded = pad_data(plaintext, block_size=16, pad_byte=padding_mode.value,
                      force_pad=force_pad)

    # Append R-string if requested
    r_string = None
    if include_r_string:
        r_string = os.urandom(32)
        padded = padded + r_string

    # Derive key from salt if provided
    derived_key_used = salt is not None
    if derived_key_used:
        hkdf = HKDF(
            algorithm=hashes.SHA512(),
            length=32,
            salt=salt,
            info=b"",
        )
        enc_key = hkdf.derive(key)
    else:
        enc_key = key

    # Generate IV if needed
    if iv is None:
        iv = os.urandom(16)

    # Encrypt using cryptography library directly
    cipher = Cipher(algorithms.AES(enc_key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(padded) + encryptor.finalize()

    return EncryptionResult(
        ciphertext=ciphertext,
        iv=iv,
        r_string=r_string,
        original_size=original_size,
        derived_key_used=derived_key_used,
        salt=salt,
    )
