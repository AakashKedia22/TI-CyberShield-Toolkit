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
X509 certificate generation module
"""

import os
import datetime

from enum import Enum
from typing import List, Dict, Optional, Tuple, Union

from asn1crypto.core import Sequence, Integer, OctetString, ObjectIdentifier
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives.asymmetric import rsa, ec

from tisecprov.crypto import ManufacturerKeys
from tisecprov.cryptoutils import (
    load_rsa_private_key,
    rsa_encrypt_with_pkcs15_padding,
    hash_data,
)
from tisecprov.crypto_interfaces import SigningAlgorithm
from tisecprov.device_config import (
    CertificateRequest,
    DeviceConfig,
    ExtendedOTPData,
    FieldFlags,
    OIDEntry,
    SecondaryCertFormat,
)


# https://downloads.ti.com/tisci/esd/latest/2_tisci_msgs/security/sec_cert_format.html#keywriter-encrypted-aes-extension
class KeywriterSequence(Sequence):
    # pylint: disable=missing-class-docstring
    _fields = [
        ("val", OctetString),
        ("size", Integer),
    ]


def asn1_enc_aes_key(val: bytes) -> bytes:
    """
    ASN.1 DER encoding of the AES encryption key
    """
    aes_enc_key = KeywriterSequence({"val": val, "size": len(val)})
    return aes_enc_key.dump()


# https://downloads.ti.com/tisci/esd/latest/2_tisci_msgs/security/sec_cert_format.html#keywriter-encrypted-smpk-signed-aes-extension
def asn1_mpk_signed_aes_key(val: bytes) -> bytes:
    """
    ASN.1 encoding of the TIFEK(pub) encrypted, MPK(priv) signed AES encryption key
    """
    mpk_signed_aes_key = KeywriterSequence({"val": val, "size": len(val)})
    return mpk_signed_aes_key.dump()


# https://downloads.ti.com/tisci/esd/latest/2_tisci_msgs/security/sec_cert_format.html#keywriter-aes-encrypted-smpkh
class KeywriterSequence2(Sequence):
    # pylint: disable=missing-class-docstring
    _fields = [
        ("val", OctetString),
        ("iv", OctetString),
        ("rs", OctetString),
        ("size", Integer),
        ("action_flags", Integer),
    ]


def flag_byte(flag: bool) -> bytes:
    """
    encoding of flag value in OTP area as byte
    """
    return b"\x5a" if flag else b"\xa5"


# pylint: disable=too-many-arguments. too-many-positional-arguments
def asn1_aes_enc_mpkh(
    val: bytes,
    iv: bytes,
    rs: bytes,
    write_protect: bool = False,
    read_protect: bool = False,
    override: bool = False,
    active: bool = False,
) -> bytes:
    """
    ASN.1 encoding of the AES-256 key encrypted SMPKH (SHA-512 hashed MPK Public key).

    Args:
        val: Encrypted SMPK or BMPK Hash data. (64 bytes SHA512 output + 32 bytes rs)
        iv: 16 bytes
        rs: 32 bytes
        write_protect: Write protect flag
        read_protect: Read protect flag
        override: Override flag
        active: Active flag

    Returns:
        ASN.1 encoded data

    Raises:
        ValueError: If input sizes are invalid
    """

    if len(iv) != 16:
        raise ValueError("IV must be 16 bytes")

    if len(rs) != 32:
        raise ValueError("random string must be 32 bytes")

    # val is the output of SHA256, which is 8 x 64bit words = 8x8=64 bytes.
    if not isinstance(val, bytes):
        raise ValueError("val must be of type bytes")

    if len(val) != 96:
        raise ValueError(f"val must be 64 bytes, got {len(val)} bytes")

    flag = (
        flag_byte(write_protect)
        + flag_byte(read_protect)
        + flag_byte(override)
        + flag_byte(active)
    )

    aes_enc_mpkh = KeywriterSequence2(
        {
            "val": val,
            "iv": iv,
            "rs": rs,
            "size": len(val),
            "action_flags": int.from_bytes(flag, byteorder="big"),
        }
    )

    return aes_enc_mpkh.dump()


# https://downloads.ti.com/tisci/esd/latest/2_tisci_msgs/security/sec_cert_format.html#keywriter-aes-encrypted-smek
def asn1_aes_enc_mek(
    val: bytes,
    iv: bytes,
    rs: bytes,
    write_protect: bool = False,
    read_protect: bool = False,
    override: bool = False,
    active: bool = False,
) -> bytes:
    """
    ASN.1 encoding of the AES-256 key encrypted MEK (symmetric key)
    """

    flag = (
        flag_byte(write_protect)
        + flag_byte(read_protect)
        + flag_byte(override)
        + flag_byte(active)
    )
    aes_enc_mek = KeywriterSequence2(
        {
            "val": val,
            "iv": iv,
            "rs": rs,
            "size": len(val),
            "action_flags": int.from_bytes(flag, byteorder="big"),
        }
    )
    return aes_enc_mek.dump()


# extended OTP: https://downloads.ti.com/tisci/esd/latest/2_tisci_msgs/security/sec_cert_format.html#keywriter-aes-encrypted-extended-otp # pylint: disable=line-too-long
class KeywriterSequence3(Sequence):
    # pylint: disable=missing-class-docstring
    _fields = [
        ("val", OctetString),
        ("iv", OctetString),
        ("rs", OctetString),
        (
            "wprp",
            OctetString,
        ),  # write protect(64 bits) || read protect (64 bits) for a row.
        ("index", Integer),
        ("size", Integer),
        ("action_flags", Integer),
    ]


def asn1_aes_enc_extotp(
    val: bytes,
    iv: bytes,
    rs: bytes,
    wprp: bytes,
    index: int,
    size: int,
    write_protect: bool = False,
    read_protect: bool = False,
    override: bool = False,
    active: bool = False,
) -> bytes:
    """
    ASN.1 encoding of the AES-256 key encrypted extended OTP
    """

    flag = (
        flag_byte(write_protect)
        + flag_byte(read_protect)
        + flag_byte(override)
        + flag_byte(active)
    )
    aes_enc_extotp = KeywriterSequence3(
        {
            "val": val,
            "iv": iv,
            "rs": rs,
            "wprp": wprp,
            "index": index,
            "size": size,
            "action_flags": int.from_bytes(flag, byteorder="big"),
        }
    )

    return aes_enc_extotp.dump()


class KeywriterSequence4(Sequence):
    # pylint: disable=missing-class-docstring
    _fields = [
        ("val", OctetString),
        ("action_flags", Integer),
    ]


# key rev. https://software-dl.ti.com/tisci/esd/latest/2_tisci_msgs/security/sec_cert_format.html#keywriter-key-revision # pylint: disable=line-too-long
def asn1_plain_key_rev(
    revision: int,
    write_protect: bool = False,
    read_protect: bool = False,
    override: bool = False,
    active: bool = False,
) -> bytes:
    """
    ASN.1 encoding of the plain key revision
    """
    if revision <= 0 or revision > 3:
        raise ValueError("Key revision must be between 1 and 2")

    if revision == 2 or revision == 3:
        val = 3
    else:
        val = revision

    flag = (
        flag_byte(write_protect)
        + flag_byte(read_protect)
        + flag_byte(override)
        + flag_byte(active)
    )

    plain_key_rev = KeywriterSequence4(
        {
            "val": val.to_bytes(4, byteorder="big"),  # key rev is 32 bits
            "action_flags": int.from_bytes(flag, byteorder="big"),
        }
    )

    return plain_key_rev.dump()


# https://downloads.ti.com/tisci/esd/latest/2_tisci_msgs/security/sec_cert_format.html#keywriter-msv
def asn1_plain_msv(
    msv: bytes,
    write_protect: bool = False,
    read_protect: bool = False,
    override: bool = False,
    active: bool = False,
) -> bytes:
    """
    ASN.1 encoding of the plain manufacturer specific value
    """

    flag = (
        flag_byte(write_protect)
        + flag_byte(read_protect)
        + flag_byte(override)
        + flag_byte(active)
    )

    plain_msv = KeywriterSequence4(
        {
            "val": msv.rjust(4, b"\x00"),
            "action_flags": int.from_bytes(flag, byteorder="big"),
        }
    )

    return plain_msv.dump()


# https://software-dl.ti.com/tisci/esd/latest/2_tisci_msgs/security/sec_cert_format.html#keywr-mpk-opt
def asn1_plain_mpk_options(
    options: bytes,
    write_protect: bool = False,
    read_protect: bool = False,
    override: bool = False,
    active: bool = False,
) -> bytes:
    """
    ASN.1 encoding of the plain mpk options
    """

    flag = (
        flag_byte(write_protect)
        + flag_byte(read_protect)
        + flag_byte(override)
        + flag_byte(active)
    )

    plain_mpk_options = KeywriterSequence4(
        {
            "val": options,
            "action_flags": int.from_bytes(flag, byteorder="big"),
        }
    )

    return plain_mpk_options.dump()


# https://software-dl.ti.com/tisci/esd/latest/2_tisci_msgs/security/sec_cert_format.html#keywriter-mek-options
def asn1_plain_mek_options(
    options: bytes,
    write_protect: bool = False,
    read_protect: bool = False,
    override: bool = False,
    active: bool = False,
) -> bytes:
    """
    ASN.1 encoding of the plain mek options
    """

    flag = (
        flag_byte(write_protect)
        + flag_byte(read_protect)
        + flag_byte(override)
        + flag_byte(active)
    )

    plain_mek_options = KeywriterSequence4(
        {
            "val": options,
            "action_flags": int.from_bytes(flag, byteorder="big"),
        }
    )

    return plain_mek_options.dump()


# https://downloads.ti.com/tisci/esd/latest/2_tisci_msgs/security/sec_cert_format.html#keywriter-key-count
def asn1_plain_key_count(
    count: int,
    write_protect: bool = False,
    read_protect: bool = False,
    override: bool = False,
    active: bool = False,
) -> bytes:
    """
    ASN.1 encoding of the plain key count
    """

    flag = (
        flag_byte(write_protect)
        + flag_byte(read_protect)
        + flag_byte(override)
        + flag_byte(active)
    )

    plain_key_count = KeywriterSequence4(
        {
            "val": count.to_bytes(4, byteorder="big"),  # key count is 32 bits
            "action_flags": int.from_bytes(flag, byteorder="big"),
        }
    )

    return plain_key_count.dump()


# sysfw swrev: https://downloads.ti.com/tisci/esd/latest/2_tisci_msgs/security/sec_cert_format.html#keywriter-software-revision-sysfw # pylint: disable=line-too-long
def asn1_plain_swrev_sysfw(
    swrev: bytes,
    write_protect: bool = False,
    read_protect: bool = False,
    override: bool = False,
    active: bool = False,
) -> bytes:
    """
    ASN.1 encoding of the plain sysfw swrev
    """

    flag = (
        flag_byte(write_protect)
        + flag_byte(read_protect)
        + flag_byte(override)
        + flag_byte(active)
    )

    plain_swrev_sysfw = KeywriterSequence4(
        {
            "val": swrev.rjust(4, b"\x00"),
            "action_flags": int.from_bytes(flag, byteorder="big"),
        }
    )

    return plain_swrev_sysfw.dump()


# sbl swrev: https://downloads.ti.com/tisci/esd/latest/2_tisci_msgs/security/sec_cert_format.html#keywriter-software-revision-sbl # pylint: disable=line-too-long
def asn1_plain_swrev_sbl(
    swrev: bytes,
    write_protect: bool = False,
    read_protect: bool = False,
    override: bool = False,
    active: bool = False,
) -> bytes:
    """
    ASN.1 encoding of the plain sbl swrev
    """

    flag = (
        flag_byte(write_protect)
        + flag_byte(read_protect)
        + flag_byte(override)
        + flag_byte(active)
    )

    plain_swrev_sbl = KeywriterSequence4(
        {
            "val": swrev.rjust(4, b"\x00"),
            "action_flags": int.from_bytes(flag, byteorder="big"),
        }
    )

    return plain_swrev_sbl.dump()


# boardcfg swrev: https://downloads.ti.com/tisci/esd/latest/2_tisci_msgs/security/sec_cert_format.html#keywriter-software-revision-sec-boardconfig # pylint: disable=line-too-long
def asn1_plain_swrev_boardcfg(
    swrev: bytes,
    write_protect: bool = False,
    read_protect: bool = False,
    override: bool = False,
    active: bool = False,
) -> bytes:
    """
    ASN.1 encoding of the plain boardcfg swrev
    """

    flag = (
        flag_byte(write_protect)
        + flag_byte(read_protect)
        + flag_byte(override)
        + flag_byte(active)
    )

    plain_swrev_boardcfg = KeywriterSequence4(
        {
            "val": swrev.rjust(4, b"\x00"),
            "action_flags": int.from_bytes(flag, byteorder="big"),
        }
    )

    return plain_swrev_boardcfg.dump()

def asn1_plain_swrev_ssu(
    swrev: bytes,
    write_protect: bool = False,
    read_protect: bool = False,
    override: bool = False,
    active: bool = False,
) -> bytes:
    """
    ASN.1 encoding of the plain ssu swrev
    """

    flag = (
        flag_byte(write_protect)
        + flag_byte(read_protect)
        + flag_byte(override)
        + flag_byte(active)
    )

    plain_ssu_sbl = KeywriterSequence4(
        {
            "val": swrev.rjust(8, b"\x00"),
            "action_flags": int.from_bytes(flag, byteorder="big"),
        }
    )

    return plain_ssu_sbl.dump()

def asn1_jtag_disable(
    write_protect: bool = False,
    read_protect: bool = False,
    override: bool = False,
    active: bool = False,
) -> bytes:

    flag = (
        flag_byte(write_protect)
        + flag_byte(read_protect)
        + flag_byte(override)
        + flag_byte(active)
    )
    jtag_val = KeywriterSequence4(
        {
            "val": b"\x00\x00\x00\x00",
            "action_flags": int.from_bytes(flag, byteorder="big"),
        }
    )

    return jtag_val.dump()


class KeywriterSequence5(Sequence):
    # pylint: disable=missing-class-docstring
    _fields = [
        ("val", OctetString),
    ]


# min keywriter version: https://downloads.ti.com/tisci/esd/latest/2_tisci_msgs/security/sec_cert_format.html#keywriter-version # pylint: disable=line-too-long
def asn1_plain_keywriter_min_version(version: bytes) -> bytes:
    """
    ASN.1 encoding of the plain keywriter min version
    """
    plain_keywriter_min_version = KeywriterSequence5(
        {
            "val": version.rjust(4, b"\x00"),
        }
    )

    return plain_keywriter_min_version.dump()


# ---------------------------------------------------------------------------
# Helper: extract slot-specific field names from OID map
# ---------------------------------------------------------------------------

def _get_slot_field_names(oids: List[OIDEntry]) -> Dict[str, str]:
    """Extract field names for device-specific OID slots (78, 79, 80, 82)."""
    result = {}
    for entry in oids:
        suffix = entry.oid.split(".")[-1]
        if suffix in ("78", "79", "80", "82"):
            result[suffix] = entry.field_name
    return result


# ---------------------------------------------------------------------------
# Unified generate_encrypted_fields
# ---------------------------------------------------------------------------

# pylint: disable=too-many-locals, too-many-statements, too-many-branches
def generate_encrypted_fields(request: CertificateRequest) -> Dict[str, bytes]:
    """
    Generate the encrypted fields that will be embedded in the certificate.

    Uses the CertificateRequest to drive all device-specific behaviour
    (field names, per-key signing algorithms, ECC padding, per-field flags).
    """
    config = request.device_config
    mkeys = request.mkeys
    aes_key = request.aes_key
    pubkey = request.tifek_pub
    per_key_algos = request.per_key_signing_algorithms
    pad_ecc = config.pad_ecc_signatures

    result: Dict[str, bytes] = {}

    assert len(mkeys) != 0
    assert len(mkeys) <= 2

    # 1. Encrypt AES key with TIFEK Pub
    encrypted_aes_key = rsa_encrypt_with_pkcs15_padding(aes_key, pubkey)
    result["enc_aes_key"] = asn1_enc_aes_key(encrypted_aes_key)

    # 2. For each manufacturer key pair, generate encrypted fields
    for count, mkey in enumerate(mkeys):
        signing_algo = per_key_algos[count] if count < len(per_key_algos) else per_key_algos[0]

        # --- sign AES key with MPK-priv ---
        print(f"signing AES key with {signing_algo}")
        aes_signed_with_mpk = mkey.sign(aes_key, signing_algo)

        # Pad ECC signatures to 512 bytes if required
        if pad_ecc and len(aes_signed_with_mpk) < 512:
            aes_signed_with_mpk += b"\x00" * (512 - len(aes_signed_with_mpk))
        assert len(aes_signed_with_mpk) == 512

        # Split signed AES key into two 256-byte halves, encrypt each with TIFEK pub
        p1 = aes_signed_with_mpk[:256]
        p2 = aes_signed_with_mpk[256:]
        p1_enc = rsa_encrypt_with_pkcs15_padding(p1, pubkey)
        p2_enc = rsa_encrypt_with_pkcs15_padding(p2, pubkey)
        aes_signed_enc_combined = p1_enc + p2_enc
        assert len(aes_signed_enc_combined) == 1024

        if count == 0:
            result["enc_smpk_signed_aes_key"] = asn1_mpk_signed_aes_key(aes_signed_enc_combined)
        elif count == 1:
            result["enc_bmpk_signed_aes_key"] = asn1_mpk_signed_aes_key(aes_signed_enc_combined)
        else:
            raise ValueError("Too many keys provided")

        # --- hash MPK-pub, encrypt with AES ---
        mpk_pub_hash = mkey.hash_pubkey()
        assert len(mpk_pub_hash) == 64
        rs1 = os.urandom(32)
        mpk_pub_hash_with_rs = mpk_pub_hash + rs1
        assert len(mpk_pub_hash_with_rs) % 16 == 0
        encrypted_mpk_pub_hash, iv1 = mkey.aes_encrypt(mpk_pub_hash_with_rs, key=aes_key)

        # Determine flags for this key's public-key hash
        if count == 0:
            key_flags = request.smpk_flags
        else:
            key_flags = request.bmpk_flags if request.bmpk_flags is not None else FieldFlags()

        if count == 0:
            result["aesenc_smpkh"] = asn1_aes_enc_mpkh(
                encrypted_mpk_pub_hash, iv1, rs1, *key_flags.as_tuple()
            )
        elif count == 1:
            result["aesenc_bmpkh"] = asn1_aes_enc_mpkh(
                encrypted_mpk_pub_hash, iv1, rs1, *key_flags.as_tuple()
            )

        # --- encrypt MEK (symmetric key) with AES ---
        should_include_mek = (count == 0 and request.include_smek) or (
            count == 1 and request.include_bmek
        )
        if should_include_mek:
            rs2 = os.urandom(32)
            mek = mkey.get_symmetric_key()
            mek_with_rs = mek + rs2
            encrypted_mek, iv2 = mkey.aes_encrypt(mek_with_rs, key=aes_key)

            if count == 0:
                mek_flags = request.smek_flags
            else:
                mek_flags = request.bmek_flags if request.bmek_flags is not None else FieldFlags()

            if count == 0:
                result["aesenc_smek"] = asn1_aes_enc_mek(
                    encrypted_mek, iv2, rs2, *mek_flags.as_tuple()
                )
            elif count == 1:
                result["aesenc_bmek"] = asn1_aes_enc_mek(
                    encrypted_mek, iv2, rs2, *mek_flags.as_tuple()
                )

    # 3. Extended OTP
    if request.ext_otp is not None:
        otp = request.ext_otp
        result["aesenc_user_otp"] = asn1_aes_enc_extotp(
            otp.data, otp.iv, otp.rs, otp.wprp,
            otp.index, otp.size, *otp.flags.as_tuple(),
        )
    else:
        result["aesenc_user_otp"] = asn1_aes_enc_extotp(
            b"\x00" * 128, b"\x00" * 16, b"\x00" * 32, b"\x00" * 16,
            0, 0, False, False, False, False,
        )

    # 4. Plaintext fields
    result["plain_key_rev"] = asn1_plain_key_rev(
        request.key_rev, *request.key_rev_flags.as_tuple()
    )
    result["plain_key_cnt"] = asn1_plain_key_count(
        request.key_cnt, *request.key_cnt_flags.as_tuple()
    )

    # SWREV fields — use field names from device config OID map
    slot_names = _get_slot_field_names(config.primary_oids)

    # Slot 78 (sysfw / hsmRT)
    field_78 = slot_names.get("78", "plain_swrev_sysfw")
    result[field_78] = asn1_plain_swrev_sysfw(
        request.swrev_slot78, *request.swrev_slot78_flags.as_tuple()
    )

    # Slot 79 (sbl)
    result["plain_swrev_sbl"] = asn1_plain_swrev_sbl(
        request.swrev_slot79, *request.swrev_slot79_flags.as_tuple()
    )

    # Slot 80 (sec_brdcfg / sec_app)
    field_80 = slot_names.get("80", "plain_swrev_sec_brdcfg")
    result[field_80] = asn1_plain_swrev_boardcfg(
        request.swrev_slot80, *request.swrev_slot80_flags.as_tuple()
    )

    # Slot 82 (jtag_disable / swrev_ssu)
    field_82 = slot_names.get("82")
    if field_82 is not None:
        if "ssu" in field_82:
            result[field_82] = asn1_plain_swrev_ssu(
                request.swrev_slot82 if request.swrev_slot82 is not None else b"\x00",
                *request.swrev_slot82_flags.as_tuple(),
            )
        else:
            # jtag_disable or similar
            result[field_82] = asn1_jtag_disable(*request.swrev_slot82_flags.as_tuple())

    result["plain_keywr_min_version"] = asn1_plain_keywriter_min_version(
        request.keywr_min_version
    )
    result["plain_msv"] = asn1_plain_msv(
        request.msv.to_bytes(4, byteorder="big"), *request.msv_flags.as_tuple()
    )
    result["plain_mpk_options"] = asn1_plain_mpk_options(
        request.mpk_options, False, False, False, request.mpk_options_active
    )
    result["plain_mek_options"] = asn1_plain_mek_options(
        request.mek_options, False, False, False, request.mek_options_active
    )

    return result


# ---------------------------------------------------------------------------
# Refactored build_primary_certificate (OID map from config)
# ---------------------------------------------------------------------------

def build_primary_certificate(
    signing_key: Union[rsa.RSAPrivateKey, ec.EllipticCurvePrivateKey],
    enc_fields: Dict[str, bytes],
    oid_map: List[OIDEntry],
    multi: bool = False,
    oid_map_multi: Optional[List[List[OIDEntry]]] = None,
    signing_algorithm: SigningAlgorithm = SigningAlgorithm.PKCS1_V15,
) -> List[bytes]:
    """
    Given the OID map and the ASN.1 encoded fields, create the signed
    primary certificate.
    """
    builder = x509.CertificateBuilder()

    subject = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "oS"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "rx"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "gQE843yQV0sag"),
            x509.NameAttribute(
                NameOID.ORGANIZATION_NAME, "dqhGYAQ2Y4gFfCq0t1yABCYxex9eAxt71f"
            ),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "a87RB35W"),
            x509.NameAttribute(NameOID.COMMON_NAME, "x0FSqGTPWbGpuiV"),
            x509.NameAttribute(
                NameOID.EMAIL_ADDRESS, "kFp5uGcgWXxcfxi@vsHs9C9qQWGrBs.com"
            ),
        ]
    )
    issuer = subject

    builder = builder.subject_name(subject)
    builder = builder.issuer_name(issuer)
    builder = builder.serial_number(x509.random_serial_number())

    one_day = datetime.timedelta(1, 0, 0)
    builder = builder.not_valid_before(datetime.datetime.today())
    builder = builder.not_valid_after(datetime.datetime.today() + (30 * one_day))

    pub_key = signing_key.public_key()
    builder = builder.public_key(pub_key)

    builder = builder.add_extension(
        x509.BasicConstraints(ca=True, path_length=None),
        critical=False,
    )

    builder_without_enc = builder

    # Select OID lists
    if multi and oid_map_multi is not None:
        oid_lists = oid_map_multi
    else:
        oid_lists = [oid_map]

    # Add extensions from all OID lists
    for oid_list in oid_lists:
        for entry in oid_list:
            if entry.field_name in enc_fields:
                builder = builder.add_extension(
                    x509.UnrecognizedExtension(
                        x509.ObjectIdentifier(entry.oid), enc_fields[entry.field_name]
                    ),
                    critical=False,
                )
            else:
                raise ValueError(
                    f"Missing field {entry.field_name} corresponding to oid {entry.oid}"
                )

    # Determine padding scheme
    padding_scheme = None
    if signing_algorithm == SigningAlgorithm.PKCS1_V15:
        padding_scheme = padding.PKCS1v15()
    elif signing_algorithm == SigningAlgorithm.RSA_SSA_PSS:
        padding_scheme = padding.PSS(
            mgf=padding.MGF1(hashes.SHA512()),
            salt_length=padding.PSS.MAX_LENGTH,
        )

    print(f"primary cert: signing with {signing_algorithm}")

    builder = builder.add_extension(
        x509.SubjectKeyIdentifier.from_public_key(pub_key), critical=False
    )

    certificates = []
    certificates.append(
        builder.sign(
            private_key=signing_key,
            algorithm=hashes.SHA512(),
            rsa_padding=padding_scheme,
        )
    )

    builder = builder_without_enc

    for j, certificate in enumerate(certificates):
        assert isinstance(certificate, x509.Certificate) is True
        certificates[j] = certificate.public_bytes(serialization.Encoding.DER)

    return certificates


# ---------------------------------------------------------------------------
# Secondary certificate helpers
# ---------------------------------------------------------------------------

# pylint: disable=missing-class-docstring
class ImageIntegrity(Sequence):
    _fields = [
        ("shaType", ObjectIdentifier),
        ("shaValue", OctetString),
        ("imageSize", Integer),
    ]

# pylint: disable=missing-class-docstring
class ImageIntegrityF29(Sequence):
    _fields = [
        ("shaType", ObjectIdentifier),
        ("shaValue", OctetString),
    ]

# pylint: disable=missing-class-docstring
class BootSeq(Sequence):
    _fields = [
        ("certType", Integer),
        ("bootCore", Integer),
        ("bootCoreOpts", Integer),
        ("destAddr", OctetString),
        ("imageSize", Integer),
    ]


def asn1_encode_image_integrity(sha512_hash: bytes, image_size: int) -> bytes:
    """
    Encode the image integrity field using ASN.1
    """
    image_integrity = ImageIntegrity(
        {
            "shaType": "2.16.840.1.101.3.4.2.3",
            "shaValue": sha512_hash,
            "imageSize": image_size,
        }
    )
    return image_integrity.dump()

def asn1_encode_image_integrity_f29h85x(sha512_hash: bytes) -> bytes:
    """
    Encode the image integrity field using ASN.1
    """
    image_integrity = ImageIntegrityF29(
        {
            "shaType": "2.16.840.1.101.3.4.2.3",
            "shaValue": sha512_hash,
        }
    )
    return image_integrity.dump()

def asn1_encode_boot_seq(cert_length: int) -> bytes:
    """
    Encode the boot sequence field using ASN.1
    """
    boot_seq = BootSeq(
        {
            "certType": 2,
            "bootCore": 0,
            "bootCoreOpts": 0,
            "destAddr": b"\x00\x00\x00\x00",
            "imageSize": cert_length,
        }
    )
    return boot_seq.dump()


# ---------------------------------------------------------------------------
# Refactored build_secondary_certificate (format from config)
# ---------------------------------------------------------------------------

def build_secondary_certificate(
    signing_key: Union[RSAPrivateKey, ec.EllipticCurvePrivateKey],
    cert_hash: bytes,
    length: int,
    secondary_format: SecondaryCertFormat = SecondaryCertFormat.STANDARD,
    signing_algorithm: SigningAlgorithm = SigningAlgorithm.PKCS1_V15,
) -> bytes:
    """
    Build a secondary certificate, given the primary certificate's hash and length and
    a signing (private) key.
    """
    builder = x509.CertificateBuilder()

    subject = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "oR"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "rx"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "gQE843yQV0sag"),
            x509.NameAttribute(
                NameOID.ORGANIZATION_NAME, "dqhGYAQ2Y4gFfCq0t1yABCYxex9eAxt71f"
            ),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "a87RB35W"),
            x509.NameAttribute(NameOID.COMMON_NAME, "x0FSqGTPWbGpuiV"),
            x509.NameAttribute(
                NameOID.EMAIL_ADDRESS, "kFp5uGcgWXxcfxi@vsHs9C9qQWGrBs.com"
            ),
        ]
    )
    issuer = subject

    builder = builder.serial_number(x509.random_serial_number())
    builder = builder.subject_name(subject)
    builder = builder.issuer_name(issuer)

    pub_key = signing_key.public_key()
    builder = builder.public_key(pub_key)

    one_day = datetime.timedelta(1, 0, 0)
    builder = builder.not_valid_before(datetime.datetime.today())
    builder = builder.not_valid_after(datetime.datetime.today() + (30 * one_day))

    builder = builder.add_extension(
        x509.BasicConstraints(ca=True, path_length=None),
        critical=False,
    )

    builder = builder.add_extension(
        x509.SubjectKeyIdentifier.from_public_key(pub_key), critical=False
    )

    # Format-driven OIDs
    if secondary_format == SecondaryCertFormat.F29:
        custom_oids = [
            ("1.3.6.1.4.1.294.1.1", asn1_encode_boot_seq(length)),
            ("1.3.6.1.4.1.294.1.2", asn1_encode_image_integrity_f29h85x(cert_hash)),
        ]
    else:
        custom_oids = [
            ("1.3.6.1.4.1.294.1.34", asn1_encode_image_integrity(cert_hash, length)),
        ]

    for oid, value in custom_oids:
        builder = builder.add_extension(
            x509.UnrecognizedExtension(x509.ObjectIdentifier(oid), value),
            critical=False,
        )

    padding_scheme = None
    if signing_algorithm == SigningAlgorithm.PKCS1_V15:
        padding_scheme = padding.PKCS1v15()
    elif signing_algorithm == SigningAlgorithm.RSA_SSA_PSS:
        padding_scheme = padding.PSS(
            mgf=padding.MGF1(hashes.SHA512()),
            salt_length=padding.PSS.MAX_LENGTH,
        )

    print(f"secondary cert: signing with {signing_algorithm}")
    certificate = builder.sign(
        private_key=signing_key,
        algorithm=hashes.SHA512(),
        rsa_padding=padding_scheme,
    )

    return certificate.public_bytes(serialization.Encoding.DER)


# ---------------------------------------------------------------------------
# Top-level orchestrator
# ---------------------------------------------------------------------------

def generate_certificate(
    request: CertificateRequest,
) -> List[Tuple[bytes, bytes, Optional[bytes]]]:
    """
    Generate certificates from a CertificateRequest.

    Returns a list of (final_cert, primary_cert, secondary_cert) tuples.
    secondary_cert is None when not generated.
    """
    config = request.device_config

    # 1. Generate encrypted fields
    enc_fields = generate_encrypted_fields(request)

    # 2. Determine primary cert signing key and algorithm
    primary_signing_key = request.mkeys[0]._private_key
    primary_algo = request.per_key_signing_algorithms[0]

    # 3. Determine OID map
    oid_map = config.primary_oids
    oid_map_multi = config.primary_oids_multi

    # 4. Build primary certificate(s)
    primary_certs = build_primary_certificate(
        primary_signing_key,
        enc_fields,
        oid_map=oid_map,
        multi=request.multi,
        oid_map_multi=oid_map_multi,
        signing_algorithm=primary_algo,
    )

    # 5. For each primary cert, optionally build secondary cert
    results = []
    for primary_cert in primary_certs:
        if request.generate_secondary_cert and len(request.mkeys) > 1:
            secondary_signing_key = request.mkeys[1]._private_key
            secondary_algo = (
                request.per_key_signing_algorithms[1]
                if len(request.per_key_signing_algorithms) > 1
                else request.per_key_signing_algorithms[0]
            )
            h = hash_data(primary_cert)
            l = len(primary_cert)
            secondary_cert = build_secondary_certificate(
                secondary_signing_key,
                h,
                l,
                secondary_format=config.secondary_cert_format,
                signing_algorithm=secondary_algo,
            )
            final_cert = secondary_cert + primary_cert
            results.append((final_cert, primary_cert, secondary_cert))
        else:
            results.append((primary_cert, primary_cert, None))

    return results
