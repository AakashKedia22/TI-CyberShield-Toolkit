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
Target operations for Backend #2.

Every function is a *job function*: it takes a ``JobContext`` (for logging,
progress and cancellation) plus the request model, and returns a result dict
or raises ``APIError``. The core provisioning/recovery modules are imported
lazily and run with the job's ``cancel_event`` wired through.
"""

from pathlib import Path
from types import SimpleNamespace
from typing import Dict, List

from services.api import APIError
from services.crypto.artifacts import get_artifact_store
from services.jobs import JobContext
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

DEVICE = "f29h85x"


def _resolve(ref) -> Path:
    """Resolve an artifact ref to its on-disk path (shared artifact store)."""
    try:
        path, _meta = get_artifact_store().get(ref.id)
        return path
    except KeyError:
        raise APIError(404, "ARTIFACT_NOT_FOUND", f"Artifact {ref.id} not found")


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------
def list_ports() -> List[Dict]:
    """List available serial ports (cross-platform names)."""
    import serial.tools.list_ports

    ports = []
    for port in serial.tools.list_ports.comports():
        ports.append(
            {
                "name": port.device,
                "description": port.description or "",
                "hwid": port.hwid or None,
            }
        )
    return ports


def list_devices() -> List[Dict]:
    """List installed device addons (falls back to the known device set)."""
    addon_base = Path.home() / "ti" / "TICST" / "addons"
    devices = []
    if addon_base.exists():
        for entry in sorted(addon_base.iterdir()):
            if entry.is_dir():
                name = entry.name
                devices.append(
                    {
                        "name": name,
                        "family": "asm" if name.startswith("f29") else "sitara",
                        "boot_modes": ["UART", "JTAG"]
                        if name.startswith("f29")
                        else ["UART"],
                    }
                )
    if not devices:
        devices.append({"name": DEVICE, "family": "asm", "boot_modes": ["UART", "JTAG"]})
    return devices


# ---------------------------------------------------------------------------
# Target state
# ---------------------------------------------------------------------------
def get_soc_id(ctx: JobContext, req: SocIdRequest) -> Dict:
    """Read the SoC ID from the target via UART (getSoCId)."""
    from apps.spt.parseSoCId import getSoCId

    args = SimpleNamespace(
        port=req.port,
        baudrate=req.baudrate,
        parity="N",
        stopbits="1",
        timeout=req.timeout,
    )
    ctx.log(f"Reading SoC ID from {req.port} (timeout {req.timeout}s)")
    try:
        soc_id = getSoCId(args)
    except Exception as exc:
        raise APIError(500, "INTERNAL", f"SoC ID read failed: {exc}")
    if not soc_id:
        raise APIError(502, "TARGET_TIMEOUT", "No SoC ID received from target")
    ctx.log(f"SoC ID: {soc_id}")
    return {"soc_id": soc_id}


def device_type_uart(ctx: JobContext, req: DeviceTypeUartRequest) -> Dict:
    """Detect device type via UART (devTypeUART)."""
    from apps.tifs.kp_cp_f29h85x.uart_provisioning import run_get_device_type_uart

    kernel = _resolve(req.uart_kernel)
    ctx.log(f"Detecting device type over UART on {req.port}")
    output = run_get_device_type_uart(
        str(kernel), DEVICE, req.port, str(req.targetbaud), cancel_event=ctx.cancel_event
    )
    ctx.set_progress(100)
    return {"device": DEVICE, "output": output}


def device_type_jtag(ctx: JobContext, req: DeviceTypeJtagRequest) -> Dict:
    """Detect device type via JTAG (devTypeJTAG)."""
    from apps.tifs.kp_cp_f29h85x.jtag_provisioning import run_get_device_type_jtag

    ctx.log(f"Detecting device type over JTAG (CCS: {req.ccs_path})")
    success, output = run_get_device_type_jtag(
        req.ccs_path, verbose=req.verbose, cancel_event=ctx.cancel_event
    )
    ctx.set_progress(100)
    if not success:
        raise APIError(502, "TARGET_ERROR", output)
    return {"device": DEVICE, "output": output}


# ---------------------------------------------------------------------------
# Provisioning
# ---------------------------------------------------------------------------
def key_provisioning(ctx: JobContext, device: str, req: KeyProvisioningRequest) -> Dict:
    """Provision keys into the target (uart_keyprov / jtag_keyprov)."""
    if req.interface == "uart":
        if not req.uart_kernel or not req.uart:
            raise APIError(
                400,
                "INVALID_ARGUMENT",
                "interface=uart requires uart_kernel and uart.port",
            )
        from apps.tifs.kp_cp_f29h85x.uart_provisioning import run_key_provisioning_uart

        otp_kw = _resolve(req.otp_kw_bin)
        certificate = _resolve(req.certificate)
        kernel = _resolve(req.uart_kernel)
        ctx.log(f"UART key provisioning on {req.uart.port}")
        code, output = run_key_provisioning_uart(
            str(kernel),
            str(certificate),
            str(otp_kw),
            req.uart.port,
            device=device,
            baudrate=str(req.uart.targetbaud),
            cancel_event=ctx.cancel_event,
        )
        ctx.set_progress(100)
        if code != 0:
            raise APIError(
                502, "TARGET_ERROR", output or f"key provisioning failed (exit {code})"
            )
        return {"device_state": "HSKP", "return_code": code, "output": output}

    if not req.jtag_kernel or not req.jtag:
        raise APIError(
            400, "INVALID_ARGUMENT", "interface=jtag requires jtag_kernel and jtag.ccs_path"
        )
    from apps.tifs.kp_cp_f29h85x.jtag_provisioning import run_key_provisioning_jtag

    otp_kw = _resolve(req.otp_kw_bin)
    certificate = _resolve(req.certificate)
    kernel = _resolve(req.jtag_kernel)
    ctx.log(f"JTAG key provisioning (CCS: {req.jtag.ccs_path})")
    success, output = run_key_provisioning_jtag(
        str(otp_kw),
        str(certificate),
        str(kernel),
        req.jtag.ccs_path,
        verbose=req.jtag.verbose,
        ccxml_path=req.jtag.ccxml_path,
        cancel_event=ctx.cancel_event,
    )
    ctx.set_progress(100)
    if not success:
        raise APIError(502, "TARGET_ERROR", output)
    return {"device_state": "HSKP", "output": output}


def code_provisioning(ctx: JobContext, device: str, req: CodeProvisioningRequest) -> Dict:
    """Provision firmware code into the target (uart_codeprov / jtag_codeprov)."""
    if req.interface == "uart":
        if not req.uart_kernel or not req.uart:
            raise APIError(
                400,
                "INVALID_ARGUMENT",
                "interface=uart requires uart_kernel and uart.port",
            )
        from apps.tifs.kp_cp_f29h85x.uart_provisioning import run_code_provisioning_uart

        hsm_image = _resolve(req.hsm_image)
        hsm_cpu = _resolve(req.hsm_cpu_code)
        c29_cpu = _resolve(req.c29_cpu_code)
        seccfg = _resolve(req.seccfg)
        c29_cpu3 = _resolve(req.c29_cpu3_code) if req.c29_cpu3_code else None
        kernel = _resolve(req.uart_kernel)
        ctx.log(f"UART code provisioning on {req.uart.port}")
        code, output = run_code_provisioning_uart(
            str(kernel),
            str(hsm_image),
            str(hsm_cpu),
            str(c29_cpu),
            str(seccfg),
            device,
            req.uart.port,
            str(req.uart.targetbaud),
            req.uart.input_parameter if req.uart.input_parameter else "3,5,6,7",
            c29_cpu3_code=str(c29_cpu3) if c29_cpu3 else None,
            cancel_event=ctx.cancel_event,
        )
        ctx.set_progress(100)
        if code != 0:
            raise APIError(
                502, "TARGET_ERROR", output or f"code provisioning failed (exit {code})"
            )
        return {"return_code": code, "output": output}

    if not req.jtag_kernel or not req.jtag:
        raise APIError(
            400, "INVALID_ARGUMENT", "interface=jtag requires jtag_kernel and jtag.ccs_path"
        )
    from apps.tifs.kp_cp_f29h85x.jtag_provisioning import run_code_provisioning_jtag

    hsm_image = _resolve(req.hsm_image)
    hsm_cpu = _resolve(req.hsm_cpu_code)
    c29_cpu = _resolve(req.c29_cpu_code)
    seccfg = _resolve(req.seccfg)
    c29_cpu3 = _resolve(req.c29_cpu3_code) if req.c29_cpu3_code else None
    kernel = _resolve(req.jtag_kernel)
    ctx.log(f"JTAG code provisioning (CCS: {req.jtag.ccs_path})")
    success, output = run_code_provisioning_jtag(
        str(hsm_image),
        str(kernel),
        req.jtag.ccs_path,
        hsm_cpu_code_path=str(hsm_cpu),
        c29_cpu_code_path=str(c29_cpu),
        seccfg_path=str(seccfg),
        c29_cpu3_code_path=str(c29_cpu3) if c29_cpu3 else None,
        verbose=req.jtag.verbose,
        cancel_event=ctx.cancel_event,
    )
    ctx.set_progress(100)
    if not success:
        raise APIError(502, "TARGET_ERROR", output)
    return {"output": output}


# ---------------------------------------------------------------------------
# Device recovery
# ---------------------------------------------------------------------------
def enable_recovery(ctx: JobContext, req: CcsOperationRequest) -> Dict:
    """Enable device recovery mode (endevrecov)."""
    from apps.tifs.f29_device_recovery.device_recovery_flow import enable_device_recovery

    ctx.log(f"Enabling device recovery (CCS: {req.ccs_path})")
    success, output = enable_device_recovery(req.ccs_path, req.verbose)
    ctx.set_progress(100)
    if not success:
        raise APIError(502, "TARGET_ERROR", output)
    return {"output": output}


def get_uid_secap(ctx: JobContext, req: CcsOperationRequest) -> Dict:
    """Retrieve device UID and security capabilities (getUIDSecap)."""
    from apps.tifs.f29_device_recovery.device_recovery_flow import (
        run_get_device_uid_secap,
    )

    ctx.log(f"Reading UID/Secap (CCS: {req.ccs_path})")
    success, output = run_get_device_uid_secap(req.ccs_path, req.verbose)
    ctx.set_progress(100)
    if not success:
        raise APIError(502, "TARGET_ERROR", output)
    return {"output": output}


def validate_recovery(ctx: JobContext, req: ValidateRecoveryRequest) -> Dict:
    """Send and validate a device recovery certificate (valdcert)."""
    from apps.tifs.f29_device_recovery.device_recovery_flow import (
        send_device_recovery_cert,
    )

    cert = _resolve(req.dev_recov_cert)
    ctx.log(f"Validating device recovery certificate (CCS: {req.ccs_path})")
    success, output = send_device_recovery_cert(str(cert), req.ccs_path, req.verbose)
    ctx.set_progress(100)
    if not success:
        raise APIError(502, "TARGET_ERROR", output)
    return {"output": output}


def download(ctx: JobContext, req: DownloadRequest) -> Dict:
    """Download a bootloader/keywriter binary into the target (download)."""
    from apps.spt.download import download_binary

    bootloader = _resolve(req.bootloader)
    ctx.log(f"Downloading bootloader to {req.port}")
    args = SimpleNamespace(serial_port=req.port, bootloader=str(bootloader))
    try:
        download_binary(args)
    except Exception as exc:
        raise APIError(502, "TARGET_ERROR", str(exc))
    ctx.set_progress(100)
    return {"port": req.port, "status": "transferred"}