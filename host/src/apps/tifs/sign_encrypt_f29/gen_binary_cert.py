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
from typing import Dict, Union
import subprocess

from tisecprov.encryption_ops import encrypt_binary_raw, PaddingByte

from asn1crypto.core import Sequence, Integer, OctetString, ObjectIdentifier
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives.asymmetric import rsa, ec

from tisecprov.cryptoutils import (
    hash_data,
)
from tisecprov.crypto_interfaces import SigningAlgorithm

fields: Dict[str,int] = {}

g_dbg_types = {
    "DBG_PERM_DISABLE": 0,
    "DBG_SOC_DEFAULT": 1,
    "DBG_PUBLIC_ENABLE": 2,
    "DBG_FULL_ENABLE": 4,
}

g_core_types = {
    "R5": '0',
    "HSM": '1',
    "C29": '2',
}

g_enc_unlock_types = {
    "LOCK": '90',
    "UNLOCK": '165',
}

class swrevseq(Sequence):
    _fields = [
        ("swrv", Integer),
    ]

def asn1_swrev_seq(swrv: Integer) -> bytes:
    """
    Encode the image integrity field using ASN.1
    """
    swrvsq = swrevseq(
        {
            "swrv": swrv,
        }
    )
    return swrvsq.dump()

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

class DebugSeq(Sequence):
    _fields = [
        ("debugUID", OctetString),
        ("debugType", Integer),
        ("coreDbgEn", Integer),
        ("coreDbgSecEn", Integer),
    ]

def asn1_encode_dbg_seq(dbg_device:OctetString, dbg_type: int ) -> bytes:
    """
    Encode the image integrity field using ASN.1
    """
    dbg_seq = DebugSeq(
        {
            "debugUID"  :dbg_device,
            "debugType" :dbg_type,
            "coreDbgEn" :0,
            "coreDbgSecEn" :0
        }
    )
    return dbg_seq.dump()

class kdsaltseq(Sequence):
    _fields = [
        ("kd_salt", OctetString),
    ]

def asn1_encode_kd_seq(kd_salt: OctetString) -> bytes:
    """
    Encode the image integrity field using ASN.1
    """
    kd_seq = kdsaltseq(
        {
            "kd_salt": kd_salt,
        }
    )
    return kd_seq.dump()


class cryptounlockseq(Sequence):
    _fields = [
        ("CryptoUnlockValue", Integer),
    ]


def asn1_encode_crypto_unlock_seq(crypto_unlock: Integer) -> bytes:
    """
    Encode the image integrity field using ASN.1
    """
    crypto_unlock_seq = cryptounlockseq(
        {
            "CryptoUnlockValue": crypto_unlock,
        }
    )
    return crypto_unlock_seq.dump()

class extenc(Sequence):
    _fields = [
        ("Iv", OctetString),
        ("Rstring", OctetString),
        ("Icount", Integer),
        ("Salt", OctetString),
    ]

def asn1_encode_ext_enc(iv_string:OctetString, r_string: OctetString, I_count: int, salt: OctetString ) -> bytes:
    """
    Encode the image integrity field using ASN.1
    """
    ext_enc = extenc(
        {
            "Iv"  :iv_string,
            "Rstring" :r_string,
            "Icount" :I_count,
            "Salt" :salt
        }
    )
    return ext_enc.dump()

class fwencseq(Sequence):
    _fields = [
        ("Iv", OctetString),
        ("Icount", Integer),
        ("Salt", OctetString),
    ]

def asn1_encode_fw_enc(iv_string:OctetString, I_count: int, salt: OctetString ) -> bytes:
    """
    Encode the firmware encryption field using ASN.1
    """
    fw_enc = fwencseq(
        {
            "Iv"  :iv_string,
            "Icount" :I_count,
            "Salt" :salt
        }
    )
    return fw_enc.dump()

class FwEncImageIntegrity(Sequence):
    _fields = [
        ("shaType", ObjectIdentifier),
        ("shaValue", OctetString),
        ("imageSize", Integer),
    ]

def asn1_encode_fw_enc_image_integrity(sha512_hash: bytes, image_size: int) -> bytes:
    """
    Encode the firmware encrypted image integrity field using ASN.1
    """
    fw_enc_image_integrity = FwEncImageIntegrity(
        {
            "shaType": "2.16.840.1.101.3.4.2.3",
            "shaValue": sha512_hash,
            "imageSize": image_size,
        }
    )
    return fw_enc_image_integrity.dump()

