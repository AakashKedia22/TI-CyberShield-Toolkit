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
Platform Utilities

This module provides platform-independent utilities for path handling, process execution,
and other OS-specific operations required by the provisioning tools.
"""

import os
import sys
import subprocess
import platform
import tempfile
import pathlib
from typing import List, Optional, Union, Tuple, Dict, Any

# Detect platform
IS_WINDOWS = platform.system() == 'Windows'
IS_LINUX = platform.system() == 'Linux'
IS_MACOS = platform.system() == 'Darwin'

# Constants for CCS paths based on platform
if IS_WINDOWS:
    RUN_SH_RELATIVE_PATH = "ccs\\scripting\\run.bat"
    PYTHON_LAUNCHER_RELATIVE_PATH = "ccs\\scripting\\python\\launcher.py"
    DEFAULT_PORT_PREFIX = "COM"
else:  # Linux/MacOS
    RUN_SH_RELATIVE_PATH = "ccs/scripting/run.sh"
    PYTHON_LAUNCHER_RELATIVE_PATH = "ccs/scripting/python/launcher.py"
    DEFAULT_PORT_PREFIX = "/dev/tty"

def get_script_dir() -> str:
    """
    Get the script directory, handling both PyInstaller and normal environments

    Returns:
        str: Path to the script directory
    """
    if getattr(sys, 'frozen', False):
        # Running in PyInstaller bundle
        return os.path.join(sys._MEIPASS, 'apps', 'tifs', 'kp_cp_f29h85x')
    else:
        # Normal Python environment
        return os.path.dirname(os.path.abspath(__file__))

def normalize_path(path: str) -> str:
    """
    Normalize a file path for the current platform

    Args:
        path (str): The path to normalize

    Returns:
        str: The normalized path
    """
    return os.path.normpath(path)

def join_path(*paths: str) -> str:
    """
    Join path components in a platform-independent way

    Args:
        *paths: Path components to join

    Returns:
        str: Joined path
    """
    return os.path.join(*paths)

def get_temp_dir(prefix: str = 'tifs_') -> str:
    """
    Create a temporary directory in a platform-independent way

    Args:
        prefix (str, optional): Prefix for the temp dir. Defaults to 'tifs_'.

    Returns:
        str: Path to the created temp directory
    """
    return tempfile.mkdtemp(prefix=prefix)

def clean_temp_dir(temp_dir: str) -> None:
    """
    Clean up a temporary directory in a platform-independent way

    Args:
        temp_dir (str): Path to the temporary directory
    """
    if os.path.exists(temp_dir):
        for file in os.listdir(temp_dir):
            os.unlink(os.path.join(temp_dir, file))
        os.rmdir(temp_dir)

def run_command(command: Union[str, List[str]], shell: bool = False,
                capture_output: bool = True, log_file: Optional[str] = None,
                env: Optional[dict] = None) -> Tuple[int, str, str]:
    """
    Run a command in a platform-independent way

    Args:
        command (Union[str, List[str]]): Command to run, either as a string or list of arguments
        shell (bool, optional): Whether to use the shell. Defaults to False.
        capture_output (bool, optional): Whether to capture stdout/stderr. Defaults to True.
        log_file (Optional[str], optional): Path to log file for output redirection. Defaults to None.
        env (Optional[dict], optional): Environment variables to pass to the command. Defaults to None.

    Returns:
        Tuple[int, str, str]: Tuple of (return_code, stdout, stderr)
    """
    # If we have a log file, modify the command to redirect output
    if log_file and shell and isinstance(command, str):
        if IS_WINDOWS:
            command = f"{command} > {log_file} 2>&1"
        else:
            command = f"{command} > {log_file} 2>&1"

    # Merge provided env with current environment
    cmd_env = os.environ.copy()
    if env:
        cmd_env.update(env)

    # Run the command
    process = subprocess.run(
        command,
        shell=shell,
        capture_output=capture_output,
        text=True,
        env=cmd_env
    )

    return process.returncode, process.stdout, process.stderr

def get_ccs_launcher(ccs_path: str) -> Tuple[str, str]:
    """
    Get the appropriate CCS launcher (run.sh/bat or Python launcher).

    Args:
        ccs_path (str): Base path to the CCS installation

    Returns:
        Tuple[str, str]: (launcher_type, launcher_path)
            launcher_type: "shell" or "python"
            launcher_path: Full path to the launcher
    """
    # First try run script (shell script on Unix, batch file on Windows)
    run_script_path = os.path.join(ccs_path, RUN_SH_RELATIVE_PATH)
    if os.path.exists(run_script_path):
        return "shell", run_script_path

    # Try Python launcher
    python_launcher_path = os.path.join(ccs_path, PYTHON_LAUNCHER_RELATIVE_PATH)
    if os.path.exists(python_launcher_path):
        return "python", python_launcher_path

    # Try alternative paths
    alt_paths = []

    if IS_WINDOWS:
        alt_paths.extend([
            ("python", os.path.join(ccs_path, "scripting\\python\\launcher.py")),
            ("python", os.path.join(ccs_path, "ccs_base\\scripting\\python\\launcher.py")),
            ("python", os.path.join(ccs_path, "eclipse\\scripting\\python\\launcher.py")),
            ("shell", os.path.join(ccs_path, "scripting\\run.bat")),
            ("shell", os.path.join(ccs_path, "ccs_base\\scripting\\run.bat")),
        ])
    else:
        alt_paths.extend([
            ("python", os.path.join(ccs_path, "scripting/python/launcher.py")),
            ("python", os.path.join(ccs_path, "ccs_base/scripting/python/launcher.py")),
            ("python", os.path.join(ccs_path, "eclipse/scripting/python/launcher.py")),
            ("shell", os.path.join(ccs_path, "scripting/run.sh")),
            ("shell", os.path.join(ccs_path, "ccs_base/scripting/run.sh")),
        ])

    for launcher_type, alt_path in alt_paths:
        if os.path.exists(alt_path):
            return launcher_type, alt_path

    # Return None if not found
    return None, None

def get_command_prefix_for_python(python_launcher_path: str) -> List[str]:
    """
    Get the correct command prefix for running Python scripts through a launcher

    Args:
        python_launcher_path (str): Path to the Python launcher

    Returns:
        List[str]: Command prefix to use
    """
    if IS_WINDOWS:
        return ["python", python_launcher_path]
    else:
        return ["python3", python_launcher_path]

def get_log_redirect(log_file: str) -> str:
    """
    Get the platform-specific command string for redirecting stdout and stderr to a log file

    Args:
        log_file (str): Path to the log file

    Returns:
        str: Command string for redirecting output
    """
    if IS_WINDOWS:
        return f" > {log_file} 2>&1"
    else:
        return f" > {log_file} 2>&1"

def get_default_baudrate() -> str:
    """Get the default baudrate for serial communication"""
    return "115200"

def get_uart_flash_programmer_path(device_family: str = "asm", device_name: str = "f29h85x") -> pathlib.Path:
    """
    Construct the path to the uart_flash_programmer based on environment and platform

    Args:
        device_family (str): Device family (default: "asm")
        device_name (str): Device name (default: "f29h85x")

    Returns:
        pathlib.Path: Path to the uart_flash_programmer
    """
    current_file = pathlib.Path(__file__)

    if getattr(sys, 'frozen', False):
        bundle_dir = pathlib.Path(sys._MEIPASS)
        base_path = bundle_dir / "host" / "bin" / device_family / device_name
    else:
        base_path = current_file.parent.parent.parent.parent.parent / "bin" / device_family / device_name

    if IS_WINDOWS:
        return base_path / "uart_flash_programmer.exe"
    else:
        return base_path / "uart_flash_programmer"