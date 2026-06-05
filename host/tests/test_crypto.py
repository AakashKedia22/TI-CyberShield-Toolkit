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

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes

from tisecprov.crypto import (
    ManufacturerKeys,
)

from tisecprov.cryptoutils import (
    FixedSizeBytes,
    hash_data,
    gen_aes256_key,
)


def pad_to_multiple_64(data: bytes) -> bytes:
    """Pad data to multiple of 64 bytes by appending zeros"""
    remainder = len(data) % 64
    if remainder == 0:
        return data
    padding_needed = 64 - remainder
    return data + (b"\0" * padding_needed)


def unpad_from_multiple_64(padded_data: bytes) -> bytes:
    """Remove zero padding from data that was padded to multiple of 64"""
    # Find the position of the last non-zero byte
    for i in range(len(padded_data) - 1, -1, -1):
        if padded_data[i] != 0:
            return padded_data[: i + 1]
    return b""  # Return empty bytes if all zeros


def test_fixed_size_bytes_valid():
    data = b"12345678"
    size = 8
    fsb = FixedSizeBytes(data, size)
    assert fsb.data == data


def test_fixed_size_bytes_invalid():
    data = b"1234567"
    size = 8
    with pytest.raises(ValueError):
        FixedSizeBytes(data, size)


def test_manufacturer_keys_repr():
    keys = ManufacturerKeys()
    repr_str = repr(keys)
    assert "ManufacturerKeys(symmetric_key=" in repr_str
    assert "..." in repr_str


def test_manufacturer_keys_rsa_encrypt_decrypt():
    keys = ManufacturerKeys()
    plaintext = b"This is a test message."

    # Encrypt
    ciphertext = keys.rsa_encrypt_with_pkcs15_padding(plaintext)

    # Decrypt
    decrypted_plaintext = keys.rsa_decrypt_with_pkcs15_padding(ciphertext)

    assert decrypted_plaintext == plaintext


def test_manufacturer_keys_sign():
    keys = ManufacturerKeys()
    message = b"This is a test message."
    signature = keys.sign(message)
    assert isinstance(signature, bytes)
    assert len(signature) > 0


def test_rsa_encrypt_decrypt_roundtrip():
    keys = ManufacturerKeys()
    plaintext = b"This is a test message."

    # encrypt
    ciphertext = keys.rsa_encrypt_with_pkcs15_padding(plaintext)

    # Decrypt
    decrypted_plaintext = keys.rsa_decrypt_with_pkcs15_padding(ciphertext)

    assert decrypted_plaintext == plaintext


def test_hash_data():
    data = b"This is a test message."
    hash = hash_data(data)
    assert len(hash) == 64
    assert isinstance(hash, bytes)


def test_aes_cbc_256_encrypt_decrypt():
    # Generate a random 256-bit key
    keys = ManufacturerKeys()

    # Define the plaintext to be encrypted
    plaintext = b"This is a test message for AES-256 encryption."
    padded_plaintext = pad_to_multiple_64(plaintext)

    aes_key = gen_aes256_key().data

    # Encrypt using CryptoInterface
    ciphertext, iv = keys.aes_encrypt(padded_plaintext, key=aes_key)

    # Decrypt using CryptoInterface
    padded_decrypted_text = keys.aes_decrypt(ciphertext, key=aes_key, iv=iv)

    decrypted_text = unpad_from_multiple_64(padded_decrypted_text)

    # Verify that the decrypted text matches the original plaintext
    assert (
        decrypted_text == plaintext
    ), "Decrypted text does not match the original plaintext"


def test_sign():
    keys = ManufacturerKeys()

    # Create a message to sign
    message = b"This is a test message."

    # Sign the message
    signature = keys.sign(message)

    # Verify the signature using the public key
    pubkey_bytes = keys.get_public_key()
    public_key_obj = serialization.load_pem_public_key(pubkey_bytes)
    try:
        public_key_obj.verify(
            signature,
            message,
            padding.PKCS1v15(),
            hashes.SHA512(),
        )
    except Exception as e:
        pytest.fail(f"Signature verification failed: {e}")

    assert isinstance(signature, bytes)


def test_sign_pss():
    keys = ManufacturerKeys()

    # Create a message to sign
    message = b"This is a test message."

    # Sign the message
    signature = keys.sign_pss(message)

    # Verify the signature using the public key
    pubkey_bytes = keys.get_public_key()
    public_key_obj = serialization.load_pem_public_key(pubkey_bytes)
    try:
        public_key_obj.verify(
            signature,
            message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA512()), salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA512(),
        )
    except Exception as e:
        pytest.fail(f"Signature verification failed: {e}")

    assert isinstance(signature, bytes)


def test_aes_cbc_256_encrypt_decrypt_fail():
    keys = ManufacturerKeys()

    # Define the plaintext to be encrypted
    plaintext = b"This is a test message for AES-256 encryption."
    padded_plaintext = pad_to_multiple_64(plaintext)

    aes_key = gen_aes256_key().data

    # Encrypt using CryptoInterface
    ciphertext, iv = keys.aes_encrypt(padded_plaintext, key=aes_key)

    # Modify the ciphertext to simulate corruption
    corrupted_ciphertext = bytearray(ciphertext)
    corrupted_ciphertext[-1] ^= 0xFF  # Flip the last byte

    # Attempt to decrypt the corrupted ciphertext
    corrupted_decrypted = keys.aes_decrypt(bytes(corrupted_ciphertext), key=aes_key, iv=iv)
    assert corrupted_decrypted != padded_plaintext
