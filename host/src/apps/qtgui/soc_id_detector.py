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
SoC ID detector module for automatically detecting device type and state
from a connected device via serial port.
"""

import time
import binascii
import struct
from typing import Dict, Any, Optional

# Import UARTReader from parseSoCId
from apps.spt.parseSoCId import UARTReader, parity_dict, stopbit_dict, BAUDRATES

# Device lists aligned with uart_boot_socid.py
K3_DEVICES = ['am243x', 'am64x']
MCU_DEVICES = ['am263x', 'am273x', 'am263px', 'am261x', 'f29h85x']

# Device type mapping from device ID to device name
DEVICE_TYPE_MAP = {
    'F29H85X': 'f29h85x',
    'AM273X': 'am273x',
    'AM263X': 'am263x',
    'AM263PX': 'am263px',
    'AM261X': 'am261x',
    'AM64X': 'am64x',
    'AM243X': 'am243x',
    'J722S': 'j722s',
    'AM62PX': 'am62px'
}

# Device state mapping from hex values to UI state names
DEVICE_STATE_MAP = {
    '0xabcd0001': 'GP',
    '0xabcd0002': 'TEST',
    '0xabcd0003': 'EMU_FS',
    '0xabcd0004': 'HS_FS',
    '0xabcd0005': 'EMU_SE',
    '0xabcd0006': 'HS_SE',
    '0xabcd0007': 'EMU_KP',
    '0xabcd0008': 'HS_KP',
    '0xabcd000a': 'HS_FA',
}

# UI display mapping (convert internal state to UI display name)
UI_STATE_MAP = {
    'HS_FS': 'HSFS',
    'HS_SE': 'HSSE',
    'EMU_FS': 'EMUFS',
    'EMU_SE': 'EMUSE',
}

def modifySocId(socid_str):
    """
    Modify SocId for AM273x (aligned with uart_boot_socid.py)
    
    Args:
        socid_str (str): SoC ID string
        
    Returns:
        str: Modified SoC ID string
    """
    ans = socid_str
    # If 6 leading 0s are there, remove 1
    if len(socid_str) > 5 and socid_str[5] == '0':
        ans = socid_str[1:]
    return ans

def extract_device_name_from_socid(binary_data: bytes) -> Optional[str]:
    """
    Extract device name from SoC ID binary data
    
    Args:
        binary_data (bytes): Raw SoC ID binary data
    
    Returns:
        Optional[str]: Device name if successfully extracted, None otherwise
    """
    try:
        # For MCU devices (including F29H85X)
        # The device name is in the HSM public info structure
        hwInfo = struct.unpack('HBBBBH', binary_data[0:8])
        pubRomInfo = struct.unpack('I', binary_data[8:12])
        hsmPubInfo = struct.unpack('12BII', binary_data[12:32])
        
        # Extract device name from bytes
        tmp_list = list(hsmPubInfo[0:12])
        hex_list = [hex(i) for i in tmp_list]
        device_name = ''.join(chr(int(c, 16)) for c in hex_list[0:7] if int(c, 16) != 0)
        return device_name.upper()
    except Exception:
        # Try K3 device format
        try:
            num_blocks = list(struct.unpack('I', binary_data[0:4]))[0]
            pub_rom_info = struct.unpack('BB2B12B4B4B4B', binary_data[4:32])
            tmp_list = list(pub_rom_info[4:15])
            hex_list = [hex(i) for i in tmp_list]
            device_name = ''.join(chr(int(c, 16)) for c in hex_list[0:] if int(c, 16) != 0)
            return device_name.upper()
        except Exception:
            return None

def extract_device_state_from_socid(binary_data: bytes, device: str) -> Optional[str]:
    """
    Extract device state from SoC ID binary data
    
    Args:
        binary_data (bytes): Raw SoC ID binary data
        device (str): Device type name
    
    Returns:
        Optional[str]: Device state if successfully extracted, None otherwise
    """
    try:
        # For MCU devices (including F29H85X)
        hwInfo = struct.unpack('HBBBBH', binary_data[0:8])
        pubRomInfo = struct.unpack('I', binary_data[8:12])
        hsmPubInfo = struct.unpack('12BII', binary_data[12:32])
        
        # Device type is in the public info (index 12)
        dev_type = hex(hsmPubInfo[12])
        
        # Convert to UI display format if available
        if dev_type in DEVICE_STATE_MAP:
            device_state = DEVICE_STATE_MAP[dev_type]
            if device_state in UI_STATE_MAP:
                return UI_STATE_MAP[device_state]
            return device_state
        return None
    except Exception:
        return None

def read_socid_from_port(port: str, baudrate: int = 115200, timeout: int = 5) -> Optional[bytes]:
    """
    Read SoC ID from a connected device via serial port
    
    Args:
        port (str): Serial port name
        baudrate (int): Communication speed
        timeout (int): Read timeout in seconds
    
    Returns:
        Optional[bytes]: Raw SoC ID binary data if successfully read, None otherwise
    """
    uart = None
    try:
        # Create UART reader
        uart = UARTReader(
            port=port,
            baudrate=baudrate,
            timeout=timeout,
            parity=parity_dict['N'],
            stopbits=stopbit_dict['1']
        )

        # Try to connect
        if not uart.connect():
            uart = None  # connect() failed; close() not needed
            return None

        # Read SoC ID as hex string
        hex_data = uart.hex_read(200)
        if not hex_data:
            return None

        # Special handling for AM273x - similar to modifySocId
        if len(hex_data) > 10 and hex_data[10] == '0':
            device_name = extract_device_name_from_socid(binascii.unhexlify(hex_data))
            if device_name and device_name.upper() == "AM273X":
                hex_data = hex_data[2:]  # Remove first byte

        # Convert hex string to binary
        return binascii.unhexlify(hex_data)
    except Exception:
        return None
    finally:
        if uart is not None:
            uart.close()

def detect_device_from_port(port: str, timeout: int = 5) -> Dict[str, Any]:
    """
    Detect device type and state from a connected device on the specified port
    
    Args:
        port (str): Serial port name
        timeout (int): Read timeout in seconds
    
    Returns:
        Dict[str, Any]: Detection result containing:
            - success (bool): Whether detection was successful
            - device (str): Detected device type (e.g. 'f29h85x')
            - device_state (str): Detected device state (e.g. 'HSFS')
            - soc_id (str): Raw SoC ID hex string if available
            - error (str): Error message if detection failed
    """
    result = {
        'success': False,
        'device': None,
        'device_state': None,
        'soc_id': None,
        'error': None
    }
    
    try:
        # Read SoC ID from port
        binary_data = read_socid_from_port(port, timeout=timeout)
        if not binary_data:
            result['error'] = f"Failed to read SoC ID from port {port}"
            return result
        
        # Store hex string of SoC ID
        result['soc_id'] = binary_data.hex()
        
        # Extract device name
        device_name = extract_device_name_from_socid(binary_data)
        if not device_name or device_name not in DEVICE_TYPE_MAP:
            result['error'] = f"Unknown device detected: {device_name}"
            return result
        
        # Get standardized device name
        result['device'] = DEVICE_TYPE_MAP[device_name]
        
        # Extract device state
        device_state = extract_device_state_from_socid(binary_data, result['device'])
        if not device_state:
            result['error'] = "Could not determine device state"
            return result
        
        result['device_state'] = device_state
        result['success'] = True
        return result
    except Exception as e:
        result['error'] = f"Error during detection: {str(e)}"
        return result