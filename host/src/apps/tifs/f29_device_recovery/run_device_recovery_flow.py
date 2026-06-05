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
from pathlib import Path
# import the scripting module. Will not work without launch.py if PYTHONPATH is not set correctly
from scripting import initScripting, ScriptingTimeoutError, ScriptingOptions

# Set up logging if desired
import logging
logger = logging.getLogger("TI.scripting")
logger.setLevel(logging.NOTSET)

CHUNK_SIZE = 0x4  # 4B

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Run code provisioning flow for HSM and C29 CPU'
    )
    
    parser.add_argument('--dev_recov_cert', required=True,
                        help='Path to HSM image file')
    args = parser.parse_args()
    
    # Validate that all files exist
    for arg_name, file_path in [
        ('dev_recov_cert', args.dev_recov_cert),
    ]:
        if not os.path.exists(file_path):
            print(f"Error: File not found for {arg_name}: {file_path}")
            sys.exit(1)
    
    return args

def create_temp_dir():
    """Create temporary directory for chunks."""
    temp_dir = tempfile.mkdtemp(prefix='code_prov_chunks_')
    return temp_dir

def cleanup_temp_dir(temp_dir):
    """Clean up temporary directory."""
    if os.path.exists(temp_dir):
        for file in os.listdir(temp_dir):
            os.unlink(os.path.join(temp_dir, file))
        os.rmdir(temp_dir)

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

def main():
    """Main function to run the code provisioning flow."""
    # Get file paths from command line arguments
    args = parse_args()
    
    logger = logging.getLogger("TI.scripting")
    logger.setLevel(logging.NOTSET)
    # Initialize scripting and obtain the main debugger scripting interface
    try:
        options = ScriptingOptions(logFile="stdout", suppressMessages="true")
        ds = initScripting(options)
    except Exception as e:
        logger.error(f"Failed to initialize scripting: {e}")
        sys.exit(1)
    # Configure a 10 second timeout on all operations (by default there is no timeout)
    try:
        ds.setScriptingTimeout(10000)
    except ScriptingTimeoutError as e:
        logger.error(f"Failed to set scripting timeout: {e}")
        ds.shutdown()
        sys.exit(1)

    # Configure the debugger and open a debug session to the HSM Secap
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        components = ds.configure(os.path.join(current_dir, "F29h85x-hsse.ccxml"))
    except Exception as e:
        logger.error(f"Failed to configure debugger: {e}")
        ds.shutdown()
        sys.exit(1)
    if len(components['nonDebugCores']) < 2:
        logger.error("Not enough non-debug cores available")
        ds.shutdown()
        sys.exit(1)
    try:
        secapHSM = ds.openSession(components['nonDebugCores'][2])
    except Exception as e:
        logger.error(f"Failed to open session to C29 Secap: {e}")
        ds.shutdown()
        sys.exit(1)
    try:
        secapHSM.target.connect()
    except Exception as e:
        logger.error(f"Failed to connect to target: {e}")
        ds.shutdown()
        sys.exit(1)

    # Writing Get UID Command to HSM Secap
    try:
        secapHSM.registers.write("TRANSMIT_CONTROL", "0x00010000")
        logger.info("Wrote to TRANSMIT_CONTROL")
        secapHSM.registers.write("TRANSMIT_DATA", "0x35131696")
        logger.info("Wrote to TRANSMIT_DATA")
    except Exception as e:
        logger.error(f"Failed to write to registers: {e}")
        ds.shutdown()
        sys.exit(1)
                
    print("--->> Override request sent. \n")

    with open(args.dev_recov_cert, 'rb') as f:
        file_data = f.read()
    
    try:
        # Get file size
        file_size = os.path.getsize(args.dev_recov_cert)
        print(f"File size: {file_size} bytes")
    except OSError as err:
        print(f"Error getting file size: {err}")
        raise err

    # Read the entire file
    try:
        with open(args.dev_recov_cert, "rb") as file:
            file_data = file.read()
        print(f"Successfully read {len(file_data)} bytes from file")
    except OSError as err:
        print(f"Error reading file: {err}")
        raise err

    # Calculate total number of chunks
    total_chunks = -(-file_size // CHUNK_SIZE)  # Ceiling division
    print(f"Total chunks to process: {total_chunks}")

    # Process file in 4-byte chunks via TRANSMIT_DATA in reverse order
    offset = 0
    sequential_chunk_index = 1

    while offset < file_size:
        current_chunk_size = min(CHUNK_SIZE, file_size - offset)
        chunk_data = file_data[offset:offset + current_chunk_size]

        # Convert chunk to 32-bit value (little-endian) with proper unsigned handling
        data_value = 0
        for i, byte in enumerate(chunk_data):
            data_value |= (byte << (i * 8))

        # Ensure unsigned 32-bit value
        data_value = data_value & 0xFFFFFFFF

        # Calculate reverse chunk number (totalChunks, totalChunks-1, ..., 1)
        chunk_number = total_chunks - sequential_chunk_index + 1

        print(f"Processing chunk {chunk_number} (sequential index {sequential_chunk_index}): offset={offset}, size={current_chunk_size}, data=0x{data_value:08x}")

        try:
            # Set TRANSMIT_CONTROL with chunk number in upper 16 bits
            transmit_control_value = (chunk_number << 16)
            # Assuming secapHSM is an object with a registers attribute
            # and write method to write to the TRANSMIT_CONTROL register
            secapHSM.registers.write("TRANSMIT_CONTROL", transmit_control_value)

            # Write data to TRANSMIT_DATA register
            secapHSM.registers.write("TRANSMIT_DATA", data_value)

            # Wait for the target to set the ready bit: (chunkNumber << 16) | 0x0001
            expected_value = (chunk_number << 16) | 0x00000001
            print(f"Waiting for chunk {chunk_number} to be consumed by target (expecting 0x{expected_value:08x})...")
            tcr = (secapHSM.registers.read("TRANSMIT_CONTROL"))
            while tcr == expected_value:
                tcr = (secapHSM.registers.read("TRANSMIT_CONTROL"))
                # print(f"Transmit Control 0x{tcr:08x} for 0x{expected_value:08x}")

            print(f"Chunk {chunk_number} successfully transmitted 0x{data_value:08x}")

        except Exception as error:
            print(f"Error transmitting chunk {chunk_number}: {error}")
            raise error

        # Update for next iteration
        offset += current_chunk_size
        sequential_chunk_index += 1

    print(f"Successfully transmitted {total_chunks} chunks ({file_size} bytes total) in reverse order")

    tcr = (secapHSM.registers.read("RECEIVE_CONTROL"))
    while ((tcr  & 0x0001) == 0):
        tcr = (secapHSM.registers.read("RECEIVE_CONTROL"))
        print("Waiting for Response")

    rdr = (secapHSM.registers.read("RECEIVE_DATA"))
    if rdr == 0xDEAD3A17:
        print("--->> OVERRIDE DONE: WIR_RESPONSE_SUCCESS")
    elif rdr == 0xDEADFA17:
        print("--->> OVERRIDE FAIL: WIR_RESPONSE_FAILURE")
    else:
        print(f"--->> ERROR! Invalid response: 0x{rdr:08x}")
    print("\n--->> Override test done\n")        
    # shutdown the debugger
    ds.shutdown()

if __name__ == "__main__":
    main()
