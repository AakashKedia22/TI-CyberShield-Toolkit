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
Certificate generation operations for Backend #1.

Wraps ``apps.spt.gencert`` and the ``apps.tifs`` certificate generators. The
session password/HSM flag come from the session token entry; every generated
file is collected into the artifact store and returned by reference.
"""

from types import SimpleNamespace
from typing import Dict

from services.crypto.api import APIError
from services.crypto.exec import (
    clean_output_dir,
    collect_outputs,
    make_output_dir,
    require_artifact,
    resolve_artifact,
    run_core,
)
from services.crypto.schemas import (
    CertificateBundle,
    CertificateRequest,
    CertificateResult,
    DebugCertRequest,
    DebugCertResult,
    RecoveryCertRequest,
    RecoveryCertResult,
    RotCertResult,
)


def generate_certificate(
    device: str, token_entry: Dict, req: CertificateRequest
) -> CertificateResult:
    """Generate the OTP key certificate (gencert)."""
    if req.ext_otp and req.ext_otp.value:
        if req.ext_otp.index is None or req.ext_otp.size is None:
            raise APIError(
                400,
                "INVALID_ARGUMENT",
                "ext_otp.index and ext_otp.size are required when ext_otp.value is set",
            )

    tifek_path = resolve_artifact(req.tifek_artifact)
    out_dir = make_output_dir("cst-cert-")
    args = SimpleNamespace(
        device=device,
        devSrVer=req.devSrVer,
        session=token_entry["name"],
        password=token_entry["password"],
        hsm=token_entry["use_hsm"],
        tifek=str(tifek_path),
        output=out_dir,
        smpk=req.smpk,
        s_protect=req.s_protect,
        s_ovrd=req.s_ovrd,
        smek=req.smek,
        smek_protect=req.smek_protect,
        smek_ovrd=req.smek_ovrd,
        bmpk=req.bmpk,
        b_protect=req.b_protect,
        b_ovrd=req.b_ovrd,
        bmek=req.bmek,
        bmek_protect=req.bmek_protect,
        bmek_ovrd=req.bmek_ovrd,
        msv=req.msv,
        msv_protect=req.msv_protect,
        msv_ovrd=False,
        keycnt=str(req.keycnt) if req.keycnt is not None else None,
        keycnt_protect=req.keycnt_protect,
        keycnt_ovrd=False,
        keyrev=str(req.keyrev) if req.keyrev is not None else None,
        keyrev_protect=req.keyrev_protect,
        keyrev_ovrd=False,
        sr_sbl=req.sr_sbl,
        sr_sbl_protect=req.sr_sbl_protect,
        sr_sbl_ovrd=False,
        sr_hsmRT=req.sr_hsmRT,
        sr_hsmRT_protect=req.sr_hsmRT_protect,
        sr_hsmRT_ovrd=False,
        sr_app=req.sr_app,
        sr_app_protect=req.sr_app_protect,
        sr_app_ovrd=False,
        sr_ssu=req.sr_ssu,
        sr_ssu_protect=req.sr_ssu_protect,
        sr_ssu_ovrd=False,
        ext_otp=req.ext_otp.value if req.ext_otp else None,
        ext_otp_indx=req.ext_otp.index if req.ext_otp else None,
        ext_otp_size=req.ext_otp.size if req.ext_otp else None,
        ext_otp_protect=req.ext_otp.wprp if req.ext_otp and req.ext_otp.protect else None,
        mpk_opt=None,
        mek_opt=None,
        aes256=None,
    )
    try:
        from apps.spt.gencert import generate_certificate_from_args

        run_core(generate_certificate_from_args, args)
        refs = collect_outputs(out_dir, device, "certificate")
        bundle = CertificateBundle(
            primary_cert=refs.get("primary_cert.bin"),
            secondary_cert=refs.get("secondary_cert.bin"),
            final_cert=refs.get("final_certificate.bin"),
        )
        return CertificateResult(certificates=[bundle])
    finally:
        clean_output_dir(out_dir)


def generate_rot_cert(device: str, token_entry: Dict) -> RotCertResult:
    """Generate a Root of Trust switching certificate (rotcert)."""
    out_dir = make_output_dir("cst-rot-")
    args = SimpleNamespace(
        device=device,
        session=token_entry["name"],
        password=token_entry["password"],
        hsm=token_entry["use_hsm"],
        rot_output=out_dir,
    )
    try:
        from apps.tifs.rot_cert_scripts.rot_switch_cert_gen import gen_rot_cert

        run_core(gen_rot_cert, args)
        refs = collect_outputs(out_dir, device, "rot_certificate")
        return RotCertResult(
            rot_switching_cert=require_artifact(
                refs, "rot_switching.cert", "ROT switching certificate"
            )
        )
    finally:
        clean_output_dir(out_dir)


def generate_debug_cert(
    device: str, token_entry: Dict, req: DebugCertRequest
) -> DebugCertResult:
    """Generate a debug authentication certificate (debugcert)."""
    out_dir = make_output_dir("cst-debug-")
    args = SimpleNamespace(
        device=device,
        session=token_entry["name"],
        password=token_entry["password"],
        hsm=token_entry["use_hsm"],
        debug_output=out_dir,
        keyrev=str(req.keyrev),
        swrv=str(req.swrv),
        dev_uid=req.dev_uid,
        dev_dbg_type=req.dev_dbg_type,
        flags=None,
        sign_key_id=None,
        enc_key_id=None,
    )
    try:
        from apps.tifs.debug_cert_scripts.debug_image_gen import gen_debug_auth_cert

        run_core(gen_debug_auth_cert, args)
        refs = collect_outputs(out_dir, device, "debug_certificate")
        return DebugCertResult(
            debug_cert=require_artifact(refs, "debug_auth.cert", "debug certificate")
        )
    finally:
        clean_output_dir(out_dir)


def generate_recovery_cert(
    device: str, token_entry: Dict, req: RecoveryCertRequest
) -> RecoveryCertResult:
    """Generate a device recovery certificate (devicerecovery)."""
    out_dir = make_output_dir("cst-recovery-")
    args = SimpleNamespace(
        device=device,
        session=token_entry["name"],
        password=token_entry["password"],
        hsm=token_entry["use_hsm"],
        device_recovery_output=out_dir,
        keyrev=str(req.keyrev),
        dev_uid=req.dev_uid,
    )
    try:
        from apps.tifs.f29_device_recovery.debug_recovery_cert_gen import (
            gen_device_recovery_cert,
        )

        run_core(gen_device_recovery_cert, args)
        refs = collect_outputs(out_dir, device, "recovery_certificate")
        return RecoveryCertResult(
            recovery_cert=require_artifact(
                refs, "device_recovery.bin", "device recovery certificate"
            )
        )
    finally:
        clean_output_dir(out_dir)