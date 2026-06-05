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
Module that generates keys and inserts them into a new
session. Additionally, dummy/devel keys can also be inserted
into the session.
"""

from typing import List, Any

from tisecprov.session import SecureSession
from tisecprov.crypto import ManufacturerKeys
from tisecprov.cryptoutils import load_rsa_private_key
from tisecprov.devel import DevelKeys
from tisecprov.crypto_selector import get_crypto_backend
from tisecprov.crypto_interfaces import SigningAlgorithm, resolve_signing_algorithm


def genkeys_args(subparsers):
    """Define arguments for gencert sub-command"""
    gencert_parser = subparsers.add_parser(
        "genkeys",
        help="Generate Manufacturer keys",
        description="Generate Manufacturer Keys and other secrets and store into the session",
    )

    gencert_parser.add_argument(
        "-s", "--session", type=str, required=True, help="Name for the generated keys"
    )
    gencert_parser.add_argument(
        "-p",
        "--password",
        type=str,
        required=True,
        help="Password used to protect the keys on the disk",
    )
    gencert_parser.add_argument(
        "--key-type",
        default="rsa",
        choices=["rsa", "ecc"],
        type=str,
        help="Key type to generate (default: %(default)s)",
    )
    group = gencert_parser.add_mutually_exclusive_group()
    group.add_argument(
        "-d",
        "--devel",
        default=None,
        choices=["v15", "v22"],
        type=str,
        help="Use TI Dummy/Developer Keys (PKCS#1 v1.5 or v2.2) (default: %(default)s)",
    )
    group.add_argument(
        "-hsm",
        "--hsm",
        action="store_true",
        help="Use HSM Device for key generation and signing (default: %(default)s)",
    )


def f29_genkeys_args(subparsers):
    """Define arguments for genkeys sub-command (F29/keywriter devices)"""
    gencert_parser = subparsers.add_parser(
        "genkeys",
        help="Generate Manufacturer keys",
        description="Generate Manufacturer Keys and other secrets and store into the session",
    )

    gencert_parser.add_argument(
        "-s", "--session", type=str, required=True, help="Name for the generated keys"
    )
    gencert_parser.add_argument(
        "-p",
        "--password",
        type=str,
        required=True,
        help="Password used to protect the keys on the disk",
    )
    gencert_parser.add_argument(
        "-hsm",
        "--hsm",
        action="store_true",
        help="Use HSM Device for key generation and signing (default: %(default)s)",
    )


def export_keys_into_current_session(session: SecureSession, keys: List[Any]):
    """
    Get keys out of the Cryptography module and export them into
    the current session.
    """
    assert len(keys) == 2, "should have two sets of keys"

    smkeys = keys[0]
    bmkeys = keys[1]

    if session.hsm_session:
        # Wrap MEKs with the key's own RSA public key before storing.
        # The raw MEK never touches disk — only the HSM-encrypted blob is saved.
        session.add_smek(smkeys.wrap_mek())
        session.add_bmek(bmkeys.wrap_mek())
    else:
        # export MEKs
        smek = smkeys.get_symmetric_key()
        bmek = bmkeys.get_symmetric_key()

        # add MEKs into the session
        session.add_smek(smek)
        session.add_bmek(bmek)

    if not session.hsm_session:
        # export SMPK-priv and BMPK-priv
        smpk_priv = smkeys.export_private_key()
        bmpk_priv = bmkeys.export_private_key()

        # add SMPK-priv and BMPK-priv into the session
        session.add_smpk_priv(smpk_priv)
        session.add_bmpk_priv(bmpk_priv)


def generate_keys(
    session: str,
    password: str,
    key_type: str = "rsa4k",
    devel: str = None,
    use_hsm: bool = False,
    smpk_signing_algorithm: str = None,
    bmpk_signing_algorithm: str = None,
) -> None:
    """
    Generate Manufacturer keys and other secrets and store into the session.

    Supports both standard SPT devices (am62px, j722s) and F29/keywriter
    devices (f29h85x, am263x).  When *smpk_signing_algorithm* is provided
    the F29 per-key algorithm path is used; otherwise the standard path
    (RSA-only, with optional devel keys) is taken.

    Args:
        session: Session name
        password: Password to unlock the session
        key_type: RSA or ECC (standard path only)
        devel: can be either v15 (PKCS#1 v1.5) or v22 (PKCS#1 v2.2) (standard path only)
        use_hsm: use PKCS#11 smart card. This option cannot be used when devel is also set.
        smpk_signing_algorithm: Per-key algo string for SMPK (F29 path, e.g. "rsa4k", "secp256r1")
        bmpk_signing_algorithm: Per-key algo string for BMPK (F29 path, e.g. "rsa4k", "secp256r1")
    Returns:
        None

    Raises:
        RuntimeError: any errors encountered in the key generation or in session management.
    """
    if session is None:
        raise ValueError("Session name must be provided")

    if password is None:
        raise ValueError("Password must be provided")

    # Detect F29 path: per-key algorithm strings provided
    f29_mode = smpk_signing_algorithm is not None

    if f29_mode:
        algo_smpk = resolve_signing_algorithm(smpk_signing_algorithm)
        algo_bmpk = resolve_signing_algorithm(bmpk_signing_algorithm)
    else:
        if devel not in [None, "v15", "v22"]:
            raise RuntimeError("invalid devel argument")

    try:
        crypto_backend = get_crypto_backend(use_hsm=use_hsm)

        print(f"Creating Session: {session}")
        with SecureSession(use_hsm=use_hsm) as s:
            _session_id = s.create_session(
                session, "This is a test session", password,
            )
            try:
                _current_session = s.open_session(session, password)

                if f29_mode and not use_hsm:
                    # F29 per-key algorithm path
                    print("Generating Secondary manufacturer keys...")
                    smkeys = crypto_backend(None, None, algo_smpk)

                    print("Generating Backup manufacturer keys...")
                    bmkeys = crypto_backend(None, None, algo_bmpk)
                elif f29_mode and use_hsm:
                    # F29 HSM path
                    print("Generating Secondary manufacturer keys...")
                    smkeys = crypto_backend(session=s, label="SMKEYS")

                    print("Generating Backup manufacturer keys...")
                    bmkeys = crypto_backend(session=s, label="BMKEYS")

                    print("Keys Stored in ", session)
                elif devel is not None:
                    # Standard devel keys path
                    print("Using Developer keys...")
                    dkey = DevelKeys(key_type=devel)

                    smkeys = ManufacturerKeys(
                        symmetric_key=dkey.smek,
                        private_key=load_rsa_private_key(dkey.smpk_private_key_bytes),
                    )
                    bmkeys = ManufacturerKeys(
                        symmetric_key=dkey.bmek,
                        private_key=load_rsa_private_key(dkey.bmpk_private_key_bytes),
                    )
                elif use_hsm:
                    # Standard HSM path
                    print("Generating Secondary manufacturer keys...")
                    smkeys = crypto_backend(session=s, label="SMKEYS")

                    print("Generating Backup manufacturer keys...")
                    bmkeys = crypto_backend(session=s, label="BMKEYS")

                    print("Keys Stored in ", session)
                else:
                    # Standard fresh RSA path
                    print("Generating Secondary manufacturer keys...")
                    smkeys = crypto_backend()

                    print("Generating Backup manufacturer keys...")
                    bmkeys = crypto_backend()
            except Exception as e:
                raise RuntimeError(
                    f"An error occurred during session initialization: {e}"
                ) from e

            export_keys_into_current_session(s, [smkeys, bmkeys])

            # save the current session with the new keys
            print("Saving session...")
            s.save_session()

    except Exception as e:
        raise RuntimeError(f"An error occurred during key generation: {e}") from e
