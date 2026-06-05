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

import os

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding


from tisecprov.certgen import (
    build_primary_certificate,
    generate_encrypted_fields,
    build_secondary_certificate,
    KeywriterSequence,
    asn1_enc_aes_key,
)
from tisecprov.crypto import (
    ManufacturerKeys,
)

from tisecprov.cryptoutils import (
    gen_aes256_key,
    hash_data,
    rsa_decrypt_with_pkcs15_padding,
    load_rsa_private_key,
)


def test_build_primary_certificate():
    """
    Generates a primary certificate using the given ManufacturerKeys and AES key.

    Raises:
        AssertionError: If the certificate signature is invalid.
    """
    # Generate a ManufacturerKeys object
    smkey = ManufacturerKeys()

    # Create a list of ManufacturerKeys objects
    smek = smkey.get_symmetric_key()
    smpk_priv = load_rsa_private_key(smkey.export_private_key())

    # Generate a Backup ManufacturerKeys object
    bmkey = ManufacturerKeys()

    # Create a list of Backup ManufacturerKeys objects
    bmek = bmkey.get_symmetric_key()
    bmpk_priv = load_rsa_private_key(bmkey.export_private_key())

    # Generate an AES key
    aes_key = os.urandom(32)

    # Create a new RSA key pair with a key size of 4096 bits
    key = rsa.generate_private_key(
        public_exponent=65537, key_size=4096, backend=default_backend()
    )
    # Get the public key in PEM format
    tifek_pub = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    # Set the MSV (Manufacturer Security Version)
    msv = 0x0c0ffe

    # Set the MPK flags
    mpk_flags = []

    # Set the MEK flags
    mek_flags = []

    enc_field = generate_encrypted_fields(
        [ManufacturerKeys(smek, smpk_priv), ManufacturerKeys(bmek, bmpk_priv)],
        aes_key,
        tifek_pub,
        msv,
        mpk_flags,
        mek_flags,
    )
    primary_cert_bytes_array = build_primary_certificate(smpk_priv, enc_field)
    for primary_cert_bytes in primary_cert_bytes_array:
        primary_cert = x509.load_der_x509_certificate(
            primary_cert_bytes, default_backend()
        )
        public_key = primary_cert.public_key()

        # Verify the certificate using the public key
        try:
            public_key.verify(
                primary_cert.signature,
                primary_cert.tbs_certificate_bytes,
                padding.PKCS1v15(),
                hashes.SHA512(),
            )
        except:
            assert False, "Certificate signature is invalid"

        # Verify the certificate using the Smkey Public Key
        try:
            serialization.load_der_public_key(smkey.get_public_key_der(), None).verify(
                primary_cert.signature,
                primary_cert.tbs_certificate_bytes,
                padding.PKCS1v15(),
                hashes.SHA512(),
            )
        except:
            assert False, "Certificate signature is invalid"


def test_build_secondary_certificate():
    # Generate a ManufacturerKeys object
    smkey = ManufacturerKeys()

    # Create a list of ManufacturerKeys objects
    smek = smkey.get_symmetric_key()
    smpk_priv = load_rsa_private_key(smkey.export_private_key())

    # Generate a Backup ManufacturerKeys object
    bmkey = ManufacturerKeys()

    # Create a list of Backup ManufacturerKeys objects
    bmek = bmkey.get_symmetric_key()
    bmpk_priv = load_rsa_private_key(bmkey.export_private_key())

    # Generate an AES key
    aes_key = os.urandom(32)

    # Create a new RSA key pair with a key size of 4096 bits
    key = rsa.generate_private_key(
        public_exponent=65537, key_size=4096, backend=default_backend()
    )
    # Get the public key in PEM format
    tifek_pub = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    # Set the MSV (Manufacturer Security Version)
    msv = 0x0c0ffe

    # Set the MPK flags
    mpk_flags = []

    # Set the MEK flags
    mek_flags = []
    enc_field = generate_encrypted_fields(
        [ManufacturerKeys(smek, smpk_priv), ManufacturerKeys(bmek, bmpk_priv)],
        aes_key,
        tifek_pub,
        msv,
        mpk_flags,
        mek_flags,
    )

    primary_certificate_array = build_primary_certificate(smpk_priv, enc_field)

    for primary_certificate in primary_certificate_array:

        # generate the secondary certificate signed with BMPK private key
        h = hash_data(primary_certificate)
        l = len(primary_certificate)
        secondary_certificate_bytes = build_secondary_certificate(bmpk_priv, h, l)
        secondary_certificate = x509.load_der_x509_certificate(
            secondary_certificate_bytes, default_backend()
        )
        public_key = secondary_certificate.public_key()

        # Verify the secondary certificate using the Bmkey Public Key

        try:
            serialization.load_der_public_key(bmkey.get_public_key_der()).verify(
                secondary_certificate.signature,
                secondary_certificate.tbs_certificate_bytes,
                padding.PKCS1v15(),
                hashes.SHA512(),
            )
        except:
            assert False, "Certificate signature is invalid"

        try:
            public_key.verify(
                secondary_certificate.signature,
                secondary_certificate.tbs_certificate_bytes,
                padding.PKCS1v15(),
                hashes.SHA512(),
            )
        except:
            assert False, "Certificate signature is invalid"


