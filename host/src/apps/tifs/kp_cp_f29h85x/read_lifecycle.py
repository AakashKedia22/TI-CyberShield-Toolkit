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
# We also need access to re package to use regular expressions
import re
# We also need access to sys package to exit the program with an exit code
import sys
import platform
# import the scripting module. Will not work without launch.py if PYTHONPATH is not set correctly
from scripting import initScripting, ScriptingTimeoutError, ScriptingOptions

# Import platform utilities
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))), "src"))
from common.platform_utils import get_script_dir, join_path

# Set up logging if desired
import logging
logger = logging.getLogger("TI.scripting")
logger.setLevel(logging.NOTSET)

# Initialize scripting and obtain the main debugger scripting interface
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

# Load program
# The path provided must be an absolute path. Here we use the current script's location
# to resolve the location.
value = session.memory.read("0x301803D4", 1, 32)

# Extract the first value from the list
value = value[0] if isinstance(value, list) else value

# Extract HSSUBTYPE field (bits 11-8)
hssubtype = (value >> 8) & 0xF

# Check device state based on HSSUBTYPE field values
if hssubtype == 0x3:  # KP - Keys Provisioned
    print("Device is in HS_KP state")
elif hssubtype == 0xA:  # FS - Field Securable
    print("Device is in HS_FS state")
elif hssubtype == 0xF:  # Not FA, so must be SE
    print("Device is in HS_FA state")
else:
    print("Device is in HS_SE state")

'''
# Set a breakpoint at ReadNextData
bp1 = session.breakpoints.add("ReadNextData")

# Set a second breakpoint using the address of the function ShapingFilter
bp2Addr = session.expressions.evaluate("ShapingFilter")
bp2 = session.breakpoints.add(bp2Addr)


# Let's define a function to run the target and check if it halts at the correct symbol
def expectRunToHaltAt(symbol):
    # Run the target and wait for it to halt
    session.target.run()

    symbolAddr = session.expressions.evaluate(symbol)
    pc = session.registers.read("PC")
    if pc == symbolAddr:
        print(f"Success: target is halted at {symbol} as expected.")
    else:
        print(
            f"Failure: Expected target to be halted at 0x{symbolAddr.toString(16)}, "
            f"but is actually halted at 0x{pc.toString(16)}."
        )
        sys.exit(1)

# If we run, we should hit our first breakpoint at ReadNextData
expectRunToHaltAt("ReadNextData")

# If we run a second time, we expect to halt at our second breakpoint
expectRunToHaltAt("ShapingFilter")

# Remove our first breakpoint
session.breakpoints.remove(bp1)

# The program runs in an infinite loop, so running a third time should, once again, halt at the second breakpoint
expectRunToHaltAt("ShapingFilter")

# If we remove our second breakpoint as well, we expect to run in a loop until we time out
session.breakpoints.remove(bp2)

# We expect the next run to timeout, let's reduce the timeout duration so we don't have to wait as long
ds.setScriptingTimeout(2000)

try:
    print("Expecting target to not halt for 2 seconds")
    session.target.run()
    print("Failure: Halted unexpectedly after removing both breakpoints.")
except Exception as err:
    # Check if we actually timed out, or if some other error occurred
    if isinstance(err, ScriptingTimeoutError):
        print("Success: we timed out while waiting for the target to halt")
        session.target.halt()
    else:
        print(f"Failure: unexpected error while running {err}")
        
        
'''
# shutdown the debugger

ds.shutdown()
