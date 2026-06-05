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
Software-based implementation of manufacturer keys using cryptography library.
"""

import os
import base64

from typing import Tuple, Optional, Union

from cryptography.hazmat.primitives.asymmetric import rsa, ec
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding as asymmetric_padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from tisecprov.crypto_interfaces import (
    CryptoInterface,
    FixedSizeBytes,
    SigningAlgorithm,
)
from tisecprov.cryptoutils import (
    gen_aes256_key,
    load_rsa_private_key,
    validate_key_size,
    generate_rsa_keypair,
    generate_ec_key,
    rsa_decrypt_with_pkcs15_padding,
    rsa_encrypt_with_pkcs15_padding,
)


class ManufacturerKeys(CryptoInterface):
    """
    Software implementation of manufacturer keys using cryptography library.
    """

    _private_key: Union[rsa.RSAPrivateKey, ec.SECP256R1, ec.SECP384R1, ec.SECP521R1, ec.BrainpoolP512R1]
    _symmetric_key: FixedSizeBytes
    _asymmetric_algorithm: SigningAlgorithm
    def __init__(
        self,
        symmetric_key: Optional[bytes] = None,
        private_key: Optional[Union[rsa.RSAPrivateKey, ec.SECP256R1, ec.SECP384R1, ec.SECP521R1, ec.BrainpoolP512R1]] = None,
        asymmetric_algorithm: SigningAlgorithm = None
    ):
        """
        Initialize manufacturer keys with optional symmetric and private keys.

        Args:
            symmetric_key: Optional 32-byte AES key
            private_key_bytes: Optional RSA private key in PEM format
        """
        self._asymmetric_algorithm = SigningAlgorithm.PKCS1_V15 if asymmetric_algorithm is None else asymmetric_algorithm

        # Handle symmetric key
        if symmetric_key is not None:
            self._symmetric_key = FixedSizeBytes(symmetric_key, 32)
        else:
            self._symmetric_key = gen_aes256_key()

        # Handle private key
        if private_key is not None:
            self._private_key = private_key
        else:
            if self._asymmetric_algorithm == SigningAlgorithm.PKCS1_V15:
                self._private_key, _ = generate_rsa_keypair()
            else:
                self._private_key = generate_ec_key(self._asymmetric_algorithm)

        self._validate_key_sizes()

    def _validate_key_sizes(self) -> None:
        """Validate that keys meet size requirements"""
        validate_key_size(self._symmetric_key.data, 32)
        if self._asymmetric_algorithm == SigningAlgorithm.PKCS1_V15 or self._asymmetric_algorithm == SigningAlgorithm.RSA_SSA_PSS:
            if self._private_key.key_size < 4096:
                raise ValueError("RSA key must be at least 4096 bits")        
        elif self._asymmetric_algorithm == SigningAlgorithm.SECP256R1:
            if self._private_key.key_size < 256:
                raise ValueError("SECP256R1 key must be at least 256 bits")
        elif self._asymmetric_algorithm == SigningAlgorithm.SECP384R1:
            if self._private_key.key_size < 384:
                raise ValueError("SECP384R1 key must be at least 384 bits")
        elif self._asymmetric_algorithm == SigningAlgorithm.SECP521R1:
            if self._private_key.key_size < 521:
                raise ValueError("SECP521R1 key must be at least 521 bits")
        elif self._asymmetric_algorithm == SigningAlgorithm.BRAINPOOL512:
            if self._private_key.key_size < 512:
                raise ValueError("BrainpoolP512R1 key must be at least 512 bits")

    def __repr__(self) -> str:
        return f"ManufacturerKeys(symmetric_key={self._symmetric_key})"

    def get_symmetric_key(self) -> bytes:
        """Get the symmetric key bytes"""
        return self._symmetric_key.data

    def generate_aes_key(self) -> bytes:
        """Generate a fresh 32-byte AES-256 key using os.urandom."""
        return gen_aes256_key().data

    def get_public_key(self) -> bytes:
        """Get the public key in PEM format"""
        return self._private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

    def get_public_key_der(self) -> bytes:
        """Get the public key in DER format"""
        return self._private_key.public_key().public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

    def get_signing_key(self):
        """Return (private_key, signing_algorithm) for certificate signing."""
        return self._private_key, self._asymmetric_algorithm

    def export_private_key(self) -> bytes:
        """
        convert the given input bytes into a value of type rsa.RSAPrivateKey
        """
        return self._private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

    def rsa_encrypt_with_pkcs15_padding(self, plaintext: bytes) -> bytes:
        """Encrypt plaintext data using RSA public key with PKCS1 v1.5 padding"""
        pubkey_bytes = self.get_public_key()
        return rsa_encrypt_with_pkcs15_padding(plaintext, pubkey_bytes)

    def rsa_decrypt_with_pkcs15_padding(self, ciphertext: bytes) -> bytes:
        """Decrypt ciphertext data using RSA private key with PKCS1 v1.5 padding"""
        private_key_bytes = self.export_private_key()
        return rsa_decrypt_with_pkcs15_padding(ciphertext, private_key_bytes)

    def sign(
        self,
        message: bytes,
        signing_algorithm: SigningAlgorithm = SigningAlgorithm.PKCS1_V15,
    ) -> bytes:
        """Sign data using PKCS1v1.5 padding and SHA512"""
        ec_arr = [SigningAlgorithm.SECP256R1, SigningAlgorithm.SECP384R1, SigningAlgorithm.SECP521R1, SigningAlgorithm.BRAINPOOL512 ]
        if signing_algorithm is SigningAlgorithm.PKCS1_V15:
            return self._private_key.sign(
                message,
                asymmetric_padding.PKCS1v15(),
                hashes.SHA512(),
            )
        elif signing_algorithm in ec_arr:
            return self._private_key.sign(
                message,
                ec.ECDSA(hashes.SHA512())
            )
        # otherwise do signing with PSS padding
        return self.sign_pss(message)

    def aes_encrypt(self, plaintext: bytes, key: Optional[bytes] = None,
                    iv: Optional[bytes] = None) -> Tuple[bytes, bytes]:
        """Encrypt data using AES-256-CBC"""
        if key is None:
            key = self.get_symmetric_key()
        if iv is None:
            iv = os.urandom(16)

        if len(plaintext) % 16 != 0:
            raise ValueError(
                f"Plaintext length must be a multiple of 16 bytes. "
                f"Current length: {len(plaintext)}"
            )

        cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(plaintext) + encryptor.finalize()
        return ciphertext, iv

    def aes_decrypt(self, ciphertext: bytes, key: Optional[bytes] = None,
                    iv: Optional[bytes] = None) -> bytes:
        """Decrypt data using AES-256-CBC"""
        if key is None:
            key = self.get_symmetric_key()
        if iv is None:
            raise ValueError("IV is required for AES-CBC decryption")

        cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
        decryptor = cipher.decryptor()
        return decryptor.update(ciphertext) + decryptor.finalize()

    def sign_pss(self, message: bytes) -> bytes:
        """Sign data using PSS padding and SHA512"""
        return self._private_key.sign(
            message,
            asymmetric_padding.PSS(
                mgf=asymmetric_padding.MGF1(hashes.SHA512()),
                salt_length=asymmetric_padding.PSS.MAX_LENGTH,
            ),
            hashes.SHA512(),
        )


def derive_key(password: str, salt: Optional[bytes] = None) -> tuple[bytes, bytes]:
    """Derive an encryption key from the low entropy password using PBKDF2."""
    if salt is None:
        salt = os.urandom(16)

    assert len(salt) == 16, "Salt must be 16 bytes long"
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = kdf.derive(password.encode())
    key_base64 = base64.urlsafe_b64encode(key)

    kdf_verify = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    kdf_verify.verify(password.encode(), key)

    return key_base64, salt
