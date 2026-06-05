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
Device configuration module for unified certificate generation.

Provides dataclasses and pre-built configs so that new devices can be
added by config alone, without touching cryptographic logic.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Set

from tisecprov.crypto_interfaces import SigningAlgorithm


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class FieldFlags:
    """Normalized flag model for OTP field write/read/override/active bits."""
    wp: bool = False
    rp: bool = False
    ovrd: bool = False
    active: bool = False

    @classmethod
    def from_list(cls, flags: List[str]) -> "FieldFlags":
        """Convert SPT-style flag list (['wp', 'active']) to FieldFlags."""
        return cls(
            wp="wp" in flags,
            rp="rp" in flags,
            ovrd="ovrd" in flags,
            active="active" in flags,
        )

    @classmethod
    def from_info_dict(cls, info: Dict[str, str]) -> "FieldFlags":
        """Convert F29-style info dict ({'wp':'yes', 'flag':'yes'}) to FieldFlags."""
        return cls(
            wp=info.get("wp", "no") == "yes",
            rp=info.get("rp", "no") == "yes",
            ovrd=info.get("ovrd", "no") == "yes",
            active=info.get("flag", "no") == "yes",
        )

    def as_tuple(self) -> tuple:
        """Return (wp, rp, ovrd, active) for unpacking into ASN.1 helpers."""
        return (self.wp, self.rp, self.ovrd, self.active)


@dataclass
class OIDEntry:
    """Maps an X.509 OID string to a field name in the enc_fields dict."""
    oid: str        # e.g. "1.3.6.1.4.1.294.1.78"
    field_name: str  # e.g. "plain_swrev_hsmRT"


class SecondaryCertFormat(Enum):
    """Format variants for the secondary (outer) certificate."""
    STANDARD = "standard"  # OID .34  (image_integrity with size)
    F29 = "f29"            # OID .1 + OID .2  (boot_seq + image_integrity without size)


@dataclass
class DeviceConfig:
    """All device-specific variations in one place."""
    device_name: str
    primary_oids: List[OIDEntry]
    primary_oids_multi: Optional[List[List[OIDEntry]]]
    secondary_cert_format: SecondaryCertFormat
    secondary_cert_required: bool
    supported_signing_algorithms: List[SigningAlgorithm]
    pad_ecc_signatures: bool
    silicon_revisions: Optional[Set[str]] = None
    otp_details: Optional[Dict[str, int]] = None


@dataclass
class ExtendedOTPData:
    """Bundles extended OTP parameters for certificate generation."""
    data: bytes     # encrypted OTP data
    iv: bytes       # 16 bytes
    rs: bytes       # 32 bytes
    wprp: bytes     # write-protect || read-protect bytes
    index: int
    size: int
    flags: FieldFlags


@dataclass
class CertificateRequest:
    """Bundles ALL inputs for certificate generation."""
    device_config: DeviceConfig
    mkeys: list                     # List[CryptoInterface]
    aes_key: bytes
    tifek_pub: bytes

    per_key_signing_algorithms: List[SigningAlgorithm] = field(
        default_factory=lambda: [SigningAlgorithm.PKCS1_V15]
    )

    # Key flags (SMPK/SMEK always present, BMPK/BMEK optional)
    smpk_flags: FieldFlags = field(default_factory=FieldFlags)
    smek_flags: FieldFlags = field(default_factory=FieldFlags)
    bmpk_flags: Optional[FieldFlags] = None
    bmek_flags: Optional[FieldFlags] = None
    include_smek: bool = True
    include_bmek: bool = True

    # Plaintext values and flags
    msv: int = 0
    msv_flags: FieldFlags = field(default_factory=lambda: FieldFlags(active=True))
    key_rev: int = 1
    key_rev_flags: FieldFlags = field(default_factory=FieldFlags)
    key_cnt: int = 1
    key_cnt_flags: FieldFlags = field(default_factory=FieldFlags)

    # SWREV values keyed by OID slot number
    swrev_slot78: bytes = field(default=b"\x00")
    swrev_slot78_flags: FieldFlags = field(default_factory=FieldFlags)
    swrev_slot79: bytes = field(default=b"\x01")
    swrev_slot79_flags: FieldFlags = field(default_factory=FieldFlags)
    swrev_slot80: bytes = field(default=b"\x00")
    swrev_slot80_flags: FieldFlags = field(default_factory=FieldFlags)
    swrev_slot82: Optional[bytes] = None
    swrev_slot82_flags: FieldFlags = field(default_factory=FieldFlags)

    # MPK/MEK options
    mpk_options: bytes = field(default=b"\x00\x00")
    mpk_options_active: bool = False
    mek_options: bytes = field(default=b"\x00")
    mek_options_active: bool = False

    # Keywriter min version
    keywr_min_version: bytes = field(default=b"\x02\x00")

    # Extended OTP
    ext_otp: Optional[ExtendedOTPData] = None

    # Certificate options
    generate_secondary_cert: bool = True
    multi: bool = False


