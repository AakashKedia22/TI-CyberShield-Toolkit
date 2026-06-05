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
# import the scripting module. Will not work without launch.py if PYTHONPATH is not set correctly
from scripting import initScripting, ScriptingTimeoutError, ScriptingOptions
# Set up logging if desired
import logging
logger = logging.getLogger("TI.scripting")
logger.setLevel(logging.INFO)
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
# Configure the debugger and open a debug session to the C29 Secap
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
    secapC29 = ds.openSession(components['nonDebugCores'][1])
except Exception as e:
    logger.error(f"Failed to open session to C29 Secap: {e}")
    ds.shutdown()
    sys.exit(1)
try:
    secapC29.target.connect()
except Exception as e:
    logger.error(f"Failed to connect to target: {e}")
    ds.shutdown()
    sys.exit(1)
# Writing Device Recovery Command to C29 Secap
try:
    secapC29.registers.write("TRANSMIT_CONTROL", "0x244")
    logger.info(f"Value 0x244 written to TRANSMIT_CONTROL register")
    secapC29.registers.write("TRANSMIT_DATA", "0x65EA6103")
    logger.info(f"Value 0x65EA6103 written to TRANSMIT_DATA register")
    logger.info("Device Recovery Command Sent")
except Exception as e:
    logger.error(f"Failed to write to registers: {e}")
    ds.shutdown()
    sys.exit(1)
try:
    secapC29.target.halt()
except Exception as e:
    logger.error(f"Failed to halt target: {e}")
    ds.shutdown()
    sys.exit(1)
try:
    ds.shutdown()
except Exception as e:
    logger.error(f"Failed to shut down debugger: {e}")
    sys.exit(1)