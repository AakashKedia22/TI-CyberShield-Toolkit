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
Pydantic request/response models for the crypto service.

These mirror the schemas declared in ``docs/api/openapi.yaml`` so that the
generated OpenAPI from FastAPI stays aligned with the frozen contract.
"""

from datetime import datetime
from typing import Dict, Literal, Optional

from pydantic import BaseModel, Field

# Shared across services (re-exported for existing imports).
from services.schemas import ArtifactRef, ErrorDetail, ErrorResponse  # noqa: F401


class SessionCreateRequest(BaseModel):
    """Create a key session (genkeys)."""

    name: str
    password: str
    key_type: Optional[Literal["rsa", "ecc"]] = None
    devel: Optional[Literal["v15", "v22"]] = None
    hsm: bool = False
    smpk_signing_algorithm: Optional[
        Literal["rsa4k", "secp256r1", "secp384r1", "secp521r1"]
    ] = None
    bmpk_signing_algorithm: Optional[
        Literal["rsa4k", "secp256r1", "secp384r1", "secp521r1"]
    ] = None


class SessionSummary(BaseModel):
    """Metadata for a session. Never contains key material."""

    name: str
    description: Optional[str] = None
    hsm: Optional[bool] = None
    smpk_algorithm: Optional[str] = None
    bmpk_algorithm: Optional[str] = None
    created_at: Optional[datetime] = None


class SessionOpenRequest(BaseModel):
    """Unlock a session and obtain a short-lived session token."""

    password: str


class SessionToken(BaseModel):
    """Short-lived token used for session-scoped operations."""

    token: str
    expires_at: datetime


class PublicKeysResponse(BaseModel):
    """Public key material. Private keys never leave the service."""

    smpk_public_key: Optional[ArtifactRef] = None
    bmpk_public_key: Optional[ArtifactRef] = None


class DevelopmentSessionRequest(BaseModel):
    """Create/recreate the F29 Development session."""

    smpk_signing_algorithm: Literal["rsa4k", "secp256r1", "secp384r1", "secp521r1"]
    bmpk_signing_algorithm: Literal["rsa4k", "secp256r1", "secp384r1", "secp521r1"]


class ExtOtpConfig(BaseModel):
    """Extended OTP row configuration (value + index + size + wprp)."""

    value: Optional[str] = None
    index: Optional[int] = None
    size: Optional[int] = None
    wprp: Optional[str] = None
    protect: bool = False


class CertificateRequest(BaseModel):
    """Full F29 OTP certificate field set (maps to the gencert CLI)."""

    devSrVer: str = Field(..., description="Device silicon revision, e.g. SR_20")
    tifek_artifact: ArtifactRef = Field(..., description="TI FEK public key")
    msv: Optional[str] = None
    msv_protect: bool = False
    smpk: bool = True
    s_protect: bool = False
    s_ovrd: bool = False
    smek: bool = True
    smek_protect: bool = False
    smek_ovrd: bool = False
    bmpk: bool = True
    b_protect: bool = False
    b_ovrd: bool = False
    bmek: bool = True
    bmek_protect: bool = False
    bmek_ovrd: bool = False
    sr_sbl: Optional[str] = None
    sr_sbl_protect: bool = False
    sr_sbl_ovrd: bool = False
    sr_hsmRT: Optional[str] = None
    sr_hsmRT_protect: bool = False
    sr_hsmRT_ovrd: bool = False
    sr_app: Optional[str] = None
    sr_app_protect: bool = False
    sr_app_ovrd: bool = False
    sr_ssu: Optional[str] = None
    sr_ssu_protect: bool = False
    sr_ssu_ovrd: bool = False
    keycnt: Optional[int] = None
    keycnt_protect: bool = False
    keycnt_ovrd: bool = False
    keyrev: Optional[int] = None
    keyrev_protect: bool = False
    keyrev_ovrd: bool = False
    ext_otp: Optional[ExtOtpConfig] = None


class CertificateBundle(BaseModel):
    """One signed certificate bundle."""

    primary_cert: Optional[ArtifactRef] = None
    secondary_cert: Optional[ArtifactRef] = None
    final_cert: Optional[ArtifactRef] = None


class CertificateResult(BaseModel):
    """Output artifacts of OTP certificate generation."""

    certificates: list[CertificateBundle]
    keycert_headers: list[ArtifactRef] = []


class RotCertResult(BaseModel):
    """Output of ROT switching certificate generation."""

    rot_switching_cert: ArtifactRef


class DebugCertRequest(BaseModel):
    """Parameters for debug certificate generation (debugcert)."""

    keyrev: int = Field(..., description="1 -> SMPK, 2 -> BMPK")
    swrv: int
    dev_dbg_type: int
    dev_uid: str = Field(..., description="64-byte hex device UID")


class DebugCertResult(BaseModel):
    """Output of debug certificate generation."""

    debug_cert: ArtifactRef


class RecoveryCertRequest(BaseModel):
    """Parameters for device recovery certificate generation (devicerecovery)."""

    keyrev: int
    dev_uid: str = Field(..., description="64-byte hex device UID")


class RecoveryCertResult(BaseModel):
    """Output of device recovery certificate generation."""

    recovery_cert: ArtifactRef


class SignImageRequest(BaseModel):
    """Parameters for signing an application image (signapp)."""

    image_artifact: ArtifactRef
    input_format: Literal["BIN", "ELF"] = "BIN"
    core: Literal["C29", "HSM"]
    keyrev: str = Field(..., description="'1' or '2'")
    loadaddr: str = Field(..., description="Hex load address, e.g. 0x10001000")
    swrv: str
    boot: Literal["FLASH", "RAM"]
    debug: Optional[str] = None
    ccs_path: Optional[str] = None
    sbl_enc: bool = False
    tifs_enc: bool = False
    fw_enc: bool = False
    enc_key: Optional[ArtifactRef] = None
    fw_enc_key: Optional[ArtifactRef] = None
    kd_salt: Optional[ArtifactRef] = None
    fw_type: Optional[str] = None
    img_integ: bool = False
    crypto_unlock: str = "no"


class SignedImageResult(BaseModel):
    """Output of image signing."""

    signed_image: ArtifactRef


class SignSecCfgRequest(BaseModel):
    """Parameters for signing a security configuration (signSecCfg)."""

    image_artifact: ArtifactRef
    swrv: str
    keyrev: str = Field(..., description="1 -> SMPK, 2 -> BMPK")
    boot: Literal["FLASH", "RAM"] = "FLASH"
    ccs_path: str = Field(..., description="CCS installation path (required)")
    fw_enc: bool = False
    fw_enc_key: Optional[ArtifactRef] = None
    kd_salt: Optional[ArtifactRef] = None


class SignedSecCfgResult(BaseModel):
    """Output of security configuration signing."""

    seccfg_bin: ArtifactRef


class EncryptRequest(BaseModel):
    """Parameters for symmetric binary encryption (encrypt)."""

    image_artifact: ArtifactRef
    key: Optional[ArtifactRef] = Field(
        default=None, description="Symmetric key; defaults to the session MEK"
    )
    encryption_mode: Literal["sbl_enc", "tifs_enc", "fw_enc"] = "sbl_enc"
    kd_salt: Optional[ArtifactRef] = None


class EncryptResult(BaseModel):
    """Output of binary encryption."""

    encrypted_image: ArtifactRef


class SignBatchResult(BaseModel):
    """Per-binary result of the prebuilt batch signing operation."""

    total: int
    succeeded: int
    failed: int
    results: list[dict] = Field(..., description="Per-binary status and artifact refs")


class ErrorDetail(BaseModel):
    """Machine-readable error detail (matches the frozen contract)."""

    code: str
    message: str
    details: Optional[Dict] = None


class ErrorResponse(BaseModel):
    """Standard error envelope."""

    error: ErrorDetail