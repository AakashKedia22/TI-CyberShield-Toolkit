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
Provisioning results dialog component for displaying the parsed log data.
"""

from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QFormLayout,
    QGridLayout,
    QScrollArea,
    QProgressBar,
    QWidget,
    QMessageBox
)
from PyQt5.QtCore import Qt
import os
import subprocess
from apps.qtgui.utils.platform_utils import open_file
from apps.qtgui.utils.log_parser import LogData

class ProvisioningResultsDialog(QDialog):
    """Dialog for displaying detailed results from provisioning operations."""
    
    def __init__(self, parent=None, log_data=None, log_file_path=None):
        """Initialize the dialog.
        
        Args:
            parent: Parent widget
            log_data: Dictionary or LogData object containing parsed log data
            log_file_path: Path to the log file for viewing
        """
        super().__init__(parent)
        
        # Handle the case where log_data could be either a dictionary or LogData object
        if isinstance(log_data, LogData):
            self.log_data = log_data.to_dict()
        else:
            self.log_data = log_data
            
        self.log_file_path = log_file_path
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI components."""
        # Set dialog properties
        self.setWindowTitle("Provisioning Results")
        self.setMinimumWidth(700)
        self.setMinimumHeight(500)
        
        # Create layout
        layout = QVBoxLayout(self)
        
        # Add title
        title_label = QLabel("Provisioning Details")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #CC0000;")
        layout.addWidget(title_label)
        
        if not self.log_data:
            # Show message if no data available
            no_data_label = QLabel("No provisioning data available")
            no_data_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(no_data_label)
        else:
            # Create scrollable area for results
            scroll_area = QWidget()
            scroll_layout = QVBoxLayout(scroll_area)
            
            # Add device information section
            self._add_device_info_section(scroll_layout)
            
            # Add key provisioning section
            self._add_key_provisioning_section(scroll_layout)
            
            # Add code provisioning section
            self._add_code_provisioning_section(scroll_layout)
            
            # Add errors section
            self._add_errors_section(scroll_layout)
            
            # Create a scroll area to contain all the results
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setWidget(scroll_area)
            layout.addWidget(scroll)
        
        # Add buttons at the bottom
        button_layout = QHBoxLayout()
        
        # View log file button
        if self.log_file_path and os.path.exists(self.log_file_path):
            view_log_button = QPushButton("View Full Log File")
            view_log_button.clicked.connect(self._open_log_file)
            button_layout.addWidget(view_log_button)
        
        # Add spacer to push buttons apart
        button_layout.addStretch()
        
        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)
        
        # Add button layout to main layout
        layout.addLayout(button_layout)
    
    def _add_device_info_section(self, parent_layout):
        """Add device information section to the dialog.
        
        Args:
            parent_layout: Layout to add the section to
        """
        device_info = self.log_data.get('device_info', {})
        if not device_info:
            return
            
        device_group = QGroupBox("Device Information")
        device_layout = QFormLayout()
        
        # Add device info fields
        for key, value in device_info.items():
            device_layout.addRow(f"{key}:", QLabel(value))
        
        device_group.setLayout(device_layout)
        parent_layout.addWidget(device_group)
    
    def _add_key_provisioning_section(self, parent_layout):
        """Add key provisioning section to the dialog.

        Args:
            parent_layout: Layout to add the section to
        """
        key_prov_data = self.log_data.get('key_provisioning', {})
        if not key_prov_data or not any([
            key_prov_data.get('key_programming'),
            key_prov_data.get('otp_status'),
            key_prov_data.get('success_messages'),
            key_prov_data.get('final_state')
        ]):
            return
            
        key_prov_group = QGroupBox("Key Provisioning Status")
        key_prov_layout = QVBoxLayout()

        # Add success messages first if available
        if key_prov_data.get('success_messages'):
            success_group = QGroupBox("Provisioning Status")
            success_layout = QVBoxLayout()

            for message in key_prov_data['success_messages']:
                success_label = QLabel(f"\u2713 {message}")
                success_label.setStyleSheet("color: #28a745; font-weight: bold;")
                success_layout.addWidget(success_label)

            success_group.setLayout(success_layout)
            key_prov_layout.addWidget(success_group)

        # Add final state if available
        if key_prov_data.get('final_state'):
            final_state = key_prov_data['final_state']
            state_label = QLabel(f"Device State: {final_state}")
            state_label.setStyleSheet("font-weight: bold; color: #28a745;")
            key_prov_layout.addWidget(state_label)

        # Add OTP status messages if available
        if key_prov_data.get('otp_status'):
            otp_status_group = QGroupBox("OTP Programming Status")
            otp_status_layout = QVBoxLayout()

            for status in key_prov_data['otp_status']:
                status_label = QLabel(f"• {status}")
                status_label.setWordWrap(True)
                if "successful" in status.lower() or "success" in status.lower():
                    status_label.setStyleSheet("color: #28a745;")
                else:
                    status_label.setStyleSheet("color: #6c757d;")
                otp_status_layout.addWidget(status_label)

            otp_status_group.setLayout(otp_status_layout)
            key_prov_layout.addWidget(otp_status_group)
        
        # Add key programming status if available
        if key_prov_data.get('key_programming'):
            key_prog_group = QGroupBox("Key Components")
            key_prog_layout = QGridLayout()
            
            # Add header
            header_key = QLabel("Component")
            header_key.setStyleSheet("font-weight: bold;")
            header_status = QLabel("Status")
            header_status.setStyleSheet("font-weight: bold;")
            key_prog_layout.addWidget(header_key, 0, 0)
            key_prog_layout.addWidget(header_status, 0, 1)
            
            # Add key components
            row = 1
            for key, status in key_prov_data['key_programming'].items():
                key_label = QLabel(key)
                key_prog_layout.addWidget(key_label, row, 0)
                
                # Add status with appropriate icon
                status_label = QLabel()
                if status.lower() == 'success':
                    status_label.setText("\u2713 Success")
                    status_label.setStyleSheet("color: #28a745; font-weight: bold;")
                else:
                    status_label.setText("\u274c Failed")
                    status_label.setStyleSheet("color: #dc3545; font-weight: bold;")
                
                key_prog_layout.addWidget(status_label, row, 1)
                row += 1
            
            key_prog_group.setLayout(key_prog_layout)
            key_prov_layout.addWidget(key_prog_group)
        
        key_prov_group.setLayout(key_prov_layout)
        parent_layout.addWidget(key_prov_group)
    
    def _add_code_provisioning_section(self, parent_layout):
        """Add code provisioning section to the dialog.
        
        Args:
            parent_layout: Layout to add the section to
        """
        code_prov_data = self.log_data.get('code_provisioning', {})
        if not code_prov_data or not (code_prov_data.get('stages') or code_prov_data.get('success_messages')):
            return
            
        code_prov_group = QGroupBox("Code Provisioning Status")
        code_prov_layout = QVBoxLayout()
        
        # Add success messages
        if code_prov_data.get('success_messages'):
            success_group = QGroupBox("Completion Status")
            success_layout = QVBoxLayout()
            
            for message in code_prov_data['success_messages']:
                success_label = QLabel(f"\u2713 {message}")
                success_label.setStyleSheet("color: #28a745; font-weight: bold;")
                success_layout.addWidget(success_label)
            
            success_group.setLayout(success_layout)
            code_prov_layout.addWidget(success_group)
        
        # Add progress bars for each stage
        if code_prov_data.get('stages'):
            stages_group = QGroupBox("Provisioning Stages")
            stages_layout = QVBoxLayout()
            
            for stage_name, stage_data in code_prov_data['stages'].items():
                stage_container = QWidget()
                stage_container_layout = QVBoxLayout(stage_container)
                stage_container_layout.setContentsMargins(0, 0, 0, 0)
                
                # Create a progress bar for this stage
                stage_label = QLabel(stage_name)
                stage_container_layout.addWidget(stage_label)
                
                progress_bar = QProgressBar()
                progress_bar.setMinimum(0)
                progress_bar.setMaximum(100)
                progress_bar.setValue(stage_data.get('final_percentage', 0))
                stage_container_layout.addWidget(progress_bar)
                
                stages_layout.addWidget(stage_container)
                stages_layout.addSpacing(5)
            
            stages_group.setLayout(stages_layout)
            code_prov_layout.addWidget(stages_group)
        
        code_prov_group.setLayout(code_prov_layout)
        parent_layout.addWidget(code_prov_group)
    
    def _add_errors_section(self, parent_layout):
        """Add errors section to the dialog.
        
        Args:
            parent_layout: Layout to add the section to
        """
        errors = self.log_data.get('errors', [])
        if not errors:
            return
            
        errors_group = QGroupBox("Errors")
        errors_layout = QVBoxLayout()
        
        for error in errors:
            error_label = QLabel(error)
            error_label.setStyleSheet("color: #dc3545;")
            error_label.setWordWrap(True)
            errors_layout.addWidget(error_label)
            
        errors_group.setLayout(errors_layout)
        parent_layout.addWidget(errors_group)
    
    def _open_log_file(self):
        """Open the log file for viewing."""
        try:
            if self.log_file_path and os.path.exists(self.log_file_path):
                QMessageBox.information(
                    self, 
                    "Log File", 
                    f"Opening log file: {self.log_file_path}\n\nNote: A debugResponse of 0x00000000 indicates successful programming despite the error message."
                )
                # Use platform-independent method to open file
                open_file(self.log_file_path)
            else:
                QMessageBox.warning(
                    self, 
                    "File Not Found", 
                    f"The log file {self.log_file_path} does not exist."
                )
        except Exception as e:
            QMessageBox.critical(
                self, 
                "Error", 
                f"Failed to open log file: {str(e)}"
            )