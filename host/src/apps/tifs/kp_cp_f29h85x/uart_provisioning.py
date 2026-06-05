#!/usr/bin/env python3
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
UART Provisioning APIs

This module provides platform-independent Python APIs for running key provisioning
and code provisioning using the CCS scripting tools.
"""

import re
import subprocess
import os
import sys
import pathlib
import platform
import logging
import threading
from typing import Optional, Dict, List, Union, Tuple

# Import platform utilities
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))), "src"))
from common.platform_utils import (
    get_script_dir, normalize_path, join_path, get_temp_dir,
    run_command, get_uart_flash_programmer_path, get_log_redirect,
    kill_proc_tree, register_proc, unregister_proc, IS_WINDOWS,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get the path to the uart_flash_programmer
uart_flash_programmer_path = get_uart_flash_programmer_path()


def _popen_uart(command: str, cancel_event=None, notify_proc=None) -> "tuple[subprocess.Popen, dict]":
    """Start *command* in a new process group (POSIX) for reliable tree-kill.

    Returns ``(proc, popen_kwargs)`` where *popen_kwargs* were passed to Popen.
    Registers *proc* in the global atexit tracker automatically.
    If *notify_proc* is provided it is called with *proc* so callers can store
    the handle for on-demand cancellation.
    """
    popen_kwargs: dict = dict(
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    if not IS_WINDOWS:
        popen_kwargs["start_new_session"] = True

    proc = subprocess.Popen(command, **popen_kwargs)
    register_proc(proc)
    if notify_proc is not None:
        notify_proc(proc)
    return proc


def _drain_proc(proc: subprocess.Popen, cancel_event=None, timeout=None) -> str:
    """Read stdout line-by-line, printing each line (for StreamCapture).

    Kills *proc* and stops early if *cancel_event* is set.
    If *timeout* seconds elapse before the process finishes, the process tree
    is killed so the caller is not blocked indefinitely.
    Returns the full captured output.
    """
    timer = None
    if timeout is not None:
        timer = threading.Timer(timeout, lambda: kill_proc_tree(proc))
        timer.start()
    try:
        output_lines = []
        for line in iter(proc.stdout.readline, ""):
            if cancel_event is not None and cancel_event.is_set():
                kill_proc_tree(proc)
                break
            # Only forward to stdout when StreamCapture has replaced it (GUI streaming).
            # Avoids flooding the console during non-streaming operations.
            if sys.stdout is not sys.__stdout__:
                print(line, end="", flush=True)
            output_lines.append(line)
        proc.stdout.close()
        proc.wait()
        unregister_proc(proc)
        return "".join(output_lines)
    finally:
        if timer is not None:
            timer.cancel()


def run_code_provisioning_uart(uart_kernel, hsm_image, hsm_cpu_code, c29_cpu_code, seccfg,
                              device, port, baudrate, input_parameter, c29_cpu3_code=None,
                              log_file="cp_logs.txt",
                              cancel_event=None, register_proc_cb=None) -> str:
    """
    Run code provisioning using UART interface.

    Args:
        uart_kernel: Path to UART kernel file
        hsm_image: Path to HSM image file
        hsm_cpu_code: Path to HSM CPU code file
        c29_cpu_code: Path to C29 CPU code file
        seccfg: Path to security config file
        device: Target device name
        port: UART port
        baudrate: UART baudrate
        input_parameter: Input parameters for provisioning
        c29_cpu3_code: Path to C29 CPU3/CPU1 image file (optional, parameter 8)
        log_file: Path to log file

    Returns:
        str: Command output
    """
    # Determine the log file path based on environment
    if getattr(sys, 'frozen', False):
        # When running as PyInstaller bundle, use a path in the user's home directory
        import tempfile
        log_path = os.path.join(tempfile.gettempdir(), log_file)
    else:
        # In normal Python environment, use path relative to this file
        log_path = join_path(get_script_dir(), log_file)

    # Build command for the UART flash programmer
    command = f"{uart_flash_programmer_path} --device {device} --port {port} --kernel {uart_kernel} --hsmrt {hsm_image} --targetbaud {baudrate} --input {input_parameter}"
    if seccfg:
        command += f" --cpseccfg {seccfg}"
    if hsm_cpu_code:
        command += f" --cpapphsm {hsm_cpu_code}"
    if c29_cpu_code:
        command += f" --cpappcpu1 {c29_cpu_code}"
    if c29_cpu3_code:
        command += f" --cpappcpu3 {c29_cpu3_code}"

    logger.info(f"Running UART CP: {command}")

    proc = _popen_uart(command, cancel_event=cancel_event, notify_proc=register_proc_cb)
    output = _drain_proc(proc, cancel_event=cancel_event)
    return_code = proc.returncode if proc.returncode is not None else -1

    logger.info(f"UART CP exit code: {return_code}")

    # Write log file for diagnostics (best-effort).
    # Strip repetitive "send N bytes" transfer-progress lines to keep the log readable.
    try:
        filtered = re.sub(r'^send \d+ bytes\s*\n', '', output, flags=re.MULTILINE)
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(filtered)
    except Exception:
        pass

    return return_code, output

def run_get_device_type_uart(uart_kernel, device, port, baudrate,
                             cancel_event=None, register_proc_cb=None) -> str:
    """
    Get device type using UART interface.

    Args:
        uart_kernel: Path to UART kernel file
        device: Target device name
        port: UART port
        baudrate: UART baudrate
        cancel_event: Optional threading.Event; when set the subprocess is killed.
        register_proc_cb: Optional callable(proc) so callers can store the handle.

    Returns:
        str: Command output
    """
    command = f"{uart_flash_programmer_path} --device {device} --port {port} --kernel {uart_kernel} --targetbaud {baudrate} --input 11"

    logger.info(f"Running UART Get Device Type Command: {command}")

    proc = _popen_uart(command, cancel_event=cancel_event, notify_proc=register_proc_cb)
    output = _drain_proc(proc, cancel_event=cancel_event, timeout=30)
    logger.info(output)
    return output

def parseCodeProvisioningUART(subparser):
    import argparse
    parser = subparser.add_parser(
        "uart_codeprov",
        help="Code Provisioning Command",
        description="Provision the Code using JTAG Kernel",
    )

    # Code provisioning command
    parser.add_argument("--uart-kernel", required=True, help="Path to JTAG flash kernel file")
    parser.add_argument("--hsm-image", required=True, help="Path to CP HSM image file")
    parser.add_argument("--hsm-cpu-code", required=True, help="Path to HSM CPU code file")
    parser.add_argument("--c29-cpu-code", required=True, help="Path to C29 CPU code file")
    parser.add_argument("--seccfg", required=True, help="Path to C29 CPU code file")
    parser.add_argument("--port", required=True, help="UART Port")
    parser.add_argument("--targetbaud", required=True, help="UART Baud Rate")
    parser.add_argument("--input", required=True, help="UART Baud Rate")

def run_key_provisioning_uart(uart_kernel, certificate, otp_kw_bin, port,
                             device="f29h85x", baudrate="115200", log_file="kp_logs.txt",
                             cancel_event=None, register_proc_cb=None) -> tuple:
    """
    Run key provisioning using UART interface.

    Args:
        uart_kernel: Path to UART kernel file
        certificate: Path to certificate file
        otp_kw_bin: Path to OTP KW binary file
        port: UART port
        device: Target device name (default: f29h85x)
        baudrate: UART baudrate (default: 115200)
        log_file: Path to log file (default: kp_logs.txt)
        cancel_event: Optional threading.Event; when set the subprocess is killed.
        register_proc_cb: Optional callable(proc) so callers can store the handle.

    Returns:
        tuple: (return_code, output) where return_code is the process exit code
               and output is the captured stdout/stderr
    """
    log_path = join_path(get_script_dir(), log_file)

    command = f"{uart_flash_programmer_path} --device {device} --port {port} --kernel {uart_kernel} --hsmrt {otp_kw_bin} --hsmkeys {certificate} --targetbaud {baudrate} --input 3,4"

    logger.info(f"Running UART KP: {command}")

    proc = _popen_uart(command, cancel_event=cancel_event, notify_proc=register_proc_cb)
    output = _drain_proc(proc, cancel_event=cancel_event)
    return_code = proc.returncode if proc.returncode is not None else -1

    logger.info(f"UART KP exit code: {return_code}")

    # Write log file for diagnostics (best-effort).
    # Strip repetitive "send N bytes" transfer-progress lines to keep the log readable.
    try:
        filtered = re.sub(r'^send \d+ bytes\s*\n', '', output, flags=re.MULTILINE)
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(filtered)
    except Exception:
        pass

    return return_code, output

def parseKeyProvisioningUART(subparser):
    import argparse
    parser = subparser.add_parser(
        "uart_keyprov",
        help="Key Provisioning Command",
        description="Provision the keys using JTAG Kernel",
    )

    # Key provisioning command
    parser.add_argument("--otp-kw-bin", required=True, help="Path to OTP KW binary file")
    parser.add_argument("--certificate", required=True, help="Path to certificate file")
    parser.add_argument("--uart-kernel", required=True, help="Path to UART flash kernel file")
    parser.add_argument("--port", required=True, help="UART Port")
    parser.add_argument("--targetbaud", required=True, help="UART Baud Rate")

def parsegetDeviceTypeUART(subparser):
    import argparse
    parser = subparser.add_parser(
        "devTypeUART",
        help="Get Device Type over UART",
        description=(
            "Get Device Type using UART.\n\n"
            "Pre-built UART kernels are provided for convenience:\n"
            "  - HS-FS devices: host/bin/asm/f29h85x/ram_based_uart_sbl.bin\n"
            "    (ready to use, no signing required)\n"
            "  - HS-KP / HS-SE devices: host/bin/asm/f29h85x/ram_based_uart_sbl.temp.bin\n"
            "    (unsigned template — must be signed with the SMPK/BMPK keys\n"
            "     provisioned on your device before use)"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Get Device Type
    parser.add_argument("--uart-kernel", required=True, help="Path to UART flash kernel file")
    parser.add_argument("--port", required=True, help="UART Port")
    parser.add_argument("--targetbaud", required=True, help="UART Baud Rate")
