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
Example of using the new device architecture.

This file demonstrates how to use the device registry and factory
to create and use device instances.
"""

from .registry import DeviceRegistry, DeviceFactory
from .register import get_device_list
from apps.qtgui.utils.platform_utils import IS_WINDOWS

def print_available_devices():
    """Print all available devices and their variants."""
    print("Available devices:")
    for device in get_device_list():
        print(f"- {device['display_name']} ({device['device_name']}/{device['variant']})")
        print(f"  Description: {device['description']}")
    print()

def create_and_use_device():
    """Demonstrate creating and using a device instance."""
    # Create an F29H85x HSFS device
    device = DeviceFactory.create_device("f29h85x", "hsfs")
    if not device:
        print("Failed to create device")
        return
    
    print(f"Created device: {device.device_name} {device.device_variant}")
    
    # Get default parameters
    print("Default parameters:")
    for key, value in device.get_default_parameters().items():
        print(f"- {key}: {value}")
    print()
    
    # Configure the device
    device.boot_mode = "UART"
    # Set a default serial port based on platform
    device.serial_port = "COM1" if IS_WINDOWS else "/dev/ttyUSB0"
    
    # Generate a certificate
    print("Generating certificate...")
    # In a real application, you would call device.generate_certificate()
    # For this example, we just print the command that would be used
    print("Command parameters that would be used:")
    print(f"- Device: {device.device_name}")
    print(f"- Variant: {device.device_variant}")
    print(f"- Boot mode: {device.boot_mode}")
    print(f"- Serial port: {device.serial_port}")
    print(f"- Development session: {device.development_session_checkbox}")
    if device.development_session_checkbox:
        print(f"- SMPK algorithm: {device.smpk}")
        print(f"- BMPK algorithm: {device.bmpk}")
    else:
        print(f"- Session name: {device.sessionName}")
        print(f"- Session password: {'*' * len(device.sessionPassword) if device.sessionPassword else None}")

def check_device_compatibility():
    """Check if a specific device and variant is supported."""
    device_name = "f29h85x"
    variant = "hsfs"
    
    print(f"Checking if {device_name}/{variant} is supported...")
    
    model_class = DeviceRegistry.get_device_model_class(device_name, variant)
    if model_class:
        print(f"Device {device_name}/{variant} is supported.")
        print(f"Model class: {model_class.__name__}")
    else:
        print(f"Device {device_name}/{variant} is not supported.")

def main():
    """Run the example."""
    print_available_devices()
    create_and_use_device()
    check_device_compatibility()

if __name__ == "__main__":
    main()