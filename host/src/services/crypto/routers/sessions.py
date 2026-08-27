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
Session and key management endpoints (Backend #1).
"""

from typing import Dict

from fastapi import APIRouter, Depends

from services.crypto import ops
from services.crypto.auth import require_api_key, require_session
from services.crypto.schemas import (
    DevelopmentSessionRequest,
    PublicKeysResponse,
    SessionCreateRequest,
    SessionOpenRequest,
    SessionSummary,
    SessionToken,
)

router = APIRouter(
    prefix="/sessions",
    tags=["crypto"],
    dependencies=[Depends(require_api_key)],
)


@router.post(
    "",
    response_model=SessionSummary,
    status_code=201,
    operation_id="createSession",
    summary="Generate manufacturer keys and create a new key session (genkeys)",
)
def create_session(req: SessionCreateRequest) -> SessionSummary:
    return ops.create_session(req)


@router.get(
    "",
    response_model=list[SessionSummary],
    operation_id="listSessions",
    summary="List existing key sessions (names + metadata only)",
)
def list_sessions() -> list[SessionSummary]:
    return ops.list_sessions()


@router.get(
    "/{name}",
    response_model=SessionSummary,
    operation_id="getSession",
    summary="Session metadata (never key material)",
)
def get_session(name: str) -> SessionSummary:
    return ops.get_session(name)


@router.delete(
    "/{name}",
    status_code=204,
    operation_id="deleteSession",
    summary="Delete a session and its encrypted key store",
)
def delete_session(name: str) -> None:
    ops.delete_session(name)


@router.post(
    "/{name}/open",
    response_model=SessionToken,
    operation_id="openSession",
    summary="Unlock a session and obtain a short-lived session token",
)
def open_session(name: str, req: SessionOpenRequest) -> SessionToken:
    return ops.open_session(name, req.password)


@router.get(
    "/{name}/public-keys",
    response_model=PublicKeysResponse,
    operation_id="getSessionPublicKeys",
    summary="Export public keys for a session (requires session token)",
)
def get_session_public_keys(
    name: str,
    token_entry: Dict = Depends(require_session),
) -> PublicKeysResponse:
    return ops.get_public_keys(
        name, token_entry["password"], use_hsm=token_entry["use_hsm"]
    )


@router.post(
    "/{name}/development",
    response_model=SessionSummary,
    status_code=201,
    operation_id="createDevelopmentSession",
    summary="Create/recreate the F29 Development session",
)
def create_development_session(
    name: str, req: DevelopmentSessionRequest
) -> SessionSummary:
    if name != "Development":
        from services.crypto.api import APIError

        raise APIError(
            404,
            "SESSION_NOT_FOUND",
            "Only the 'Development' session can be created via this endpoint",
        )
    return ops.create_development_session(req)