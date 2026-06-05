#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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
This is the main entry point of the commandline application. Each of
the sub-commands are implemented in their own individual modules.
"""
import argparse
import traceback
import sys

# from tisecprov import __version__
from apps.spt.genkeys import generate_keys, f29_genkeys_args, export_keys_into_current_session
from tisecprov.crypto_interfaces import resolve_signing_algorithm
from apps.spt.parseSoCId import parseSoCId_args, invoke_parseSoCID, getSoCId_args, getSoCId
from apps.tifs.socidparser.mcup_uart_boot_socid import parse_mcu_soc_info
import binascii
from tisecprov.session import SecureSession
from tisecprov.crypto import ManufacturerKeys
from apps.spt.gencert import f29_gencert_args, generate_certificate_from_args
from apps.spt.f29_devel_keys.load_development_keys import load_develop_keys
from apps.tifs.kp_cp_f29h85x.jtag_provisioning import run_key_provisioning_jtag, parseKeyProvisioningJTAG 
from apps.tifs.kp_cp_f29h85x.jtag_provisioning import run_code_provisioning_jtag, parseCodeProvisioningJTAG
from apps.tifs.kp_cp_f29h85x.jtag_provisioning import parsegetDeviceTypeJTAG, run_get_device_type_jtag
from apps.tifs.kp_cp_f29h85x.uart_provisioning import run_key_provisioning_uart, parseKeyProvisioningUART
from apps.tifs.kp_cp_f29h85x.uart_provisioning import parseCodeProvisioningUART, run_code_provisioning_uart
from apps.tifs.kp_cp_f29h85x.uart_provisioning import parsegetDeviceTypeUART, run_get_device_type_uart
from apps.tifs.sign_encrypt_f29.sign_encrypt import sign_encrypt, parseSignEncrypt, parseSecCfgCert, sign_sec_cfg
from apps.spt.encrypt import encrypt_args, encrypt_binary_command
from apps.tifs.rot_cert_scripts.rot_switch_cert_gen import parseRoTCert, gen_rot_cert
from apps.tifs.debug_cert_scripts.debug_image_gen import parseDebugAuthCert, gen_debug_auth_cert
from apps.tifs.f29_device_recovery.debug_recovery_cert_gen import parseDeviceRecoveryCert, gen_device_recovery_cert
from apps.tifs.f29_device_recovery.device_recovery_flow import parseEnableDeviceRecovery, enable_device_recovery
from apps.tifs.f29_device_recovery.device_recovery_flow import parseGetUIDSecap, run_get_device_uid_secap
from apps.tifs.f29_device_recovery.device_recovery_flow import parseValidateDeviceRecoveryCert, send_device_recovery_cert

def create_development_session(key_type_smpk: str = "rsa4k",key_type_bmpk: str = "rsa4k"):

    session = "Development"
    password = "develop123#"

    with SecureSession() as s:
        if s.does_session_exist(session):
            s.delete_session(session)
        print(f"Creating Development Session")
        _session_id = s.create_session(session, "This is a test session", password)
        try:
            _current_session = s.open_session(session, password)

            dev_keys = load_develop_keys(key_type_smpk,key_type_bmpk)

            algo_smpk = resolve_signing_algorithm(key_type_smpk)
            algo_bmpk = resolve_signing_algorithm(key_type_bmpk)

            smkeys = ManufacturerKeys(
                        symmetric_key=dev_keys[0],
                        private_key= dev_keys[1],
                        asymmetric_algorithm=algo_smpk
                    )
            bmkeys = ManufacturerKeys(
                        symmetric_key=dev_keys[2],
                        private_key= dev_keys[3],
                        asymmetric_algorithm=algo_bmpk
                    )
        except Exception as e:
            raise RuntimeError(
                f"An error occurred during session initialization: {e}"
            ) from e

        export_keys_into_current_session(s, [smkeys, bmkeys])

        # Store the development AES key in the session
        s._add_key("aes_key", dev_keys[4])

        # save the current session with the new keys
        print("Saving Development session...")
        s.save_session()

def list_ports(subparsers):
    """List available serial ports"""
    list_parser = subparsers.add_parser(
        "list-ports", help="List available serial ports"
    )
    list_parser.add_argument(
        "--regexp-filter", help="Regular expression filter to apply to port names"
    )


def f29_main():
    """
    The main commandline application that implements a series of sub-commands
    for each of its functionality like key generation, certificate generation,
    downloading code etc.
    """
    print("-----------------------------------------------")
    print("F29H85x CyberShield Toolkit CLI")
    print("-----------------------------------------------")

    f29_parser = argparse.ArgumentParser(description="F29H85x Parser")
    f29_parser.add_argument("-d","--device", metavar="", help="Device Type TIFS")
    f29_parser.add_argument("-s","--session", action="store", default= "Development", help="Development Session")
    f29_parser.add_argument("-p","--password", action="store", default= "develop123#", help="Development Session Password")
    f29_parser.add_argument("--smpk_signing_algorithm", action="store", default="rsa4k", help="Default SMPK Key Type", type=str)
    f29_parser.add_argument("--bmpk_signing_algorithm", action="store", default="rsa4k", help="Default BMPK Key Type", type=str)

    subparsers = f29_parser.add_subparsers(title="commands", description="valid commands", dest="command")
    parseSoCId_args(subparsers)
    f29_genkeys_args(subparsers)
    f29_gencert_args(subparsers)
    getSoCId_args(subparsers)
    parseKeyProvisioningJTAG(subparsers)
    parseCodeProvisioningJTAG(subparsers)
    parsegetDeviceTypeJTAG(subparsers)
    parseKeyProvisioningUART(subparsers)
    parseCodeProvisioningUART(subparsers)
    parsegetDeviceTypeUART(subparsers)
    parseSignEncrypt(subparsers)
    encrypt_args(subparsers)
    parseRoTCert(subparsers)
    parseDebugAuthCert(subparsers)
    parseSecCfgCert(subparsers)
    parseDeviceRecoveryCert(subparsers)
    parseEnableDeviceRecovery(subparsers)
    parseGetUIDSecap(subparsers)
    parseValidateDeviceRecoveryCert(subparsers)
    args = f29_parser.parse_args()

    if args.smpk_signing_algorithm is False:
        args.smpk_signing_algorithm = "rsa4k"
    if args.bmpk_signing_algorithm is False:
        args.bmpk_signing_algorithm = "rsa4k"
    
    if(args.session == "Development" and (args.command == "gencert" or args.command =="signapp" or args.command == "rotcert" or args.command == "signSecCfg" or args.command == "encrypt")):
        create_development_session(args.smpk_signing_algorithm,args.bmpk_signing_algorithm)

    try:
        if args.command == "genkeys" and args.session != "Development":
            generate_keys(
                args.session, args.password, use_hsm=args.hsm,
                smpk_signing_algorithm=args.smpk_signing_algorithm,
                bmpk_signing_algorithm=args.bmpk_signing_algorithm,
            )
            print("Keys generated successfully")

        elif args.command == "getSoCId":
            s = getSoCId(args)
            if s:
                print(f"SoCId: {s}")
                print("SoCId captured successfully")
                parse_mcu_soc_info('f29h85x', binascii.unhexlify(s))
            else:
                raise Exception("No SoCId received. Ensure the device is in UART boot mode and reset after running this command.")

        elif args.command == "gencert":
            generate_certificate_from_args(args)
    
            print("Certificate generated successfully")

        elif args.command == "uart_keyprov":
            run_key_provisioning_uart(
                args.uart_kernel,
                args.certificate,
                args.otp_kw_bin,
                args.device,
                args.port,
                args.targetbaud
            )
        
        elif args.command == "uart_codeprov":
            run_code_provisioning_uart(
                args.uart_kernel,
                args.hsm_image,
                args.hsm_cpu_code,
                args.c29_cpu_code,
                args.seccfg,
                args.device,
                args.port,
                args.targetbaud,
                args.input
            )
        
        elif args.command == "jtag_keyprov":
            success, output = run_key_provisioning_jtag(
                args.otp_kw_bin,
                args.certificate,
                args.jtag_kernel,
                args.ccs_path,
                args.verbose
            )
            if not success:
                print(f"Error: {output}")
                sys.exit(1)
            print(output)

        elif args.command == "jtag_codeprov":
            success, output = run_code_provisioning_jtag(
                args.hsm_image,
                args.jtag_kernel,
                args.ccs_path,
                hsm_cpu_code_path=args.hsm_cpu_code,
                c29_cpu_code_path=args.c29_cpu_code,
                seccfg_path=args.seccfg,
                c29_cpu3_code_path=args.c29_cpu3_code,
                verbose=args.verbose
            )
            if not success:
                print(f"Error: {output}")
                sys.exit(1)
            print(output)

        elif args.command =="devTypeJTAG":
            success,output = run_get_device_type_jtag(
                args.ccs_path,
                args.verbose
                )

        elif args.command =="devTypeUART":
            run_get_device_type_uart(
                args.uart_kernel,
                args.device,
                args.port,
                args.targetbaud
            )

        elif args.command =="signapp":
            sign_encrypt(args)

        elif args.command =="rotcert":
            gen_rot_cert(args)

        elif args.command =="debugcert":
            gen_debug_auth_cert(args)

        elif args.command =="devicerecovery":
            gen_device_recovery_cert(args)

        elif args.command =="endevrecov":
            enable_device_recovery(
                args.ccs_path,
                args.verbose
                )

        elif args.command =="getUIDSecap":
            run_get_device_uid_secap(
                args.ccs_path,
                args.verbose
                )

        elif args.command =="valdcert":
            send_device_recovery_cert(
                args.dev_recov_cert,
                args.ccs_path,
                args.verbose
                )

        elif args.command == "parseSoCId":
            print(
                f"SoC Id parse:"
            )
            invoke_parseSoCID(args)
        
        elif args.command =="signSecCfg":
            sign_sec_cfg(args)

        elif args.command == "encrypt":
            args.device = "f29h85x"
            encrypt_binary_command(args)

        else:
            f29_parser.print_help()
    
    except RuntimeError as e:
        traceback.print_exc()
        print(f"Error: {e}")


if __name__ == "__main__":
    f29_main()
