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

from pathlib import Path
import tempfile
from unittest.mock import patch
from asn1crypto.core import Sequence, load

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.x509 import load_der_x509_certificate, ObjectIdentifier
from cryptography.hazmat.primitives import hashes

from tisecprov.session import SecureSession
from tisecprov.cryptoutils import gen_aes256_key, generate_rsa_keypair, hash_data
from tisecprov.crypto import ManufacturerKeys
from tisecprov.certgen import KeywriterSequence, KeywriterSequence2, KeywriterSequence4
from apps.spt.gencert import generate_certificate

# OIDs from the certgen.py
TIFEK_ENC_AES_KEY_OID   = ObjectIdentifier("1.3.6.1.4.1.294.1.64")
SMPK_SIGNED_AES_KEY_OID = ObjectIdentifier("1.3.6.1.4.1.294.1.65")
BMPK_SIGNED_AES_KEY_OID = ObjectIdentifier("1.3.6.1.4.1.294.1.66")
SMPKH_ENC_OID           = ObjectIdentifier("1.3.6.1.4.1.294.1.67")
SMEK_ENC_OID            = ObjectIdentifier("1.3.6.1.4.1.294.1.68")
BMPKH_ENC_OID           = ObjectIdentifier("1.3.6.1.4.1.294.1.70")
BMEK_ENC_OID            = ObjectIdentifier("1.3.6.1.4.1.294.1.71")
MSV_OID                 = ObjectIdentifier("1.3.6.1.4.1.294.1.76")

# CryptoInterface-based AES decrypt helper (replaces old aes_cbc_256_decrypt)
_decrypt_helper = ManufacturerKeys()

