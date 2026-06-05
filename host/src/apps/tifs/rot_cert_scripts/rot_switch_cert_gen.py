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
Root of Trust Switching X509 certificate generation module
"""
"""
rot_switch_cert_gen.py

This module generates an x509 certificate signed using both SPMK and BMPK to enable RoT Switching

It uses various utilities and helper functions to parse command-line arguments,
validate input data/key material, and generate the necessary cryptographic components.

Contents may be hashed, encrypted and put into the x509 as part of the extensions
which are then parsed, validated and programmed.
"""

import sys
import os
from tisecprov.certgen import *
from tisecprov.session import SecureSession
from tisecprov.crypto_selector import get_crypto_backend
import datetime
from typing import List, Dict, Union
from pathlib import Path

from asn1crypto.core import Sequence, Integer, OctetString, ObjectIdentifier
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives.asymmetric import rsa, ec

from tisecprov.cryptoutils import (
    hash_data
)
from tisecprov.crypto_interfaces import SigningAlgorithm

fields: Dict[str,int] = {}

class ImageIntegrity(Sequence):
    _fields = [
        ("shaType", ObjectIdentifier),
        ("shaValue", OctetString),
    ]

def asn1_encode_image_integrity(sha512_hash: bytes) -> bytes:
    """
    Encode the image integrity field using ASN.1
    """
    image_integrity = ImageIntegrity(
        {
            "shaType": "2.16.840.1.101.3.4.2.3",
            "shaValue": sha512_hash,
        }
    )
    return image_integrity.dump()


class BootSeq(Sequence):
    _fields = [
        ("certType", Integer),
        ("bootCore", Integer),
        ("bootCoreOpts", Integer),
        ("destAddr", OctetString),
        ("imageSize", Integer),
    ]

def asn1_encode_boot_seq(cert_type:int, boot_core_Id:int, boot_core_opt:int, dest_addr: OctetString, cert_length: int) -> bytes:
    """
    Encode the boot sequence field using ASN.1
    """
    boot_seq = BootSeq(
        {
            "certType": cert_type,
            "bootCore": boot_core_Id,
            "bootCoreOpts": boot_core_opt,
            "destAddr": dest_addr,
            "imageSize": cert_length,
        }
    )
    return boot_seq.dump()

def create_fields_rot(certType, image: bytes = None ):

    boot_addr = int('0x00000000', 16).to_bytes(4, 'big')
    if certType == "inner":
        certVal = 0xA5000005
        fields['boot_seq'] = asn1_encode_boot_seq(certVal,0,0,boot_addr,0)
    else:
        certVal = 0xA5000006
        fields['boot_seq'] = asn1_encode_boot_seq(certVal,0,0,boot_addr,len(image))
        fields['img_int_seq'] = asn1_encode_image_integrity(hash_data(image))

    return fields



def build_hsm_rot_cert(
    signing_key: Union[rsa.RSAPrivateKey, ec.SECP256R1, ec.SECP384R1, ec.SECP521R1, ec.BrainpoolP512R1],
    fields: Dict[str, bytes],
    signing_algorithm: SigningAlgorithm = SigningAlgorithm.PKCS1_V15,
) -> bytes:
    """
    Given the OIDs and the asn1 encoded fields, create the signed
    primary certificate.  If multi is true, then a list containing
    three signed certificates are generated, else the list contains
    one signed certificate.
    """
    builder = x509.CertificateBuilder()

    subject = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "SC"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "New York"),
            x509.NameAttribute(
                NameOID.ORGANIZATION_NAME, "Texas Instruments., Inc."
            ),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "SITARA MCU"),
            x509.NameAttribute(NameOID.COMMON_NAME, "Albert"),
            x509.NameAttribute(
                NameOID.EMAIL_ADDRESS, "Albert@gt.ti.com"
            ),
        ]
    )
    issuer = subject

    builder = builder.subject_name(subject)
    builder = builder.issuer_name(issuer)

    # certificates should have a serial number
    builder = builder.serial_number(x509.random_serial_number())

    # set validity
    one_day = datetime.timedelta(1, 0, 0)
    builder = builder.not_valid_before(datetime.datetime.today())
    # make it valid till one month after certificate creation (As followed in the original keywriter gencert code)
    builder = builder.not_valid_after(datetime.datetime.today() + (30 * one_day))

    # signing key should be of type rsa.RSAPrivateKey
    # assert isinstance(signing_key, RSAPrivateKey) is True
    pub_key = signing_key.public_key()
    builder = builder.public_key(pub_key)

    builder = builder.add_extension(
        x509.BasicConstraints(ca=True, path_length=None),
        critical=False,
    )

    # builder_without_enc = builder
    # Custom OIDs and extensions
    
    custom_oids = [
        ("1.3.6.1.4.1.294.1.1", "boot_seq"),
    ]

    if "img_int_seq" in fields.keys():
        custom_oids.append(("1.3.6.1.4.1.294.1.2", "img_int_seq"))
    
    oids = [custom_oids]

    for custom_oids in oids:
        for oid, name in custom_oids:
            # look up the name in fields
            if name in fields:
                builder = builder.add_extension(
                    x509.UnrecognizedExtension(
                        x509.ObjectIdentifier(oid), fields[name]
                    ),
                    critical=False,
                )
            else:
                raise ValueError(f"Missing field {name} corresponding to oid {oid}")

    # sign the certificate and append to array
    padding_scheme = None
    if signing_algorithm == SigningAlgorithm.PKCS1_V15:
        padding_scheme = padding.PKCS1v15()
    elif signing_algorithm == SigningAlgorithm.RSA_SSA_PSS:
        padding_scheme = padding.PSS(
            mgf=padding.MGF1(hashes.SHA512()),
            salt_length=padding.PSS.MAX_LENGTH,
        )

    print(f"primary cert: signing with {signing_algorithm}")

    # # Add Subject Key Identifier extension
    # builder = builder.add_extension(
    #     x509.SubjectKeyIdentifier.from_public_key(pub_key), critical=False
    # )

    certificate = (
        builder.sign(
            private_key=signing_key,
            algorithm=hashes.SHA512(),
            rsa_padding=padding_scheme,
        )
    )

    return certificate.public_bytes(serialization.Encoding.DER)

def set_output_path(device = 'temp'):
    # Use os.path.expanduser to get home directory cross-platform
    home = os.path.expanduser("~")
    output_path = Path(home, "ti", device + "/rot_cert/")
    return output_path

def parseRoTCert(subparser):
    pass
    parser = subparser.add_parser(
        "rotcert",
        help="Sign an Application",
        description="Sign an Application using SMPK/BMPK Private Key",
    )
    parser.add_argument("--rot_output", help="Output Directory", type=Path)
    parser.add_argument(
        "-hsm",
        "--hsm",
        action="store_true",
        help="Use HSM Device to access the keys",
    )

def gen_rot_cert(args) -> None:
    """
    Processes command-line arguments and updates global dictionaries accordingly.

    This function processes the command-line arguments provided to the script,
    validates them, and signs an object file with specified private key and generates an x509 certificate.
    It also handles errors and logs messages as needed.

    Parameters
    ----------
    args : argparse.Namespace
        The parsed command-line arguments.

    Returns
    -------
    None
    """
    output_path: str = ""
    if not args.rot_output:
        output_path = set_output_path(str(args.device))
    else:
        output_path = args.rot_output

    crypto_backend = get_crypto_backend(use_hsm=args.hsm)

    secure_session = SecureSession(use_hsm=args.hsm)

    with secure_session as s:
        print(f"opening session: {args.session}")
        _session = s.open_session(args.session, args.password)
        keys = s.get_manufacturer_keys(crypto_backend)

        smpk_key, smpk_signing_algorithm = keys[0].get_signing_key()
        bmpk_key, bmpk_signing_algorithm = keys[1].get_signing_key()

        inner_cert_fields = create_fields_rot("inner", None)
        inner_cert = build_hsm_rot_cert(smpk_key, inner_cert_fields, smpk_signing_algorithm)

        outer_cert_fields = create_fields_rot("outer", inner_cert)
        outer_cert = build_hsm_rot_cert(bmpk_key, outer_cert_fields, bmpk_signing_algorithm)

    print(f"writing certificates into {output_path}")
    temp_dir_path = output_path
    temp_dir_path.mkdir(parents=True, exist_ok=True)
    with open(temp_dir_path / "rot_switching.cert", "wb") as f:
        f.write(outer_cert)
        f.write(inner_cert)

    # with open(temp_dir_path / "inner_cert.cert", "wb") as f:
    #     f.write(inner_cert)

    # with open(temp_dir_path / "outer_cert.cert", "wb") as f:
    #     f.write(outer_cert)
