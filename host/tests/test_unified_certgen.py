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
Tests for the unified certificate generation architecture.

Covers:
  - DeviceConfig lookup via get_device_config()
  - FieldFlags conversion methods (from_list, from_info_dict, as_tuple)
  - generate_certificate() across multiple device configs
  - OID correctness in generated primary certificates
"""

import pytest
from cryptography.x509 import load_der_x509_certificate, ObjectIdentifier
from cryptography.hazmat.primitives import serialization

from tisecprov.crypto import ManufacturerKeys
from tisecprov.cryptoutils import gen_aes256_key, generate_rsa_keypair
from tisecprov.crypto_interfaces import SigningAlgorithm
from tisecprov.certgen import (
    generate_certificate,
    KeywriterSequence,
    KeywriterSequence2,
    KeywriterSequence4,
)
from tisecprov.device_config import (
    CertificateRequest,
    DeviceConfig,
    FieldFlags,
    OIDEntry,
    SecondaryCertFormat,
    get_device_config,
    DEVICE_CONFIGS,
)


# ---------------------------------------------------------------------------
# FieldFlags tests
# ---------------------------------------------------------------------------

class TestFieldFlags:
    def test_from_list_empty(self):
        ff = FieldFlags.from_list([])
        assert ff == FieldFlags(wp=False, rp=False, ovrd=False, active=False)

    def test_from_list_all(self):
        ff = FieldFlags.from_list(["wp", "rp", "ovrd", "active"])
        assert ff == FieldFlags(wp=True, rp=True, ovrd=True, active=True)

    def test_from_list_partial(self):
        ff = FieldFlags.from_list(["active", "wp"])
        assert ff.active is True
        assert ff.wp is True
        assert ff.rp is False
        assert ff.ovrd is False

    def test_from_list_ignores_unknown(self):
        ff = FieldFlags.from_list(["active", "bogus"])
        assert ff.active is True
        assert ff.wp is False

    def test_from_info_dict_empty(self):
        ff = FieldFlags.from_info_dict({})
        assert ff == FieldFlags()

    def test_from_info_dict_all_yes(self):
        ff = FieldFlags.from_info_dict({
            "wp": "yes", "rp": "yes", "ovrd": "yes", "flag": "yes"
        })
        assert ff == FieldFlags(wp=True, rp=True, ovrd=True, active=True)

    def test_from_info_dict_mixed(self):
        ff = FieldFlags.from_info_dict({"wp": "yes", "rp": "no", "flag": "yes"})
        assert ff.wp is True
        assert ff.rp is False
        assert ff.ovrd is False
        assert ff.active is True

    def test_from_info_dict_no_values(self):
        ff = FieldFlags.from_info_dict({"wp": "no", "flag": "no"})
        assert ff == FieldFlags()

    def test_as_tuple(self):
        ff = FieldFlags(wp=True, rp=False, ovrd=True, active=False)
        assert ff.as_tuple() == (True, False, True, False)

    def test_as_tuple_default(self):
        assert FieldFlags().as_tuple() == (False, False, False, False)


# ---------------------------------------------------------------------------
# DeviceConfig lookup tests
# ---------------------------------------------------------------------------

class TestDeviceConfig:
    def test_lookup_default(self):
        cfg = get_device_config("default")
        assert cfg.device_name == "default"
        assert cfg.secondary_cert_format == SecondaryCertFormat.STANDARD
        assert cfg.pad_ecc_signatures is False

    def test_lookup_f29h85x(self):
        cfg = get_device_config("f29h85x")
        assert cfg.device_name == "f29h85x"
        assert cfg.secondary_cert_format == SecondaryCertFormat.F29
        assert cfg.pad_ecc_signatures is True
        assert cfg.silicon_revisions == {"SR_10", "SR_20"}
        assert cfg.otp_details is not None
        assert cfg.otp_details["MAX_SWREV_SSU_VALUE_SIZE"] == 64

    def test_lookup_am263x(self):
        cfg = get_device_config("am263x")
        assert cfg.device_name == "am263x"
        assert cfg.secondary_cert_format == SecondaryCertFormat.STANDARD
        assert cfg.pad_ecc_signatures is True
        assert cfg.silicon_revisions == {"SR_10", "SR_11"}

    def test_lookup_am273x(self):
        cfg = get_device_config("am273x")
        assert cfg.silicon_revisions == {"SR_10", "SR_11", "SR_12"}

    def test_lookup_unknown_falls_back_to_default(self):
        cfg = get_device_config("nonexistent_device_xyz")
        assert cfg.device_name == "default"

    def test_all_configs_have_primary_oids(self):
        for name, cfg in DEVICE_CONFIGS.items():
            assert len(cfg.primary_oids) > 0, f"{name} has no primary OIDs"

    def test_f29_has_ssu_oid(self):
        cfg = get_device_config("f29h85x")
        field_names = [e.field_name for e in cfg.primary_oids]
        assert "plain_swrev_ssu" in field_names
        assert "plain_swrev_hsmRT" in field_names
        assert "plain_swrev_sec_app" in field_names

    def test_default_has_sysfw_oid(self):
        cfg = get_device_config("default")
        field_names = [e.field_name for e in cfg.primary_oids]
        assert "plain_swrev_sysfw" in field_names
        assert "plain_swrev_sec_brdcfg" in field_names
        assert "jtag_disable" in field_names

    def test_am26x_has_hsmrt_no_slot82(self):
        cfg = get_device_config("am263x")
        field_names = [e.field_name for e in cfg.primary_oids]
        assert "plain_swrev_hsmRT" in field_names
        assert "plain_swrev_sec_app" in field_names
        # am26x OIDs should NOT include OID .82
        oid_suffixes = [e.oid.split(".")[-1] for e in cfg.primary_oids]
        assert "82" not in oid_suffixes


# ---------------------------------------------------------------------------
# Helper to build a CertificateRequest with test keys
# ---------------------------------------------------------------------------

def _make_test_request(
    device_name: str = "default",
    msv: int = 0xABCD,
    signing_algo: SigningAlgorithm = SigningAlgorithm.PKCS1_V15,
    generate_secondary: bool = True,
) -> CertificateRequest:
    """Build a CertificateRequest with freshly generated RSA keys."""
    tifek_priv, tifek_pub = generate_rsa_keypair()
    tifek_pub_pem = tifek_pub.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    aes_key = gen_aes256_key().data

    smpk = ManufacturerKeys()
    bmpk = ManufacturerKeys()

    config = get_device_config(device_name)

    return CertificateRequest(
        device_config=config,
        mkeys=[smpk, bmpk],
        aes_key=aes_key,
        tifek_pub=tifek_pub_pem,
        per_key_signing_algorithms=[signing_algo, signing_algo],
        smpk_flags=FieldFlags(active=True),
        smek_flags=FieldFlags(active=True),
        bmpk_flags=FieldFlags(active=True),
        bmek_flags=FieldFlags(active=True),
        msv=msv,
        generate_secondary_cert=generate_secondary,
    )


# ---------------------------------------------------------------------------
# generate_certificate tests
# ---------------------------------------------------------------------------

class TestGenerateCertificateFromRequest:
    def test_default_config_produces_valid_cert(self):
        request = _make_test_request("default")
        results = generate_certificate(request)

        assert len(results) == 1
        final_cert, primary_cert, secondary_cert = results[0]
        assert len(primary_cert) > 0
        assert secondary_cert is not None
        assert final_cert == secondary_cert + primary_cert

        # Primary cert should be parseable as X.509
        cert = load_der_x509_certificate(primary_cert)
        assert cert is not None

    def test_default_config_has_correct_oids(self):
        request = _make_test_request("default")
        results = generate_certificate(request)
        primary_cert = results[0][1]
        cert = load_der_x509_certificate(primary_cert)

        # Check key OIDs are present
        expected_oids = [
            "1.3.6.1.4.1.294.1.64",  # enc_aes_key
            "1.3.6.1.4.1.294.1.65",  # enc_smpk_signed_aes_key
            "1.3.6.1.4.1.294.1.66",  # enc_bmpk_signed_aes_key
            "1.3.6.1.4.1.294.1.67",  # aesenc_smpkh
            "1.3.6.1.4.1.294.1.68",  # aesenc_smek
            "1.3.6.1.4.1.294.1.76",  # plain_msv
            "1.3.6.1.4.1.294.1.78",  # plain_swrev_sysfw (slot 78)
            "1.3.6.1.4.1.294.1.80",  # plain_swrev_sec_brdcfg (slot 80)
            "1.3.6.1.4.1.294.1.82",  # jtag_disable (slot 82)
        ]
        for oid_str in expected_oids:
            ext = cert.extensions.get_extension_for_oid(ObjectIdentifier(oid_str))
            assert ext is not None, f"Missing OID {oid_str}"

    def test_default_msv_value(self):
        request = _make_test_request("default", msv=0x12345)
        results = generate_certificate(request)
        primary_cert = results[0][1]
        cert = load_der_x509_certificate(primary_cert)

        msv_ext = cert.extensions.get_extension_for_oid(
            ObjectIdentifier("1.3.6.1.4.1.294.1.76")
        )
        msv_asn1 = KeywriterSequence4.load(msv_ext.value.value)
        msv_bytes = msv_asn1["val"].native
        msv_int = int.from_bytes(msv_bytes, "big")
        assert msv_int == 0x12345

    def test_f29h85x_config_produces_valid_cert(self):
        request = _make_test_request("f29h85x")
        results = generate_certificate(request)

        assert len(results) == 1
        final_cert, primary_cert, secondary_cert = results[0]
        assert len(primary_cert) > 0
        assert secondary_cert is not None

        cert = load_der_x509_certificate(primary_cert)
        assert cert is not None

    def test_f29h85x_has_correct_oids(self):
        request = _make_test_request("f29h85x")
        results = generate_certificate(request)
        primary_cert = results[0][1]
        cert = load_der_x509_certificate(primary_cert)

        # F29 should have OIDs .78 (hsmRT), .80 (sec_app), .82 (ssu)
        for oid_str in [
            "1.3.6.1.4.1.294.1.78",  # plain_swrev_hsmRT
            "1.3.6.1.4.1.294.1.80",  # plain_swrev_sec_app
            "1.3.6.1.4.1.294.1.82",  # plain_swrev_ssu
        ]:
            ext = cert.extensions.get_extension_for_oid(ObjectIdentifier(oid_str))
            assert ext is not None, f"Missing OID {oid_str} in f29h85x cert"

    def test_f29h85x_secondary_cert_has_boot_seq_oid(self):
        request = _make_test_request("f29h85x")
        results = generate_certificate(request)
        secondary_cert_bytes = results[0][2]
        assert secondary_cert_bytes is not None

        sec_cert = load_der_x509_certificate(secondary_cert_bytes)
        # F29 secondary should have OID .1 (boot_seq) and .2 (image_integrity)
        boot_seq_ext = sec_cert.extensions.get_extension_for_oid(
            ObjectIdentifier("1.3.6.1.4.1.294.1.1")
        )
        assert boot_seq_ext is not None
        img_integrity_ext = sec_cert.extensions.get_extension_for_oid(
            ObjectIdentifier("1.3.6.1.4.1.294.1.2")
        )
        assert img_integrity_ext is not None

    def test_default_secondary_cert_has_image_integrity_oid(self):
        request = _make_test_request("default")
        results = generate_certificate(request)
        secondary_cert_bytes = results[0][2]
        assert secondary_cert_bytes is not None

        sec_cert = load_der_x509_certificate(secondary_cert_bytes)
        # Standard secondary should have OID .34 (image_integrity with size)
        ext = sec_cert.extensions.get_extension_for_oid(
            ObjectIdentifier("1.3.6.1.4.1.294.1.34")
        )
        assert ext is not None

    def test_am263x_config_produces_valid_cert(self):
        request = _make_test_request("am263x")
        results = generate_certificate(request)

        assert len(results) == 1
        primary_cert = results[0][1]
        cert = load_der_x509_certificate(primary_cert)
        assert cert is not None

        # am263x uses hsmRT/sec_app naming but no OID .82
        ext_78 = cert.extensions.get_extension_for_oid(
            ObjectIdentifier("1.3.6.1.4.1.294.1.78")
        )
        assert ext_78 is not None

        ext_80 = cert.extensions.get_extension_for_oid(
            ObjectIdentifier("1.3.6.1.4.1.294.1.80")
        )
        assert ext_80 is not None

        # OID .82 should NOT be present for am263x
        with pytest.raises(Exception):
            cert.extensions.get_extension_for_oid(
                ObjectIdentifier("1.3.6.1.4.1.294.1.82")
            )

    def test_no_secondary_cert_when_disabled(self):
        request = _make_test_request("default", generate_secondary=False)
        results = generate_certificate(request)

        assert len(results) == 1
        final_cert, primary_cert, secondary_cert = results[0]
        assert secondary_cert is None
        assert final_cert == primary_cert

    def test_am273x_config_produces_valid_cert(self):
        request = _make_test_request("am273x")
        results = generate_certificate(request)

        assert len(results) == 1
        primary_cert = results[0][1]
        cert = load_der_x509_certificate(primary_cert)
        assert cert is not None

    def test_encrypted_smek_decryptable(self):
        """Verify that the AES-encrypted SMEK in the cert can be decrypted."""
        tifek_priv, tifek_pub = generate_rsa_keypair()
        tifek_pub_pem = tifek_pub.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        aes_key = gen_aes256_key().data
        smpk = ManufacturerKeys()
        bmpk = ManufacturerKeys()

        request = CertificateRequest(
            device_config=get_device_config("default"),
            mkeys=[smpk, bmpk],
            aes_key=aes_key,
            tifek_pub=tifek_pub_pem,
            per_key_signing_algorithms=[SigningAlgorithm.PKCS1_V15, SigningAlgorithm.PKCS1_V15],
            smpk_flags=FieldFlags(active=True),
            smek_flags=FieldFlags(active=True),
            bmpk_flags=FieldFlags(active=True),
            bmek_flags=FieldFlags(active=True),
        )

        results = generate_certificate(request)
        primary_cert = results[0][1]
        cert = load_der_x509_certificate(primary_cert)

        # Decrypt AES key with TIFEK-priv
        from cryptography.hazmat.primitives.asymmetric import padding
        enc_aes_ext = cert.extensions.get_extension_for_oid(
            ObjectIdentifier("1.3.6.1.4.1.294.1.64")
        )
        enc_aes_asn1 = KeywriterSequence.load(enc_aes_ext.value.value)
        enc_aes = enc_aes_asn1["val"].native
        decrypted_aes_key = tifek_priv.decrypt(enc_aes, padding.PKCS1v15())
        assert decrypted_aes_key == aes_key

        # Decrypt SMEK
        smek_ext = cert.extensions.get_extension_for_oid(
            ObjectIdentifier("1.3.6.1.4.1.294.1.68")
        )
        smek_asn1 = KeywriterSequence2.load(smek_ext.value.value)
        enc_smek = smek_asn1["val"].native
        iv = smek_asn1["iv"].native

        helper = ManufacturerKeys()
        decrypted_smek_with_rs = helper.aes_decrypt(enc_smek, key=aes_key, iv=iv)
        dec_smek = decrypted_smek_with_rs[:-32]  # last 32 bytes are random string
        assert dec_smek == smpk.get_symmetric_key()
