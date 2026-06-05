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
Common cryptographic utility functions and helpers used across the project.
"""

import os
import sys
import base64
from typing import Tuple, Optional, Union

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.asymmetric import rsa, ec, padding as asymmetric_padding
from cryptography.hazmat.primitives.asymmetric.types import PrivateKeyTypes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

from tisecprov.crypto_interfaces import FixedSizeBytes,SigningAlgorithm

def hash_data(data: bytes) -> bytes:
    """
    Hash data using SHA-512.

    Args:
        data: Bytes to hash

    Returns:
        bytes: SHA-512 hash of input data
    """
    digest = hashes.Hash(hashes.SHA512())
    digest.update(data)
    return digest.finalize()


def gen_aes256_key() -> FixedSizeBytes:
    """
    Generate a random 256-bit key suitable for AES-256.

    Returns:
        FixedSizeBytes: A 32-byte random key
    """
    n_bytes = 32  # 256 bits = 32 bytes
    key = os.urandom(n_bytes)
    return FixedSizeBytes(key, n_bytes)


def derive_key(password: str, salt: Optional[bytes] = None) -> Tuple[bytes, bytes]:
    """
    Derive an encryption key from a password using PBKDF2.

    Args:
        password: The password to derive key from
        salt: Optional salt bytes. If None, generates random salt

    Returns:
        Tuple[bytes, bytes]: (derived key in base64, salt used)

    Raises:
        AssertionError: If salt length is not 16 bytes
    """
    if salt is None:
        salt = os.urandom(16)

    assert len(salt) == 16, "Salt must be 16 bytes long"

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,  # 256 bit key
        salt=salt,
        iterations=100000,  # 100k rounds
    )

    key = kdf.derive(password.encode())
    key_base64 = base64.urlsafe_b64encode(key)

    # Verify the key derivation
    kdf_verify = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    kdf_verify.verify(password.encode(), key)

    return key_base64, salt


def load_private_key(
    key_bytes: bytes, password: Optional[bytes] = None
) -> PrivateKeyTypes:
    """
    Load a private key (RSA or EC) from PEM or DER formatted bytes.

    Unlike load_rsa_private_key / load_ec_private_key this does **not**
    type-check the result, so it works for any key type supported by
    the cryptography library.

    Args:
        key_bytes: The key bytes in PEM or DER format
        password: Optional password if key is encrypted

    Returns:
        The loaded private key object

    Raises:
        ValueError: If key format is invalid
    """
    try:
        return serialization.load_pem_private_key(key_bytes, password)
    except ValueError:
        try:
            return serialization.load_der_private_key(key_bytes, password)
        except ValueError as e:
            raise ValueError("Invalid key format - must be PEM or DER") from e


def load_rsa_public_key(key_bytes: bytes) -> rsa.RSAPublicKey:
    """
    Load an RSA public key from PEM or DER formatted bytes.

    Args:
        key_bytes: The key bytes in PEM or DER format

    Returns:
        RSAPublicKey: The loaded public key

    Raises:
        ValueError: If key format is invalid
        TypeError: If key is not an RSA public key
    """
    try:
        key = serialization.load_pem_public_key(key_bytes)
    except ValueError:
        try:
            key = serialization.load_der_public_key(key_bytes)
        except ValueError as e:
            raise ValueError("Invalid key format - must be PEM or DER") from e

    if not isinstance(key, rsa.RSAPublicKey):
        raise TypeError("Key is not an RSA public key")

    return key


def load_rsa_private_key(
    key_bytes: bytes, password: Optional[bytes] = None
) -> rsa.RSAPrivateKey:
    """
    Load an RSA private key from PEM or DER formatted bytes.

    Args:
        key_bytes: The key bytes in PEM or DER format
        password: Optional password if key is encrypted

    Returns:
        RSAPrivateKey: The loaded private key

    Raises:
        ValueError: If key format is invalid
        TypeError: If key is not an RSA private key
    """
    try:
        key = serialization.load_pem_private_key(key_bytes, password)
    except ValueError:
        try:
            key = serialization.load_der_private_key(key_bytes, password)
        except ValueError as e:
            raise ValueError("Invalid key format - must be PEM or DER") from e

    if not isinstance(key, rsa.RSAPrivateKey):
        raise TypeError("Key is not an RSA private key")

    return key


def load_ec_private_key(
    key_bytes: bytes, password: Optional[bytes] = None
) -> ec.EllipticCurvePrivateKey:
    """
    Load an RSA private key from PEM or DER formatted bytes.

    Args:
        key_bytes: The key bytes in PEM or DER format
        password: Optional password if key is encrypted

    Returns:
        EllipticCurvePrivateKey: The loaded private key

    Raises:
        ValueError: If key format is invalid
        TypeError: If key is not an RSA private key
    """
    try:
        key = serialization.load_pem_private_key(key_bytes, password)
    except ValueError:
        try:
            key = serialization.load_der_private_key(key_bytes, password)
        except ValueError as e:
            raise ValueError("Invalid key format - must be PEM or DER") from e

    if not isinstance(key, ec.EllipticCurvePrivateKey):
        raise TypeError("Key is not an EC private key")

    return key


def validate_key_size(data: bytes, expected_size: int) -> None:
    """
    Validate that a key meets the expected size requirement.

    Args:
        data: The key bytes to validate
        expected_size: The expected size in bytes

    Raises:
        ValueError: If key size doesn't match expected size
    """
    if len(data) != expected_size:
        raise ValueError(f"Key must be exactly {expected_size} bytes")


def generate_rsa_keypair(
    key_size: int = 4096,
) -> Tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey]:
    """
    Generate a new RSA keypair.

    Args:
        key_size: The key size in bits (default 4096)

    Returns:
        Tuple[RSAPrivateKey, RSAPublicKey]: The generated private and public keys
    """
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=key_size,
    )
    public_key = private_key.public_key()
    return private_key, public_key

def generate_ec_key(
    key_type: SigningAlgorithm,
) -> ec.EllipticCurvePrivateKey:
    """
    Generate a new EC Private Key.

    Args:
        key_type: The key type

    Returns:
        EllipticCurvePrivateKey: The generated private key
    """
    if key_type == SigningAlgorithm.SECP256R1:
        return ec.generate_private_key(ec.SECP256R1())
    elif key_type == SigningAlgorithm.SECP384R1:
        return ec.generate_private_key(ec.SECP384R1())
    elif key_type == SigningAlgorithm.SECP521R1:
        return ec.generate_private_key(ec.SECP521R1())
    elif key_type == SigningAlgorithm.BRAINPOOL512:
        return ec.generate_private_key(ec.BrainpoolP512R1())
    else:
        print("EC Algorithm not supported")
        sys.exit() 


def rsa_decrypt_with_pkcs15_padding(
    ciphertext: bytes, private_key_bytes: bytes
) -> bytes:
    """
    Decrypt ciphertext data using RSA private key with PKCS1 v1.5 padding

    Args:
        private_key_bytes: PEM formatted bytes that correspond to the private key
    """
    private_key = serialization.load_pem_private_key(private_key_bytes, password=None)

    return private_key.decrypt(ciphertext, asymmetric_padding.PKCS1v15())


def rsa_encrypt_with_pkcs15_padding(plaintext: bytes, pubkey: bytes) -> bytes:
    """
    Encrypt plaintext data using RSA public key with PKCS1 v1.5 padding

    Args:
        plaintext: The bytes that needs to be encrypted
        pubkey: The RSA Pubkey in PEM format as bytes
    Returns:
        encrypted ciphertext as bytes.
    Raises:
        TypeError: If pubkey is not an instance of rsa.RSAPublicKey.
    """
    public_key = serialization.load_pem_public_key(pubkey)
    if not isinstance(public_key, rsa.RSAPublicKey):
        raise TypeError("Provided key is not an RSA Public Key")

    return public_key.encrypt(plaintext, asymmetric_padding.PKCS1v15())


def aes_cbc_256_encrypt(plaintext: bytes, key: bytes = None) -> Tuple[bytes, bytes]:
    """
    Encrypt plaintext data using AES-256 in CBC mode with random IV.
    Plaintext must be a multiple of 16 bytes.

    .. deprecated::
        Use :meth:`tisecprov.crypto_interfaces.CryptoInterface.aes_encrypt` instead.
    """
    import warnings
    warnings.warn(
        "aes_cbc_256_encrypt() is deprecated. "
        "Use CryptoInterface.aes_encrypt() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    if len(plaintext) % 16 != 0:
        raise ValueError(
            f"Plaintext length must be a multiple of 16 bytes. Current length: {len(plaintext)}"
        )

    iv = os.urandom(16)  # AES block_size is 128 bits or 16 bytes.
    cipher = Cipher(algorithms.AES256(key), mode=modes.CBC(iv))
    encryptor = cipher.encryptor()

    try:
        ciphertext = encryptor.update(plaintext) + encryptor.finalize()
    except Exception as e:
        raise ValueError(
            "AES encryption failed. This could be due to an incorrect key size."
        ) from e

    return (ciphertext, iv)


def aes_cbc_256_decrypt(ciphertext: bytes, key: bytes, iv: bytes) -> bytes:
    """
    AES-256 decrypt in CBC mode, the given ciphertext into plaintext
    with the given key and iv.

    Args:
        ciphertext: Encrypted data
        key: AES-256 key
        iv: Initialization vector used for encryption

    Returns:
        bytes: Decrypted data

    Raises:
        RuntimeError: If decryption fails

    .. deprecated::
        Use :meth:`tisecprov.crypto_interfaces.CryptoInterface.aes_decrypt` instead.
    """
    import warnings
    warnings.warn(
        "aes_cbc_256_decrypt() is deprecated. "
        "Use CryptoInterface.aes_decrypt() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    cipher = Cipher(
        algorithms.AES256(key),
        modes.CBC(iv),
        backend=default_backend(),
    )
    decryptor = cipher.decryptor()

    try:
        return decryptor.update(ciphertext) + decryptor.finalize()
    except Exception as e:
        raise RuntimeError("AES decryption failed") from e
