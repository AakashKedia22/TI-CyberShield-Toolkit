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
    QTabWidget,
    QScrollArea,
    QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread, pyqtSlot, QObject
from PyQt5.QtWidgets import QApplication
import threading
import serial.tools.list_ports
from apps.qtgui.utils.platform_utils import format_serial_port_name, get_serial_port_filter, get_home_directory, join_path_components, get_addon_root
from common.device_utils import get_device_prebuilt_dir, get_device_output_dir, infer_device_family
from common.platform_utils import kill_proc_tree
import os
import getpass
import tempfile
import sys
from pathlib import Path
from apps.qtgui.soc_id_detector import detect_device_from_port


class SocIdDetectionThread(QThread):
    """Thread for handling SoC ID detection without blocking the UI"""
    detection_complete = pyqtSignal(dict)
    
    def __init__(self, port):
        super().__init__()
        self.port = port
        
    def run(self):
        """Run the detection process"""
        # Call the detection function
        result = detect_device_from_port(self.port)
        # Emit the result
        self.detection_complete.emit(result)


class DeviceDetectionThread(QThread):
    """Generic detection thread — delegates to the device/boot-mode-specific callable."""
    detection_complete = pyqtSignal(dict)

    def __init__(self, device_name: str, boot_mode_id: str, connection_info: dict):
        super().__init__()
        self.device_name = device_name
        self.boot_mode_id = boot_mode_id
        self.connection_info = connection_info
        self._cancel_event = threading.Event()
        self._active_proc = None
        self._proc_lock = threading.Lock()

    def cancel(self) -> None:
        """Request cancellation and kill any running subprocess immediately."""
        self._cancel_event.set()
        with self._proc_lock:
            if self._active_proc is not None and self._active_proc.poll() is None:
                kill_proc_tree(self._active_proc)

    def _register_proc(self, proc) -> None:
        """Store subprocess reference so cancel() can kill it."""
        with self._proc_lock:
            self._active_proc = proc

    def run(self):
        from apps.qtgui.devices.register import get_detect_spec_for_device
        spec = get_detect_spec_for_device(self.device_name, self.boot_mode_id)
        detect_fn = spec.get("fn") if spec else None
        if detect_fn is None:
            self.detection_complete.emit({
                "success": False,
                "error": f"No detection function for {self.device_name}/{self.boot_mode_id}",
                "device": None, "device_state": None,
            })
            return
        try:
            ci = dict(self.connection_info)
            ci["_cancel_event"] = self._cancel_event
            ci["_register_proc"] = self._register_proc
            success, device_state, error = detect_fn(ci)
            if self._cancel_event.is_set():
                # Swallow the result — caller already handled the cancel
                return
            if success:
                self.detection_complete.emit({
                    "success": True,
                    "device": self.device_name,
                    "device_state": device_state,
                })
            else:
                self.detection_complete.emit({
                    "success": False, "error": error,
                    "device": None, "device_state": None,
                })
        except Exception as e:
            if not self._cancel_event.is_set():
                self.detection_complete.emit({
                    "success": False, "error": str(e),
                    "device": None, "device_state": None,
                })

