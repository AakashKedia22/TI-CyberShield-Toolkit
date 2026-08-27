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
Image signing/encryption endpoints (Backend #1).
"""

from typing import Dict, List, Optional

from fastapi import APIRouter, Depends

from services.crypto import imgops
from services.crypto.auth import require_api_key, require_session_token
from services.crypto.schemas import (
    EncryptRequest,
    EncryptResult,
    SignedImageResult,
    SignedSecCfgResult,
    SignImageRequest,
    SignSecCfgRequest,
)

router = APIRouter(
    prefix="/devices/{device}/images",
    tags=["crypto"],
    dependencies=[Depends(require_api_key)],
)


@router.post(
    "/sign",
    response_model=SignedImageResult,
    operation_id="signImage",
    summary="Sign an application image for a core and boot mode (signapp)",
)
def sign_image(
    device: str,
    req: SignImageRequest,
    token_entry: Dict = Depends(require_session_token),
) -> SignedImageResult:
    return imgops.sign_image(device, token_entry, req)


@router.post(
    "/sign-seccfg",
    response_model=SignedSecCfgResult,
    operation_id="signSecCfg",
    summary="Sign a security configuration image (signSecCfg)",
)
def sign_sec_cfg(
    device: str,
    req: SignSecCfgRequest,
    token_entry: Dict = Depends(require_session_token),
) -> SignedSecCfgResult:
    return imgops.sign_sec_cfg(device, token_entry, req)


@router.post(
    "/encrypt",
    response_model=EncryptResult,
    operation_id="encryptImage",
    summary="Encrypt a binary with a symmetric key (encrypt)",
)
def encrypt_image(
    device: str,
    req: EncryptRequest,
    token_entry: Dict = Depends(require_session_token),
) -> EncryptResult:
    return imgops.encrypt_image(device, token_entry, req)


@router.post(
    "/sign-batch",
    response_model=dict,
    status_code=202,
    operation_id="signBatchImages",
    summary="Sign the prebuilt binary set for a device (async job)",
)
def sign_batch_images(
    device: str,
    binaries: Optional[List[str]] = None,
    ccs_path: Optional[str] = None,
    token_entry: Dict = Depends(require_session_token),
) -> dict:
    from services.jobs import job_manager, to_job_response

    job = job_manager.submit(
        "crypto",
        "sign_batch",
        lambda ctx: imgops.sign_batch(
            device, token_entry, binaries, ccs_path, ctx=ctx
        ).model_dump(mode="json"),
    )
    return to_job_response(job)