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

from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QGroupBox,
    QLabel,
    QComboBox,
    QRadioButton,
    QButtonGroup,
    QPushButton,
    QLineEdit,
    QFileDialog,
    QMessageBox,
    QCheckBox,
    QFormLayout,
    QSpacerItem,
    QSizePolicy,
    QProgressDialog,
    QFrame,
    QTabWidget,
    QDialog,
    QScrollArea,
    QProgressBar
)
from PyQt5.QtGui import QColor, QPainter, QPen, QFont, QFontMetrics
from PyQt5.QtCore import Qt, pyqtSignal, QThread, pyqtSlot, QTimer, QSize, QPropertyAnimation, QEasingCurve, QPoint
from apps.qtgui.utils.log_parser import LogManager, parse_provisioning_logs, LogData
from apps.qtgui.devices.register import (
    get_provisioning_spec_for_device,
    get_boot_modes_for_device,
    get_provisioning_ui_for_device,
    get_key_options_for_device,
    DeviceRegistry,
)
from apps.qtgui.views.components.provisioning_results_dialog import ProvisioningResultsDialog
from apps.qtgui.services.provisioning_worker import (
    start_provisioning_task,
    create_progress_dialog,
    stream_provisioning_output,
    run_post_provisioning_detection,
)
from apps.qtgui.views.pages.prov_tabs.session_info_panel import SessionInfoPanel
from apps.qtgui.views.pages.prov_tabs.provisioning_progress_dialog import ProvisioningProgressDialog
import serial.tools.list_ports
from apps.qtgui.utils.platform_utils import format_serial_port_name, get_serial_port_filter, get_home_directory, open_file
from common.device_utils import get_device_prebuilt_dir, get_device_output_dir, get_device_file_pattern, infer_device_family
import os
import getpass
import re
from collections import OrderedDict

class ProvisioningDetailsPanel(QWidget):
    """Panel to display detailed information about provisioning components for each state"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.session_info = {}
        self.provisioning_log_data = None
        self.current_state = None
        self._state_groups: dict = {}   # state_key → QGroupBox
        self._device_states: list = []
        self.init_ui()

    def init_ui(self):
        """Initialize the UI components"""
        # Main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(5, 5, 5, 5)

        # Create a scroll area to contain all content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        # Content widget
        content_widget = QWidget()
        self.content_layout = QVBoxLayout(content_widget)

        # Header
        self.header_label = QLabel("Provisioning Details")
        self.header_label.setStyleSheet("font-weight: bold; color: #CC0000;")
        self.content_layout.addWidget(self.header_label)

        # Add spacer at bottom (groups are inserted before this)
        self.content_layout.addStretch()

        # Set the content widget to the scroll area
        scroll.setWidget(content_widget)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Add scroll area to main layout
        self.main_layout.addWidget(scroll)

    def configure_states(self, device_states, device_state_labels):
        """Create/recreate state groups for the given device states."""
        for g in self._state_groups.values():
            self.content_layout.removeWidget(g)
            g.deleteLater()
        self._state_groups = {}
        self._device_states = list(device_states)
        idx_descs = [
            lambda lbl: f"Device is in {lbl} state — ready for provisioning.",
            lambda lbl: f"Keys have been provisioned ({lbl}).",
            lambda lbl: f"Device fully provisioned ({lbl}).",
        ]
        for i, state in enumerate(device_states):
            label = device_state_labels.get(state, state)
            desc = idx_descs[min(i, len(idx_descs) - 1)](label)
            group = self.create_state_group(f"{state} - {label}", desc)
            self._state_groups[state] = group
            self.content_layout.insertWidget(self.content_layout.count() - 1, group)
            group.hide()
        self.current_state = None
    
    def create_state_group(self, title, description):
        """Create a collapsible group box for a state"""
        group = QGroupBox(title)
        group.setCheckable(True)
        group.setChecked(True)  # Initially expanded
        
        layout = QVBoxLayout(group)
        
        # Description
        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # Form layout for details
        form_widget = QWidget()
        form_layout = QFormLayout(form_widget)
        form_layout.setContentsMargins(0, 0, 0, 0)
        
        # Store the form layout reference for later use
        setattr(group, "form_layout", form_layout)
        
        layout.addWidget(form_widget)
        return group
    
    def set_session_info(self, session_info):
        """Set session information and update UI"""
        self.session_info = session_info
        self.update_details()
    
    def set_provisioning_log_data(self, provisioning_log_data):
        """Set provisioning log data and update UI"""
        self.provisioning_log_data = provisioning_log_data
        self.update_details()
    
    def set_current_state(self, state):
        """Set the current state and update UI"""
        self.current_state = state
        self.update_visible_groups()
        self.update_details()
    
    def update_visible_groups(self):
        """Update which groups are visible based on current state"""
        if not self._state_groups:
            return
        idx = self._device_states.index(self.current_state) \
              if self.current_state in self._device_states else -1
        for i, state in enumerate(self._device_states):
            g = self._state_groups.get(state)
            if g:
                g.setVisible(i <= idx)
    
    def update_details(self):
        """Update the details in each section based on available data"""
        self.clear_details()
        states = self._device_states

        # Update first-state group details from session_info
        if self.session_info and states:
            device = self.session_info.get('device', 'Unknown')
            boot_mode = self.session_info.get('boot_mode', 'Unknown')
            connection_info = self.session_info.get('connection_info', {})

            connection_str = "Unknown"
            if connection_info:
                from apps.qtgui.devices.register import get_boot_mode_specs_for_device
                bm_specs = get_boot_mode_specs_for_device(self.session_info.get('device', '').lower())
                conn_type = connection_info.get('type', '')
                bm_spec = next((s for s in bm_specs if s["connection_type"] == conn_type), None)
                if bm_spec:
                    connection_str = f"{bm_spec['id']}: {connection_info.get(bm_spec['connection_param'], '')}"

            first_group = self._state_groups.get(states[0])
            if first_group:
                first_form = getattr(first_group, "form_layout")
                self.add_detail_row(first_form, "Device Type", device)
                self.add_detail_row(first_form, "Boot Mode", boot_mode)
                self.add_detail_row(first_form, "Connection", connection_str)

        # Update second-state group details from provisioning_log_data (key provisioning info)
        if self.provisioning_log_data and self.current_state in self._device_states[1:] and len(states) >= 2:
            key_provisioning = self.provisioning_log_data.get('key_provisioning', {})
            device_info = self.provisioning_log_data.get('device_info', {})
            second_group = self._state_groups.get(states[1])

            if second_group:
                hskp_form = getattr(second_group, "form_layout")

                # Add key types if available
                if device_info:
                    for key, value in device_info.items():
                        if "Key Type" in key or "Version" in key:
                            self.add_detail_row(hskp_form, key, value)

                # Add key component statuses
                key_programming = key_provisioning.get('key_programming', {})
                if key_programming:
                    key_status_label = QLabel("Key Components:")
                    key_status_label.setStyleSheet("font-weight: bold;")
                    hskp_form.addRow(key_status_label)
                    for key, status in key_programming.items():
                        status_text = "✓ Success" if status == "Success" else "❌ Failed"
                        status_color = "#28a745" if status == "Success" else "#dc3545"
                        self.add_detail_row(hskp_form, key, status_text, status_color)

                # Add OTP status messages
                otp_status = key_provisioning.get('otp_status', [])
                if otp_status:
                    otp_status_label = QLabel("OTP Programming:")
                    otp_status_label.setStyleSheet("font-weight: bold;")
                    hskp_form.addRow(otp_status_label)
                    for status in otp_status[:3]:  # Limit to first 3 for brevity
                        status_color = "#28a745" if "successful" in status.lower() else "#6c757d"
                        status_row = QLabel(status)
                        status_row.setStyleSheet(f"color: {status_color};")
                        status_row.setWordWrap(True)
                        hskp_form.addRow("", status_row)

        # Update last-state group details from provisioning_log_data (code provisioning info)
        final_state = states[-1] if states else None
        if self.provisioning_log_data and self.current_state == final_state and len(states) >= 3:
            code_provisioning = self.provisioning_log_data.get('code_provisioning', {})
            last_group = self._state_groups.get(final_state)
            if last_group:
                hsse_form = getattr(last_group, "form_layout")

                # Add code provisioning success messages
                success_messages = code_provisioning.get('success_messages', [])
                if success_messages:
                    code_status_label = QLabel("Code Components:")
                    code_status_label.setStyleSheet("font-weight: bold;")
                    hsse_form.addRow(code_status_label)
                    for message in success_messages:
                        status_text = f"✓ {message}"
                        if 'SecCfg Loading is successful' in message:
                            status_text = "✓ Security Configuration loaded successfully"
                        self.add_detail_row(hsse_form, "", status_text, "#28a745")

                # Add code provisioning error messages
                errors = self.provisioning_log_data.get('errors', [])
                if errors:
                    error_status_label = QLabel("Errors:")
                    error_status_label.setStyleSheet("font-weight: bold; color: #dc3545;")
                    hsse_form.addRow(error_status_label)
                    for error in errors:
                        self.add_detail_row(hsse_form, "", f"❌ {error}", "#dc3545")

                # Add code provisioning stages info
                stages = code_provisioning.get('stages', {})
                if stages:
                    stages_label = QLabel("Provisioning Stages:")
                    stages_label.setStyleSheet("font-weight: bold;")
                    hsse_form.addRow(stages_label)
                    for stage_name, stage_data in stages.items():
                        percentage = stage_data.get('final_percentage', 0)
                        self.add_detail_row(hsse_form, stage_name, f"{percentage}% complete")

    def clear_details(self):
        """Clear all details from the form layouts"""
        for group in self._state_groups.values():
            form = getattr(group, "form_layout")
            while form.rowCount() > 0:
                form.removeRow(0)
    
    def add_detail_row(self, form_layout, label_text, value_text, color=None):
        """Add a detail row to a form layout"""
        value_label = QLabel(value_text)
        value_label.setWordWrap(True)
        if color:
            value_label.setStyleSheet(f"color: {color};")
        
        form_layout.addRow(label_text, value_label)


class DeviceStateIndicator(QWidget):
    """Widget for visualizing device state progression (HSFS → HSKP → HSSE)"""

    def __init__(self, states=None, state_labels=None, parent=None):
        super().__init__(parent)
        self.current_state = None
        self.states = states or ["HSFS", "HSKP", "HSSE"]
        self.state_descriptions = state_labels or {
            "HSFS": "Field Secure",
            "HSKP": "Keys Provisioned",
            "HSSE": "Code Provisioned",
        }
        self.colors = {
            "active": QColor(40, 167, 69),     # Green for active state
            "completed": QColor(40, 167, 69), # Green for completed states
            "pending": QColor(200, 200, 200), # Gray for pending states
            "text": QColor(30, 30, 30),       # Dark gray for text
            "line": QColor(180, 180, 180)     # Gray for connecting lines
        }
        self.setMinimumHeight(80)
        self.setMinimumWidth(400)
    
    def set_current_state(self, state):
        """Set the current state and update the display"""
        if state in self.states or state is None:
            self.current_state = state
            self.update()  # Trigger a repaint
    
    def get_state_index(self, state):
        """Get the index of a state in the sequence"""
        if state in self.states:
            return self.states.index(state)
        return -1

    def set_states(self, states: list, state_labels: dict = None):
        """Reload the indicator with a new state list from the device registry."""
        if states:
            self.states = states
        if state_labels:
            self.state_descriptions = state_labels
        self.update()  # Trigger a repaint

    def paintEvent(self, event):
        """Paint the state progression indicator"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Calculate dimensions
        width = self.width()
        height = self.height()
        circle_diameter = min(height * 0.6, 30)  # Smaller of 60% of height or 30px
        circle_radius = circle_diameter / 2
        
        # Calculate horizontal spacing
        num_states = len(self.states)
        horizontal_spacing = (width - circle_diameter * num_states) / (num_states + 1)
        
        # Calculate vertical positions
        circle_y = height * 0.25
        text_y = circle_y + circle_diameter + 5
        
        # Get current state index
        current_idx = self.get_state_index(self.current_state)
        
        # Draw connecting lines first (behind the circles)
        if num_states > 1:
            painter.setPen(QPen(self.colors["line"], 2))
            line_y = circle_y + circle_radius
            for i in range(num_states - 1):
                x1 = horizontal_spacing * (i + 1) + circle_diameter * (i + 0.5)
                x2 = horizontal_spacing * (i + 2) + circle_diameter * (i + 1.5)
                painter.drawLine(int(x1), int(line_y), int(x2), int(line_y))
        
        # Draw each state circle and label
        for i, state in enumerate(self.states):
            # Calculate position
            x = horizontal_spacing * (i + 1) + circle_diameter * i
            
            # Determine state color
            if current_idx == -1:
                # No state selected, all gray
                color = self.colors["pending"]
            elif i < current_idx:
                # Completed state
                color = self.colors["completed"]
            elif i == current_idx:
                # Current active state
                color = self.colors["active"]
            else:
                # Future state
                color = self.colors["pending"]
            
            # Draw circle
            painter.setPen(QPen(color, 2))
            painter.setBrush(QColor(255, 255, 255))  # White fill
            painter.drawEllipse(int(x), int(circle_y), int(circle_diameter), int(circle_diameter))
            
            # Draw state text inside circle
            text_color = color
            painter.setPen(text_color)
            font = QFont()
            font.setBold(True)
            font.setPointSize(8)
            painter.setFont(font)
            
            # Center text in circle
            text_rect = painter.fontMetrics().boundingRect(state)
            text_x = x + (circle_diameter - text_rect.width()) / 2
            text_y_centered = circle_y + (circle_diameter + text_rect.height()) / 2 - 2  # -2 for visual adjustment
            painter.drawText(int(text_x), int(text_y_centered), state)
            
            # Draw description below
            description = self.state_descriptions.get(state, "")
            if description:
                font.setPointSize(8)
                font.setBold(False)
                painter.setFont(font)
                painter.setPen(self.colors["text"])
                
                desc_rect = painter.fontMetrics().boundingRect(description)
                desc_x = x + (circle_diameter - desc_rect.width()) / 2
                painter.drawText(int(desc_x), int(text_y + 15), description)


