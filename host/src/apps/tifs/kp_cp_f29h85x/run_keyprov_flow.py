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

# Since we don't know where CCS will be installed, we must find files relative
# to this script. To this end, we will need access to os package
import os
import sys
import argparse
import platform
import struct
import tempfile
# import the scripting module. Will not work without launch.py if PYTHONPATH is not set correctly
from scripting import initScripting, ScriptingTimeoutError, ScriptingOptions

# Import platform utilities
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))), "src"))
from common.platform_utils import get_script_dir, join_path

# Set up logging if desired
import logging
logger = logging.getLogger("TI.scripting")
logger.setLevel(logging.NOTSET)

# Parse command line arguments
def parse_args():
    """Parse command line arguments for the key provisioning flow"""
    parser = argparse.ArgumentParser(
        description='Run key provisioning flow for F29H85x device',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--otp-kw-bin',
        required=True,
        help='Path to OTP KW binary file (required)',
        metavar='<path>'
    )
    
    parser.add_argument(
        '--certificate',
        required=True,
        help='Path to certificate file (required)',
        metavar='<path>'
    )
    
    parser.add_argument(
        '--jtag-kernel',
        required=True,
        help='Path to JTAG flash kernel file (required)',
        metavar='<path>'
    )
    
    args = parser.parse_args()
    
    # Validate that files exist
    files_to_check = [
        ('--otp-kw-bin', args.otp_kw_bin),
        ('--certificate', args.certificate),
        ('--jtag-kernel', args.jtag_kernel)
    ]
    
    for arg_name, file_path in files_to_check:
        if not os.path.exists(file_path):
            print(f"Error: File not found for {arg_name}: {file_path}")
            sys.exit(1)
    
    # Convert to absolute paths
    args.otp_kw_bin = os.path.abspath(args.otp_kw_bin)
    args.certificate = os.path.abspath(args.certificate)
    args.jtag_kernel = os.path.abspath(args.jtag_kernel)
    
    return args

# Main execution
def main():
    # Get file paths from command line arguments
    args = parse_args()
    
    print(f"OTP KW Binary: {args.otp_kw_bin}")
    print(f"Certificate: {args.certificate}")
    print(f"JTAG Kernel: {args.jtag_kernel}")
    
    # Initialize scripting and obtain the main debugger scripting interface
    # Using suppressMessages equivalent - no direct equivalent in Python, using minimal logging
    ds = initScripting()
    
    # Configure a 1 minute timeout on all operations (by default there is no timeout).
    # Key provisioning can take >30s (cert processing alone ~3.6s on HS-FS) so 10s is too short.
    ds.setScriptingTimeout(60000)
    
    # Configure the debugger and open a debug session to the cortex M core
    # Check for PyInstaller temp directory first, then fall back to script_dir
    script_dir = get_script_dir()
    ccxml_path = os.environ.get('CCXML_PATH', join_path(script_dir, "F29h85x-hsse.ccxml"))
    ds.configure(ccxml_path)
    session = ds.openSession("Texas Instruments XDS110 USB Debug Probe/C29xx_CPU1")

    session.target.connect()

    # Begin capture to log file (overwrite if it already exists)
    log_file_path = join_path(script_dir, "log.txt")
    session.cio.beginCapture(log_file_path)
    
    session.target.halt()
    
    # Load the OTP KW binary at a fixed address i.e. 0x200E0000
    print(f"Loading OTP KW binary from: {args.otp_kw_bin}")
    session.memory.loadBinary(0x200E0000, args.otp_kw_bin)
    
    # Load the OTP KW certificate at a fixed address i.e. 0x200F8000
    print(f"Loading certificate from: {args.certificate}")
    session.memory.loadBinary(0x200F8000, args.certificate)
    
    # Write CMD_CTRL_REG bitmask: CMD_BIT_HSM_RT | CMD_BIT_HSM_KEYS
    cmd_bits = 0x00000003  # CMD_BIT_HSM_RT | CMD_BIT_HSM_KEYS
    fd, cmd_bits_tmp = tempfile.mkstemp(suffix='.bin')
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(struct.pack('<I', cmd_bits))
        print(f"Writing CMD_CTRL_REG bitmask 0x{cmd_bits:08X} to 0x30180508")
        session.memory.loadBinary(0x30180508, cmd_bits_tmp)
    finally:
        os.unlink(cmd_bits_tmp)

    # Load a JTAG flash Kernel out file to a fixed location
    print(f"Loading JTAG flash kernel from: {args.jtag_kernel}")
    session.memory.loadProgram(args.jtag_kernel)
    
    # Run the target, till stopped.
    try:
        print("Expecting target to not halt for 120 seconds")
        session.target.run()
        print("Failure: Halted unexpectedly after removing both breakpoints.")
    except Exception as err:
        # Check if we actually timed out, or if some other error occurred
        if isinstance(err, ScriptingTimeoutError):
            print("Success: we timed out while waiting for the target to halt")
            session.target.halt()
        else:
            print(f"Failure: unexpected error while running {err}")

    # End CIO capture to flush all buffered output to log.txt before reading it
    try:
        session.cio.endCapture()
    except Exception:
        pass

    # Read and print the contents of log.txt
    try:
        with open(log_file_path, 'r') as log_file:
            log_content = log_file.read()
            print("Log file contents:")
            print(log_content)
    except FileNotFoundError:
        print(f"Warning: Log file not found at {log_file_path}")
    except Exception as e:
        print(f"Error reading log file: {e}")
        
        
    session.target.disconnect()
    # Shutdown the debugger
    ds.shutdown()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
