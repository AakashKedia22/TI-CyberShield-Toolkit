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

import pkcs11
import os
import json

from typing import Tuple, Optional
from pathlib import Path
from pkcs11 import KeyType, ObjectClass, Mechanism
from pkcs11.util.rsa import encode_rsa_public_key

from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes

from tisecprov.crypto_interfaces import (
    CryptoInterface,
    FixedSizeBytes,
    SigningAlgorithm,
)
from tisecprov.cryptoutils import (
    load_rsa_public_key,
)


class HSMManufacturerKeys(CryptoInterface):
    def __init__(self, session, label, wrapped_symmetric_key: Optional[bytes] = None):
        self.label = label
        self.hsm_session = session.hsm_session

        # Generate or get existing keypair
        try:
            # Check if keys already exist
            self.pub_key = self.hsm_session.get_key(
                key_type=KeyType.RSA,
                object_class=ObjectClass.PUBLIC_KEY,
                label=label,
            )
            print(f"key {label} exists")
        except pkcs11.exceptions.NoSuchKey as e:
            # Generate keys if they don't exist
            print("Generating Keys")
            self.hsm_session.generate_keypair(
                KeyType.RSA,
                4096,
                store=True,
                label=label,
                id=self.hsm_session.generate_random(192),
            )
            print(label)

        self.pub_key = self.hsm_session.get_key(
            key_type=KeyType.RSA,
            object_class=ObjectClass.PUBLIC_KEY,
            label=label,
        )

        private_key = self.hsm_session.get_key(
            key_type=KeyType.RSA,
            object_class=ObjectClass.PRIVATE_KEY,
            label=label,
        )

        # unfortunately, pkcs11 private key type does not have a way
        # to derive pubkey from it, so we have to get the generated
        # key (generated via the generate_keypair() above) and store
        # it in the HSMRSAPrivateKey object.
        self.priv_key = HSMRSAPrivateKey(private_key, self.pub_key)

        # Set MEK:
        #   - wrapped_symmetric_key: RSA-wrapped blob stored in session, unwrap via HSM C_Decrypt
        #   - else: generate fresh random MEK (key generation path)
        # Note: SmartCard-HSM cannot extract CKA_VALUE from generated AES keys,
        # so generate_random() is used to produce raw bytes for software AES.
        if wrapped_symmetric_key is not None:
            self._symmetric_key = bytes(private_key.decrypt(wrapped_symmetric_key, mechanism=Mechanism.RSA_PKCS))
        else:
            self._symmetric_key = bytes(self.hsm_session.generate_random(256))

        # Convert PKCS#11 public key to cryptography format for some operations
        pub_key_der = encode_rsa_public_key(self.pub_key)
        self._crypto_pub_key = serialization.load_der_public_key(pub_key_der)

    def __repr__(self):
        return f"HSMManufacturerKeys(label={self.label})"

    def get_signing_key(self):
        """Return (private_key, signing_algorithm) for certificate signing."""
        from tisecprov.crypto_interfaces import SigningAlgorithm
        return self.priv_key, SigningAlgorithm.PKCS1_V15

    @property
    def _private_key(self):
        """Expose priv_key as _private_key for certgen.py compatibility."""
        return self.priv_key

    def get_symmetric_key(self) -> bytes:
        return self._symmetric_key

    def generate_aes_key(self) -> bytes:
        """Generate a fresh 32-byte AES-256 key using the HSM hardware RNG."""
        return bytes(self.hsm_session.generate_random(256))

    def get_public_key(self) -> bytes:
        return self._crypto_pub_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

    def get_private_key(self) -> RSAPrivateKey:
        return self.priv_key

    def export_private_key(self) -> bytes:
        raise NotImplementedError(
            "HSM private keys cannot be exported. Key material stays on the HSM."
        )

    def get_public_key_der(self) -> bytes:
        return self._crypto_pub_key.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

    def rsa_encrypt_with_pkcs15_padding(self, plaintext: bytes) -> bytes:
        return self._crypto_pub_key.encrypt(plaintext, padding.PKCS1v15())

    def rsa_decrypt_with_pkcs15_padding(self, ciphertext: bytes) -> bytes:
        return self.priv_key.decrypt(ciphertext)

    def wrap_mek(self) -> bytes:
        """RSA-encrypt the MEK with this key's PKCS#11 public key (C_Encrypt, PKCS#1 v1.5).

        Returns a 512-byte ciphertext that can only be decrypted by the HSM
        private key, providing an extra layer of protection beyond the Fernet
        session encryption when the blob is stored on disk.
        """
        return bytes(self.pub_key.encrypt(self._symmetric_key, mechanism=Mechanism.RSA_PKCS))

    def sign(
        self,
        message: bytes,
        signing_algorithm: SigningAlgorithm = SigningAlgorithm.PKCS1_V15,
    ):
        assert isinstance(signing_algorithm, SigningAlgorithm) is True
        if signing_algorithm is SigningAlgorithm.PKCS1_V15:
            return self.sign_pkcs1v15(message)

        return self.sign_pss(message)

    def sign_pkcs1v15(self, message: bytes) -> bytes:
        """Sign using PKCS1v1.5 after SHA512 hashing"""
        # First create SHA-512 digest
        # TODO Use the HSM to do the Hashing
        digest = hashes.Hash(hashes.SHA512())
        digest.update(message)
        message_digest = digest.finalize()

        # Sign the digest using RSA PKCS
        return self.priv_key.sign(
            message_digest,
            padding.PKCS1v15(),
            None,
        )

    def sign_pss(self, message: bytes) -> bytes:
        """Sign using PSS padding and SHA512"""
        # Note: Using SHA512_RSA_PSS mechanism which combines hashing and signing
        return self.priv_key.sign(
            message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA512()),
                salt_length=padding.PSS.MAX_LENGTH,
            ),
            None,
        )

    def aes_encrypt(self, plaintext: bytes, key: Optional[bytes] = None,
                    iv: Optional[bytes] = None) -> Tuple[bytes, bytes]:
        """Encrypt data using AES-256-CBC (software).
        SmartCard-HSM does not support importing AES session keys via PKCS#11."""
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        if key is None:
            key = self._symmetric_key
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
        """Decrypt data using AES-256-CBC (software).
        SmartCard-HSM does not support importing AES session keys via PKCS#11."""
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        if key is None:
            key = self._symmetric_key
        if iv is None:
            raise ValueError("IV is required for AES-CBC decryption")

        cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
        decryptor = cipher.decryptor()
        return decryptor.update(ciphertext) + decryptor.finalize()

    def aes_cbc_256_encrypt(
        self, plaintext: bytes, key: FixedSizeBytes = None
    ) -> Tuple[bytes, bytes]:
        """Encrypt data using AES-CBC.

        .. deprecated::
            Use :meth:`aes_encrypt` instead.
        """
        import warnings
        warnings.warn(
            "aes_cbc_256_encrypt() is deprecated, use aes_encrypt() instead",
            DeprecationWarning,
            stacklevel=2,
        )
        # Legacy behavior: adds PKCS padding and returns (iv, ciphertext)
        block_size = 16
        padding_length = block_size - (len(plaintext) % block_size)
        padding = bytes([padding_length] * padding_length)
        padded_data = plaintext + padding

        iv = os.urandom(16)

        encrypted_data = key.encrypt(
            padded_data,
            mechanism=Mechanism.AES_CBC,
            mechanism_param=iv,
        )
        return iv, encrypted_data

    def aes_cbc_256_decrypt(self, ciphertext: bytes, iv: bytes) -> bytes:
        """Decrypt data using AES-CBC.

        .. deprecated::
            Use :meth:`aes_decrypt` instead.
        """
        import warnings
        warnings.warn(
            "aes_cbc_256_decrypt() is deprecated, use aes_decrypt() instead",
            DeprecationWarning,
            stacklevel=2,
        )
        try:
            aes_key = self.hsm_session.create_object(
                {
                    pkcs11.Attribute.CLASS: pkcs11.ObjectClass.SECRET_KEY,
                    pkcs11.Attribute.KEY_TYPE: pkcs11.KeyType.AES,
                    pkcs11.Attribute.VALUE: self._aes_key.data,
                }
            )
            plaintext = aes_key.decrypt(
                ciphertext, mechanism=Mechanism.AES_CBC, mechanism_param=iv
            )
            aes_key.destroy()
            return plaintext
        except Exception as e:
            raise RuntimeError("AES decryption failed.") from e


