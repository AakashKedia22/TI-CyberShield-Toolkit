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

from apps.tifs.socidparser.mcup_uart_boot_socid import parseSoCId
"""
module that deals with SoC Id parsing.
"""

import serial
import time
import platform

# Import platform utilities if available
try:
    from apps.qtgui.utils.platform_utils import IS_WINDOWS, IS_LINUX, IS_MACOS, get_serial_port_filter
    PLATFORM_UTILS_AVAILABLE = True
except ImportError:
    # Fallback to direct platform detection if platform_utils is not available
    IS_WINDOWS = platform.system() == 'Windows'
    IS_LINUX = platform.system() == 'Linux'
    IS_MACOS = platform.system() == 'Darwin'
    PLATFORM_UTILS_AVAILABLE = False

class UARTReader:
    def __init__(self, port=None, baudrate=115200, timeout=10, parity = 'N', stopbits = '1'):
        """
        Initialize UART connection

        Args:
            port (str): Serial port name (defaults to platform-appropriate default)
            baudrate (int): Communication speed
            timeout (float): Read timeout
        """
        # Set default port based on platform if none provided
        if port is None:
            if IS_WINDOWS:
                port = 'COM1'
            elif IS_LINUX:
                port = '/dev/ttyACM0'
            elif IS_MACOS:
                port = '/dev/cu.usbmodem'
            else:
                port = '/dev/ttyACM0'  # Linux-like default
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.parity = parity
        self.stopbits = stopbits
        self.serial_connection = None

    def connect(self):
        """
        Establish serial connection
        """
        try:
            self.serial_connection = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                parity=self.parity,
                stopbits=self.stopbits, 
                bytesize=serial.EIGHTBITS
            )
            print(f"Connected to {self.port} successfully!")
            return True
        except serial.SerialException as e:
            print(f"Error connecting to {self.port}: {e}")
            return False

    def read_line(self):
        """
        Read a single line from UART
        
        Returns:
            str: Decoded line or None
        """
        try:
            if not self.serial_connection:
                self.connect()
            
            # Read line
            line = self.serial_connection.readline().decode('utf-8', errors='ignore').strip()
            return line
        except Exception as e:
            print(f"Error reading line: {e}")
            return None

    def read_bytes(self, size=100):
        """
        Read specific number of bytes
        
        Args:
            size (int): Number of bytes to read
        
        Returns:
            bytes: Raw byte data
        """
        try:
            if not self.serial_connection:
                self.connect()
            
            # Read bytes
            data = self.serial_connection.read(size)
            return data
        except Exception as e:
            print(f"Error reading bytes: {e}")
            return None

    def continuous_read(self, duration=60):
        """
        Continuously read from UART for specified duration
        
        Args:
            duration (int): Reading duration in seconds
        """
        start_time = time.time()
        print("Starting continuous read...")
        
        while time.time() - start_time < duration:
            line = self.read_line()
            if line:
                print(line)
            time.sleep(0.1)

    def hex_read(self, size=200):
        """
        Read and convert to hex string
        
        Args:
            size (int): Number of bytes to read
        
        Returns:
            str: Hex representation
        """
        try:
            data = self.read_bytes(size)
            if data:
                return data.hex()
            return None
        except Exception as e:
            print(f"Hex conversion error: {e}")
            return None

    def close(self):
        """
        Close serial connection
        """
        if self.serial_connection:
            self.serial_connection.close()
            print("Serial connection closed.")
        
parity_dict = {
    'N': serial.PARITY_NONE,
    'E': serial.PARITY_EVEN,
    'O': serial.PARITY_ODD,
    'M': serial.PARITY_MARK,
    'S': serial.PARITY_SPACE
}

stopbit_dict = {
    '1': serial.STOPBITS_ONE,
    '1.5': serial.STOPBITS_ONE_POINT_FIVE, 
    '2': serial.STOPBITS_TWO
}

BAUDRATES = (50, 75, 110, 134, 150, 200, 300, 600, 1200, 1800, 2400, 4800,
            9600, 19200, 38400, 57600, 115200, 230400, 460800, 500000,
            576000, 921600, 1000000, 1152000, 1500000, 2000000, 2500000,
            3000000, 3500000, 4000000)

class PortNotFound(Exception):
        pass

class IncorrectParity(Exception):
        pass
class IncorrectStopBits(Exception):
        pass
class IncorrectBaudRate(Exception):
        pass
def parseSoCId_args(subparsers):
    """Define arguments for parse SoC Id sub-command"""
    parseSoCId_parser = subparsers.add_parser(
        "parseSoCId",
        help="SoC Id parser",
        description="SoC Id parser",
    )
    parseSoCId_parser.add_argument("-s", "--string", help="Soc id reported from UART console")
    parseSoCId_parser.add_argument("-f", "--file", help="File which contains the soc id reported from UART console")

def invoke_parseSoCID(args):
    parseSoCId(args)
    

def getSoCId_args(subparsers):
    """Define arguments for parse SoC Id sub-command"""
    getSoCId_parser = subparsers.add_parser(
        "getSoCId",
        help="SoC Id parser",
        description="SoC Id parser",
    )
    getSoCId_parser.add_argument("--port", type = str, help="Port form which the Soc id will be read over UART console")
    getSoCId_parser.add_argument("--baudrate", type = int, action="store", default= 115200, help="UART Baud Rate")
    getSoCId_parser.add_argument("--parity", type = str, action="store", default= 'N', help="UART Parity Bit")
    getSoCId_parser.add_argument("--stopbits", type = str, action="store", default= '1', help="UART Stop Bits")
    getSoCId_parser.add_argument("--timeout", type = int, action="store", default= 10, help="UART read timeout in seconds")

def getSoCId(args) -> str:
    if not args.port:
        raise PortNotFound ("Port not provided")

    if(args.parity not in parity_dict.keys()):
        raise IncorrectParity ("Parity should be 'N', 'E' or 'O'")

    if(args.stopbits not in stopbit_dict.keys()):
        raise IncorrectParity ("Stop Bits should be '1', '1.5' or '2'")

    if(args.baudrate not in BAUDRATES):
        raise IncorrectBaudRate ("Select one of the",BAUDRATES)

    uart = UARTReader(
        port=args.port,
        baudrate=args.baudrate,
        timeout=args.timeout,
        parity=parity_dict[args.parity],
        stopbits=stopbit_dict[args.stopbits]
    )

    uart.connect()
    print("POR device now")
    # SoCId is 480 hex chars (240 binary bytes); read extra to handle trailing \r\n
    raw = uart.read_bytes(482)
    uart.close()
    if raw:
        decoded = raw.decode('ascii', errors='ignore')
        # Keep only valid hex characters, then take exactly 480 (the SoCId size)
        hex_str = ''.join(c for c in decoded if c in '0123456789abcdefABCDEF')
        hex_str = hex_str[:480]
        return hex_str if hex_str else None
    return None