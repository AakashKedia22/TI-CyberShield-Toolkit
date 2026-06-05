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
Platform utilities for cross-platform compatibility in the TI Cybershield Toolkit.
Provides functions to handle platform-specific operations on Windows and Linux.
"""

import os
# sys is unused, removing import
# import sys
import platform
import subprocess
# pathlib is unused, removing import
# import pathlib
from typing import List, Optional

from common.platform_utils import get_addon_root  # re-export

# Platform detection
IS_WINDOWS = platform.system() == 'Windows'
IS_LINUX = platform.system() == 'Linux'
IS_MACOS = platform.system() == 'Darwin'


def get_home_directory() -> str:
    """Get the user's home directory in a cross-platform way."""
    return os.path.expanduser("~")


def normalize_path(path: str) -> str:
    """Normalize a path for the current platform, converting slashes as needed."""
    return os.path.normpath(path) if path else path


def open_file(file_path: str) -> None:
    """Open a file with the default application for the current platform."""
    file_path = normalize_path(file_path)

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    try:
        if IS_WINDOWS:
            os.startfile(file_path)
        elif IS_MACOS:
            subprocess.Popen(['open', file_path])
        else:  # Linux
            subprocess.Popen(['xdg-open', file_path])
    except Exception as e:
        print(f"Error opening file: {e}")


def format_serial_port_name(port: str) -> str:
    """Format serial port name for display, accounting for platform differences."""
    return port


def get_serial_port_filter() -> List[str]:
    """Return platform-specific filters for serial port patterns."""
    if IS_WINDOWS:
        return ["COM"]
    elif IS_LINUX:
        return ["/dev/ttyUSB", "/dev/ttyACM"]
    elif IS_MACOS:
        return ["/dev/cu.usbserial", "/dev/cu.usbmodem"]
    else:
        return []


def join_path_components(*args) -> str:
    """Join path components in a platform-appropriate way."""
    valid_args = [arg for arg in args if arg]
    return os.path.join(*valid_args) if valid_args else ""