class ConfigPage(QWidget):
    """Second page of the wizard with boot mode and certificate generation"""
    
    # Signals
    boot_mode_changed = pyqtSignal()
    device_detected = pyqtSignal(str, str)  # device, device_state
    device_detection_requested = pyqtSignal(str, dict)  # boot_mode, connection_info
    binary_signing_requested = pyqtSignal()  # No parameters needed for batch signing
    rot_cert_requested = pyqtSignal(dict)  # ROT certificate generation parameters
    debug_cert_requested = pyqtSignal(dict)  # Debug certificate generation parameters
    seccfg_cert_requested = pyqtSignal(dict)  # Sec-Cfg certificate generation parameters
    custom_binary_signing_requested = pyqtSignal(dict)  # Custom binary signing parameters
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.device = None
        self.device_name = None
        self.device_family = None
        self.key_type = None
        self.key_data = None
        self.ccs_path = None
        self.target_config_path = None
        self.certificate_info = None
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI components"""
        # Create a scroll area to make the entire page scrollable
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        
        # Create content widget for the scroll area
        content_widget = QWidget()
        
        # Main layout
        main_layout = QVBoxLayout(content_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Set the scroll area widget
        scroll_area.setWidget(content_widget)
        
        # Add scroll area to the page
        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll_area)
        
        # Page title
        title_label = QLabel("Configuration")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #CC0000;")
        main_layout.addWidget(title_label)
        
        # Key and device info section
        info_group = QGroupBox("Session Information")
        info_layout = QFormLayout()
        
        # Device label
        self.device_label = QLabel("No device selected")
        info_layout.addRow("Device:", self.device_label)
        
        # Key type label
        self.key_type_label = QLabel("No key selected")
        info_layout.addRow("Key Type:", self.key_type_label)
        
        # Session name label
        self.session_name_label = QLabel("")
        info_layout.addRow("Session Name:", self.session_name_label)
        
        # F29 Development session key types
        self.smpk_label = QLabel("")
        self.smpk_label.hide()  # Initially hidden
        info_layout.addRow("SMPK Key Type:", self.smpk_label)
        
        self.bmpk_label = QLabel("")
        self.bmpk_label.hide()  # Initially hidden
        info_layout.addRow("BMPK Key Type:", self.bmpk_label)
        
        # Certificate status label
        self.certificate_label = QLabel("Not generated")
        self.certificate_label.setStyleSheet("color: #ff9800; font-weight: bold;")
        info_layout.addRow("Certificate:", self.certificate_label)
        
        info_group.setLayout(info_layout)
        main_layout.addWidget(info_group)
        
        # Device connection group
        connection_group = QGroupBox("Device Connection")
        connection_layout = QVBoxLayout()
        
        # Boot mode
        boot_mode_layout = QFormLayout()
        boot_mode_layout.setContentsMargins(0, 0, 0, 0)
        self.boot_mode_dropdown = QComboBox()
        self.boot_mode_dropdown.currentTextChanged.connect(self._on_boot_mode_changed)
        boot_mode_layout.addRow("Boot Mode:", self.boot_mode_dropdown)
        connection_layout.addLayout(boot_mode_layout)
        
        # Serial port section (hidden initially)
        self.serial_group = QWidget()
        serial_layout = QFormLayout(self.serial_group)
        serial_layout.setContentsMargins(0, 10, 0, 0)
        
        self.serial_dropdown = QComboBox()
        serial_layout.addRow("Serial Port:", self.serial_dropdown)
        
        # Detect button
        self.detect_button = QPushButton("Detect Device")
        self.detect_button.clicked.connect(self._on_detect_clicked)
        self.detect_button.setStyleSheet("""
            QPushButton {
                background-color: #CC0000;
                color: white;
                padding: 5px 15px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #990000;
            }
        """)
        serial_layout.addRow("", self.detect_button)
        
        # Hide serial group initially
        self.serial_group.hide()
        connection_layout.addWidget(self.serial_group)
        
        # CCS path section (hidden initially)
        self.ccs_group = QWidget()
        ccs_layout = QFormLayout(self.ccs_group)
        ccs_layout.setContentsMargins(0, 10, 0, 0)
        
        ccs_input_layout = QHBoxLayout()
        self.ccs_path_input = QLineEdit()
        self.ccs_path_input.textChanged.connect(self._on_ccs_path_changed)
        ccs_browse_button = QPushButton("Browse")
        ccs_browse_button.clicked.connect(self._browse_ccs_path)
        ccs_input_layout.addWidget(self.ccs_path_input)
        ccs_input_layout.addWidget(ccs_browse_button)

        ccs_layout.addRow("CCS Path:", ccs_input_layout)
        
        # Detect button for JTAG
        self.jtag_detect_button = QPushButton("Detect Device")
        self.jtag_detect_button.clicked.connect(self._on_jtag_detect_clicked)
        self.jtag_detect_button.setStyleSheet("""
            QPushButton {
                background-color: #CC0000;
                color: white;
                padding: 5px 15px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #990000;
            }
        """)
        ccs_layout.addRow("", self.jtag_detect_button)
        
        # Hide CCS group initially
        self.ccs_group.hide()
        connection_layout.addWidget(self.ccs_group)
        
        # Device state input
        self.device_state_layout = QFormLayout()
        self.device_state_layout.setContentsMargins(0, 10, 0, 0)
        self.device_state_input = QLineEdit()
        self.device_state_input.setReadOnly(False)
        self.device_state_input.setPlaceholderText("HSFS, HSSE, etc. - Auto-detected or enter manually")
        self.device_state_layout.addRow("Device State:", self.device_state_input)
        connection_layout.addLayout(self.device_state_layout)
        
        connection_group.setLayout(connection_layout)
        main_layout.addWidget(connection_group)
        
        # Binary Signing Group
        binary_signing_group = QGroupBox("Binary Signing")
        binary_signing_layout = QVBoxLayout()
        
        # Description label
        description_label = QLabel(
            "Automatically sign all prebuilt binary images using the selected keys."
            " This will sign csd.bin and TIFS binaries"
            " with their optimal configurations."
        )
        description_label.setWordWrap(True)
        binary_signing_layout.addWidget(description_label)
        
        # Sign button
        self.sign_binary_button = QPushButton("Sign and Encrypt All Prebuilt Binaries")
        self.sign_binary_button.setStyleSheet("""
            QPushButton {
                background-color: #CC0000;
                color: white;
                padding: 8px 20px;
                border: none;
                border-radius: 4px;
                min-width: 180px;
            }
            QPushButton:hover {
                background-color: #990000;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.sign_binary_button.clicked.connect(self._on_sign_all_binaries)
        self.sign_binary_button.setEnabled(False)  # Disabled by default, enabled when F29H85x is selected
        binary_signing_layout.addWidget(self.sign_binary_button, 0, Qt.AlignCenter)
        
        binary_signing_group.setLayout(binary_signing_layout)
        main_layout.addWidget(binary_signing_group)
        
        # Create collapsible advanced certificate options (only visible for F29H85x devices)
        self.adv_cert_container = QWidget()
        self.adv_cert_container.setVisible(False)  # Initially hidden, shown only for F29H85x
        adv_cert_container_layout = QVBoxLayout(self.adv_cert_container)
        adv_cert_container_layout.setContentsMargins(0, 15, 0, 0)
        adv_cert_container_layout.setSpacing(0)
        
        # Header with collapsible toggle button
        adv_header_widget = QWidget()
        adv_header_widget.setCursor(Qt.PointingHandCursor)  # Change cursor to hand when hovering
        adv_header_widget.setStyleSheet("""
            QWidget {
                background-color: #f8f8f8;
                border: none;
                border-bottom: 2px solid #CC0000;
            }
            QWidget:hover {
                background-color: #f0f0f0;
            }
        """)
        
        adv_header_layout = QHBoxLayout(adv_header_widget)
        adv_header_layout.setContentsMargins(0, 8, 0, 8)
        
        # Add left margin for text
        spacer_left = QSpacerItem(15, 10, QSizePolicy.Fixed, QSizePolicy.Minimum)
        adv_header_layout.addItem(spacer_left)
        
        # Create an elegant dropdown indicator using an arrow icon
        self.adv_toggle_arrow = QLabel("▶")  # Right-facing triangle
        self.adv_toggle_arrow.setStyleSheet("""
            color: #CC0000;
            font-size: 12px;
            font-weight: bold;
        """)
        adv_header_layout.addWidget(self.adv_toggle_arrow)
        
        # Header text with professional styling
        adv_header_label = QLabel("Advanced Certificate Options")
        adv_header_label.setStyleSheet("""
            font-size: 14px; 
            font-weight: bold;
            color: #333333;
            padding-left: 8px;
        """)
        adv_header_layout.addWidget(adv_header_label)
        adv_header_layout.addStretch()
        
        # Create a filter to intercept mouse events for the header
        class ClickableWidgetFilter(QObject):
            def __init__(self, parent, callback):
                super().__init__(parent)
                self.callback = callback
                
            def eventFilter(self, obj, event):
                if event.type() == event.MouseButtonRelease:
                    self.callback()
                    return True
                return False
        
        # Install event filter to make header clickable
        click_filter = ClickableWidgetFilter(adv_header_widget, self._toggle_advanced_options)
        adv_header_widget.installEventFilter(click_filter)
        
        # Content area for advanced certificate options (initially collapsed)
        self.adv_cert_content = QWidget()
        self.adv_cert_content.setVisible(False)  # Initially collapsed
        
        # Create a tab widget for advanced certificate options
        adv_cert_content_layout = QVBoxLayout()
        adv_cert_content_layout.setContentsMargins(15, 20, 15, 30)  # Reduced left/right margins
        adv_cert_content_layout.setSpacing(24)  # Increase spacing between sections
        
        # Create tab widget
        self.adv_cert_tabs = QTabWidget()
        self.adv_cert_tabs.setDocumentMode(True)  # Makes tabs look more modern
        self.adv_cert_tabs.setUsesScrollButtons(False)  # Prevents scroll buttons from appearing
        self.adv_cert_tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #e0e0e0;
                background-color: white;
                border-radius: 4px;
            }
            QTabWidget::tab-bar {
                alignment: center;
            }
            QTabBar::tab {
                background-color: #f8f8f8;
                color: #333333;
                min-width: 200px;  /* Increased from 150px */
                padding: 8px 20px;  /* Increased horizontal padding */
                border: 1px solid #e0e0e0;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                margin-right: 4px;  /* Increased spacing between tabs */
                font-size: 13px;  /* Explicitly set font size */
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 2px solid #CC0000;
                font-weight: bold;
            }
            QTabBar::tab:hover {
                background-color: #f0f0f0;
            }
        """)
        
        # Tab widgets are built lazily — see adv_tabs/ registry
        self._adv_tab_store = {}   # tab_id → QWidget (populated on demand)
        # Tabs are populated by _update_advanced_tabs() on device selection
        
        # Add header and content to the container
        adv_cert_container_layout.addWidget(adv_header_widget)
        
        # Style the content area with an elegant design
        self.adv_cert_content.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
            }
        """)
        
        adv_cert_content_layout.addWidget(self.adv_cert_tabs)
        self.adv_cert_content.setLayout(adv_cert_content_layout)
        
        adv_cert_container_layout.addWidget(self.adv_cert_content)
        
        # Add the container to the main layout
        main_layout.addWidget(self.adv_cert_container)
        
        # Add spacer at the bottom
        main_layout.addStretch()
        
    def set_device(self, device):
        """Set device information and update UI"""
        self.device = device
        self.device_name = device.lower() if device else None
        self.device_family = infer_device_family(self.device_name) if self.device_name else None

        # Update device label
        self.device_label.setText(device)
        
        # Update boot modes based on device
        self.boot_mode_dropdown.clear()
        self.boot_mode_dropdown.addItem("")  # Empty first item
        
        from apps.qtgui.devices.register import get_boot_modes_for_device
        for boot_mode in get_boot_modes_for_device(self.device_name or ""):
            self.boot_mode_dropdown.addItem(boot_mode)
            
        # Update JTAG option status based on CCS path
        self._update_jtag_boot_mode_status()
        
        # Update binary signing button state
        self._update_binary_signing_button_state()
        
        # Update advanced certificate options visibility
        self._update_advanced_cert_options_visibility()
    
    def set_key_info(self, key_type, key_data):
        """Set key information and update UI"""
        self.key_type = key_type
        self.key_data = key_data
        
        # Update key type label
        key_type_display = {
            "new": "New Keys",
            "existing": "Existing Keys",
            "sdk": "SDK Dummy Keys",
            "pkcs11": "PKCS#11 Smart Card",
            "f29_development": "F29H85x Development Session"
        }
        
        self.key_type_label.setText(key_type_display.get(key_type, "Unknown"))
        
        # Update session name label if available
        if key_data and "name" in key_data:
            self.session_name_label.setText(key_data["name"])
        elif key_type == "f29_development":
            self.session_name_label.setText("Development")
        else:
            self.session_name_label.setText("")
            
        # Handle F29 Development session key types
        if key_type == "f29_development" and key_data:
            # Show and update SMPK and BMPK labels
            smpk_algo = key_data.get("smpk_algo", "rsa4k")
            bmpk_algo = key_data.get("bmpk_algo", "rsa4k")
            
            self.smpk_label.setText(smpk_algo)
            self.smpk_label.setStyleSheet("color: #006400; font-weight: bold;")  # Dark green
            self.smpk_label.show()
            
            self.bmpk_label.setText(bmpk_algo)
            self.bmpk_label.setStyleSheet("color: #006400; font-weight: bold;")  # Dark green
            self.bmpk_label.show()
        else:
            # Hide SMPK and BMPK labels for other key types
            self.smpk_label.hide()
            self.bmpk_label.hide()
            
        # Update binary signing button state
        self._update_binary_signing_button_state()
        
        # Update advanced certificate options visibility
        self._update_advanced_cert_options_visibility()
        
        # Update advanced certificate options visibility
        self._update_advanced_cert_options_visibility()
        
    def set_ccs_path(self, path):
        """Set CCS path from landing page"""
        self.ccs_path = path

        if hasattr(self, 'ccs_path_input') and self.ccs_path_input:
            self.ccs_path_input.setText(path)

        for widget in self._adv_tab_store.values():
            widget.set_ccs_path(path)

    def set_target_config_path(self, path):
        """Set target config path from landing page"""
        self.target_config_path = path

        # If boot mode dropdown is already initialized, update JTAG status
        if hasattr(self, 'boot_mode_dropdown') and self.boot_mode_dropdown is not None:
            self._update_jtag_boot_mode_status()
    
    def _update_paths_for_device(self, device):
        """Update paths based on selected device - no longer needed for certificates"""
        # Method kept for backward compatibility, but no longer does anything
        pass
    
    def _on_boot_mode_changed(self, boot_mode):
        """Handle boot mode selection change"""
        from apps.qtgui.devices.register import get_boot_mode_specs_for_device
        self.serial_group.hide()
        self.ccs_group.hide()

        specs = get_boot_mode_specs_for_device(self.device_name or "")
        spec = next((s for s in specs if s["id"] == boot_mode), None)

        if spec:
            if spec["connection_widget"] == "serial":
                self._populate_serial_ports()
                self.serial_group.show()
            elif spec["connection_widget"] == "ccs":
                if self.ccs_path:
                    self.ccs_path_input.setText(self.ccs_path)
                    self.ccs_group.show()
                else:
                    self._show_error(
                        f"CCS path is required for {boot_mode} boot mode. "
                        "Please enter CCS path on the home page.")
                    self.boot_mode_dropdown.setCurrentText("")
                    return

        # Emit signal for wizard navigation
        self.boot_mode_changed.emit()
    
    def _populate_serial_ports(self):
        """Populate serial ports dropdown"""
        self.serial_dropdown.clear()
        
        # Get available ports
        ports = serial.tools.list_ports.comports()
        if ports:
            self.serial_dropdown.addItem("")  # Empty first item
            self.serial_dropdown.addItems([format_serial_port_name(port.device) for port in ports])
        else:
            self.serial_dropdown.addItem("No ports found")
    
    def _browse_ccs_path(self):
        """Browse for CCS path"""
        path = QFileDialog.getExistingDirectory(self, "Browse CCS Path")
        if path:
            self.ccs_path = path
            self.ccs_path_input.setText(path)

    def _on_ccs_path_changed(self, path):
        """Handle CCS path change in device connection widget"""
        self.ccs_path = path

        for widget in self._adv_tab_store.values():
            widget.set_ccs_path(path)
    
    
    def _on_detect_clicked(self):
        """Handle device detection via UART"""
        port = self.serial_dropdown.currentText()
        if not port:
            self._show_error("Please select a serial port")
            return

        from apps.qtgui.devices.register import get_detect_spec_for_device
        detect_spec = get_detect_spec_for_device(self.device_name or "", "UART")

        if detect_spec:
            if detect_spec.get("requires_reset"):
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Information)
                msg.setText("Please reset the device and press OK to continue")
                msg.setWindowTitle("Device Reset Required")
                msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
                if msg.exec_() != QMessageBox.Ok:
                    return

            progress = QProgressDialog("Detecting device via UART...", "Cancel", 0, 0, self)
            progress.setWindowTitle("Please Wait")
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(0)
            progress.show()

            self.detection_thread = DeviceDetectionThread(
                self.device_name, "UART", {"port": port, "baudrate": 115200}
            )
            progress.canceled.connect(self._cancel_detection)
            self.detection_thread.detection_complete.connect(self._handle_detection_result)
            self.detection_thread.finished.connect(progress.close)
            self.detection_thread.start()
        else:
            # Standard SoC detection path (non-f29h85x devices)
            connection_info = {"type": "uart", "port": port}
            self.device_detection_requested.emit("UART", connection_info)

            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setText("Please reset the device and press OK to continue")
            msg.setWindowTitle("Device Reset Required")
            msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
            msg.button(QMessageBox.Ok).setText("OK")
            if msg.exec_() != QMessageBox.Ok:
                return

            progress = QProgressDialog("Detecting device...", "Cancel", 0, 0, self)
            progress.setWindowTitle("Please Wait")
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(0)
            progress.show()

            self.detection_thread = SocIdDetectionThread(port)
            progress.canceled.connect(self._cancel_detection)
            self.detection_thread.detection_complete.connect(self._handle_detection_result)
            self.detection_thread.finished.connect(progress.close)
            self.detection_thread.start()
    
    def _cancel_detection(self) -> None:
        """Cancel any in-progress UART device detection and free the COM port."""
        if hasattr(self, 'detection_thread') and self.detection_thread is not None:
            self.detection_thread.cancel()

    def _cancel_jtag_detection(self) -> None:
        """Cancel any in-progress JTAG device detection."""
        if hasattr(self, 'jtag_detection_thread') and self.jtag_detection_thread is not None:
            self.jtag_detection_thread.cancel()

    def cleanup_active_operations(self) -> None:
        """Kill any running detection subprocesses. Called on application close."""
        self._cancel_detection()
        self._cancel_jtag_detection()

    @pyqtSlot(dict)
    def _handle_detection_result(self, result):
        """Handle SoC ID detection result"""
        if result['success']:
            # Detection successful
            device = result['device']
            device_state = result['device_state']
            
            # Update UI
            self.device_state_input.setText(device_state)
            
            # Emit signal for other components that might need to know
            self.device_detected.emit(device, device_state)
            
            # Update next button state immediately
            self.boot_mode_changed.emit()
            
            # For F29H85x detection, add device detection type to the message
            if device and device.lower() == "f29h85x":
                # Show success message with UART device detection method
                QMessageBox.information(
                    self,
                    "UART Device Detection Successful",
                    f"Detected F29H85x device via UART: {device_state}"
                )
            else:
                # Show regular success message
                QMessageBox.information(
                    self,
                    "Detection Successful",
                    f"Detected device: {device} ({device_state})"
                )
        else:
            # Detection failed
            error = result['error'] or "Unknown error during device detection"
            self._show_error(f"Detection failed: {error}")
            
            # Inform user they can manually enter the device state
            QMessageBox.information(
                self,
                "Manual Entry Option",
                "You can manually enter the device state (HSFS, HSSE, etc.) in the Device State field."
            )
            
    @pyqtSlot(dict)
    def _handle_jtag_detection_result(self, result):
        """Handle JTAG detection result"""
        if result['success']:
            # Detection successful
            device = result['device']
            device_state = result['device_state']
            
            # Update UI
            self.device_state_input.setText(device_state)
            
            # Emit signal for other components that might need to know
            self.device_detected.emit(device, device_state)
            
            # Update next button state immediately
            self.boot_mode_changed.emit()
            
            # Show success message
            QMessageBox.information(
                self,
                "Detection Successful",
                f"Detected device via JTAG: {device} ({device_state})"
            )
        else:
            # Detection failed
            error = result['error'] or "Unknown error during JTAG device detection"
            self._show_error(f"JTAG detection failed: {error}")
            
            # Inform user they can manually enter the device state
            QMessageBox.information(
                self,
                "Manual Entry Option",
                "You can manually enter the device state (HSFS, HSSE, etc.) in the Device State field."
            )
    
    def _update_jtag_boot_mode_status(self):
        """Update JTAG boot mode option based on CCS path availability"""
        # Find the JTAG option index
        jtag_index = self.boot_mode_dropdown.findText("JTAG")
        if jtag_index >= 0:
            if not self.ccs_path:
                # Disable JTAG option and add tooltip
                self.boot_mode_dropdown.setItemData(
                    jtag_index, 
                    "Please provide CCS path on home page to enable JTAG", 
                    Qt.ToolTipRole
                )
                
                # Create a model that makes this item non-selectable
                model = self.boot_mode_dropdown.model()
                item = model.item(jtag_index)
                if item:
                    item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
            else:
                # Enable JTAG option and add tooltip about the CCS path
                self.boot_mode_dropdown.setItemData(
                    jtag_index,
                    f"Using CCS path: {self.ccs_path}",
                    Qt.ToolTipRole
                )
                
                # Enable the item
                model = self.boot_mode_dropdown.model()
                item = model.item(jtag_index)
                if item:
                    item.setFlags(item.flags() | Qt.ItemIsEnabled)
                    
    def _on_jtag_detect_clicked(self):
        """Handle device detection via JTAG"""
        # Use the CCS path from the landing page
        ccs_path = self.ccs_path
        if not ccs_path:
            self._show_error("Please provide CCS path on the home page")
            return

        # Validate CCS path exists
        if not os.path.isdir(ccs_path):
            self._show_error(f"CCS path does not exist or is not a directory: {ccs_path}")
            return

        ccxml_path = self.target_config_path if self.target_config_path and os.path.exists(self.target_config_path) else None

        # Emit signal for controller to handle detection
        connection_info = {"type": "jtag", "ccs_path": ccs_path}
        self.device_detection_requested.emit("JTAG", connection_info)

        # Show progress dialog
        progress = QProgressDialog("Detecting device via JTAG...", "Cancel", 0, 0, self)
        progress.setWindowTitle("Please Wait")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.show()

        # Start detection thread
        self.jtag_detection_thread = DeviceDetectionThread(
            self.device_name or "f29h85x",
            "JTAG",
            {"ccs_path": ccs_path, "ccxml_path": ccxml_path}
        )
        progress.canceled.connect(self._cancel_jtag_detection)
        self.jtag_detection_thread.detection_complete.connect(self._handle_jtag_detection_result)
        self.jtag_detection_thread.finished.connect(progress.close)
        self.jtag_detection_thread.start()

    def _show_error(self, message):
        """Show error message dialog"""
        error_box = QMessageBox()
        error_box.setIcon(QMessageBox.Warning)
        error_box.setText(message)
        error_box.setWindowTitle("Error")
        error_box.exec_()
    
    def validate(self):
        """Validate the page before proceeding"""
        # Check if boot mode is selected
        if not self.boot_mode_dropdown.currentText():
            self._show_error("Please select a boot mode")
            return False
        
        # Check if device state is detected
        if not self.device_state_input.text():
            self._show_error("Please detect device state")
            return False
        
        # Certificate generation is optional
        return True
    
    def is_valid(self):
        """Check if the page has valid data for enabling Next button"""
        # Next button should be enabled as soon as boot mode is selected and device state is set
        has_boot_mode = bool(self.boot_mode_dropdown.currentText())
        has_device_state = bool(self.device_state_input.text())
        return has_boot_mode and has_device_state
    
    def get_boot_mode(self):
        """Get the selected boot mode"""
        return self.boot_mode_dropdown.currentText()
    
    def get_connection_info(self):
        """Get connection info based on boot mode"""
        from apps.qtgui.devices.register import get_boot_mode_specs_for_device
        boot_mode = self.get_boot_mode()
        specs = get_boot_mode_specs_for_device(self.device_name or "")
        spec = next((s for s in specs if s["id"] == boot_mode), None)
        if spec:
            param_value = (self.serial_dropdown.currentText()
                           if spec["connection_widget"] == "serial"
                           else self.ccs_path_input.text())
            return {"type": spec["connection_type"], spec["connection_param"]: param_value}
        return {"type": "none"}
    
    def get_device_state(self):
        """Get detected device state"""
        return self.device_state_input.text()
    
    def get_certificate_info(self):
        """Get certificate generation info"""
        return self.certificate_info
        
    def set_certificate_info(self, certificate_info):
        """Set certificate information"""
        self.certificate_info = certificate_info
        
        # Update certificate status in UI
        if certificate_info:
            self.certificate_label.setText("Generated \u2713")
            self.certificate_label.setStyleSheet("color: #28a745; font-weight: bold;")
        else:
            self.certificate_label.setText("Not generated")
            self.certificate_label.setStyleSheet("color: #ff9800; font-weight: bold;")
            
    def _update_binary_signing_button_state(self):
        """Update binary signing button state based on device and key type"""
        from apps.qtgui.devices.register import get_binary_signing_for_device
        supports_binary_signing = get_binary_signing_for_device(self.device_name or "")
        has_keys = self.key_type in ["f29_development", "existing", "new", "pkcs11"]

        if supports_binary_signing and has_keys:
            self.sign_binary_button.setEnabled(True)
            self.sign_binary_button.setToolTip("Sign binary images using current session")
        else:
            self.sign_binary_button.setEnabled(False)
            if not supports_binary_signing:
                self.sign_binary_button.setToolTip("Binary signing is not supported for this device")
            elif not has_keys:
                self.sign_binary_button.setToolTip("Please select a key type first")
    
    def _toggle_advanced_options(self):
        """Toggle visibility of advanced certificate options content"""
        is_visible = self.adv_cert_content.isVisible()
        self.adv_cert_content.setVisible(not is_visible)
        
        # Change arrow direction based on visibility
        if not is_visible:
            # Expanded state - show downward arrow
            self.adv_toggle_arrow.setText("▼")
            self.adv_toggle_arrow.setStyleSheet("""
                color: #CC0000;
                font-size: 12px;
                font-weight: bold;
            """)
        else:
            # Collapsed state - show right arrow
            self.adv_toggle_arrow.setText("▶")
            self.adv_toggle_arrow.setStyleSheet("""
                color: #CC0000;
                font-size: 12px;
                font-weight: bold;
            """)
    
    def _update_advanced_tabs(self, tab_specs):
        """Rebuild adv_cert_tabs from the ADV_TAB_CLASSES registry (lazy build + cache)."""
        from apps.qtgui.views.pages.adv_tabs.registry import ADV_TAB_CLASSES

        self.adv_cert_tabs.clear()  # removes tabs without destroying widgets
        device_tab_classes = ADV_TAB_CLASSES.get(self.device_name or "", {})
        for spec in tab_specs:
            tab_id = spec["id"]
            if tab_id not in self._adv_tab_store:
                cls = device_tab_classes.get(tab_id)
                if cls:
                    widget = cls(self)
                    widget.completed.connect(self._on_adv_tab_completed)
                    self._adv_tab_store[tab_id] = widget
            widget = self._adv_tab_store.get(tab_id)
            if widget:
                self.adv_cert_tabs.addTab(widget, spec.get("label", tab_id))

    def _update_advanced_cert_options_visibility(self):
        """Update advanced certificate options visibility based on device and key type"""
        from apps.qtgui.devices.register import get_advanced_tabs_for_device
        tab_specs = get_advanced_tabs_for_device(self.device_name or "")
        has_tabs = bool(tab_specs)
        has_keys = self.key_type in ["f29_development", "existing", "new", "pkcs11"]

        if has_tabs and has_keys:
            self._update_advanced_tabs(tab_specs)
            self.adv_cert_container.setVisible(True)

            if not self.device_name:
                raise ValueError("Device name must be set before accessing output directories")

            prebuilt_images_dir = get_addon_root(self.device_name) / "bin"

            # Inject session context and paths into each cached tab widget
            for widget in self._adv_tab_store.values():
                widget.set_model(None, self.key_type, self.key_data, self.device or "")
                widget.set_ccs_path(getattr(self, 'ccs_path', '') or '')
                widget.set_prebuilt_dir(prebuilt_images_dir)

            # Set per-tab output directories from spec (tabs only update if their field is empty)
            for spec in tab_specs:
                widget = self._adv_tab_store.get(spec["id"])
                if widget and "output_dir_key" in spec:
                    widget.set_output_path(
                        get_device_output_dir(self.device_name, spec["output_dir_key"]))

            # Reset to collapsed state by default when shown
            self.adv_cert_content.setVisible(False)
            self.adv_toggle_arrow.setText("▶")  # Right arrow
        else:
            self.adv_cert_container.setVisible(False)
    
    def _on_sign_all_binaries(self):
        """Handle sign all binaries button click"""
        # Validate key information first
        if not self.key_type or not self.key_data:
            self._show_error("Please select a key type and session before signing binaries")
            return
            
        # Get CCS path
        ccs_path = self.ccs_path
        if not ccs_path:
            self._show_error("CCS path is required for signing. Please set it on the home page.")
            return
            
        # Show progress dialog
        progress = QProgressDialog("Signing and encrypting binaries using optimal configurations...", "Cancel", 0, 100, self)
        progress.setWindowTitle("Please Wait")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(10)
        progress.setAutoClose(True)
        
        # Update the status message
        progress.setLabelText("Preparing to sign binaries...")
        QApplication.processEvents()
        
        try:
            # Create model instance for handling signing operations
            from apps.qtgui.models.F29H85xDeviceModel import F29H85xDeviceModel
            model = F29H85xDeviceModel()
            
            # Enable HSM signing for PKCS11 sessions (private key on device, never extractable)
            hsm_flag = (self.key_type == "pkcs11")

            # Set up the model with session information
            if self.key_type == "f29_development":
                model.development_session_checkbox = True
                model.sessionName = "Development"
                model.sessionPassword = "develop123#"
                model.smpk = self.key_data.get("smpk_algo", "secp384r1")
                model.bmpk = self.key_data.get("bmpk_algo", "secp384r1")
            else:
                model.development_session_checkbox = False
                model.sessionName = self.key_data.get("name", "")
                model.sessionPassword = self.key_data.get("password", "")

            # Extract the session's SMEK for encryption (non-dev sessions)
            enc_key_path = None
            smek_tmp_path = None
            if self.key_type != "f29_development":
                from tisecprov.session import SecureSession
                from tisecprov.crypto_selector import get_crypto_backend
                secure_session = SecureSession(use_hsm=hsm_flag)
                with secure_session as s:
                    s.open_session(model.sessionName, model.sessionPassword)
                    crypto_backend = get_crypto_backend(use_hsm=hsm_flag)
                    keys = s.get_manufacturer_keys(crypto_backend)
                    smek_bytes = keys[0].get_symmetric_key()
                smek_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".key")
                smek_tmp.write(smek_bytes)
                smek_tmp.close()
                smek_tmp_path = smek_tmp.name
                enc_key_path = smek_tmp_path

            # Get path to prebuilt images
            import getpass
            from pathlib import Path
            
            # Get path to prebuilt images
            import sys

            if not self.device_name:
                raise ValueError("Device name must be set before batch signing")

            prebuilt_images_dir = get_addon_root(self.device_name) / "bin"

            if not prebuilt_images_dir.exists():
                raise FileNotFoundError(f"Prebuilt images directory not found: {prebuilt_images_dir}")

            # Default to the static dev key if no session SMEK was extracted
            if enc_key_path is None:
                enc_key_path = str(prebuilt_images_dir / "mcu_custMek.key")

            output_path = Path(get_device_output_dir(self.device_name, "signedImages"))
            output_path.mkdir(parents=True, exist_ok=True)
            
            binary_images = model.get_prebuilt_signing_specs()
            if not binary_images:
                raise ValueError(f"No binary image specs found for device '{self.device_name}'")

            total = len(binary_images)
            signed_labels = []

            for i, spec in enumerate(binary_images):
                pct = 20 + int((i / total) * 70)
                progress.setValue(pct)
                progress.setLabelText(f"Signing {spec['label']}...")
                QApplication.processEvents()

                # Resolve filename
                if spec.get("filename"):
                    filename = spec["filename"]
                else:
                    filename = spec["filename_template"].format(device_name=self.device_name)
                image_path = prebuilt_images_dir / filename
                if not image_path.exists():
                    raise FileNotFoundError(f"{spec['label']} not found: {image_path}")

                # Build runtime config from spec
                cfg = dict(spec.get("sign_config", {}))
                use_tifs_enc = cfg.pop("tifs_enc", False)
                use_fw_enc   = cfg.pop("fw_enc", False)
                cfg["image"] = str(image_path)
                cfg["output_path"] = output_path
                cfg["ccs_path"] = ccs_path
                cfg["hsm"] = hsm_flag
                if use_tifs_enc:
                    cfg["tifs_enc"]  = True
                    cfg["enc_key"]   = enc_key_path
                    cfg["kd_salt"]   = str(prebuilt_images_dir / "kd_salt.txt")
                if use_fw_enc:
                    cfg["fw_enc"]     = True
                    cfg["fw_enc_key"] = enc_key_path
                    cfg["kd_salt"]    = str(prebuilt_images_dir / "kd_salt.txt")

                # Dispatch by sign_type
                if spec.get("sign_type") == "seccfg":
                    ok, msg = model.sign_sec_cfg_wrapper(**cfg)
                else:
                    ok, msg = model.sign_binary(**cfg)

                if not ok:
                    raise Exception(f"Failed to sign {spec['label']}: {msg}")
                signed_labels.append(spec["label"])

            # Clean up temporary SMEK file
            if smek_tmp_path and os.path.exists(smek_tmp_path):
                os.unlink(smek_tmp_path)

            # Complete the progress
            progress.setValue(100)
            progress.setLabelText("Signing process completed.")
            QApplication.processEvents()

            # Close progress dialog
            progress.close()

            # Show success message
            items = "\n".join(f"{j + 1}. {lbl}" for j, lbl in enumerate(signed_labels))
            success_message = (
                f"Successfully signed and encrypted all binaries to:\n"
                f"{output_path}\n\n"
                f"{items}"
            )
            
            QMessageBox.information(
                self,
                "Binary Signing Successful",
                success_message
            )

            
        except Exception as e:
            # Clean up temporary SMEK file on error
            if smek_tmp_path and os.path.exists(smek_tmp_path):
                os.unlink(smek_tmp_path)
            # Close progress dialog
            progress.close()

            # Show error message
            self._show_error(f"Error during binary signing: {str(e)}")

    def _on_batch_signing_result(self, success, message):
        """Handle batch signing result from controller"""
        if success:
            # Show success message
            QMessageBox.information(
                self,
                "Binary Signing Successful",
                f"All binaries have been successfully signed.\n\n{message}"
            )
        else:
            # Show error message
            QMessageBox.warning(
                self,
                "Binary Signing Failed",
                f"Failed to sign some or all binaries.\n\n{message}"
            )
        # No need to show error message here as it's already handled in the dialog

    def _on_adv_tab_completed(self, success: bool, message: str):
        """Unified result handler for all advanced tab actions."""
        if success:
            QMessageBox.information(self, "Success", message)
        else:
            QMessageBox.critical(self, "Error", message)