# ---------------------------------------------------------------------------
# Pre-built OID maps
# ---------------------------------------------------------------------------

_STANDARD_PRIMARY_OIDS = [
    OIDEntry("1.3.6.1.4.1.294.1.64", "enc_aes_key"),
    OIDEntry("1.3.6.1.4.1.294.1.65", "enc_smpk_signed_aes_key"),
    OIDEntry("1.3.6.1.4.1.294.1.66", "enc_bmpk_signed_aes_key"),
    OIDEntry("1.3.6.1.4.1.294.1.67", "aesenc_smpkh"),
    OIDEntry("1.3.6.1.4.1.294.1.68", "aesenc_smek"),
    OIDEntry("1.3.6.1.4.1.294.1.69", "plain_mpk_options"),
    OIDEntry("1.3.6.1.4.1.294.1.70", "aesenc_bmpkh"),
    OIDEntry("1.3.6.1.4.1.294.1.71", "aesenc_bmek"),
    OIDEntry("1.3.6.1.4.1.294.1.72", "plain_mek_options"),
    OIDEntry("1.3.6.1.4.1.294.1.73", "aesenc_user_otp"),
    OIDEntry("1.3.6.1.4.1.294.1.74", "plain_key_rev"),
    OIDEntry("1.3.6.1.4.1.294.1.76", "plain_msv"),
    OIDEntry("1.3.6.1.4.1.294.1.77", "plain_key_cnt"),
    OIDEntry("1.3.6.1.4.1.294.1.78", "plain_swrev_sysfw"),
    OIDEntry("1.3.6.1.4.1.294.1.79", "plain_swrev_sbl"),
    OIDEntry("1.3.6.1.4.1.294.1.80", "plain_swrev_sec_brdcfg"),
    OIDEntry("1.3.6.1.4.1.294.1.81", "plain_keywr_min_version"),
    OIDEntry("1.3.6.1.4.1.294.1.82", "jtag_disable"),
]

_F29_PRIMARY_OIDS = [
    OIDEntry("1.3.6.1.4.1.294.1.64", "enc_aes_key"),
    OIDEntry("1.3.6.1.4.1.294.1.65", "enc_smpk_signed_aes_key"),
    OIDEntry("1.3.6.1.4.1.294.1.66", "enc_bmpk_signed_aes_key"),
    OIDEntry("1.3.6.1.4.1.294.1.67", "aesenc_smpkh"),
    OIDEntry("1.3.6.1.4.1.294.1.68", "aesenc_smek"),
    OIDEntry("1.3.6.1.4.1.294.1.69", "plain_mpk_options"),
    OIDEntry("1.3.6.1.4.1.294.1.70", "aesenc_bmpkh"),
    OIDEntry("1.3.6.1.4.1.294.1.71", "aesenc_bmek"),
    OIDEntry("1.3.6.1.4.1.294.1.72", "plain_mek_options"),
    OIDEntry("1.3.6.1.4.1.294.1.73", "aesenc_user_otp"),
    OIDEntry("1.3.6.1.4.1.294.1.74", "plain_key_rev"),
    OIDEntry("1.3.6.1.4.1.294.1.76", "plain_msv"),
    OIDEntry("1.3.6.1.4.1.294.1.77", "plain_key_cnt"),
    OIDEntry("1.3.6.1.4.1.294.1.78", "plain_swrev_hsmRT"),
    OIDEntry("1.3.6.1.4.1.294.1.79", "plain_swrev_sbl"),
    OIDEntry("1.3.6.1.4.1.294.1.80", "plain_swrev_sec_app"),
    OIDEntry("1.3.6.1.4.1.294.1.81", "plain_keywr_min_version"),
    OIDEntry("1.3.6.1.4.1.294.1.82", "plain_swrev_ssu"),
]

