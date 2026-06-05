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

import sys
import os
import glob
import getpass
from pathlib import Path
from apps.spt.f29_spt import f29_main
from apps.tifs.kp_cp_f29h85x.jtag_provisioning import run_key_provisioning_jtag, run_code_provisioning_jtag
from apps.tifs.sign_encrypt_f29.sign_encrypt import sign_encrypt, sign_sec_cfg
from common.platform_utils import get_prebuilt_images_dir


# Ordered signing specs for batch signing of prebuilt F29H85x binaries.
# Each entry defines one image to sign via _on_sign_all_binaries() in config_page.py.
PREBUILT_SIGNING_SPECS = [
    {
        "id": "hsm_cpu",
        "label": "HSM CPU Image",
        "filename_template": "tifs_{device_name}_hs_se.release.bin",
        "sign_type": "binary",
        "sign_config": {
            "input_format": "BIN",
            "core": "HSM",
            "boot": "FLASH",
            "loadaddr": "0x00000000",
            "keyrev": "1",
            "swrv": "1",
            "debug": "DBG_SOC_DEFAULT",
            "fw_enc": True,
        },
    },
    {
        "id": "hsm_cp_image",
        "label": "HSM Code Provisioning Image",
        "filename": "tifs_f29h85x_hs_se_code_provisioning.release.bin",
        "sign_type": "binary",
        "sign_config": {
            "input_format": "BIN",
            "core": "HSM",
            "boot": "RAM",
            "loadaddr": "0x00000000",
            "keyrev": "1",
            "swrv": "1",
            "debug": "DBG_SOC_DEFAULT",
            "tifs_enc": True,
        },
    },
    {
        "id": "secure_boot_manager",
        "label": "Secure Boot Manager",
        "filename": "secure_boot_manager.bin",
        "sign_type": "binary",
        "sign_config": {
            "input_format": "BIN",
            "core": "C29",
            "boot": "FLASH",
            "loadaddr": "0x10001000",
            "keyrev": "1",
            "swrv": "1",
            "fw_enc": True,
        },
    },
    {
        "id": "combined_services_demo",
        "label": "Combined Services Demo",
        "filename": "combined_services_demo.bin",
        "sign_type": "binary",
        "sign_config": {
            "input_format": "BIN",
            "core": "C29",
            "boot": "FLASH",
            "loadaddr": "0x10040000",
            "keyrev": "1",
            "swrv": "1",
            "fw_enc": True,
            "fw_type": "CPU1_APP",
        },
    },
    {
        "id": "seccfg",
        "label": "Security Configuration",
        "filename": "default_seccfg_bankmode_0_ssumode1.out",
        "sign_type": "seccfg",
        "sign_config": {
            "swrv": "1",
            "keyrev": "1",
            "boot": "FLASH",
        },
    },
]

# Static signing parameters for known F29H85x prebuilt binaries.
# Dynamic fields (keyrev, swrv) are populated at call time by sign_all_prebuilt_binaries().
PREBUILT_BINARY_CONFIGS = {
    "csd.bin":                         {"core": "C29",  "boot": "FLASH", "loadaddr": "0x10001000", "debug": None},
    "combined_services_demo.bin":      {"core": "C29",  "boot": "FLASH", "loadaddr": "0x10040000", "debug": None},
    "secure_boot_manager.bin":         {"core": "C29",  "boot": "FLASH", "loadaddr": "0x10001000", "debug": None},
    "ram_based_uart_sbl.bin":          {"core": "C29",  "boot": "RAM",   "loadaddr": "0x200E1000", "debug": None},
    "ram_based_uart_sbl.temp.bin":     {"core": "C29",  "boot": "RAM",   "loadaddr": "0x200E1000", "debug": "DBG_SOC_DEFAULT"},
    "tifs_f29h85x_hs_se.release.bin":  {"core": "HSM",  "boot": "FLASH", "loadaddr": "0x00000000", "debug": "DBG_SOC_DEFAULT"},
    "tifs_f29h85x_hs_se_code_provisioning.release.bin": {
                                        "core": "HSM",  "boot": "RAM",   "loadaddr": "0x00000000", "debug": "DBG_SOC_DEFAULT"},
}


def get_device_prebuilt_dir(device_name: str = "f29h85x", device_family: str = None) -> Path:
    """
    Get prebuilt directory for a device, inferring family if not provided.

    Args:
        device_name (str): Device name (default: "f29h85x")
        device_family (str, optional): Device family. If not provided, will be inferred from device name.

    Returns:
        Path: Path to the prebuilt images directory
    """
    if device_family is None:
        if device_name.startswith("f29"):
            device_family = "asm"
        elif device_name.startswith("am"):
            device_family = "sitara"
        elif device_name.startswith("j7"):
            device_family = "jacinto"
        else:
            device_family = "asm"

    return get_prebuilt_images_dir(device_family, device_name)

