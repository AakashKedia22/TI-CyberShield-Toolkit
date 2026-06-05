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

import os
import sys
from tisecprov.session import SecureSession
from ...spt.genkeys import generate_keys
from ...spt.gencert import generate_certificate
from pathlib import Path
# Import F29 specific model
from .F29H85xDeviceModel import F29H85xDeviceModel


class KeyCertModel:
    def __init__(self):
        self.session = SecureSession()
        self.session_name = None
        self.session_password = None
        self.dkey = None
        self.hsm_option = False
        self.current_device = None
        self.using_development_session = False
        self.smpk_signing_algorithm = None
        self.bmpk_signing_algorithm = None

    def list_sessions(self):
        """Get list of existing sessions"""
        return self.session.list_sessions()

    def gen_keys(self, name, password, devel_keys=None, hsm=False, device=None):
        """Generate new keys"""
        try:
            print(f"DEBUG: Generating keys with parameters:")
            print(f"  - Session name: {name}")
            print(f"  - Development keys: {devel_keys}")
            print(f"  - HSM: {hsm}")
            print(f"  - Device: {device}")
            
            # Validate device and key type combinations
            if device and device.lower() == "f29h85x" and devel_keys:
                error_msg = "SDK dummy keys are not available for F29H85x devices"
                print(f"ERROR: {error_msg}")
                raise Exception(error_msg)
            
            # Store session information
            self.session_name = name
            self.session_password = password
            self.current_device = device  # Track current device
            self.using_development_session = False  # Reset development session flag
            
            if devel_keys not in ["v15", "v22"]:
                print(f"DEBUG: Invalid devel_keys value '{devel_keys}', setting to None")
                devel_keys = None
            self.dkey = devel_keys
            self.hsm_option = hsm
            
            # For F29H85x devices, we need to use F29-specific key generation
            if device and device.lower() == "f29h85x":
                print("DEBUG: Using F29-specific key generation")
                
                # Set up default key algorithms
                smpk_algo = "rsa4k"  # Default to RSA4K
                bmpk_algo = "rsa4k"  # Default to RSA4K
                
                # Handle F29 key generation with proper parameters
                if name == "Development":
                    # For development session, just store key types - don't create an actual session
                    self.using_development_session = True
                    self.smpk_signing_algorithm = smpk_algo
                    self.bmpk_signing_algorithm = bmpk_algo
                    print(f"DEBUG: Stored development session parameters with SMPK: {smpk_algo}, BMPK: {bmpk_algo}")
                else:
                    # For regular session, use standard generate_keys with F29 parameters
                    from ...spt.genkeys import generate_keys as f29_generate_keys
                    f29_generate_keys(name, password, use_hsm=hsm,
                                      smpk_signing_algorithm=smpk_algo,
                                      bmpk_signing_algorithm=bmpk_algo)
            else:
                # For all other devices, use the standard key generation
                from ...spt.genkeys import generate_keys
                print(f"DEBUG: Calling generate_keys with parameters: name={name}, devel={devel_keys}, use_hsm={hsm}")
                generate_keys(name, password, devel=devel_keys, use_hsm=hsm)
            
            print(f"DEBUG: Keys generated successfully for session: {name}")
            return True

        except Exception as e:
            print(f"ERROR: Failed to generate keys: {str(e)}")
            raise Exception(f"{str(e)}")

    def load_existing_key(self, name, password, device=None, hsm=False):
        """Load existing key session"""
        try:
            print(f"DEBUG: Loading existing key session: {name}")
            print(f"  - Device: {device}")

            # Check if this is a Development session for F29H85x
            if name == "Development" and device and device.lower() == "f29h85x":
                print("DEBUG: This is a Development session for F29H85x")

            # Check if this is a Development session for a non-F29H85x device
            if name == "Development" and device and device.lower() != "f29h85x":
                error_msg = "Development session is only valid for F29H85x devices"
                print(f"ERROR: {error_msg}")
                raise Exception(error_msg)

            # Simply store the session name and password for later use
            self.hsm_option = hsm
            self.dkey = None
            self.session_name = name
            self.session_password = password
            self.current_device = device  # Track current device
            self.using_development_session = (name == "Development" and device and device.lower() == "f29h85x")  
            
            # If this is the Development session for F29H85x, set the flag and additional parameters
            if self.using_development_session:
                print("DEBUG: Loaded F29H85x Development Session")
                # Set default signing algorithms - using RSA4K as default per request
                self.smpk_signing_algorithm = "rsa4k"  # Default to RSA4K
                self.bmpk_signing_algorithm = "rsa4k"  # Default to RSA4K
                
                # For Development session, we'll validate that it exists but not attempt to create it
                try:
                    from tisecprov.session import SecureSession
                    with SecureSession() as s:
                        if s.does_session_exist(name):
                            print(f"DEBUG: Development session exists, ready for use")
                        else:
                            print(f"DEBUG: Development session does not exist. Will be created when needed.")
                except Exception as session_error:
                    print(f"DEBUG: Could not verify session existence: {str(session_error)}")
            else:
                # For standard sessions, verify it exists
                try:
                    from tisecprov.session import SecureSession
                    with SecureSession() as s:
                        if s.does_session_exist(name):
                            print(f"DEBUG: Session '{name}' exists, ready for use")
                        else:
                            print(f"DEBUG: Session '{name}' does not exist. Please generate keys first.")
                            # We'll still store the name and password, but warn the user
                            print(f"WARNING: Session '{name}' not found but will be used if it exists when needed")
                except Exception as session_error:
                    print(f"DEBUG: Could not verify session existence: {str(session_error)}")
            
            print(f"DEBUG: Successfully stored key session credentials: {name}")
            return True
        except Exception as e:
            print(f"ERROR: Failed to load key: {str(e)}")
            raise Exception(f"Failed to load key: {str(e)}")


    def generate_certificate(
        self, msv, mpk_flags, mek_flags, output_dir_path, is_multishot, pub_key_path
    ):
        """Generate certificate with given parameters"""
        try:
            # Check if we're using a development session for F29H85x
            if self.using_development_session and self.current_device == "f29h85x":
                print(f"DEBUG: Redirecting to F29 Development Session certificate generation")
                # Build flags for F29
                flags = []
                if mpk_flags:
                    for flag in mpk_flags:
                        flags.append(flag)
                if mek_flags:
                    for flag in mek_flags:
                        flags.append(flag)
                        
                # Call F29 certificate generation with development session
                return self.generate_f29_certificate(
                    device="f29h85x",
                    msv=msv,
                    flags=flags,
                    output_dir_path=output_dir_path,
                    pub_key_path=pub_key_path,
                    dev_sr_ver="SR_20",  # Default
                    keycnt="2",  # Default from example
                    keyrev="1",  # Default from example
                    sr_sbl="1",  # Default from example
                    sr_hsmrt="1",  # Default from example 
                    sr_app="1",  # Default from example
                    sr_ssu="1",  # Default from example
                    ext_otp="0x80000001",  # Default from example
                    ext_otp_indx="0",  # Default from example
                    ext_otp_size="32",  # Default from example
                    smpk_signing_algorithm=self.smpk_signing_algorithm,
                    bmpk_signing_algorithm=self.bmpk_signing_algorithm
                )
            
            # Check if we have a session loaded (except for F29 development session)
            if not self.using_development_session and (not self.session_name or not self.session_password):
                error_msg = "No key session loaded. Please generate or load keys first."
                print(f"ERROR: {error_msg}")
                raise Exception(error_msg)
                
            # For AM62Px, J722S and other devices, use the standard flow
            print(f"DEBUG: Generating standard certificate with parameters:")
            print(f"  - Session: {self.session_name}")
            print(f"  - MSV: {msv}")
            print(f"  - MPK Flags: {mpk_flags}")
            print(f"  - MEK Flags: {mek_flags}")
            print(f"  - HSM: {self.hsm_option}")
            print(f"  - Output: {output_dir_path}")
            print(f"  - Multishot: {is_multishot}")
            print(f"  - TIFEK Path: {pub_key_path}")
            print(f"  - Device: {self.current_device if self.current_device else 'Not specified'}")
            
            # If we have a current device, add it to the command
            device_arg = ["--device", self.current_device] if self.current_device else []
            
            # Add device-specific handling
            if self.current_device:
                if self.current_device.lower() == "f29h85x":
                    # F29H85x without development session needs to use the regular flow
                    # but we'll add debug message to clarify
                    print(f"DEBUG: Using standard certificate flow for {self.current_device} with regular session")
                elif self.current_device.lower() in ["am62px", "j722s"]:
                    print(f"DEBUG: Using default SPT flow for {self.current_device}")
                    # For AM62Px and J722S, we would use subprocess to call spt with device parameter
                    # but for now we'll use the existing generate_certificate function
                
            # Use the standard certificate generation function
            return generate_certificate(
                session=self.session_name,
                password=self.session_password,
                msv=msv,
                mpk_flags=mpk_flags,
                mek_flags=mek_flags,
                use_hsm=self.hsm_option,
                output_dir_path=output_dir_path,
                multishot=is_multishot,
                tifek_pub_path=pub_key_path
            )
        except Exception as e:
            print(f"ERROR: Failed to generate certificate: {str(e)}")
            raise Exception(f"Failed to generate certificate: {str(e)}")
            
    def generate_f29_certificate(self, device, msv, flags, output_dir_path, pub_key_path,
                                dev_sr_ver, keycnt, keyrev, sr_sbl, sr_hsmrt, sr_app, sr_ssu, 
                                ext_otp, ext_otp_indx, ext_otp_size, smpk_signing_algorithm,
                                bmpk_signing_algorithm):
        """Generate F29H85x-specific certificate using the F29H85xDeviceModel"""
        try:
            print(f"DEBUG: Generating F29H85x certificate using F29H85xDeviceModel")
            
            # Create an instance of the F29 specific model
            f29_model = F29H85xDeviceModel()
            
            # Set up the model with all the required parameters
            f29_model.device = device
            f29_model.ti_fek_public_pem = str(pub_key_path)
            f29_model.msv = msv
            
            # Set the software revision values
            f29_model.sr_sbl = str(sr_sbl)
            f29_model.sr_hsmRT = str(sr_hsmrt)
            f29_model.sr_app = str(sr_app)
            f29_model.sr_ssu = str(sr_ssu)
            
            # Set key information
            f29_model.keycnt = str(keycnt)
            f29_model.keyrev = str(keyrev)
            f29_model.devSrVer = str(dev_sr_ver)
            
            # Set extended OTP information
            f29_model.ext_otp = str(ext_otp)
            f29_model.ext_otp_indx = str(ext_otp_indx)
            f29_model.ext_otp_size = str(ext_otp_size)
            
            # Set session information and development flag
            f29_model.sessionName = self.session_name
            f29_model.sessionPassword = self.session_password
            f29_model.development_session_checkbox = self.using_development_session
            
            # Set signing algorithms if we're in development mode
            if self.using_development_session:
                f29_model.smpk = smpk_signing_algorithm
                f29_model.bmpk = bmpk_signing_algorithm
            
            # Set protect flags based on the flags array
            self._set_f29_protect_flags(f29_model, flags)
            
            # Print debugging information
            print(f"DEBUG: F29 model configured with:")
            print(f"  - Device: {f29_model.device}")
            print(f"  - MSV: {f29_model.msv}")
            print(f"  - Using development session: {f29_model.development_session_checkbox}")
            
            # Call the generate_certificate method on the F29 model
            print("DEBUG: Calling f29_model.generate_certificate()")
            f29_model.generate_certificate()
            
            print("DEBUG: F29 certificate generation completed successfully")
            return True
            
        except Exception as e:
            error_msg = f"Failed to generate F29 certificate: {str(e)}"
            print(f"ERROR: {error_msg}")
            raise Exception(error_msg)
            
    def _set_f29_protect_flags(self, f29_model, flags):
        """Set the protect flags on the F29 model based on the flags array"""
        # Default all flags to False
        f29_model.msv_protect = False
        f29_model.s_protect = False
        f29_model.smek_protect = False
        f29_model.b_protect = False
        f29_model.bmek_protect = False
        f29_model.keycnt_protect = False
        
        # Set flags based on the array
        for flag in flags:
            if flag == "msv_protect":
                f29_model.msv_protect = True
            elif flag == "s_protect":
                f29_model.s_protect = True
            elif flag == "smek_protect":
                f29_model.smek_protect = True
            elif flag == "b_protect":
                f29_model.b_protect = True
            elif flag == "bmek_protect":
                f29_model.bmek_protect = True
            elif flag == "keycnt_protect":
                f29_model.keycnt_protect = True
            
    def setup_f29_development_session(self, smpk_algo, bmpk_algo):
        """Set up F29H85x Development Session"""
        try:
            print(f"DEBUG: Setting up F29 Development Session with SMPK: {smpk_algo}, BMPK: {bmpk_algo}")
            
            # Verify device type is F29H85x
            if not self.current_device or self.current_device.lower() != "f29h85x":
                error_msg = "F29 Development Session is only available for F29H85x devices"
                print(f"ERROR: {error_msg}")
                raise Exception(error_msg)
            
            # Delete previous Development session if it exists
            try:
                from tisecprov.session import SecureSession
                with SecureSession() as s:
                    if s.does_session_exist("Development"):
                        print("DEBUG: Deleting previous Development session")
                        s.delete_session("Development")
                        print("DEBUG: Previous Development session deleted")
            except Exception as delete_error:
                print(f"WARNING: Error while trying to delete previous Development session: {str(delete_error)}")
            
            # Just store the key types and development mode flag
            # We don't need to create an actual session for development mode
            self.session_name = "Development"
            self.session_password = ""  # Not needed for development mode
            self.using_development_session = True
            self.smpk_signing_algorithm = smpk_algo
            self.bmpk_signing_algorithm = bmpk_algo
            
            # Record device type
            self.current_device = "f29h85x"
            
            print("DEBUG: F29 Development Session parameters stored successfully")
            return True
            
        except Exception as e:
            error_msg = f"Failed to set up F29 Development Session parameters: {str(e)}"
            print(f"ERROR: {error_msg}")
            raise Exception(error_msg)
