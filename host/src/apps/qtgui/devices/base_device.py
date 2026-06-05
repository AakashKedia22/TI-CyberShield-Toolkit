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

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple


class BaseDevice(ABC):
    """
    Base abstract class for all device implementations.
    
    This class defines the interface that all device implementations must follow,
    providing common functionality and requiring specific implementations to be
    provided by subclasses.
    """
    
    def __init__(self, device_name: str, device_variant: str, device_family: str):
        """
        Initialize a device instance.

        Args:
            device_name (str): Name of the device (e.g., "f29h85x")
            device_variant (str): Variant of the device (e.g., "hsfs", "hsse")
            device_family (str): Device family (e.g., "asm")
        """
        self.device_name = device_name.lower()
        self.device_variant = device_variant.lower()
        self.device_family = device_family
        self.boot_mode = None
        self.serial_port = None
        self.ccs_path = None
        self.certificate = None

    @abstractmethod
    def generate_certificate(self, **kwargs) -> bool:
        """
        Generate a certificate for the device.
        
        Args:
            **kwargs: Device-specific certificate parameters
            
        Returns:
            bool: True if certificate generation was successful, False otherwise
        """
        pass
        
    @abstractmethod
    def convert_device(self) -> bool:
        """
        Convert the device to a specific security state.
        
        Returns:
            bool: True if conversion was successful, False otherwise
        """
        pass
        
    @abstractmethod
    def get_soc_id(self, port: str) -> Dict[str, Any]:
        """
        Get SoC ID from the device.
        
        Args:
            port (str): Serial port to use
            
        Returns:
            Dict[str, Any]: Dictionary containing device information
        """
        pass
        
    @abstractmethod
    def get_device_type(self, ccs_path: str = None) -> Optional[str]:
        """
        Get device type using JTAG.
        
        Args:
            ccs_path (str, optional): Path to CCS installation
            
        Returns:
            Optional[str]: Device type if successful, None otherwise
        """
        pass
    
    def get_supported_variants(self) -> List[str]:
        """
        Get list of supported variants for this device.
        
        Returns:
            List[str]: List of supported variant names
        """
        return ["hsfs", "hsse"]
    
    def get_supported_boot_modes(self) -> List[str]:
        """
        Get list of supported boot modes for this device.
        
        Returns:
            List[str]: List of supported boot modes
        """
        return ["UART", "JTAG"]
    
    def get_default_parameters(self) -> Dict[str, Any]:
        """
        Get default parameters for this device.
        
        Returns:
            Dict[str, Any]: Dictionary of default parameter values
        """
        return {}
    
    @abstractmethod
    def validate_parameters(self, parameters: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate the provided parameters for this device.
        
        Args:
            parameters (Dict[str, Any]): Parameters to validate
            
        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        pass