class F29H85xDeviceModel:
    @classmethod
    def get_prebuilt_signing_specs(cls) -> list:
        """Return the ordered list of prebuilt binary signing specs."""
        return PREBUILT_SIGNING_SPECS

    def __init__(self, **kwargs):
        self.device = None
        self.device_name = "f29h85x"
        self.device_family = "asm"
        self.ti_fek_public_pem = None
        self.msv = None
        self.msv_protect = False
        self.b_protect = False
        self.bmek_protect = False
        self.s_protect = False
        self.smek_protect = False
        self.sr_sbl = None
        self.sr_hsmRT = None
        self.sr_app = None
        self.sr_ssu = None
        self.keycnt = None
        self.keycnt_protect = False
        self.keyrev = None
        self.devSrVer = None
        self.ext_otp = None
        self.ext_otp_indx = None
        self.ext_otp_size = None
        self.output_dir_path = None
        self.flash_kernel = None
        self.otp_keywriter_binary = None
        self.certificate = None
        self.ccs_path = None
        self.boot_mode = None
        self.serial_port = None
        self.sessionName = None
        self.sessionPassword = None
        self.hsm = False
        self.smpk = None
        self.bmpk = None
        self.development_session_checkbox = False
        self.code_binary = None  # For code provisioning
        
    def gen_keys(self, name, password, devel_keys=None, hsm=False, device=None):
        """Generate keys specifically for F29H85x device"""
        try:
            print(f"DEBUG: F29 Model - Generating keys with parameters:")
            print(f"  - Session name: {name}")
            print(f"  - HSM: {hsm}")
            
            # Check if this is the Development session
            if name == "Development":
                # Delete previous Development session if it exists
                try:
                    from tisecprov.session import SecureSession
                    with SecureSession() as s:
                        if s.does_session_exist("Development"):
                            print("DEBUG: F29 Model - Deleting previous Development session")
                            s.delete_session("Development")
                            print("DEBUG: F29 Model - Previous Development session deleted")
                except Exception as delete_error:
                    print(f"WARNING: F29 Model - Error while trying to delete previous Development session: {str(delete_error)}")

            # Store session information
            self.sessionName = name
            self.sessionPassword = password
            self.hsm = hsm
            self.device = "f29h85x"  # Always set device to f29h85x in this model
            
            # Set up default key algorithms
            smpk_algo = self.smpk if self.smpk else "rsa4k"  # Use existing or default to RSA4K
            bmpk_algo = self.bmpk if self.bmpk else "rsa4k"  # Use existing or default to RSA4K
            
            print(f"  - SMPK algorithm: {smpk_algo}")
            print(f"  - BMPK algorithm: {bmpk_algo}")
            
            if name == "Development":
                # For development session, just store the key types and set the flag
                # We don't need to create an actual session
                self.development_session_checkbox = True
                self.smpk = smpk_algo
                self.bmpk = bmpk_algo
                print(f"DEBUG: F29 Model - Development session parameters stored with SMPK: {smpk_algo}, BMPK: {bmpk_algo}")
            else:
                # For regular sessions, use the standard key generation
                from apps.spt.genkeys import generate_keys
                self.development_session_checkbox = False
                generate_keys(name, password, use_hsm=hsm,
                              smpk_signing_algorithm=smpk_algo,
                              bmpk_signing_algorithm=bmpk_algo)
            
            print(f"DEBUG: F29 Model - Keys generated successfully for session: {name}")
            return True
        except Exception as e:
            print(f"ERROR: F29 Model - Failed to generate keys: {str(e)}")
            raise Exception(f"{str(e)}")
            
    def load_existing_key(self, name, password, device=None, hsm=False):
        """Load existing key session for F29H85x device"""
        try:
            print(f"DEBUG: F29 Model - Loading existing key session: {name}")

            # Store session information
            self.sessionName = name
            self.sessionPassword = password
            self.hsm = hsm
            self.device = "f29h85x"  # Always set device to f29h85x in this model
            
            # Check if this is the Development session
            if name == "Development":
                self.development_session_checkbox = True
                # Set default signing algorithms to RSA4K
                self.smpk = "rsa4k"
                self.bmpk = "rsa4k"
                print("DEBUG: F29 Model - Loaded Development Session with RSA4K algorithms")
            else:
                self.development_session_checkbox = False
                print(f"DEBUG: F29 Model - Loaded regular session: {name}")
            
            # Verify the session exists but don't try to open it now
            try:
                from tisecprov.session import SecureSession
                with SecureSession() as s:
                    if s.does_session_exist(name):
                        print(f"DEBUG: F29 Model - Session {name} exists, ready for use")
                    else:
                        print(f"DEBUG: F29 Model - Session {name} does not exist, will be used if available when needed")
            except Exception as session_error:
                print(f"DEBUG: F29 Model - Could not verify session: {str(session_error)}")
            
            return True
        except Exception as e:
            print(f"ERROR: F29 Model - Failed to load key session: {str(e)}")
            raise Exception(f"{str(e)}")

    def _validate_cert_params(self):
        """Validate certificate generation parameters before building sys.argv.

        Raises ValueError with a descriptive message if any field is invalid.
        """
        import re
        from tisecprov.validators import (
            validate_swrev, validate_msv, validate_key_cnt, validate_key_rev,
        )
        from tisecprov.device_config import get_device_config

        device_config = get_device_config('f29h85x')
        otp = (device_config.otp_details or {}) if device_config.otp_details else {}

        # Validate SW revisions
        for field, label, max_key, default_max, byte_len in [
            (self.sr_sbl,   'SBL SW revision',         'MAX_SWREV_SBL_VALUE_SIZE',      32, 4),
            (self.sr_hsmRT, 'HSM Runtime SW revision', 'MAX_SWREV_HSMRT_VALUE_SIZE',    32, 4),
            (self.sr_app,   'CPU1 App SW revision',    'MAX_SWREV_SEC_APP_VALUE_SIZE',  32, 4),
            (self.sr_ssu,   'CPU1 SECCFG SW revision', 'MAX_SWREV_SSU_VALUE_SIZE',      64, 8),
        ]:
            if field and str(field) != "None":
                validate_swrev(str(field), otp.get(max_key, default_max), byte_len, label)

        # Validate MSV
        if self.msv and str(self.msv) != "None":
            validate_msv(str(self.msv), device_config)

        # Validate key count and key revision
        if self.keycnt and str(self.keycnt) != "None":
            validate_key_cnt(str(self.keycnt))
        if self.keyrev and str(self.keyrev) != "None":
            validate_key_rev(str(self.keyrev))

        # Validate extended OTP
        if self.ext_otp and str(self.ext_otp) != "None":
            cleaned = str(self.ext_otp).replace("0x", "").replace("0X", "")
            if not re.match(r'^[0-9a-fA-F]+$', cleaned):
                raise ValueError(f"Extended OTP value is not valid hexadecimal: {self.ext_otp}")
            if self.ext_otp_indx and str(self.ext_otp_indx) != "None":
                try:
                    int(str(self.ext_otp_indx))
                except (ValueError, TypeError):
                    raise ValueError(f"Extended OTP index must be an integer, got: {self.ext_otp_indx}")
            if self.ext_otp_size and str(self.ext_otp_size) != "None":
                try:
                    size = int(str(self.ext_otp_size))
                except (ValueError, TypeError):
                    raise ValueError(f"Extended OTP size must be an integer, got: {self.ext_otp_size}")
                if size < 32 or size % 8 != 0:
                    raise ValueError(
                        f"Extended OTP size must be a multiple of 8 and at least 32 bits, got: {size}"
                    )

    def generate_certificate(self):
        """Generate F29H85x certificate using f29_main"""
        try:
            # Validate parameters before building sys.argv
            self._validate_cert_params()

            # Build the command line arguments array
            # Start with the base args based on whether this is a development session or not
            if self.development_session_checkbox == False:
                print('Using regular session mode')
                sys.argv = [
                    'script_name',  # Script name (typically ignored)
                    '--device', 'f29h85x',
                    '--session', self.sessionName,
                    '--password', self.sessionPassword,
                    'gencert'
                ]
                if self.hsm:
                    sys.argv.append('--hsm')
            else:
                print("Using development session mode")
                sys.argv = [
                    'script_name',  # Script name (typically ignored)
                    '--device', 'f29h85x',
                    '--smpk_signing_algorithm', self.smpk,
                    '--bmpk_signing_algorithm', self.bmpk, 
                    'gencert'
                ]

            # Add the common arguments
            self._add_certificate_common_args()
            
            # Print the command for debugging
            print(f"DEBUG: F29 certificate generation command: {' '.join(sys.argv)}")
            
            # Call f29_main to generate the certificate
            print("DEBUG: Calling f29_main()")
            f29_main()
            print("DEBUG: F29 certificate generation completed successfully")
            
            return True
            
        except SystemExit as e:
            error_msg = f"F29 certificate generation failed: invalid arguments (exit code {e.code})"
            print(f"ERROR: {error_msg}")
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"F29 certificate generation failed: {str(e)}"
            print(f"ERROR: {error_msg}")
            raise Exception(error_msg)
    
    def _add_certificate_common_args(self):
        """Add common certificate generation arguments to sys.argv"""
        # Add TI FEK public key path
        if self.ti_fek_public_pem and str(self.ti_fek_public_pem) != "None":
            sys.argv.extend(['-t', self.ti_fek_public_pem])
            
        # Add MSV and MSV protect flag if needed
        if self.msv and str(self.msv) != "None":
            sys.argv.extend(['--msv', self.msv])
        if self.msv_protect:
            sys.argv.append('--msv_protect')
            
        # Add BMPK/BMEK flags
        sys.argv.append('--bmpk')
        sys.argv.append('--bmek')
        if self.b_protect:
            sys.argv.append('--b_protect')
        if self.bmek_protect:
            sys.argv.append('--bmek_protect')
            
        # Add SMPK/SMEK flags
        sys.argv.append('--smpk')
        sys.argv.append('--smek')
        if self.s_protect:
            sys.argv.append('--s_protect')
        if self.smek_protect:
            sys.argv.append('--smek_protect')
            
        # Add software revision information
        if self.sr_sbl and str(self.sr_sbl) != "None":
            sys.argv.extend(['--sr_sbl', self.sr_sbl])
        if self.sr_hsmRT and str(self.sr_hsmRT) != "None":
            sys.argv.extend(['--sr_hsmRT', self.sr_hsmRT])
        if self.sr_app and str(self.sr_app) != "None":
            sys.argv.extend(['--sr_app', self.sr_app])
        if self.sr_ssu and str(self.sr_ssu) != "None":
            sys.argv.extend(['--sr_ssu', self.sr_ssu])
            
        # Add key count and related flags
        if self.keycnt and str(self.keycnt) != "None":
            sys.argv.extend(['--keycnt', self.keycnt])
        if self.keycnt_protect:
            sys.argv.append('--keycnt_protect')
        if self.keyrev and str(self.keyrev) != "None":
            sys.argv.extend(['--keyrev', self.keyrev])
            
        # Add device and SR version
        sys.argv.extend(['-d', 'f29h85x'])  # Hardcoded since this is the F29 model
        if self.devSrVer and str(self.devSrVer) != "None":
            sys.argv.extend(['--devSrVer', self.devSrVer])
            
        # Add extended OTP options
        if self.ext_otp and str(self.ext_otp) != "None":
            sys.argv.extend(['--ext_otp', self.ext_otp])
        if self.ext_otp_indx and str(self.ext_otp_indx) != "None":
            sys.argv.extend(['--ext_otp_indx', self.ext_otp_indx])
        if self.ext_otp_size and str(self.ext_otp_size) != "None":
            sys.argv.extend(['--ext_otp_size', self.ext_otp_size])

        # Add output directory if specified
        if self.output_dir_path and str(self.output_dir_path) != "None":
            sys.argv.extend(['-o', str(self.output_dir_path)])

    
    def convert_device(self):
        """Convert device using either UART or JTAG method"""
        if self.boot_mode == 'UART':
            # Validate required parameters
            if not self.otp_keywriter_binary or not self.flash_kernel or not self.certificate or not self.serial_port:
                error_msg = "Missing required parameters for UART key provisioning"
                print(error_msg)
                return False, error_msg
                
            # Use the original f29_main approach for UART
            sys.argv = [
                'script_name',  # Script name (typically ignored)
                '--device', 'f29h85x',
                'uart_keyprov',
                '--otp-kw-bin', self.otp_keywriter_binary,
                '--uart-kernel', self.flash_kernel,
                '--certificate', self.certificate,
                '--port', self.serial_port
            ]
            
            print(f"Running UART key provisioning with args: {' '.join(str(arg) for arg in sys.argv)}")
            f29_main()
            print("UART Key Provisioning completed")
            return True, "UART Key Provisioning completed successfully"
            
        elif self.boot_mode == 'JTAG':
            # Validate required parameters
            if not self.otp_keywriter_binary:
                error_msg = "Missing OTP keywriter binary path"
                print(error_msg)
                return False, error_msg
                
            if not self.certificate:
                error_msg = "Missing certificate path"
                print(error_msg)
                return False, error_msg
                
            if not self.flash_kernel:
                error_msg = "Missing JTAG kernel path"
                print(error_msg)
                return False, error_msg
                
            if not self.ccs_path:
                error_msg = "Missing CCS path"
                print(error_msg)
                return False, error_msg
            
            # Use the direct function call for JTAG (more reliable)
            print(f"Running JTAG key provisioning with parameters:")
            print(f"  OTP KW Binary: {self.otp_keywriter_binary}")
            print(f"  Certificate: {self.certificate}")
            print(f"  JTAG Kernel: {self.flash_kernel}")
            print(f"  CCS Path: {self.ccs_path}")
            
            try:
                # Call the run_key_provisioning_jtag function directly
                success, output = run_key_provisioning_jtag(
                    self.otp_keywriter_binary,
                    self.certificate,
                    self.flash_kernel,
                    self.ccs_path,
                    True  # Enable verbose output
                )
                
                if not success:
                    error_msg = f"JTAG Key Provisioning failed: {output}"
                    print(error_msg)
                    return False, error_msg
                
                print(f"JTAG Key Provisioning succeeded: {output}")
                return True, output
                
            except Exception as e:
                error_msg = f"Exception during JTAG Key Provisioning: {str(e)}"
                print(error_msg)
                return False, error_msg
        
        # Invalid boot mode
        error_msg = f"Invalid boot mode: {self.boot_mode}"
        print(error_msg)
        return False, error_msg
        
    def get_soc_id(self, serial_port):
        """Get SoC ID from the device via UART
        
        Args:
            serial_port (str): Serial port to use
            
        Returns:
            bool: True if command succeeded, False otherwise
        """
        try:
            sys.argv = [
                'script_name',  # Script name (typically ignored)
                '--device', 'f29h85x',
                'getSoCId',
                '--port', serial_port,
                '--baudrate', '115200',
                '--parity', 'N',
                '--stopbits', '1',
                '--timeout', '5'
            ]
            
            print("Running getSoCId command with args:", sys.argv)
            f29_main()
            return True
        except Exception as e:
            print(f"Error getting SoC ID: {str(e)}")
            return False
            
    def get_device_type(self, ccs_path):
        """Get device type using JTAG
        
        Args:
            ccs_path (str): Path to CCS installation
            
        Returns:
            tuple: (bool, str) Success flag and output message
        """
        try:
            sys.argv = [
                'script_name',  # Script name (typically ignored)
                '--device', 'f29h85x',
                'devTypeJTAG',  # Fixed command name to match parser in f29_spt.py
                '--ccs-path', ccs_path,
                '--verbose'
            ]
            
            print("Running devTypeJTAG command with args:", sys.argv)
            f29_main()
            return True, "Device type detection successful"
        except Exception as e:
            error_msg = f"Error getting device type: {str(e)}"
            print(error_msg)
            return False, error_msg
            
    def provision_code(self, uart_kernel=None, hsm_image=None, hsm_cpu_code=None, 
                 c29_cpu_code=None, seccfg=None, device=None, port=None,
                 jtag_kernel=None, ccs_path=None, verbose=True):
        """
        Provision code to the device using either UART or JTAG
        
        This method accepts parameters for both UART and JTAG code provisioning.
        Only parameters relevant to the current boot mode will be used.
        """
        if self.boot_mode == 'UART':
            # Use provided parameters or fall back to instance variables
            uart_kernel = uart_kernel or self.flash_kernel
            hsm_image = hsm_image or self.code_binary
            port = port or self.serial_port
            device = device or 'f29h85x'
            
            # Validate required parameters
            if not uart_kernel or not hsm_image or not port:
                error_msg = "Missing required parameters for UART code provisioning"
                print(error_msg)
                return False, error_msg
                
            # If optional parameters are provided, use them
            hsm_cpu_code = hsm_cpu_code or self.code_binary
            c29_cpu_code = c29_cpu_code or self.code_binary
            seccfg = seccfg or self.code_binary
            
            try:
                # Call run_code_provisioning_uart directly
                run_code_provisioning_uart(
                    uart_kernel,
                    hsm_image,
                    hsm_cpu_code,
                    c29_cpu_code,
                    seccfg,
                    device,
                    port
                )
                print("UART Code Provisioning completed")
                return True, "UART Code Provisioning completed successfully"
            except Exception as e:
                error_msg = f"UART Code Provisioning failed: {str(e)}"
                print(error_msg)
                return False, error_msg
        
        elif self.boot_mode == 'JTAG':
            # Use provided parameters or fall back to instance variables
            jtag_kernel = jtag_kernel or self.flash_kernel
            hsm_image = hsm_image or self.code_binary
            ccs_path = ccs_path or self.ccs_path
            
            # Validate required parameters
            if not hsm_image:
                error_msg = "Missing HSM image path"
                print(error_msg)
                return False, error_msg
                
            if not jtag_kernel:
                error_msg = "Missing JTAG kernel path"
                print(error_msg)
                return False, error_msg
                
            if not ccs_path:
                error_msg = "Missing CCS path"
                print(error_msg)
                return False, error_msg
            
            # If optional parameters are provided, use them
            hsm_cpu_code = hsm_cpu_code or hsm_image
            c29_cpu_code = c29_cpu_code or hsm_image
            seccfg = seccfg or hsm_image
            
            # Use the direct function call for JTAG
            print(f"Running JTAG code provisioning with parameters:")
            print(f"  HSM Image: {hsm_image}")
            print(f"  JTAG Kernel: {jtag_kernel}")
            print(f"  CCS Path: {ccs_path}")
            
            try:
                # Call the run_code_provisioning_jtag function directly
                success, output = run_code_provisioning_jtag(
                    hsm_image,
                    jtag_kernel,
                    ccs_path,
                    hsm_cpu_code_path=hsm_cpu_code,
                    c29_cpu_code_path=c29_cpu_code,
                    seccfg_path=seccfg,
                    verbose=verbose
                )
                
                if not success:
                    error_msg = f"JTAG Code Provisioning failed: {output}"
                    print(error_msg)
                    return False, error_msg
                
                print(f"JTAG Code Provisioning succeeded: {output}")
                return True, output
                
            except Exception as e:
                error_msg = f"Exception during JTAG Code Provisioning: {str(e)}"
                print(error_msg)
                return False, error_msg
            
        # Invalid boot mode
        error_msg = f"Invalid boot mode: {self.boot_mode}"
        print(error_msg)
        return False, error_msg
        
    def sign_binary(self, **kwargs):
        """
        Sign a binary file using the sign_encrypt function
        
        Args:
            image (str): Path to the binary file
            input_format (str): Input format (BIN or ELF)
            core (str): Target core (C29 or HSM)
            keyrev (str): Key revision (1 or 2)
            loadaddr (str): Load address (hex string)
            swrv (str): Software revision number
            boot (str): Boot mode (FLASH or RAM)
            debug (str, optional): Debug options
            ccs_path (str, optional): Path to CCS installation
            
        Returns:
            tuple: (bool, str) Success flag and output message
        """
        try:
            # Extract parameters
            image = kwargs.get('image')
            input_format = kwargs.get('input_format', 'BIN')
            core = kwargs.get('core')
            keyrev = kwargs.get('keyrev')
            loadaddr = kwargs.get('loadaddr')
            swrv = kwargs.get('swrv')
            boot = kwargs.get('boot')
            debug = kwargs.get('debug')
            ccs_path = kwargs.get('ccs_path')
            
            # Validate required parameters
            if not image:
                raise ValueError("Binary image path is required")
                
            if not core:
                raise ValueError("Target core is required")
                
            if not keyrev:
                raise ValueError("Key revision is required")
                
            if not loadaddr:
                raise ValueError("Load address is required")
                
            if not boot:
                raise ValueError("Boot mode is required")
                
            if not swrv:
                raise ValueError("Software revision is required")
            
            # Create a new args object for sign_encrypt
            class Args:
                pass
                
            args = Args()
            
            # Set required parameters
            args.device = "f29h85x"  # Always f29h85x for this model
            # Convert Path to string if it's a Path object
            args.image = str(image) if isinstance(image, Path) else image
            args.input_format = input_format
            args.core = core
            args.keyrev = keyrev
            args.loadaddr = loadaddr
            args.swrv = swrv
            args.boot = boot
            
            # Set optional parameters with better defaults
            args.sbl_enc = kwargs.get('sbl_enc', False)
            args.tifs_enc = kwargs.get('tifs_enc', False)
            args.fw_enc = kwargs.get('fw_enc', False)
            args.fw_type = kwargs.get('fw_type', None)
            args.enc_key = kwargs.get('enc_key', None)
            args.fw_enc_key = kwargs.get('fw_enc_key', None)
            args.kd_salt = kwargs.get('kd_salt', None)
            args.img_integ = kwargs.get('img_integ', False)
            args.crypto_unlock = kwargs.get('crypto_unlock', 'no')
            args.hsm = kwargs.get('hsm', False)
            
            # Set optional parameters if provided
            if debug:
                args.debug = debug
            else:
                args.debug = None
                
            if ccs_path:
                args.ccs_path = ccs_path
            else:
                args.ccs_path = None
                
            # Set session info based on model state
            if self.development_session_checkbox:
                # For development session - use development session credentials
                # For direct calling of sign_encrypt, session is required
                args.session = "Development"
                args.password = "develop123#"  # Default development password
                args.hsm = False  # Development sessions don't use HSM
            else:
                # For regular session
                args.session = self.sessionName
                args.password = self.sessionPassword
                
            # Set the signing algorithms based on model attributes
            if hasattr(self, 'smpk') and self.smpk:
                args.smpk_signing_algorithm = self.smpk
            if hasattr(self, 'bmpk') and self.bmpk:
                args.bmpk_signing_algorithm = self.bmpk
            
            # Use the set_output_path function from sign_encrypt.py if no path is specified
            if 'output_path' in kwargs and kwargs['output_path']:
                args.output_path = kwargs['output_path']
            else:
                # Import set_output_path function to use the same path as sign_encrypt.py
                from apps.tifs.sign_encrypt_f29.sign_encrypt import set_output_path
                args.output_path = set_output_path()
                
            # Ensure output directory exists
            Path(args.output_path).mkdir(parents=True, exist_ok=True)
            
            # Store original sys.argv
            original_argv = sys.argv.copy()
            
            print(f"DEBUG: Signing binary {Path(image).name} with parameters:")
            print(f"  - Core: {core}")
            print(f"  - Boot: {boot}")
            print(f"  - KeyRev: {keyrev}")
            print(f"  - LoadAddr: {loadaddr}")
            print(f"  - SwRv: {swrv}")
            if debug:
                print(f"  - Debug: {debug}")
            if ccs_path:
                print(f"  - CCS Path: {ccs_path}")
                
            # Call sign_encrypt with the prepared args
            sign_encrypt(args)
            
            # Restore original sys.argv
            sys.argv = original_argv
            
            # Get the output directory and filename
            output_dir = args.output_path  # Already set above
            
            # Determine the output filename based on the input filename
            input_path = Path(image)
            if core == "HSM":
                output_basename = f"{input_path.stem}.hs.hsmimage.bin"
            elif core == "C29":
                output_basename = f"{input_path.stem}.cert.bin"
            else:
                output_basename = f"{input_path.stem}.bin"
                
            output_path = output_dir / output_basename
            
            return True, f"Binary signed successfully as {output_path}"
            
        except Exception as e:
            error_msg = f"Failed to sign binary: {str(e)}"
            print(f"ERROR: {error_msg}")
            return False, error_msg
            
    def sign_sec_cfg_wrapper(self, **kwargs):
        """
        Sign a Sec-Cfg binary using the sign_sec_cfg function from sign_encrypt.py
        
        This method wraps the sign_sec_cfg function from the sign_encrypt.py module,
        handling parameter preparation and session management. It signs a Security
        Configuration image with the specified private key and generates signed
        binary files for all CPU cores.
        
        Args:
            image (str): Path to the Sec-Cfg image to sign
            swrv (str): Software revision number for the Sec-Cfg
            keyrev (str): Key revision to use: 1-> SMPK and 2->BMPK
            ccs_path (str): Path to CCS installation directory
            output_path (Path, optional): Output directory for signed binaries
            boot (str, optional): Boot mode (FLASH or RAM), defaults to FLASH
            hsm (bool, optional): Whether to use HSM Device to access the keys
            
        Returns:
            tuple: (bool, str) Success flag and output message with details of the operation
            
        Raises:
            ValueError: If any required parameters are missing
            Exception: If there are errors during the signing process
        """
        try:
            # Extract parameters
            image = kwargs.get('image')
            swrv = kwargs.get('swrv')
            keyrev = kwargs.get('keyrev')
            ccs_path = kwargs.get('ccs_path')
            output_path = kwargs.get('output_path')
            boot = kwargs.get('boot', 'FLASH')  # Default to FLASH if not provided
            
            # Validate required parameters
            if not image:
                raise ValueError("Sec-Cfg image path is required")
                
            if not swrv:
                raise ValueError("Software revision is required")
                
            if not keyrev:
                raise ValueError("Key revision is required")
                
            if not ccs_path:
                raise ValueError("CCS path is required")
            
            # Create a new args object for sign_sec_cfg
            class Args:
                pass
                
            args = Args()
            
            # Set required parameters
            args.device = "f29h85x"  # Always f29h85x for this model
            args.image = str(image) if isinstance(image, Path) else image
            args.swrv = swrv
            args.keyrev = keyrev
            args.ccs_path = ccs_path
            args.boot = boot  
            
            # Set output path
            if output_path:
                args.output_path = output_path
            else:
                # Import set_output_path function to use the same path as sign_encrypt.py
                from apps.tifs.sign_encrypt_f29.sign_encrypt import set_output_path
                args.output_path = set_output_path()
                
            # Ensure output directory exists
            Path(args.output_path).mkdir(parents=True, exist_ok=True)
            
            # Set session info based on model state
            if self.development_session_checkbox:
                # For development session
                args.session = "Development"
                args.password = "develop123#"  # Default development password
                args.hsm = False  # Development sessions don't use HSM
            else:
                # For regular session
                args.session = self.sessionName
                args.password = self.sessionPassword
                args.hsm = kwargs.get('hsm', False)
                
            # Set the signing algorithms based on model attributes
            if hasattr(self, 'smpk') and self.smpk:
                args.smpk_signing_algorithm = self.smpk
            if hasattr(self, 'bmpk') and self.bmpk:
                args.bmpk_signing_algorithm = self.bmpk
                
            # Store original sys.argv
            original_argv = sys.argv.copy()
            
            print(f"DEBUG: Signing Sec-Cfg {Path(image).name} with parameters:")
            print(f"  - KeyRev: {keyrev}")
            print(f"  - SwRv: {swrv}")
            print(f"  - Boot: {boot}")
            print(f"  - CCS Path: {ccs_path}")
            
            # Call sign_sec_cfg with the prepared args
            sign_sec_cfg(args)
            
            # Restore original sys.argv
            sys.argv = original_argv

            # Get the output path - convert to Path if string
            output_path = Path(args.output_path) if isinstance(args.output_path, str) else args.output_path
            output_file = output_path / "seccfg.bin"

            return True, f"Sec-Cfg signed successfully as {output_file}"
            
        except Exception as e:
            error_msg = f"Failed to sign Sec-Cfg: {str(e)}"
            print(f"ERROR: {error_msg}")
            return False, error_msg

    def gen_debug_cert(self, **kwargs):
        """
        Generate a Debug Authentication certificate using gen_debug_auth_cert function

        This method wraps the gen_debug_auth_cert function from debug_image_gen.py,
        handling parameter preparation and session management. It generates a debug
        certificate signed with either SMPK or BMPK key.

        Args:
            keyrev (str): Key revision to use: 1-> SMPK and 2->BMPK
            swrv (str): Software revision number
            dev_uid (str): Device UID (64-byte hexadecimal string)
            dev_dbg_type (int): Debug type (1, 2, 3, or 4)
            output_path (Path, optional): Output directory for debug certificate
            hsm (bool, optional): Whether to use HSM Device to access the keys

        Returns:
            tuple: (bool, str) Success flag and output message with details of the operation

        Raises:
            ValueError: If any required parameters are missing
            Exception: If there are errors during certificate generation
        """
        try:
            from apps.tifs.debug_cert_scripts.debug_image_gen import gen_debug_auth_cert

            keyrev = kwargs.get('keyrev')
            swrv = kwargs.get('swrv')
            dev_uid = kwargs.get('dev_uid')
            dev_dbg_type = kwargs.get('dev_dbg_type')
            output_path = kwargs.get('output_path')

            if not keyrev:
                raise ValueError("Key revision is required")

            if not swrv:
                raise ValueError("Software revision is required")

            if not dev_uid:
                raise ValueError("Device UID is required")

            if not dev_dbg_type:
                raise ValueError("Debug type is required")

            class Args:
                pass

            args = Args()

            args.device = "f29h85x"
            args.keyrev = str(keyrev)
            args.swrv = str(swrv)
            args.dev_uid = dev_uid
            args.dev_dbg_type = int(dev_dbg_type)
            args.flags = None
            args.sign_key_id = None
            args.enc_key_id = None

            if output_path:
                args.debug_output = output_path
            else:
                from apps.tifs.debug_cert_scripts.debug_image_gen import set_output_path
                args.debug_output = set_output_path("f29h85x")

            Path(args.debug_output).mkdir(parents=True, exist_ok=True)

            if self.development_session_checkbox:
                args.session = "Development"
                args.password = "develop123#"
                args.hsm = False

                args.smpk_signing_algorithm = self.smpk if self.smpk else "rsa4k"
                args.bmpk_signing_algorithm = self.bmpk if self.bmpk else "rsa4k"
            else:
                args.session = self.sessionName
                args.password = self.sessionPassword
                args.hsm = kwargs.get('hsm', False)

            original_argv = sys.argv.copy()

            print(f"DEBUG: Generating Debug certificate with parameters:")
            print(f"  - KeyRev: {keyrev}")
            print(f"  - SwRv: {swrv}")
            print(f"  - Debug Type: {dev_dbg_type}")
            print(f"  - Device UID: {dev_uid}")

            gen_debug_auth_cert(args)

            sys.argv = original_argv

            output_file = args.debug_output / "debug_auth.cert"

            return True, f"Debug certificate generated successfully as {output_file}"

        except Exception as e:
            error_msg = f"Failed to generate debug certificate: {str(e)}"
            print(f"ERROR: {error_msg}")
            return False, error_msg

    def gen_rot_cert(self, **kwargs):
        """
        Generate a Root of Trust (ROT) switching certificate.

        Args:
            output_path (Path, optional): Output directory for ROT certificate.
            hsm (bool, optional): Whether to use HSM device to access the keys.

        Returns:
            tuple: (bool, str) Success flag and output message.
        """
        try:
            from apps.tifs.rot_cert_scripts.rot_switch_cert_gen import (
                gen_rot_cert as _gen_rot_cert,
                set_output_path as _default_output_path,
            )

            output_path = kwargs.get("output_path")

            class Args:
                pass

            args = Args()
            args.device = "f29h85x"
            args.rot_output = Path(output_path) if output_path else _default_output_path("f29h85x")

            if self.development_session_checkbox:
                args.session = "Development"
                args.password = "develop123#"
                args.hsm = False
            else:
                args.session = self.sessionName
                args.password = self.sessionPassword
                args.hsm = kwargs.get("hsm", False)

            print(f"DEBUG: Generating ROT certificate with session '{args.session}'")
            print(f"  - Output: {args.rot_output}")

            _gen_rot_cert(args)

            output_file = args.rot_output / "rot_switching.cert"
            return True, f"ROT certificate generated successfully as {output_file}"

        except Exception as e:
            error_msg = f"Failed to generate ROT certificate: {str(e)}"
            print(f"ERROR: {error_msg}")
            return False, error_msg

    def sign_all_prebuilt_binaries(self, ccs_path=None):
        """
        Sign all prebuilt binary files in host/bin/asm/f29h85x/ directory
        
        Args:
            ccs_path (str, optional): Path to CCS installation
            
        Returns:
            tuple: (bool, str) Success flag and detailed result message
        """
        # Verify session information first
        if not hasattr(self, 'sessionName') or not self.sessionName:
            if not self.development_session_checkbox:
                error_msg = "No session information available. Please select a key first."
                print(f"ERROR: {error_msg}")
                return False, error_msg
            else:
                print("Using development session...")
                
        # Known binary configurations (static fields; keyrev/swrv added dynamically below)
        prebuilt_images_dir = get_device_prebuilt_dir(self.device_name, self.device_family)
        binary_configs = PREBUILT_BINARY_CONFIGS
        
        # Check if directory exists
        if not prebuilt_images_dir.exists():
            error_msg = f"Prebuilt images directory not found: {prebuilt_images_dir}"
            print(f"ERROR: {error_msg}")
            return False, error_msg
        
        # Get all binary files in the directory
        all_binary_files = list(prebuilt_images_dir.glob("*.bin"))
        if not all_binary_files:
            error_msg = "No binary files found in prebuilt images directory"
            print(f"ERROR: {error_msg}")
            return False, error_msg
            
        # Filter out OTP keywriter files that should not be signed
        binary_files = [bf for bf in all_binary_files if "otp_kw" not in bf.name.lower()]
        print(f"DEBUG: Found {len(all_binary_files)} binary files, {len(binary_files)} will be processed (excluding OTP keywriter files)")
            
        # Results tracking
        results = []
        success_count = 0
        fail_count = 0
        
        # Process each binary file
        for binary_file in binary_files:
            binary_name = binary_file.name
            
            # Use known config if available, otherwise use default
            if binary_name in binary_configs:
                config = dict(binary_configs[binary_name])
                config.setdefault("keyrev", "1")
                config.setdefault("swrv", "1")
                print(f"Using predefined configuration for {binary_name}")
            else:
                # Use default configuration
                config = {
                    "core": "C29" if "c29" in binary_name.lower() else "HSM",
                    "boot": "FLASH",
                    "loadaddr": "0x10001000" if "c29" in binary_name.lower() else "0x00000000",
                    "keyrev": "1",
                    "swrv": "1",
                    "debug": "DBG_SOC_DEFAULT" if "hsm" in binary_name.lower() else None
                }
                print(f"Using default configuration for {binary_name}")
                
            # Add CCS path if provided
            if ccs_path:
                config["ccs_path"] = ccs_path
                
            # Add binary file path - convert Path to string
            config["image"] = str(binary_file)
            config["input_format"] = "BIN"  # Always BIN for prebuilt binaries
                
            try:
                # Sign the binary
                print(f"Signing {binary_name}...")
                success, message = self.sign_binary(**config)
                
                # Track result
                if success:
                    results.append(f"✓ {binary_name}: {message}")
                    success_count += 1
                else:
                    results.append(f"✗ {binary_name}: {message}")
                    fail_count += 1
            except Exception as e:
                error_msg = f"Exception while signing {binary_name}: {str(e)}"
                print(f"ERROR: {error_msg}")
                results.append(f"✗ {binary_name}: {error_msg}")
                fail_count += 1
                
        # Compile final result message
        total_eligible_binaries = len(binary_files)
        result_message = f"Signed {success_count} of {total_eligible_binaries} binaries successfully.\n\n"
        result_message += "\n".join(results)
        
        # Overall success if at least one binary was signed successfully
        overall_success = success_count > 0
        return overall_success, result_message