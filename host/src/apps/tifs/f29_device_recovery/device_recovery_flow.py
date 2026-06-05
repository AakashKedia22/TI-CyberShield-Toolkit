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

This module provides Python APIs for running key provisioning and code provisioning
using the CCS scripting tools.
"""

import os
import sys
import subprocess
import logging
from typing import Optional, Dict, List, Union, Tuple

# Import platform utilities
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))), "src"))
from common.platform_utils import get_ccs_launcher, get_command_prefix_for_python

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def enable_device_recovery(
    ccs_path: str,
    verbose: bool = False,
) -> Tuple[bool, str]:
    """
    Enter Device Recovery

    Args:
        ccs_path (str): Path to the CCS installation directory
        verbose (bool, optional): Whether to print verbose output. Defaults to False.

    Returns:
        Tuple[bool, str]: A tuple containing a success flag and output message
    """
    
    # Path to the script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
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
        enable_device_recovery = os.path.join(script_dir, "enter_device_recovery.py")
        cmd = get_command_prefix_for_python(launcher_path) + [enable_device_recovery]
    else:
        # Use JavaScript script with shell launcher
        enable_device_recovery = os.path.join(script_dir, "enter_device_recovery.js")
        cmd = [
            launcher_path,
            enable_device_recovery,
        ]

    logger.info(f"Enable Device Recovery command: {' '.join(cmd)}")

    try:
        # Run the command
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate()

        # Log output
        if verbose:
            if stdout:
                logger.info(f"Command output:\n{stdout}")
            if stderr:
                logger.warning(f"Command errors:\n{stderr}")

        print(stdout)
        # Check return code
        if process.returncode != 0:
            error_msg = f"Enable Device Recovery failed with return code {process.returncode}"
            if stderr:
                error_msg += f"\nError: {stderr}"
            logger.error(error_msg)
            return False, error_msg

        success_msg = "Enable Device Recovery completed successfully"
        logger.info(success_msg)
        return True, stdout if stdout else success_msg

    except Exception as e:
        error_msg = f"Error enabling device recovery UID: {str(e)}"
        logger.exception(error_msg)
        return False, error_msg

def run_get_device_uid_secap(
    ccs_path: str,
    verbose: bool = True
) -> Tuple[bool, str]:
    """
    Run the get device type using jtag interface.
    Args:
        ccs_path (str): Path to the CCS installation directory
        verbose (bool, optional): Whether to print verbose output. Defaults to False.

    Returns:
        str: Returns the device type which can be either HS-FS, HS-KP, or HS-SE
    """
    # Path to the script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
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
        run_get_uid = os.path.join(script_dir, "run_get_uid_secap.py")
        cmd = get_command_prefix_for_python(launcher_path) + [run_get_uid]
    else:
        # Use JavaScript script with shell launcher
        run_get_uid = os.path.join(script_dir, "run_get_uid_secap.js")
        cmd = [
            launcher_path,
            run_get_uid,
        ]

    logger.info(f"Running Get Device UID command: {' '.join(cmd)}")

    try:
        # Run the command
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate()

        # Log output
        if verbose:
            if stdout:
                logger.info(f"Command output:\n{stdout}")
            if stderr:
                logger.warning(f"Command errors:\n{stderr}")

        print(stdout)
        # Check return code
        if process.returncode != 0:
            error_msg = f"Get Device UID failed with return code {process.returncode}"
            if stderr:
                error_msg += f"\nError: {stderr}"
            logger.error(error_msg)
            return False, error_msg

        success_msg = "Get Device UID completed successfully"
        logger.info(success_msg)
        return True, stdout if stdout else success_msg

    except Exception as e:
        error_msg = f"Error running Get Device UID: {str(e)}"
        logger.exception(error_msg)
        return False, error_msg

def send_device_recovery_cert(
    dev_recov_cert: str,
    ccs_path: str,
    verbose: bool = False,
) -> Tuple[bool, str]:
    """
    Run the code provisioning process using the specified files.

    Args:
        dev_recov_cert (str): Path to the device recovery certificate
        ccs_path (str): Path to the CCS installation directory
        verbose (bool, optional): Whether to print verbose output. Defaults to False.

    Returns:
        Tuple[bool, str]: A tuple containing a success flag and output message
    """
    # Validate file paths
    for path, name in [
        (dev_recov_cert, "Device Recovey Cert"),
    ]:
        if not os.path.exists(path):
            error_msg = f"{name} file not found: {path}"
            logger.error(error_msg)
            return False, error_msg

    # Path to the script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
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
        run_device_recovery_flow = os.path.join(script_dir, "run_device_recovery_flow.py")
        cmd = get_command_prefix_for_python(launcher_path) + [
            run_device_recovery_flow,
            "--dev_recov_cert", dev_recov_cert,
        ]
    else:
        # Use JavaScript script with shell launcher
        run_device_recovery_flow = os.path.join(script_dir, "run_device_recovery_flow.js")
        cmd = [
            launcher_path,
            run_device_recovery_flow,
            "--dev_recov_cert", dev_recov_cert
            ]

    logger.info(f"Running validate device recovery certificate with command: {' '.join(cmd)}")

    try:
        # Run the command
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate()

        # Log output
        if verbose:
            if stdout:
                logger.info(f"Command output:\n{stdout}")
            if stderr:
                logger.warning(f"Command errors:\n{stderr}")

        # Check return code
        if process.returncode != 0:
            error_msg = f"Device recovery cert validation failed with return code {process.returncode}"
            if stderr:
                error_msg += f"\nError: {stderr}"
            logger.error(error_msg)
            return False, error_msg

        success_msg = "Device recovery cert validation completed successfully"
        logger.info(success_msg)
        return True, stdout if stdout else success_msg

    except Exception as e:
        error_msg = f"Error running device recovery cert validation: {str(e)}"
        logger.exception(error_msg)
        return False, error_msg

def parseValidateDeviceRecoveryCert(subparser):
    import argparse
    parser = subparser.add_parser(
        "valdcert",
        help="Validate Device Recovery Cert",
        description="Validate Device Recovery Cert",
    )

    # Code provisioning command
    parser.add_argument("--ccs-path", required=True, help="Path to CCS installation directory")
    parser.add_argument("--dev_recov_cert", required=True, help="Path to HSM image file")
    parser.add_argument("--verbose", action="store_true", help="Print verbose output")


def parseGetUIDSecap(subparser):
    import argparse
    parser = subparser.add_parser(
        "getUIDSecap",
        help="Get Device UID",
        description="Get Device UID",
    )

    parser.add_argument("--ccs-path", required=True, help="Path to CCS installation directory")
    parser.add_argument("--verbose", action="store_true", help="Print verbose output")


def parseEnableDeviceRecovery(subparser):
    import argparse
    parser = subparser.add_parser(
        "endevrecov",
        help="Get Device UID",
        description="Get Device UID",
    )

    parser.add_argument("--ccs-path", required=True, help="Path to CCS installation directory")
    parser.add_argument("--verbose", action="store_true", help="Print verbose output")
