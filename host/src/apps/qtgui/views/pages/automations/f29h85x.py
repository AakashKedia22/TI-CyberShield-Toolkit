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

"""f29h85x-specific path resolvers — no Qt dependency."""

import os
import getpass

from apps.qtgui.utils.platform_utils import get_home_directory, get_addon_root


def resolve_tifek_path() -> str | None:
    """Resolve ti_fek_public.pem from the addon directory.

    Returns None if the file does not exist so the field is left empty.
    """
    from apps.qtgui.devices.register import get_tifek_subpath_for_device

    subpath_parts = get_tifek_subpath_for_device("f29h85x").replace("\\", "/").split("/")
    device_name = subpath_parts[0]
    sr_parts    = subpath_parts[1:]
    path = str(get_addon_root(device_name) / "tifek" / os.path.join(*sr_parts) / "ti_fek_public.pem")
    return path if os.path.isfile(path) else None


def resolve_target_config_path() -> str | None:
    """Scan ~/ti/CCSTargetConfigurations for f29-prefixed .ccxml."""
    from apps.qtgui.devices.register import get_target_config_prefix_for_device

    prefix = get_target_config_prefix_for_device("f29h85x")
    if not prefix:
        return None

    home_dir = get_home_directory()
    possible_dirs = [
        os.path.join(home_dir, "ti", "CCSTargetConfigurations"),
        os.path.join("C:\\Users", getpass.getuser(), "ti", "CCSTargetConfigurations"),
    ]

    for directory in possible_dirs:
        if os.path.exists(directory):
            try:
                all_files = os.listdir(directory)
            except OSError:
                continue

            matching_files = [
                os.path.join(directory, f)
                for f in all_files
                if f.lower().startswith(prefix) and f.lower().endswith(".ccxml")
            ]

            if matching_files:
                return matching_files[0]

    return None


def resolve_cert_output_dir() -> str:
    """Return ~/ti/f29h85x/certificates (creates it if missing)."""
    home_dir = get_home_directory()
    output_dir = os.path.join(home_dir, "ti", "f29h85x", "certificates")
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


def sign_prebuilt_binaries(session_data: dict, controller) -> tuple[bool, str]:
    """Sign the project-bundled RAM-based SBL for f29h85x.

    Called by run_config_page_enter_automation() when the addon is installed.
    The HSM CP image (tifs_f29h85x_hs_se_code_provisioning.release.bin) lives in
    the addon and is signed separately via "Sign and Encrypt All Prebuilt Binaries".
    """
    result = controller.sign_f29h85x_specific_binaries(
        session_data.get("key_type"),
        session_data.get("key_data"),
        session_data.get("ccs_path"),
        ["ram_based_uart_sbl.temp.bin"],   # only the project-bundled SBL
    )
    # Guard against the controller's exception path returning None implicitly (pre-existing bug)
    if result is None:
        return False, "Binary signing returned no result (internal error)"
    return result
