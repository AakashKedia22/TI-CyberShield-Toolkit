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

from pathlib import Path
from typing import Optional

from .types import (
    SignatureConfig, ImageMetadata, EncryptionConfig,
    ExtendedAttributes, OperationResult, CertificateRequest,
    SessionInfo, Architecture, BootMode, SignatureAlgorithm,
    DEVICE_CONFIGS,
)


def sign_binary(
    image_path: Path,
    output_path: Path,
    signature: SignatureConfig,
    metadata: ImageMetadata,
    session: SessionInfo,
    encryption: Optional[EncryptionConfig] = None,
    extended: Optional[ExtendedAttributes] = None,
    ccs_path: Optional[Path] = None
) -> OperationResult:
    """
    Pure signing API - no device-specific logic.

    This function provides a device-agnostic interface for signing binaries.
    All device-specific logic should be handled by adapters before calling this.

    Args:
        image_path: Path to input binary
        output_path: Directory where signed binary will be written
        signature: Signature configuration (algorithm, keys, revisions)
        metadata: Image metadata (load address, architecture, boot mode)
        session: Session/keystore information
        encryption: Optional encryption configuration
        extended: Optional device-specific attributes as key-value pairs
        ccs_path: Optional path to CCS installation (for ELF processing)

    Returns:
        OperationResult with success status and details
    """
    try:
        device_name = extended.get('soc_id') if extended else None

        if not device_name:
            return OperationResult.error_result("Device name (soc_id) required in extended attributes")

        if device_name == 'f29h85x':
            return _sign_f29h85x(
                image_path, output_path, signature, metadata,
                session, encryption, extended, ccs_path
            )
        elif device_name == 'am26x':
            return _sign_am26x(
                image_path, output_path, signature, metadata,
                session, encryption, extended, ccs_path
            )
        else:
            return OperationResult.error_result(f"Unsupported device: {device_name}")

    except Exception as e:
        return OperationResult.error_result(f"Signing failed: {str(e)}")


def _sign_f29h85x(
    image_path: Path,
    output_path: Path,
    signature: SignatureConfig,
    metadata: ImageMetadata,
    session: SessionInfo,
    encryption: Optional[EncryptionConfig],
    extended: Optional[ExtendedAttributes],
    ccs_path: Optional[Path]
) -> OperationResult:
    """Sign binary for F29H85x device"""
    try:
        from apps.tifs.sign_encrypt_f29.sign_encrypt import sign_encrypt_binary

        core_map = {
            Architecture.C29: "C29",
            Architecture.ARM_HSM: "HSM"
        }
        core = core_map.get(metadata.target_architecture, "C29")

        boot_map = {
            BootMode.FLASH: "FLASH",
            BootMode.RAM: "RAM"
        }
        boot = boot_map.get(metadata.boot_mode, "FLASH")

        input_format = "ELF" if str(image_path).endswith('.out') else "BIN"

        params = {
            'image': str(image_path),
            'input_format': input_format,
            'core': core,
            'boot': boot,
            'keyrev': str(signature.key_revision),
            'swrv': str(signature.software_revision),
            'loadaddr': hex(metadata.load_address),
            'output_path': str(output_path),
            'debug': signature.debug_options or "DBG_SOC_DEFAULT"
        }

        if ccs_path and input_format == "ELF":
            params['ccs_path'] = str(ccs_path)

        if encryption and encryption.enabled:
            if core == "HSM":
                params['fw_enc'] = True
                params['fw_enc_key'] = str(encryption.key_file)
            else:
                params['sbl_enc'] = True
                params['enc_key'] = str(encryption.key_file)

            if encryption.iv_salt:
                params['kd_salt'] = str(encryption.iv_salt)

        if extended:
            if extended.get('fw_type'):
                params['fw_type'] = extended.get('fw_type')
            if extended.get('ext_otp'):
                params['ext_otp'] = extended.get('ext_otp')

        if session.is_development:
            params['development_session'] = True
            if session.smpk_algorithm:
                params['smpk_algo'] = DEVICE_CONFIGS['f29h85x'].get_backend_algo(session.smpk_algorithm)
            if session.bmpk_algorithm:
                params['bmpk_algo'] = DEVICE_CONFIGS['f29h85x'].get_backend_algo(session.bmpk_algorithm)
        else:
            if session.session_name:
                params['session'] = session.session_name
            if session.session_password:
                params['password'] = session.session_password

        success, message = sign_encrypt_binary(**params)

        if success:
            signed_file = output_path / f"{image_path.stem}_signed{image_path.suffix}"
            return OperationResult.success_result(
                message=message,
                output_path=signed_file
            )
        else:
            return OperationResult.error_result(message)

    except Exception as e:
        return OperationResult.error_result(f"F29H85x signing failed: {str(e)}")


def _sign_am26x(
    image_path: Path,
    output_path: Path,
    signature: SignatureConfig,
    metadata: ImageMetadata,
    session: SessionInfo,
    encryption: Optional[EncryptionConfig],
    extended: Optional[ExtendedAttributes],
    ccs_path: Optional[Path]
) -> OperationResult:
    """Sign binary for AM26x device"""
    return OperationResult.error_result("AM26x signing not yet implemented")