# Helper function
def generate_aes_key(session) -> bytes:
    """Generate a 32-byte AES-256 key using the HSM hardware RNG."""
    return bytes(session.generate_random(256))


def hash_data(data: bytes) -> bytes:
    """Hash data using SHA-512"""
    digest = hashes.Hash(hashes.SHA512())
    digest.update(data)
    return digest.finalize()


def get_pkcs11_lib() -> pkcs11.lib:
    libname = os.getenv("PKCS11_LIB", default="/usr/local/lib/libsc-hsm-pkcs11.so")
    libpath = Path(libname)
    if not libpath.exists():
        raise RuntimeError("pkcs11 HSM driver module cannot be found")

    return pkcs11.lib(libname)


# SHA-512 DigestInfo prefix per RFC 8017 §9.2 / RFC 3447
# SEQUENCE { SEQUENCE { OID sha-512, NULL }, OCTET STRING(64) }
_SHA512_DIGESTINFO_PREFIX = bytes([
    0x30, 0x51,              # SEQUENCE, length 81
    0x30, 0x0d,              # SEQUENCE (AlgorithmIdentifier), length 13
    0x06, 0x09,              # OID, length 9
    0x60, 0x86, 0x48, 0x01, 0x65, 0x03, 0x04, 0x02, 0x03,  # OID 2.16.840.1.101.3.4.2.3
    0x05, 0x00,              # NULL
    0x04, 0x40,              # OCTET STRING, length 64
])