def test_verify_oids_and_encfields():
    # Generate a primary certificate
    smkey = ManufacturerKeys()
    smek = smkey.get_symmetric_key()
    smpk_priv = load_rsa_private_key(smkey.export_private_key())
    bmkey = ManufacturerKeys()
    bmek = bmkey.get_symmetric_key()
    bmpk_priv = load_rsa_private_key(bmkey.export_private_key())
    aes_key = gen_aes256_key().data
    key = rsa.generate_private_key(
        public_exponent=65537, key_size=4096, backend=default_backend()
    )
    tifek_pub = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    msv = 0x0c0ffe
    mpk_flags = []
    mek_flags = []
    enc_field = generate_encrypted_fields(
        [ManufacturerKeys(smek, smpk_priv), ManufacturerKeys(bmek, bmpk_priv)],
        aes_key,
        tifek_pub,
        msv,
        mpk_flags,
        mek_flags,
    )
    primary_cert_bytes_array = build_primary_certificate(smpk_priv, enc_field)

    for primary_cert_bytes in primary_cert_bytes_array:
        # Load the certificate
        primary_cert = x509.load_der_x509_certificate(
            primary_cert_bytes, default_backend()
        )

        custom_oids = [
            ("1.3.6.1.4.1.294.1.64", "enc_aes_key"),
            ("1.3.6.1.4.1.294.1.65", "enc_smpk_signed_aes_key"),
            ("1.3.6.1.4.1.294.1.66", "enc_bmpk_signed_aes_key"),
            ("1.3.6.1.4.1.294.1.67", "aesenc_smpkh"),
            ("1.3.6.1.4.1.294.1.68", "aesenc_smek"),
            ("1.3.6.1.4.1.294.1.69", "plain_mpk_options"),
            ("1.3.6.1.4.1.294.1.70", "aesenc_bmpkh"),
            ("1.3.6.1.4.1.294.1.71", "aesenc_bmek"),
            ("1.3.6.1.4.1.294.1.72", "plain_mek_options"),
            ("1.3.6.1.4.1.294.1.73", "aesenc_user_otp"),
            ("1.3.6.1.4.1.294.1.74", "plain_key_rev"),
            ("1.3.6.1.4.1.294.1.76", "plain_msv"),
            ("1.3.6.1.4.1.294.1.77", "plain_key_cnt"),
            ("1.3.6.1.4.1.294.1.78", "plain_swrev_sysfw"),
            ("1.3.6.1.4.1.294.1.79", "plain_swrev_sbl"),
            ("1.3.6.1.4.1.294.1.80", "plain_swrev_sec_brdcfg"),
            ("1.3.6.1.4.1.294.1.81", "plain_keywr_min_version"),
        ]
        # Iterate through all the oids and compare with encrypted fields
        for ext in primary_cert.extensions[1:]:
            x = ext.oid.dotted_string
            print(x)
            for element in custom_oids:
                if element[0] == x:
                    assert enc_field[element[1]] == ext.value.value


