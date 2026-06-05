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
import signal
import subprocess
import platform
import tempfile
import pathlib
import atexit
import weakref
from typing import List, Optional, Union, Tuple, Dict, Any

# Detect platform
IS_WINDOWS = platform.system() == 'Windows'
IS_LINUX = platform.system() == 'Linux'
IS_MACOS = platform.system() == 'Darwin'

# ---------------------------------------------------------------------------
# Subprocess lifecycle helpers
# ---------------------------------------------------------------------------

# Module-level registry of active subprocesses; entries are weak-referenced
# so that completed processes are garbage-collected automatically.
_active_procs: "list[subprocess.Popen]" = []


def _cleanup_active_procs() -> None:
    """Kill any still-running tracked subprocesses on interpreter exit."""
    for proc in list(_active_procs):
        if proc.poll() is None:
            kill_proc_tree(proc)


atexit.register(_cleanup_active_procs)


def register_proc(proc: subprocess.Popen) -> None:
    """Track *proc* so it is killed automatically if the process exits."""
    _active_procs.append(proc)


def unregister_proc(proc: subprocess.Popen) -> None:
    """Remove *proc* from the tracking list once it has finished."""
    try:
        _active_procs.remove(proc)
    except ValueError:
        pass


def kill_proc_tree(proc: subprocess.Popen) -> None:
    """Kill *proc* and all its children, cross-platform.

    On POSIX the process is started in its own session (caller must pass
    ``start_new_session=True`` to ``Popen``), so ``killpg`` reaches every
    child.  On Windows ``taskkill /T`` achieves the same effect.
    Falls back to ``proc.kill()`` if anything goes wrong.
    """
    try:
        if IS_WINDOWS:
            subprocess.call(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Constants for CCS paths based on platform
if IS_WINDOWS:
    RUN_SH_RELATIVE_PATH = "ccs\\scripting\\run.bat"
    PYTHON_LAUNCHER_RELATIVE_PATH = "ccs\\scripting\\python\\launcher.py"
    DEFAULT_PORT_PREFIX = "COM"
else:  # Linux/MacOS
    RUN_SH_RELATIVE_PATH = "ccs/scripting/run.sh"
    PYTHON_LAUNCHER_RELATIVE_PATH = "ccs/scripting/python/launcher.py"
    DEFAULT_PORT_PREFIX = "/dev/tty"

def get_project_root() -> str:
    """
    Get the project root directory

    Returns:
        str: Path to the project root directory
    """
    # This will find the root of the tisecprov project
    # assuming this file is in host/src/common/
    current_file = pathlib.Path(__file__)
    return str(current_file.parent.parent.parent.parent)

def get_script_dir(script_path=None) -> str:
    """
    Get the script directory, handling both PyInstaller and normal environments

    Args:
        script_path (str, optional): Path to the script. If None, uses __file__ from the caller.

    Returns:
        str: Path to the script directory
    """
    if getattr(sys, 'frozen', False):
        # Running in PyInstaller bundle
        return os.path.join(sys._MEIPASS, 'apps', 'tifs', 'kp_cp_f29h85x')
    else:
        # Normal Python environment
        if script_path:
            return os.path.dirname(os.path.abspath(script_path))
        else:
            # Get the caller's frame
            import inspect
            caller_frame = inspect.stack()[1]
            caller_file = caller_frame.filename
            return os.path.dirname(os.path.abspath(caller_file))

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

# --- addon base override (set via GUI) ---
_addon_base_override: "pathlib.Path | None" = None

def set_addon_base(path: "str | None") -> None:
    """Override the addon base directory (session-scoped, not persisted)."""
    global _addon_base_override
    _addon_base_override = pathlib.Path(path) if path else None

def get_addon_root(device_name: str) -> pathlib.Path:
    """Return the external addon root for *device_name*."""
    base = _addon_base_override if _addon_base_override is not None \
           else pathlib.Path.home() / "ti" / "TICST" / "addons"
    return base / device_name


def get_prebuilt_images_dir(device_family: str, device_name: str) -> pathlib.Path:
    """
    Get the prebuilt images directory for a specific device family and name

    Args:
        device_family (str): Device family (e.g., "asm")
        device_name (str): Device name (e.g., "f29h85x")

    Returns:
        pathlib.Path: Path to the prebuilt images directory
    """
    if getattr(sys, 'frozen', False):
        bundle_dir = pathlib.Path(sys._MEIPASS)
        return bundle_dir / "host" / "bin" / device_family / device_name
    project_root = pathlib.Path(get_project_root())
    return project_root / "host" / "bin" / device_family / device_name

def get_uart_flash_programmer_path(device_family: str = "asm", device_name: str = "f29h85x") -> pathlib.Path:
    """
    Construct the path to the uart_flash_programmer based on environment and platform

    Args:
        device_family (str): Device family (default: "asm")
        device_name (str): Device name (default: "f29h85x")

    Returns:
        pathlib.Path: Path to the uart_flash_programmer
    """
    base_path = get_prebuilt_images_dir(device_family, device_name)

    if IS_WINDOWS:
        exe_path = base_path / "uart_flash_programmer.exe"
        if not exe_path.exists():
            linux_path = base_path / "uart_flash_programmer"
            if linux_path.exists():
                raise RuntimeError(
                    f"Windows executable not found. Found Linux binary instead at {linux_path}. "
                    "This likely means the PyInstaller bundle was built on Linux. "
                    "Please rebuild the Windows installer on a Windows machine."
                )
        return exe_path
    else:
        linux_path = base_path / "uart_flash_programmer"
        if not linux_path.exists():
            exe_path = base_path / "uart_flash_programmer.exe"
            if exe_path.exists():
                raise RuntimeError(
                    f"Linux executable not found. Found Windows binary instead at {exe_path}. "
                    "This likely means the PyInstaller bundle was built on Windows. "
                    "Please rebuild the Linux installer on a Linux machine."
                )
        return linux_path