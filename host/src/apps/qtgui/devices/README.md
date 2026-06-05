# Device Scalability Architecture

This document describes the new device architecture that provides better scalability and support for different device variants.

## Overview

The new architecture implements:

- A device registry that maps device types to their variants
- A factory pattern for creating device instances
- A hierarchical class structure for device implementations
- Configuration-based device parameters
- UI support for device variant selection

## Directory Structure

```
devices/
├── __init__.py
├── base_device.py      # Abstract base class for all devices
├── registry.py         # Device registry and factory
├── register.py         # Device registration module
├── README.md           # This file
├── f29h85x/            # F29H85x device implementations
│   ├── __init__.py
│   ├── common.py       # Common F29H85x functionality
│   ├── hsfs.py         # F29H85x HSFS implementation
│   └── hsse.py         # F29H85x HSSE implementation
├── am62px/             # AM62Px device implementations (placeholder)
└── j722s/              # J722S device implementations (placeholder)
```

## Key Components

### Base Device Class

The `BaseDevice` abstract class defines the interface that all device implementations must follow:

- `generate_certificate()`: Generate a certificate for the device
- `convert_device()`: Convert the device to a specific security state
- `get_soc_id()`: Get SoC ID from the device
- `get_device_type()`: Get device type using JTAG
- `validate_parameters()`: Validate device parameters

### Device Registry

The `DeviceRegistry` class maintains mappings between device types/variants and their implementation classes:

- `register_device_model()`: Register a device model class
- `register_device_view()`: Register a device view class
- `register_device_controller()`: Register a device controller class
- `register_device_config()`: Register configuration data for a device
- `get_supported_devices()`: Get all supported device names
- `get_supported_variants()`: Get supported variants for a device

### Device Factory

The `DeviceFactory` class creates instances of the appropriate classes:

- `create_device()`: Create a device model instance
- `create_view()`: Create a device view instance
- `create_controller()`: Create a device controller instance

### Configuration-Based Parameters

Device parameters are defined in configuration files:

- Default parameters are specified in the `register.py` file
- These can be overridden at runtime when creating device instances

## Adding a New Device

To add a new device type or variant:

1. Create a new device class that extends `BaseDevice`
2. Register the device in `register.py`
3. Define the device configuration in `register.py`

### Example: Adding a new device

```python
# 1. Create the device class (my_device/new_variant.py)
class MyDeviceNewVariant(BaseDevice):
    def __init__(self, device_name, device_variant, **kwargs):
        super().__init__(device_name, device_variant, **kwargs)
        # Add device-specific initialization
    
    def generate_certificate(self, **kwargs):
        # Implement certificate generation
        pass
    
    def convert_device(self):
        # Implement device conversion
        pass
    
    def get_soc_id(self, port):
        # Implement SoC ID retrieval
        pass
    
    def get_device_type(self, ccs_path=None):
        # Implement device type detection
        pass
    
    def validate_parameters(self, parameters):
        # Implement parameter validation
        return True, ""

# 2. Register the device (register.py)
from .my_device.new_variant import MyDeviceNewVariant

# Define configuration
MY_DEVICE_CONFIG = {
    'parameter1': 'value1',
    'parameter2': 'value2',
    'display_name': 'My Device New Variant',
    'description': 'Description of my new device variant'
}

# Register the device
DeviceRegistry.register_device_model("my_device", "new_variant", MyDeviceNewVariant)
DeviceRegistry.register_device_config("my_device", "new_variant", MY_DEVICE_CONFIG)
```

## UI Integration

The UI has been enhanced to support device variant selection with the `DeviceVariantSelector` component. This provides:

- A device dropdown for selecting the device model
- A variant dropdown that updates based on the selected device
- Appropriate display names for devices and variants

## Backward Compatibility

The new architecture maintains backward compatibility with existing code:

- The `settings.py` file continues to export the legacy device lists
- Device detection and handling logic falls back to legacy implementations when needed