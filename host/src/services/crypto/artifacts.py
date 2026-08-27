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
On-disk artifact store.

Files (binaries, certificates, keys) are stored under a configurable directory
(default: the platform cache dir). Each artifact is addressed by a UUID; its
metadata (filename, content type, declared purpose) lives in a sidecar JSON
file so the store survives restarts.
"""

import json
import os
import uuid
from pathlib import Path
from typing import Any, Dict, Tuple

from appdirs import user_cache_dir

from services.crypto.schemas import ArtifactRef


class ArtifactStore:
    """Stores binary blobs addressed by UUID."""

    def __init__(self, base_dir: Path | None = None) -> None:
        if base_dir is None:
            base_dir = Path(user_cache_dir("tisecprov", "cst-artifacts"))
        base_dir.mkdir(parents=True, exist_ok=True)
        self.base_dir = base_dir

    def save(
        self,
        data: bytes,
        filename: str | None = None,
        content_type: str | None = None,
        device: str | None = None,
        purpose: str | None = None,
    ) -> ArtifactRef:
        """Persist a blob and return its ``ArtifactRef``."""
        artifact_id = str(uuid.uuid4())
        (self.base_dir / artifact_id).write_bytes(data)
        meta: Dict[str, Any] = {
            "id": artifact_id,
            "filename": filename,
            "content_type": content_type,
            "size": len(data),
            "device": device,
            "purpose": purpose,
        }
        (self.base_dir / f"{artifact_id}.json").write_text(
            json.dumps(meta), encoding="utf-8"
        )
        return ArtifactRef(**meta)

    def get(self, artifact_id: str) -> Tuple[Path, Dict[str, Any]]:
        """Return ``(data_path, metadata)``. Raises ``KeyError`` if unknown."""
        artifact_id = self._validate_id(artifact_id)
        data_path = self.base_dir / artifact_id
        if not data_path.exists():
            raise KeyError(artifact_id)
        meta_path = self.base_dir / f"{artifact_id}.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        else:
            meta = {
                "id": artifact_id,
                "filename": None,
                "content_type": None,
                "size": data_path.stat().st_size,
            }
        return data_path, meta

    @staticmethod
    def _validate_id(artifact_id: str) -> str:
        """Reject non-UUID ids to prevent path traversal."""
        name = Path(artifact_id).name
        try:
            uuid.UUID(name)
        except ValueError as exc:
            raise KeyError(artifact_id) from exc
        return name


def get_artifact_store() -> ArtifactStore:
    """Return the module singleton, honouring the ``CST_ARTIFACT_DIR`` override.

    The environment variable is read on every call so tests can redirect the
    store without re-importing the module.
    """
    global _artifact_store
    override = os.environ.get("CST_ARTIFACT_DIR")
    if _artifact_store is None or (
        override and _artifact_store.base_dir != Path(override)
    ):
        _artifact_store = ArtifactStore(Path(override) if override else None)
    return _artifact_store


_artifact_store: ArtifactStore | None = None