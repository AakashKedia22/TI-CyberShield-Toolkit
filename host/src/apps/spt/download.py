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
module that deals with the download of code into the target
via serial etc.
"""

import os
import time
import tempfile
import serial
import platform
from tqdm import tqdm
from xmodem import XMODEM1k

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

BOOTLOADER_UART_STATUS_LOAD_SUCCESS = 0x53554343
BOOTLOADER_UART_STATUS_LOAD_FAIL = 0x4641494C
BOOTLOADER_UART_STATUS_APPIMAGE_SIZE_EXCEEDED = 0x45584344

# BUFFERED IO PROTOCOL DEFINES
BOOTLOADER_BUF_IO_MAGIC = 0xBF0000BF
BOOTLOADER_BUF_IO_OK = 0xBF000000
BOOTLOADER_BUF_IO_ERR = 0xBF000001
BOOTLOADER_BUF_IO_FILE_RECEIVE_COMPLETE = 0xBF000002
BOOTLOADER_BUF_IO_SEND_FILE = 0xBF000003


# XMODEM specific constants
XMODEM_ACK = b"\x06"
XMODEM_NAK = b"\x15"
XMODEM_CAN = b"\x18"
XMODEM_EOT = b"\x04"

# Transfer settings
XMODEM_RETRY_LIMIT = 10
XMODEM_TIMEOUT = 10

MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


def parse_response_evm(f):
    """Parse response sent from EVM"""
    resp_bytes = f.read(128)
    response = int.from_bytes(resp_bytes[0:4], "little")

    status_messages = {
        BOOTLOADER_UART_STATUS_LOAD_SUCCESS: "Application load SUCCESS.",
        BOOTLOADER_UART_STATUS_LOAD_FAIL: "ERROR: Application load FAILED.",
        BOOTLOADER_UART_STATUS_APPIMAGE_SIZE_EXCEEDED: "ERROR: Application load FAILED, file size exceeds LIMIT on the EVM.",
    }

    return status_messages.get(response, "ERROR: Bad response from EVM.")


def verify_serial_port(serialport):
    """Verify serial port exists and is accessible in a cross-platform way"""
    # For Windows COM ports, we can't use os.path.exists
    if IS_WINDOWS:
        # Windows COM ports are not checked with os.path.exists
        # Instead, we'll let the Serial constructor handle errors
        # Just verify the port name format
        if not serialport.upper().startswith('COM'):
            raise RuntimeError(
                f"Port {serialport} has invalid format for Windows.\n"
                "Possible solutions:\n"
                "1. Check if the device is properly connected\n"
                "2. Use a port name like 'COM1', 'COM2', etc.\n"
                "3. Use Device Manager to verify available ports"
            )
        return

    # For Linux/macOS, check if the port exists
    if not os.path.exists(serialport):
        # Prepare platform-appropriate error message
        if IS_LINUX:
            cmd_suggestion = "'ls /dev/ttyUSB*' or 'ls /dev/ttyACM*'"
        elif IS_MACOS:
            cmd_suggestion = "'ls /dev/cu.*' to list available ports"
        else:
            cmd_suggestion = "appropriate commands to list serial ports"

        raise RuntimeError(
            f"Port {serialport} not found.\n"
            "Possible solutions:\n"
            "1. Check if the device is properly connected\n"
            "2. Verify the correct port name\n"
            f"3. Run {cmd_suggestion} to list available ports"
        )

    # Check permissions on Linux/macOS
    if not os.access(serialport, os.R_OK | os.W_OK):
        if IS_LINUX:
            permission_suggestion = "1. Run 'sudo adduser $USER dialout' and log out/in\n"\
                                    "2. Run 'sudo chmod 666 {serialport}'"
        elif IS_MACOS:
            permission_suggestion = "Run 'sudo chmod 666 {serialport}'"
        else:
            permission_suggestion = "Check file permissions for your operating system"

        raise RuntimeError(
            f"No permission to access {serialport}.\n"
            "Try these solutions:\n"
            f"{permission_suggestion}"
        )


def calculate_transfer_rate(bytes_transferred, time_taken):
    """Calculate and format transfer rate"""
    rate = bytes_transferred / time_taken if time_taken > 0 else 0
    if rate > 1024 * 1024:
        return f"{rate/1024/1024:.2f} MB/s"
    if rate > 1024:
        return f"{rate/1024:.2f} KB/s"
    return f"{rate:.2f} B/s"


def xmodem_send_receive_file(stream, serialport, baudrate=115200, get_response=True):
    """
    Sends file to EVM via XMODEM protocol and handles responses

    Args:
        stream: File stream to send
        serialport: Serial port to use
        baudrate: Baud rate for serial communication (default 115200)
        get_response: Whether to wait for device response (default True)

    Returns:
        tuple: (response_status, time_taken, bytes_transferred)

    Raises:
        RuntimeError: For various transfer failures with detailed messages
    """
    file_size = os.fstat(stream.fileno()).st_size
    bytes_transferred = 0
    retry_count = 0

    # Verify port before starting
    verify_serial_port(serialport)
    print(f"Sending {stream.name} ({file_size} bytes) to {serialport}...")
    while retry_count < MAX_RETRIES:
        try:
            # Open serial port
            ser = serial.Serial(serialport, baudrate, timeout=3)

            with ser, tqdm(
                total=file_size,
                unit="bytes",
                leave=False,
                desc=f"Sending {stream.name} (Attempt {retry_count + 1}/{MAX_RETRIES})",
            ) as progress_bar:

                def getc(size, timeout=1):
                    """Read from serial port with timeout"""
                    data = ser.read(size)
                    if not data:
                        if retry_count == 0:  # Only show warning on first attempt
                            print(f"\nWarning: No data received after {timeout}s")
                    return data or None

                def putc(data, timeout=1):
                    """Write to serial port with byte counting"""
                    try:
                        bytes_written = ser.write(data)
                        if bytes_written:
                            nonlocal bytes_transferred
                            # Ensure we don't count more bytes than file size
                            remaining = file_size - bytes_transferred
                            actual_bytes = min(bytes_written, remaining)
                            bytes_transferred += actual_bytes
                            progress_bar.update(actual_bytes)
                        return bytes_written
                    except serial.SerialTimeoutException:
                        print("\nWrite timeout occurred")
                        return None
                    except serial.SerialException as e:
                        print(f"\nSerial error during write: {e}")
                        return None

                try:
                    # Initialize XMODEM
                    modem = XMODEM1k(getc, putc)
                    start_time = time.time()

                    # Reset counters for new attempt
                    bytes_transferred = 0
                    progress_bar.reset()

                    # Perform transfer
                    success = modem.send(stream, quiet=True, timeout=10, retry=10)

                    if success:
                        time_taken = round(time.time() - start_time, 2)

                        # Verify exact file size match
                        if bytes_transferred == file_size:
                            # Handle response if requested
                            if get_response:
                                with tempfile.TemporaryFile() as response_file:
                                    response_success = modem.recv(
                                        response_file, quiet=True, timeout=20
                                    )
                                    if not response_success:
                                        raise RuntimeError(
                                            "Failed to receive response from device.\n"
                                            "Device may not be in correct state"
                                        )
                                    response_file.seek(0)
                                    response_status = parse_response_evm(response_file)
                            else:
                                response_status = None

                            # Calculate and show transfer rate
                            transfer_rate = calculate_transfer_rate(
                                bytes_transferred, time_taken
                            )
                            print(f"\nTransfer rate: {transfer_rate}")

                            return response_status, time_taken, bytes_transferred

                        else:
                            # Size mismatch - retry
                            stream.seek(0)  # Reset file pointer
                            retry_count += 1
                            if retry_count < MAX_RETRIES:
                                print(
                                    f"\nTransfer size mismatch ({bytes_transferred}/{file_size} bytes). Retrying... ({retry_count}/{MAX_RETRIES})"
                                )
                                time.sleep(RETRY_DELAY)
                                continue
                            raise RuntimeError(
                                f"Transfer size mismatch: {bytes_transferred}/{file_size} bytes.\n"
                                "Possible solutions:\n"
                                "1. Check USB connection\n"
                                "2. Power cycle the board\n"
                                "3. Try a different USB port"
                            )

                    else:
                        # Transfer failed - retry
                        stream.seek(0)
                        retry_count += 1
                        if retry_count < MAX_RETRIES:
                            print(
                                f"\nTransfer failed. Retrying... ({retry_count}/{MAX_RETRIES})"
                            )
                            time.sleep(RETRY_DELAY)
                            continue
                        raise RuntimeError(
                            "XMODEM transfer failed after all retries.\n"
                            "Possible solutions:\n"
                            "1. Power cycle the board\n"
                            "2. Make sure board is in bootloader mode\n"
                            "3. Check baud rate settings\n"
                            "4. Verify cable connections"
                        )

                except (TimeoutError, serial.SerialTimeoutException) as e:
                    stream.seek(0)
                    retry_count += 1
                    if retry_count < MAX_RETRIES:
                        print(
                            f"\nTimeout occurred: {str(e)}. Retrying... ({retry_count}/{MAX_RETRIES})"
                        )
                        time.sleep(RETRY_DELAY)
                        continue
                    raise RuntimeError(
                        "Communication timeout after all retries.\n"
                        "Possible solutions:\n"
                        "1. Check if device is powered on\n"
                        "2. Verify board is in bootloader mode\n"
                        "3. Check cable connections\n"
                        "4. Try power cycling the board"
                    )

        except Exception as e:
            if "expected ACK" in str(e):
                stream.seek(0)
                retry_count += 1
                if retry_count < MAX_RETRIES:
                    print(
                        f"\nACK error: {str(e)}. Retrying... ({retry_count}/{MAX_RETRIES})"
                    )
                    time.sleep(RETRY_DELAY)
                    continue
            raise RuntimeError(
                f"Transfer failed: {str(e)}\n"
                "General troubleshooting:\n"
                "1. Check physical connections\n"
                "2. Verify correct serial port and permissions\n"
                "3. Power cycle the board\n"
                "4. Try a different USB cable/port\n"
                "5. Run diagnostic commands to check for USB/serial errors"
                "   (Linux: 'dmesg', Windows: Device Manager, macOS: 'system_profiler SPUSBDataType')"
            )

    raise RuntimeError(f"Transfer failed after {MAX_RETRIES} attempts")


def download_args(subparsers):
    """Define arguments for download sub-command"""
    download_parser = subparsers.add_parser(
        "download",
        help="download a binary into the target",
        description="download a binary into the target",
    )
    download_parser.add_argument(
        "-p", "--serial-port", required=True, help="Serial port to use for the transfer"
    )
    download_parser.add_argument(
        "-b", "--bootloader", required=True, help="Path to the key writer binary"
    )


def download_binary(args):
    """Main function to handle binary download"""
    serialport = args.serial_port
    bootloader_file_path = args.bootloader

    try:
        if not os.path.exists(bootloader_file_path):
            raise RuntimeError(f"Bootloader file not found: {bootloader_file_path}")

        file_size = os.path.getsize(bootloader_file_path)
        if file_size == 0:
            raise RuntimeError("Bootloader file is empty")

        print(f"Sending bootloader {bootloader_file_path} ({file_size} bytes)...")

        with open(bootloader_file_path, "rb") as bootloader_file:
            _send_status, time_taken, bytes_transferred = xmodem_send_receive_file(
                bootloader_file, serialport, get_response=False
            )

            # Verify transfer completion
            if bytes_transferred == file_size:
                print(
                    f"Transfer completed: {bytes_transferred}/{file_size} bytes in {time_taken}s"
                )
            else:
                raise RuntimeError(
                    f"Incomplete transfer: {bytes_transferred}/{file_size} bytes transferred"
                )

    except Exception as e:
        print("\nDownload failed!")
        print(str(e))
        raise RuntimeError("Download failed - see error message above") from e
