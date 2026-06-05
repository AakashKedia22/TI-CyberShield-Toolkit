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
Code Provisioning Flow Script

This script handles code provisioning for HSM and C29 CPU using JTAG.
"""

import os
import sys
import argparse
import tempfile
import platform
import struct
from pathlib import Path
# import the scripting module. Will not work without launch.py if PYTHONPATH is not set correctly
from scripting import initScripting, ScriptingTimeoutError, ScriptingOptions

# Import platform utilities
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))), "src"))
from common.platform_utils import get_script_dir, join_path, get_temp_dir, clean_temp_dir

# Set up logging if desired
import logging
logger = logging.getLogger("TI.scripting")
logger.setLevel(logging.NOTSET)

# Constants for chunk sizes
FIRST_CHUNK_SIZE = 0x1000  # 4KB
CHUNK_SIZE = 0x4000  # 16KB

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Run code provisioning flow for HSM and C29 CPU'
    )
    
    parser.add_argument('--hsm-image', required=True,
                        help='Path to HSM image file')
    parser.add_argument('--jtag-kernel', required=True,
                        help='Path to JTAG flash kernel file')
    parser.add_argument('--hsm-cpu-code', required=False, default=None,
                        help='Path to HSM CPU code file')
    parser.add_argument('--c29-cpu-code', required=False, default=None,
                        help='Path to C29 CPU1 code file')
    parser.add_argument('--c29-cpu3-code', required=False, default=None,
                        help='Path to C29 CPU3 code file (optional; uses same loading address as CPU1)')
    parser.add_argument('--seccfg', required=False, default=None,
                        help='Path to C29 CPU SECCFG file')

    args = parser.parse_args()

    # Validate that required files exist
    for arg_name, file_path in [
        ('hsm-image', args.hsm_image),
        ('jtag-kernel', args.jtag_kernel),
    ]:
        if not os.path.exists(file_path):
            print(f"Error: File not found for {arg_name}: {file_path}")
            sys.exit(1)

    for arg_name, file_path in [
        ('hsm-cpu-code', args.hsm_cpu_code),
        ('c29-cpu-code', args.c29_cpu_code),
        ('seccfg', args.seccfg),
        ('c29-cpu3-code', args.c29_cpu3_code),
    ]:
        if file_path and not os.path.exists(file_path):
            print(f"Error: File not found for {arg_name}: {file_path}")
            sys.exit(1)
    
    return args

# Using platform_utils for temp directory functions

def run_target_with_timeout(session):
    """Run target with timeout handling."""
    try:
        # print("Expecting target to not halt for 10 seconds")
        session.target.run()
    except ScriptingTimeoutError:
        print("Success: we timed out while waiting for the target to halt")
        session.target.halt()
    except Exception as err:
        raise err

def process_file_in_chunks(file_path, session, temp_dir):
    """Process file in chunks."""
    print(f"Processing file: {file_path}")
    file_size = os.path.getsize(file_path)
    
    with open(file_path, 'rb') as f:
        file_data = f.read()
    
    # Process first chunk (4KB)
    first_chunk_path = join_path(temp_dir, "chunk_0.bin")
    with open(first_chunk_path, 'wb') as f:
        f.write(file_data[:FIRST_CHUNK_SIZE])
    
    # Load and process first chunk
    session.memory.loadBinary(0x200F8000, first_chunk_path)
    # print(f"Loaded first chunk of {FIRST_CHUNK_SIZE} bytes at address 0x200F8000")
    run_target_with_timeout(session)
    
    # Process remaining chunks
    remaining_size = file_size - FIRST_CHUNK_SIZE
    chunk_number = 1
    offset = FIRST_CHUNK_SIZE
    
    while remaining_size > 0:
        current_chunk_size = min(CHUNK_SIZE, remaining_size)
        chunk_path = join_path(temp_dir, f"chunk_{chunk_number}.bin")
        
        # Create chunk file
        with open(chunk_path, 'wb') as f:
            f.write(file_data[offset:offset + current_chunk_size])
        
        # Load and process chunk
        session.memory.loadBinary(0x200F8000, chunk_path)
        # print(f"Loaded chunk {chunk_number} of size {current_chunk_size} bytes at address 0x200F8000")
        run_target_with_timeout(session)
        
        # Update for next iteration
        remaining_size -= current_chunk_size
        offset += current_chunk_size
        chunk_number += 1

def main():
    """Main function to run the code provisioning flow."""
    # Get file paths from command line arguments
    args = parse_args()
    
    # Initialize scripting and obtain the main debugger scripting interface
    # Using suppressMessages equivalent
    options = ScriptingOptions(logFile="stdout", suppressMessages="true")
    ds = initScripting(options)
    
    # Configure a 10 second timeout on all operations (by default there is no timeout)
    ds.setScriptingTimeout(10000)
    
    # Configure the debugger and open a debug session to the cortex M core
    # Check for PyInstaller temp directory first, then fall back to script_dir
    script_dir = get_script_dir()
    ccxml_path = os.environ.get('CCXML_PATH', join_path(script_dir, "F29h85x-hsse.ccxml"))
    ds.configure(ccxml_path)
    session = ds.openSession("Texas Instruments XDS110 USB Debug Probe/C29xx_CPU1")

    session.target.connect()

    # overwrite file if it already exists
    log_path = join_path(script_dir, "log.txt")
    session.cio.beginCapture(log_path)
    
    session.target.halt()
    
    # Load the HSM image at fixed address 0x200E0000
    print(f"Loading HSM image from: {args.hsm_image}")
    session.memory.loadBinary(0x200E0000, args.hsm_image)
    
    # Load a JTAG flash Kernel out file to a fixed location
    print(f"Loading JTAG flash kernel from: {args.jtag_kernel}")
    session.memory.loadProgram(args.jtag_kernel)
    
    # Create temporary directory for chunks
    temp_dir = get_temp_dir('code_prov_chunks_')

    # CMD_CTRL_REG bit definitions (must match ex3_jtag_get_function_cpu1.h)
    CMD_BIT_HSM_RT  = (1 << 0)
    CMD_BIT_HSM_CP  = (1 << 2)
    CMD_BIT_CPU1_CP = (1 << 3)
    CMD_BIT_CPU3_CP = (1 << 4)
    CMD_BIT_SEC_CFG = (1 << 5)

    # Compute bitmask from provided inputs
    cmd_bits = CMD_BIT_HSM_RT
    if args.hsm_cpu_code:
        cmd_bits |= CMD_BIT_HSM_CP
    if args.c29_cpu_code:
        cmd_bits |= CMD_BIT_CPU1_CP
    if args.c29_cpu3_code:
        cmd_bits |= CMD_BIT_CPU3_CP
    if args.seccfg:
        cmd_bits |= CMD_BIT_SEC_CFG

    # Write cmd_bits to CMD_CTRL_REG (0x30180508) so the kernel reads it at startup
    print(f"Writing CMD_CTRL_REG bitmask 0x{cmd_bits:08X} to 0x30180508")
    cmd_bits_bin = os.path.join(temp_dir, "cmd_bits.bin")
    with open(cmd_bits_bin, 'wb') as f:
        f.write(struct.pack('<I', cmd_bits))
    session.memory.loadBinary(0x30180508, cmd_bits_bin)

    try:
        # Phase 1: HSM CPU Code Provisioning
        if args.hsm_cpu_code:
            print("Moving to HSM CPU Code Provisioning")
            process_file_in_chunks(args.hsm_cpu_code, session, temp_dir)

        # Phase 2: C29 CPU1 Code Provisioning
        if args.c29_cpu_code:
            print("Moving to C29 CPU1 Code Provisioning")
            process_file_in_chunks(args.c29_cpu_code, session, temp_dir)

        # Phase 2.5: C29 CPU3 Code Provisioning (optional, same load address as CPU1)
        if args.c29_cpu3_code:
            print("Moving to C29 CPU3 Code Provisioning")
            process_file_in_chunks(args.c29_cpu3_code, session, temp_dir)

        # Phase 3: C29 CPU SECCFG Code Provisioning
        if args.seccfg:
            session.memory.loadBinary(0x200F8000, args.seccfg)
            run_target_with_timeout(session)
        
    except Exception as err:
        print(f"Error during code provisioning: {err}")
        raise err
    finally:
        # Clean up temporary files
        clean_temp_dir(temp_dir)
        
        # Read and print the contents of log.txt
        with open(log_path, 'r') as f:
            log_content = f.read()
        print("Log file contents:")
        print(log_content)


        session.target.disconnect()        
        # shutdown the debugger
        ds.shutdown()

if __name__ == "__main__":
    main()
