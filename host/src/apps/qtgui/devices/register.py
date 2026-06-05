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
Device registration module.

This module registers all device implementations with the device registry.
"""

from .registry import DeviceRegistry
from .f29h85x.hsfs import F29H85xHSFSDevice
from .f29h85x.hsse import F29H85xHSSEDevice
import json
import os
import pathlib

def _get_tisecprov_path():
    """Get the path to the tisecprov directory."""
    # Get the base path
    current_dir = os.getcwd()
    path = pathlib.Path(current_dir)
    
    # Find tisecprov directory
    while path.name != "tisecprov" and path != path.parent:
        path = path.parent
        
    # If tisecprov not found, use current directory
    if path.name != "tisecprov":
        path = pathlib.Path(current_dir)
        
    return path

# Get the base path
TISECPROV_PATH = _get_tisecprov_path()

def _load_device_json(json_path):
    with open(json_path, "r") as f:
        return json.load(f)

def _resolve_device_paths(data, base_path):
    """Resolve relative path strings in a flat dict against base_path."""
    result = {}
    for k, v in data.items():
        if isinstance(v, str) and "/" in v and not v.startswith("/"):
            if v.startswith("../"):
                result[k] = str(base_path.parent / v[3:])
            else:
                result[k] = str(base_path / v)
        else:
            result[k] = v
    return result

_F29_JSON_PATH = pathlib.Path(__file__).parent / "f29h85x" / "device.json"
_f29_data = _load_device_json(str(_F29_JSON_PATH))


def _build_provisioning_ui(prov_data):
    """Inject shared_main_fields into each boot-mode entry where main_fields is null."""
    ui = prov_data.get("ui", {})
    if not ui:
        return {}
    shared = prov_data.get("shared_main_fields", [])
    result = {}
    for mode, mode_spec in ui.items():
        entry = dict(mode_spec)
        if entry.get("main_fields") is None and shared:
            entry["main_fields"] = list(shared)
        result[mode] = entry
    return result

F29H85X_HSFS_CONFIG = {}
F29H85X_HSFS_CONFIG.update(_resolve_device_paths(_f29_data["variants"]["hsfs"], TISECPROV_PATH))
F29H85X_HSFS_CONFIG.update({
    "device_family":       _f29_data["device_family"],
    "device_name":         _f29_data["device_name"],
    "cert_fields":         _f29_data["cert_fields"],
    "cert_flags":          _f29_data["cert_flags"],
    "key_options":         _f29_data["key_options"],
    "boot_modes":          _f29_data.get("boot_modes",          ["UART", "JTAG"]),
    "binary_signing":      _f29_data.get("binary_signing",      False),
    "advanced_tabs":       _f29_data.get("advanced_tabs",       []),
    "device_states":       _f29_data.get("device_states",       ["HSFS", "HSKP", "HSSE"]),
    "device_state_labels": _f29_data.get("device_state_labels", {}),
    "initial_state":       _f29_data.get("initial_state",       "HSFS"),
    "provisioning_type":   _f29_data.get("provisioning_type",   "f29"),
    "key_provisioning":    _f29_data.get("key_provisioning",    {}),
    "code_provisioning":   _f29_data.get("code_provisioning",   {}),
    "key_provisioning_ui":  _build_provisioning_ui(_f29_data.get("key_provisioning",  {})),
    "code_provisioning_ui": _build_provisioning_ui(_f29_data.get("code_provisioning", {})),
    "target_config_prefix": _f29_data.get("target_config_prefix", "f29"),
    "target_config_dest":   _f29_data.get("target_config_dest",   ""),
    "tifek_subpath":        _f29_data.get("tifek_subpath",        "f29h85x"),
})

F29H85X_HSSE_CONFIG = dict(F29H85X_HSFS_CONFIG)
F29H85X_HSSE_CONFIG.update(_resolve_device_paths(_f29_data["variants"]["hsse"], TISECPROV_PATH))

# Register F29H85x HSFS device
DeviceRegistry.register_device_model("f29h85x", "hsfs", F29H85xHSFSDevice)
DeviceRegistry.register_device_config("f29h85x", "hsfs", F29H85X_HSFS_CONFIG)

# Register F29H85x HSSE device
DeviceRegistry.register_device_model("f29h85x", "hsse", F29H85xHSSEDevice)
DeviceRegistry.register_device_config("f29h85x", "hsse", F29H85X_HSSE_CONFIG)

# TODO: Register AM62Px devices when implemented
# TODO: Register J722S devices when implemented

# ---------------------------------------------------------------------------
# Certificate field specifications
# ---------------------------------------------------------------------------

# Always-on protection flags for F29H85x certificates
F29H85X_CERT_FLAGS = [
    "msv_protect", "s_protect", "smek_protect", "b_protect", "bmek_protect",
    "keycnt_protect", "smpk", "smek", "bmpk", "bmek",
]

# Field specs for F29H85x certificate generation
F29H85X_CERT_FIELDS = [
    # Top-level (rendered above Advanced Settings, tab=None)
    {
        "key": "output_dir_path",
        "label": "Output Folder",
        "widget_type": "dir_browse",
        "default": "",
        "tab": None,
        "required": True,
    },
    # Basic tab
    {
        "key": "pub_key_path",
        "label": "TI FEK Public Key",
        "widget_type": "file_browse",
        "default": "",
        "tab": "Basic",
        "required": True,
    },
    {
        "key": "msv",
        "label": "MSV",
        "widget_type": "text",
        "default": "0x1E22D",
        "tab": "Basic",
    },
    {
        "key": "dev_sr_ver",
        "label": "Device SR Version",
        "widget_type": "combo",
        "default": "SR_20",
        "tab": "Basic",
        "options": [
            ("Software Release v10 (RevA Silicon)", "SR_10"),
            ("Software Release v20 (RevB Silicon)", "SR_20"),
        ],
    },
    # Keys tab
    {
        "key": "keycnt",
        "label": "Program Keys",
        "widget_type": "combo",
        "default": "2",
        "tab": "Keys",
        "options": [
            ("SMPK", "1"),
            ("SMPK and BMPK", "2"),
        ],
    },
    {
        "key": "keyrev",
        "label": "Key Revision",
        "widget_type": "combo",
        "default": "1",
        "tab": "Keys",
        "options": [
            ("Use SMPK (1)", "1"),
            ("Use BMPK (2)", "2"),
        ],
    },
    # SW Revisions tab
    {
        "key": "sr_sbl",
        "label": "SBL",
        "widget_type": "text",
        "default": "1",
        "tab": "SW Revisions",
    },
    {
        "key": "sr_hsmRT",
        "label": "HSM Runtime",
        "widget_type": "text",
        "default": "1",
        "tab": "SW Revisions",
    },
    {
        "key": "sr_app",
        "label": "CPU1 Application",
        "widget_type": "text",
        "default": "1",
        "tab": "SW Revisions",
    },
    {
        "key": "sr_ssu",
        "label": "CPU1 SECCFG",
        "widget_type": "text",
        "default": "1",
        "tab": "SW Revisions",
    },
    # Extended OTP tab
    {
        "key": "ext_otp",
        "label": "Extended OTP Value",
        "widget_type": "text",
        "default": "0x80000001",
        "tab": "Extended OTP",
    },
    {
        "key": "ext_otp_indx",
        "label": "Extended OTP Index",
        "widget_type": "combo",
        "default": "0",
        "tab": "Extended OTP",
        "options": [("0", "0"), ("1", "1"), ("2", "2"), ("3", "3")],
    },
    {
        "key": "ext_otp_size",
        "label": "Extended OTP Size",
        "widget_type": "text",
        "default": "32",
        "tab": "Extended OTP",
    },
]

# Field specs for standard devices (AM261x, AM263Px, etc.)
STANDARD_CERT_FIELDS = [
    # Top-level fields
    {
        "key": "output_dir_path",
        "label": "Output Folder",
        "widget_type": "dir_browse",
        "default": "",
        "tab": None,
        "required": True,
    },
    {
        "key": "is_multishot",
        "label": "Multishot",
        "widget_type": "checkbox",
        "default": False,
        "tab": None,
    },
    # Basic tab
    {
        "key": "pub_key_path",
        "label": "TI FEK Public Key",
        "widget_type": "file_browse",
        "default": "",
        "tab": "Basic",
        "required": True,
    },
    {
        "key": "msv",
        "label": "Model Specific Value",
        "widget_type": "text",
        "default": "0x00001",
        "tab": "Basic",
        "placeholder": "0x00001",
    },
    # Key Flags tab — individual checkboxes, read by wizard_controller FLAG_MAP
    {
        "key": "mpk_write_protect",
        "label": "MPK write protect",
        "widget_type": "checkbox",
        "default": False,
        "tab": "Key Flags",
    },
    {
        "key": "mpk_read_protect",
        "label": "MPK read protect",
        "widget_type": "checkbox",
        "default": False,
        "tab": "Key Flags",
    },
    {
        "key": "mpk_override",
        "label": "MPK override",
        "widget_type": "checkbox",
        "default": False,
        "tab": "Key Flags",
    },
    {
        "key": "mpk_active",
        "label": "MPK active",
        "widget_type": "checkbox",
        "default": True,
        "tab": "Key Flags",
    },
    {
        "key": "mek_write_protect",
        "label": "MEK write protect",
        "widget_type": "checkbox",
        "default": False,
        "tab": "Key Flags",
    },
    {
        "key": "mek_read_protect",
        "label": "MEK read protect",
        "widget_type": "checkbox",
        "default": False,
        "tab": "Key Flags",
    },
    {
        "key": "mek_override",
        "label": "MEK override",
        "widget_type": "checkbox",
        "default": False,
        "tab": "Key Flags",
    },
    {
        "key": "mek_active",
        "label": "MEK active",
        "widget_type": "checkbox",
        "default": True,
        "tab": "Key Flags",
    },
]

STANDARD_KEY_OPTIONS = [
    {"key_type": "new",      "label": "Generate new keys"},
    {"key_type": "existing", "label": "Use existing secure session"},
    {"key_type": "sdk",      "label": "Use SDK dummy keys"},
    {"key_type": "pkcs11",   "label": "Use PKCS#11 Smart Card"},
]

STANDARD_DEVICE_CONFIG = {
    "boot_modes": [
        {
            "id": "UART", "connection_type": "uart",
            "connection_widget": "serial", "connection_param": "port",
            "extra_params": {}, "session_params": []
        }
    ],
    "binary_signing": False,
    "advanced_tabs": [],
    # Provisioning spec for standard devices (AM261x, AM263Px, etc.)
    "device_states":       ["READY", "PROVISIONED"],
    "device_state_labels": {"READY": "Ready", "PROVISIONED": "Provisioned"},
    "initial_state":       "READY",
    "provisioning_type":   "standard",
    "key_provisioning": {
        "enabled_in_states": ["READY"],
        "files": [
            {"id": "firmware",    "label": "Firmware Image", "required": True},
            {"id": "certificate", "label": "Certificate",    "required": True},
        ],
    },
    "code_provisioning": {
        "enabled_in_states": ["READY"],
        "files": [
            {"id": "code_binary", "label": "Code Binary", "required": True},
        ],
    },
    "key_provisioning_ui": {
        "UART": {
            "provision_button_label": "Provision Keys",
            "task_key": "uart_keyprov",
            "stream": False,
            "requires_reset_before": True,
            "advanced_fields": [],
            "main_fields": [
                {"id": "firmware",    "label": "Firmware Image", "widget_type": "file_browse", "required": True,  "param_key": "firmware"},
                {"id": "certificate", "label": "Certificate",    "widget_type": "file_browse", "required": True,  "param_key": "certificate"},
            ],
        },
    },
    "code_provisioning_ui": {
        "UART": {
            "provision_button_label": "Provision Code",
            "task_key": "uart_codeprov",
            "stream": False,
            "requires_reset_before": True,
            "advanced_fields": [],
            "main_fields": [
                {"id": "code_binary", "label": "Code Binary", "widget_type": "file_browse", "required": True, "param_key": "code_binary"},
            ],
        },
    },
}


def get_key_options_for_device(device_name: str) -> list:
    """Return the list of key option specs for the given device name."""
    name = device_name.lower() if device_name else ""
    if name == "f29h85x":
        try:
            config = DeviceRegistry.get_device_config("f29h85x", "hsfs")
            return config.get("key_options", [])
        except Exception:
            return _f29_data.get("key_options", [])
    return STANDARD_KEY_OPTIONS


def get_boot_mode_specs_for_device(device_name: str) -> list:
    """Return the list of boot mode spec objects for the given device name."""
    name = device_name.lower() if device_name else ""
    if name == "f29h85x":
        try:
            config = DeviceRegistry.get_device_config("f29h85x", "hsfs")
            return config.get("boot_modes", [])
        except Exception:
            return _f29_data.get("boot_modes", [])
    return STANDARD_DEVICE_CONFIG.get("boot_modes", [])


def get_boot_modes_for_device(device_name: str) -> list:
    """Return the list of boot mode IDs for the given device name."""
    return [s["id"] for s in get_boot_mode_specs_for_device(device_name)]


def get_advanced_tabs_for_device(device_name: str) -> list:
    """Return the list of advanced tab specs for the given device name."""
    name = device_name.lower() if device_name else ""
    if name == "f29h85x":
        try:
            config = DeviceRegistry.get_device_config("f29h85x", "hsfs")
            return config.get("advanced_tabs", [])
        except Exception:
            return _f29_data.get("advanced_tabs", [])
    return STANDARD_DEVICE_CONFIG.get("advanced_tabs", [])


def get_binary_signing_for_device(device_name: str) -> bool:
    """Return whether binary signing is supported for the given device name."""
    name = device_name.lower() if device_name else ""
    if name == "f29h85x":
        try:
            config = DeviceRegistry.get_device_config("f29h85x", "hsfs")
            return config.get("binary_signing", False)
        except Exception:
            return _f29_data.get("binary_signing", False)
    return STANDARD_DEVICE_CONFIG.get("binary_signing", False)


def get_provisioning_spec_for_device(device_name: str) -> dict:
    """Return full provisioning spec for the given device name.

    Returns a dict with keys:
        provisioning_type, device_states, device_state_labels,
        initial_state, key_provisioning, code_provisioning
    """
    name = device_name.lower() if device_name else ""
    if name == "f29h85x":
        try:
            config = DeviceRegistry.get_device_config("f29h85x", "hsfs")
        except Exception:
            config = _f29_data
        return {
            "provisioning_type":   config.get("provisioning_type",   "f29"),
            "device_states":       config.get("device_states",       ["HSFS", "HSKP", "HSSE"]),
            "device_state_labels": config.get("device_state_labels", {}),
            "initial_state":       config.get("initial_state",       "HSFS"),
            "key_provisioning":    config.get("key_provisioning",    {}),
            "code_provisioning":   config.get("code_provisioning",   {}),
        }
    return {
        "provisioning_type":   STANDARD_DEVICE_CONFIG.get("provisioning_type",   "standard"),
        "device_states":       STANDARD_DEVICE_CONFIG.get("device_states",       ["READY", "PROVISIONED"]),
        "device_state_labels": STANDARD_DEVICE_CONFIG.get("device_state_labels", {}),
        "initial_state":       STANDARD_DEVICE_CONFIG.get("initial_state",       "READY"),
        "key_provisioning":    STANDARD_DEVICE_CONFIG.get("key_provisioning",    {}),
        "code_provisioning":   STANDARD_DEVICE_CONFIG.get("code_provisioning",   {}),
    }


def get_cert_fields_for_device(device_name: str):
    """Return (cert_fields, cert_flags) for the given device name.

    For f29h85x, reads from the registry config.
    For all other devices, returns STANDARD_CERT_FIELDS with no always-on flags.
    """
    name = device_name.lower() if device_name else ""
    if name == "f29h85x":
        # Try to get from registry (hsfs variant as canonical source)
        try:
            config = DeviceRegistry.get_device_config("f29h85x", "hsfs")
            return config.get('cert_fields', F29H85X_CERT_FIELDS), config.get('cert_flags', F29H85X_CERT_FLAGS)
        except Exception:
            return F29H85X_CERT_FIELDS, F29H85X_CERT_FLAGS
    return STANDARD_CERT_FIELDS, []


def get_device_list():
    """Get list of all registered devices with their variants."""
    devices = []
    for device_name in DeviceRegistry.get_supported_devices():
        for variant in DeviceRegistry.get_supported_variants(device_name):
            config = DeviceRegistry.get_device_config(device_name, variant)
            display_name = config.get('display_name', f"{device_name.upper()} {variant.upper()}")
            devices.append({
                'device_name': device_name,
                'variant': variant,
                'display_name': display_name,
                'description': config.get('description', '')
            })
    return devices

def get_device_display_name(device_name, variant):
    """Get the display name for a device and variant."""
    config = DeviceRegistry.get_device_config(device_name, variant)
    return config.get('display_name', f"{device_name.upper()} {variant.upper()}")


def get_target_config_prefix_for_device(device_name: str) -> str:
    """Return the filename prefix used when auto-detecting target config files for a device."""
    name = device_name.lower() if device_name else ""
    if name == "f29h85x":
        try:
            config = DeviceRegistry.get_device_config("f29h85x", "hsfs")
            return config.get("target_config_prefix", "f29")
        except Exception:
            return _f29_data.get("target_config_prefix", "f29")
    return name


def get_target_config_dest_for_device(device_name: str) -> str:
    """Return the relative destination path for the target config file (relative to project root)."""
    name = device_name.lower() if device_name else ""
    if name == "f29h85x":
        try:
            config = DeviceRegistry.get_device_config("f29h85x", "hsfs")
            return config.get("target_config_dest", "")
        except Exception:
            return _f29_data.get("target_config_dest", "")
    return ""


def get_tifek_subpath_for_device(device_name: str) -> str:
    """Return the subdirectory path (relative to the tifek/ root) for a device's FEK public key."""
    name = device_name.lower() if device_name else ""
    if name == "f29h85x":
        try:
            config = DeviceRegistry.get_device_config("f29h85x", "hsfs")
            return config.get("tifek_subpath", name)
        except Exception:
            return _f29_data.get("tifek_subpath", name)
    return name