class HSMRSAPrivateKey(RSAPrivateKey):
    def __init__(self, pkcs11_privkey, pkcs11_pubkey):
        self._key = pkcs11_privkey
        self._pubkey = pkcs11_pubkey
        self._key_size = pkcs11_privkey.key_length

    @property
    def key_size(self) -> int:
        return self._key_size

    def sign(self, data: bytes, padding_scheme, algorithm):
        """
        sign without hashing. It is assumed that hashing is done elsewhere.

        Args:
            data: data to be signed
            padding: which padding algorithm to use.
            algorithm: hashing algorithm to use.
        """
        if isinstance(padding_scheme, padding.PKCS1v15):
            # only sign, hashing is done outside as
            # mechanism=SHA512_RSA_PKCS gives an InvalidMechanism
            # error.
            print("signing with PKCS#1v1.5 padding")
            # When algorithm is provided (e.g. from x509 builder), hash data first.
            # When algorithm is None (e.g. from sign_pkcs1v15), data is already a digest.
            if algorithm is not None:
                digest = hashes.Hash(hashes.SHA512())
                digest.update(data)
                data = digest.finalize()
            # Wrap hash in DigestInfo (required by PKCS#1 v1.5; CKM_SHA512_RSA_PKCS not supported by HSM)
            return bytes(self._key.sign(
                _SHA512_DIGESTINFO_PREFIX + data, mechanism=Mechanism.RSA_PKCS
            ))
        elif isinstance(padding_scheme, padding.PSS):
            # for some reason signing with pss does hash + signing
            print("signing with PSS padding")

            # First hash the data with SHA512
            digest = hashes.Hash(hashes.SHA512())
            digest.update(data)
            message_digest = digest.finalize()

            return self._key.sign(
                message_digest,
                mechanism=Mechanism.RSA_PKCS_PSS,
                mechanism_param=(Mechanism.SHA512, pkcs11.MGF.SHA512, 64),
            )
        else:
            raise RuntimeError("unknown padding mechanism")

    def decrypt(self, ciphertext, padding=None):
        return self._key.decrypt(ciphertext, mechanism=Mechanism.RSA_PKCS)

    def public_key(self):
        # Get the public key components from the HSM
        public_key_der = encode_rsa_public_key(self._pubkey)
        return load_rsa_public_key(public_key_der)

    # Required abstract method implementations
    def private_numbers(self):
        raise NotImplementedError("Private numbers not available for HSM keys")

    def private_bytes(self, encoding, format, encryption_algorithm):
        raise NotImplementedError("Private bytes not available for HSM keys")
    
    def __copy__(self):
        # Since this is dealing with HSM keys, we probably want to return the same instance
        # rather than creating a true copy, since the actual key material lives in the HSM
        return self