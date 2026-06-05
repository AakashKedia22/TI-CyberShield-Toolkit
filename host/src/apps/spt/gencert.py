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
module that deals with taking user inputs for generating the
certificate via the tisecprov.certgen
"""

import argparse
import sys
import os
import tempfile
import platform
from pathlib import Path
from typing import Dict, List, Optional, Union

# Import platform utilities if available
try:
    from apps.qtgui.utils.platform_utils import IS_WINDOWS, IS_LINUX, IS_MACOS
    PLATFORM_UTILS_AVAILABLE = True
except ImportError:
    # Fallback to direct platform detection if platform_utils is not available
    IS_WINDOWS = platform.system() == 'Windows'
    IS_LINUX = platform.system() == 'Linux'
    IS_MACOS = platform.system() == 'Darwin'
    PLATFORM_UTILS_AVAILABLE = False

from tisecprov.session import SecureSession
from tisecprov.crypto import gen_aes256_key
from tisecprov.cryptoutils import hash_data
from tisecprov.devel import get_tifek_pub, get_output_path
from tisecprov.crypto_selector import get_crypto_backend
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey

from tisecprov import certgen as certgen_core
from tisecprov.certgen import SigningAlgorithm
from tisecprov.device_config import (
    CertificateRequest,
    ExtendedOTPData,
    FieldFlags,
    get_device_config,
)
from tisecprov.util.bin2c import generate_c_header

ENABLE_FLAG = "5A"
DISABLE_FLAG = "A5"

tifek_pub_def = get_tifek_pub()
output_path = get_output_path()


def gencert_args(subparsers: argparse._SubParsersAction) -> None:
    """
    arguments for gencert sub-command
    """
    gencert_parser = subparsers.add_parser(
        "gencert",
        help="Generate an x.509 certificate",
        description="Generate x.509 certificate for the given options",
    )

    gencert_parser.add_argument(
        "-s", "--session", required=True, type=str, help="Open the session"
    )
    gencert_parser.add_argument(
        "-p",
        "--password",
        required=True,
        type=str,
        help="Password to unlock the session",
    )
    gencert_parser.add_argument(
        "--msv", default="0x00000", type=str, help="Manufacturer Specific Value (MSV)"
    )
    gencert_parser.add_argument(
        "--mpk-options",
        default="active",
        type=str,
        help="Comma separated MPK options",
    )
    gencert_parser.add_argument(
        "--mek-options",
        default="active",
        type=str,
        help="Comma separated MEK options",
    )
    gencert_parser.add_argument(
        "--signing-algorithm",
        default="rsa-pkcs1v1.5",
        choices=["rsa-pss", "rsa-pkcs1v1.5"],
        type=str,
        help="RSA Signing Algorithm to use",
    )
    gencert_parser.add_argument(
        "-multishot",
        "--multishot",
        action="store_true",
        help="Use Multi Shot Certificate Generation",
    )
    gencert_parser.add_argument(
        "-hsm",
        "--hsm",
        action="store_true",
        help="Use HSM Device to access the keys",
    )
    gencert_parser.add_argument(
        "-o", "--output", default=output_path, help="Output Directory", type=Path
    )
    gencert_parser.add_argument(
        "-tifek-pub","--tifek-pub", default=tifek_pub_def, help="TIFEK Public Key", type=Path
    )


def f29_gencert_args(subparsers: argparse._SubParsersAction) -> None:
    """F29-style CLI arguments for gencert sub-command."""
    parser = subparsers.add_parser(
        "gencert",
        help="Generate an x.509 certificate",
        description="Generate x.509 certificate for the given options",
    )

    # Use HSM
    parser.add_argument(
        "-hsm", "--hsm", action="store_true",
        help="Use HSM Device to access the keys",
    )
    # AES256 key argument
    parser.add_argument('-a', '--aes256', help="AES256 key")

    # TIFEK argument
    parser.add_argument('-t', '--tifek', required=True, help="TIFEK key")

    # SMPK arguments
    parser.add_argument('--smpk', action="store_true", default=True, help="SMPK key")
    parser.add_argument('--s_protect', action='store_true', help="Protect SMPK key")
    parser.add_argument('--s_ovrd', action='store_true', help="Override SMPK key")

    # SMEK arguments
    parser.add_argument('--smek', action="store_true", default=True, help="SMEK key")
    parser.add_argument('--smek_protect', action='store_true', help="Protect SMEK key")
    parser.add_argument('--smek_ovrd', action='store_true', help="Override SMEK key")

    # Application software revision arguments
    parser.add_argument('--sr_app', help="SR App key")
    parser.add_argument('--sr_app_protect', action='store_true', help="Protect SR App key")
    parser.add_argument('--sr_app_ovrd', action='store_true', help="Override SR App key")

    # SSU software revision arguments
    parser.add_argument('--sr_ssu', help="SR SSU key")
    parser.add_argument('--sr_ssu_protect', action='store_true', help="Protect SR SSU key")
    parser.add_argument('--sr_ssu_ovrd', action='store_true', help="Override SR SSU key")

    # SBL software revision arguments
    parser.add_argument('--sr_sbl', help="SR SBL key")
    parser.add_argument('--sr_sbl_protect', action='store_true', help="Protect SR SBL key")
    parser.add_argument('--sr_sbl_ovrd', action='store_true', help="Override SR SBL key")

    # HSMRT software revision arguments
    parser.add_argument('--sr_hsmRT', help="SR HSMRT key")
    parser.add_argument('--sr_hsmRT_protect', action='store_true', help="Protect SR HSMRT key")
    parser.add_argument('--sr_hsmRT_ovrd', action='store_true', help="Override SR HSMRT key")

    # BMPK arguments
    parser.add_argument('--bmpk', action="store_true", default=True, help="BMPK key")
    parser.add_argument('--b_protect', action='store_true', help="Protect BMPK key")
    parser.add_argument('--b_ovrd', action='store_true', help="Override BMPK key")

    # BMEK arguments
    parser.add_argument('--bmek', action="store_true", default=True, help="BMEK key")
    parser.add_argument('--bmek_protect', action='store_true', help="Protect BMEK key")
    parser.add_argument('--bmek_ovrd', action='store_true', help="Override BMEK key")

    # Certificate and generation arguments
    parser.add_argument('-c', '--cert', help="Certificate")
    parser.add_argument('-ch', '--certhelp', action='store_true', help="Show help message")

    # MSV arguments
    parser.add_argument('--msv', help="MSV key")
    parser.add_argument('--msv_protect', action='store_true', help="Protect MSV key")
    parser.add_argument('--msv_ovrd', action='store_true', help="Override MSV key")

    # Key count arguments
    parser.add_argument('--keycnt', help="Key count")
    parser.add_argument('--keycnt_protect', action='store_true', help="Protect key count")
    parser.add_argument('--keycnt_ovrd', action='store_true', help="Override key count")

    # Key revision arguments
    parser.add_argument('--keyrev', help="Key revision")
    parser.add_argument('--keyrev_protect', action='store_true', help="Protect key revision")
    parser.add_argument('--keyrev_ovrd', action='store_true', help="Override key revision")

    # Extended OTP arguments
    parser.add_argument('--ext_otp', help="External OTP")
    parser.add_argument('--ext_otp_indx', help="External OTP index")
    parser.add_argument('--ext_otp_size', help="External OTP size")
    parser.add_argument('--ext_otp_protect', help="External OTP protection")

    # MPK and MEK options
    parser.add_argument('--mpk_opt', help="MPK option")
    parser.add_argument('--mek_opt', help="MEK option")

    # Device and version arguments
    parser.add_argument(
        '--device', '-d', required=False, default='f29h85x', type=str,
        choices=['am263x', 'am263px', 'am273x', 'am261x', 'f29h85x'],
        help="Device type",
    )
    parser.add_argument(
        '--devSrVer', required=True,
        choices=['SR_10', 'SR_11', 'SR_12', 'SR_20'],
        help="Device SR version",
    )

    parser.add_argument(
        "-o", "--output", help="Output Directory", type=Path
    )


def _safe_bytes(val, default_len: int = 4) -> bytes:
    """Ensure val is bytes; convert from int if needed."""
    if isinstance(val, bytes):
        return val
    if isinstance(val, int):
        return val.to_bytes(default_len, byteorder="big")
    # hex string fallback
    return bytes.fromhex(str(val).replace("0x", "").rjust(default_len * 2, "0"))


# pylint: disable=too-many-locals,too-many-branches,too-many-statements
def generate_certificate(
    session: str,
    password: str,
    msv: Union[int, str] = "0x00000",
    use_hsm: bool = False,
    # --- existing params (backward compat) ---
    mpk_flags: List[str] = [],
    mek_flags: List[str] = [],
    output_dir_path: Path = output_path,
    multishot: bool = False,
    signing_algorithm: str = "rsa-pkcs1v1.5",
    secure_session: Optional[SecureSession] = None,
    tifek_pub_path: Optional[Path] = None,
    # --- NEW: device selection ---
    device: str = "default",
    # --- NEW: F29-style per-field flags (as info dicts) ---
    smpk_flags_dict: Optional[Dict] = None,
    smek_flags_dict: Optional[Dict] = None,
    bmpk_flags_dict: Optional[Dict] = None,
    bmek_flags_dict: Optional[Dict] = None,
    # --- NEW: F29-specific values ---
    key_rev: Optional[int] = None,
    key_cnt: Optional[int] = None,
    swrev_hsmRT: Optional[bytes] = None,
    swrev_sbl: Optional[bytes] = None,
    swrev_sec_app: Optional[bytes] = None,
    swrev_ssu: Optional[bytes] = None,
    mpk_options: Optional[bytes] = None,
    mek_options: Optional[bytes] = None,
    ext_otp_data: Optional[ExtendedOTPData] = None,
    # --- NEW: per-key signing (ECC support) ---
    per_key_signing_algorithms: Optional[List[SigningAlgorithm]] = None,
    # --- NEW: development session AES key ---
    aes_key_override: Optional[bytes] = None,
    generate_secondary_cert: bool = True,
    # --- NEW: field-level flags for plaintext fields ---
    msv_flags: Optional[FieldFlags] = None,
    key_rev_flags: Optional[FieldFlags] = None,
    key_cnt_flags: Optional[FieldFlags] = None,
    swrev_hsmRT_flags: Optional[FieldFlags] = None,
    swrev_sbl_flags: Optional[FieldFlags] = None,
    swrev_sec_app_flags: Optional[FieldFlags] = None,
    swrev_ssu_flags: Optional[FieldFlags] = None,
    mpk_options_active: bool = False,
    mek_options_active: bool = False,
    include_smek: Optional[bool] = None,
    include_bmek: Optional[bool] = None,
) -> None:
    """
    Generate an x.509 certificate for the given options.

    Supports both the SPT flow (default/j722s/am62px) via mpk_flags/mek_flags
    and the F29 flow (f29h85x/am263x/am273x) via *_flags_dict parameters.
    """
    # Validate SPT-style flags if used
    if smpk_flags_dict is None:
        try:
            validate_flags(mpk_flags, "MPK options")
            validate_flags(mek_flags, "MEK options")
        except ValueError as e:
            raise e

    with open(tifek_pub_path, "rb") as f:
        tifek_pub = f.read()

    if isinstance(msv, str):
        msv_int = int(msv, 16)
    else:
        msv_int = msv

    # Determine signing algorithms
    if per_key_signing_algorithms is not None:
        algos = per_key_signing_algorithms
    elif signing_algorithm == "rsa-pkcs1v1.5":
        algos = [SigningAlgorithm.PKCS1_V15, SigningAlgorithm.PKCS1_V15]
    else:
        algos = [SigningAlgorithm.RSA_SSA_PSS, SigningAlgorithm.RSA_SSA_PSS]

    try:
        crypto_backend = get_crypto_backend(use_hsm=use_hsm)

        if secure_session is None:
            secure_session = SecureSession(use_hsm=use_hsm)

        with secure_session as s:
            # Ensure cross-platform path handling
            temp_dir_path = output_dir_path / "temp"
            try:
                temp_dir_path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                # Provide platform-appropriate error message
                if IS_WINDOWS:
                    raise RuntimeError(
                        f"Failed to create directory '{str(temp_dir_path)}'. "
                        f"Check if you have write permissions or if the path contains invalid characters. Error: {e}"
                    ) from e
                else:
                    raise RuntimeError(
                        f"Failed to create directory '{str(temp_dir_path)}'. "
                        f"Check file permissions and ownership. Error: {e}"
                    ) from e

            print(f"opening session: {session}")
            _session = s.open_session(session, password)

            keys = s.get_manufacturer_keys(crypto_backend)

            # Create ephemeral key for encrypting other extension payloads
            if aes_key_override is not None:
                aes_key: bytes = aes_key_override
            else:
                aes_key = keys[0].generate_aes_key()

            # Build device config
            device_config = get_device_config(device)

            # Determine field flags: F29-style (info dicts) vs SPT-style (list)
            if smpk_flags_dict is not None:
                smpk_ff = FieldFlags.from_info_dict(smpk_flags_dict)
                smpk_ff.active = True
                smek_ff = FieldFlags.from_info_dict(smek_flags_dict or {})
                smek_ff.active = True
                bmpk_ff = FieldFlags.from_info_dict(bmpk_flags_dict or {})
                bmpk_ff.active = True
                bmek_ff = FieldFlags.from_info_dict(bmek_flags_dict or {})
                bmek_ff.active = True
            else:
                smpk_ff = FieldFlags.from_list(mpk_flags)
                smek_ff = FieldFlags.from_list(mek_flags)
                bmpk_ff = smpk_ff
                bmek_ff = smek_ff

            # Resolve per-key signing algorithms from session if in F29 mode
            if per_key_signing_algorithms is not None:
                algos = per_key_signing_algorithms
            elif smpk_flags_dict is not None:
                # F29 mode: resolve from keys (algorithms set by get_manufacturer_keys)
                _, smpk_algo = keys[0].get_signing_key()
                _, bmpk_algo = keys[1].get_signing_key()
                algos = [smpk_algo, bmpk_algo]

            # Build CertificateRequest
            request = CertificateRequest(
                device_config=device_config,
                mkeys=keys,
                aes_key=aes_key,
                tifek_pub=tifek_pub,
                per_key_signing_algorithms=algos,
                smpk_flags=smpk_ff,
                smek_flags=smek_ff,
                bmpk_flags=bmpk_ff,
                bmek_flags=bmek_ff,
                include_smek=include_smek if include_smek is not None else True,
                include_bmek=include_bmek if include_bmek is not None else True,
                msv=msv_int,
                msv_flags=msv_flags or FieldFlags(active=True),
                key_rev=key_rev if key_rev is not None else 1,
                key_rev_flags=key_rev_flags or FieldFlags(),
                key_cnt=key_cnt if key_cnt is not None else 1,
                key_cnt_flags=key_cnt_flags or FieldFlags(),
                swrev_slot78=swrev_hsmRT if swrev_hsmRT is not None else b"\x00",
                swrev_slot78_flags=swrev_hsmRT_flags or FieldFlags(),
                swrev_slot79=swrev_sbl if swrev_sbl is not None else b"\x01",
                swrev_slot79_flags=swrev_sbl_flags or FieldFlags(),
                swrev_slot80=swrev_sec_app if swrev_sec_app is not None else b"\x00",
                swrev_slot80_flags=swrev_sec_app_flags or FieldFlags(),
                swrev_slot82=swrev_ssu,
                swrev_slot82_flags=swrev_ssu_flags or FieldFlags(),
                mpk_options=mpk_options if mpk_options is not None else b"\x00\x00",
                mpk_options_active=mpk_options_active,
                mek_options=mek_options if mek_options is not None else b"\x00",
                mek_options_active=mek_options_active,
                ext_otp=ext_otp_data,
                generate_secondary_cert=generate_secondary_cert,
                multi=multishot,
            )

            results = certgen_core.generate_certificate(request)

            for i, (final_cert, primary_certificate, secondary_certificate) in enumerate(results):
                print(f"writing certificates into {output_dir_path}")
                with open(temp_dir_path / f"primary_cert_{i}.bin", "wb") as f:
                    f.write(primary_certificate)
                if secondary_certificate is not None:
                    with open(temp_dir_path / f"secondary_cert_{i}.bin", "wb") as f:
                        f.write(secondary_certificate)

                with open(temp_dir_path / f"temporary_cert_{i}.bin", "wb") as f:
                    f.write(final_cert)

                with tempfile.TemporaryFile() as temp:
                    temp.write(final_cert)
                    # C header file generation
                    temp.seek(0)
                    generate_c_header(
                        temp,
                        output_dir_path / f"keycert_{i}.h",
                        "keycert",
                        "keycert",
                        "ti_tspa",
                    )

    except Exception as e:
        raise RuntimeError(
            f"An error occurred during certificate generation: {e}"
        ) from e


# pylint: disable=too-many-locals,too-many-branches,too-many-statements
def generate_certificate_from_args(args, aes_key_development: bytes = None) -> None:
    """F29-style CLI adapter: validates args, builds params, calls generate_certificate().

    Takes an argparse.Namespace (from f29_gencert_args), runs validation,
    constructs ext OTP if needed, then calls generate_certificate().
    """
    from tisecprov.validators import (
        validate_device_sr,
        validate_msv,
        validate_key_cnt,
        validate_key_rev,
        validate_swrev,
        validate_extotp_wprp,
        validate_mpk_opt,
        validate_mek_opt,
    )
    from tisecprov.ext_otp import construct_ext_otp_hex

    device_config = get_device_config(args.device)

    # Validate device silicon revision
    validate_device_sr(device_config, args.devSrVer)

    # Build info dicts from args (same structure as the old flow)
    smpk_info = {"flag": "yes" if args.smpk else "no", "wp": "no", "rp": "no", "ovrd": "no"}
    if args.s_protect:
        smpk_info["wp"] = "yes"
        smpk_info["rp"] = "yes"
    if args.s_ovrd:
        smpk_info["ovrd"] = "yes"

    smek_info = {"flag": "yes" if args.smek else "no", "wp": "no", "rp": "no", "ovrd": "no"}
    if args.smek_protect:
        smek_info["wp"] = "yes"
        smek_info["rp"] = "yes"
    if args.smek_ovrd:
        smek_info["ovrd"] = "yes"

    bmpk_info = {"flag": "yes" if args.bmpk else "no", "wp": "no", "rp": "no", "ovrd": "no"}
    if args.b_protect:
        bmpk_info["wp"] = "yes"
        bmpk_info["rp"] = "yes"
    if args.b_ovrd:
        bmpk_info["ovrd"] = "yes"

    bmek_info = {"flag": "yes" if args.bmek else "no", "wp": "no", "rp": "no", "ovrd": "no"}
    if args.bmek_protect:
        bmek_info["wp"] = "yes"
        bmek_info["rp"] = "yes"
    if args.bmek_ovrd:
        bmek_info["ovrd"] = "yes"

    # MSV
    msv_info = {"flag": "no", "wp": "no", "rp": "no", "ovrd": "no"}
    msv_val = 0
    if args.msv:
        msv_val = validate_msv(args.msv, device_config)
        msv_info["flag"] = "yes"
    if args.msv_protect:
        msv_info["wp"] = "yes"
        msv_info["rp"] = "yes"
    if args.msv_ovrd:
        msv_info["ovrd"] = "yes"

    # Key count
    key_cnt_info = {"flag": "no", "wp": "no", "rp": "no", "ovrd": "no"}
    key_cnt_val = 1
    if args.keycnt:
        key_cnt_val = validate_key_cnt(args.keycnt)
        key_cnt_info["flag"] = "yes"
    if args.keycnt_protect:
        key_cnt_info["wp"] = "yes"
        key_cnt_info["rp"] = "yes"
    if args.keycnt_ovrd:
        key_cnt_info["ovrd"] = "yes"

    # Key revision
    key_rev_info = {"flag": "no", "wp": "no", "rp": "no", "ovrd": "no"}
    key_rev_val = 1
    if args.keyrev:
        key_rev_val = validate_key_rev(args.keyrev)
        key_rev_info["flag"] = "yes"
    if args.keyrev_protect:
        key_rev_info["wp"] = "yes"
        key_rev_info["rp"] = "yes"
    if args.keyrev_ovrd:
        key_rev_info["ovrd"] = "yes"

    # Validate key revision does not exceed key count (compare original user inputs)
    keycnt_input = int(args.keycnt) if args.keycnt else 1
    keyrev_input = int(args.keyrev) if args.keyrev else 1
    if keyrev_input > keycnt_input:
        raise ValueError(
            f"Key revision ({keyrev_input}) cannot be greater than the number of "
            f"programmed keys (keycnt={keycnt_input}). "
            "Use --keyrev 1 (SMPK) when only SMPK is being programmed."
        )

    # SWREV fields
    otp = device_config.otp_details or {}

    swrev_hsmRT_info = {"flag": "no", "wp": "no", "rp": "no", "ovrd": "no"}
    swrev_hsmRT_bytes = b"\x00\x00\x00\x00"
    if args.sr_hsmRT:
        swrev_hsmRT_bytes = validate_swrev(
            args.sr_hsmRT, otp.get("MAX_SWREV_HSMRT_VALUE_SIZE", 32),
            4, "SWREV_HSMRT",
        )
        swrev_hsmRT_info["flag"] = "yes"
    if args.sr_hsmRT_protect:
        swrev_hsmRT_info["wp"] = "yes"
        swrev_hsmRT_info["rp"] = "yes"
    if args.sr_hsmRT_ovrd:
        swrev_hsmRT_info["ovrd"] = "yes"

    swrev_sbl_info = {"flag": "no", "wp": "no", "rp": "no", "ovrd": "no"}
    swrev_sbl_bytes = b"\x00\x00\x00\x00"
    if args.sr_sbl:
        swrev_sbl_bytes = validate_swrev(
            args.sr_sbl, otp.get("MAX_SWREV_SBL_VALUE_SIZE", 32),
            4, "SWREV_SBL",
        )
        swrev_sbl_info["flag"] = "yes"
    if args.sr_sbl_protect:
        swrev_sbl_info["wp"] = "yes"
        swrev_sbl_info["rp"] = "yes"
    if args.sr_sbl_ovrd:
        swrev_sbl_info["ovrd"] = "yes"

    swrev_sec_app_info = {"flag": "no", "wp": "no", "rp": "no", "ovrd": "no"}
    swrev_sec_app_bytes = b"\x00\x00\x00\x00"
    if args.sr_app:
        swrev_sec_app_bytes = validate_swrev(
            args.sr_app, otp.get("MAX_SWREV_SEC_APP_VALUE_SIZE", 32),
            4, "SWREV_SEC_APP",
        )
        swrev_sec_app_info["flag"] = "yes"
    if args.sr_app_protect:
        swrev_sec_app_info["wp"] = "yes"
        swrev_sec_app_info["rp"] = "yes"
    if args.sr_app_ovrd:
        swrev_sec_app_info["ovrd"] = "yes"

    swrev_ssu_info = {"flag": "no", "wp": "no", "rp": "no", "ovrd": "no"}
    swrev_ssu_bytes = None
    if args.device == "f29h85x":
        swrev_ssu_bytes = b"\x00\x00\x00\x00\x00\x00\x00\x00"
        if args.sr_ssu:
            swrev_ssu_bytes = validate_swrev(
                args.sr_ssu, otp.get("MAX_SWREV_SSU_VALUE_SIZE", 64),
                8, "SWREV_SSU",
            )
            swrev_ssu_info["flag"] = "yes"
        if args.sr_ssu_protect:
            swrev_ssu_info["wp"] = "yes"
            swrev_ssu_info["rp"] = "yes"
        if args.sr_ssu_ovrd:
            swrev_ssu_info["ovrd"] = "yes"

    # Extended OTP
    extotp_info = {
        "flag": "no", "wp": "no", "rp": "no",
        "wprp": "00000000000000000000000000000000",
        "index": "0", "size": "0",
    }
    if args.ext_otp:
        args.ext_otp_indx = int(args.ext_otp_indx)
        args.ext_otp_size = int(args.ext_otp_size)
        extotp_info["flag"] = "yes"
    if args.ext_otp_indx:
        extotp_info["index"] = args.ext_otp_indx
    if args.ext_otp_size:
        extotp_info["size"] = args.ext_otp_size
    if args.ext_otp_protect:
        wprp = validate_extotp_wprp(args.ext_otp_protect)
        extotp_info["wprp"] = wprp
        extotp_info["wp"] = "yes"
        extotp_info["rp"] = "yes"

    # MPK/MEK options
    mpk_opt_active = False
    mpk_opt_bytes = b"\x00\x00"
    if args.mpk_opt:
        mpk_opt_val = validate_mpk_opt(args.mpk_opt, device_config)
        mpk_opt_bytes = mpk_opt_val.to_bytes(4, byteorder="big")
        mpk_opt_active = True

    mek_opt_active = False
    mek_opt_bytes = b"\x00"
    if args.mek_opt:
        mek_opt_val = validate_mek_opt(args.mek_opt, device_config)
        mek_opt_bytes = mek_opt_val.to_bytes(4, byteorder="big")
        mek_opt_active = True

    # Determine output path
    if not args.output:
        out_path = get_output_path(args.device)
    else:
        out_path = args.output

    # Clean output dir
    import shutil
    try:
        if os.path.exists(out_path):
            shutil.rmtree(out_path)
    except Exception as e:
        print(f"Warning: Could not remove existing directory {out_path}: {e}")

    # Determine if secondary cert should be generated
    gen_secondary = bmpk_info["flag"] == "yes"

    if gen_secondary:
        print("Generating Dual signed certificate!!")
    else:
        print("Generating Single signed certificate!!")

    # Use generate_certificate() with F29 parameters.
    # The ext OTP handling requires access to crypto keys, so we do it
    # inside generate_certificate by passing a callback-style approach.
    # Instead, we pre-construct the ext OTP data structure here if needed,
    # but the encryption requires the keys which are inside the session.
    # We pass ext_otp raw data and let generate_certificate handle encryption.

    # For ext OTP, we need to construct the hex string first, then encrypt
    # inside generate_certificate. But the current architecture encrypts
    # ext OTP before building the CertificateRequest. To maintain
    # backward compat, we handle it the same way: construct ExtendedOTPData
    # with plaintext, then encrypt inside.

    # Since ext OTP encryption happens in cert_gen_main using key_data[0][0].aes_encrypt,
    # and we need the session keys for that, we'll handle it by pre-constructing
    # the ext OTP as a special case that generate_certificate processes.

    # For now, pass the ext OTP params and let generate_certificate handle it.
    # We'll construct the hex string and pass it as ExtendedOTPData with
    # a flag indicating it needs encryption.

    ext_otp_result = None
    ext_otp_hex = None
    if extotp_info["flag"] == "yes":
        ext_otp_hex = construct_ext_otp_hex(
            args.ext_otp,
            int(extotp_info["index"]),
            int(extotp_info["size"]),
            device_config,
        )

    # We need to handle ext OTP encryption inside the session context.
    # generate_certificate already opens a session, so we'll pass the raw
    # ext OTP data and handle encryption there. For this, we expand
    # generate_certificate to accept ext_otp_raw_hex.

    # Actually, looking at the original flow more carefully, the ext OTP
    # is encrypted with the AES key and the first manufacturer key pair.
    # This is done in cert_gen_main before building CertificateRequest.
    # Since generate_certificate now handles session opening and key retrieval,
    # we can do the ext OTP encryption inside generate_certificate.
    # But that would complicate the function. The simpler approach is to
    # open the session here, do the encryption, then call generate_certificate
    # with the pre-encrypted data and the session.

    # Let's follow the same pattern as cert_gen_main: open session, get keys,
    # encrypt ext OTP, then call generate_certificate with secure_session.

    crypto_backend = get_crypto_backend(use_hsm=args.hsm)
    secure_session = SecureSession(use_hsm=args.hsm)

    with secure_session as s:
        print(f"opening session: {args.session}")
        _session = s.open_session(args.session, args.password)

        keys = s.get_manufacturer_keys(crypto_backend)

        # Get AES key: prefer explicit override, then session-stored key, then random
        if aes_key_development is not None:
            aes_key = aes_key_development
        else:
            try:
                aes_key = s.get_key("aes_key")
            except ValueError:
                aes_key = keys[0].generate_aes_key()

        # Construct and encrypt ext OTP
        if ext_otp_hex is not None:
            otp = bytes.fromhex(ext_otp_hex)
            rs_otp = os.urandom(32)
            otp_with_rs = otp + rs_otp
            encrypted_otp, iv_otp = keys[0].aes_encrypt(otp_with_rs, key=aes_key)
            ext_otp_result = ExtendedOTPData(
                data=encrypted_otp,
                iv=iv_otp,
                rs=rs_otp,
                wprp=extotp_info["wprp"].encode() if isinstance(extotp_info["wprp"], str) else extotp_info["wprp"],
                index=int(extotp_info["index"]),
                size=int(extotp_info["size"]),
                flags=FieldFlags.from_info_dict(extotp_info),
            )
        else:
            # Zeroed ext OTP placeholder
            ext_otp_result = ExtendedOTPData(
                data=b"\x00" * 128,
                iv=b"\x00" * 16,
                rs=b"\x00" * 32,
                wprp=extotp_info["wprp"].encode() if isinstance(extotp_info["wprp"], str) else extotp_info["wprp"],
                index=int(extotp_info["index"]),
                size=int(extotp_info["size"]),
                flags=FieldFlags.from_info_dict(extotp_info),
            )

        # Build CertificateRequest directly (avoid re-opening session in generate_certificate)
        smpk_ff = FieldFlags.from_info_dict(smpk_info)
        smpk_ff.active = True
        smek_ff = FieldFlags.from_info_dict(smek_info)
        smek_ff.active = True
        bmpk_ff = FieldFlags.from_info_dict(bmpk_info)
        bmpk_ff.active = True
        bmek_ff = FieldFlags.from_info_dict(bmek_info)
        bmek_ff.active = True

        _, smpk_signing_algorithm = keys[0].get_signing_key()
        _, bmpk_signing_algorithm = keys[1].get_signing_key()

        with open(args.tifek, "rb") as f:
            tifek_pub = f.read()

        request = CertificateRequest(
            device_config=device_config,
            mkeys=keys,
            aes_key=aes_key,
            tifek_pub=tifek_pub,
            per_key_signing_algorithms=[smpk_signing_algorithm, bmpk_signing_algorithm],
            smpk_flags=smpk_ff,
            smek_flags=smek_ff,
            bmpk_flags=bmpk_ff,
            bmek_flags=bmek_ff,
            include_smek=(smek_info["flag"] == "yes"),
            include_bmek=(bmek_info["flag"] == "yes"),
            msv=msv_val,
            msv_flags=FieldFlags.from_info_dict(msv_info),
            key_rev=key_rev_val,
            key_rev_flags=FieldFlags.from_info_dict(key_rev_info),
            key_cnt=key_cnt_val,
            key_cnt_flags=FieldFlags.from_info_dict(key_cnt_info),
            swrev_slot78=swrev_hsmRT_bytes,
            swrev_slot78_flags=FieldFlags.from_info_dict(swrev_hsmRT_info),
            swrev_slot79=swrev_sbl_bytes,
            swrev_slot79_flags=FieldFlags.from_info_dict(swrev_sbl_info),
            swrev_slot80=swrev_sec_app_bytes,
            swrev_slot80_flags=FieldFlags.from_info_dict(swrev_sec_app_info),
            swrev_slot82=swrev_ssu_bytes,
            swrev_slot82_flags=FieldFlags.from_info_dict(swrev_ssu_info) if args.device == "f29h85x" else FieldFlags(),
            mpk_options=mpk_opt_bytes if args.mpk_opt else b"\x00\x00",
            mpk_options_active=mpk_opt_active,
            mek_options=mek_opt_bytes if args.mek_opt else b"\x00",
            mek_options_active=mek_opt_active,
            ext_otp=ext_otp_result,
            generate_secondary_cert=gen_secondary,
            multi=False,
        )

        results = certgen_core.generate_certificate(request)

        # Write output files
        print(f"writing certificates into {out_path}")
        out_path.mkdir(parents=True, exist_ok=True)

        for i, (final_cert, primary_certificate, secondary_certificate) in enumerate(results):
            with open(out_path / "primary_cert.bin", "wb") as f:
                f.write(primary_certificate)
            if secondary_certificate is not None:
                with open(out_path / "secondary_cert.bin", "wb") as f:
                    f.write(secondary_certificate)
                with open(out_path / "final_certificate.bin", "wb") as f:
                    f.write(final_cert)


def validate_flags(flags: List[str], flag_type: str) -> None:
    """
    Validate that all flags are in the valid_flags set.

    Args:
        flags: List of flags to validate
        flag_type: String indicating the type of flags (for error message)

    Raises:
        ValueError: If any flag is not in valid_flags
    """

    valid_flags = {"rp", "wp", "ovrd", "active"}

    invalid_flags = set(flags) - valid_flags
    if invalid_flags:
        raise ValueError(
            f"Invalid flag(s) found in {flag_type}: {', '.join(invalid_flags)}. "
            f"Supported flags are: {', '.join(valid_flags)}"
        )
