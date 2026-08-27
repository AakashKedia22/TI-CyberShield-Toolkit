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
Artifact upload/download endpoints (file store shared by both backends).
"""

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse

from services.crypto import ops
from services.crypto.auth import require_api_key
from services.crypto.schemas import ArtifactRef

router = APIRouter(
    prefix="/artifacts",
    tags=["artifacts"],
    dependencies=[Depends(require_api_key)],
)


@router.post(
    "",
    response_model=ArtifactRef,
    status_code=201,
    operation_id="uploadArtifact",
    summary="Upload a binary, certificate, or key file (multipart)",
)
async def upload_artifact(
    file: UploadFile = File(...),
    device: str | None = Form(default=None),
    purpose: str | None = Form(default=None),
) -> ArtifactRef:
    data = await file.read()
    return ops.store_artifact(
        data,
        filename=file.filename or None,
        content_type=file.content_type,
        device=device,
        purpose=purpose,
    )


@router.get(
    "/{id}",
    response_class=FileResponse,
    operation_id="getArtifact",
    summary="Download a generated artifact (certificates, signed images, headers)",
)
def get_artifact(id: str) -> FileResponse:
    path, meta = ops.load_artifact(id)
    return FileResponse(
        path,
        media_type=meta.get("content_type") or "application/octet-stream",
        filename=meta.get("filename"),
    )