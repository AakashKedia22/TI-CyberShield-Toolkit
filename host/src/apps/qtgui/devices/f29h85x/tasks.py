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
Device-specific task callable registry for f29h85x.

All functions follow normalised signatures:
  provisioning: (params: dict) -> (success: bool, output: str)
  detection:    (connection_info: dict) -> (success: bool, device_state: str|None, error: str|None)
"""
import os
from apps.tifs.kp_cp_f29h85x.uart_provisioning import (
    run_key_provisioning_uart, run_code_provisioning_uart, run_get_device_type_uart,
)
from apps.tifs.kp_cp_f29h85x.jtag_provisioning import (
    run_key_provisioning_jtag, run_code_provisioning_jtag, run_get_device_type_jtag,
)

# ---------------------------------------------------------------------------
# Provisioning wrappers
# ---------------------------------------------------------------------------

def _run_uart_keyprov(params: dict) -> tuple:
    try:
        rc, output = run_key_provisioning_uart(
            params.get("uart_kernel"), params.get("certificate"), params.get("otp_kw_bin"),
            params.get("port"), params.get("device", "f29h85x").lower(),
            params.get("baudrate", "115200"), log_file="kp_logs.txt",
            cancel_event=params.get("_cancel_event"),
            register_proc_cb=params.get("_register_proc"),
        )
        return rc == 0, output
    except Exception as e:
        return False, f"UART key provisioning failed: {e}"


def _run_jtag_keyprov(params: dict) -> tuple:
    tcp = params.get("target_config_path", "")
    ccxml = tcp if tcp and os.path.exists(tcp) else None
    return run_key_provisioning_jtag(
        params.get("otp_kw_bin"), params.get("certificate"), params.get("jtag_kernel"),
        params.get("ccs_path"), params.get("verbose", True),
        log_file="kp_logs.txt", ccxml_path=ccxml,
        cancel_event=params.get("_cancel_event"),
        register_proc_cb=params.get("_register_proc"),
    )


def _run_uart_codeprov(params: dict) -> tuple:
    try:
        pids = ["3"]  # hsm_image always required
        if params.get("seccfg"):        pids.append("5")
        if params.get("hsm_cpu_code"):  pids.append("6")
        if params.get("c29_cpu_code"):  pids.append("7")
        if params.get("c29_cpu3_code"): pids.append("8")
        return_code, output = run_code_provisioning_uart(
            params.get("uart_kernel"), params.get("hsm_image"),
            params.get("hsm_cpu_code"), params.get("c29_cpu_code"), params.get("seccfg"),
            params.get("device", "f29h85x").lower(), params.get("port"),
            params.get("baudrate", "115200"), ",".join(pids),
            c29_cpu3_code=params.get("c29_cpu3_code"),
            cancel_event=params.get("_cancel_event"),
            register_proc_cb=params.get("_register_proc"),
        )
        return (return_code == 0), output
    except Exception as e:
        return False, f"UART code provisioning failed: {e}"


def _run_jtag_codeprov(params: dict) -> tuple:
    tcp = params.get("target_config_path", "")
    ccxml = tcp if tcp and os.path.exists(tcp) else None
    return run_code_provisioning_jtag(
        params.get("hsm_image"), params.get("jtag_kernel"), params.get("ccs_path"),
        hsm_cpu_code_path=params.get("hsm_cpu_code"),
        c29_cpu_code_path=params.get("c29_cpu_code"),
        seccfg_path=params.get("seccfg"),
        c29_cpu3_code_path=params.get("c29_cpu3_code"),
        verbose=params.get("verbose", True),
        log_file="cp_logs.txt", ccxml_path=ccxml,
        cancel_event=params.get("_cancel_event"),
        register_proc_cb=params.get("_register_proc"),
    )


# ---------------------------------------------------------------------------
# Detection wrappers — return (success, device_state | None, error | None)
# ---------------------------------------------------------------------------

_STATE_MAP = [
    (("HS_FS", "EMU_FS"), "HSFS"),
    (("HS_KP", "EMU_KP"), "HSKP"),
    (("HS_SE", "EMU_SE"), "HSSE"),
]


def _parse_state(output: str):
    for markers, state in _STATE_MAP:
        if any(m in output for m in markers):
            return state
    return None


def _detect_uart(connection_info: dict) -> tuple:
    from common.device_utils import get_device_output_dir
    try:
        signed_images = get_device_output_dir("f29h85x", "signedImages")
        uart_kernel = os.path.join(signed_images, "ram_based_uart_sbl.cert.bin")
        output = run_get_device_type_uart(
            uart_kernel=uart_kernel, device="f29h85x",
            port=connection_info.get("port"),
            baudrate=connection_info.get("baudrate", 115200),
            cancel_event=connection_info.get("_cancel_event"),
            register_proc_cb=connection_info.get("_register_proc"),
        )
        state = _parse_state(output)
        if state:
            return True, state, None
        return False, None, "Failed to detect device state from output"
    except Exception as e:
        return False, None, str(e)


def _detect_jtag(connection_info: dict) -> tuple:
    try:
        success, output = run_get_device_type_jtag(
            connection_info.get("ccs_path", ""), verbose=True,
            ccxml_path=connection_info.get("ccxml_path"),
            cancel_event=connection_info.get("_cancel_event"),
            register_proc_cb=connection_info.get("_register_proc"),
        )
        if success:
            return True, _parse_state(output) or "HSFS", None
        return False, None, output
    except Exception as e:
        return False, None, str(e)


# ---------------------------------------------------------------------------
# Public registries
# ---------------------------------------------------------------------------

TASK_SPECS: dict = {
    "uart_keyprov":  _run_uart_keyprov,
    "jtag_keyprov":  _run_jtag_keyprov,
    "uart_codeprov": _run_uart_codeprov,
    "jtag_codeprov": _run_jtag_codeprov,
}

DETECT_SPECS: dict = {
    "UART": {"fn": _detect_uart, "requires_reset": True},
    "JTAG": {"fn": _detect_jtag, "requires_reset": False},
}