# Standard OIDs for am263x-family but with hsmRT/sec_app/ssu naming
# (these devices go through the F29 flow but use standard-format secondary cert)
_AM26X_PRIMARY_OIDS = [
    OIDEntry("1.3.6.1.4.1.294.1.64", "enc_aes_key"),
    OIDEntry("1.3.6.1.4.1.294.1.65", "enc_smpk_signed_aes_key"),
    OIDEntry("1.3.6.1.4.1.294.1.66", "enc_bmpk_signed_aes_key"),
    OIDEntry("1.3.6.1.4.1.294.1.67", "aesenc_smpkh"),
    OIDEntry("1.3.6.1.4.1.294.1.68", "aesenc_smek"),
    OIDEntry("1.3.6.1.4.1.294.1.69", "plain_mpk_options"),
    OIDEntry("1.3.6.1.4.1.294.1.70", "aesenc_bmpkh"),
    OIDEntry("1.3.6.1.4.1.294.1.71", "aesenc_bmek"),
    OIDEntry("1.3.6.1.4.1.294.1.72", "plain_mek_options"),
    OIDEntry("1.3.6.1.4.1.294.1.73", "aesenc_user_otp"),
    OIDEntry("1.3.6.1.4.1.294.1.74", "plain_key_rev"),
    OIDEntry("1.3.6.1.4.1.294.1.76", "plain_msv"),
    OIDEntry("1.3.6.1.4.1.294.1.77", "plain_key_cnt"),
    OIDEntry("1.3.6.1.4.1.294.1.78", "plain_swrev_hsmRT"),
    OIDEntry("1.3.6.1.4.1.294.1.79", "plain_swrev_sbl"),
    OIDEntry("1.3.6.1.4.1.294.1.80", "plain_swrev_sec_app"),
    OIDEntry("1.3.6.1.4.1.294.1.81", "plain_keywr_min_version"),
]

_STANDARD_MULTI_OIDS = [
    [
        OIDEntry("1.3.6.1.4.1.294.1.64", "enc_aes_key"),
        OIDEntry("1.3.6.1.4.1.294.1.65", "enc_smpk_signed_aes_key"),
    ],
    [
        OIDEntry("1.3.6.1.4.1.294.1.66", "enc_bmpk_signed_aes_key"),
        OIDEntry("1.3.6.1.4.1.294.1.69", "plain_mpk_options"),
        OIDEntry("1.3.6.1.4.1.294.1.72", "plain_mek_options"),
    ],
    [
        OIDEntry("1.3.6.1.4.1.294.1.67", "aesenc_smpkh"),
        OIDEntry("1.3.6.1.4.1.294.1.68", "aesenc_smek"),
        OIDEntry("1.3.6.1.4.1.294.1.70", "aesenc_bmpkh"),
        OIDEntry("1.3.6.1.4.1.294.1.71", "aesenc_bmek"),
        OIDEntry("1.3.6.1.4.1.294.1.73", "aesenc_user_otp"),
        OIDEntry("1.3.6.1.4.1.294.1.74", "plain_key_rev"),
        OIDEntry("1.3.6.1.4.1.294.1.76", "plain_msv"),
        OIDEntry("1.3.6.1.4.1.294.1.77", "plain_key_cnt"),
        OIDEntry("1.3.6.1.4.1.294.1.78", "plain_swrev_sysfw"),
        OIDEntry("1.3.6.1.4.1.294.1.79", "plain_swrev_sbl"),
        OIDEntry("1.3.6.1.4.1.294.1.80", "plain_swrev_sec_brdcfg"),
        OIDEntry("1.3.6.1.4.1.294.1.81", "plain_keywr_min_version"),
    ],
]

