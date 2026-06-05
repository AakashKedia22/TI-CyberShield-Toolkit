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
Texas Instruments Cybershield Toolkit Wizard Launcher

This script provides a simple way to launch the Cybershield Toolkit wizard
interface from the command line. It sets up the Python path correctly and handles
any initialization needed.
"""

import os
import sys
import pathlib
from PyQt5.QtWidgets import QWidget, QVBoxLayout

def main():
    """Main entry point for the wizard launcher"""
    # Get the root directory of the repository
    repo_root = pathlib.Path(__file__).parent.absolute()
    
    # Add the repository root to the Python path
    sys.path.append(str(repo_root))
    
    # Print a welcome message
    print("Starting TI Cybershield Toolkit Wizard...")
    
    try:
        # First try to run with the actual controller
        try:
            from host.src.apps.qtgui.main_wizard import main as wizard_main
            wizard_main()
        except ImportError as e:
            print(f"Could not import main wizard module: {str(e)}")
            print("Trying fallback to test UI...")
            
            # If that fails, try the test UI
            try:
                from test_updated_ui import main as test_ui_main
                test_ui_main()
            except ImportError:
                print("Could not import test_updated_ui, trying alternative imports...")
            
    except Exception as e:
        print(f"Error launching wizard: {str(e)}")
        
        # If all else fails, try to run the simplest UI test
        try:
            print("Trying minimal UI test...")
            try:
                from test_key_selection import main as test_key_main
                test_key_main()
            except ImportError:
                print("Could not import test_key_selection either.")
                print("\nFalling back to direct wizard view launch...")
                from PyQt5.QtWidgets import QApplication
                from host.src.apps.qtgui.views.wizard_view import WizardView
                from host.src.apps.qtgui.controllers.wizard_controller import WizardController
                
                app = QApplication([])
                app.setApplicationName("CyberShield Toolkit")
                window = QWidget()
                window.setWindowTitle("TI Cybershield Toolkit")
                
                # Create wizard view
                wizard_view = WizardView()
                
                # Create wizard controller
                controller = WizardController(wizard_view)
                
                # Set as central widget in a simple layout
                layout = QVBoxLayout(window)
                layout.addWidget(wizard_view)
                
                # Set window properties
                window.setMinimumSize(1200, 800)  
                window.resize(1200, 900)
                window.show()
                
                sys.exit(app.exec_())
        except Exception as e2:
            print(f"Fatal error launching any UI: {str(e2)}")
            sys.exit(1)

if __name__ == "__main__":
    main()