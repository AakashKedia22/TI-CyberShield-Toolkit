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

from typing import Dict, Any, Optional, List, Tuple
import sys

from ..base_device import BaseDevice


class F29H85xBaseDevice(BaseDevice):
    """
    Base class for all F29H85x device variants with common functionality.
    """
    
    def __init__(self, device_name: str, device_variant: str, **kwargs):
        """
        Initialize an F29H85x device.

        Args:
            device_name (str): Name of the device (should be "f29h85x")
            device_variant (str): Variant of the device (e.g., "hsfs", "hsse")
            **kwargs: Additional device parameters
        """
        super().__init__(device_name, device_variant, device_family="asm")
        
        # F29H85x-specific parameters
        self.ti_fek_public_pem = kwargs.get('ti_fek_public_pem')
        self.msv = kwargs.get('msv', '0x1E22D')
        self.msv_protect = kwargs.get('msv_protect', False)
        self.b_protect = kwargs.get('b_protect', False)
        self.bmek_protect = kwargs.get('bmek_protect', False)
        self.s_protect = kwargs.get('s_protect', False)
        self.smek_protect = kwargs.get('smek_protect', False)
        self.sr_sbl = kwargs.get('sr_sbl', '1')
        self.sr_hsmRT = kwargs.get('sr_hsmRT', '1')
        self.sr_app = kwargs.get('sr_app', '1')
        self.sr_ssu = kwargs.get('sr_ssu', '1')
        self.keycnt = kwargs.get('keycnt', '2')
        self.keycnt_protect = kwargs.get('keycnt_protect', False)
        self.keyrev = kwargs.get('keyrev', '1')
        self.devSrVer = kwargs.get('devSrVer', 'SR_20')
        self.ext_otp = kwargs.get('ext_otp')
        self.ext_otp_indx = kwargs.get('ext_otp_indx')
        self.ext_otp_size = kwargs.get('ext_otp_size')
        self.flash_kernel = kwargs.get('flash_kernel')
        self.otp_keywriter_binary = kwargs.get('otp_keywriter_binary')
        self.certificate = kwargs.get('certificate')
        
        # Session parameters
        self.sessionName = kwargs.get('sessionName')
        self.sessionPassword = kwargs.get('sessionPassword')
        self.smpk = kwargs.get('smpk')
        self.bmpk = kwargs.get('bmpk')
        self.development_session_checkbox = kwargs.get('development_session_checkbox', False)
        
        # Code provisioning parameters
        self.code_binary = kwargs.get('code_binary')
    
    def get_soc_id(self, port: str) -> Dict[str, Any]:
        """
        Get SoC ID from the device via UART.
        
        Args:
            port (str): Serial port to use
            
        Returns:
            Dict[str, Any]: Dictionary containing device information
        """
        try:
            sys.argv = [
                'script_name',  # Script name (typically ignored)
                '--device', 'f29h85x',
                'getSoCId',
                '--port', port,
                '--baudrate', '115200',
                '--parity', 'N',
                '--stopbits', '1',
                '--timeout', '5'
            ]
            
            # Import here to avoid circular imports
            from apps.spt.f29_spt import f29_main
            
            print("Running getSoCId command with args:", sys.argv)
            result = f29_main()
            
            # For now, return a dummy result since we don't have actual parsing of f29_main output
            return {
                'success': True,
                'device': 'f29h85x',
                'device_state': self.device_variant.upper()
            }
        except Exception as e:
            print(f"Error getting SoC ID: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
            
    def get_device_type(self, ccs_path: str = None) -> Optional[str]:
        """
        Get device type using JTAG.
        
        Args:
            ccs_path (str, optional): Path to CCS installation
            
        Returns:
            Optional[str]: Device type if successful, None otherwise
        """
        if not ccs_path:
            return None
            
        try:
            # Import here to avoid circular imports
            from apps.spt.f29_spt import f29_main
            
            sys.argv = [
                'script_name',  # Script name (typically ignored)
                '--device', 'f29h85x',
                'devTypeJTAG',  # Correct command for JTAG device type detection
                '--ccs-path', ccs_path,
                '--verbose'
            ]
            
            print("Running devTypeJTAG command with args:", sys.argv)
            result = f29_main()
            
            # For now, return a dummy result
            return self.device_variant.upper()
        except Exception as e:
            print(f"Error getting device type: {str(e)}")
            return None
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate parameters for F29H85x device.
        
        Args:
            parameters (Dict[str, Any]): Parameters to validate
            
        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        # Check required parameters for certificate generation
        required_cert_params = ['ti_fek_public_pem', 'msv', 'sr_sbl', 'sr_hsmRT', 'sr_app', 'sr_ssu', 'keycnt', 'keyrev', 'devSrVer']
        for param in required_cert_params:
            if param not in parameters or not parameters[param]:
                return False, f"Missing required parameter: {param}"
                
        # Check required parameters for device conversion
        required_conv_params = ['flash_kernel', 'otp_keywriter_binary', 'certificate']
        for param in required_conv_params:
            if param not in parameters or not parameters[param]:
                return False, f"Missing required parameter: {param}"
                
        # All checks passed
        return True, ""
        
    def run_command(self, command: str, args: List[str]) -> Any:
        """
        Run a command with the F29 SPT tool.
        
        Args:
            command (str): Command to run
            args (List[str]): Command arguments
            
        Returns:
            Any: Command result
        """
        # Import here to avoid circular imports
        from apps.spt.f29_spt import f29_main
        
        # Build the command
        sys.argv = ['script_name', '--device', 'f29h85x', command] + args
        
        print(f"Running command with args: {sys.argv}")
        return f29_main()

    def provision_code(self) -> bool:
        """
        Provision code to the device.
        
        Returns:
            bool: True if code provisioning was successful, False otherwise
        """
        try:
            if self.boot_mode == "UART":
                # Build the command for UART code provisioning
                sys.argv = [
                    'script_name',
                    '--device', 'f29h85x',
                    'uart_code_prov',
                    '--uart-kernel', self.flash_kernel,
                    '--code-binary', self.code_binary,
                    '--certificate', self.certificate,
                    '--port', self.serial_port
                ]
            elif self.boot_mode == "JTAG":
                # Build the command for JTAG code provisioning
                sys.argv = [
                    'script_name',
                    '--device', 'f29h85x',
                    'jtag_code_prov',
                    '--ccs-path', self.ccs_path,
                    '--code-binary', self.code_binary,
                    '--certificate', self.certificate,
                ]
            
            # Import here to avoid circular imports
            from apps.spt.f29_spt import f29_main
            
            print(f"Running code provisioning with args: {sys.argv}")
            f29_main()
            return True
        except Exception as e:
            print(f"Error during code provisioning: {str(e)}")
            return False