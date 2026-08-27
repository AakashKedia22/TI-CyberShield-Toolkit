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
Operations layer: wraps the tisecprov/apps core so routers stay thin.

All functions translate core ``RuntimeError``/``ValueError`` into ``APIError``
so the exception handlers in ``main.py`` can produce the frozen error envelope.
The core modules are imported lazily so that loading this module is cheap and
does not pull in unused chains (e.g. Qt / GUI deps).
"""

import logging
import os
from pathlib import Path
from typing import List, Tuple

from tisecprov.session import SecureSession

from services.crypto.api import APIError, map_session_error
from services.crypto.artifacts import get_artifact_store
from services.crypto.schemas import (
    ArtifactRef,
    DevelopmentSessionRequest,
    PublicKeysResponse,
    SessionCreateRequest,
    SessionSummary,
    SessionToken,
)
from services.crypto.tokens import token_store

logger = logging.getLogger(__name__)


def _secure_session(use_hsm: bool = False) -> SecureSession:
    """Build a ``SecureSession`` honouring the ``TISECPROV_SESSION_DIR`` override."""
    storage = os.environ.get("TISECPROV_SESSION_DIR")
    if storage:
        return SecureSession(storage_path=Path(storage), use_hsm=use_hsm)
    return SecureSession(use_hsm=use_hsm)


def _open_and_describe(session_name: str, password: str) -> bool:
    """Validate the password and return whether the session is HSM-backed.

    Tries the on-disk backend first, then (only if the PKCS#11 library is
    installed) the HSM backend. Raises ``APIError`` on failure.
    """
    disk_error: Exception | None = None
    try:
        with _secure_session(use_hsm=False) as s:
            s.open_session(session_name, password)
        return False
    except Exception as exc:
        disk_error = exc

    try:
        import pkcs11  # noqa: F401  (probe; the HSM path needs this library)
    except ImportError:
        raise map_session_error(disk_error)

    try:
        with _secure_session(use_hsm=True) as s:
            s.open_session(session_name, password)
        return True
    except Exception as exc:
        raise map_session_error(exc)


def create_session(req: SessionCreateRequest) -> SessionSummary:
    """Generate manufacturer keys and create a new session (genkeys)."""
    # Imported lazily: apps.spt pulls in tifs provisioning chains.
    from apps.spt.genkeys import generate_keys

    try:
        generate_keys(
            session=req.name,
            password=req.password,
            key_type=req.key_type or "rsa",
            devel=req.devel,
            use_hsm=req.hsm,
            smpk_signing_algorithm=req.smpk_signing_algorithm,
            bmpk_signing_algorithm=req.bmpk_signing_algorithm,
        )
    except Exception as exc:
        raise map_session_error(exc)
    return SessionSummary(name=req.name, hsm=req.hsm)


def list_sessions() -> List[SessionSummary]:
    """List session names (metadata only, no key material)."""
    with _secure_session() as s:
        return [SessionSummary(name=item["name"]) for item in s.list_sessions()]


def get_session(session_name: str) -> SessionSummary:
    """Return metadata for a single session."""
    with _secure_session() as s:
        if not s.does_session_exist(session_name):
            raise APIError(
                404, "SESSION_NOT_FOUND", f"Session {session_name} does not exist"
            )
    return SessionSummary(name=session_name)


def delete_session(session_name: str) -> None:
    """Delete a session and its encrypted key store."""
    with _secure_session() as s:
        if not s.does_session_exist(session_name):
            raise APIError(
                404, "SESSION_NOT_FOUND", f"Session {session_name} does not exist"
            )
        s.delete_session(session_name)


def open_session(session_name: str, password: str) -> SessionToken:
    """Validate the password and issue a short-lived session token."""
    use_hsm = _open_and_describe(session_name, password)
    token, expires_at = token_store.issue(session_name, password, use_hsm)
    return SessionToken(token=token, expires_at=expires_at)


def get_public_keys(session_name: str, password: str, use_hsm: bool) -> PublicKeysResponse:
    """Export the SMPK/BMPK public keys as stored artifacts.

    Only public key material is returned; private keys stay in the session.
    """
    from tisecprov.crypto_selector import get_crypto_backend

    try:
        crypto_backend = get_crypto_backend(use_hsm=use_hsm)
        with _secure_session(use_hsm=use_hsm) as s:
            s.open_session(session_name, password)
            keys = s.get_manufacturer_keys(crypto_backend)
    except Exception as exc:
        raise map_session_error(exc)

    store = get_artifact_store()
    smpk_ref = store.save(
        keys[0].get_public_key(),
        filename=f"{session_name}_smpk_public.pem",
        content_type="application/x-pem-file",
        device=None,
        purpose="public_key",
    )
    bmpk_ref = store.save(
        keys[1].get_public_key(),
        filename=f"{session_name}_bmpk_public.pem",
        content_type="application/x-pem-file",
        device=None,
        purpose="public_key",
    )
    return PublicKeysResponse(smpk_public_key=smpk_ref, bmpk_public_key=bmpk_ref)


def create_development_session(req: DevelopmentSessionRequest) -> SessionSummary:
    """Create/recreate the F29 Development session."""
    from apps.spt.f29_spt import create_development_session as _dev

    try:
        _dev(req.smpk_signing_algorithm, req.bmpk_signing_algorithm)
    except Exception as exc:
        raise map_session_error(exc)
    return SessionSummary(name="Development", hsm=False)


def store_artifact(
    data: bytes,
    filename: str | None,
    content_type: str | None,
    device: str | None,
    purpose: str | None,
) -> ArtifactRef:
    """Persist an uploaded blob into the artifact store."""
    return get_artifact_store().save(
        data,
        filename=filename,
        content_type=content_type,
        device=device,
        purpose=purpose,
    )


def load_artifact(artifact_id: str) -> Tuple[Path, dict]:
    """Resolve an artifact id to ``(path, metadata)`` or raise ``APIError``."""
    try:
        return get_artifact_store().get(artifact_id)
    except KeyError:
        raise APIError(404, "ARTIFACT_NOT_FOUND", f"Artifact {artifact_id} not found")