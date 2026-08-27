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
Image signing and encryption operations for Backend #1.

Wraps ``apps.tifs.sign_encrypt_f29`` and ``apps.tifs.core.api``. All wrapped
functions are CLI-style and are executed via ``run_core`` so their failures
surface as the frozen error envelope.
"""

from pathlib import Path
from types import SimpleNamespace
from typing import Dict, List, Optional

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
    ArtifactRef,
    EncryptRequest,
    EncryptResult,
    SignBatchResult,
    SignedImageResult,
    SignedSecCfgResult,
    SignImageRequest,
    SignSecCfgRequest,
)

# Boot/core defaults for binaries that have no entry in PREBUILT_BINARY_CONFIGS.
_C29_HINTS = ("c29", "sbl", "secure_boot_manager", "csd", "combined_services_demo")


def _signed_output_name(image_filename: str, core: str) -> str:
    """Mirror sign_encrypt's output naming for the primary signed image."""
    parts = image_filename.split(".")
    stem = ".".join(parts[:-1])
    if core == "HSM":
        return f"{stem}.hs.hsmimage"
    if core == "C29":
        return f"{stem}.cert.bin"
    return f"{stem}.bin"


def _sign_image(
    device: str,
    token_entry: Dict,
    image_path: Path,
    req: SignImageRequest,
    display_name: Optional[str] = None,
) -> SignedImageResult:
    """Sign an image file located on the server (shared by single/batch paths).

    ``display_name`` is the original image filename; the wrapped core derives
    the output filename from it (the on-disk path may be an opaque artifact id).
    """
    enc_key = resolve_artifact(req.enc_key) if req.enc_key else None
    fw_enc_key = resolve_artifact(req.fw_enc_key) if req.fw_enc_key else None
    kd_salt = resolve_artifact(req.kd_salt) if req.kd_salt else None

    out_dir = make_output_dir("cst-sign-")
    kwargs = dict(
        image=str(image_path),
        input_format=req.input_format,
        core=req.core,
        keyrev=req.keyrev,
        loadaddr=req.loadaddr,
        swrv=req.swrv,
        boot=req.boot,
        output_path=out_dir,
        debug=req.debug,
        ccs_path=req.ccs_path,
        sbl_enc=req.sbl_enc,
        tifs_enc=req.tifs_enc,
        fw_enc=req.fw_enc,
        enc_key=str(enc_key) if enc_key else None,
        fw_enc_key=str(fw_enc_key) if fw_enc_key else None,
        kd_salt=str(kd_salt) if kd_salt else None,
        fw_type=req.fw_type,
        img_integ=req.img_integ,
        crypto_unlock=req.crypto_unlock,
        hsm=token_entry["use_hsm"],
        session=token_entry["name"],
        password=token_entry["password"],
    )
    try:
        from apps.tifs.sign_encrypt_f29.sign_encrypt import sign_encrypt_binary

        ok, message = run_core(sign_encrypt_binary, **kwargs)
        if not ok:
            raise APIError(500, "INTERNAL", message)

        expected = _signed_output_name(display_name or image_path.name, req.core)
        out_files = [p for p in out_dir.iterdir() if p.is_file()]
        if expected not in {p.name for p in out_files} and len(out_files) == 1:
            # The core derives the name from the on-disk path (an opaque
            # artifact id); restore the original image filename.
            out_files[0].rename(out_dir / expected)

        refs = collect_outputs(out_dir, device, "signed_image")
        main = refs.get(expected) or (next(iter(refs.values())) if refs else None)
        if main is None:
            raise APIError(500, "INTERNAL", "signing produced no output file")
        return SignedImageResult(signed_image=main)
    finally:
        clean_output_dir(out_dir)


def sign_image(device: str, token_entry: Dict, req: SignImageRequest) -> SignedImageResult:
    """Sign an uploaded application image (signapp)."""
    return _sign_image(
        device,
        token_entry,
        resolve_artifact(req.image_artifact),
        req,
        display_name=req.image_artifact.filename,
    )


def sign_sec_cfg(
    device: str, token_entry: Dict, req: SignSecCfgRequest
) -> SignedSecCfgResult:
    """Sign a security configuration image (signSecCfg)."""
    image_path = resolve_artifact(req.image_artifact)
    fw_enc_key = resolve_artifact(req.fw_enc_key) if req.fw_enc_key else None
    kd_salt = resolve_artifact(req.kd_salt) if req.kd_salt else None

    out_dir = make_output_dir("cst-seccfg-")
    kwargs = dict(
        image=str(image_path),
        swrv=req.swrv,
        keyrev=req.keyrev,
        boot=req.boot,
        output_path=out_dir,
        ccs_path=req.ccs_path,
        hsm=token_entry["use_hsm"],
        fw_enc=req.fw_enc,
        fw_enc_key=str(fw_enc_key) if fw_enc_key else None,
        kd_salt=str(kd_salt) if kd_salt else None,
        session=token_entry["name"],
        password=token_entry["password"],
    )
    try:
        from apps.tifs.sign_encrypt_f29.sign_encrypt import sign_sec_cfg_binary

        ok, message = run_core(sign_sec_cfg_binary, **kwargs)
        if not ok:
            raise APIError(500, "INTERNAL", message)
        refs = collect_outputs(out_dir, device, "seccfg")
        return SignedSecCfgResult(
            seccfg_bin=require_artifact(refs, "seccfg.bin", "seccfg")
        )
    finally:
        clean_output_dir(out_dir)


