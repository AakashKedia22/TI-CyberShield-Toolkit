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

from typing import Dict, Any, List
import sys
import os

from .common import F29H85xBaseDevice


class F29H85xHSFSDevice(F29H85xBaseDevice):
    """
    F29H85x HSFS (High Security Field Secure) device implementation.
    """
    
    def __init__(self, device_name: str, device_variant: str, **kwargs):
        """
        Initialize an F29H85x HSFS device.
        
        Args:
            device_name (str): Name of the device (should be "f29h85x")
            device_variant (str): Variant of the device (should be "hsfs")
            **kwargs: Additional device parameters
        """
        super().__init__(device_name, device_variant, **kwargs)
    
    def generate_certificate(self, **kwargs) -> bool:
        """
        Generate a certificate for F29H85x HSFS device.
        
        Args:
            **kwargs: Additional certificate parameters
            
        Returns:
            bool: True if certificate generation was successful, False otherwise
        """
        try:
            # Override instance parameters with any provided kwargs
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            
            # Build the command line arguments array
            # Start with the base args based on whether this is a development session or not
            if not self.development_session_checkbox:
                print('Using regular session mode')
                sys.argv = [
                    'script_name',  # Script name (typically ignored)
                    '--device', 'f29h85x',
                    '--session', self.sessionName,
                    '--password', self.sessionPassword,
                    'gencert'
                ]
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
            
            # Import here to avoid circular imports
            from apps.spt.f29_spt import f29_main
            
            # Call f29_main to generate the certificate
            print("DEBUG: Calling f29_main()")
            f29_main()
            print("DEBUG: F29 certificate generation completed successfully")
            
            return True
            
        except Exception as e:
            error_msg = f"F29 certificate generation failed: {str(e)}"
            print(f"ERROR: {error_msg}")
            return False
    
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
    
    def convert_device(self) -> bool:
        """
        Convert the F29H85x device from HSFS to other state.
        
        Returns:
            bool: True if conversion was successful, False otherwise
        """
        try:
            # Import here to avoid circular imports
            from apps.spt.f29_spt import f29_main
            
            if self.boot_mode == 'UART':
                sys.argv = [
                    'script_name',  # Script name (typically ignored)
                    '--device', 'f29h85x',
                    'uart_keyprov',
                    '--otp-kw-bin', self.otp_keywriter_binary,
                    '--uart-kernel', self.flash_kernel,
                    '--certificate', self.certificate,
                    '--port', self.serial_port
                ]
            elif self.boot_mode == 'JTAG':
                sys.argv = [
                    'script_name',  # Script name (typically ignored)
                    '--device', 'f29h85x',
                    'jtag_keyprov',
                    '--ccs-path', self.ccs_path,
                    '--otp-kw-bin', self.otp_keywriter_binary,
                    '--jtag-kernel', self.flash_kernel,
                    '--certificate', self.certificate,
                ]
            else:
                print(f"ERROR: Unsupported boot mode: {self.boot_mode}")
                return False
            
            print(f"DEBUG: F29 device conversion command: {' '.join(sys.argv)}")
            print(f"DEBUG: OTP Keywriter binary: {self.otp_keywriter_binary}")
            
            # Call f29_main to convert the device
            f29_main()
            print("DEBUG: F29 device conversion completed successfully")
            
            return True
        except Exception as e:
            print(f"ERROR: F29 device conversion failed: {str(e)}")
            return False
    
    def get_supported_variants(self) -> List[str]:
        """
        Get list of supported variants for F29H85x device.
        
        Returns:
            List[str]: List of supported variant names
        """
        return ["hsfs", "hsse", "hskp"]