def generate_certificate(
    request: CertificateRequest,
    session: SessionInfo
) -> OperationResult:
    """
    Generate a device-specific certificate.

    Args:
        request: Certificate generation request
        session: Session/keystore information

    Returns:
        OperationResult with success status and details
    """
    try:
        device_name = request.extended.get('soc_id') if request.extended else None

        if not device_name:
            return OperationResult.error_result("Device name (soc_id) required")

        if device_name == 'f29h85x':
            return _generate_cert_f29h85x(request, session)
        else:
            return OperationResult.error_result(f"Unsupported device: {device_name}")

    except Exception as e:
        return OperationResult.error_result(f"Certificate generation failed: {str(e)}")


def _generate_cert_f29h85x(
    request: CertificateRequest,
    session: SessionInfo
) -> OperationResult:
    """Generate OTP keywriter certificate for F29H85x."""
    try:
        from apps.spt.gencert import generate_certificate as spt_generate_certificate
        from pathlib import Path

        tifek_path = Path(str(request.public_keys[0])) if request.public_keys else None
        if not tifek_path:
            return OperationResult.error_result("ti_fek_public_pem is required")

        msv = request.extended.get('msv', '0x00000') if request.extended else '0x00000'
        output_dir = Path(str(request.output_path))

        # Determine session params
        if session.is_development:
            session_name = 'Development'
            session_password = 'develop123#'
        else:
            session_name = session.session_name or 'Development'
            session_password = session.session_password or 'develop123#'

        # Build flag dicts from request.flags
        flags = request.flags or []
        smpk_info = {"flag": "yes" if "smpk" in flags else "no", "wp": "no", "rp": "no", "ovrd": "no"}
        if "s_protect" in flags:
            smpk_info["wp"] = "yes"
            smpk_info["rp"] = "yes"
        smek_info = {"flag": "yes" if "smek" in flags else "no", "wp": "no", "rp": "no", "ovrd": "no"}
        if "smek_protect" in flags:
            smek_info["wp"] = "yes"
            smek_info["rp"] = "yes"
        bmpk_info = {"flag": "yes" if "bmpk" in flags else "no", "wp": "no", "rp": "no", "ovrd": "no"}
        if "b_protect" in flags:
            bmpk_info["wp"] = "yes"
            bmpk_info["rp"] = "yes"
        bmek_info = {"flag": "yes" if "bmek" in flags else "no", "wp": "no", "rp": "no", "ovrd": "no"}
        if "bmek_protect" in flags:
            bmek_info["wp"] = "yes"
            bmek_info["rp"] = "yes"

        spt_generate_certificate(
            session=session_name,
            password=session_password,
            msv=msv,
            use_hsm=False,
            output_dir_path=output_dir,
            tifek_pub_path=tifek_path,
            device="f29h85x",
            smpk_flags_dict=smpk_info,
            smek_flags_dict=smek_info,
            bmpk_flags_dict=bmpk_info,
            bmek_flags_dict=bmek_info,
            generate_secondary_cert=(bmpk_info["flag"] == "yes"),
        )

        cert_file = request.output_path / "final_certificate.bin"
        return OperationResult.success_result(
            message="Certificate generated successfully",
            output_path=cert_file,
        )

    except Exception as e:
        return OperationResult.error_result(f"F29H85x cert generation failed: {str(e)}")


def encrypt_binary(
    image_path: Path,
    output_path: Path,
    encryption: EncryptionConfig,
    session: SessionInfo,
    extended: Optional[ExtendedAttributes] = None,
) -> OperationResult:
    """
    Encrypt a binary image using the configured encryption settings.

    This function provides a device-agnostic interface for encrypting binaries.
    Device-specific logic is dispatched based on soc_id in extended attributes.

    Args:
        image_path: Path to input binary
        output_path: Path where encrypted binary will be written
        encryption: Encryption configuration (algorithm, key, salt, padding)
        session: Session/keystore information
        extended: Optional device-specific attributes

    Returns:
        OperationResult with success status and details
    """
    try:
        device_name = extended.get('soc_id') if extended else None

        if not device_name:
            return OperationResult.error_result(
                "Device name (soc_id) required in extended attributes"
            )

        if device_name == 'f29h85x':
            return _encrypt_f29h85x(
                image_path, output_path, encryption, session, extended
            )
        else:
            return OperationResult.error_result(
                f"Encryption not supported for device: {device_name}"
            )

    except Exception as e:
        return OperationResult.error_result(f"Encryption failed: {str(e)}")


