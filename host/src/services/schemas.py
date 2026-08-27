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
Shared Pydantic models for both services.

These mirror the schemas declared in ``docs/api/openapi.yaml`` so the
FastAPI-generated OpenAPI stays aligned with the frozen contract.
"""

from datetime import datetime
from typing import Dict, Literal, Optional

from pydantic import BaseModel, Field


class ArtifactRef(BaseModel):
    """Reference to a file stored in the artifact store."""

    id: str = Field(..., description="UUID of the stored artifact")
    filename: Optional[str] = None
    content_type: Optional[str] = None
    size: Optional[int] = None


class ErrorDetail(BaseModel):
    """Machine-readable error detail (matches the frozen contract)."""

    code: str
    message: str
    details: Optional[Dict] = None


class ErrorResponse(BaseModel):
    """Standard error envelope."""

    error: ErrorDetail


class PortInfo(BaseModel):
    """A serial port."""

    name: str
    description: str = ""
    hwid: Optional[str] = None


class DeviceInfo(BaseModel):
    """An installed device addon."""

    name: str
    family: str
    boot_modes: list[str] = []
    addon_version: Optional[str] = None


class UartConnection(BaseModel):
    """UART connection details for target operations."""

    port: str
    targetbaud: int = 115200
    timeout: Optional[int] = None
    input_parameter: Optional[str] = Field(
        default=None, description="Comma-separated provisioning input sequence, e.g. 3,5,6,7"
    )


class JtagConnection(BaseModel):
    """JTAG/CCS connection details for target operations."""

    ccs_path: str
    verbose: bool = False
    ccxml_path: Optional[str] = None
    target_config_path: Optional[str] = None


JobStatus = Literal["queued", "running", "succeeded", "failed", "cancelled"]


class LogLine(BaseModel):
    """A single job log line."""

    seq: int
    timestamp: datetime
    level: str = "info"
    message: str


class Job(BaseModel):
    """An asynchronous operation (created on both services)."""

    id: str
    service: Literal["crypto", "target"]
    type: str
    status: JobStatus
    progress: int = 0
    exit_code: Optional[int] = None
    result: Optional[Dict] = None
    error: Optional[ErrorResponse] = None
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    logs_url: Optional[str] = None
    stream_url: Optional[str] = None