def get_enc_filename(fname):
    return fname+"-enc"

def get_encrypted_file_iv_rs(kd_salt, bin_file_name, enc_key):
    """Encrypt a binary with zero-padding, R-string, and optional HKDF key derivation.

    Used for SBL and TIFS encryption modes. Always pads to block alignment
    (even when already aligned) via force_pad=True.
    """
    if (enc_key is None) or (not os.path.exists(enc_key)):
        print("ERROR: Please give the key to be used for encryption. It's either missing or file not found!")
        exit(1)

    with open(enc_key, "rb") as f:
        key_bytes = f.read()

    salt = None
    if kd_salt is not None:
        salt_hex = get_key_derivation_salt(kd_salt)
        salt = bytes.fromhex(salt_hex)

    with open(bin_file_name, "rb") as f:
        plaintext = f.read()

    result = encrypt_binary_raw(
        plaintext=plaintext,
        key=key_bytes,
        padding_mode=PaddingByte.ZERO,
        salt=salt,
        include_r_string=True,
        force_pad=True,
    )

    encbin_name = get_enc_filename(bin_file_name)
    with open(encbin_name, 'wb') as f:
        f.write(result.ciphertext)

    enc_iv_hex = result.iv.hex()
    enc_rs_hex = result.r_string.hex()

    return encbin_name, enc_iv_hex, enc_rs_hex

def get_encrypted_file_iv(kd_salt, bin_file_name, enc_key):
    """Encrypt a binary with FF-padding and optional HKDF key derivation.

    Used for firmware encryption mode. Only pads when data is not aligned
    (force_pad=False, the default).
    """
    if (enc_key is None) or (not os.path.exists(enc_key)):
        print("ERROR: Please give the key to be used for firmware encryption. It's either missing or file not found!")
        exit(1)

    with open(enc_key, "rb") as f:
        key_bytes = f.read()

    salt = None
    if kd_salt is not None:
        salt_hex = get_key_derivation_salt(kd_salt)
        salt = bytes.fromhex(salt_hex)

    with open(bin_file_name, "rb") as f:
        plaintext = f.read()

    result = encrypt_binary_raw(
        plaintext=plaintext,
        key=key_bytes,
        padding_mode=PaddingByte.FF,
        salt=salt,
        include_r_string=False,
        force_pad=False,
    )

    encbin_name = get_enc_filename(bin_file_name)
    with open(encbin_name, 'wb') as f:
        f.write(result.ciphertext)

    enc_iv_hex = result.iv.hex()

    return encbin_name, enc_iv_hex

def get_key_derivation_salt(kd_salt_file_name):
    if(not os.path.exists(kd_salt_file_name)):
        # Error, key derivation salt has to be given
        print("Please give the key derivation salt file name. It's either missing or file not found!")
        exit(1)
    else:
        kd_salt = None
        with open(kd_salt_file_name, "r") as f:
            kd_salt = f.read()
            kd_salt = kd_salt.strip('\n')

    return kd_salt

