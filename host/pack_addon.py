#!/usr/bin/env python3
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
Generic addon packaging script.

Creates a zip archive from host/addons/<device>/ that can be distributed
out-of-band and installed via host/install_addon.py.

Usage:
    python pack_addon.py --device <device> [--version <ver>] [--out <dir>]

Supported devices:
    f29h85x, am261x, am263x, am263px, am273x
"""

import argparse
import pathlib
import sys
import zipfile

# Per-device list of files that must be present before packing.
# Keys match the addon source directory name under host/addons/.
DEVICE_CONFIGS: dict[str, list[str]] = {
    "f29h85x": [
        "bin/otp_kw_f29h85x_hs_fs.hsmimage.bin",
        "bin/tifs_f29h85x_hs_se.release.bin",
        "bin/tifs_f29h85x_hs_se_code_provisioning.release.bin",
        "bin/combined_services_demo.bin",
        "bin/secure_boot_manager.bin",
        "bin/default_seccfg_bankmode_0_ssumode1.out",
        "tifek/SR_20/ti_fek_public.pem",
    ],
    "am261x":  ["tifek/SR_10/ti_fek_public.pem"],
    "am263x":  ["tifek/SR_11/ti_fek_public.pem"],
    "am263px": ["tifek/SR_10/ti_fek_public.pem"],
    "am273x":  ["tifek/SR_10/ti_fek_public.pem",
                 "tifek/SR_11_12/ti_fek_public.pem"],
}


def main():
    parser = argparse.ArgumentParser(
        description="Pack a device addon into a distributable zip."
    )
    parser.add_argument(
        "--device",
        required=True,
        metavar="DEVICE",
        choices=sorted(DEVICE_CONFIGS),
        help=f"Target device ({', '.join(sorted(DEVICE_CONFIGS))})",
    )
    parser.add_argument(
        "--version",
        metavar="VER",
        help="Version string appended to zip name (e.g. 1.0.0)",
    )
    parser.add_argument(
        "--out",
        metavar="DIR",
        help="Output directory for the zip (default: same dir as script)",
    )
    args = parser.parse_args()

    script_dir = pathlib.Path(__file__).resolve().parent
    src_dir = script_dir / "addons" / args.device

    if not src_dir.is_dir():
        print(f"Error: addon source directory not found: {src_dir}")
        sys.exit(1)

    # Verify all expected files are present before packing
    expected = DEVICE_CONFIGS[args.device]
    missing = [f for f in expected if not (src_dir / f).is_file()]
    if missing:
        print(f"Error: {len(missing)} expected file(s) missing from {src_dir}:")
        for f in missing:
            print(f"  {f}")
        sys.exit(1)

    # Determine output zip name and path
    zip_name = f"{args.device}_addon"
    if args.version:
        zip_name += f"_{args.version}"
    zip_name += ".zip"

    out_dir = pathlib.Path(args.out).resolve() if args.out else script_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = out_dir / zip_name

    # Build zip preserving relative structure under addons/<device>/
    packed = []
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for item in sorted(src_dir.rglob("*")):
            if item.is_file():
                rel = item.relative_to(src_dir)
                zf.write(item, rel)
                packed.append(rel)

    total_bytes = zip_path.stat().st_size
    print(f"Created: {zip_path}")
    print(f"Files:   {len(packed)}")
    print(f"Size:    {total_bytes:,} bytes")


if __name__ == "__main__":
    main()
