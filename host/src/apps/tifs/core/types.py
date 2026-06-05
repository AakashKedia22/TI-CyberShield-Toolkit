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

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Literal
from pathlib import Path
from enum import Enum


class Architecture(Enum):
    C29 = "c29"
    ARM_HSM = "arm_hsm"
    ARM_CORTEX_M = "arm_cortex_m"
    ARM_CORTEX_A = "arm_cortex_a"


class BootMode(Enum):
    FLASH = "flash"
    RAM = "ram"


class EncryptionAlgorithm(Enum):
    AES_256_CBC = "aes-256-cbc"


class PaddingMode(Enum):
    ZERO = "0x00"
    FF = "0xFF"
    PKCS7 = "pkcs7"


class SignatureAlgorithm(Enum):
    RSA4K = "rsa4k"
    ECDSA256R1 = "secp256r1"
    ECDSA384R1 = "secp384r1"
    ECDSA521R1 = "secp521r1"
    BRAINPOOL512 = "brainpool512"


class CertificateType(Enum):
    X509 = "x509"
    CUSTOM = "custom"
    SIMPLE = "simple"


@dataclass
class SignatureConfig:
    algorithm: SignatureAlgorithm
    key_revision: int
    software_revision: int
    certificate_type: CertificateType = CertificateType.X509
    debug_options: Optional[str] = None


@dataclass
class EncryptionConfig:
    enabled: bool
    algorithm: Optional[EncryptionAlgorithm] = None
    key_file: Optional[Path] = None
    iv_salt: Optional[Path] = None
    padding_mode: Optional[PaddingMode] = None


@dataclass
class ImageMetadata:
    load_address: int
    target_architecture: Architecture
    boot_mode: BootMode
    entry_point: Optional[int] = None
    image_size: Optional[int] = None


@dataclass
class ExtendedAttributes:
    attributes: Dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        return self.attributes.get(key, default)

    def set(self, key: str, value: Any):
        self.attributes[key] = value


@dataclass
class OperationResult:
    success: bool
    message: str = ""
    output_path: Optional[Path] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def success_result(message: str = "Operation completed successfully",
                      output_path: Optional[Path] = None,
                      **metadata) -> 'OperationResult':
        return OperationResult(
            success=True,
            message=message,
            output_path=output_path,
            metadata=metadata
        )

    @staticmethod
    def error_result(message: str, **metadata) -> 'OperationResult':
        return OperationResult(
            success=False,
            message=message,
            metadata=metadata
        )


@dataclass
class CertificateRequest:
    output_path: Path
    certificate_type: str
    public_keys: List[Path]
    security_version: int
    flags: List[str] = field(default_factory=list)
    extended: Optional[ExtendedAttributes] = None


@dataclass
class DeviceConfig:
    """Device-specific algorithm and capability metadata."""
    soc_id: str
    algo_map: Dict[SignatureAlgorithm, str]
    supported_encryption: List[EncryptionAlgorithm] = field(default_factory=list)
    supported_architectures: List[Architecture] = field(default_factory=list)

    def get_backend_algo(self, algo: SignatureAlgorithm) -> str:
        if algo not in self.algo_map:
            raise ValueError(
                f"Algorithm {algo.value} not supported for device {self.soc_id}. "
                f"Supported: {[a.value for a in self.algo_map]}"
            )
        return self.algo_map[algo]


# --- Device configurations ---

F29H85X_CONFIG = DeviceConfig(
    soc_id='f29h85x',
    algo_map={
        SignatureAlgorithm.RSA4K: 'rsa4k',
        SignatureAlgorithm.ECDSA256R1: 'secp256r1',
        SignatureAlgorithm.ECDSA384R1: 'secp384r1',
        SignatureAlgorithm.ECDSA521R1: 'secp521r1',
        SignatureAlgorithm.BRAINPOOL512: 'brainpool512',
    },
    supported_encryption=[EncryptionAlgorithm.AES_256_CBC],
    supported_architectures=[Architecture.C29, Architecture.ARM_HSM],
)

DEVICE_CONFIGS: Dict[str, DeviceConfig] = {
    'f29h85x': F29H85X_CONFIG,
}


@dataclass
class SessionInfo:
    keystore_path: Optional[Path] = None
    session_name: Optional[str] = None
    session_password: Optional[str] = None
    is_development: bool = False
    smpk_algorithm: Optional[SignatureAlgorithm] = None
    bmpk_algorithm: Optional[SignatureAlgorithm] = None