def create_fields(args):
    fields: Dict[str, bytes] = {}
    image_bin_name = args.image_bin
    original_image_bin_name = args.image_bin
    swrev = int(args.swrv)

    if(swrev is None):
        swrev = 1

    sbl_enc_enabled = hasattr(args, 'sbl_enc') and args.sbl_enc
    tifs_enc_enabled = hasattr(args, 'tifs_enc') and args.tifs_enc
    fw_enc_enabled = hasattr(args, 'fw_enc') and args.fw_enc

    encryption_count = sum([sbl_enc_enabled, tifs_enc_enabled, fw_enc_enabled])

    if encryption_count > 1:
        print("ERROR: Multiple encryption types specified. Only one encryption method can be used at a time.")
        exit(1)

    if(args.core != None):
        if(args.core == 'R5'):
            bootAddress = 0
            bootCore_id = 16
            certType = 1
            bootCoreOptions = 0
        elif(((args.device == 'f29h85x') or (args.device == 'f29p32x')) and (args.core == 'C29') and (args.fw_type != 'SEC_CFG_CPU1') 
             and (args.fw_type != 'SEC_CFG_CPU2') and (args.fw_type != 'SEC_CFG_CPU3') and (args.fw_type != 'CPU3')and (args.fw_type != 'CPU1_APP')):
            bootAddress = 0
            bootCore_id = 16
            certType = 1
            bootCoreOptions = 0
        elif(((args.device == 'f29h85x') or (args.device == 'f29p32x')) and (args.core == 'C29') and (args.fw_type == 'SEC_CFG_CPU1')):
            bootAddress = 0
            bootCore_id = 16
            certType = 3
            bootCoreOptions = 0
        elif(((args.device == 'f29h85x') or (args.device == 'f29p32x')) and (args.core == 'C29') and (args.fw_type == 'SEC_CFG_CPU2')):
            bootAddress = 0
            bootCore_id = 16
            certType = 5
            bootCoreOptions = 0
        elif(((args.device == 'f29h85x') or (args.device == 'f29p32x')) and (args.core == 'C29') and (args.fw_type == 'SEC_CFG_CPU3')):
            bootAddress = 0
            bootCore_id = 16
            certType = 6
            bootCoreOptions = 0
        elif((args.device == 'f29h85x') and (args.core == 'C29') and (args.fw_type == 'CPU3')):
            bootAddress = 0
            bootCore_id = 16
            certType = 4
            bootCoreOptions = 0
        elif(((args.device == 'f29h85x') or (args.device == 'f29p32x')) and (args.core == 'C29') and (args.fw_type == 'CPU1_APP')):
            bootAddress = 0
            bootCore_id = 16
            certType = 7
            bootCoreOptions = 0
        else:
            bootAddress = 0
            bootCore_id = 0
            certType = 2
            bootCoreOptions = 0

    if (hasattr(args, 'fw_enc') and args.fw_enc and ((args.device == 'f29h85x') or (args.device == 'f29p32x')) and args.boot == 'FLASH'):
        fw_enc_iter_count = 0
        fw_enc_salt = '0000'
        if hasattr(args, 'kd_salt') and args.kd_salt:
            fw_enc_iter_count = 1
            fw_enc_salt = get_key_derivation_salt(args.kd_salt)

    if (hasattr(args, 'sbl_enc') and args.sbl_enc) or (hasattr(args, 'tifs_enc') and args.tifs_enc):
        enc_iter_count = 0
        enc_salt = '0000'
        if hasattr(args, 'kd_salt') and args.kd_salt:
            enc_iter_count = 1
            enc_salt = get_key_derivation_salt(args.kd_salt)
        else:
            enc_iter_count = 0
            enc_salt = '0000'

    if hasattr(args, 'sbl_enc') and args.sbl_enc:
        encsbl_name, enc_iv, enc_rs = get_encrypted_file_iv_rs(args.kd_salt if hasattr(args, 'kd_salt') else None,
            args.image_bin, args.enc_key)
        enc_iv_bytes = bytes.fromhex(enc_iv)
        enc_rs_bytes = bytes.fromhex(enc_rs)
        enc_salt_bytes = bytes.fromhex(enc_salt)
        fields['ext_enc_seq'] = asn1_encode_ext_enc(enc_iv_bytes, enc_rs_bytes, enc_iter_count, enc_salt_bytes)
        image_bin_name = encsbl_name
    elif hasattr(args, 'tifs_enc') and args.tifs_enc:
        enctifs_name, enc_iv, enc_rs = get_encrypted_file_iv_rs(args.kd_salt if hasattr(args, 'kd_salt') else None,
            args.image_bin, args.enc_key)
        enc_iv_bytes = bytes.fromhex(enc_iv)
        enc_rs_bytes = bytes.fromhex(enc_rs)
        enc_salt_bytes = bytes.fromhex(enc_salt)
        fields['ext_enc_seq'] = asn1_encode_ext_enc(enc_iv_bytes, enc_rs_bytes, enc_iter_count, enc_salt_bytes)
        image_bin_name = enctifs_name

    try:
        with open(image_bin_name, "rb") as binary_file:
            binary_image = binary_file.read()
    except FileNotFoundError:
        print(f"Error: The file {image_bin_name} was not found.")
        exit(1)
    except Exception as e:
        print(f"An error occurred: {e}")
        exit(1)

    fields['img_int_seq'] = asn1_encode_image_integrity(hash_data(binary_image))

    if hasattr(args, 'kd_salt') and args.kd_salt and ((hasattr(args, 'sbl_enc') and args.sbl_enc) or (hasattr(args, 'fw_enc') and args.fw_enc and args.boot == 'FLASH')):
        kd_salt = get_key_derivation_salt(args.kd_salt)
        kd_salt_bytes = bytes.fromhex(kd_salt)
        fields['kd_ext'] = asn1_encode_kd_seq(kd_salt_bytes)

    if hasattr(args, 'fw_enc') and args.fw_enc and ((args.device == 'f29h85x') or (args.device == 'f29p32x')) and args.boot == 'FLASH':
        if (hasattr(args, 'sbl_enc') and args.sbl_enc) or (hasattr(args, 'tifs_enc') and args.tifs_enc):
            print("WARNING: Both sbl_enc/tifs_enc and fw_enc are enabled. Only fw_enc will be applied.")
            if 'ext_enc_seq' in fields:
                del fields['ext_enc_seq']

        encfw_name, fw_enc_iv = get_encrypted_file_iv(args.kd_salt if hasattr(args, 'kd_salt') else None,
            args.image_bin, args.fw_enc_key)
        fw_enc_iv_bytes = bytes.fromhex(fw_enc_iv)
        fw_enc_salt_bytes = bytes.fromhex(fw_enc_salt)
        fields['fw_enc_seq'] = asn1_encode_fw_enc(fw_enc_iv_bytes, fw_enc_iter_count, fw_enc_salt_bytes)
        image_bin_name = encfw_name

        with open(image_bin_name, "rb") as fw_enc_file:
            fw_enc_binary = fw_enc_file.read()
        fields['fw_enc_img_int'] = asn1_encode_fw_enc_image_integrity(hash_data(fw_enc_binary), os.path.getsize(image_bin_name))

    boot_addr = int(args.loadaddr, 16).to_bytes(4, 'big')
    if args.core == 'HSM' and hasattr(args, 'fw_enc') and args.fw_enc:
        boot_seq_image_size = os.path.getsize(original_image_bin_name)
    else:
        boot_seq_image_size = os.path.getsize(image_bin_name)
    fields['boot_seq'] = asn1_encode_boot_seq(certType,bootCore_id,bootCoreOptions,boot_addr ,boot_seq_image_size)

    fields['swrv'] = asn1_swrev_seq(swrev)

    if(args.debug is not None):
        if(args.debug in g_dbg_types):
            uid = (int('00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000',16))

            fields['dbg_ext'] = asn1_encode_dbg_seq(uid.to_bytes(64, byteorder='big'),
                                                    g_dbg_types[args.debug])
        else:
            print("ERROR: Invalid debug extension, exiting ...")
            exit(2)


    if((args.crypto_unlock.lower()) == 'yes'):
        fields['crypto_unlock_ext'] = asn1_encode_crypto_unlock_seq(195)

    return fields, image_bin_name