def get_task_fn_for_device(device_name: str, task_key: str):
    """Return the normalised task callable for (device, task_key), or None."""
    name = device_name.lower() if device_name else ""
    if name == "f29h85x":
        from apps.qtgui.devices.f29h85x.tasks import TASK_SPECS
        return TASK_SPECS.get(task_key)
    return None


def get_detect_spec_for_device(device_name: str, boot_mode_id: str) -> dict:
    """Return detect spec dict with keys 'fn' and 'requires_reset', or {}."""
    name = device_name.lower() if device_name else ""
    if name == "f29h85x":
        from apps.qtgui.devices.f29h85x.tasks import DETECT_SPECS
        return DETECT_SPECS.get(boot_mode_id, {})
    return {}


def get_provisioning_ui_for_device(device_name: str, prov_type: str, boot_mode: str) -> dict:
    """Return the UI mode spec for a given device, provisioning type, and boot mode.

    prov_type: "key" or "code"
    boot_mode: "UART" or "JTAG"
    Returns a dict with keys: advanced_fields, main_fields, provision_button_label,
    task_key, stream, requires_reset_before.  Returns {} if not found.
    """
    name = device_name.lower() if device_name else ""
    ui_key = f"{prov_type}_provisioning_ui"
    if name == "f29h85x":
        try:
            config = DeviceRegistry.get_device_config("f29h85x", "hsfs")
            return config.get(ui_key, {}).get(boot_mode, {})
        except Exception:
            raw = _f29_data.get(f"{prov_type}_provisioning", {})
            return _build_provisioning_ui(raw).get(boot_mode, {})
    return STANDARD_DEVICE_CONFIG.get(ui_key, {}).get(boot_mode, {})

