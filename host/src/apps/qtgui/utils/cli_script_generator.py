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
Generate a bash shell script equivalent to the GUI wizard provisioning flow.
"""

import os
import stat
from datetime import datetime

from apps.qtgui.utils.platform_utils import IS_WINDOWS


def _posix_path(path: str) -> str:
    """Convert any OS path to forward-slash form for embedding in bash scripts."""
    return path.replace("\\", "/")


_DEVELOPMENT_KEY_TYPES = {"sdk", "f29_development", "development"}


def _heuristic_config(binary_name: str) -> dict:
    """Return a best-guess config for an unknown binary."""
    name_lower = binary_name.lower()
    core = "HSM" if "hsm" in name_lower or "tifs" in name_lower else "C29"
    boot = "RAM" if "ram" in name_lower or "uart" in name_lower else "FLASH"
    loadaddr = "0x00000000" if core == "HSM" else "0x10001000"
    debug = "DBG_SOC_DEFAULT" if core == "HSM" else None
    return {"core": core, "boot": boot, "loadaddr": loadaddr, "debug": debug}


def _auth_lines(key_data: dict, smpk_algo: str, bmpk_algo: str) -> list:
    """
    Return the global auth args lines (with trailing backslashes) to insert
    between '--device f29h85x \\' and the subcommand line.

    Regular session  → --session {name} --password {password}
    Dev session      → --smpk_signing_algorithm {algo} --bmpk_signing_algorithm {algo}
    """
    key_type = key_data.get("type", "")
    if key_type in _DEVELOPMENT_KEY_TYPES:
        return [
            f'    --smpk_signing_algorithm {smpk_algo} \\',
            f'    --bmpk_signing_algorithm {bmpk_algo} \\',
        ]
    return ['    --session "$SESSION_NAME" --password "$SESSION_PASSWORD" \\']


def _session_label(key_data: dict) -> str:
    key_type = key_data.get("type", "")
    if key_type in _DEVELOPMENT_KEY_TYPES:
        return "Development"
    return key_data.get("name", "unknown")


def _reverse_signed_name(signed_path: str) -> str | None:
    """
    Derive the original unsigned .bin filename from a signed output path.

    Naming conventions used by the signing toolchain:
      C29 signed  : {name}.cert.bin       → {name}.bin
      HSM signed  : {name}.hs.hsmimage    → {name}.bin

    Returns None if the filename doesn't match a known convention.
    """
    name = os.path.basename(signed_path)
    if name.endswith(".hs.hsmimage"):
        return name[: -len(".hs.hsmimage")] + ".bin"
    if name.endswith(".cert.bin"):
        return name[: -len(".cert.bin")] + ".bin"
    return None


def _signed_fields_by_boot_mode(prov_data: dict, boot_mode: str) -> dict:
    """Return {field_name: signed_path} for the signed binaries used in codeprov."""
    if boot_mode.upper() == "JTAG":
        return {
            "c29_cpu_code": prov_data.get("c29_cpu_code", ""),
            "hsm_image":    prov_data.get("hsm_image", ""),
            "hsm_cpu_code": prov_data.get("hsm_cpu_code", ""),
        }
    # UART
    return {
        "flash_kernel": prov_data.get("flash_kernel", ""),
    }


def _build_gencert_section(cert_info: dict, auth: list, cli_var: str, device_cli_name: str) -> list:
    lines = [
        'echo "Step 1: Generate OTP Certificate"',
        f'"{cli_var}" --device {device_cli_name} \\',
    ] + auth + [
        '    gencert \\',
        f'    -t "{_posix_path(cert_info["pub_key_path"])}" \\',
        f'    --msv {cert_info["msv"]} \\',
    ]

    flags = cert_info.get("flags", [])
    if flags:
        lines.append(f'    {" ".join("--" + f for f in flags)} \\')

    lines += [
        f'    --sr_sbl {cert_info.get("sr_sbl", "1")} '
        f'--sr_hsmRT {cert_info.get("sr_hsmRT", "1")} '
        f'--sr_app {cert_info.get("sr_app", "1")} '
        f'--sr_ssu {cert_info.get("sr_ssu", "1")} \\',
        f'    --keycnt {cert_info["keycnt"]} --keycnt_protect '
        f'--keyrev {cert_info["keyrev"]} \\',
        f'    -d {device_cli_name} --devSrVer {cert_info.get("dev_sr_ver", "1")} \\',
        f'    --ext_otp {cert_info.get("ext_otp", "0")} '
        f'--ext_otp_indx {cert_info.get("ext_otp_indx", "0")} '
        f'--ext_otp_size {cert_info.get("ext_otp_size", "0")} \\',
        f'    -o "{_posix_path(cert_info["output_dir_path"])}"',
        "",
    ]
    return lines


def _build_signapp_sections(
    prebuilt_dir: str,
    signed_imgs_dir: str,
    auth: list,
    keyrev: str,
    swrv: str,
    cli_var: str,
    known_binary_configs: dict,
    device_cli_name: str,
    start_step: int = 2,
) -> tuple:
    lines = []
    step = start_step

    # Use known_binary_configs as the canonical ordered list so that expected
    # binaries are always included even when they live outside prebuilt_dir.
    # Append any extra .bin files found on disk that aren't in the canonical list.
    if os.path.isdir(prebuilt_dir):
        disk_files = {
            f for f in os.listdir(prebuilt_dir)
            if f.endswith(".bin") and "otp_kw" not in f.lower()
        }
        bin_files = list(known_binary_configs.keys()) + sorted(
            f for f in disk_files if f not in known_binary_configs
        )
    else:
        bin_files = list(known_binary_configs.keys())

    for binary_name in bin_files:
        cfg = known_binary_configs.get(binary_name) or _heuristic_config(binary_name)
        lines.append(f'echo "Step {step}: Sign {binary_name}"')
        cmd = [
            f'"{cli_var}" --device {device_cli_name} \\',
        ] + auth + [
            '    signapp \\',
            f'    --image "{prebuilt_dir}/{binary_name}" \\',
            '    --input-format bin \\',
            f'    --core {cfg["core"]} --boot {cfg["boot"]} \\',
            f'    --keyrev {keyrev} --loadaddr {cfg["loadaddr"]} --swrv {swrv} \\',
        ]
        if cfg["debug"]:
            cmd.append(f'    --debug {cfg["debug"]} \\')
        cmd.append(f'    --output_path "{signed_imgs_dir}"')
        lines += cmd
        lines.append("")
        step += 1

    return lines, step


def _build_custom_binary_todos(
    prov_data: dict,
    prebuilt_dir: str,
    signed_imgs_dir: str,
    auth: list,
    keyrev: str,
    swrv: str,
    boot_mode: str,
    cli_var: str,
    known_binary_configs: dict,
    device_cli_name: str,
) -> list:
    """
    For each signed binary referenced in provisioning_data, check whether its
    source .bin can be found in prebuilt_dir.  If not — the binary was custom
    (signed from outside the prebuilt tree) — emit a commented-out TODO signapp
    block so the user knows exactly what to fill in.

    The source metadata stored under provisioning_data['signed_binaries'] by
    the wizard (if present) is used first; the naming-convention reversal
    (_reverse_signed_name) is used as a fallback.
    """
    lines = []
    signed_meta = prov_data.get("signed_binaries", {})  # {field: {source, core, boot, loadaddr, debug}}
    signed_fields = _signed_fields_by_boot_mode(prov_data, boot_mode)

    # Set of source binary names already covered by the prebuilt scan
    covered = set()
    if os.path.isdir(prebuilt_dir):
        covered = {
            f for f in os.listdir(prebuilt_dir)
            if f.endswith(".bin") and "otp_kw" not in f.lower()
        }
    else:
        covered = set(known_binary_configs.keys())

    found_any = False
    for field, signed_path in signed_fields.items():
        if not signed_path:
            continue

        # Use wizard-supplied metadata if available
        meta = signed_meta.get(field)
        if meta:
            source_path = meta.get("source", "")
            source_name = os.path.basename(source_path)
        else:
            source_name = _reverse_signed_name(signed_path)
            source_path = None  # unknown

        if source_name is None:
            # Can't determine source from filename convention
            source_name = "UNKNOWN_SOURCE.bin"
            source_path = None

        # If the source name is already covered by the prebuilt scan, skip
        if source_name in covered:
            continue

        # ── Custom binary detected ────────────────────────────────────────
        if not found_any:
            lines += [
                "# ── Custom Binaries ─────────────────────────────────────────────",
                "# The following binaries were not found in the standard prebuilt",
                "# directory. Edit the --image path and signing parameters below.",
                "",
            ]
            found_any = True

        cfg = (
            {k: meta[k] for k in ("core", "boot", "loadaddr", "debug") if k in meta}
            if meta else _heuristic_config(source_name)
        )
        image_arg = _posix_path(source_path) if source_path else f"/path/to/{source_name}"

        commented_cmd = [
            f'# TODO [{field}]: sign custom binary → {os.path.basename(signed_path)}',
            f'# "{cli_var}" --device {device_cli_name} \\',
        ] + [f'# {line}' for line in auth] + [
            '#     signapp \\',
            f'#     --image "{image_arg}" \\',
            '#     --input-format bin \\',
            f'#     --core {cfg["core"]} --boot {cfg["boot"]} \\',
            f'#     --keyrev {keyrev} --loadaddr {cfg["loadaddr"]} --swrv {swrv}',
        ]
        if cfg.get("debug"):
            commented_cmd[-1] += " \\"
            commented_cmd.append(f'#     --debug {cfg["debug"]}')
        commented_cmd += [
            f'#     --output_path "{_posix_path(os.path.dirname(signed_path)) or signed_imgs_dir}"',
            "",
        ]
        lines += commented_cmd

    return lines


def _build_signseccfg_section(
    prebuilt_dir: str,
    signed_imgs_dir: str,
    auth: list,
    keyrev: str,
    swrv: str,
    ccs_path: str,
    step: int,
    cli_var: str,
    device_cli_name: str,
) -> list:
    seccfg_image = _posix_path(os.path.join(prebuilt_dir, "default_seccfg_bankmode_0_ssumode1.out"))
    lines = [
        f'echo "Step {step}: Sign Security Configuration"',
        f'"{cli_var}" --device {device_cli_name} \\',
    ] + auth + [
        '    signSecCfg \\',
        f'    --image "{seccfg_image}" \\',
        f'    --keyrev {keyrev} --swrv {swrv} --boot FLASH \\',
        f'    --ccs-path "{_posix_path(ccs_path)}" \\',
        f'    --output_path "{signed_imgs_dir}"',
        "",
    ]
    return lines


def _build_keyprov_section(kp_data: dict, step: int, cli_var: str, signed_imgs_dir: str, device_cli_name: str) -> list:
    conn_info = kp_data.get("connection_info", {})
    boot_mode = kp_data.get("boot_mode", "JTAG").upper()

    # Determine the signed kernel path
    unsigned_kernel = kp_data.get("flash_kernel", "")
    if unsigned_kernel:
        signed_kernel = _posix_path(os.path.join(signed_imgs_dir, os.path.basename(unsigned_kernel) + ".cert.bin"))
    else:
        signed_kernel = "<signed_kernel_path>"

    if boot_mode == "UART":
        lines = [
            f'echo "Step {step}: UART Key Provisioning"',
            f'"{cli_var}" --device {device_cli_name} \\',
            '    uart_keyprov \\',
            f'    --uart-kernel "{signed_kernel}" \\',
            f'    --otp-kw-bin "{_posix_path(kp_data.get("otp_keywriter", "<otp_keywriter_path>"))}" \\',
            f'    --certificate "{_posix_path(kp_data.get("certificate", "<certificate_path>"))}" \\',
            f'    --port "{conn_info.get("port", "/dev/ttyACM0")}" \\',
            '    --targetbaud 115200',
        ]
    else:  # JTAG
        ccs_path = _posix_path(conn_info.get("ccs_path", "<ccs_path>"))
        lines = [
            f'echo "Step {step}: JTAG Key Provisioning"',
            f'"{cli_var}" --device {device_cli_name} \\',
            '    jtag_keyprov \\',
            f'    --ccs-path "{ccs_path}" \\',
            f'    --otp-kw-bin "{_posix_path(kp_data.get("otp_keywriter", "<otp_keywriter_path>"))}" \\',
            f'    --certificate "{_posix_path(kp_data.get("certificate", "<certificate_path>"))}" \\',
            f'    --jtag-kernel "{signed_kernel}"',
        ]
        if conn_info.get("verbose"):
            lines[-1] += " \\"
            lines.append("    --verbose")

    lines.append("")
    return lines


def _infer_jtag_cp_data(signed_imgs_dir: str, prebuilt_dir: str) -> dict:
    """
    Build a best-effort cp_data dict using expected output filenames when the
    wizard did not populate cp_data (provisioning_page limitation).
    """
    return {
        "hsm_image":    os.path.join(signed_imgs_dir, "tifs_f29h85x_hs_se_code_provisioning.release.hs.hsmimage"),
        "jtag_kernel":  os.path.join(prebuilt_dir,    "secure_ram_based_jtag_kernel.out"),
        "hsm_cpu_code": os.path.join(signed_imgs_dir, "tifs_f29h85x_hs_se.release.hs.hsmimage"),
        "c29_cpu_code": os.path.join(signed_imgs_dir, "secure_boot_manager.cert.bin"),
        "c29_cpu3_code": os.path.join(signed_imgs_dir, "combined_services_demo.cert.bin"),
        "seccfg":       os.path.join(signed_imgs_dir, "seccfg.bin"),
        "connection_info": {},
    }


def _build_codeprov_section(
    prov_data: dict,
    ccs_path: str,
    step: int,
    boot_mode: str,
    cli_var: str,
    device_cli_name: str,
) -> list:
    conn_info = prov_data.get("connection_info", {})

    if boot_mode.upper() == "UART":
        lines = [
            f'echo "Step {step}: UART Code Provisioning"',
            f'"{cli_var}" --device {device_cli_name} \\',
            '    uart_codeprov \\',
            f'    --flash-kernel "{_posix_path(prov_data.get("uart_kernel", "<flash_kernel_path>"))}" \\',
            f'    --otp-keywriter "{_posix_path(prov_data.get("otp_keywriter", "<otp_keywriter_path>"))}" \\',
            f'    --certificate "{_posix_path(prov_data.get("certificate", "<certificate_path>"))}" \\',
            f'    --port "{conn_info.get("port", "/dev/ttyACM0")}"',
        ]
    else:
        lines = [
            f'echo "Step {step}: JTAG Code Provisioning"',
            f'"{cli_var}" --device {device_cli_name} \\',
            '    jtag_codeprov \\',
            f'    --ccs-path "{_posix_path(ccs_path)}" \\',
            f'    --hsm-image "{_posix_path(prov_data.get("hsm_image", "<hsm_image_path>"))}" \\',
            f'    --jtag-kernel "{_posix_path(prov_data.get("jtag_kernel", "<jtag_kernel_path>"))}" \\',
            f'    --hsm-cpu-code "{_posix_path(prov_data.get("hsm_cpu_code", "<hsm_cpu_code_path>"))}" \\',
            f'    --c29-cpu-code "{_posix_path(prov_data.get("c29_cpu_code", "<c29_cpu_code_path>"))}" \\',
            f'    --c29-cpu3-code "{_posix_path(prov_data.get("c29_cpu3_code", "<c29_cpu3_code_path>"))}" \\',
            f'    --seccfg "{_posix_path(prov_data.get("seccfg", "<seccfg_path>"))}"',
        ]

    if conn_info.get("verbose"):
        lines[-1] += " \\"
        lines.append("    --verbose")

    lines.append("")
    return lines


def generate_f29h85x_cli_script(
    wizard_data: dict,
    cli_binary: str = "TI_CST_CLI",
    known_binary_configs: dict | None = None,
) -> str:
    """
    Generate a bash script that replays the wizard provisioning flow.

    Parameters
    ----------
    wizard_data : dict
        The ``session_data`` dict collected by WizardView.
    cli_binary : str
        Fallback CLI name when ``$1`` is not supplied at run-time.
    known_binary_configs : dict, optional
        Mapping of binary filename → signing params (core/boot/loadaddr/debug).
        Defaults to ``PREBUILT_BINARY_CONFIGS`` from ``F29H85xDeviceModel``.

    Returns
    -------
    str
        Absolute path to the saved shell script.
    """
    if known_binary_configs is None:
        from apps.qtgui.models.F29H85xDeviceModel import PREBUILT_BINARY_CONFIGS
        known_binary_configs = PREBUILT_BINARY_CONFIGS
    cert_info = wizard_data.get("certificate_info")
    if cert_info is None:
        raise ValueError("certificate_info is missing — gencert step was not completed")
    ccs_path = wizard_data.get("ccs_path", "")

    # ── Detect which flows were run ──────────────────────────────────────────
    kp_data = wizard_data.get("kp_data")   # set iff KP was run in this session
    cp_data = wizard_data.get("cp_data")   # set iff CP was run in this session

    # Backward compat: old session_data only has 'provisioning_data'
    if kp_data is None and cp_data is None:
        legacy = wizard_data.get("provisioning_data") or {}
        prov_type = legacy.get("type", "")
        if "kp" in prov_type or "keyprov" in prov_type:
            kp_data = legacy
        else:
            cp_data = legacy

    # ── Determine primary data source for shared paths ───────────────────────
    prov_data = cp_data or kp_data or {}

    boot_mode = (
        wizard_data.get("boot_mode")
        or prov_data.get("boot_mode", "JTAG")
    )

    key_data = wizard_data.get("key_data", {})
    smpk_algo = (
        cert_info.get("smpk_signing_algorithm")
        or key_data.get("smpk_algo")
        or "rsa4k"
    )
    bmpk_algo = (
        cert_info.get("bmpk_signing_algorithm")
        or key_data.get("bmpk_algo")
        or smpk_algo
    )

    auth = _auth_lines(key_data, smpk_algo, bmpk_algo)
    keyrev = str(cert_info["keyrev"])
    swrv = str(cert_info.get("sr_sbl", "1"))

    if boot_mode.upper() == "UART":
        if cp_data:
            prebuilt_dir    = os.path.dirname(cp_data.get("uart_kernel", ""))
            signed_imgs_dir = os.path.dirname(cp_data.get("hsm_image", ""))
        else:  # KP only (or cert-only — kp_data may be None)
            prebuilt_dir    = os.path.dirname((kp_data or {}).get("flash_kernel", ""))
            signed_imgs_dir = prebuilt_dir
    else:  # JTAG
        if cp_data:
            prebuilt_dir    = os.path.dirname(cp_data.get("jtag_kernel", ""))
            signed_imgs_dir = os.path.dirname(cp_data.get("hsm_image", ""))
        else:  # KP only (or cert-only — kp_data may be None)
            prebuilt_dir    = os.path.dirname((kp_data or {}).get("flash_kernel", ""))
            signed_imgs_dir = prebuilt_dir

    # ── Fallback: derive paths from device model when wizard data has no paths ─
    if not prebuilt_dir or not signed_imgs_dir:
        from apps.qtgui.models.F29H85xDeviceModel import get_device_prebuilt_dir
        from common.device_utils import get_device_output_dir
        device_name = wizard_data.get("device", "f29h85x").lower()
        if not prebuilt_dir:
            prebuilt_dir = str(get_device_prebuilt_dir(device_name))
        if not signed_imgs_dir:
            signed_imgs_dir = get_device_output_dir(device_name, "signedImages", create=False)

    prebuilt_dir    = _posix_path(prebuilt_dir)
    signed_imgs_dir = _posix_path(signed_imgs_dir)
    ccs_path        = _posix_path(ccs_path)

    cli_var = "$CLI"
    device_cli_name = wizard_data.get("device", "f29h85x").lower()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    session_label = _session_label(key_data)

    is_dev_session = key_data.get("type", "") in _DEVELOPMENT_KEY_TYPES

    # ── Header ──────────────────────────────────────────────────────────────
    script_lines = [
        "#!/bin/bash",
        "# TI F29H85x Provisioning Script",
        f"# Generated by TI Cybershield Toolkit Wizard — {timestamp}",
        f"# Device: F29H85X | Boot Mode: {boot_mode.upper()} | Session: {session_label}",
        "# Windows users: run this script with Git Bash or WSL",
        f"CLI=\"${{1:-{cli_binary}}}\"  # Pass path as $1 or ensure {cli_binary} is on PATH",
    ]
    if not is_dev_session:
        script_lines += [
            'SESSION_NAME="${2:?Error: SESSION_NAME required as $2}"',
            'SESSION_PASSWORD="${3:?Error: SESSION_PASSWORD required as $3}"',
        ]
    script_lines += ["set -e", ""]

    # ── Step 1: gencert ──────────────────────────────────────────────────────
    script_lines += _build_gencert_section(cert_info, auth, cli_var, device_cli_name)
    next_step = 2

    # ── Steps 2..N: signapp (standard prebuilt binaries) ────────────────────
    signapp_lines, next_step = _build_signapp_sections(
        prebuilt_dir, signed_imgs_dir, auth, keyrev, swrv, cli_var,
        known_binary_configs, device_cli_name,
        start_step=next_step,
    )
    script_lines += signapp_lines

    # ── TODO blocks for custom binaries not in prebuilt_dir ─────────────────
    script_lines += _build_custom_binary_todos(
        prov_data, prebuilt_dir, signed_imgs_dir,
        auth, keyrev, swrv, boot_mode, cli_var,
        known_binary_configs, device_cli_name,
    )

    # ── Step N+1: signSecCfg ─────────────────────────────────────────────────
    script_lines += _build_signseccfg_section(
        prebuilt_dir, signed_imgs_dir, auth,
        keyrev, swrv, ccs_path, next_step, cli_var, device_cli_name,
    )
    next_step += 1

    # ── Step N+2 (optional): keyprov ─────────────────────────────────────────
    if kp_data:
        script_lines += _build_keyprov_section(kp_data, next_step, cli_var, signed_imgs_dir, device_cli_name)
        next_step += 1

    # ── Step N+3 (optional): codeprov ────────────────────────────────────────
    # Use explicit cp_data if available; fall back to inferred paths for JTAG.
    # Normalize empty dict (from legacy backward-compat path) to None so the
    # JTAG inference branch is reached when no real cp_data was captured.
    effective_cp = cp_data if cp_data else None
    if effective_cp is None and boot_mode.upper() == "JTAG":
        effective_cp = _infer_jtag_cp_data(signed_imgs_dir, prebuilt_dir)
    if effective_cp:
        script_lines += _build_codeprov_section(effective_cp, ccs_path, next_step, boot_mode, cli_var, device_cli_name)

    script_content = "\n".join(script_lines)

    # Save one level above the certificate output directory so that the
    # gencert step (which wipes cert_info["output_dir_path"] via shutil.rmtree)
    # does not delete the script on a re-run.
    output_path = os.path.join(
        os.path.dirname(cert_info["output_dir_path"]), "provision_f29h85x.sh"
    )
    with open(output_path, "w", newline="\n") as fh:
        fh.write(script_content)

    if not IS_WINDOWS:
        os.chmod(output_path, os.stat(output_path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return output_path
