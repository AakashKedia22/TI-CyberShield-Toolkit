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
JTAG Provisioning APIs

This module provides platform-independent Python APIs for running key provisioning and code provisioning
using the CCS scripting tools.
"""

import os
import sys
import subprocess
import logging
import platform
from typing import Optional, Dict, List, Union, Tuple

# Import platform utilities
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))), "src"))
from common.platform_utils import (
    get_script_dir, normalize_path, join_path,
    get_ccs_launcher, get_command_prefix_for_python, run_command,
    kill_proc_tree, register_proc, unregister_proc, IS_WINDOWS,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _popen_jtag(cmd: list, env: dict = None, cancel_event=None, notify_proc=None):
    """Start *cmd* as a managed subprocess in a new session (POSIX).

    Registers the process in the global atexit tracker and optionally notifies
    the caller via *notify_proc(proc)* so it can store the handle.
    """
    import subprocess as _sp
    kwargs: dict = dict(
        stdout=_sp.PIPE,
        stderr=_sp.STDOUT,
        text=True,
        bufsize=1,
    )
    if env:
        import os as _os
        merged = _os.environ.copy()
        merged.update(env)
        kwargs["env"] = merged
    if not IS_WINDOWS:
        kwargs["start_new_session"] = True

    proc = _sp.Popen(cmd, **kwargs)
    register_proc(proc)
    if notify_proc is not None:
        notify_proc(proc)
    return proc


def _drain_jtag(proc, cancel_event=None) -> str:
    """Read all stdout from *proc*, killing it early if *cancel_event* is set."""
    output_lines = []
    for line in iter(proc.stdout.readline, ""):
        if cancel_event is not None and cancel_event.is_set():
            kill_proc_tree(proc)
            break
        output_lines.append(line)
    proc.stdout.close()
    proc.wait()
    unregister_proc(proc)
    return "".join(output_lines)

def run_key_provisioning_jtag(
    otp_kw_bin_path: str,
    certificate_path: str,
    jtag_kernel_path: str,
    ccs_path: str,
    verbose: bool = False,
    log_file: str = "kp_logs.txt",
    ccxml_path: str = None,
    cancel_event=None,
    register_proc_cb=None,
) -> Tuple[bool, str]:
    """
    Run the key provisioning process using the specified files.

    Args:
        otp_kw_bin_path (str): Path to the OTP KW binary file
        certificate_path (str): Path to the certificate file
        jtag_kernel_path (str): Path to the JTAG flash kernel file
        ccs_path (str): Path to the CCS installation directory
        verbose (bool, optional): Whether to print verbose output. Defaults to False.
        log_file (str, optional): Path to log file. Defaults to "kp_logs.txt".
        ccxml_path (str, optional): Path to the CCXML configuration file. Defaults to None.

    Returns:
        Tuple[bool, str]: A tuple containing a success flag and output message
    """
    # Validate file paths
    for path, name in [
        (otp_kw_bin_path, "OTP KW binary"),
        (certificate_path, "Certificate"),
        (jtag_kernel_path, "JTAG flash kernel")
    ]:
        if not os.path.exists(path):
            error_msg = f"{name} file not found: {path}"
            logger.error(error_msg)
            return False, error_msg

    # Get the script directory
    script_dir = get_script_dir()

    # Get the appropriate launcher
    launcher_type, launcher_path = get_ccs_launcher(ccs_path)

    if not launcher_path or not os.path.exists(launcher_path):
        error_msg = (
            f"CCS launcher not found for path: {ccs_path}\n"
            f"Please ensure:\n"
            f"1. CCS is properly installed at: {ccs_path}\n"
            f"2. The scripting component is installed\n"
            f"If CCS is installed elsewhere, please update the CCS path."
        )
        logger.error(error_msg)
        return False, error_msg

    # Choose the appropriate script based on launcher type
    if launcher_type == "python":
        # Use Python script with Python launcher
        keyprov_script = join_path(script_dir, "run_keyprov_flow.py")
        cmd = get_command_prefix_for_python(launcher_path)
        cmd.extend([
            keyprov_script,
            "--otp-kw-bin", otp_kw_bin_path,
            "--certificate", certificate_path,
            "--jtag-kernel", jtag_kernel_path
        ])
    else:
        # Use JavaScript script with shell launcher
        keyprov_script = join_path(script_dir, "run_keyprov_flow.js")
        cmd = [
            launcher_path,
            keyprov_script,
            "--otp-kw-bin", otp_kw_bin_path,
            "--certificate", certificate_path,
            "--jtag-kernel", jtag_kernel_path
        ]

    logger.info(f"Running key provisioning with command: {' '.join(cmd)}")

    env_vars = {}
    if ccxml_path:
        env_vars['CCXML_PATH'] = ccxml_path
        logger.info(f"Using CCXML path: {ccxml_path}")

    try:
        proc = _popen_jtag(cmd, env=env_vars, cancel_event=cancel_event, notify_proc=register_proc_cb)
        output = _drain_jtag(proc, cancel_event=cancel_event)
        return_code = proc.returncode if proc.returncode is not None else -1

        # Write log file for diagnostics (best-effort), matching UART behaviour
        if output:
            try:
                log_path = join_path(get_script_dir(), log_file)
                with open(log_path, "w", encoding="utf-8") as f:
                    f.write(output)
            except Exception:
                pass

        if cancel_event is not None and cancel_event.is_set():
            return False, "Key provisioning cancelled"

        if return_code != 0:
            logger.error(f"Key provisioning failed with return code {return_code}")
            return False, output or f"Key provisioning failed with return code {return_code}"

        # The JS script may exit 0 even when it reports a failure in its output.
        # Scan for known failure patterns to catch these cases.
        import re as _re
        if output and _re.search(r'^Failure:', output, _re.MULTILINE):
            logger.error("Key provisioning failed (script reported Failure)")
            return False, output
        if output and _re.search(r'OTP-KW Error encountered', output):
            # debugResponse = 0x00000000 means success despite the error message
            debug_resp = _re.search(r'OTP-KW debugResponse = (0x[0-9a-fA-F]+)', output)
            if not (debug_resp and debug_resp.group(1) == '0x00000000'):
                logger.error("Key provisioning failed (OTP keywriter error)")
                return False, output

        logger.info("Key provisioning completed successfully")
        return True, output if output else "Key provisioning completed successfully"

    except Exception as e:
        error_msg = f"Error running key provisioning: {str(e)}"
        logger.exception(error_msg)
        return False, error_msg

def run_get_device_type_jtag(
    ccs_path: str,
    verbose: bool = True,
    ccxml_path: str = None,
    cancel_event=None,
    register_proc_cb=None,
) -> Tuple[bool, str]:
    """
    Run the get device type using jtag interface.
    Args:
        ccs_path (str): Path to the CCS installation directory
        verbose (bool, optional): Whether to print verbose output. Defaults to False.
        ccxml_path (str, optional): Path to the CCXML configuration file. Defaults to None.

    Returns:
        str: Returns the device type which can be either HS-FS, HS-KP, or HS-SE
    """
    
    # # Path to the run_codeprov_flow.js script
    # script_dir = os.path.dirname(os.path.abspath(__file__))
    # codeprov_script = os.path.join(script_dir, "read_lifecycle.js")

    # # Get the full path to run.sh
    # run_sh_path = get_run_sh_path(ccs_path)  
    # # Validate run.sh path
    # if not os.path.exists(run_sh_path):
    #     error_msg = f"CCS run.sh script not found: {run_sh_path}"
    #     logger.error(error_msg)
    #     return False, error_msg
    # # Build the command
    # cmd = [
    #     run_sh_path,
    #     codeprov_script
    #     ]

    # Get the script directory
    script_dir = get_script_dir()

    # Get the appropriate launcher
    launcher_type, launcher_path = get_ccs_launcher(ccs_path)
    
    if not launcher_path or not os.path.exists(launcher_path):
        error_msg = (
            f"CCS launcher not found for path: {ccs_path}\n"
            f"Please ensure:\n"
            f"1. CCS is properly installed at: {ccs_path}\n"
            f"2. The scripting component is installed\n"
            f"If CCS is installed elsewhere, please update the CCS path."
        )
        logger.error(error_msg)
        return False, error_msg
    
    # Choose the appropriate script based on launcher type
    if launcher_type == "python":
        # Use Python script with Python launcher
        read_lifecycle = join_path(script_dir, "read_lifecycle.py")
        cmd = get_command_prefix_for_python(launcher_path)
        cmd.append(read_lifecycle)
    else:
        # Use JavaScript script with shell launcher
        read_lifecycle = join_path(script_dir, "read_lifecycle.js")
        cmd = [
            launcher_path,
            read_lifecycle,
        ]

    logger.info(f"Running Get Device Type command: {' '.join(cmd)}")

    env_vars = {}
    if ccxml_path:
        env_vars['CCXML_PATH'] = ccxml_path
        logger.info(f"Using CCXML path: {ccxml_path}")

    try:
        proc = _popen_jtag(cmd, env=env_vars, cancel_event=cancel_event, notify_proc=register_proc_cb)
        output = _drain_jtag(proc, cancel_event=cancel_event)
        return_code = proc.returncode if proc.returncode is not None else -1

        if verbose and output:
            logger.info(f"Command output:\n{output}")
        print(output)

        if cancel_event is not None and cancel_event.is_set():
            return False, "Detection cancelled"

        if return_code != 0:
            error_msg = f"Get Device Type failed with return code {return_code}\n{output}"
            logger.error(error_msg)
            return False, error_msg

        success_msg = "Get Device Type completed successfully"
        logger.info(success_msg)
        return True, output if output else success_msg

    except Exception as e:
        error_msg = f"Error running Get Device Type: {str(e)}"
        logger.exception(error_msg)
        return False, error_msg

def run_code_provisioning_jtag(
    hsm_image_path: str,
    jtag_kernel_path: str,
    ccs_path: str,
    hsm_cpu_code_path: str = None,
    c29_cpu_code_path: str = None,
    seccfg_path: str = None,
    c29_cpu3_code_path: str = None,
    verbose: bool = False,
    log_file: str = "cp_logs.txt",
    ccxml_path: str = None,
    cancel_event=None,
    register_proc_cb=None,
) -> Tuple[bool, str]:
    """
    Run the code provisioning process using the specified files.

    Args:
        hsm_image_path (str): Path to the HSM image file
        jtag_kernel_path (str): Path to the JTAG flash kernel file
        hsm_cpu_code_path (str): Path to the HSM CPU code file
        c29_cpu_code_path (str): Path to the C29 CPU1 code file
        seccfg_path (str): Path to the security configuration file
        ccs_path (str): Path to the CCS installation directory
        c29_cpu3_code_path (str, optional): Path to the C29 CPU3 code file. Defaults to None.
        verbose (bool, optional): Whether to print verbose output. Defaults to False.
        log_file (str, optional): Path to log file. Defaults to "cp_logs.txt".
        ccxml_path (str, optional): Path to the CCXML configuration file. Defaults to None.

    Returns:
        Tuple[bool, str]: A tuple containing a success flag and output message
    """
    # Validate file paths
    for path, name in [
        (hsm_image_path, "HSM image"),
        (jtag_kernel_path, "JTAG flash kernel"),
    ]:
        if not os.path.exists(path):
            error_msg = f"{name} file not found: {path}"
            logger.error(error_msg)
            return False, error_msg

    for path, name in [
        (hsm_cpu_code_path, "HSM CPU code"),
        (c29_cpu_code_path, "C29 CPU1 code"),
        (seccfg_path, "C29 SECCFG code"),
        (c29_cpu3_code_path, "C29 CPU3 code"),
    ]:
        if path and not os.path.exists(path):
            error_msg = f"{name} file not found: {path}"
            logger.error(error_msg)
            return False, error_msg

    # Get the script directory
    script_dir = get_script_dir()

    # Get the appropriate launcher
    launcher_type, launcher_path = get_ccs_launcher(ccs_path)
    
    if not launcher_path or not os.path.exists(launcher_path):
        error_msg = (
            f"CCS launcher not found for path: {ccs_path}\n"
            f"Please ensure:\n"
            f"1. CCS is properly installed at: {ccs_path}\n"
            f"2. The scripting component is installed\n"
            f"If CCS is installed elsewhere, please update the CCS path."
        )
        logger.error(error_msg)
        return False, error_msg
    
    # Choose the appropriate script based on launcher type
    if launcher_type == "python":
        # Use Python script with Python launcher
        codeprov_script = join_path(script_dir, "run_codeprov_flow.py")
        cmd = get_command_prefix_for_python(launcher_path)
        cmd.extend([
            codeprov_script,
            "--hsm-image", hsm_image_path,
            "--jtag-kernel", jtag_kernel_path,
        ])
        if hsm_cpu_code_path:
            cmd.extend(["--hsm-cpu-code", hsm_cpu_code_path])
        if c29_cpu_code_path:
            cmd.extend(["--c29-cpu-code", c29_cpu_code_path])
        if c29_cpu3_code_path:
            cmd.extend(["--c29-cpu3-code", c29_cpu3_code_path])
        if seccfg_path:
            cmd.extend(["--seccfg", seccfg_path])
    else:
        # Use JavaScript script with shell launcher
        codeprov_script = join_path(script_dir, "run_codeprov_flow.js")
        cmd = [
            launcher_path,
            codeprov_script,
            "--hsm-image", hsm_image_path,
            "--jtag-kernel", jtag_kernel_path,
        ]
        if hsm_cpu_code_path:
            cmd.extend(["--hsm-cpu-code", hsm_cpu_code_path])
        if c29_cpu_code_path:
            cmd.extend(["--c29-cpu-code", c29_cpu_code_path])
        if c29_cpu3_code_path:
            cmd.extend(["--c29-cpu3-code", c29_cpu3_code_path])
        if seccfg_path:
            cmd.extend(["--seccfg", seccfg_path])

    logger.info(f"Running code provisioning with command: {' '.join(cmd)}")

    env_vars = {}
    if ccxml_path:
        env_vars['CCXML_PATH'] = ccxml_path
        logger.info(f"Using CCXML path: {ccxml_path}")

    try:
        proc = _popen_jtag(cmd, env=env_vars, cancel_event=cancel_event, notify_proc=register_proc_cb)
        output = _drain_jtag(proc, cancel_event=cancel_event)
        return_code = proc.returncode if proc.returncode is not None else -1

        # Write log file for diagnostics (best-effort), matching UART behaviour
        if output:
            try:
                log_path = join_path(get_script_dir(), log_file)
                with open(log_path, "w", encoding="utf-8") as f:
                    f.write(output)
            except Exception:
                pass

        if cancel_event is not None and cancel_event.is_set():
            return False, "Code provisioning cancelled"

        if return_code != 0:
            logger.error(f"Code provisioning failed with return code {return_code}")
            return False, output or f"Code provisioning failed with return code {return_code}"

        # The script may exit 0 even when it reports a failure in its output.
        # Scan for known failure patterns to catch these cases.
        import re as _re
        if output and _re.search(r'^Failure:', output, _re.MULTILINE):
            logger.error("Code provisioning failed (script reported Failure)")
            return False, output
        if output and _re.search(r'!! \w.*FAILED !!', output):
            logger.error("Code provisioning failed (stage failure detected)")
            return False, output

        logger.info("Code provisioning completed successfully")
        return True, output if output else "Code provisioning completed successfully"

    except Exception as e:
        error_msg = f"Error running code provisioning: {str(e)}"
        logger.exception(error_msg)
        return False, error_msg

def parseCodeProvisioningJTAG(subparser):
    import argparse
    parser = subparser.add_parser(
        "jtag_codeprov",
        help="Code Provisioning Command",
        description="Provision the Code using JTAG Kernel",
    )

    # Code provisioning command
    parser.add_argument("--ccs-path", required=True, help="Path to CCS installation directory")
    parser.add_argument("--hsm-image", required=True, help="Path to HSM image file")
    parser.add_argument("--jtag-kernel", required=True, help="Path to JTAG flash kernel file")
    parser.add_argument("--hsm-cpu-code", required=True, help="Path to HSM CPU code file")
    parser.add_argument("--c29-cpu-code", required=True, help="Path to C29 CPU1 code file")
    parser.add_argument("--c29-cpu3-code", required=False, default=None,
                        help="Path to C29 CPU3 code file (optional; uses same load address as CPU1)")
    parser.add_argument("--seccfg", required=True, help="Path to C29 CPU SECCFG file")
    parser.add_argument("--verbose", action="store_true", help="Print verbose output")

def parseKeyProvisioningJTAG(subparser):
    import argparse
    parser = subparser.add_parser(
        "jtag_keyprov",
        help="Key Provisioning Command",
        description="Provision the keys using JTAG Kernel",
    )

    # Key provisioning command
    parser.add_argument("--ccs-path", required=True, help="Path to CCS installation directory")
    parser.add_argument("--otp-kw-bin", required=True, help="Path to OTP KW binary file")
    parser.add_argument("--certificate", required=True, help="Path to certificate file")
    parser.add_argument("--jtag-kernel", required=True, help="Path to JTAG flash kernel file")
    parser.add_argument("--verbose", action="store_true", help="Print verbose output")


def parsegetDeviceTypeJTAG(subparser):
    import argparse
    parser = subparser.add_parser(
        "devTypeJTAG",
        help="Get Device Type",
        description="Get Device Type using the JTAG",
    )

    # Get Device Type
    parser.add_argument("--ccs-path", required=True, help="Path to CCS installation directory")
    parser.add_argument("--verbose", action="store_true", help="Print verbose output")
