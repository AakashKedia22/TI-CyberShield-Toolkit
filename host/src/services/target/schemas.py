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

"""Pydantic request models for the target service (Backend #2)."""

from typing import Literal, Optional

from pydantic import BaseModel, Field

from services.schemas import ArtifactRef, JtagConnection, UartConnection


class SocIdRequest(BaseModel):
    """Read the SoC ID from a target via UART."""

    port: str
    baudrate: int = 115200
    timeout: int = 10


class DeviceTypeUartRequest(BaseModel):
    """Detect device type via UART."""

    port: str
    targetbaud: int = 115200
    uart_kernel: ArtifactRef


class DeviceTypeJtagRequest(BaseModel):
    """Detect device type via JTAG."""

    ccs_path: str
    verbose: bool = False


class KeyProvisioningRequest(BaseModel):
    """Provision keys into a target (uart_keyprov / jtag_keyprov)."""

    interface: Literal["uart", "jtag"]
    otp_kw_bin: ArtifactRef
    certificate: ArtifactRef
    uart_kernel: Optional[ArtifactRef] = None
    jtag_kernel: Optional[ArtifactRef] = None
    uart: Optional[UartConnection] = None
    jtag: Optional[JtagConnection] = None


class CodeProvisioningRequest(BaseModel):
    """Provision firmware code into a target (uart_codeprov / jtag_codeprov)."""

    interface: Literal["uart", "jtag"]
    hsm_image: ArtifactRef
    hsm_cpu_code: ArtifactRef
    c29_cpu_code: ArtifactRef
    c29_cpu3_code: Optional[ArtifactRef] = None
    seccfg: ArtifactRef
    uart_kernel: Optional[ArtifactRef] = None
    jtag_kernel: Optional[ArtifactRef] = None
    uart: Optional[UartConnection] = None
    jtag: Optional[JtagConnection] = None


class CcsOperationRequest(BaseModel):
    """A CCS-driven device recovery operation."""

    ccs_path: str
    verbose: bool = False


class ValidateRecoveryRequest(BaseModel):
    """Send and validate a device recovery certificate."""

    ccs_path: str
    dev_recov_cert: ArtifactRef
    verbose: bool = False


class DownloadRequest(BaseModel):
    """Download a bootloader/keywriter binary into a target via serial."""

    port: str
    bootloader: ArtifactRef = Field(..., description="Path to the key writer binary")