def test_verify_multishot_oids_and_encfields():
    # Generate a primary certificate
    smkey = ManufacturerKeys()
    smek = smkey.get_symmetric_key()
    smpk_priv = load_rsa_private_key(smkey.export_private_key())
    bmkey = ManufacturerKeys()
    bmek = bmkey.get_symmetric_key()
    bmpk_priv = load_rsa_private_key(bmkey.export_private_key())
    aes_key = gen_aes256_key().data
    key = rsa.generate_private_key(
        public_exponent=65537, key_size=4096, backend=default_backend()
    )
    tifek_pub = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    msv = 0x0c0ffe
    mpk_flags = []
    mek_flags = []
    enc_field = generate_encrypted_fields(
        [ManufacturerKeys(smek, smpk_priv), ManufacturerKeys(bmek, bmpk_priv)],
        aes_key,
        tifek_pub,
        msv,
        mpk_flags,
        mek_flags,
    )

    # multishot
    multi = True

    primary_cert_bytes_array = build_primary_certificate(smpk_priv, enc_field, multi)

    for index, primary_cert_bytes in enumerate(primary_cert_bytes_array):
        # Load the certificate
        primary_cert = x509.load_der_x509_certificate(
            primary_cert_bytes, default_backend()
        )

        custom_oids_1 = [
            ("1.3.6.1.4.1.294.1.64", "enc_aes_key"),
            ("1.3.6.1.4.1.294.1.65", "enc_smpk_signed_aes_key"),
        ]

        custom_oids_2 = [
            ("1.3.6.1.4.1.294.1.66", "enc_bmpk_signed_aes_key"),
            ("1.3.6.1.4.1.294.1.69", "plain_mpk_options"),
            ("1.3.6.1.4.1.294.1.72", "plain_mek_options"),
        ]

        custom_oids_3 = [
            ("1.3.6.1.4.1.294.1.67", "aesenc_smpkh"),
            ("1.3.6.1.4.1.294.1.68", "aesenc_smek"),
            ("1.3.6.1.4.1.294.1.70", "aesenc_bmpkh"),
            ("1.3.6.1.4.1.294.1.71", "aesenc_bmek"),
            ("1.3.6.1.4.1.294.1.73", "aesenc_user_otp"),
            ("1.3.6.1.4.1.294.1.74", "plain_key_rev"),
            ("1.3.6.1.4.1.294.1.76", "plain_msv"),
            ("1.3.6.1.4.1.294.1.77", "plain_key_cnt"),
            ("1.3.6.1.4.1.294.1.78", "plain_swrev_sysfw"),
            ("1.3.6.1.4.1.294.1.79", "plain_swrev_sbl"),
            ("1.3.6.1.4.1.294.1.80", "plain_swrev_sec_brdcfg"),
            ("1.3.6.1.4.1.294.1.81", "plain_keywr_min_version"),
        ]
        oids = [custom_oids_1, custom_oids_2, custom_oids_3]

        # Iterate through all the oids and compare with encrypted fields
        for ext in primary_cert.extensions[1:]:
            x = ext.oid.dotted_string
            print(x)
            for element in oids[index]:
                if element[0] == x:
                    assert enc_field[element[1]] == ext.value.value


def test_asn1_aes_enc_key():
    # Test with a sample AES key
    aes_key = b"\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10"
    encoded_key = asn1_enc_aes_key(aes_key)

    # Decode the encoded key to verify its contents
    decoded_key = KeywriterSequence.load(encoded_key)

    # Check if the decoded value matches the original key
    assert decoded_key["val"].native == aes_key
    assert decoded_key["size"].native == len(aes_key)


def test_asn1_aes_enc_key_empty():
    # Test with an empty AES key
    aes_key = b""
    encoded_key = asn1_enc_aes_key(aes_key)

    # Decode the encoded key to verify its contents
    decoded_key = KeywriterSequence.load(encoded_key)

    # Check if the decoded value matches the original key
    assert decoded_key["val"].native == aes_key
    assert decoded_key["size"].native == len(aes_key)


def test_asn1_aes_enc_key_large():
    # Test with a large AES key
    aes_key = b"\x01" * 1024
    encoded_key = asn1_enc_aes_key(aes_key)

    # Decode the encoded key to verify its contents
    decoded_key = KeywriterSequence.load(encoded_key)

    # Check if the decoded value matches the original key
    assert decoded_key["val"].native == aes_key
    assert decoded_key["size"].native == len(aes_key)