_RSA_ONLY = [SigningAlgorithm.PKCS1_V15, SigningAlgorithm.RSA_SSA_PSS]
_ALL_ALGORITHMS = [
    SigningAlgorithm.PKCS1_V15,
    SigningAlgorithm.RSA_SSA_PSS,
    SigningAlgorithm.SECP256R1,
    SigningAlgorithm.SECP384R1,
    SigningAlgorithm.SECP521R1,
    SigningAlgorithm.BRAINPOOL512,
]


# ---------------------------------------------------------------------------
# Pre-built device configs
# ---------------------------------------------------------------------------

DEVICE_CONFIGS: Dict[str, DeviceConfig] = {
    "default": DeviceConfig(
        device_name="default",
        primary_oids=_STANDARD_PRIMARY_OIDS,
        primary_oids_multi=_STANDARD_MULTI_OIDS,
        secondary_cert_format=SecondaryCertFormat.STANDARD,
        secondary_cert_required=True,
        supported_signing_algorithms=_RSA_ONLY,
        pad_ecc_signatures=False,
    ),
    "j722s": DeviceConfig(
        device_name="j722s",
        primary_oids=_STANDARD_PRIMARY_OIDS,
        primary_oids_multi=_STANDARD_MULTI_OIDS,
        secondary_cert_format=SecondaryCertFormat.STANDARD,
        secondary_cert_required=True,
        supported_signing_algorithms=_RSA_ONLY,
        pad_ecc_signatures=False,
    ),
    "am62px": DeviceConfig(
        device_name="am62px",
        primary_oids=_STANDARD_PRIMARY_OIDS,
        primary_oids_multi=_STANDARD_MULTI_OIDS,
        secondary_cert_format=SecondaryCertFormat.STANDARD,
        secondary_cert_required=True,
        supported_signing_algorithms=_RSA_ONLY,
        pad_ecc_signatures=False,
    ),
    "f29h85x": DeviceConfig(
        device_name="f29h85x",
        primary_oids=_F29_PRIMARY_OIDS,
        primary_oids_multi=None,
        secondary_cert_format=SecondaryCertFormat.F29,
        secondary_cert_required=False,
        supported_signing_algorithms=_ALL_ALGORITHMS,
        pad_ecc_signatures=True,
        silicon_revisions={"SR_10", "SR_20"},
        otp_details={
            "MIN_EXT_PROG_BITS": 4,
            "MAX_EXT_OTP_SIZE": 1664,
            "MEK_OPT_SIZE": 5,
            "MAX_MEK_OPT_VALUE_SIZE_OCTETS": 2,
            "MPK_OPT_SIZE": 10,
            "MAX_MPK_OPT_VALUE_SIZE_OCTETS": 3,
            "MAX_MSV_VALUE_SIZE_OCTETS": 6,
            "MAX_SWREV_HSMRT_VALUE_SIZE": 32,
            "MAX_SWREV_SBL_VALUE_SIZE": 32,
            "MAX_SWREV_SEC_APP_VALUE_SIZE": 32,
            "MAX_SWREV_SSU_VALUE_SIZE": 64,
        },
    ),
    "am263x": DeviceConfig(
        device_name="am263x",
        primary_oids=_AM26X_PRIMARY_OIDS,
        primary_oids_multi=None,
        secondary_cert_format=SecondaryCertFormat.STANDARD,
        secondary_cert_required=False,
        supported_signing_algorithms=_ALL_ALGORITHMS,
        pad_ecc_signatures=True,
        silicon_revisions={"SR_10", "SR_11"},
        otp_details={
            "MIN_EXT_PROG_BITS": 4,
            "MAX_EXT_OTP_SIZE": 1664,
            "MEK_OPT_SIZE": 5,
            "MAX_MEK_OPT_VALUE_SIZE_OCTETS": 2,
            "MPK_OPT_SIZE": 10,
            "MAX_MPK_OPT_VALUE_SIZE_OCTETS": 3,
            "MAX_MSV_VALUE_SIZE_OCTETS": 6,
            "MAX_SWREV_HSMRT_VALUE_SIZE": 32,
            "MAX_SWREV_SBL_VALUE_SIZE": 32,
            "MAX_SWREV_SEC_APP_VALUE_SIZE": 96,
        },
    ),
    "am263px": DeviceConfig(
        device_name="am263px",
        primary_oids=_AM26X_PRIMARY_OIDS,
        primary_oids_multi=None,
        secondary_cert_format=SecondaryCertFormat.STANDARD,
        secondary_cert_required=False,
        supported_signing_algorithms=_ALL_ALGORITHMS,
        pad_ecc_signatures=True,
        silicon_revisions={"SR_10"},
        otp_details={
            "MIN_EXT_PROG_BITS": 4,
            "MAX_EXT_OTP_SIZE": 1664,
            "MEK_OPT_SIZE": 5,
            "MAX_MEK_OPT_VALUE_SIZE_OCTETS": 2,
            "MPK_OPT_SIZE": 10,
            "MAX_MPK_OPT_VALUE_SIZE_OCTETS": 3,
            "MAX_MSV_VALUE_SIZE_OCTETS": 6,
            "MAX_SWREV_HSMRT_VALUE_SIZE": 32,
            "MAX_SWREV_SBL_VALUE_SIZE": 32,
            "MAX_SWREV_SEC_APP_VALUE_SIZE": 96,
        },
    ),
    "am261x": DeviceConfig(
        device_name="am261x",
        primary_oids=_AM26X_PRIMARY_OIDS,
        primary_oids_multi=None,
        secondary_cert_format=SecondaryCertFormat.STANDARD,
        secondary_cert_required=False,
        supported_signing_algorithms=_ALL_ALGORITHMS,
        pad_ecc_signatures=True,
        silicon_revisions={"SR_10"},
        otp_details={
            "MIN_EXT_PROG_BITS": 4,
            "MAX_EXT_OTP_SIZE": 1664,
            "MEK_OPT_SIZE": 5,
            "MAX_MEK_OPT_VALUE_SIZE_OCTETS": 2,
            "MPK_OPT_SIZE": 10,
            "MAX_MPK_OPT_VALUE_SIZE_OCTETS": 3,
            "MAX_MSV_VALUE_SIZE_OCTETS": 6,
            "MAX_SWREV_HSMRT_VALUE_SIZE": 32,
            "MAX_SWREV_SBL_VALUE_SIZE": 32,
            "MAX_SWREV_SEC_APP_VALUE_SIZE": 96,
        },
    ),
    "am273x": DeviceConfig(
        device_name="am273x",
        primary_oids=_AM26X_PRIMARY_OIDS,
        primary_oids_multi=None,
        secondary_cert_format=SecondaryCertFormat.STANDARD,
        secondary_cert_required=False,
        supported_signing_algorithms=_ALL_ALGORITHMS,
        pad_ecc_signatures=True,
        silicon_revisions={"SR_10", "SR_11", "SR_12"},
        otp_details={
            "MIN_EXT_PROG_BITS": 4,
            "MAX_EXT_OTP_SIZE": 1664,
            "MEK_OPT_SIZE": 5,
            "MAX_MEK_OPT_VALUE_SIZE_OCTETS": 2,
            "MPK_OPT_SIZE": 10,
            "MAX_MPK_OPT_VALUE_SIZE_OCTETS": 3,
            "MAX_MSV_VALUE_SIZE_OCTETS": 6,
            "MAX_SWREV_HSMRT_VALUE_SIZE": 32,
            "MAX_SWREV_SBL_VALUE_SIZE": 32,
            "MAX_SWREV_SEC_APP_VALUE_SIZE": 96,
        },
    ),
}


def get_device_config(device_name: str) -> DeviceConfig:
    """Look up a DeviceConfig by name, falling back to 'default'."""
    return DEVICE_CONFIGS.get(device_name, DEVICE_CONFIGS["default"])