def test_certificate_generation():
    tifek_priv, tifek_pub = generate_rsa_keypair()

    # Convert public key to PEM format
    tifek_pub_pem = tifek_pub.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir)
        with open(output_dir / "key.pem", "wb") as f:
            f.write(tifek_pub_pem)

        tifek_pub_path = output_dir / "key.pem"
        with SecureSession(in_memory=True) as session:
            # Create test session
            session_name = "test_session"
            session_password = "test_password"
            session.create_session(session_name, "Test Description", session_password)
            _s = session.open_session(session_name, session_password) 
        
            # generate test keys
            test_smek_bytes = gen_aes256_key().data
            test_bmek_bytes = gen_aes256_key().data
            smpkPriv, smpkPub = generate_rsa_keypair()
            bmpkPriv, bmpkPub = generate_rsa_keypair()
            test_smpk_priv_bytes = smpkPriv.private_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
            test_bmpk_priv_bytes = bmpkPriv.private_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )

            # Add required test keys
            session.add_smek(test_smek_bytes)
            session.add_bmek(test_bmek_bytes)
            session.add_smpk_priv(test_smpk_priv_bytes)
            session.add_bmpk_priv(test_bmpk_priv_bytes)

            with patch('apps.spt.gencert.tifek_pub_def', tifek_pub_pem):
                # Test certificate generation
                generate_certificate(
                    session="test_session",
                    password="test_password",
                    msv="0x12345",
                    use_hsm=False,
                    secure_session=session,
                    output_dir_path=output_dir,
                    tifek_pub_path=tifek_pub_path
                )
        
                with open(output_dir / "temp" / "primary_cert_0.bin", "rb") as f:
                    primary_cert_data = f.read()
                primary_cert = load_der_x509_certificate(primary_cert_data)

                # get the encrypted AES key and decrypt it with TIFEK-priv
                enc_aes_key_ext = primary_cert.extensions.get_extension_for_oid(TIFEK_ENC_AES_KEY_OID)
                enc_aes_key_asn1 = KeywriterSequence.load(enc_aes_key_ext.value.value)
                enc_aes_key = enc_aes_key_asn1['val'].native

                print(f"length of enc_aes_key: {len(enc_aes_key)}")

                # decrypt AES key using tifek priv and pkcs1 v1.5 padding
                aes_key = tifek_priv.decrypt(
                    enc_aes_key,
                    padding.PKCS1v15(),
                )
                print(f"Decrypted AES key length: {len(aes_key)} bytes")

                # get and verify SMEK
                smek_ext = primary_cert.extensions.get_extension_for_oid(SMEK_ENC_OID)
                smek_asn1 = KeywriterSequence2.load(smek_ext.value.value)
                enc_smek = smek_asn1['val'].native
                iv1 = smek_asn1['iv'].native
                rs1 = smek_asn1['rs'].native
                decrypted_smek = _decrypt_helper.aes_decrypt(enc_smek, key=aes_key, iv=iv1)
                # Remove random string from decrypted data
                dec_smek = decrypted_smek[:-32]  # Last 32 bytes are random string
                assert dec_smek == test_smek_bytes, "SMEK mismatch"
                print("SMEK verified successfully")

                # Get and verify BMEK
                bmek_ext = primary_cert.extensions.get_extension_for_oid(BMEK_ENC_OID)
                bmek_asn1 = KeywriterSequence2.load(bmek_ext.value.value)
                enc_bmek = bmek_asn1['val'].native
                iv2 = bmek_asn1['iv'].native
                rs2 = bmek_asn1['rs'].native
                decrypted_bmek = _decrypt_helper.aes_decrypt(enc_bmek, key=aes_key, iv=iv2)
                # Remove random string from decrypted data
                dec_bmek = decrypted_bmek[:-32]  # Last 32 bytes are random string
                assert dec_bmek == test_bmek_bytes, "BMEK mismatch"
                print("BMEK verified successfully")

                # Get and verify MSV
                msv_ext = primary_cert.extensions.get_extension_for_oid(MSV_OID)
                msv_asn1 = KeywriterSequence4.load(msv_ext.value.value)
                msv_bytes = msv_asn1['val'].native
                msv_int = int.from_bytes(msv_bytes, 'big')
                assert msv_int == 0x12345, f"MSV mismatch: expected 0x12345, got 0x{msv_int:x}"
                print(f"MSV verified successfully: 0x{msv_int:x}")

                # get and verify smpkh
                smpkh_ext = primary_cert.extensions.get_extension_for_oid(SMPKH_ENC_OID)
                smpkh_asn1 = KeywriterSequence2.load(smpkh_ext.value.value)

                print("\nSMPKH ASN.1 structure:")
                print(f"val length: {len(smpkh_asn1['val'].native)}")
                print(f"iv length: {len(smpkh_asn1['iv'].native)}")
                print(f"rs length: {len(smpkh_asn1['rs'].native)}")
                print(f"size: {smpkh_asn1['size'].native}")
                print(f"action_flags: {smpkh_asn1['action_flags'].native:x}")

                enc_smpkh = smpkh_asn1['val'].native
                iv3 = smpkh_asn1['iv'].native
                rs3 = smpkh_asn1['rs'].native

                decrypted_smpkh = _decrypt_helper.aes_decrypt(enc_smpkh, key=aes_key, iv=iv3)

                # First 64 bytes are the hash, remaining 32 bytes are random string
                dec_smpkh = decrypted_smpkh[:64]
                actual_rs = decrypted_smpkh[64:96]
                # print(f"actual rs: {actual_rs}")

                # Calculate expected SMPKH
                smpk_pub_der = smpkPub.public_bytes(
                    encoding=serialization.Encoding.DER,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo,
                )

                expected_smpkh = hash_data(smpk_pub_der)

                print("Decrypted SMPKH:", dec_smpkh.hex())
                print("Expected SMPKH:", expected_smpkh.hex())
                print("Public key DER length:", len(smpk_pub_der))

                assert dec_smpkh == expected_smpkh, "SMPKH mismatch"
                print("SMPKH verified successfully")

                # get and verify bmpkh
                bmpkh_ext = primary_cert.extensions.get_extension_for_oid(BMPKH_ENC_OID)
                bmpkh_asn1 = KeywriterSequence2.load(bmpkh_ext.value.value)

                enc_bmpkh = bmpkh_asn1['val'].native
                iv4 = bmpkh_asn1['iv'].native
                rs4 = bmpkh_asn1['rs'].native

                decrypted_bmpkh = _decrypt_helper.aes_decrypt(enc_bmpkh, key=aes_key, iv=iv4)

                # First 64 bytes are the hash, remaining 32 bytes are random string
                dec_bmpkh = decrypted_bmpkh[:64]
                actual_rs = decrypted_bmpkh[64:96]

                # Calculate expected BMPKH
                bmpk_pub_der = bmpkPub.public_bytes(
                    encoding=serialization.Encoding.DER,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo,
                )

                expected_bmpkh = hash_data(bmpk_pub_der)

                print("Decrypted BMPKH:", dec_bmpkh.hex())
                print("Expected BMPKH:", expected_bmpkh.hex())
                print("Public key DER length:", len(bmpk_pub_der))

                assert dec_bmpkh == expected_bmpkh, "BMPKH mismatch"
                print("BMPKH verified successfully")
