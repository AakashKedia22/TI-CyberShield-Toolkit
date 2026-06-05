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

# Legacy device and type definitions (maintained for backward compatibility)
legacy_devices = ["F29H85x", 'AM26', 'AM62Px', 'J722S']
boot_modes = ["UART", "JTAG"]
device_type = ['HSSE', 'HSFS', 'HSKP']

# New device registry-based definitions
# These will be populated when devices.register is imported
devices = []
device_variants = {}
device_display_names = {}

try:
    # Try to import the device registry
    from .devices.register import get_device_list, get_device_display_name
    
    # Get the list of registered devices
    registered_devices = get_device_list()
    
    # Build the devices list (device_name only, for backward compatibility)
    unique_device_names = set()
    for device in registered_devices:
        unique_device_names.add(device['device_name'].upper())
    
    devices = list(unique_device_names)
    
    # Build the device variants mapping
    for device in registered_devices:
        device_name = device['device_name'].upper()
        if device_name not in device_variants:
            device_variants[device_name] = []
        
        variant = device['variant'].upper()
        if variant not in device_variants[device_name]:
            device_variants[device_name].append(variant)
            
        # Store the display name
        key = f"{device_name}_{variant}"
        device_display_names[key] = device['display_name']
    
except ImportError:
    # If the registry isn't available, use legacy definitions
    devices = legacy_devices
    # Default variants for legacy devices
    device_variants = {
        "F29H85X": ["HSFS", "HSSE"],
        "AM26": ["HSFS", "HSSE"],
        "AM62PX": ["HSFS", "HSSE"],
        "J722S": ["HSFS", "HSSE"]
    }
    # Default display names
    device_display_names = {
        "F29H85X_HSFS": "F29H85x HSFS",
        "F29H85X_HSSE": "F29H85x HSSE",
        "AM26_HSFS": "AM26 HSFS",
        "AM26_HSSE": "AM26 HSSE",
        "AM62PX_HSFS": "AM62Px HSFS",
        "AM62PX_HSSE": "AM62Px HSSE",
        "J722S_HSFS": "J722S HSFS",
        "J722S_HSSE": "J722S HSSE"
    }

# Helper functions
def get_variants_for_device(device_name):
    """Get the variants for a device."""
    return device_variants.get(device_name.upper(), [])

def get_display_name(device_name, variant):
    """Get the display name for a device and variant."""
    key = f"{device_name.upper()}_{variant.upper()}"
    return device_display_names.get(key, f"{device_name} {variant}")