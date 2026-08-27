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
Shared helpers for the crypto service operation layer.

The wrapped core functions are CLI-style: they print, write files to an output
directory, and raise ``RuntimeError``/``ValueError`` (or call ``sys.exit``).
``run_core`` translates those into the frozen ``APIError`` envelope, and
``collect_outputs`` turns a freshly generated output directory into artifacts.
"""

import shutil
import tempfile
from pathlib import Path
from typing import Any, Callable, Dict

from services.crypto.api import APIError, map_session_error
from services.crypto.artifacts import get_artifact_store
from services.crypto.schemas import ArtifactRef


def resolve_artifact(ref: ArtifactRef) -> Path:
    """Return the on-disk path for an artifact ref (raises ``APIError``)."""
    from services.crypto.ops import load_artifact

    path, _meta = load_artifact(ref.id)
    return path


def make_output_dir(prefix: str) -> Path:
    """Create a fresh temporary output directory."""
    return Path(tempfile.mkdtemp(prefix=prefix))


def clean_output_dir(output_dir: Path) -> None:
    """Best-effort removal of a temporary output directory."""
    shutil.rmtree(output_dir, ignore_errors=True)


def run_core(func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """Run a core operation, translating its failures into ``APIError``.

    - ``SystemExit`` (core ``sys.exit`` calls)      -> 500 INTERNAL
    - ``ValueError`` (validation)                   -> 400 INVALID_ARGUMENT
    - ``RuntimeError`` (session/state)              -> mapped via error contract
    - anything else                                 -> 500 INTERNAL
    """
    try:
        return func(*args, **kwargs)
    except SystemExit as exc:
        raise APIError(500, "INTERNAL", f"core operation aborted (exit {exc.code})")
    except ValueError as exc:
        raise APIError(400, "INVALID_ARGUMENT", str(exc))
    except APIError:
        raise
    except RuntimeError as exc:
        raise map_session_error(exc)
    except Exception as exc:
        raise APIError(500, "INTERNAL", f"{type(exc).__name__}: {exc}")


def collect_outputs(
    output_dir: Path, device: str | None, purpose: str
) -> Dict[str, ArtifactRef]:
    """Store every file in ``output_dir`` as an artifact, keyed by filename."""
    refs: Dict[str, ArtifactRef] = {}
    for path in sorted(Path(output_dir).iterdir()):
        if path.is_file():
            refs[path.name] = get_artifact_store().save(
                path.read_bytes(),
                filename=path.name,
                content_type="application/octet-stream",
                device=device,
                purpose=purpose,
            )
    return refs


def require_artifact(refs: Dict[str, ArtifactRef], key: str, what: str) -> ArtifactRef:
    """Return ``refs[key]`` or raise a 500 (the core produced no such file)."""
    if key not in refs:
        raise APIError(500, "INTERNAL", f"operation produced no {what} file ({key})")
    return refs[key]