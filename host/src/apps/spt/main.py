#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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
This is the main entry point of the commandline application. Each of
the sub-commands are implemented in their own individual modules.
"""
import argparse
from typing import List, Dict
import traceback
import importlib
import sys
import platform
import serial.tools.list_ports

from tisecprov import __version__
from apps.spt.genkeys import genkeys_args, generate_keys
from apps.spt.gencert import gencert_args, generate_certificate
from apps.spt.sign import sign_args
from apps.spt.encrypt import encrypt_args, encrypt_binary_command
from apps.spt.download import download_args, download_binary
from apps.spt.parseSoCId import parseSoCId_args, invoke_parseSoCID

# Import platform utilities if available
try:
    from apps.qtgui.utils.platform_utils import IS_WINDOWS, IS_LINUX, IS_MACOS, format_serial_port_name, get_serial_port_filter
    PLATFORM_UTILS_AVAILABLE = True
except ImportError:
    # Fallback to direct platform detection if platform_utils is not available
    IS_WINDOWS = platform.system() == 'Windows'
    IS_LINUX = platform.system() == 'Linux'
    IS_MACOS = platform.system() == 'Darwin'
    PLATFORM_UTILS_AVAILABLE = False

# Device handler mapping - maps device names to their handler module paths
DEVICE_HANDLERS: Dict[str, str] = {
    "f29h85x": "apps.spt.f29_spt.f29_main",
    # Add new device handlers here in the format:
    # "device_name": "module.path.to.device_main_function",
    # Example:
    # "am62px": "apps.spt.am62px_spt.am62px_main",
    # "j722s": "apps.spt.j722s_spt.j722s_main",
}

def list_ports(subparsers):
    """List available serial ports"""
    list_parser = subparsers.add_parser(
        "list-ports", help="List available serial ports"
    )
    list_parser.add_argument(
        "--regexp-filter", help="Regular expression filter to apply to port names"
    )


def show_available_ports():
    """Show all available serial ports in a platform-independent way"""
    print("\nAvailable serial ports:")
    ports = serial.tools.list_ports.comports()

    if not ports:
        print("  No serial ports found.")
        return

    for i, port in enumerate(ports):
        # Format port name based on platform
        port_name = format_serial_port_name(port.device) if PLATFORM_UTILS_AVAILABLE else port.device
        print(f"  {i+1}. {port_name} - {port.description}")

    # Print platform-specific help
    print("\nNote:")
    if IS_WINDOWS:
        print("  On Windows, use 'COM<n>' format (e.g., 'COM1', 'COM3').")
    elif IS_LINUX:
        print("  On Linux, use '/dev/ttyUSB<n>' or '/dev/ttyACM<n>' format.")
    elif IS_MACOS:
        print("  On macOS, use '/dev/cu.usbmodem<id>' or '/dev/cu.usbserial<id>' format.")
    print("")  # Add empty line


def run_device_handler(handler_path: str) -> None:
    """
    Dynamically imports and runs a device-specific handler function.
    
    Args:
        handler_path: Dot-separated path to the handler function (module.path.function)
    """
    try:
        module_path, function_name = handler_path.rsplit('.', 1)
        module = importlib.import_module(module_path)
        handler_function = getattr(module, function_name)
        handler_function()
    except (ImportError, AttributeError) as e:
        print(f"Error: Could not load handler for device: {e}")
        sys.exit(1)


def default_spt_flow(filtered_args: List[str]):
    """
    The default SPT flow for standard devices (am62px, j722s, etc.)
    
    Args:
        filtered_args: Command line arguments without the device flag
    """
    parser = argparse.ArgumentParser(
        description=f"Texas Instruments Cybershield Toolkit v{__version__}"
    )
    parser.add_argument("--version", action="version", version=f"{__version__}")

    subparsers = parser.add_subparsers(
        title="commands", description="valid commands", dest="command"
    )
    genkeys_args(subparsers)
    gencert_args(subparsers)
    sign_args(subparsers)
    encrypt_args(subparsers)
    download_args(subparsers)
    parseSoCId_args(subparsers)
    
    # Parse the filtered arguments
    args = parser.parse_args(filtered_args)
    try:
        if args.command == "genkeys":
            generate_keys(
                args.session, args.password, args.key_type, args.devel, args.hsm
            )
            print("Keys generated successfully")
        elif args.command == "gencert":
            mpk_flags: List[str] = (
                args.mpk_options.split(",") if args.mpk_options is not None else []
            )
            mek_flags: List[str] = (
                args.mek_options.split(",") if args.mek_options is not None else []
            )
            generate_certificate(
                args.session,
                args.password,
                args.msv,
                args.hsm,
                mpk_flags,
                mek_flags,
                args.output,
                multishot=args.multishot,
                signing_algorithm=args.signing_algorithm,
                tifek_pub_path=args.tifek_pub,
            )
            print("Certificate generated successfully")
        elif args.command == "sign":
            # Handle sign sub-command
            print(
                f"Sign file: input={args.input}, output={args.output}, key={args.key}"
            )
        elif args.command == "encrypt":
            encrypt_binary_command(args)
        elif args.command == "download":
            print(
                f"downloading binary {args.bootloader} via serial port {args.serial_port}"
            )
            download_binary(args)
        elif args.command == "parseSoCId":
            print("SoC Id parse:")
            invoke_parseSoCID(args)
        elif args.command == "list-ports":
            show_available_ports()
        else:
            parser.print_help()
    except RuntimeError as e:
        traceback.print_exc()
        print(f"Error: {e}")


def main():
    """
    The main commandline application that implements a series of sub-commands
    for each of its functionality like key generation, certificate generation,
    downloading code etc.
    """
    args = sys.argv[1:]
    has_device = any(a in ("-d", "--device") or a.startswith("--device=") for a in args)
    has_help = any(a in ("-h", "--help") for a in args)

    # --version (always handled here)
    if "--version" in args:
        print(__version__)
        sys.exit(0)

    # No device given: show top-level help and exit
    if not has_device or (has_help and not has_device):
        pre_parser = argparse.ArgumentParser(
            description=(
                f"Texas Instruments Cybershield Toolkit v{__version__}\n\n"
                "Use --device to select a target device.\n"
                "For device-specific help, run:\n"
                "  cst --device <device_name> --help\n\n"
                f"Available devices: {', '.join(DEVICE_HANDLERS.keys())}"
            ),
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        pre_parser.add_argument(
            "-d", "--device",
            metavar="<device_name>",
            help=f"Target device (e.g. {', '.join(DEVICE_HANDLERS.keys())}). Run 'cst --device <device_name> --help' for device-specific options.",
        )
        pre_parser.add_argument("--version", action="version", version=__version__)
        pre_parser.print_help()
        sys.exit(0)

    # First parser - only for device detection
    device_parser = argparse.ArgumentParser(add_help=False)
    device_parser.add_argument("-d", "--device", metavar="", help="Device", required=True)

    # Parse only the device argument
    device_args, remaining_args = device_parser.parse_known_args()
    
    # Check if there's a specific handler for this device
    device_type = device_args.device.lower()
    if device_type in DEVICE_HANDLERS:
        run_device_handler(DEVICE_HANDLERS[device_type])
        return
    
    # Filter out the --device argument from remaining_args
    filtered_args = []
    i = 0
    while i < len(remaining_args):
        if remaining_args[i] == "--device":
            i += 2  # Skip the flag and its value
        elif remaining_args[i].startswith("--device="):
            i += 1  # Skip the combined flag and value
        else:
            filtered_args.append(remaining_args[i])
            i += 1
    
    # Use default SPT flow for other devices
    default_spt_flow(filtered_args)


if __name__ == "__main__":
    main()
