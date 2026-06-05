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
from abc import ABC, abstractmethod
from typing import Tuple, Optional
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.asymmetric import rsa, ec


class SigningAlgorithm(Enum):
    PKCS1_V15 = 0
    RSA_SSA_PSS = 1
    SECP256R1 = 2
    SECP384R1 = 3
    SECP521R1 = 4
    BRAINPOOL512 = 5


def resolve_signing_algorithm(algo_str: str) -> "SigningAlgorithm":
    """Map an algorithm name string to a SigningAlgorithm enum value."""
    mapping = {
        "rsa4k": SigningAlgorithm.PKCS1_V15,
        "secp256r1": SigningAlgorithm.SECP256R1,
        "secp384r1": SigningAlgorithm.SECP384R1,
        "secp521r1": SigningAlgorithm.SECP521R1,
        "brainpool512": SigningAlgorithm.BRAINPOOL512,
    }
    result = mapping.get(algo_str)
    if result is None:
        raise ValueError(f"Unsupported signing algorithm: {algo_str}")
    return result


_EC_CURVE_TO_ALGO = {
    "secp256r1": SigningAlgorithm.SECP256R1,
    "secp384r1": SigningAlgorithm.SECP384R1,
    "secp521r1": SigningAlgorithm.SECP521R1,
    "brainpoolP512r1": SigningAlgorithm.BRAINPOOL512,
}


def infer_signing_algorithm(private_key) -> "SigningAlgorithm":
    """Infer the SigningAlgorithm from a loaded private key object.

    - RSA keys always map to PKCS1_V15 (PSS would require an out-of-band
      indicator that we don't have; all current TI flows use PKCS#1 v1.5).
    - EC keys are mapped by inspecting ``key.curve.name``.

    Raises:
        TypeError: If the key type is not RSA or EC.
        ValueError: If the EC curve is not recognised.
    """
    if isinstance(private_key, rsa.RSAPrivateKey):
        return SigningAlgorithm.PKCS1_V15

    if isinstance(private_key, ec.EllipticCurvePrivateKey):
        curve_name = private_key.curve.name
        algo = _EC_CURVE_TO_ALGO.get(curve_name)
        if algo is None:
            raise ValueError(f"Unsupported EC curve: {curve_name}")
        return algo

    raise TypeError(f"Unsupported private key type: {type(private_key)}")


class CryptoInterface(ABC):
    """Abstract base class defining the interface for cryptographic operations"""

    @abstractmethod
    def get_symmetric_key(self) -> bytes:
        """Get the symmetric key bytes"""
        pass

    @abstractmethod
    def generate_aes_key(self) -> bytes:
        """Generate a fresh 32-byte AES-256 key using the backend's RNG."""
        pass

    @abstractmethod
    def get_public_key(self) -> bytes:
        """Get the public key in PEM format"""
        pass

    @abstractmethod
    def get_public_key_der(self) -> bytes:
        """Get the public key in DER format"""
        pass

    @abstractmethod
    def rsa_encrypt_with_pkcs15_padding(self, plaintext: bytes) -> bytes:
        """Encrypt data using RSA with PKCS1v1.5 padding"""
        pass

    @abstractmethod
    def rsa_decrypt_with_pkcs15_padding(self, ciphertext: bytes) -> bytes:
        """Decrypt data using RSA with PKCS1v1.5 padding"""
        pass

    @abstractmethod
    def sign(self, message: bytes, signing_algorithm: SigningAlgorithm) -> bytes:
        """Sign Data after hashing with SHA512"""
        pass

    def hash_pubkey(self) -> bytes:
        """Hash the public key using SHA-512 - concrete implementation"""
        return self.hash_data(self.get_public_key_der())

    @staticmethod
    def hash_data(data: bytes) -> bytes:
        """Static helper method to hash data using SHA-512"""
        digest = hashes.Hash(hashes.SHA512())
        digest.update(data)
        return digest.finalize()

    @abstractmethod
    def aes_encrypt(self, plaintext: bytes, key: Optional[bytes] = None,
                    iv: Optional[bytes] = None) -> Tuple[bytes, bytes]:
        """
        Encrypt data using AES-256-CBC.

        Args:
            plaintext: Data to encrypt, must be block-aligned (multiple of 16 bytes)
            key: AES-256 key. If None, uses self.get_symmetric_key()
            iv: Initialization vector. If None, generates random 16-byte IV

        Returns:
            Tuple of (ciphertext, iv)
        """
        pass

    @abstractmethod
    def aes_decrypt(self, ciphertext: bytes, key: Optional[bytes] = None,
                    iv: Optional[bytes] = None) -> bytes:
        """
        Decrypt data using AES-256-CBC.

        Args:
            ciphertext: Encrypted data
            key: AES-256 key. If None, uses self.get_symmetric_key()
            iv: Initialization vector used during encryption

        Returns:
            Decrypted plaintext bytes
        """
        pass

    def derive_key_hkdf(self, salt: bytes, length: int = 32,
                        info: bytes = b"") -> bytes:
        """
        Derive a key using HKDF-SHA512 from the symmetric key.

        Uses self.get_symmetric_key() as the input key material (IKM).
        Subclasses can override for hardware-accelerated HKDF.

        Args:
            salt: Salt for HKDF extraction
            length: Desired output key length in bytes
            info: Optional context/application-specific info

        Returns:
            Derived key bytes of the requested length
        """
        hkdf = HKDF(
            algorithm=hashes.SHA512(),
            length=length,
            salt=salt if salt else None,
            info=info,
        )
        return hkdf.derive(self.get_symmetric_key())

    def verify_key_size(self, data: bytes, expected_size: int) -> None:
        """Helper method to verify key sizes"""
        if len(data) != expected_size:
            raise ValueError(f"Data must be exactly {expected_size} bytes")


class FixedSizeBytes:
    """A wrapper around bytes that enforces a fixed size"""

    def __init__(self, data: bytes, size: int):
        if len(data) != size:
            raise ValueError(f"data must be exactly {size} bytes")
        self.data = data

    def __repr__(self):
        preview = f"{self.data[:2]}...{self.data[-2:]}"
        return f"FixedSizeBytes({preview})"