def test_asn1_aes_enc_key_encoding():
    s = "308202080482020071623CFA38358BB23D0BF64C4676971B343742C2988398E3CD1610BE5D6940C81F636FAE0887B534B92376D301E5E402F9129D2426376DAED2F337FEAFEE8782B1D1E82E40F1A9B9DF7E6B6D1DDD688BA01A28E233AB05774DCD4CA9AD37F2CDE51C2C98BC32E820987A49ED6F225DC8963D5A9E9400ACD07946FEC5946552B35102B865C2EB4793FBFE68B0848886DB71CAB9C9BE5E68A5A3F1C93ACA21CD85C0374DCCAEC6F337FFEE5F6799EE889CFEDB1F73D34251B3F86CCBC9DB49F13D64DF7063F95B1100EFABA375A4391FA7D0C4CAF3DF7371EF424DC37AF18C5FD9F7C4D76661D18AAB86AB86717A61E4B8064D97D668B8CE2F9111C3EEBA477B19283330A56A732621B986FD18FC43A30D0EC6C7DA58587AB8845F30C78F4839E6D78F01B8DD828842AF59D4E8689D9B9186799974736B9E0409F57D917124D61934770FAE966E90380DFDE0DDD85DFA6C890626BDD3FFE5E414CA64BD74F2DF19430E25A0AC6C794D87E1CA5647CCFBE77D66F0A62CB7849CF9C6474B691DB617AB71333F08CC4CBA8A37CD8A0F0BEDD88A4C57A7B87386669D0CAAD4C96BEE64C5D2E0E04DEDC4E891E890B5D18B2EAE27C940D39249323F24B782847D92DB1D4C0861ACEC82DFE6C2F2937D164F06E88059D8CB3EE948E5D2F2E15EA431EF4A0660EE96DC30828BD82F6A8892467D04B8AA1B20C6F178D164ED7BABCC75E5E902020200"
    s_bytes = bytes.fromhex(s)
    obj = KeywriterSequence.load(s_bytes)
    assert obj["size"].native == 512
    assert (obj["val"].native) == bytes.fromhex(
        "71623CFA38358BB23D0BF64C4676971B343742C2988398E3CD1610BE5D6940C81F636FAE0887B534B92376D301E5E402F9129D2426376DAED2F337FEAFEE8782B1D1E82E40F1A9B9DF7E6B6D1DDD688BA01A28E233AB05774DCD4CA9AD37F2CDE51C2C98BC32E820987A49ED6F225DC8963D5A9E9400ACD07946FEC5946552B35102B865C2EB4793FBFE68B0848886DB71CAB9C9BE5E68A5A3F1C93ACA21CD85C0374DCCAEC6F337FFEE5F6799EE889CFEDB1F73D34251B3F86CCBC9DB49F13D64DF7063F95B1100EFABA375A4391FA7D0C4CAF3DF7371EF424DC37AF18C5FD9F7C4D76661D18AAB86AB86717A61E4B8064D97D668B8CE2F9111C3EEBA477B19283330A56A732621B986FD18FC43A30D0EC6C7DA58587AB8845F30C78F4839E6D78F01B8DD828842AF59D4E8689D9B9186799974736B9E0409F57D917124D61934770FAE966E90380DFDE0DDD85DFA6C890626BDD3FFE5E414CA64BD74F2DF19430E25A0AC6C794D87E1CA5647CCFBE77D66F0A62CB7849CF9C6474B691DB617AB71333F08CC4CBA8A37CD8A0F0BEDD88A4C57A7B87386669D0CAAD4C96BEE64C5D2E0E04DEDC4E891E890B5D18B2EAE27C940D39249323F24B782847D92DB1D4C0861ACEC82DFE6C2F2937D164F06E88059D8CB3EE948E5D2F2E15EA431EF4A0660EE96DC30828BD82F6A8892467D04B8AA1B20C6F178D164ED7BABCC75E5E9"
    )


def test_embed_and_verify_aes_key():
    # Generate an AES key
    aes_key = gen_aes256_key().data

    # Create a new RSA key pair for TIFEK
    tifek_priv = rsa.generate_private_key(
        public_exponent=65537, key_size=4096, backend=default_backend()
    )

    tifek_pub = tifek_priv.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    # Generate ManufacturerKeys objects
    smkey = ManufacturerKeys()
    smek = smkey.get_symmetric_key()
    smpk_priv = load_rsa_private_key(smkey.export_private_key())

    bmkey = ManufacturerKeys()
    bmek = bmkey.get_symmetric_key()
    bmpk_priv = load_rsa_private_key(bmkey.export_private_key())

    # Set the MSV, MPK flags, and MEK flags
    msv = 0x0c0ffe
    mpk_flags = []
    mek_flags = []

    # Generate encrypted fields
    enc_field = generate_encrypted_fields(
        [ManufacturerKeys(smek, smpk_priv), ManufacturerKeys(bmek, bmpk_priv)],
        aes_key,
        tifek_pub,
        msv,
        mpk_flags,
        mek_flags,
    )

    # Build the primary certificate
    primary_cert_bytes_array = build_primary_certificate(smpk_priv, enc_field)

    for primary_cert_bytes in primary_cert_bytes_array:
        # Load the certificate
        primary_cert = x509.load_der_x509_certificate(
            primary_cert_bytes, default_backend()
        )

        # Extract the DER encoded bytes corresponding to the OID of enc_aes_key
        oid_enc_aes_key_pair = KeywriterSequence.load(
            primary_cert.extensions[1].value.value
        )

        # Decrypt the extracted bytes using the TIFEK private key
        decrypted_aes_key = rsa_decrypt_with_pkcs15_padding(
            oid_enc_aes_key_pair["val"].native,
            tifek_priv.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            ),
        )

        # Verify that the decrypted AES key matches the original AES key
        assert (
            decrypted_aes_key == aes_key
        ), "Decrypted AES key does not match the original AES key"