def _encrypt_f29h85x(
    image_path: Path,
    output_path: Path,
    encryption: EncryptionConfig,
    session: SessionInfo,
    extended: Optional[ExtendedAttributes],
) -> OperationResult:
    """Encrypt binary for F29H85x device."""
    try:
        from tisecprov.crypto import ManufacturerKeys
        from tisecprov.encryption_ops import (
            encrypt_binary_raw, PaddingByte, EncryptionResult,
        )

        # Read encryption key from file
        if not encryption.key_file or not encryption.key_file.exists():
            return OperationResult.error_result(
                "Encryption key file is required and must exist"
            )

        with open(encryption.key_file, "rb") as f:
            enc_key = f.read()

        # Read salt from file if provided
        salt = None
        if encryption.iv_salt and encryption.iv_salt.exists():
            with open(encryption.iv_salt, "r") as f:
                salt_hex = f.read().strip('\n')
            salt = bytes.fromhex(salt_hex)

        # Determine padding mode and R-string from encryption_mode in extended
        encryption_mode = extended.get('encryption_mode', 'sbl_enc') if extended else 'sbl_enc'

        if encryption_mode in ('sbl_enc', 'tifs_enc'):
            padding_byte = PaddingByte.ZERO
            include_r_string = True
            force_pad = True
        elif encryption_mode == 'fw_enc':
            padding_byte = PaddingByte.FF
            include_r_string = False
            force_pad = False
        else:
            return OperationResult.error_result(
                f"Unknown encryption mode: {encryption_mode}"
            )

        # Read input binary
        if not image_path.exists():
            return OperationResult.error_result(
                f"Input file not found: {image_path}"
            )

        with open(image_path, "rb") as f:
            plaintext = f.read()

        # Encrypt using raw key approach (file-based workflow).
        # NOTE: For session/HSM-based encryption (where the key lives in a
        # CryptoInterface rather than a file), use encrypt_binary() from
        # encryption_ops instead.  That path is not yet wired up here.
        result: EncryptionResult = encrypt_binary_raw(
            plaintext=plaintext,
            key=enc_key,
            padding_mode=padding_byte,
            salt=salt,
            include_r_string=include_r_string,
            force_pad=force_pad,
        )

        # Write encrypted output
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "wb") as f:
            f.write(result.ciphertext)

        metadata = {
            'iv': result.iv.hex(),
            'original_size': result.original_size,
            'encryption_mode': encryption_mode,
        }
        if result.r_string:
            metadata['r_string'] = result.r_string.hex()
        if result.salt:
            metadata['salt'] = result.salt.hex()

        return OperationResult.success_result(
            message=f"Binary encrypted successfully: {output_file}",
            output_path=output_file,
            **metadata,
        )

    except Exception as e:
        return OperationResult.error_result(
            f"F29H85x encryption failed: {str(e)}"
        )


def sign_sec_cfg(
    image_path: Path,
    output_path: Path,
    signature: SignatureConfig,
    session: SessionInfo,
    extended: Optional[ExtendedAttributes] = None,
    ccs_path: Optional[Path] = None,
    boot_mode: str = "FLASH"
) -> OperationResult:
    """
    Sign security configuration binary.

    Args:
        image_path: Path to sec-cfg image (.out file)
        output_path: Directory for output
        signature: Signature configuration
        session: Session information
        extended: Optional device-specific attributes
        ccs_path: Path to CCS installation
        boot_mode: Boot mode (FLASH/RAM)

    Returns:
        OperationResult with success status
    """
    try:
        device_name = extended.get('soc_id') if extended else None

        if not device_name:
            return OperationResult.error_result("Device name required")

        if device_name == 'f29h85x':
            return _sign_seccfg_f29h85x(
                image_path, output_path, signature, session, extended, ccs_path, boot_mode
            )
        else:
            return OperationResult.error_result(f"Sec-cfg signing not supported for {device_name}")

    except Exception as e:
        return OperationResult.error_result(f"Sec-cfg signing failed: {str(e)}")


def _sign_seccfg_f29h85x(
    image_path: Path,
    output_path: Path,
    signature: SignatureConfig,
    session: SessionInfo,
    extended: Optional[ExtendedAttributes],
    ccs_path: Optional[Path],
    boot_mode: str
) -> OperationResult:
    """Sign sec-cfg for F29H85x"""
    try:
        from apps.tifs.sign_encrypt_f29.sign_encrypt import sign_sec_cfg_binary as f29_sign_sec_cfg

        params = {
            'image': str(image_path),
            'swrv': str(signature.software_revision),
            'keyrev': str(signature.key_revision),
            'boot': boot_mode,
            'output_path': str(output_path)
        }

        if ccs_path:
            params['ccs_path'] = str(ccs_path)

        if session.is_development:
            params['development_session'] = True
            if session.smpk_algorithm:
                params['smpk_algo'] = DEVICE_CONFIGS['f29h85x'].get_backend_algo(session.smpk_algorithm)
            if session.bmpk_algorithm:
                params['bmpk_algo'] = DEVICE_CONFIGS['f29h85x'].get_backend_algo(session.bmpk_algorithm)
        else:
            if session.session_name:
                params['session'] = session.session_name
            if session.session_password:
                params['password'] = session.session_password

        success, message = f29_sign_sec_cfg(**params)

        if success:
            seccfg_file = output_path / "seccfg.bin"
            return OperationResult.success_result(
                message=message,
                output_path=seccfg_file
            )
        else:
            return OperationResult.error_result(message)

    except Exception as e:
        return OperationResult.error_result(f"F29H85x sec-cfg signing failed: {str(e)}")
