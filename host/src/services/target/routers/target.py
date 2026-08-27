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
Target endpoints (Backend #2): discovery, target state and provisioning jobs.
"""

from fastapi import APIRouter, Depends

from services.jobs import job_manager, to_job_response
from services.target import targetops
from services.target.auth import require_api_key
from services.target.schemas import (
    CcsOperationRequest,
    CodeProvisioningRequest,
    DeviceTypeJtagRequest,
    DeviceTypeUartRequest,
    DownloadRequest,
    KeyProvisioningRequest,
    SocIdRequest,
    ValidateRecoveryRequest,
)

router = APIRouter(
    tags=["target"],
    dependencies=[Depends(require_api_key)],
)


@router.get(
    "/ports",
    response_model=list,
    operation_id="listPorts",
    summary="List available serial ports (cross-platform)",
)
def list_ports() -> list:
    return targetops.list_ports()


@router.get(
    "/devices",
    response_model=list,
    operation_id="listTargetDevices",
    summary="List installed device addons",
)
def list_devices() -> list:
    return targetops.list_devices()


@router.post(
    "/targets/socid",
    response_model=dict,
    status_code=202,
    operation_id="getSoCId",
    summary="Retrieve SoC ID from a device via UART (getSoCId)",
)
def get_soc_id(req: SocIdRequest) -> dict:
    job = job_manager.submit("target", "get_soc_id", lambda ctx: targetops.get_soc_id(ctx, req))
    return to_job_response(job)


@router.post(
    "/targets/type/uart",
    response_model=dict,
    status_code=202,
    operation_id="getDeviceTypeUart",
    summary="Detect device type via UART (devTypeUART)",
)
def get_device_type_uart(req: DeviceTypeUartRequest) -> dict:
    job = job_manager.submit(
        "target", "device_type_uart", lambda ctx: targetops.device_type_uart(ctx, req)
    )
    return to_job_response(job)


@router.post(
    "/targets/type/jtag",
    response_model=dict,
    status_code=202,
    operation_id="getDeviceTypeJtag",
    summary="Detect device type via JTAG (devTypeJTAG)",
)
def get_device_type_jtag(req: DeviceTypeJtagRequest) -> dict:
    job = job_manager.submit(
        "target", "device_type_jtag", lambda ctx: targetops.device_type_jtag(ctx, req)
    )
    return to_job_response(job)


@router.post(
    "/targets/{device}/key-provisioning",
    response_model=dict,
    status_code=202,
    operation_id="keyProvisioning",
    summary="Provision keys into the target (uart_keyprov / jtag_keyprov)",
)
def key_provisioning(device: str, req: KeyProvisioningRequest) -> dict:
    job = job_manager.submit(
        "target",
        "key_provisioning",
        lambda ctx: targetops.key_provisioning(ctx, device, req),
    )
    return to_job_response(job)


@router.post(
    "/targets/{device}/code-provisioning",
    response_model=dict,
    status_code=202,
    operation_id="codeProvisioning",
    summary="Provision firmware code into the target (uart_codeprov / jtag_codeprov)",
)
def code_provisioning(device: str, req: CodeProvisioningRequest) -> dict:
    job = job_manager.submit(
        "target",
        "code_provisioning",
        lambda ctx: targetops.code_provisioning(ctx, device, req),
    )
    return to_job_response(job)


@router.post(
    "/targets/recovery/enable",
    response_model=dict,
    status_code=202,
    operation_id="enableDeviceRecovery",
    summary="Enable device recovery mode (endevrecov)",
)
def enable_recovery(req: CcsOperationRequest) -> dict:
    job = job_manager.submit(
        "target", "enable_recovery", lambda ctx: targetops.enable_recovery(ctx, req)
    )
    return to_job_response(job)


@router.post(
    "/targets/recovery/uid-secap",
    response_model=dict,
    status_code=202,
    operation_id="getUidSecap",
    summary="Retrieve device UID and security capabilities (getUIDSecap)",
)
def get_uid_secap(req: CcsOperationRequest) -> dict:
    job = job_manager.submit(
        "target", "get_uid_secap", lambda ctx: targetops.get_uid_secap(ctx, req)
    )
    return to_job_response(job)


@router.post(
    "/targets/recovery/validate",
    response_model=dict,
    status_code=202,
    operation_id="validateDeviceRecoveryCert",
    summary="Send and validate a device recovery certificate (valdcert)",
)
def validate_recovery(req: ValidateRecoveryRequest) -> dict:
    job = job_manager.submit(
        "target", "validate_recovery", lambda ctx: targetops.validate_recovery(ctx, req)
    )
    return to_job_response(job)


@router.post(
    "/targets/download",
    response_model=dict,
    status_code=202,
    operation_id="downloadBinary",
    summary="Download a bootloader/keywriter binary into the target (download)",
)
def download(req: DownloadRequest) -> dict:
    job = job_manager.submit("target", "download", lambda ctx: targetops.download(ctx, req))
    return to_job_response(job)