class ProvisioningPage(QWidget):
    """Combined page for both key and code provisioning operations"""
    
    # Signals
    convert_requested = pyqtSignal(dict)
    device_state_changed = pyqtSignal(str)  # Signal to notify device state change
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.session_info = {}
        self.device_name = None
        self.device_variant = None
        self.device_family = None
        self.provisioning_data = None
        self.key_provisioning_data = None
        self.code_provisioning_data = None
        self.provisioning_log_data = None
        self.progress_dialog = None
        # Generic field storage: [boot_mode][field_id] -> {"input": widget, "check": widget, ...}
        self._key_prov_fields: dict = {}
        self._code_prov_fields: dict = {}
        self._adv_groups: dict = {}    # "key_UART", "code_JTAG", etc.
        self._adv_headers: dict = {}
        self._prov_buttons: dict = {}  # "key_UART", "code_JTAG", etc.
        self._prov_tab_store: dict = {}   # "key_UART" etc. → ProvisioningTabBase
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI components"""
        # Create main scroll area to make the entire page scrollable
        self.main_scroll_area = QScrollArea()
        self.main_scroll_area.setWidgetResizable(True)
        self.main_scroll_area.setFrameShape(QFrame.NoFrame)
        self.main_scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.main_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.main_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Create container widget for scroll area
        scroll_content = QWidget()
        scroll_content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Main layout for scrollable content
        main_layout = QVBoxLayout(scroll_content)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Set the scroll content as the widget for the scroll area
        self.main_scroll_area.setWidget(scroll_content)
        
        # Layout for the main widget that contains the scroll area
        self_layout = QVBoxLayout(self)
        self_layout.setContentsMargins(0, 0, 0, 0)
        self_layout.setSpacing(0)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self_layout.addWidget(self.main_scroll_area)
        
        # Page title
        title_label = QLabel("Device Provisioning")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #CC0000;")
        main_layout.addWidget(title_label)
        
        # Session info panel + provisioning details panel
        self.provisioning_details_panel = ProvisioningDetailsPanel()
        self.provisioning_details_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.provisioning_details_panel.setMinimumHeight(200)

        self._session_panel = SessionInfoPanel(self.provisioning_details_panel)
        main_layout.addWidget(self._session_panel)

        # Expose legacy proxy attributes so external callers still work
        self.state_indicator = self._session_panel.state_indicator

        # Add provisioning details panel as separate section
        details_group = QGroupBox("Provisioning Details")
        details_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        details_layout = QVBoxLayout(details_group)
        details_layout.addWidget(self.provisioning_details_panel)
        main_layout.addWidget(details_group)
        
        # Add separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background-color: #CCCCCC;")
        main_layout.addWidget(separator)
        
        # Create main tabs for key provisioning and code provisioning
        self.main_tabs = QTabWidget()
        self.main_tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # === KEY PROVISIONING TAB ===
        key_provisioning_tab = QWidget()
        key_provisioning_tab.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        key_provisioning_layout = QVBoxLayout(key_provisioning_tab)

        self.key_prov_empty_label = QLabel(
            "Start a provisioning session to continue.\n"
            "Select a device and configure your keys on the previous steps."
        )
        self.key_prov_empty_label.setAlignment(Qt.AlignCenter)
        self.key_prov_empty_label.setStyleSheet(
            "color: #888888; font-style: italic; padding: 24px;"
        )
        key_provisioning_layout.addWidget(self.key_prov_empty_label)

        # Generic provisioning container — populated dynamically by _build_prov_ui_from_spec
        self.prov_group = QGroupBox("Keys Provisioning")
        self.prov_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        _pg_layout = QVBoxLayout()
        self.prov_tabs = QTabWidget()
        self.prov_tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        _pg_layout.addWidget(self.prov_tabs)
        self.prov_group.setLayout(_pg_layout)
        key_provisioning_layout.addWidget(self.prov_group)
        self.prov_group.hide()

        # Add Key Provisioning Tab
        self.main_tabs.addTab(key_provisioning_tab, "Keys Provisioning")
        
        # === CODE PROVISIONING TAB ===
        code_provisioning_tab = QWidget()
        code_provisioning_tab.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        code_provisioning_layout = QVBoxLayout(code_provisioning_tab)

        self.code_prov_empty_label = QLabel(
            "Complete key provisioning first to unlock code provisioning."
        )
        self.code_prov_empty_label.setAlignment(Qt.AlignCenter)
        self.code_prov_empty_label.setStyleSheet(
            "color: #888888; font-style: italic; padding: 24px;"
        )
        code_provisioning_layout.addWidget(self.code_prov_empty_label)

        # Generic code provisioning container — populated dynamically
        self.code_prov_group = QGroupBox("Code Provisioning")
        self.code_prov_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        _cpg_layout = QVBoxLayout()
        self.code_prov_tabs = QTabWidget()
        self.code_prov_tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        _cpg_layout.addWidget(self.code_prov_tabs)
        self.code_prov_group.setLayout(_cpg_layout)
        code_provisioning_layout.addWidget(self.code_prov_group)
        self.code_prov_group.hide()

        # Add Code Provisioning Tab
        self.main_tabs.addTab(code_provisioning_tab, "Code Provisioning")
        
        # Add tabs to main layout
        self.main_tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        main_layout.addWidget(self.main_tabs)
        
        # Add spacer at the bottom
        main_layout.addStretch(1)
        
        # The advanced settings are already initialized as hidden through setVisible(False)
    
    def set_session_info(self, session_data):
        """Set session information and update UI"""
        # Store the previous device state to detect changes
        previous_device_state = self.session_info.get('device_state', '') if hasattr(self, 'session_info') and self.session_info else ''

        # Hide empty state labels when a valid session is loaded
        if session_data:
            self.key_prov_empty_label.hide()
            self.code_prov_empty_label.hide()

        # Update the session info with new data
        self.session_info = session_data
        
        # Update provisioning details panel with session info
        self.provisioning_details_panel.set_session_info(session_data)
        
        # Update labels with session info
        device = session_data.get('device', '')
        device_state = session_data.get('device_state', '')
        boot_mode = session_data.get('boot_mode', '')
        connection_info = session_data.get('connection_info', {})
        key_type = session_data.get('key_type', '')
        key_data = session_data.get('key_data', {})
        certificate_info = session_data.get('certificate_info', {})

        # Extract device info for dynamic path resolution
        self.device_name = device.lower() if device else None
        self.device_family = infer_device_family(self.device_name) if self.device_name else None
        # Infer device variant from device_state (HSSE → hsse, else → hsfs)
        device_state_raw = session_data.get('device_state', '')
        if device_state_raw and device_state_raw.strip().upper() == "HSSE":
            self.device_variant = "hsse"
        else:
            self.device_variant = session_data.get('device_variant', 'hsfs')

        # Update session panel labels and configure device state progression
        prov_spec = get_provisioning_spec_for_device(self.device_name or "")
        key_prov  = prov_spec.get("key_provisioning",  {})
        code_prov = prov_spec.get("code_provisioning", {})
        key_options = get_key_options_for_device(self.device_name or "")
        self._session_panel.update(session_data, prov_spec, key_options)

        # Set provisioning statuses based on device state
        device_state_upper = device_state.strip().upper() if device_state else ""
        can_provision_keys = device_state_upper in key_prov.get("enabled_in_states", [])
        can_provision_code = device_state_upper in code_prov.get("enabled_in_states", [])

        if can_provision_keys:
            # State allows key provisioning (e.g. HSFS for F29, READY for standard)
            self._session_panel.set_device_state(device_state_upper, device_state_upper)
            self._session_panel.set_key_prov_status("Not Started", "color: #FF9800; font-weight: bold;")
            self._session_panel.set_code_prov_status("Not Available", "color: #999999; font-weight: normal;")
            # Enable and show key provisioning tab, disable code provisioning tab
            self.main_tabs.setTabVisible(0, True)  # Show key provisioning tab
            self.main_tabs.setTabEnabled(0, True)
            self.main_tabs.setTabEnabled(1, False)
            self.main_tabs.setCurrentIndex(0)  # Select key provisioning tab
            # Enable key provisioning buttons, disable code provisioning buttons
            self._enable_provisioning_buttons("key", True)
            self._enable_provisioning_buttons("code", False)
        elif can_provision_code:
            # State allows code provisioning (e.g. HSKP for F29)
            self._session_panel.set_device_state(device_state_upper, device_state_upper)
            self._session_panel.set_key_prov_status("Completed ✓", "color: #28a745; font-weight: bold;")
            self._session_panel.set_code_prov_status("Not Started", "color: #FF9800; font-weight: bold;")
            # Hide key provisioning tab, show only code provisioning
            self.main_tabs.setTabVisible(0, False)
            self.main_tabs.setTabEnabled(1, True)
            self.main_tabs.setCurrentIndex(1)  # Select code provisioning tab
            # Disable key provisioning buttons (already provisioned), enable code provisioning buttons
            self._enable_provisioning_buttons("key", False)
            self._enable_provisioning_buttons("code", True)
        else:
            # All provisioning complete (e.g. HSSE for F29, PROVISIONED for standard)
            self._session_panel.set_device_state(
                device_state_upper or "",
                device_state_upper or None,
            )
            self._session_panel.set_key_prov_status("Completed ✓", "color: #28a745; font-weight: bold;")
            self._session_panel.set_code_prov_status("Completed ✓", "color: #28a745; font-weight: bold;")
            # Hide key provisioning tab, show only code provisioning
            self.main_tabs.setTabVisible(0, False)
            self.main_tabs.setTabEnabled(1, True)
            self.main_tabs.setCurrentIndex(1)  # Select code provisioning tab
            # Disable both provisioning buttons as both key and code are already provisioned
            self._enable_provisioning_buttons("key", False)
            self._enable_provisioning_buttons("code", True)

        # Build generic provisioning UI from device config
        self._build_prov_ui_from_spec("key")
        self._build_prov_ui_from_spec("code")

        # Mark any mandatory fields (must be after _build_prov_ui_from_spec so widgets exist)
        for _bm, mode_fields in self._code_prov_fields.items():
            for fid, fw in mode_fields.items():
                spec = fw.get("spec", {})
                if device_state_upper in spec.get("mandatory_in_states", []):
                    self._update_mandatory_field_status("code", fid, True)

        # Push session info to all custom provisioning tab instances
        for _adv_key, _tab_instance in self._prov_tab_store.items():
            _tab_instance.set_session_info(self.session_info)

        # Select boot-mode tab matching current connection
        from apps.qtgui.devices.register import get_boot_mode_specs_for_device
        bm_specs = get_boot_mode_specs_for_device(self.session_info.get('device', '').lower())
        conn_type = connection_info.get('type', '') if connection_info else ''
        bm_spec = next((s for s in bm_specs if s["connection_type"] == conn_type), None)
        if bm_spec:
            for tabs_widget in [self.prov_tabs, self.code_prov_tabs]:
                for i in range(tabs_widget.count()):
                    if tabs_widget.tabText(i) == bm_spec["id"]:
                        tabs_widget.setCurrentIndex(i)
                        break
    
    # -------------------------------------------------------------------------
    # Generic provisioning UI builders (Step 4)
    # -------------------------------------------------------------------------

    _TAB_STYLE = """
        QTabWidget::pane { border: 1px solid #cccccc; background: white; border-radius: 3px; }
        QTabBar::tab {
            background: #f0f0f0; border: 1px solid #cccccc; border-bottom: none;
            border-top-left-radius: 3px; border-top-right-radius: 3px;
            padding: 2px 6px; margin-right: 2px; min-height: 16px; font-size: 11px;
        }
        QTabBar::tab:selected { background: #ffffff; border-bottom: 1px solid #ffffff; font-weight: bold; }
        QTabBar::tab:!selected { margin-top: 2px; }
    """
    _BTN_STYLE = """
        QPushButton {
            background-color: #CC0000; color: white;
            padding: 6px 15px; border: none; border-radius: 3px; min-width: 160px;
        }
        QPushButton:hover { background-color: #990000; }
        QPushButton:disabled { background-color: #cccccc; color: #666666; }
    """
    _ADV_HDR_STYLE = """
        QPushButton {
            text-align: left; padding: 5px 8px; font-weight: bold; font-size: 11px;
            background-color: #CC0000; color: white; border: 1px solid #990000; border-radius: 4px;
        }
        QPushButton:hover { background-color: #990000; }
    """
    _ADV_GRP_STYLE = """
        QGroupBox {
            border: 1px solid #990000; border-top: none;
            border-radius: 0px 0px 4px 4px; margin-top: 0px;
            padding: 5px; background-color: #f8f8f8;
        }
    """

    def _build_prov_ui_from_spec(self, prov_type: str):
        """Tear down and rebuild prov_tabs / code_prov_tabs from device config."""
        if prov_type == "key":
            tabs_widget = self.prov_tabs
            group_widget = self.prov_group
            fields_dict = self._key_prov_fields
        else:
            tabs_widget = self.code_prov_tabs
            group_widget = self.code_prov_group
            fields_dict = self._code_prov_fields

        # Clear state
        while tabs_widget.count():
            tabs_widget.removeTab(0)
        fields_dict.clear()
        for k in [k for k in self._adv_groups if k.startswith(f"{prov_type}_")]:
            del self._adv_groups[k]
        for k in [k for k in self._adv_headers if k.startswith(f"{prov_type}_")]:
            del self._adv_headers[k]
        for k in [k for k in self._prov_buttons if k.startswith(f"{prov_type}_")]:
            del self._prov_buttons[k]

        if not self.device_name:
            group_widget.hide()
            return

        from apps.qtgui.views.pages.prov_tabs.registry import PROV_TAB_CLASSES

        boot_modes = get_boot_modes_for_device(self.device_name)
        has_any = False
        for boot_mode in boot_modes:
            mode_spec = get_provisioning_ui_for_device(self.device_name, prov_type, boot_mode)
            if not mode_spec:
                continue

            device_prov_classes = PROV_TAB_CLASSES.get(self.device_name or "", {})
            tab_class = device_prov_classes.get(prov_type, {}).get(boot_mode)

            if tab_class:
                adv_key = f"{prov_type}_{boot_mode}"
                if adv_key not in self._prov_tab_store:
                    instance = tab_class(self)
                    instance.provision_clicked.connect(
                        lambda _c=None, pt=prov_type, bm=boot_mode: self.on_provision_clicked(pt, bm)
                    )
                    self._prov_tab_store[adv_key] = instance
                tabs_widget.addTab(self._prov_tab_store[adv_key], boot_mode)
                has_any = True
            else:
                tab_widget, mode_fields = self._build_boot_mode_tab(prov_type, boot_mode, mode_spec)
                fields_dict[boot_mode] = mode_fields
                tabs_widget.addTab(tab_widget, boot_mode)
                has_any = True

        tabs_widget.setStyleSheet(self._TAB_STYLE)
        # Hide the tab bar when only one boot mode is available — no point showing a selector
        tabs_widget.tabBar().setVisible(tabs_widget.count() > 1)
        if has_any:
            group_widget.show()
            self._update_default_paths(prov_type)
        else:
            group_widget.hide()

    def _build_boot_mode_tab(self, prov_type: str, boot_mode: str, mode_spec: dict):
        """Build one UART/JTAG tab widget for the given prov_type and mode_spec."""
        tab = QWidget()
        tab.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(3)

        mode_fields: dict = {}
        adv_key = f"{prov_type}_{boot_mode}"

        # --- Advanced section ---
        adv_fields = mode_spec.get("advanced_fields", [])
        if adv_fields:
            adv_container = QWidget()
            adv_container_layout = QVBoxLayout(adv_container)
            adv_container_layout.setContentsMargins(0, 0, 0, 0)
            adv_container_layout.setSpacing(0)

            adv_header = QPushButton("▶ Advanced Settings")
            adv_header.setStyleSheet(self._ADV_HDR_STYLE)
            adv_container_layout.addWidget(adv_header)

            adv_group = QGroupBox()
            adv_group.setStyleSheet(self._ADV_GRP_STYLE)
            adv_group.setProperty("prov_type", prov_type)
            adv_group.setVisible(False)
            adv_group_layout = QVBoxLayout(adv_group)
            adv_group_layout.setContentsMargins(5, 5, 5, 5)
            adv_group_layout.setSpacing(2)

            for spec in adv_fields:
                row = self._build_field_row(spec, mode_fields, compact=True)
                adv_group_layout.addWidget(row)

            adv_container_layout.addWidget(adv_group)
            layout.addWidget(adv_container)

            adv_header.clicked.connect(
                lambda _checked, g=adv_group, h=adv_header: self._toggle_advanced_section(g, h)
            )
            self._adv_groups[adv_key] = adv_group
            self._adv_headers[adv_key] = adv_header

        # --- Main fields ---
        main_fields = mode_spec.get("main_fields", []) or []
        for spec in main_fields:
            row = self._build_field_row(spec, mode_fields, compact=False)
            layout.addWidget(row)

        # --- Provision button ---
        btn_label = mode_spec.get("provision_button_label", f"Provision ({boot_mode})")
        btn = QPushButton(btn_label)
        btn.setStyleSheet(self._BTN_STYLE)
        btn.clicked.connect(
            lambda _checked, pt=prov_type, bm=boot_mode: self.on_provision_clicked(pt, bm)
        )
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)
        self._prov_buttons[adv_key] = btn

        layout.addStretch(1)
        return tab, mode_fields

    def _build_field_row(self, spec: dict, field_dict: dict, compact: bool = True) -> QWidget:
        """Build one field row widget and store refs in field_dict[spec['id']]."""
        fid = spec["id"]
        label_text = spec.get("label", fid)
        wtype = spec.get("widget_type", "file_browse")
        ls = "font-size: 10px;" if compact else ""
        inp_ls = "font-size: 10px; height: 18px;" if compact else ""

        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(4)

        entry: dict = {"spec": spec}

        if wtype == "serial_combo":
            lbl = QLabel(f"{label_text}:")
            lbl.setStyleSheet(ls)
            row_layout.addWidget(lbl)
            combo = QComboBox()
            if compact:
                combo.setStyleSheet("font-size: 10px; height: 18px;")
            row_layout.addWidget(combo)
            refresh_btn = QPushButton("Refresh")
            if compact:
                refresh_btn.setStyleSheet("font-size: 10px; height: 18px;")
            refresh_btn.clicked.connect(lambda _checked, cb=combo: self._populate_serial_ports(cb))
            row_layout.addWidget(refresh_btn)
            self._populate_serial_ports(combo)
            entry["input"] = combo

        elif wtype in ("file_browse", "dir_browse"):
            lbl = QLabel(f"{label_text}:")
            lbl.setStyleSheet(ls)
            row_layout.addWidget(lbl)
            line = QLineEdit()
            if compact:
                line.setStyleSheet(inp_ls)
            row_layout.addWidget(line)
            browse_btn = QPushButton("Browse")
            if compact:
                browse_btn.setStyleSheet("font-size: 10px; height: 18px;")
            is_dir = (wtype == "dir_browse")
            browse_btn.clicked.connect(
                lambda _checked, le=line, d=is_dir, lbl_txt=label_text: self._on_browse_clicked(le, d, lbl_txt)
            )
            row_layout.addWidget(browse_btn)
            entry["input"] = line

        elif wtype == "optional_file":
            check = QCheckBox("")
            check.setChecked(spec.get("default_checked", False))
            check.setToolTip(f"Include {label_text}")
            row_layout.addWidget(check)
            lbl = QLabel(f"{label_text}:")
            lbl.setStyleSheet(ls)
            row_layout.addWidget(lbl)
            line = QLineEdit()
            if compact:
                line.setStyleSheet(inp_ls)
            row_layout.addWidget(line)
            browse_btn = QPushButton("Browse")
            if compact:
                browse_btn.setStyleSheet("font-size: 10px; height: 18px;")
            browse_btn.clicked.connect(
                lambda _checked, le=line, lbl_txt=label_text: self._on_browse_clicked(le, False, lbl_txt)
            )
            row_layout.addWidget(browse_btn)
            mandatory_label = QLabel("(Mandatory)")
            mandatory_label.setStyleSheet("color: #CC0000; font-weight: bold; font-size: 10px;")
            mandatory_label.setVisible(False)
            row_layout.addWidget(mandatory_label)
            entry["input"] = line
            entry["check"] = check
            entry["mandatory_label"] = mandatory_label

        field_dict[fid] = entry
        return row_widget

    def _on_browse_clicked(self, line_edit: QLineEdit, is_dir: bool, label: str):
        """Generic browse handler for file or directory selection."""
        if is_dir:
            path = QFileDialog.getExistingDirectory(self, f"Browse {label}")
        else:
            path, _ = QFileDialog.getOpenFileName(
                self, f"Browse {label}", "", "Binary Files (*.bin *.out *.pem);;All Files (*.*)"
            )
        if path:
            line_edit.setText(path)

    def _populate_serial_ports_combo(self, combo: QComboBox):
        """Populate a serial port combo box with available ports."""
        current = combo.currentText()
        combo.clear()
        port_filter = get_serial_port_filter()
        ports = serial.tools.list_ports.comports()
        for port in ports:
            port_name = format_serial_port_name(port.device)
            if port_filter and not any(f.lower() in port_name.lower() for f in port_filter):
                continue
            combo.addItem(port_name)
        if current:
            idx = combo.findText(current)
            if idx >= 0:
                combo.setCurrentIndex(idx)

    def _resolve_default_path(self, path_spec: dict, device_config: dict) -> str:
        """Resolve a default_path spec to an absolute path string (may not exist)."""
        if not path_spec:
            return ""

        def _base_dir(base_name: str) -> str:
            if base_name == "prebuilt":
                return get_device_prebuilt_dir(self.device_name, self.device_family or "")
            return get_device_output_dir(self.device_name, base_name)

        def _render_filename(tmpl: str) -> str:
            return tmpl.format(device_name=self.device_name) if self.device_name else tmpl

        def _from_session(dot_path: str, filename: str = "") -> str:
            """Walk self.session_info by dot-separated path."""
            parts = dot_path.split(".")
            val = self.session_info
            for p in parts:
                if isinstance(val, dict):
                    val = val.get(p, "")
                else:
                    val = ""
                    break
            if val and filename:
                return os.path.join(str(val), filename)
            return str(val) if val else ""

        # variant_key: look up from device registry config for current variant
        if "variant_key" in path_spec:
            vkey = path_spec["variant_key"]
            try:
                vcfg = DeviceRegistry.get_device_config(self.device_name, self.device_variant or "hsfs")
                raw = vcfg.get(vkey, device_config.get(vkey, ""))
            except Exception:
                raw = device_config.get(vkey, "")
            if raw and os.sep not in raw and "/" not in raw:
                prebuilt = get_device_prebuilt_dir(self.device_name, self.device_family or "")
                return os.path.join(str(prebuilt), raw)
            return raw

        # from_session: read a dot-path from session_info
        if "from_session" in path_spec:
            return _from_session(path_spec["from_session"], path_spec.get("filename", ""))

        # priority: list of specs, try each, return first that exists (or last as fallback)
        if "priority" in path_spec:
            candidates = []
            for entry in path_spec["priority"]:
                resolved = self._resolve_default_path(entry, device_config)
                candidates.append(resolved)
            for c in candidates:
                if c and os.path.exists(c):
                    return c
            return candidates[-1] if candidates else ""

        # base + filename / filename_template
        base_name = path_spec.get("base", "")
        filename = path_spec.get("filename", "")
        filename_tmpl = path_spec.get("filename_template", "")
        if filename_tmpl:
            filename = _render_filename(filename_tmpl)
        if base_name and filename:
            return os.path.join(_base_dir(base_name), filename)
        if filename:
            return filename
        return ""

    def _update_default_paths(self, prov_type: str):
        """Populate widget defaults for all boot modes of the given prov_type."""
        if prov_type == "key":
            fields_by_mode = self._key_prov_fields
        else:
            fields_by_mode = self._code_prov_fields

        if not self.device_name:
            return

        try:
            device_config = DeviceRegistry.get_device_config(
                self.device_name, self.device_variant or "hsfs"
            )
        except Exception:
            device_config = {}

        connection_info = self.session_info.get('connection_info', {}) if self.session_info else {}

        for boot_mode, mode_fields in fields_by_mode.items():
            for fid, fw in mode_fields.items():
                spec = fw.get("spec", {})
                path_spec = spec.get("default_path")
                if not path_spec:
                    continue
                widget = fw.get("input")
                if widget is None:
                    continue

                # For serial_combo, try to select from connection_info
                if spec.get("widget_type") == "serial_combo":
                    if connection_info.get('type') == 'uart':
                        port = connection_info.get('port', '')
                        if port:
                            idx = widget.findText(port)
                            if idx >= 0:
                                widget.setCurrentIndex(idx)
                    continue

                # Only set if currently empty
                if isinstance(widget, QLineEdit) and widget.text():
                    continue

                resolved = self._resolve_default_path(path_spec, device_config)
                if resolved:
                    if isinstance(widget, QLineEdit):
                        # Ensure parent dir exists
                        try:
                            os.makedirs(os.path.dirname(resolved), exist_ok=True)
                        except Exception:
                            pass
                        widget.setText(resolved)

    def _validate_fields(self, prov_type: str, boot_mode: str) -> bool:
        """Validate required fields for the given prov_type and boot_mode."""
        if prov_type == "key":
            mode_fields = self._key_prov_fields.get(boot_mode, {})
        else:
            mode_fields = self._code_prov_fields.get(boot_mode, {})

        adv_key = f"{prov_type}_{boot_mode}"
        adv_group = self._adv_groups.get(adv_key)
        adv_visible = adv_group.isVisible() if adv_group else True

        # Determine which field specs are in the advanced vs main section
        mode_spec = get_provisioning_ui_for_device(self.device_name or "", prov_type, boot_mode)
        adv_ids = {s["id"] for s in mode_spec.get("advanced_fields", [])}

        for fid, fw in mode_fields.items():
            spec = fw.get("spec", {})
            in_adv = fid in adv_ids

            # Skip advanced fields when section is collapsed
            if in_adv and not adv_visible:
                continue

            wtype = spec.get("widget_type", "file_browse")
            required = spec.get("required", False)
            widget = fw.get("input")
            check = fw.get("check")

            # optional_file: only validate if checkbox is checked
            if wtype == "optional_file":
                if check and not check.isChecked():
                    continue

            if not required and wtype != "optional_file":
                continue

            if widget is None:
                continue

            if wtype == "serial_combo":
                if not widget.currentText():
                    self._show_error(f"Please select a {spec.get('label', fid)}")
                    return False
            elif wtype == "dir_browse":
                val = widget.text().strip()
                if not val:
                    self._show_error(f"Please provide {spec.get('label', fid)}")
                    return False
                if not os.path.isdir(val):
                    self._show_error(f"{spec.get('label', fid)} path does not exist: {val}")
                    return False
            else:  # file_browse / optional_file
                val = widget.text().strip()
                if not val:
                    self._show_error(f"Please provide {spec.get('label', fid)}")
                    return False
                if not os.path.exists(val):
                    self._show_error(f"{spec.get('label', fid)} file does not exist: {val}")
                    return False
        return True

    def _collect_params(self, prov_type: str, boot_mode: str) -> dict:
        """Collect widget values into a params dict keyed by param_key."""
        if prov_type == "key":
            mode_fields = self._key_prov_fields.get(boot_mode, {})
        else:
            mode_fields = self._code_prov_fields.get(boot_mode, {})

        params: dict = {}
        for fid, fw in mode_fields.items():
            spec = fw.get("spec", {})
            param_key = spec.get("param_key", fid)
            wtype = spec.get("widget_type", "file_browse")
            widget = fw.get("input")
            check = fw.get("check")

            if widget is None:
                params[param_key] = None
                continue

            if wtype == "serial_combo":
                params[param_key] = widget.currentText()
            elif wtype == "optional_file":
                if check and not check.isChecked():
                    params[param_key] = None
                else:
                    params[param_key] = widget.text().strip() or None
            else:
                params[param_key] = widget.text().strip() or None
        return params

    def on_provision_clicked(self, prov_type: str, boot_mode: str):
        """Generic provision button handler for any prov_type + boot_mode."""
        adv_key = f"{prov_type}_{boot_mode}"
        tab = self._prov_tab_store.get(adv_key)

        if tab:
            # --- Custom tab path ---
            valid, err = tab.validate()
            if not valid:
                self._show_error(err)
                return
            meta = tab.get_task_meta()
            params = tab.collect_params()
            task_key = meta["task_key"]
            is_stream = meta["stream"]
            requires_reset = meta["requires_reset_before"]
        else:
            # --- JSON-driven path ---
            if not self._validate_fields(prov_type, boot_mode):
                return

            mode_spec = get_provisioning_ui_for_device(self.device_name or "", prov_type, boot_mode)
            if not mode_spec:
                self._show_error(f"No provisioning spec found for {prov_type}/{boot_mode}")
                return

            self._update_default_paths(prov_type)

            task_key = mode_spec.get("task_key", f"{boot_mode.lower()}_{prov_type}prov")
            is_stream = mode_spec.get("stream", False)
            requires_reset = mode_spec.get("requires_reset_before", False)

            params = self._collect_params(prov_type, boot_mode)

            # Build input_parameter for code provisioning
            if prov_type == "code":
                mode_fields = self._code_prov_fields.get(boot_mode, {})
                input_params = []
                for fid, fw in mode_fields.items():
                    spec = fw.get("spec", {})
                    pid = spec.get("parameter_id")
                    if not pid:
                        continue
                    check = fw.get("check")
                    required = spec.get("required", False)
                    if required or (check and check.isChecked()):
                        input_params.append(pid)
                params["input_parameter"] = ",".join(input_params)
                if not params["input_parameter"]:
                    self._show_error("Please select at least one component to provision")
                    return

        # --- Common setup ---
        params["device"] = self.session_info.get('device', '')

        from apps.qtgui.devices.register import get_boot_mode_specs_for_device
        bm_specs = get_boot_mode_specs_for_device(self.session_info.get('device', '').lower())
        bm_spec = next((s for s in bm_specs if s["id"] == boot_mode), {})
        for k, v in bm_spec.get("extra_params", {}).items():
            params.setdefault(k, v)
        for k in bm_spec.get("session_params", []):
            params[k] = self.session_info.get(k, '')

        # Pre-provisioning reset dialog
        if requires_reset:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setText("Please reset the device and press OK to continue")
            msg.setWindowTitle("Device Reset Required")
            msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
            ok_btn = msg.button(QMessageBox.Ok)
            if ok_btn:
                ok_btn.setText("OK")
            if msg.exec_() != QMessageBox.Ok:
                return

        prov_btn = self._prov_buttons.get(adv_key)

        if is_stream:
            # Streaming (code provisioning)
            stages = meta.get("progress_stages", []) if tab else \
                     mode_spec.get("progress_stages", [])
            self.progress_dialog = ProvisioningProgressDialog(
                prov_type, boot_mode, stages, self
            )
            self.progress_dialog.cancel_requested.connect(self._handle_cancel_provisioning)

            def on_finished():
                if self.progress_dialog and self.progress_dialog.isVisible():
                    self.progress_dialog.accept()
                self._active_worker = None

            def on_result(success, message):
                self.handle_code_operation_result(success, message)

            def on_error(error_message):
                if self.progress_dialog and self.progress_dialog.isVisible():
                    self.progress_dialog.accept()
                self._active_worker = None
                error_box = QMessageBox()
                error_box.setIcon(QMessageBox.Critical)
                error_box.setText(f"{boot_mode} Code Provisioning Failed")
                error_box.setInformativeText(error_message)
                error_box.setWindowTitle("Error")
                error_box.setStandardButtons(QMessageBox.Ok)
                error_box.exec_()

            def on_output(output):
                self.progress_dialog.update_from_output(output)

            self.progress_dialog.show()
            self._active_worker = stream_provisioning_output(
                task_key, params,
                output_callback=on_output,
                finished_callback=on_finished,
                result_callback=on_result,
                error_callback=on_error,
            )
        else:
            # Non-streaming (key provisioning)
            self.progress = create_progress_dialog(self, "Please Wait", f"Provisioning keys via {boot_mode}...")
            cancel_button = self.progress.findChild(QPushButton)
            if cancel_button:
                try:
                    cancel_button.clicked.disconnect()
                except TypeError:
                    pass
                cancel_button.clicked.connect(self._handle_cancel_provisioning)

            def on_finished():
                self.progress.close()
                self._active_worker = None

            def on_result(success, message):
                if prov_btn:
                    self._update_button_ui(prov_btn, success=success, operation_type="Keys")
                self.provisioning_log_data = self.parse_provisioning_logs(message)
                self.update_session_info_from_logs()
                self.provisioning_details_panel.set_provisioning_log_data(self.provisioning_log_data)
                self._show_detailed_results_dialog()
                if success:
                    self._show_power_reset_dialog()

            def on_error(error_message):
                self.progress.close()
                self._active_worker = None
                error_box = QMessageBox()
                error_box.setIcon(QMessageBox.Critical)
                error_box.setText(f"{boot_mode} Key Provisioning Failed")
                error_box.setInformativeText(error_message)
                error_box.setWindowTitle("Error")
                error_box.setStandardButtons(QMessageBox.Ok)
                error_box.exec_()

            self.progress.show()
            self._active_worker = start_provisioning_task(
                task_key, params,
                on_finished=on_finished,
                on_result=on_result,
                on_error=on_error,
            )

    def _update_mandatory_field_status(self, prov_type: str, field_id: str, mandatory: bool):
        """Show/hide the (Mandatory) label and auto-check an optional_file field."""
        if prov_type == "key":
            fields_by_mode = self._key_prov_fields
        else:
            fields_by_mode = self._code_prov_fields

        for boot_mode, mode_fields in fields_by_mode.items():
            fw = mode_fields.get(field_id)
            if not fw:
                continue
            check = fw.get("check")
            ml = fw.get("mandatory_label")
            if ml:
                ml.setVisible(mandatory)
            if check and mandatory:
                check.setChecked(True)
                check.setEnabled(False)
            elif check and not mandatory:
                check.setEnabled(True)

    def _enable_provisioning_buttons(self, prov_type: str, enable: bool):
        """Enable or disable all provision buttons for the given prov_type."""
        prefix = f"{prov_type}_"
        for key, btn in self._prov_buttons.items():
            if key.startswith(prefix):
                btn.setEnabled(enable)
                if not enable:
                    btn.setText("Already Provisioned" if prov_type == "key" else "N/A")
                    btn.setStyleSheet("""
                        QPushButton {
                            background-color: #cccccc; color: #666666;
                            padding: 6px 15px; border: none; border-radius: 3px; min-width: 160px;
                        }
                    """)

    def _handle_cancel_provisioning(self):
        """Kill the active subprocess and update UI to reflect cancellation."""
        if hasattr(self, '_active_worker') and self._active_worker is not None:
            self._active_worker.cancel()
        if self.progress_dialog and self.progress_dialog.isVisible():
            self.progress_dialog.overall_status_label.setText("Cancelling operation... Please wait.")
            self.progress_dialog.overall_status_label.setStyleSheet("color: #FF9800; font-weight: bold;")
        elif hasattr(self, 'progress') and self.progress:
            self.progress.setLabelText("Cancelling operation...")
            self.progress.setCancelButton(None)

    def cleanup_active_operations(self):
        """Kill any running provisioning subprocess. Called on application close."""
        if hasattr(self, '_active_worker') and self._active_worker is not None:
            self._active_worker.cancel()
    
    def _show_error(self, message):
        """Show error message dialog"""
        error_box = QMessageBox()
        error_box.setIcon(QMessageBox.Warning)
        error_box.setText(message)
        error_box.setWindowTitle("Error")
        error_box.exec_()
    
    def get_provisioning_data(self):
        """Get provisioning data"""
        return self.provisioning_data
        
    def update_session_info_from_logs(self):
        """Update session info display with parsed log data"""
        if not self.provisioning_log_data:
            return

        # Lazily add summary + seccfg rows to the session panel
        self._session_panel.add_provisioning_summary(self.provisioning_log_data)
        self.seccfg_status_label = self._session_panel.add_seccfg_status()

        # Compile summary from log data
        device_info = self.provisioning_log_data.get('device_info', {})
        key_provisioning = self.provisioning_log_data.get('key_provisioning', {})
        code_provisioning = self.provisioning_log_data.get('code_provisioning', {})

        # Create a summary text with more details
        summary_text = ""

        # Add device info summary
        if device_info:
            soc_type = device_info.get('SOC Type', 'Unknown')
            device_type = device_info.get('Device Type', 'Unknown')
            hsm_type = device_info.get('HSM Type', 'Unknown')
            bin_type = device_info.get('Binary Type', 'Unknown')

            summary_text += f"<b>{soc_type} {device_type}</b>: {hsm_type}, {bin_type}<br>"

        # Add KEY PROVISIONING summary
        key_success = key_provisioning.get('success_messages', [])
        key_programming = key_provisioning.get('key_programming', {})

        if key_programming or key_success:
            summary_text += "<b>Key provisioning completed:</b><br>"

            # Show key component statuses
            if key_programming:
                successful = [k for k, v in key_programming.items() if v == 'Success']
                if successful:
                    summary_text += f"<small>✓ {len(successful)} key components programmed successfully</small><br>"

            # Show OTP status messages
            if key_success:
                for message in key_success[:3]:
                    summary_text += f"<small>✓ {message}</small><br>"

        # Add CODE PROVISIONING summary
        code_success = code_provisioning.get('success_messages', [])
        if code_success:
            summary_text += "<b>Code provisioning completed successfully:</b><br>"
            for message in code_success:
                summary_text += f"<small>✓ {message}</small><br>"

            # Check specifically for SecCfg loading success
            seccfg_success = any('SecCfg Loading is successful' in msg for msg in code_success)
            if seccfg_success:
                summary_text += "<small style='color: #28a745; font-weight: bold;'>✓ Security Configuration loaded successfully</small><br>"
                # Update dedicated SecCfg status label
                self.seccfg_status_label.setText("Loaded Successfully ✓")
                self.seccfg_status_label.setStyleSheet("color: #28a745; font-weight: bold;")
                self.seccfg_status_label.setVisible(True)
            else:
                # Check if there were any SecCfg failures
                seccfg_failed = any('SecCfg' in error for error in self.provisioning_log_data.get('errors', []))
                if seccfg_failed:
                    self.seccfg_status_label.setText("Loading Failed ✗")
                    self.seccfg_status_label.setStyleSheet("color: #dc3545; font-weight: bold;")
                    self.seccfg_status_label.setVisible(True)
                else:
                    self.seccfg_status_label.setText("Not Loaded")
                    self.seccfg_status_label.setStyleSheet("color: #6c757d; font-weight: normal;")
                    self.seccfg_status_label.setVisible(False)

        # Update the label
        self._session_panel.provisioning_summary_label.setText(summary_text)
        self._session_panel.provisioning_summary_label.setVisible(True)
    
    def handle_operation_result(self, success, message):
        """Handle operation result from controller"""
        # Determine active boot mode from the generic prov_tabs
        boot_mode = "UART"
        if hasattr(self, 'prov_tabs') and self.prov_tabs.count() > 0:
            idx = self.prov_tabs.currentIndex()
            boot_mode = self.prov_tabs.tabText(idx) or "UART"
        btn = self._prov_buttons.get(f"key_{boot_mode}")

        if success:
            self.provisioning_log_data = self.parse_provisioning_logs(message)
            self.update_session_info_from_logs()
            if btn:
                self._update_button_ui(btn, success=True, operation_type="Keys")
            self._show_detailed_results_dialog()
            self._show_power_reset_dialog()
        else:
            if btn:
                self._update_button_ui(btn, success=False, operation_type="Keys")
            error_box = QMessageBox()
            error_box.setIcon(QMessageBox.Critical)
            error_box.setText("Keys Provisioning Failed")
            error_box.setInformativeText(message)
            error_box.setWindowTitle("Error")
            error_box.setStandardButtons(QMessageBox.Ok)
            error_box.exec_()
            
    def parse_provisioning_logs(self, log_text):
        """Parse provisioning logs to extract relevant information.
        
        This method delegates to the centralized parsing function.
        
        Returns:
            Dictionary containing parsed log data for backward compatibility
        """
        log_data = parse_provisioning_logs(log_text)
        # Check if we got a LogData object or dict and handle accordingly
        if isinstance(log_data, LogData):
            return log_data.to_dict()
        return log_data
        
    def _show_detailed_results_dialog(self):
        """Show detailed results from provisioning logs"""
        if not self.provisioning_log_data:
            return

        # Get the log manager
        log_manager = LogManager()

        # Determine the appropriate log file based on operation type
        # Check if this is code provisioning by looking for code-specific messages
        is_code_provisioning = False
        if self.provisioning_log_data and self.provisioning_log_data.get('code_provisioning', {}).get('success_messages'):
            is_code_provisioning = True
            log_file_path = log_manager.get_cp_log_path()
        else:
            # Default to key provisioning log
            log_file_path = log_manager.get_kp_log_path()

        # Create and show the dialog
        dialog = ProvisioningResultsDialog(
            parent=self,
            log_data=self.provisioning_log_data,
            log_file_path=log_file_path
        )
        dialog.exec_()
    
    # This method is no longer needed, functionality moved to ProvisioningResultsDialog
    def _legacy_open_log_file(self, file_path):
        """Legacy method, kept for backward compatibility"""
        try:
            # Use the default system application to open the log file
            if os.path.exists(file_path):
                QMessageBox.information(
                    self,
                    "Log File",
                    f"Opening log file: {file_path}\n\nNote: A debugResponse of 0x00000000 indicates successful programming despite the error message."
                )
                # Use platform-independent method to open file
                open_file(file_path)
            else:
                QMessageBox.warning(
                    self,
                    "File Not Found",
                    f"The log file {file_path} does not exist."
                )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to open log file: {str(e)}"
            )

    def _extract_error_details(self, message):
        """Extract error details from log message"""
        error_info = {
            'stage': 'Unknown',
            'command_code': None,
            'error_messages': [],
            'device_config': {}
        }

        if not message:
            return error_info

        lines = message.split('\n')
        last_device_config_index = -1

        for i, line in enumerate(lines):
            line = line.strip()

            # Detect failure stage
            if "HSM key provisioning" in line:
                error_info['stage'] = 'HSM Key Provisioning'
            elif "SBL kernel" in line:
                error_info['stage'] = 'SBL Kernel Loading'
            elif "baud rate" in line.lower():
                error_info['stage'] = 'UART Configuration'

            # Extract command code (get the last one before error)
            if "Command code:" in line:
                try:
                    error_info['command_code'] = line.split("Command code:")[1].strip()
                except:
                    pass

            # Extract error messages
            if "FAILURE:" in line or "NAK packet" in line or "error has occurred" in line.lower():
                error_info['error_messages'].append(line)

            # Track device configuration sections
            if "Device configuration:" in line:
                last_device_config_index = i

        # Extract the last device configuration before errors (the one that failed)
        if last_device_config_index >= 0:
            j = last_device_config_index + 1
            while j < len(lines) and j < last_device_config_index + 10:
                config_line = lines[j].strip()
                if config_line and ':' in config_line and not config_line.startswith('Device'):
                    # Skip lines that look like status messages
                    if any(skip in config_line.lower() for skip in ['received', 'target', 'waiting', 'downloading', 'sending']):
                        break
                    try:
                        key, value = config_line.split(':', 1)
                        error_info['device_config'][key.strip()] = value.strip()
                    except:
                        pass
                elif config_line == "" or config_line.startswith('Downloading') or config_line.startswith('Received'):
                    break
                j += 1

        return error_info

    def _show_key_provisioning_failure_details(self, error_details=None):
        """Show detailed failure dialog with all expected key provisioning fields

        Args:
            error_details: Optional dict with error information extracted from logs
        """
        dialog = QDialog(self)
        dialog.setWindowTitle("Key Provisioning Failed - Details")
        dialog.setMinimumWidth(650)
        dialog.setMinimumHeight(550)

        layout = QVBoxLayout(dialog)

        # Title
        title_label = QLabel("<b>Key Provisioning Failed</b>")
        title_label.setStyleSheet("font-size: 14px; color: #dc3545; padding: 10px;")
        layout.addWidget(title_label)

        # Show error details if available
        if error_details and error_details.get('error_messages'):
            error_group = QGroupBox("Error Information")
            error_layout = QVBoxLayout(error_group)

            # Stage information
            stage_label = QLabel(f"<b>Failed at stage:</b> {error_details.get('stage', 'Unknown')}")
            stage_label.setStyleSheet("color: #721c24; padding: 5px;")
            error_layout.addWidget(stage_label)

            # Command code if available
            if error_details.get('command_code'):
                cmd_label = QLabel(f"<b>Command code:</b> {error_details['command_code']}")
                cmd_label.setStyleSheet("color: #721c24; padding: 5px;")
                error_layout.addWidget(cmd_label)

            # Error messages
            error_msg_label = QLabel("<b>Error messages:</b>")
            error_msg_label.setStyleSheet("color: #721c24; padding: 5px;")
            error_layout.addWidget(error_msg_label)

            for msg in error_details['error_messages']:
                msg_label = QLabel(f"  • {msg}")
                msg_label.setWordWrap(True)
                msg_label.setStyleSheet("color: #dc3545; padding: 2px 5px; font-family: monospace; font-size: 10px;")
                error_layout.addWidget(msg_label)

            # Device configuration if available
            if error_details.get('device_config'):
                config_label = QLabel("<b>Device Configuration:</b>")
                config_label.setStyleSheet("color: #721c24; padding: 5px; margin-top: 5px;")
                error_layout.addWidget(config_label)

                for key, value in error_details['device_config'].items():
                    config_item = QLabel(f"  • {key}: {value}")
                    config_item.setWordWrap(True)
                    config_item.setStyleSheet("color: #721c24; padding: 2px 5px; font-size: 10px;")
                    error_layout.addWidget(config_item)

            layout.addWidget(error_group)

        # Description
        if error_details and error_details.get('error_messages'):
            desc_text = (
                "The key provisioning operation encountered an error during execution. "
                "The following key components were expected to be programmed but may not have been completed:"
            )
        else:
            desc_text = (
                "The key provisioning process failed without producing detailed logs. "
                "The following key components were expected to be programmed but their status is unknown:"
            )

        desc_label = QLabel(desc_text)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("padding: 5px 10px;")
        layout.addWidget(desc_label)

        # Scroll area for the list
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)

        # Expected key components for F29H85x
        expected_components = [
            ("SMPK (Secure MPK)", "Secure Manufacturing Protection Key"),
            ("BMPK (Backup MPK)", "Backup Manufacturing Protection Key"),
            ("SMEK (Secure MEK)", "Secure Manufacturing Encryption Key"),
            ("BMEK (Backup MEK)", "Backup Manufacturing Encryption Key"),
            ("KEYREV (Key Revision)", "Key Revision Field"),
            ("KEYCOUNT (Key Count)", "Key Count Field"),
            ("SWREV (Software Revision)", "Software Revision Field"),
            ("BSWAES (BSWAES Key)", "Boot Software AES Key"),
            ("USER OTP ROWS", "User OTP Configuration Rows"),
            ("Debug Extension", "Debug Extension Configuration"),
            ("Certificate", "Device Certificate")
        ]

        # Group box for components
        components_group = QGroupBox("Expected Key Components")
        components_layout = QVBoxLayout(components_group)

        for component_name, component_desc in expected_components:
            # Create a frame for each component
            component_frame = QFrame()
            component_frame.setFrameShape(QFrame.StyledPanel)
            component_frame.setStyleSheet("""
                QFrame {
                    background-color: #f8d7da;
                    border: 1px solid #f5c6cb;
                    border-radius: 4px;
                    padding: 8px;
                    margin: 2px;
                }
            """)

            frame_layout = QHBoxLayout(component_frame)
            frame_layout.setContentsMargins(10, 5, 10, 5)

            # Status icon
            status_icon = QLabel("❌")
            status_icon.setStyleSheet("font-size: 16px;")
            frame_layout.addWidget(status_icon)

            # Component info
            info_layout = QVBoxLayout()
            name_label = QLabel(f"<b>{component_name}</b>")
            name_label.setStyleSheet("color: #721c24;")
            info_layout.addWidget(name_label)

            desc_label_item = QLabel(component_desc)
            desc_label_item.setStyleSheet("color: #721c24; font-size: 10px;")
            info_layout.addWidget(desc_label_item)

            frame_layout.addLayout(info_layout)

            # Status
            status_label = QLabel("<i>Not Programmed / Unknown</i>")
            status_label.setStyleSheet("color: #721c24;")
            status_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            frame_layout.addWidget(status_label)

            components_layout.addWidget(component_frame)

        scroll_layout.addWidget(components_group)
        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)

        # Additional information
        info_group = QGroupBox("Troubleshooting Guide")
        info_layout = QVBoxLayout(info_group)

        # Determine connection type from session info
        connection_info = self.session_info.get('connection_info', {})
        connection_type = connection_info.get('type', 'unknown')

        if connection_type == 'uart':
            troubleshoot_text = (
                "<b>UART Connection Issues:</b><br>"
                "• Check that UART communication is consistent and stable<br>"
                "• Ensure the serial port buffer is empty before starting<br>"
                "• Verify the serial port is not being used by another application (minicom, PuTTY, etc.)<br>"
                "• Confirm the correct serial port is selected<br>"
                "• Verify the baud rate and other serial settings are correct<br><br>"
                "<b>General Checks:</b><br>"
                "• Verify the device is properly connected and powered<br>"
                "• Check that flash kernel and OTP keywriter binaries are valid<br>"
                "• Verify the device is in HSFS (Field Securable) state<br>"
                "• Reset the device and try again<br>"
                "• Check the log files for more detailed error information"
            )
        elif connection_type == 'jtag':
            troubleshoot_text = (
                "<b>JTAG Connection Issues:</b><br>"
                "• Verify the correct target configuration file (.ccxml) is being used for your device<br>"
                "• Ensure the JTAG port is not being used by another application (CCS debug session, etc.)<br>"
                "• Check that CCS installation path is correct<br>"
                "• Verify JTAG connections are secure and properly seated<br><br>"
                "<b>General Checks:</b><br>"
                "• Verify the device is properly connected and powered<br>"
                "• Check that flash kernel and OTP keywriter binaries are valid<br>"
                "• Verify the device is in HSFS (Field Securable) state<br>"
                "• Reset the device and try again<br>"
                "• Check the log files for more detailed error information"
            )
        else:
            troubleshoot_text = (
                "• Verify the device is properly connected and powered<br>"
                "• Ensure the connection port is correctly configured<br>"
                "• Check that the flash kernel and OTP keywriter binaries are valid<br>"
                "• Verify the device is in HSFS (Field Securable) state<br>"
                "• Check that the connection port is not being used by another application<br>"
                "• Reset the device and try again<br>"
                "• Check the log files for more detailed error information"
            )

        info_text = QLabel(troubleshoot_text)
        info_text.setWordWrap(True)
        info_text.setStyleSheet("padding: 5px;")
        info_layout.addWidget(info_text)

        layout.addWidget(info_group)

        # Buttons
        button_layout = QHBoxLayout()

        close_button = QPushButton("Close")
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                padding: 8px 20px;
                border: none;
                border-radius: 4px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        close_button.clicked.connect(dialog.accept)
        button_layout.addStretch()
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

        dialog.exec_()
    
    def _show_power_reset_dialog(self, provisioning_type="Keys"):
        """Show power reset dialog after provisioning
        
        Args:
            provisioning_type: String indicating the type of provisioning ("Keys" or "Code")
        """
        # Create dialog instructing user to power reset device
        reset_dialog = QMessageBox()
        reset_dialog.setIcon(QMessageBox.Information)
        reset_dialog.setText(f"{provisioning_type} provisioning complete. Please power reset the device now.")
        reset_dialog.setInformativeText("Click 'Done' after the device has been reset.")
        reset_dialog.setWindowTitle("Power Reset Required")
        reset_dialog.setStandardButtons(QMessageBox.Ok)
        done_button = reset_dialog.button(QMessageBox.Ok)
        done_button.setText("Done")
        reset_dialog.exec_()
        
        # After user confirms reset, verify device state change
        self._verify_device_state_change(provisioning_type=provisioning_type)

    def _show_code_provisioning_error_dialog(self, error_message):
        """Show detailed error dialog for code provisioning failures with troubleshooting guide.

        Args:
            error_message: The error message from the provisioning operation
        """
        dialog = QDialog(self)
        dialog.setWindowTitle("Code Provisioning Failed - Troubleshooting")
        dialog.setMinimumWidth(700)
        dialog.setMinimumHeight(600)

        layout = QVBoxLayout(dialog)

        # Title
        title_label = QLabel("<b>Code Provisioning Failed</b>")
        title_label.setStyleSheet("font-size: 14px; color: #dc3545; padding: 10px;")
        layout.addWidget(title_label)

        # Error message
        error_group = QGroupBox("Error Details")
        error_layout = QVBoxLayout(error_group)

        error_text = QLabel(error_message)
        error_text.setWordWrap(True)
        error_text.setStyleSheet("color: #721c24; padding: 5px; font-family: monospace;")
        error_layout.addWidget(error_text)
        layout.addWidget(error_group)

        # Troubleshooting guide
        troubleshoot_group = QGroupBox("Troubleshooting Guide")
        troubleshoot_layout = QVBoxLayout(troubleshoot_group)

        # Determine connection type from session info
        connection_info = self.session_info.get('connection_info', {})
        connection_type = connection_info.get('type', 'unknown')

        if connection_type == 'uart':
            troubleshoot_text = (
                "<b>UART Connection Issues:</b><br>"
                "• Check that UART communication is consistent and stable<br>"
                "• Ensure the serial port buffer is empty before starting<br>"
                "• Verify the serial port is not being used by another application (minicom, PuTTY, etc.)<br>"
                "• Confirm the correct serial port is selected<br>"
                "• Verify the baud rate and other serial settings are correct<br><br>"
                "<b>Code Provisioning Specific:</b><br>"
                "• Verify that the correct session keys are being used for signing binaries<br>"
                "• Check that the flash is set to erasable mode<br>"
                "• Ensure HSM image, HSM CPU code, C29 CPU code, and SecCfg files are valid and correctly signed<br>"
                "• Verify that the device is in HSKP (Key Provisioned) state before code provisioning<br>"
                "• Check that the SecCfg matches the device configuration<br><br>"
                "<b>General Checks:</b><br>"
                "• Verify the device is properly connected and powered<br>"
                "• Reset the device and try again<br>"
                "• Check the log files for more detailed error information"
            )
        elif connection_type == 'jtag':
            troubleshoot_text = (
                "<b>JTAG Connection Issues:</b><br>"
                "• Verify the correct target configuration file (.ccxml) is being used for your device<br>"
                "• Ensure the JTAG port is not being used by another application (CCS debug session, etc.)<br>"
                "• Check that CCS installation path is correct<br>"
                "• Verify JTAG connections are secure and properly seated<br><br>"
                "<b>Code Provisioning Specific:</b><br>"
                "• Verify that the correct session keys are being used for signing binaries<br>"
                "• Check that the flash is set to erasable mode<br>"
                "• Ensure HSM image, HSM CPU code, C29 CPU code, and SecCfg files are valid and correctly signed<br>"
                "• Verify that the device is in HSKP (Key Provisioned) state before code provisioning<br>"
                "• Check that the SecCfg matches the device configuration<br><br>"
                "<b>General Checks:</b><br>"
                "• Verify the device is properly connected and powered<br>"
                "• Reset the device and try again<br>"
                "• Check the log files for more detailed error information"
            )
        else:
            troubleshoot_text = (
                "<b>Code Provisioning Specific:</b><br>"
                "• Verify that the correct session keys are being used for signing binaries<br>"
                "• Check that the flash is set to erasable mode<br>"
                "• Ensure HSM image, HSM CPU code, C29 CPU code, and SecCfg files are valid and correctly signed<br>"
                "• Verify that the device is in HSKP (Key Provisioned) state before code provisioning<br>"
                "• Check that the SecCfg matches the device configuration<br><br>"
                "<b>General Checks:</b><br>"
                "• Verify the device is properly connected and powered<br>"
                "• Ensure the connection port is correctly configured<br>"
                "• Check that the connection port is not being used by another application<br>"
                "• Reset the device and try again<br>"
                "• Check the log files for more detailed error information"
            )

        troubleshoot_label = QLabel(troubleshoot_text)
        troubleshoot_label.setWordWrap(True)
        troubleshoot_label.setStyleSheet("padding: 5px;")
        troubleshoot_layout.addWidget(troubleshoot_label)
        layout.addWidget(troubleshoot_group)

        # Common issues section
        common_group = QGroupBox("Common Issues")
        common_layout = QVBoxLayout(common_group)

        common_text = QLabel(
            "<b>1. Signing Key Mismatch:</b> Ensure binaries are signed with keys matching the device's provisioned keys<br><br>"
            "<b>2. Flash Not Erasable:</b> Flash must be set to erasable in the device configuration<br><br>"
            "<b>3. Device Not in HSKP State:</b> Device must be key-provisioned (HSKP) before code provisioning<br><br>"
            "<b>4. Binary Corruption:</b> Verify integrity of HSM image, CPU code, and SecCfg files"
        )
        common_text.setWordWrap(True)
        common_text.setStyleSheet("padding: 5px;")
        common_layout.addWidget(common_text)
        layout.addWidget(common_group)

        # Buttons
        button_layout = QHBoxLayout()

        close_button = QPushButton("Close")
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                padding: 8px 20px;
                border: none;
                border-radius: 4px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        close_button.clicked.connect(dialog.accept)
        button_layout.addStretch()
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

        dialog.exec_()

    def _verify_device_state_change(self, provisioning_type="Keys"):
        """Start post-provisioning state detection via the worker module."""
        progress = QProgressDialog("Verifying device state...", None, 0, 0, self)
        progress.setWindowTitle("Please Wait")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setCancelButton(None)
        progress.setMinimumDuration(0)
        progress.show()

        connection_info = self.session_info.get('connection_info', {})
        conn_type = connection_info.get('type', '')
        boot_mode = 'UART' if conn_type == 'uart' else 'JTAG' if conn_type == 'jtag' else ''

        if not boot_mode:
            progress.close()
            self._show_error("Unknown connection type")
            return

        def _on_complete(result):
            progress.close()
            self._handle_state_verification_result(result, provisioning_type)

        self._detection_worker = run_post_provisioning_detection(
            device_name=self.device_name or '',
            boot_mode=boot_mode,
            connection_info=connection_info,
            on_complete=_on_complete,
        )
    
    def _handle_state_verification_result(self, result, provisioning_type="Keys"):
        """Handle device state verification result
        
        Args:
            result: The detection result dictionary
            provisioning_type: String indicating the type of provisioning ("Keys" or "Code")
        """
        # Compute expected states dynamically from device registry
        prov_spec     = get_provisioning_spec_for_device(self.device_name or "")
        device_states = prov_spec.get("device_states", ["HSFS", "HSKP", "HSSE"])
        initial_state = prov_spec.get("initial_state", device_states[0] if device_states else "")
        final_state   = device_states[-1] if device_states else ""

        if provisioning_type == "Keys":
            expected_states = device_states[1:] if len(device_states) > 1 else [final_state]
        else:
            expected_states = [final_state]
        expected_states_str = " or ".join(expected_states)

        # Resolve the active boot mode and custom tab (if any) for result callbacks
        _svr_prov_str = "key" if provisioning_type == "Keys" else "code"
        _svr_tabs = self.prov_tabs if provisioning_type == "Keys" else self.code_prov_tabs
        _svr_bm = _svr_tabs.tabText(_svr_tabs.currentIndex()) if _svr_tabs.count() > 0 else "UART"
        _svr_tab = self._prov_tab_store.get(f"{_svr_prov_str}_{_svr_bm}")

        if result['success']:
            # Get detected device information
            device = result['device']
            device_state = result['device_state']

            if device_state in expected_states:
                # Success - state changed to expected state
                if provisioning_type == "Keys":
                    self._session_panel.set_key_prov_status("Completed ✓", "color: #28a745; font-weight: bold;")
                else:
                    self._session_panel.set_code_prov_status("Completed ✓", "color: #28a745; font-weight: bold;")

                if _svr_tab:
                    _svr_tab.on_provision_result(True)

                # Update session info with new device state
                if self.session_info:
                    self.session_info['device_state'] = device_state

                # Update the Device State label, indicator, and details panel
                self._session_panel.set_device_state(device_state, device_state)

                # Emit signal for device state change
                self.device_state_changed.emit(device_state)

                # Show success message
                success_type = "converted" if provisioning_type == "Keys" else "provisioned with code"
                QMessageBox.information(
                    self,
                    "Verification Successful",
                    f"Device successfully {success_type} to {device_state} state!"
                )

                # Enable code provisioning tab when no longer in initial state
                if device_state != initial_state:
                    self.main_tabs.setTabVisible(0, False)  # Hide key provisioning tab
                    self.main_tabs.setTabEnabled(1, True)   # Enable code provisioning tab
                    self._enable_code_provisioning_buttons(True)
                    self.main_tabs.setCurrentIndex(1)
            else:
                # Failed - state didn't change to expected state
                if provisioning_type == "Keys":
                    self._session_panel.set_key_prov_status("Failed ✗", "color: #dc3545; font-weight: bold;")
                else:
                    self._session_panel.set_code_prov_status("Failed ✗", "color: #dc3545; font-weight: bold;")

                if _svr_tab:
                    _svr_tab.on_provision_result(False)

                # Update session info and Device State label with actual detected state
                if self.session_info:
                    self.session_info['device_state'] = device_state
                self._session_panel.device_state_label.setText(device_state)

                # Update the active tab's button to show failure
                tabs = self.prov_tabs if provisioning_type == "Keys" else self.code_prov_tabs
                bm = tabs.tabText(tabs.currentIndex()) if tabs.count() > 0 else "UART"
                btn = self._prov_buttons.get(f"{'key' if provisioning_type == 'Keys' else 'code'}_{bm}")
                if btn:
                    self._update_button_ui(btn, success=False, operation_type=provisioning_type)

                QMessageBox.warning(
                    self,
                    "Verification Failed",
                    f"Device is in {device_state} state. Expected {expected_states_str} state after {provisioning_type.lower()} provisioning."
                )
        else:
            # Detection failed
            if provisioning_type == "Keys":
                self._session_panel.set_key_prov_status("Failed ✗", "color: #dc3545; font-weight: bold;")
            else:
                self._session_panel.set_code_prov_status("Failed ✗", "color: #dc3545; font-weight: bold;")

            if _svr_tab:
                _svr_tab.on_provision_result(False)

            # Update the active tab's button to show failure
            tabs = self.prov_tabs if provisioning_type == "Keys" else self.code_prov_tabs
            bm = tabs.tabText(tabs.currentIndex()) if tabs.count() > 0 else "UART"
            btn = self._prov_buttons.get(f"{'key' if provisioning_type == 'Keys' else 'code'}_{bm}")
            if btn:
                self._update_button_ui(btn, success=False, operation_type=provisioning_type)

            error = result.get('error', "Unknown error during device detection")
            QMessageBox.critical(
                self,
                "Verification Error",
                f"Failed to verify device state: {error}"
            )
            
    def handle_code_operation_result(self, success, message):
        """Handle code provisioning operation result from controller"""
        # Determine active boot mode from the generic code_prov_tabs
        boot_mode = "UART"
        if hasattr(self, 'code_prov_tabs') and self.code_prov_tabs.count() > 0:
            idx = self.code_prov_tabs.currentIndex()
            boot_mode = self.code_prov_tabs.tabText(idx) or "UART"
        btn = self._prov_buttons.get(f"code_{boot_mode}")
        _code_tab = self._prov_tab_store.get(f"code_{boot_mode}")

        if success:
            self.provisioning_log_data = self.parse_provisioning_logs(message)
            self.update_session_info_from_logs()
            self.provisioning_details_panel.set_provisioning_log_data(self.provisioning_log_data)
            self._session_panel.set_code_prov_status("Completed ✓", "color: #28a745; font-weight: bold;")
            prov_spec   = get_provisioning_spec_for_device(self.device_name or "")
            final_state = prov_spec.get("device_states", ["HSSE"])[-1]
            self._session_panel.set_device_state(final_state, final_state)
            if btn:
                self._update_button_ui(btn, success=True, operation_type="Code")
            if _code_tab:
                _code_tab.on_provision_result(True)
            self._show_detailed_results_dialog()
            self._show_power_reset_dialog(provisioning_type="Code")
        else:
            if btn:
                self._update_button_ui(btn, success=False, operation_type="Code")
            if _code_tab:
                _code_tab.on_provision_result(False)
            self._show_code_provisioning_error_dialog(message)
    
    def _update_button_ui(self, button, success=True, operation_type="Keys", show_message=False, message=""):
        """Update UI button and optionally show a message dialog
        
        Args:
            button: The button to update
            success: Whether the operation was successful
            operation_type: String indicating operation type ("Keys" or "Code")
            show_message: Whether to show a message dialog
            message: Message to display in the dialog
        """
        if success:
            # Success style
            button.setText(f"{operation_type} Provisioned ✓")
            button.setStyleSheet("""
                QPushButton {
                    background-color: #28a745;
                    color: white;
                    padding: 8px 20px;
                    border: none;
                    border-radius: 4px;
                    min-width: 180px;
                }
                QPushButton:hover {
                    background-color: #218838;
                }
            """)
            
            # Show success message if requested
            if show_message:
                QMessageBox.information(
                    self,
                    "Success",
                    f"{operation_type} has been successfully provisioned\n\n{message}"
                )
        else:
            # Failure style
            button.setText(f"{operation_type} Provisioning Failed")
            button.setStyleSheet("""
                QPushButton {
                    background-color: #dc3545;
                    color: white;
                    padding: 8px 20px;
                    border: none;
                    border-radius: 4px;
                    min-width: 180px;
                }
                QPushButton:hover {
                    background-color: #c82333;
                }
            """)
            
            # Show error message if requested
            if show_message:
                error_box = QMessageBox()
                error_box.setIcon(QMessageBox.Critical)
                error_box.setText(f"{operation_type} Provisioning Failed")
                error_box.setInformativeText(message)
                error_box.setWindowTitle("Error")
                error_box.setStandardButtons(QMessageBox.Ok)
                error_box.exec_()
        
    def _populate_serial_ports(self, combo_box):
        """Populate serial port dropdown"""
        combo_box.clear()
        
        # Get available ports
        # Import already done at module level
        ports = serial.tools.list_ports.comports()
        if ports:
            for port in ports:
                combo_box.addItem(format_serial_port_name(port.device))
        else:
            combo_box.addItem("No ports found")
            
        # Select the previously selected port if there was one
        connection_info = self.session_info.get('connection_info', {})
        if connection_info and connection_info.get('type') == 'uart' and 'port' in connection_info:
            port = connection_info['port']
            index = combo_box.findText(port)
            if index >= 0:
                combo_box.setCurrentIndex(index)


    def _enable_code_provisioning_buttons(self, enable=True):
        """Enable or disable all code provisioning buttons"""
        self._enable_provisioning_buttons("code", enable)
    
    def _toggle_advanced_section(self, content_group, header_button):
        """Toggle the visibility of the advanced settings section
        
        Args:
            content_group: The QGroupBox containing the advanced settings
            header_button: The button that toggles the section
        """
        # Get current visibility state
        is_visible = content_group.isVisible()
        
        # Toggle visibility
        content_group.setVisible(not is_visible)
        
        # Update button text with appropriate arrow
        if not is_visible:
            # Expanding, show down arrow
            header_button.setText("▼ Advanced Settings")
            
            # When expanded, header has rounded top corners only
            header_button.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 5px 8px;
                    font-weight: bold;
                    font-size: 11px;
                    background-color: #CC0000;
                    color: white;
                    border: 1px solid #990000;
                    border-radius: 4px 4px 0 0;
                    border-bottom: none;
                }
                QPushButton:hover {
                    background-color: #990000;
                }
            """)
            
            # Increase container height when advanced section expands
            prov_type_prop = content_group.property("prov_type")
            if prov_type_prop == "key":
                self.prov_group.setMaximumHeight(16777215)
                self.prov_tabs.setMaximumHeight(16777215)
            elif prov_type_prop == "code":
                self.code_prov_group.setMaximumHeight(16777215)
                self.code_prov_tabs.setMaximumHeight(16777215)
            self.main_tabs.setMaximumHeight(16777215)
                
        else:
            # Collapsing, show right arrow
            header_button.setText("▶ Advanced Settings")
            
            # When collapsed, header has all rounded corners
            header_button.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 5px 8px;
                    font-weight: bold;
                    font-size: 11px;
                    background-color: #CC0000;
                    color: white;
                    border: 1px solid #990000;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #990000;
                }
            """)
            
            # generic groups (key/code) don't have a capped height
    
