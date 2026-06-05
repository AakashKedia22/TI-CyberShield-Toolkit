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

from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal
import serial.tools.list_ports
from apps.qtgui.utils.platform_utils import format_serial_port_name, get_serial_port_filter
from common.device_utils import get_device_prebuilt_dir
from pathlib import Path

from apps.qtgui.models.host_model import KeyCertModel
from apps.qtgui.models.F29H85xDeviceModel import F29H85xDeviceModel
import os
import tempfile

class WizardController(QObject):
    """
    Controller for the wizard flow that connects models with the wizard view
    and handles business logic
    """
    
    # Signal for device state change (e.g., HSFS -> HSKP after conversion)
    device_state_changed = pyqtSignal(str)
    
    # Signal for operation result
    operation_result = pyqtSignal(bool, str)
    
    def __init__(self, wizard_view):
        super().__init__()
        self.wizard_view = wizard_view
        self.key_cert_model = KeyCertModel()
        self.f29_model = F29H85xDeviceModel()
        
        # Define devices and boot modes (moved from TargetModel)
        self.devices = [
            "F29H85x", 
            "AM261x", 
            "AM263Px", 
            "AM261x"
        ]
        
        self.boot_modes = {
            "F29H85x": ["UART", "JTAG"],
            "AM261x": ["UART"],
            "AM263Px": ["UART"],
        }
        
        # Connect signals from the wizard view
        self._connect_signals()
        
    def _connect_signals(self):
        """Connect signals from the wizard view to controller methods"""
        # Landing page signals
        landing_page = self.wizard_view.landing_page
        landing_page.device_changed.connect(self._on_device_changed)

        # Key operation signals
        landing_page.key_generated.connect(self._on_key_generated)
        landing_page.key_loaded.connect(self._on_key_loaded)
        landing_page.f29_development_session_set.connect(self._on_f29_development_session_set)
        landing_page.certificate_request.connect(self._on_certificate_request)

        # Config page signals
        config_page = self.wizard_view.config_page
        config_page.device_detection_requested.connect(self._on_device_detection_requested)
        config_page.binary_signing_requested.connect(self._on_binary_signing_requested)
        config_page.seccfg_cert_requested.connect(self._on_seccfg_cert_requested)

        # Provisioning page signals
        prov_page = self.wizard_view.provisioning_page
        prov_page.convert_requested.connect(self._on_convert_requested)

        # Connect our signals to wizard_view's methods
        self.device_state_changed.connect(self.wizard_view.handle_device_state_changed)
        self.operation_result.connect(self.wizard_view.handle_operation_result)

        # CLI script generation when wizard finishes
        self.wizard_view.wizard_completed.connect(self._on_wizard_completed)
    
    @pyqtSlot(str)
    def _on_device_changed(self, device):
        """Handle device selection change"""
        print(f"Device changed to: {device}")
        # Update model with selected device
        if device.lower() == "f29h85x":
            self.current_model = self.f29_model
            self.current_model.device = device.lower()
        else:
            self.current_model = self.key_cert_model
            if hasattr(self.current_model, 'current_device'):
                self.current_model.current_device = device.lower()
    
    @pyqtSlot(dict)
    def _on_key_generated(self, key_data):
        """Handle key generation"""
        print(f"Generating keys with data: {key_data}")
        
        name = key_data.get("name")
        password = key_data.get("password")
        devel_keys = key_data.get("type") == "sdk"
        hsm = key_data.get("type") == "pkcs11"
        
        # Use the appropriate model based on device
        if hasattr(self.current_model, 'gen_keys'):
            device = self.wizard_view.landing_page.get_selected_device()
            try:
                self.current_model.gen_keys(
                    name,
                    password,
                    devel_keys,
                    hsm,
                    device=device.lower()
                )
            except Exception as e:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.critical(
                    self.wizard_view,
                    "Key Generation Failed",
                    str(e)
                )
                return
        else:
            print("Model does not support key generation")
    
    @pyqtSlot(dict)
    def _on_key_loaded(self, key_data):
        """Handle loading existing keys"""
        print(f"Loading keys with data: {key_data}")

        name = key_data.get("name")
        password = key_data.get("password")
        hsm = key_data.get("type") == "pkcs11"

        # Use the appropriate model based on device
        if hasattr(self.current_model, 'load_existing_key'):
            device = self.wizard_view.landing_page.get_selected_device()
            self.current_model.load_existing_key(
                name,
                password,
                device=device.lower(),
                hsm=hsm
            )
        else:
            print("Model does not support key loading")
    
    @pyqtSlot(dict)
    def _on_f29_development_session_set(self, session_data):
        """Handle F29 development session setup"""
        print(f"Setting up F29 development session with data: {session_data}")

        smpk_algo = session_data.get("smpk_algo", "rsa4k")
        bmpk_algo = session_data.get("bmpk_algo", "rsa4k")

        # Create/recreate the Development session with the specified algorithms
        # so it's ready for signing binaries without requiring cert gen first
        from apps.spt.f29_spt import create_development_session
        try:
            create_development_session(smpk_algo, bmpk_algo)
            self.f29_model.development_session_checkbox = True
            self.f29_model.smpk = smpk_algo
            self.f29_model.bmpk = bmpk_algo
        except Exception as e:
            print(f"WARNING: Could not create Development session: {e}")
    
    @pyqtSlot(dict)
    def _on_certificate_request(self, cert_data):
        """Handle certificate generation request"""
        print(f"Generating certificate with data: {cert_data}")
        
        # Check if this is for F29H85x
        if cert_data.get('device', '').lower() == 'f29h85x':
            self._handle_f29_certificate(cert_data)
        else:
            self._handle_standard_certificate(cert_data)
    
    def _handle_standard_certificate(self, cert_data):
        """Handle standard certificate generation"""
        # Map certificate parameters to model's expected format
        if hasattr(self.key_cert_model, 'generate_certificate'):
            # Extract parameters from cert_data
            msv = cert_data.get('msv')

            # Build mpk_flags / mek_flags from individual checkbox keys
            _MPK_MAP = {
                "mpk_write_protect": "wp",
                "mpk_read_protect": "rp",
                "mpk_override": "ovrd",
                "mpk_active": "active",
            }
            _MEK_MAP = {
                "mek_write_protect": "wp",
                "mek_read_protect": "rp",
                "mek_override": "ovrd",
                "mek_active": "active",
            }
            mpk_flags = [v for k, v in _MPK_MAP.items() if cert_data.get(k)]
            mek_flags = [v for k, v in _MEK_MAP.items() if cert_data.get(k)]

            flags = []
            flags.extend(mpk_flags)
            flags.extend(mek_flags)
            
            # Build parameters dictionary
            params = {
                'msv': msv,
                'flags': flags,
                'output_dir_path': cert_data.get('output_dir_path'),
                'pub_key_path': cert_data.get('pub_key_path'),
                'is_multishot': cert_data.get('is_multishot', False),
                'device': self.wizard_view.landing_page.get_selected_device().lower()
            }
            
            # Call model to generate certificate
            self.key_cert_model.generate_certificate(**params)
        else:
            print("Model does not support standard certificate generation")
    
    def _handle_f29_certificate(self, cert_data):
        """Handle F29H85x certificate generation"""
        # Map F29-specific parameters to model
        if hasattr(self.f29_model, 'generate_certificate'):
            # Set all required properties on the model
            self.f29_model.device = 'f29h85x'
            self.f29_model.ti_fek_public_pem = cert_data.get('pub_key_path')
            self.f29_model.msv = cert_data.get('msv')
            self.f29_model.sr_sbl = cert_data.get('sr_sbl')
            self.f29_model.sr_hsmRT = cert_data.get('sr_hsmRT')
            self.f29_model.sr_app = cert_data.get('sr_app')
            self.f29_model.sr_ssu = cert_data.get('sr_ssu')
            self.f29_model.keycnt = cert_data.get('keycnt')
            self.f29_model.keyrev = cert_data.get('keyrev')
            self.f29_model.devSrVer = cert_data.get('dev_sr_ver')
            self.f29_model.ext_otp = cert_data.get('ext_otp')
            self.f29_model.ext_otp_indx = cert_data.get('ext_otp_indx')
            self.f29_model.ext_otp_size = cert_data.get('ext_otp_size')
            self.f29_model.output_dir_path = cert_data.get('output_dir_path')
            
            # Set F29-specific flags
            for flag in cert_data.get('flags', []):
                if flag == 'msv_protect':
                    self.f29_model.msv_protect = True
                elif flag == 'b_protect':
                    self.f29_model.b_protect = True
                elif flag == 'bmek_protect':
                    self.f29_model.bmek_protect = True
                elif flag == 's_protect':
                    self.f29_model.s_protect = True
                elif flag == 'smek_protect':
                    self.f29_model.smek_protect = True
                elif flag == 'keycnt_protect':
                    self.f29_model.keycnt_protect = True
            
            # Set development session algorithms if applicable
            key_type = self.wizard_view.landing_page.get_selected_key_type()
            key_data = self.wizard_view.landing_page.get_key_data()
            if key_type == "f29_development" and key_data:
                self.f29_model.smpk = cert_data.get("smpk_signing_algorithm", key_data.get("smpk_algo", "secp256r1"))
                self.f29_model.bmpk = cert_data.get("bmpk_signing_algorithm", key_data.get("bmpk_algo", "secp384r1"))
                self.f29_model.development_session_checkbox = True
            else:
                # For non-development sessions, set these from the landing page data
                self.f29_model.sessionName = self.wizard_view.landing_page.get_session_name()
                self.f29_model.sessionPassword = self.wizard_view.landing_page.get_session_password()
                self.f29_model.development_session_checkbox = False
                self.f29_model.hsm = (key_type == "pkcs11")

            # Call generate_certificate on the model
            try:
                self.f29_model.generate_certificate()
            except (Exception, SystemExit) as e:
                self.wizard_view._show_error(f"Certificate generation failed:\n{str(e)}")
        else:
            print("F29 model does not support certificate generation")
    
    @pyqtSlot(str, dict)  
    def _on_device_detection_requested(self, boot_mode, connection_info):
        """Handle device detection request"""
        print(f"Detecting device with boot mode: {boot_mode}, connection info: {connection_info}")
        
        # Parse connection info
        if boot_mode == "UART":
            # TODO: Implement actual detection via UART
            serial_port = connection_info.get("port")
            if serial_port and hasattr(self.f29_model, 'get_soc_id'):
                try:
                    self.f29_model.get_soc_id(serial_port)
                    # Device type would be returned by the model
                    return "f29h85x", "HSFS"  # Dummy result
                except Exception as e:
                    print(f"Error during UART detection: {str(e)}")
        
        elif boot_mode == "JTAG":
            # JTAG detection is handled by JtagDetectionThread in config_page.py
            # which calls run_get_device_type_jtag() from f29_spt module
            pass

        # Return default values - actual detection is handled by UI threads
        return None, None
    
    @pyqtSlot(dict)
    def _on_convert_requested(self, provisioning_data):
        """Handle device conversion/provisioning request"""
        print(f"Converting device with data: {provisioning_data}")
        
        prov_type = provisioning_data.get('type', '')
        success = False
        message = ""
        
        try:
            if prov_type == 'f29h85x_uart':
                success, message = self._handle_f29_uart_conversion(provisioning_data)
            elif prov_type == 'f29h85x_jtag':
                success, message = self._handle_f29_jtag_conversion(provisioning_data)
            elif prov_type == 'standard':
                success, message = self._handle_standard_provision(provisioning_data)
            elif prov_type == 'standard_code':
                success, message = self._handle_standard_code_provision(provisioning_data)
            elif prov_type == 'f29h85x_uart_code':
                success, message = self._handle_f29_uart_code_provision(provisioning_data)
            elif prov_type == 'f29h85x_jtag_code':
                success, message = self._handle_f29_jtag_code_provision(provisioning_data)
            else:
                success = False
                message = f"Unknown provisioning type: {prov_type}"
                print(message)
        except Exception as e:
            success = False
            message = f"Error during {prov_type} operation: {str(e)}"
            print(f"Exception in conversion/provisioning: {message}")
        
        # Emit the result signal for the UI to use
        self.operation_result.emit(success, message)
        
        # Also return the result for direct use
        return success, message
    
    def _handle_f29_uart_conversion(self, provisioning_data):
        """Handle F29H85x conversion via UART"""
        if hasattr(self.f29_model, 'convert_device'):
            # Set the model properties from provisioning data
            self.f29_model.boot_mode = "UART"
            self.f29_model.flash_kernel = provisioning_data.get('flash_kernel')
            self.f29_model.otp_keywriter_binary = provisioning_data.get('otp_keywriter')
            self.f29_model.certificate = provisioning_data.get('certificate')
            
            # Get connection info
            conn_info = provisioning_data.get('connection_info', {})
            self.f29_model.serial_port = conn_info.get('port')
            
            # Call the model to convert the device and get result
            success, message = self.f29_model.convert_device()
            
            # Update status based on result
            if success:
                print(f"UART conversion succeeded: {message}")
                # After conversion, the device state changes to HSKP
                # Emit signal to notify the wizard view
                self.device_state_changed.emit("HSKP")
                # Return success message to display to user
                return True, message
            else:
                print(f"UART conversion failed: {message}")
                # Return error message to display to user
                return False, message
        else:
            error_msg = "F29 model does not support UART conversion"
            print(error_msg)
            return False, error_msg
    
    def _handle_f29_jtag_conversion(self, provisioning_data):
        """Handle F29H85x conversion via JTAG"""
        if hasattr(self.f29_model, 'convert_device'):
            # Set the model properties from provisioning data
            self.f29_model.boot_mode = "JTAG"
            self.f29_model.flash_kernel = provisioning_data.get('flash_kernel')
            self.f29_model.otp_keywriter_binary = provisioning_data.get('otp_keywriter')
            self.f29_model.certificate = provisioning_data.get('certificate')

            # Get connection info
            conn_info = provisioning_data.get('connection_info', {})
            self.f29_model.ccs_path = conn_info.get('ccs_path')

            # Check for custom target configuration file
            target_config_path = conn_info.get('target_config_path')

            # Get target configuration file from landing page if available
            if not target_config_path and hasattr(self.wizard_view, 'landing_page'):
                target_config_path = self.wizard_view.landing_page.get_target_config_path()

            # We'll include the target_config_path in the parameters passed to the provisioning worker
            # rather than modifying the model directly, as the worker handles the file copying

            # Call the model to convert the device and get result
            from apps.qtgui.services.provisioning_worker import stream_provisioning_output

            params = {
                'otp_kw_bin': self.f29_model.otp_keywriter_binary,
                'certificate': self.f29_model.certificate,
                'jtag_kernel': self.f29_model.flash_kernel,
                'ccs_path': self.f29_model.ccs_path,
                'verbose': True,
                'target_config_path': target_config_path
            }

            # Start provisioning in a worker thread
            result = {'success': False, 'message': ''}

            def on_result(success, message):
                result['success'] = success
                result['message'] = message

                # Update status based on result
                if success:
                    print(f"JTAG conversion succeeded: {message}")
                    # After conversion, the device state changes to HSKP
                    # Emit signal to notify the wizard view
                    self.device_state_changed.emit("HSKP")
                else:
                    print(f"JTAG conversion failed: {message}")

            # Start the worker and wait for completion
            worker = stream_provisioning_output('jtag_keyprov', params, result_callback=on_result)

            # Return result (worker will continue in background)
            return result['success'], result['message']
        else:
            error_msg = "F29 model does not support JTAG conversion"
            print(error_msg)
            return False, error_msg
    
    def _handle_standard_provision(self, provisioning_data):
        """Handle standard device provisioning"""
        # TODO: Implement actual standard device provisioning
        device = provisioning_data.get('device')
        firmware = provisioning_data.get('firmware')
        certificate = provisioning_data.get('certificate')
        
        print(f"Standard provisioning for {device} with firmware {firmware} and certificate {certificate}")
        # This is a placeholder since we don't have a model implementation yet
        # Once implemented, this should call the appropriate model method
        
        # For now, just return success
        return True, "Standard provisioning placeholder successful"
        
    def _handle_standard_code_provision(self, provisioning_data):
        """Handle standard device code provisioning"""
        # TODO: Implement actual standard device code provisioning
        device = provisioning_data.get('device')
        firmware = provisioning_data.get('firmware')
        certificate = provisioning_data.get('certificate')
        
        print(f"Standard code provisioning for {device} with code {firmware} and certificate {certificate}")
        # This is a placeholder since we don't have a model implementation yet
        # Once implemented, this should call the appropriate model method
        
        # For now, just return success
        return True, "Standard code provisioning placeholder successful"
        
    def _handle_f29_uart_code_provision(self, provisioning_data):
        """Handle F29H85x code provisioning via UART"""
        if hasattr(self.f29_model, 'provision_code'):
            # Extract all the required parameters from provisioning_data
            uart_kernel = provisioning_data.get('uart_kernel')
            hsm_image = provisioning_data.get('hsm_image')
            hsm_cpu_code = provisioning_data.get('hsm_cpu_code')
            c29_cpu_code = provisioning_data.get('c29_cpu_code')
            seccfg = provisioning_data.get('seccfg')
            device = provisioning_data.get('device')
            
            # Get connection info
            conn_info = provisioning_data.get('connection_info', {})
            port = conn_info.get('port')
            
            # Call the model to provision code with all required parameters
            # Matches f29_spt.py run_code_provisioning_uart parameters
            success, message = self.f29_model.provision_code(
                uart_kernel=uart_kernel,
                hsm_image=hsm_image,
                hsm_cpu_code=hsm_cpu_code,
                c29_cpu_code=c29_cpu_code,
                seccfg=seccfg,
                device=device,
                port=port
            )
            
            # Update status based on result
            if success:
                print(f"UART code provisioning succeeded: {message}")
                return True, message
            else:
                print(f"UART code provisioning failed: {message}")
                return False, message
        else:
            error_msg = "F29 model does not support code provisioning via UART"
            print(error_msg)
            return False, error_msg
    
    def _handle_f29_jtag_code_provision(self, provisioning_data):
        """Handle F29H85x code provisioning via JTAG"""
        if hasattr(self.f29_model, 'provision_code'):
            # Extract all the required parameters from provisioning_data
            hsm_image = provisioning_data.get('hsm_image')
            jtag_kernel = provisioning_data.get('jtag_kernel')
            hsm_cpu_code = provisioning_data.get('hsm_cpu_code')
            c29_cpu_code = provisioning_data.get('c29_cpu_code')
            seccfg = provisioning_data.get('seccfg')

            # Get connection info
            conn_info = provisioning_data.get('connection_info', {})
            ccs_path = conn_info.get('ccs_path')
            verbose = conn_info.get('verbose', True)
            target_config_path = conn_info.get('target_config_path')

            # Get target configuration file from landing page if available
            if not target_config_path and hasattr(self.wizard_view, 'landing_page'):
                target_config_path = self.wizard_view.landing_page.get_target_config_path()

            # Use provisioning worker to handle target configuration replacement
            from apps.qtgui.services.provisioning_worker import stream_provisioning_output

            params = {
                'hsm_image': hsm_image,
                'jtag_kernel': jtag_kernel,
                'hsm_cpu_code': hsm_cpu_code,
                'c29_cpu_code': c29_cpu_code,
                'seccfg': seccfg,
                'ccs_path': ccs_path,
                'verbose': verbose,
                'target_config_path': target_config_path
            }

            # Start provisioning in a worker thread
            result = {'success': False, 'message': ''}

            def on_result(success, message):
                result['success'] = success
                result['message'] = message

                # Update status based on result
                if success:
                    print(f"JTAG code provisioning succeeded: {message}")
                else:
                    print(f"JTAG code provisioning failed: {message}")

            # Start the worker and wait for completion
            worker = stream_provisioning_output('jtag_codeprov', params, result_callback=on_result)

            # Return result (worker will continue in background)
            return result['success'], result['message']
        else:
            error_msg = "F29 model does not support code provisioning via JTAG"
            print(error_msg)
            return False, error_msg
            
    def _on_proceed_to_code_provisioning(self, session_data):
        """Handle request to proceed to code provisioning page after conversion"""
        print("Proceeding to code provisioning with session data:", session_data)
        
        # Update session data with HSKP device state
        session_data['device_state'] = 'HSKP'
        
        # Notify the wizard view to transition to the code provisioning page
        self.device_state_changed.emit("HSKP")
        
    def get_serial_ports(self):
        """
        Retrieve all available serial ports, filtering and formatting for cross-platform compatibility

        Returns:
            list: A list of available serial port names
        """
        ports = serial.tools.list_ports.comports()
        return [format_serial_port_name(port.device) for port in ports]
        
    @pyqtSlot()
    def _on_binary_signing_requested(self):
        """Handle batch binary signing request
        
        Returns:
            tuple: (bool, str) Success flag and output message
        """
        print("DEBUG: Batch binary signing requested")
        
        # Ensure we have the F29 model initialized
        if not hasattr(self, 'f29_model') or not self.f29_model:
            error_msg = "F29 model not initialized"
            print(f"ERROR: {error_msg}")
            self.operation_result.emit(False, error_msg)
            return False, error_msg
        
        try:
            # Get session information
            landing_page = self.wizard_view.landing_page
            key_type = landing_page.get_selected_key_type()
            key_data = landing_page.get_key_data()
            
            # Get CCS path from config page
            ccs_path = None
            if hasattr(self.wizard_view.config_page, 'ccs_path'):
                ccs_path = self.wizard_view.config_page.ccs_path
                
            # Ensure session info is properly set in the model
            if key_type == "f29_development":
                # For development session
                self.f29_model.development_session_checkbox = True
                self.f29_model.sessionName = "Development"
                self.f29_model.sessionPassword = "develop123#"
                if key_data:
                    self.f29_model.smpk = key_data.get("smpk_algo", "rsa4k")
                    self.f29_model.bmpk = key_data.get("bmpk_algo", "rsa4k")
            elif key_type in ["new", "existing"] and key_data:
                # For regular sessions
                self.f29_model.development_session_checkbox = False
                self.f29_model.sessionName = key_data.get("name", "")
                self.f29_model.sessionPassword = key_data.get("password", "")
                
            # Print session info for debugging
            print(f"DEBUG: Using session: {self.f29_model.sessionName}")
            if self.f29_model.development_session_checkbox:
                print(f"DEBUG: Development session with SMPK: {self.f29_model.smpk}, BMPK: {self.f29_model.bmpk}")
                
            # Call the model's sign_all_prebuilt_binaries method
            print("Calling sign_all_prebuilt_binaries with CCS path:", ccs_path)
            success, message = self.f29_model.sign_all_prebuilt_binaries(ccs_path=ccs_path)
            
            # Log and return result
            if success:
                print(f"DEBUG: Batch binary signing completed with some successes")
                # Emit operation result signal for UI update
                self.operation_result.emit(True, message)
            else:
                print(f"ERROR: Batch binary signing failed completely")
                # Emit operation result signal for UI update
                self.operation_result.emit(False, message)
                
            # Call the config page's handler for batch signing result
            if hasattr(self.wizard_view.config_page, '_on_batch_signing_result'):
                self.wizard_view.config_page._on_batch_signing_result(success, message)
                
            return success, message
            
        except Exception as e:
            error_msg = f"Exception during batch binary signing: {str(e)}"
            print(f"ERROR: {error_msg}")
            # Emit operation result signal for UI update
            self.operation_result.emit(False, error_msg)
            # Call the config page's handler for batch signing result
            if hasattr(self.wizard_view.config_page, '_on_batch_signing_result'):
                self.wizard_view.config_page._on_batch_signing_result(False, error_msg)
            return False, error_msg

    @pyqtSlot(dict)
    def _on_seccfg_cert_requested(self, seccfg_params):
        """Handle Sec-Cfg certificate generation request

        Args:
            seccfg_params (dict): Parameters for Sec-Cfg certificate generation

        Returns:
            tuple: (bool, str) Success flag and output message
        """
        print(f"Generating Sec-Cfg certificate with params: {seccfg_params}")

        try:
            # Validate CCS path
            if not seccfg_params.get("ccs_path"):
                error_msg = "CCS path is required for Sec-Cfg signing"
                print(f"ERROR: {error_msg}")
                self.operation_result.emit(False, error_msg)
                return False, error_msg

            # Convert output_path to a Path object if it's a string
            from pathlib import Path
            if "output_path" in seccfg_params and isinstance(seccfg_params["output_path"], str):
                seccfg_params["output_path"] = Path(seccfg_params["output_path"])

            # Use the sign_sec_cfg_wrapper method from the F29H85xDeviceModel
            success, message = self.f29_model.sign_sec_cfg_wrapper(**seccfg_params)

            # Emit result signal for UI update
            self.operation_result.emit(success, message)

            return success, message
        except Exception as e:
            error_msg = f"Error generating Sec-Cfg certificate: {str(e)}"
            print(f"ERROR: {error_msg}")
            self.operation_result.emit(False, error_msg)
            return False, error_msg

    def sign_f29h85x_specific_binaries(self, key_type, key_data, ccs_path, target_binaries=None):
        """Sign specific F29H85x binaries
        
        This method signs specific F29H85x binaries, particularly the RAM based SBL and HSM CP Image.
        It is called when transitioning from landing page to config page for F29H85x devices.
        
        Args:
            key_type (str): Type of key being used (new, existing, f29_development)
            key_data (dict): Key data from the landing page
            ccs_path (str): Path to CCS installation
            target_binaries (list): List of binary filenames to sign, defaults to RAM based SBL and HSM CP Image
            
        Returns:
            tuple: (bool, str) Success flag and output message
        """
        print(f"DEBUG: Signing specific F29H85x binaries: {target_binaries}")
        print("DEBUG: F29H85x specific binary signing requested")
        
        # Set default target binaries if not provided
        if not target_binaries:
            target_binaries = ["ram_based_uart_sbl.bin"]
        
        # Ensure we have the F29 model initialized
        if not hasattr(self, 'f29_model') or not self.f29_model:
            error_msg = "F29 model not initialized"
            print(f"ERROR: {error_msg}")
            return False, error_msg
        
        try:
            # Configure the F29 model based on key type and key data
            if key_type == "f29_development":
                # For development session
                self.f29_model.development_session_checkbox = True
                self.f29_model.sessionName = "Development"
                self.f29_model.sessionPassword = "develop123#"
                if key_data:
                    self.f29_model.smpk = key_data.get("smpk_algo", "rsa4k")
                    self.f29_model.bmpk = key_data.get("bmpk_algo", "rsa4k")
            elif key_type in ["new", "existing", "pkcs11"] and key_data:
                # For regular sessions
                self.f29_model.development_session_checkbox = False
                self.f29_model.sessionName = key_data.get("name", "")
                self.f29_model.sessionPassword = key_data.get("password", "")
            else:
                error_msg = "Invalid key type or missing key data"
                print(f"ERROR: {error_msg}")
                return False, error_msg

            # Enable HSM signing for PKCS11 sessions (private key on device, never extractable)
            hsm_flag = (key_type == "pkcs11")

            # Print session info for debugging
            print(f"DEBUG: Using session: {self.f29_model.sessionName}")
            if self.f29_model.development_session_checkbox:
                print(f"DEBUG: Development session with SMPK: {self.f29_model.smpk}, BMPK: {self.f29_model.bmpk}")

            # Safety net: if session name is "Development" but session is missing or
            # lacks smek (e.g. loaded via "Use existing" without cert gen), recreate it.
            if self.f29_model.sessionName == "Development":
                from tisecprov.session import SecureSession
                from apps.spt.f29_spt import create_development_session
                needs_init = False
                with SecureSession() as _s:
                    if not _s.does_session_exist("Development"):
                        needs_init = True
                    else:
                        _s.open_session("Development", self.f29_model.sessionPassword)
                        try:
                            _s.get_key("smek")
                        except (ValueError, Exception):
                            needs_init = True
                if needs_init:
                    create_development_session(
                        self.f29_model.smpk or "rsa4k",
                        self.f29_model.bmpk or "rsa4k"
                    )

            enc_key_path = None
            smek_tmp_path = None

            if key_type != "f29_development":
                from tisecprov.session import SecureSession
                from tisecprov.crypto_selector import get_crypto_backend
                secure_session = SecureSession(use_hsm=hsm_flag)
                with secure_session as s:
                    s.open_session(self.f29_model.sessionName, self.f29_model.sessionPassword)
                    crypto_backend = get_crypto_backend(use_hsm=hsm_flag)
                    keys = s.get_manufacturer_keys(crypto_backend)
                    smek_bytes = keys[0].get_symmetric_key()
                smek_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".key")
                smek_tmp.write(smek_bytes)
                smek_tmp.close()
                smek_tmp_path = smek_tmp.name
                enc_key_path = smek_tmp_path

            # Get prebuilt images directory
            prebuilt_images_dir = get_device_prebuilt_dir(
                self.f29_model.device_name,
                self.f29_model.device_family
            )

            print(f"DEBUG: Using prebuilt images directory: {prebuilt_images_dir}")

            # Default to the static dev key if no session SMEK was extracted
            if enc_key_path is None:
                enc_key_path = str(prebuilt_images_dir / "mcu_custMek.key")

            # Check if directory exists
            if not prebuilt_images_dir.exists():
                error_msg = f"Prebuilt images directory not found: {prebuilt_images_dir}"
                print(f"ERROR: {error_msg}")
                return False, error_msg
                
            # Binary configurations - target the specific binaries needed
            binary_configs = {
                "ram_based_uart_sbl.temp.bin": {
                    "core": "C29",
                    "boot": "RAM",
                    "loadaddr": "0x200E1000",
                    "keyrev": "1",
                    "swrv": "1",
                    "debug": "DBG_SOC_DEFAULT",
                    "img_integ": True,
                    "hsm": hsm_flag,
                },
                "tifs_f29h85x_hs_se_code_provisioning.release.bin": {
                    "core": "HSM",
                    "boot": "RAM",
                    "loadaddr": "0x00000000",
                    "keyrev": "1",
                    "swrv": "1",
                    "debug": "DBG_SOC_DEFAULT",
                    "tifs_enc": True,
                    "enc_key": enc_key_path,
                    "hsm": hsm_flag,
                    "kd_salt": str(prebuilt_images_dir / "kd_salt.txt")
                }
            }
            
            # Results tracking
            results = []
            success_count = 0
            fail_count = 0
            
            # Compute project bin dir once for binaries that live there (not in the addon)
            from common.platform_utils import get_project_root
            from common.device_utils import infer_device_family
            _family = infer_device_family(self.f29_model.device_name)
            project_bin = (
                Path(get_project_root())
                / "host" / "bin" / _family / self.f29_model.device_name
            )

            # Process each target binary
            for binary_name in target_binaries:
                # Skip OTP keywriter files - they should not be signed
                if "otp_kw" in binary_name.lower():
                    print(f"Skipping OTP keywriter file: {binary_name}")
                    continue

                # ram_based_uart_sbl.temp.bin is project-bundled; everything else comes from the addon
                if binary_name == "ram_based_uart_sbl.temp.bin":
                    binary_file = project_bin / "ram_based_uart_sbl.temp.bin"
                else:
                    binary_file = prebuilt_images_dir / binary_name

                # Check if binary exists
                if not binary_file.exists():
                    error_msg = f"Binary file not found: {binary_file}"
                    print(f"ERROR: {error_msg}")
                    results.append(f"✗ {binary_name}: File not found")
                    fail_count += 1
                    continue
                    
                # Get binary configuration
                if binary_name in binary_configs:
                    config = binary_configs[binary_name]
                else:
                    # Skip binary if configuration is not defined
                    error_msg = f"No configuration defined for binary: {binary_name}"
                    print(f"ERROR: {error_msg}")
                    results.append(f"✗ {binary_name}: {error_msg}")
                    fail_count += 1
                    continue
                    
                # Add CCS path if provided
                if ccs_path:
                    config["ccs_path"] = ccs_path
                    
                # Add binary file path - convert Path to string
                config["image"] = str(binary_file)
                config["input_format"] = "BIN"  # Always BIN for prebuilt binaries
                    
                try:
                    # Sign the binary
                    print(f"Signing {binary_name}...")
                    success, message = self.f29_model.sign_binary(**config)
                    
                    # Track result
                    if success:
                        # Rename signed output to drop "_temp" from the filename
                        if binary_name == "ram_based_uart_sbl.temp.bin":
                            from common.device_utils import get_device_output_dir
                            signed_dir = Path(get_device_output_dir(self.f29_model.device_name, "signedImages"))
                            src = signed_dir / "ram_based_uart_sbl.temp.cert.bin"
                            dst = signed_dir / "ram_based_uart_sbl.cert.bin"
                            if src.exists():
                                src.replace(dst)
                                print(f"Renamed {src.name} → {dst.name}")
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
                    
            # Clean up temporary SMEK file
            if smek_tmp_path and os.path.exists(smek_tmp_path):
                os.unlink(smek_tmp_path)

            # Compile final result message
            # Filter target_binaries to exclude OTP keywriter files for accurate count
            eligible_binaries = [b for b in target_binaries if "otp_kw" not in b.lower()]
            result_message = f"Signed {success_count} of {len(eligible_binaries)} binaries successfully.\n\n"
            result_message += "\n".join(results)
            
            # Overall success if at least one binary was signed successfully
            overall_success = success_count > 0
            return overall_success, result_message
                
        except Exception as e:
            # Clean up temporary SMEK file on error
            if smek_tmp_path and os.path.exists(smek_tmp_path):
                os.unlink(smek_tmp_path)
            error_msg = f"Exception during F29H85x specific binary signing: {str(e)}"
            print(f"ERROR: {error_msg}")
            return False, error_msg

    @pyqtSlot(dict)
    def _on_wizard_completed(self, wizard_data):
        """Generate CLI script when wizard finishes (non-fatal)."""
        try:
            from apps.qtgui.utils.cli_script_generator import generate_f29h85x_cli_script
            from apps.qtgui.models.F29H85xDeviceModel import PREBUILT_BINARY_CONFIGS as F29_BINARY_CONFIGS
            script_path = generate_f29h85x_cli_script(wizard_data, known_binary_configs=F29_BINARY_CONFIGS)
            print(f"CLI script saved: {script_path}")
        except Exception as e:
            print(f"Warning: Could not generate CLI script: {e}")