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

from typing import Dict, Any, Optional, Type, List, Callable, Tuple
from .base_device import BaseDevice

class DeviceRegistry:
    """
    Registry for device models, views, controllers, and components.
    
    This registry maintains mappings between device types/variants and their
    corresponding implementation classes, allowing dynamic creation of the
    appropriate classes at runtime.
    """
    
    # Dictionaries to store registered classes
    _device_models: Dict[str, Type[BaseDevice]] = {}
    _device_views: Dict[str, Type[Any]] = {}
    _device_controllers: Dict[str, Type[Any]] = {}
    _device_configs: Dict[str, Dict[str, Any]] = {}
    
    # Maps device models to their supported variants
    _device_variants: Dict[str, List[str]] = {}
    
    @classmethod
    def register_device_model(cls, device_name: str, variant: str, model_class: Type[BaseDevice]) -> None:
        """
        Register a device model class for a device name and variant.
        
        Args:
            device_name (str): The name of the device (e.g., "f29h85x")
            variant (str): The variant of the device (e.g., "hsfs", "hsse")
            model_class (Type[BaseDevice]): The model class for the device variant
        """
        key = f"{device_name.lower()}_{variant.lower()}"
        cls._device_models[key] = model_class
        
        # Update the variants mapping
        device_key = device_name.lower()
        if device_key not in cls._device_variants:
            cls._device_variants[device_key] = []
        
        if variant.lower() not in cls._device_variants[device_key]:
            cls._device_variants[device_key].append(variant.lower())
    
    @classmethod
    def register_device_view(cls, device_name: str, variant: str, view_class: Type[Any]) -> None:
        """
        Register a device view class for a device name and variant.
        
        Args:
            device_name (str): The name of the device (e.g., "f29h85x")
            variant (str): The variant of the device (e.g., "hsfs", "hsse")
            view_class (Type[Any]): The view class for the device variant
        """
        key = f"{device_name.lower()}_{variant.lower()}"
        cls._device_views[key] = view_class
    
    @classmethod
    def register_device_controller(cls, device_name: str, variant: str, controller_class: Type[Any]) -> None:
        """
        Register a device controller class for a device name and variant.
        
        Args:
            device_name (str): The name of the device (e.g., "f29h85x")
            variant (str): The variant of the device (e.g., "hsfs", "hsse")
            controller_class (Type[Any]): The controller class for the device variant
        """
        key = f"{device_name.lower()}_{variant.lower()}"
        cls._device_controllers[key] = controller_class
    
    @classmethod
    def register_device_config(cls, device_name: str, variant: str, config: Dict[str, Any]) -> None:
        """
        Register configuration data for a device and variant.
        
        Args:
            device_name (str): The name of the device (e.g., "f29h85x")
            variant (str): The variant of the device (e.g., "hsfs", "hsse")
            config (Dict[str, Any]): Configuration data for the device variant
        """
        key = f"{device_name.lower()}_{variant.lower()}"
        cls._device_configs[key] = config
    
    @classmethod
    def get_device_model_class(cls, device_name: str, variant: str) -> Optional[Type[BaseDevice]]:
        """
        Get the model class for a device name and variant.
        
        Args:
            device_name (str): The name of the device
            variant (str): The variant of the device
            
        Returns:
            Optional[Type[BaseDevice]]: The model class if found, None otherwise
        """
        key = f"{device_name.lower()}_{variant.lower()}"
        return cls._device_models.get(key)
    
    @classmethod
    def get_device_view_class(cls, device_name: str, variant: str) -> Optional[Type[Any]]:
        """
        Get the view class for a device name and variant.
        
        Args:
            device_name (str): The name of the device
            variant (str): The variant of the device
            
        Returns:
            Optional[Type[Any]]: The view class if found, None otherwise
        """
        key = f"{device_name.lower()}_{variant.lower()}"
        return cls._device_views.get(key)
    
    @classmethod
    def get_device_controller_class(cls, device_name: str, variant: str) -> Optional[Type[Any]]:
        """
        Get the controller class for a device name and variant.
        
        Args:
            device_name (str): The name of the device
            variant (str): The variant of the device
            
        Returns:
            Optional[Type[Any]]: The controller class if found, None otherwise
        """
        key = f"{device_name.lower()}_{variant.lower()}"
        return cls._device_controllers.get(key)
    
    @classmethod
    def get_device_config(cls, device_name: str, variant: str) -> Dict[str, Any]:
        """
        Get configuration data for a device and variant.
        
        Args:
            device_name (str): The name of the device
            variant (str): The variant of the device
            
        Returns:
            Dict[str, Any]: Configuration data (empty dict if not found)
        """
        key = f"{device_name.lower()}_{variant.lower()}"
        return cls._device_configs.get(key, {})
    
    @classmethod
    def get_supported_devices(cls) -> List[str]:
        """
        Get a list of all supported device names.
        
        Returns:
            List[str]: List of device names
        """
        return list(cls._device_variants.keys())
    
    @classmethod
    def get_supported_variants(cls, device_name: str) -> List[str]:
        """
        Get a list of supported variants for a device.
        
        Args:
            device_name (str): The name of the device
            
        Returns:
            List[str]: List of supported variant names
        """
        device_key = device_name.lower()
        return cls._device_variants.get(device_key, [])


class DeviceFactory:
    """
    Factory for creating device models, views, and controllers.
    
    This factory uses the DeviceRegistry to create instances of the appropriate
    classes based on the device name and variant.
    """
    
    @staticmethod
    def create_device(device_name: str, variant: str, **kwargs) -> Optional[BaseDevice]:
        """
        Create a device model instance.
        
        Args:
            device_name (str): The name of the device
            variant (str): The variant of the device
            **kwargs: Additional parameters for device initialization
            
        Returns:
            Optional[BaseDevice]: Device instance if successful, None otherwise
        """
        model_class = DeviceRegistry.get_device_model_class(device_name, variant)
        if model_class:
            # Merge configuration with provided kwargs
            config = DeviceRegistry.get_device_config(device_name, variant)
            merged_kwargs = {**config, **kwargs}
            
            # Create the device instance
            return model_class(device_name, variant, **merged_kwargs)
        return None
    
    @staticmethod
    def create_view(device_name: str, variant: str, **kwargs) -> Optional[Any]:
        """
        Create a device view instance.
        
        Args:
            device_name (str): The name of the device
            variant (str): The variant of the device
            **kwargs: Additional parameters for view initialization
            
        Returns:
            Optional[Any]: View instance if successful, None otherwise
        """
        view_class = DeviceRegistry.get_device_view_class(device_name, variant)
        if view_class:
            return view_class(**kwargs)
        return None
    
    @staticmethod
    def create_controller(device_name: str, variant: str, model: BaseDevice, view: Any) -> Optional[Any]:
        """
        Create a device controller instance.
        
        Args:
            device_name (str): The name of the device
            variant (str): The variant of the device
            model (BaseDevice): The device model instance
            view (Any): The device view instance
            
        Returns:
            Optional[Any]: Controller instance if successful, None otherwise
        """
        controller_class = DeviceRegistry.get_device_controller_class(device_name, variant)
        if controller_class:
            return controller_class(model, view)
        return None