def build_hsm_firmware_cert(
    args,
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
        ("1.3.6.1.4.1.294.1.3", "swrv")
    ]

    if "img_int_seq" in fields.keys():
        custom_oids.append(("1.3.6.1.4.1.294.1.2", "img_int_seq"))
    if "ext_enc_seq" in fields.keys():
        custom_oids.append(("1.3.6.1.4.1.294.1.4", "ext_enc_seq"))
    if "kd_ext" in fields.keys():
        custom_oids.append(("1.3.6.1.4.1.294.1.5", "kd_ext"))
    if "dbg_ext" in fields.keys():
        custom_oids.append(("1.3.6.1.4.1.294.1.8", "dbg_ext"))
    if "crypto_unlock_ext" in fields.keys():
        custom_oids.append(("1.3.6.1.4.1.294.1.12", "crypto_unlock_ext"))
    if "fw_enc_seq" in fields.keys():
        custom_oids.append(("1.3.6.1.4.1.294.1.13", "fw_enc_seq"))
    if "fw_enc_img_int" in fields.keys():
        custom_oids.append(("1.3.6.1.4.1.294.1.14", "fw_enc_img_int"))
    
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

    final_cert = certificate.public_bytes(serialization.Encoding.DER)

    if args.boot == "FLASH" or args.core == "HSM":
        if ((args.fw_type != "SEC_CFG_CPU1") and (args.fw_type != "SEC_CFG_CPU2") and (args.fw_type != "SEC_CFG_CPU3")):
            desired_size = 4096  # 4Kb
        else :
            desired_size = 2048  # 2Kb

        if len(final_cert) < desired_size:
                zeros_to_append = desired_size - len(final_cert)
                final_cert += b'\x00' * zeros_to_append
            
    return final_cert
