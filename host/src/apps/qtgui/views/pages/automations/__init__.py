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

"""Automations: path resolution and UI defaults for qtgui pages."""

import os
import re

from apps.qtgui.utils.platform_utils import get_home_directory, get_addon_root
from apps.qtgui.views.pages.automations.f29h85x import (
    resolve_tifek_path,
    resolve_cert_output_dir,
    resolve_target_config_path as _f29_resolve_target_config_path,
    sign_prebuilt_binaries as _f29_sign_prebuilt_binaries,
)

# Registry: device name → callable(session_data, controller) -> tuple[bool, str]
_CONFIG_PAGE_ENTER_REGISTRY: dict = {
    "f29h85x": _f29_sign_prebuilt_binaries,
}

# Registry: device name → field key → callable() -> str
_REGISTRY: dict = {
    "f29h85x": {
        "pub_key_path":    resolve_tifek_path,
        "output_dir_path": resolve_cert_output_dir,
    },
}


def resolve_target_config_path(device: str) -> str | None:
    """Return a matching .ccxml path for the given device."""
    _DEVICES = {
        "f29h85x": _f29_resolve_target_config_path,
    }
    fn = _DEVICES.get(device.lower() if device else "")
    return fn() if fn else None


def is_addon_installed(device: str) -> bool:
    """Return True if ~/ti/TICST/addons/<device>/ directory is present."""
    if not device:
        return True
    return get_addon_root(device.lower()).is_dir()


def apply_cert_defaults(device: str, widgets: dict) -> None:
    """Set widget text for each registered field for the given device."""
    providers = _REGISTRY.get(device.lower(), {})
    for field_key, provider in providers.items():
        if field_key not in widgets:
            continue
        value = provider()
        if value:
            widgets[field_key].setText(value)


def has_config_page_enter_automation(device: str) -> bool:
    """Return True if there is a registered automation AND the addon is installed."""
    key = device.lower() if device else ""
    return key in _CONFIG_PAGE_ENTER_REGISTRY and is_addon_installed(device)


def run_config_page_enter_automation(
    device: str,
    session_data: dict,
    controller,
) -> tuple[bool, str]:
    """Run the config-page-enter automation for the given device.

    Returns (True, "") if no automation is registered or addon is not installed.
    Returns (False, message) on automation failure.
    """
    key = device.lower() if device else ""
    fn = _CONFIG_PAGE_ENTER_REGISTRY.get(key)
    if fn is None or not is_addon_installed(device):
        return True, ""
    return fn(session_data, controller)


def resolve_ccs_path() -> str | None:
    """Scan common locations for the newest CCS installation."""
    home_dir = get_home_directory()

    base_paths = [
        os.path.join(home_dir, "ti"),
        "C:\\ti",
        os.path.join("/opt", "ti"),
        "C:\\Program Files\\Texas Instruments",
    ]

    found_versions = []

    for base_path in base_paths:
        if os.path.exists(base_path):
            try:
                for item in os.listdir(base_path):
                    item_path = os.path.join(base_path, item)
                    if os.path.isdir(item_path) and item.lower().startswith("ccs"):
                        version_match = re.search(r"ccs(\d+)", item.lower())
                        if version_match:
                            version_num = int(version_match.group(1))
                            found_versions.append((version_num, item_path))
                        elif item.lower() == "ccs":
                            found_versions.append((0, item_path))
            except (OSError, PermissionError):
                continue

    if found_versions:
        found_versions.sort(key=lambda x: x[0], reverse=True)
        return found_versions[0][1]

    return None