def _session_mek(token_entry: Dict) -> bytes:
    """Extract the SMEK for a session (used when no key artifact is supplied)."""
    from tisecprov.crypto_selector import get_crypto_backend
    from tisecprov.session import SecureSession

    use_hsm = token_entry["use_hsm"]
    crypto_backend = get_crypto_backend(use_hsm=use_hsm)
    with SecureSession(use_hsm=use_hsm) as s:
        s.open_session(token_entry["name"], token_entry["password"])
        keys = s.get_manufacturer_keys(crypto_backend)
        return keys[0].get_symmetric_key()


def encrypt_image(device: str, token_entry: Dict, req: EncryptRequest) -> EncryptResult:
    """Encrypt a binary with a symmetric key (encrypt)."""
    image_path = resolve_artifact(req.image_artifact)
    kd_salt = resolve_artifact(req.kd_salt) if req.kd_salt else None

    out_dir = make_output_dir("cst-enc-")
    try:
        if req.key:
            key_path = resolve_artifact(req.key)
        else:
            key_path = out_dir / "mek.key"
            key_path.write_bytes(_session_mek(token_entry))

        output_path = out_dir / "encrypted.bin"

        from apps.tifs.core.api import encrypt_binary
        from apps.tifs.core.types import (
            EncryptionAlgorithm,
            EncryptionConfig,
            ExtendedAttributes,
            PaddingMode,
            SessionInfo,
        )

        padding = PaddingMode.FF if req.encryption_mode == "fw_enc" else PaddingMode.ZERO
        encryption = EncryptionConfig(
            enabled=True,
            algorithm=EncryptionAlgorithm.AES_256_CBC,
            key_file=key_path,
            iv_salt=kd_salt,
            padding_mode=padding,
        )
        session = SessionInfo(
            session_name=token_entry["name"],
            session_password=token_entry["password"],
            is_development=(token_entry["name"] == "Development"),
        )
        extended = ExtendedAttributes(
            attributes={
                "soc_id": device.lower(),
                "device_family": "asm",
                "encryption_mode": req.encryption_mode,
            }
        )
        result = run_core(
            encrypt_binary,
            image_path=image_path,
            output_path=output_path,
            encryption=encryption,
            session=session,
            extended=extended,
        )
        if not result.success:
            raise APIError(500, "INTERNAL", result.message)
        return EncryptResult(
            encrypted_image=require_artifact(
                collect_outputs(out_dir, device, "encrypted_image"),
                "encrypted.bin",
                "encrypted image",
            )
        )
    finally:
        clean_output_dir(out_dir)


def sign_batch(
    device: str,
    token_entry: Dict,
    binaries: Optional[List[str]] = None,
    ccs_path: Optional[str] = None,
    ctx: Optional[object] = None,
) -> SignBatchResult:
    """Sign the prebuilt binary set for a device (async job on the crypto service)."""
    from apps.qtgui.models.F29H85xDeviceModel import PREBUILT_BINARY_CONFIGS
    from common.device_utils import get_device_prebuilt_dir, infer_device_family

    if ctx is not None:
        ctx.log(f"Batch signing for device {device}")
        ctx.set_progress(5)

    family = infer_device_family(device)
    prebuilt_dir = Path(get_device_prebuilt_dir(device, family))
    if not prebuilt_dir.exists():
        raise APIError(
            404, "DEVICE_NOT_FOUND", f"Prebuilt images dir not found: {prebuilt_dir}"
        )

    if binaries:
        targets = [prebuilt_dir / name for name in binaries]
    else:
        targets = [
            p for p in prebuilt_dir.glob("*.bin") if "otp_kw" not in p.name.lower()
        ]

    results: List[dict] = []
    success_count = 0
    total = len(targets)
    for idx, path in enumerate(targets, start=1):
        if ctx is not None:
            ctx.log(f"[{idx}/{total}] signing {path.name}")
            ctx.set_progress(5 + int(90 * (idx - 1) / max(1, total)))
        if not path.exists():
            results.append({"name": path.name, "success": False, "message": "file not found"})
            continue

        config = dict(PREBUILT_BINARY_CONFIGS.get(path.name, {}))
        if not config:
            is_c29 = any(hint in path.name.lower() for hint in _C29_HINTS)
            config = {
                "core": "C29" if is_c29 else "HSM",
                "boot": "FLASH",
                "loadaddr": "0x10001000" if is_c29 else "0x00000000",
                "debug": None,
            }
        config.setdefault("keyrev", "1")
        config.setdefault("swrv", "1")

        req = SignImageRequest(
            image_artifact=ArtifactRef(id="prebuilt-local"),
            input_format="BIN",
            core=config["core"],
            keyrev=str(config["keyrev"]),
            loadaddr=config["loadaddr"],
            swrv=str(config["swrv"]),
            boot=config["boot"],
            debug=config.get("debug"),
            ccs_path=ccs_path,
        )
        try:
            result = _sign_image(
                device, token_entry, path, req, display_name=path.name
            )
            success_count += 1
            results.append(
                {
                    "name": path.name,
                    "success": True,
                    "signed_image": result.signed_image.model_dump(mode="json"),
                }
            )
        except APIError as exc:
            results.append(
                {"name": path.name, "success": False, "message": exc.message}
            )

    failed = len(results) - success_count
    if ctx is not None:
        ctx.log(f"Batch signing finished: {success_count} succeeded, {failed} failed")
        ctx.set_progress(100)
    return SignBatchResult(
        total=len(results), succeeded=success_count, failed=failed, results=results
    )