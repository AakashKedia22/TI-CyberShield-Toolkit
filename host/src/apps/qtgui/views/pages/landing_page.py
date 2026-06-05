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
    QTabWidget,
    QScrollArea,
    QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer

import os
import sys
import getpass
import pathlib
import shutil
from apps.qtgui.utils.platform_utils import get_home_directory

class ExtOtpRowsWidget(QWidget):
    """Displays Extended OTP rows as a selectable table.

    Row count and bits-per-row come from device.json (num_rows / row_bits).
    Row N maps to bit index N*row_bits.  The user selects one row to configure
    its Value and Size; unselected rows are grayed-out.  A QScrollArea keeps
    the widget compact.  Call get_selected() to retrieve the active row's data.
    """

    def __init__(self, default_value="0x80000001", default_size="128",
                 num_rows=13, row_bits=128, parent=None):
        super().__init__(parent)
        self.NUM_ROWS = int(num_rows)
        self.ROW_BITS = int(row_bits)
        self._row_data = []   # list of (val_edit, size_edit) per row
        self._radios = []     # QRadioButton per OTP row
        self._none_radio = None
        self._radio_group = QButtonGroup(self)
        self._init_ui(default_value, default_size)

    def _init_ui(self, default_value, default_size):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setFrameShadow(QFrame.Plain)
        frame.setStyleSheet("QFrame { border: 1px solid #cccccc; border-radius: 4px; }")

        grid = QGridLayout(frame)
        grid.setContentsMargins(10, 8, 10, 10)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(6)

        # Column headers: col 0=radio, 1=row, 2=bit range, 3=value, 4=size
        hdr_style = "font-weight: bold; font-size: 12px; color: #555555; border: none;"
        for col, text in enumerate(["", "Row", "Bit range", "Value (hex)", "Size (bits)"]):
            lbl = QLabel(text)
            lbl.setStyleSheet(hdr_style)
            grid.addWidget(lbl, 0, col)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        grid.addWidget(line, 1, 0, 1, 5)

        # "Disabled" option — sentinel id = NUM_ROWS
        none_radio = QRadioButton()
        none_radio.setChecked(True)
        self._radio_group.addButton(none_radio, self.NUM_ROWS)
        self._none_radio = none_radio
        none_lbl = QLabel("Disabled (no extended OTP)")
        none_lbl.setStyleSheet("color: #888888; font-style: italic; border: none;")
        grid.addWidget(none_radio, 2, 0)
        grid.addWidget(none_lbl, 2, 1, 1, 4)
        none_radio.toggled.connect(self._on_selection_changed)

        disabled_style = "QLineEdit:disabled { background-color: #f0f0f0; color: #aaaaaa; }"
        for i in range(self.NUM_ROWS):
            grid_row = i + 3   # header=0, line=1, none=2, rows start at 3
            bit_start = i * self.ROW_BITS
            bit_end = bit_start + self.ROW_BITS - 1

            radio = QRadioButton()
            self._radio_group.addButton(radio, i)
            radio.toggled.connect(self._on_selection_changed)
            self._radios.append(radio)

            row_lbl = QLabel(f"Row {i}")
            row_lbl.setStyleSheet("font-size: 13px; font-weight: bold; min-width: 50px; border: none;")

            range_lbl = QLabel(f"{bit_start} – {bit_end}")
            range_lbl.setStyleSheet("font-size: 12px; color: #777777; min-width: 80px; border: none;")

            val_edit = QLineEdit(default_value if i == 0 else "")
            val_edit.setPlaceholderText("e.g. 0x80000001")
            val_edit.setMinimumWidth(160)
            val_edit.setEnabled(False)
            val_edit.setStyleSheet(disabled_style)

            size_edit = QLineEdit(default_size if i == 0 else "")
            size_edit.setPlaceholderText("bits")
            size_edit.setMinimumWidth(60)
            size_edit.setMaximumWidth(80)
            size_edit.setEnabled(False)
            size_edit.setStyleSheet(disabled_style)

            grid.addWidget(radio,     grid_row, 0)
            grid.addWidget(row_lbl,   grid_row, 1)
            grid.addWidget(range_lbl, grid_row, 2)
            grid.addWidget(val_edit,  grid_row, 3)
            grid.addWidget(size_edit, grid_row, 4)

            self._row_data.append((val_edit, size_edit))

        grid.setColumnStretch(3, 1)

        # Wrap frame in a scroll area so 13 rows don't overflow the tab
        scroll = QScrollArea()
        scroll.setWidget(frame)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        outer.addWidget(scroll)

    def _on_selection_changed(self):
        checked_id = self._radio_group.checkedId()
        for i, (val_edit, size_edit) in enumerate(self._row_data):
            active = (i == checked_id)
            val_edit.setEnabled(active)
            size_edit.setEnabled(active)

    def get_selected(self):
        """Return {'index', 'value', 'size'} for the selected row, or None if disabled.

        'index' is the bit position of the row (row N → N * 128).
        """
        checked_id = self._radio_group.checkedId()
        if checked_id == self.NUM_ROWS:
            return None
        if 0 <= checked_id < self.NUM_ROWS:
            val_edit, size_edit = self._row_data[checked_id]
            return {
                'index': str(checked_id * self.ROW_BITS),
                'value': val_edit.text().strip(),
                'size':  size_edit.text().strip(),
            }
        return None


class CollapsibleSection(QWidget):
    """A collapsible section widget with a header button that toggles content visibility"""
    
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.is_collapsed = True
        self.animation = None
        self.init_ui(title)
        
    def init_ui(self, title):
        # Create layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Create header with toggle button and arrow
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        self.toggle_button = QPushButton(title)
        self.toggle_button.setStyleSheet(
            "QPushButton { text-align: left; padding: 5px; font-weight: bold; background-color: #CC0000; color: white; border: 1px solid #990000; border-radius: 4px; }"
            "QPushButton:hover { background-color: #990000; }"
        )
        self.toggle_button.setMinimumHeight(30)
        self.toggle_button.clicked.connect(self.toggle_section)
        
        self.arrow_label = QLabel("▶")
        self.arrow_label.setStyleSheet("font-size: 14px; padding-right: 10px; color: white;")
        
        header_layout.addWidget(self.toggle_button)
        header_layout.addWidget(self.arrow_label)
        header_layout.addStretch()
        
        # Create content area
        self.content_area = QWidget()
        self.content_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(10, 10, 10, 10)
        self.content_layout.setSpacing(10)
        
        # Add to main layout
        self.main_layout.addLayout(header_layout)
        self.main_layout.addWidget(self.content_area)
        
        # Initialize as collapsed
        self.content_area.setVisible(False)
        
    def toggle_section(self):
        self.is_collapsed = not self.is_collapsed
        self.content_area.setVisible(not self.is_collapsed)
        
        # Update arrow direction
        if self.is_collapsed:
            self.arrow_label.setText("▶")  # Right arrow (collapsed)
        else:
            self.arrow_label.setText("▼")  # Down arrow (expanded)
        
        # Find the landing page (parent that has updateGeometry method)
        landing_page = self.find_landing_page()
        if landing_page:
            # Force layout update
            landing_page.updateGeometry()
            
            # Find scroll area if it exists
            scroll_area = self.find_scroll_area()
            if scroll_area:
                # Ensure scroll area updates
                scroll_area.updateGeometry()
                
                # If expanded, ensure content is visible by scrolling to it
                if not self.is_collapsed:
                    # Give the UI a moment to update before scrolling
                    QTimer.singleShot(100, lambda: self.ensure_visible())
    
    def ensure_visible(self):
        """Ensure this section is visible in the scroll area"""
        scroll_area = self.find_scroll_area()
        if scroll_area and not self.is_collapsed:
            # Calculate position to ensure this section is visible
            scroll_area.ensureWidgetVisible(self.content_area)
    
    def find_landing_page(self):
        """Find the parent LandingPage widget"""
        parent = self.parent()
        while parent:
            if isinstance(parent, QWidget) and hasattr(parent, "updateGeometry"):
                return parent
            parent = parent.parent()
        return None
    
    def find_scroll_area(self):
        """Find the parent ScrollArea widget"""
        parent = self.parent()
        while parent:
            if isinstance(parent, QScrollArea):
                return parent
            parent = parent.parent()
        return None
    
    def add_widget(self, widget):
        self.content_layout.addWidget(widget)
        
    def add_layout(self, layout):
        self.content_layout.addLayout(layout)

# Handle SecureSession import gracefully
try:
    from tisecprov.session import SecureSession
except ImportError:
    # Create a dummy SecureSession for development
    class SecureSession:
        def __init__(self):
            pass
            
        def list_sessions(self):
            return [{'name': 'Sample Session'}]

class LandingPage(QWidget):
    """First page of the wizard with device and key selection"""
    
    # Signals
    device_changed = pyqtSignal(str)
    key_selected = pyqtSignal()
    key_generated = pyqtSignal(dict)
    key_loaded = pyqtSignal(dict)
    development_session_set = pyqtSignal(dict)
    f29_development_session_set = pyqtSignal(dict)  # compat shim — use development_session_set
    certificate_request = pyqtSignal(dict)
    ccs_path_changed = pyqtSignal(str)
    target_config_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ccs_path = ""
        self.target_config_path = ""
        self.certificate_data = None
        self.device = None
        self.key_type = None
        self.key_data = None
        self._session_confirmed = False
        self._key_options = []
        self._addon_installed: bool = True
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI components"""
        # Create a scroll area for the entire page
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.NoFrame)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Create content widget to hold all page elements
        content_widget = QWidget()
        content_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
        
        # Main layout
        main_layout = QVBoxLayout(content_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Page title
        title_label = QLabel("Device & Key Selection")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #CC0000;")
        main_layout.addWidget(title_label)
        
        # Device selection group
        device_group = QGroupBox("Device Selection")
        device_layout = QFormLayout()
        
        # Device dropdown
        self.device_dropdown = QComboBox()
        self.device_dropdown.setPlaceholderText("Select Device")
        # Import devices list from settings
        from apps.qtgui import settings
        self.device_dropdown.addItem("")  # Empty first item
        self.device_dropdown.addItems(settings.devices)
        self.device_dropdown.currentTextChanged.connect(self._on_device_changed)
        
        device_layout.addRow("Device:", self.device_dropdown)

        self._addon_status_label = QLabel()
        self._addon_status_label.setWordWrap(True)
        self._addon_status_label.hide()
        device_layout.addRow(self._addon_status_label)

        # Addon path override row (shown only when addon is not detected)
        addon_path_container = QWidget()
        addon_path_layout = QHBoxLayout(addon_path_container)
        addon_path_layout.setContentsMargins(0, 0, 0, 0)
        addon_path_layout.setSpacing(4)
        self._addon_path_edit = QLineEdit()
        self._addon_path_edit.setPlaceholderText("Path to addons base directory")
        self._addon_path_edit.setToolTip(
            "Directory that contains device specific security binaries (e.g. f29h85x/, am261x/)"
        )
        addon_browse_btn = QPushButton("Browse")
        addon_browse_btn.setFixedWidth(70)
        addon_browse_btn.clicked.connect(self._browse_addon_path)
        addon_path_layout.addWidget(self._addon_path_edit)
        addon_path_layout.addWidget(addon_browse_btn)
        self._addon_path_row = addon_path_container
        self._addon_path_row.hide()
        device_layout.addRow("Addon Path:", self._addon_path_row)
        self._addon_path_edit.textChanged.connect(self._on_addon_path_changed)

        device_group.setLayout(device_layout)
        main_layout.addWidget(device_group)
        
        # CCS Path input group
        ccs_path_group = QGroupBox("CCS Installation Path")
        ccs_path_layout = QVBoxLayout()
        
        # Add explanation label
        ccs_path_explanation = QLabel("Provide CCS installation path to enable JTAG boot mode in configuration.")
        ccs_path_explanation.setWordWrap(True)
        ccs_path_layout.addWidget(ccs_path_explanation)
        
        # CCS path input layout
        ccs_input_layout = QHBoxLayout()
        self.ccs_path_input = QLineEdit()
        self.ccs_path_input.setPlaceholderText("Path to Code Composer Studio installation")
        self.ccs_path_input.setToolTip("This path is required if you want to use JTAG boot mode later")
        ccs_browse_button = QPushButton("Browse")
        ccs_browse_button.clicked.connect(self._browse_ccs_path)
        ccs_input_layout.addWidget(self.ccs_path_input)
        ccs_input_layout.addWidget(ccs_browse_button)
        ccs_path_layout.addLayout(ccs_input_layout)

        # Target configuration file input layout
        target_config_label = QLabel("Target Configuration File:")
        target_config_label.setStyleSheet("font-weight: normal;")
        ccs_path_layout.addWidget(target_config_label)

        target_config_layout = QHBoxLayout()
        self.target_config_input = QLineEdit()
        self.target_config_input.setPlaceholderText("Path to target configuration file (.ccxml)")
        self.target_config_input.setToolTip("Target configuration file to be used for JTAG Bootmode")
        self.target_config_input.setClearButtonEnabled(True)  # Enable clear button inside the input field
        self.target_config_browse_button = QPushButton("Browse")
        self.target_config_browse_button.clicked.connect(self._browse_target_config)
        target_config_layout.addWidget(self.target_config_input)
        target_config_layout.addWidget(self.target_config_browse_button)
        ccs_path_layout.addLayout(target_config_layout)

        # Set default CCS path if available
        self._set_default_ccs_path()

        # Connect textChanged signals
        self.ccs_path_input.textChanged.connect(self._on_ccs_path_changed)
        self.target_config_input.textChanged.connect(self._on_target_config_changed)

        # Initially disable target configuration input until CCS path is provided
        self._update_target_config_state()

        ccs_path_group.setLayout(ccs_path_layout)
        main_layout.addWidget(ccs_path_group)
        
        # Key selection group — populated dynamically by _update_key_options_ui on device change
        self.key_selection_group = QGroupBox("Key Selection")
        key_selection_layout = QVBoxLayout()
        self._key_selection_layout = key_selection_layout

        # Empty button group; buttons are added per device in _update_key_options_ui
        self.key_selection_button_group = QButtonGroup(self)
        self.key_selection_button_group.buttonClicked.connect(self.on_key_selection_changed)
        self._key_radio_map   = {}   # key_type → QRadioButton
        self._key_type_map    = {}   # QRadioButton → key_type
        self._key_panel_map   = {}   # key_type → panel widget
        self._key_panel_widgets = {} # key_type → {field_key: widget}

        self.key_empty_label = QLabel("Select a device to view key options")
        self.key_empty_label.setAlignment(Qt.AlignCenter)
        self.key_empty_label.setStyleSheet("color: #888888; font-style: italic; padding: 16px;")
        key_selection_layout.addWidget(self.key_empty_label)

        self.key_selection_group.setLayout(key_selection_layout)
        main_layout.addWidget(self.key_selection_group)
        
        # Certificate generation group - initially hidden
        self.certificate_group = QGroupBox("Certificate Generation")
        self.certificate_layout = QVBoxLayout()
        self.certificate_layout.setSpacing(10)  # Slightly reduced spacing
        # self.certificate_layout.setContentsMargins(15, 15, 15, 15)  # Reduced margins
        
        # Dynamic cert UI — populated by _update_certificate_ui when device is chosen
        self._cert_widgets = {}      # key -> data widget
        self._cert_flags = []        # always-on flags for current device
        self._cert_group_widget = None   # the QGroupBox currently in certificate_layout
        self._cert_btn = None        # Generate Certificate button in current group
        self._current_cert_fields = []   # field specs for current device

        # Set layout and add to main layout
        self.certificate_group.setLayout(self.certificate_layout)
        
        # Allow certificate group to expand as needed to fit content
        self.certificate_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
        main_layout.addWidget(self.certificate_group)
        self.certificate_group.hide()
        
        # Add spacer at the bottom
        main_layout.addStretch()
        
        # Set the content widget in the scroll area
        scroll_area.setWidget(content_widget)
        
        # Set scroll area as the main widget
        main_widget_layout = QVBoxLayout(self)
        main_widget_layout.setContentsMargins(0, 0, 0, 0)
        main_widget_layout.addWidget(scroll_area)
    
    _KEY_BTN_STYLE = """
        QPushButton {
            background-color: #CC0000;
            color: white;
            padding: 5px 15px;
            border: none;
            border-radius: 4px;
            min-width: 120px;
        }
        QPushButton:hover {
            background-color: #990000;
        }
        QPushButton:disabled {
            background-color: #cccccc;
            color: #666666;
        }
    """

    def _build_new_keys_panel(self) -> QWidget:
        """Build and return the 'Generate new keys' panel widget."""
        widget = QWidget()
        layout = QGridLayout(widget)

        info_label = QLabel(
            "Note: Both secondary and backup keys are generated using RSA algorithm with OpenSSL APIs "
            "locally and stored in a password-protected session in your ~/.local/share folder (Linux) "
            "or %LOCALAPPDATA% folder (Windows)"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet(
            "QLabel { background-color: #e3f2fd; color: #1976d2; padding: 10px; "
            "border: 1px solid #90caf9; border-radius: 4px; font-size: 12px; }"
        )
        layout.addWidget(info_label, 0, 0, 1, 2)

        layout.addWidget(QLabel("Name:"), 1, 0)
        self.new_keys_name_input = QLineEdit()
        layout.addWidget(self.new_keys_name_input, 1, 1)

        layout.addWidget(QLabel("Password:"), 2, 0)
        self.new_keys_password_input = QLineEdit()
        self.new_keys_password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.new_keys_password_input, 2, 1)

        layout.addWidget(QLabel("Confirm Password:"), 3, 0)
        self.new_keys_confirm_password_input = QLineEdit()
        self.new_keys_confirm_password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.new_keys_confirm_password_input, 3, 1)

        self.generate_save_btn = QPushButton("Generate && Save")
        self.generate_save_btn.setStyleSheet(self._KEY_BTN_STYLE)
        self.generate_save_btn.setEnabled(False)
        self.generate_save_btn.clicked.connect(self.on_generate_keys_clicked)
        layout.addWidget(self.generate_save_btn, 4, 1)

        self.new_keys_name_input.textChanged.connect(self.validate_new_keys)
        self.new_keys_password_input.textChanged.connect(self.validate_new_keys)
        self.new_keys_confirm_password_input.textChanged.connect(self.validate_new_keys)
        return widget

    def _build_existing_keys_panel(self) -> QWidget:
        """Build and return the 'Use existing secure session' panel widget."""
        widget = QWidget()
        layout = QGridLayout(widget)

        layout.addWidget(QLabel("Select Key:"), 0, 0)
        self.existing_keys_combo = QComboBox()
        self.existing_keys_combo.setMinimumWidth(300)
        layout.addWidget(self.existing_keys_combo, 0, 1)

        layout.addWidget(QLabel("Password:"), 1, 0)
        self.existing_keys_password = QLineEdit()
        self.existing_keys_password.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.existing_keys_password, 1, 1)

        self.load_existing_btn = QPushButton("Load")
        self.load_existing_btn.setStyleSheet(self._KEY_BTN_STYLE)
        self.load_existing_btn.setEnabled(False)
        self.load_existing_btn.clicked.connect(self.on_load_existing_keys_clicked)
        layout.addWidget(self.load_existing_btn, 2, 1)

        try:
            sessions = SecureSession().list_sessions()
            for s in sessions:
                self.existing_keys_combo.addItem(s["name"])
        except Exception as e:
            print(f"Error loading sessions: {str(e)}")

        self.existing_keys_combo.currentTextChanged.connect(self.validate_existing_keys)
        self.existing_keys_password.textChanged.connect(self.validate_existing_keys)
        return widget

    def _build_sdk_keys_panel(self) -> QWidget:
        """Build and return the 'Use SDK dummy keys' panel widget."""
        widget = QWidget()
        layout = QGridLayout(widget)

        layout.addWidget(QLabel("Name:"), 0, 0)
        self.sdk_name_input = QLineEdit()
        layout.addWidget(self.sdk_name_input, 0, 1)

        layout.addWidget(QLabel("Password:"), 1, 0)
        self.sdk_password_input = QLineEdit()
        self.sdk_password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.sdk_password_input, 1, 1)

        layout.addWidget(QLabel("Version:"), 2, 0)
        version_layout = QHBoxLayout()
        self.sdk_version_button_group = QButtonGroup(self)
        self.radio_v15 = QRadioButton("v1.5")
        self.radio_v22 = QRadioButton("v2.2")
        self.radio_v15.setChecked(True)
        self.sdk_version_button_group.addButton(self.radio_v15)
        self.sdk_version_button_group.addButton(self.radio_v22)
        version_layout.addWidget(self.radio_v15)
        version_layout.addWidget(self.radio_v22)
        version_layout.addStretch()
        layout.addLayout(version_layout, 2, 1)

        self.sdk_generate_btn = QPushButton("Generate")
        self.sdk_generate_btn.setStyleSheet(self._KEY_BTN_STYLE)
        self.sdk_generate_btn.setEnabled(False)
        self.sdk_generate_btn.clicked.connect(self.on_generate_sdk_keys_clicked)
        layout.addWidget(self.sdk_generate_btn, 3, 1)

        self.sdk_name_input.textChanged.connect(self.validate_sdk_keys)
        self.sdk_password_input.textChanged.connect(self.validate_sdk_keys)
        return widget

    def _build_pkcs11_panel(self) -> QWidget:
        """Build and return the 'Use PKCS#11 Smart Card' panel widget."""
        widget = QWidget()
        layout = QGridLayout(widget)

        pkcs11_info_label = QLabel(
            "Note: You must have a PKCS#11 library and tool setup (like libsc-hsm) "
            "installed and configured locally to be used by this application"
        )
        pkcs11_info_label.setWordWrap(True)
        pkcs11_info_label.setStyleSheet(
            "QLabel { background-color: #e3f2fd; color: #1976d2; padding: 10px; "
            "border: 1px solid #90caf9; border-radius: 4px; font-size: 12px; }"
        )
        layout.addWidget(pkcs11_info_label, 0, 0, 1, 2)

        layout.addWidget(QLabel("Name:"), 1, 0)
        self.pkcs11_name_input = QLineEdit()
        layout.addWidget(self.pkcs11_name_input, 1, 1)

        layout.addWidget(QLabel("PIN:"), 2, 0)
        self.pkcs11_password_input = QLineEdit()
        self.pkcs11_password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.pkcs11_password_input, 2, 1)

        self.pkcs11_generate_btn = QPushButton("Generate HSM Keys")
        self.pkcs11_generate_btn.setStyleSheet(self._KEY_BTN_STYLE)
        self.pkcs11_generate_btn.setEnabled(False)
        self.pkcs11_generate_btn.clicked.connect(self.on_generate_pkcs11_keys_clicked)
        layout.addWidget(self.pkcs11_generate_btn, 3, 1)

        self.pkcs11_name_input.textChanged.connect(self.validate_pkcs11_keys)
        self.pkcs11_password_input.textChanged.connect(self.validate_pkcs11_keys)
        return widget

    def _build_development_session_panel(self, option_spec) -> QWidget:
        """Build and return a Development Session panel from option_spec fields."""
        widget = QWidget()
        layout = QGridLayout(widget)

        info = QLabel("Development Session uses default SDK/TIFS keys for testing purposes")
        info.setWordWrap(True)
        info.setStyleSheet(
            "background-color:#e3f2fd;color:#1976d2;padding:10px;"
            "border:1px solid #90caf9;border-radius:4px;font-size:12px;"
        )
        layout.addWidget(info, 0, 0, 1, 2)

        self._key_panel_widgets.clear()
        for row_idx, field in enumerate(option_spec.get("fields", []), start=1):
            data_widget, _ = self._make_field_row(field)
            self._key_panel_widgets[field["key"]] = data_widget
            layout.addWidget(QLabel(field["label"]), row_idx, 0)
            layout.addWidget(data_widget, row_idx, 1)

        key_type = option_spec["key_type"]
        btn = QPushButton("Use Development Session")
        btn.setStyleSheet(self._CERT_BTN_STYLE)
        btn.clicked.connect(lambda _checked=False, kt=key_type: self.on_development_session_clicked(kt))
        layout.addWidget(btn, len(option_spec.get("fields", [])) + 1, 1)
        return widget
    
    def on_key_selection_changed(self, button):
        """Handle key selection radio button changes"""
        self.key_type = self._key_type_map.get(button)

        # Hide all input widgets first
        for panel in self._key_panel_map.values():
            panel.hide()

        # Show appropriate widget and run validation
        if self.key_type in self._key_panel_map:
            self._key_panel_map[self.key_type].show()
            if self.key_type == "new":
                self.validate_new_keys()
            elif self.key_type == "existing":
                self.validate_existing_keys()
            elif self.key_type == "sdk":
                self.validate_sdk_keys()
            elif self.key_type == "pkcs11":
                self.validate_pkcs11_keys()

        # Update certificate buttons status
        self._update_certificate_buttons_status()

        # Emit key selected signal
        self.key_selected.emit()
    
    def _on_device_changed(self, device):
        """Handle device selection changes"""
        self.device = device
        self.device_changed.emit(device)
        self.reset_key_selection()
        self._update_key_options_ui(device)
        self._refresh_addon_state(device)
        self._update_certificate_ui(device)
        # Auto-detect target config for the newly selected device (only if field is empty)
        if not self.target_config_path:
            self._set_default_target_config_path(device)

    def _update_key_options_ui(self, device):
        """Clear existing key options and rebuild from device registry."""
        from apps.qtgui.devices.register import get_key_options_for_device

        # 1. Clear existing radio buttons and panels
        for btn in list(self._key_radio_map.values()):
            self.key_selection_button_group.removeButton(btn)
            btn.deleteLater()
        for panel in list(self._key_panel_map.values()):
            panel.deleteLater()
        self._key_radio_map.clear()
        self._key_type_map.clear()
        self._key_panel_map.clear()
        self._key_panel_widgets.clear()

        # 2. Get key options from registry
        key_options = get_key_options_for_device(device)
        self._key_options = key_options

        # 3. Build radio + panel for each option
        _PANEL_BUILDERS = {
            "new":      self._build_new_keys_panel,
            "existing": self._build_existing_keys_panel,
            "sdk":      self._build_sdk_keys_panel,
            "pkcs11":   self._build_pkcs11_panel,
        }
        layout = self._key_selection_layout
        for spec in key_options:
            key_type = spec["key_type"]
            radio = QRadioButton(spec["label"])
            self.key_selection_button_group.addButton(radio)
            layout.addWidget(radio)
            if spec.get("fields"):
                panel = self._build_development_session_panel(spec)
            else:
                builder = _PANEL_BUILDERS.get(key_type)
                panel = builder() if builder else QWidget()
            panel.hide()
            layout.addWidget(panel)
            self._key_radio_map[key_type] = radio
            self._key_type_map[radio] = key_type
            self._key_panel_map[key_type] = panel

        # 4. Toggle placeholder
        has_options = bool(key_options)
        self.key_empty_label.setVisible(not has_options)
        self.key_selection_group.setVisible(True)

    def reset_key_selection(self):
        """Reset key selection when device changes"""
        # Uncheck all radio buttons
        for button in self.key_selection_button_group.buttons():
            button.setAutoExclusive(False)
            button.setChecked(False)
            button.setAutoExclusive(True)

        # Hide all input widgets
        for panel in self._key_panel_map.values():
            panel.hide()
        
        # Reset key type, data, and confirmation flag
        self.key_type = None
        self.key_data = None
        self._session_confirmed = False

        # Also reset certificate data when device changes
        self.certificate_data = None
        self.update_certificate_button()
        
        # Update certificate buttons status
        self._update_certificate_buttons_status()
    
    def validate_new_keys(self):
        """Validate new keys input fields"""
        name = self.new_keys_name_input.text().strip()
        password = self.new_keys_password_input.text().strip()
        confirm_password = self.new_keys_confirm_password_input.text().strip()
        
        # All fields must be filled and passwords must match
        valid = (
            bool(name) and 
            bool(password) and 
            bool(confirm_password) and 
            password == confirm_password
        )
        
        self.generate_save_btn.setEnabled(valid)
        return valid
    
    def validate_existing_keys(self):
        """Validate existing keys input fields"""
        name = self.existing_keys_combo.currentText()
        password = self.existing_keys_password.text().strip()
        
        # Both fields must be filled
        valid = bool(name) and bool(password)
        
        self.load_existing_btn.setEnabled(valid)
        return valid
    
    def validate_sdk_keys(self):
        """Validate SDK keys input fields"""
        name = self.sdk_name_input.text().strip()
        password = self.sdk_password_input.text().strip()
        
        # Both fields must be filled
        valid = bool(name) and bool(password)
        
        self.sdk_generate_btn.setEnabled(valid)
        return valid
    
    def validate_pkcs11_keys(self):
        """Validate PKCS#11 keys input fields"""
        name = self.pkcs11_name_input.text().strip()
        password = self.pkcs11_password_input.text().strip()
        
        # Both fields must be filled
        valid = bool(name) and bool(password)
        
        self.pkcs11_generate_btn.setEnabled(valid)
        return valid
    
    def _set_default_ccs_path(self):
        """Set default CCS path based on common installation locations"""
        from apps.qtgui.views.pages.automations import resolve_ccs_path
        path = resolve_ccs_path()
        if path:
            self.ccs_path = path
            self.ccs_path_input.setText(path)

    def _refresh_addon_state(self, device):
        """Check addon presence for device and cache result in self._addon_installed."""
        if not device:
            self._addon_installed = True
            self._addon_status_label.hide()
            return
        from apps.qtgui.views.pages.automations import is_addon_installed
        self._addon_installed = is_addon_installed(device)
        self._update_addon_status_label()

    def _update_addon_status_label(self):
        """Refresh the addon detected/not-detected indicator below the device dropdown."""
        import pathlib
        if not self._addon_path_edit.text():
            self._addon_path_edit.setText(
                str(pathlib.Path.home() / "ti" / "TICST" / "addons")
            )
        if self._addon_installed:
            self._addon_status_label.setText("✓ Security addon detected")
            self._addon_status_label.setStyleSheet("color: #2e7d32; font-size: 12px;")
        else:
            self._addon_status_label.setText(
                "⚠ Security addon not detected — extract addon files to ~/ti/TICST/addons"
                " or specify the path below"
            )
            self._addon_status_label.setStyleSheet("color: #e65100; font-size: 12px;")
        self._addon_path_row.show()
        self._addon_status_label.show()

    def _set_default_target_config_path(self, device=None):
        """Auto-detect target configuration file based on the device's file prefix."""
        if not device:
            return
        from apps.qtgui.views.pages.automations import resolve_target_config_path
        path = resolve_target_config_path(device)
        if path:
            self.target_config_path = path
            self.target_config_input.setText(path)

    def _browse_addon_path(self):
        path = QFileDialog.getExistingDirectory(self, "Select Addon Base Directory")
        if path:
            self._addon_path_edit.setText(path)

    def _on_addon_path_changed(self, path: str) -> None:
        from common.platform_utils import set_addon_base
        set_addon_base(path.strip() if path.strip() else None)
        if self.device:
            self._refresh_addon_state(self.device)

    def _browse_ccs_path(self):
        """Browse for CCS installation path"""
        path = QFileDialog.getExistingDirectory(
            self, "Select CCS Installation Directory"
        )
        if path:
            self.ccs_path = path
            self.ccs_path_input.setText(path)
    
    def _on_ccs_path_changed(self, path):
        """Handle CCS path changes"""
        self.ccs_path = path
        self.ccs_path_changed.emit(path)
        # Update target configuration input state based on CCS path
        self._update_target_config_state()

    def _update_target_config_state(self):
        """Update the enabled state of target configuration UI based on CCS path"""
        # Enable target configuration only when CCS path is provided
        has_ccs_path = bool(self.ccs_path and self.ccs_path.strip())

        # Enable/disable the input field and browse button
        self.target_config_input.setEnabled(has_ccs_path)
        self.target_config_browse_button.setEnabled(has_ccs_path)

        # Update tooltip
        if has_ccs_path:
            self.target_config_input.setToolTip("Custom target configuration file")
        else:
            self.target_config_input.setToolTip("Enter a CCS path first to enable target configuration")

            # Clear the target configuration path if CCS path is empty
            if self.target_config_path:
                self.target_config_input.clear()
                self.target_config_path = ""

    def _browse_target_config(self):
        """Browse for target configuration file"""
        file_filter = "Target Configuration Files (*.ccxml);;All Files (*.*)"

        # Determine initial directory for file browser
        initial_dir = ""
        if self.target_config_path and os.path.exists(self.target_config_path):
            # If we have a detected path, use its directory
            initial_dir = os.path.dirname(self.target_config_path)
        else:
            # Otherwise, try to find the CCSTargetConfigurations directory
            home_dir = get_home_directory()
            possible_dirs = [
                os.path.join(home_dir, "ti", "CCSTargetConfigurations"),
                os.path.join("C:\\Users", getpass.getuser(), "ti", "CCSTargetConfigurations")
            ]
            for directory in possible_dirs:
                if os.path.exists(directory):
                    initial_dir = directory
                    break

        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Target Configuration File", initial_dir, file_filter
        )
        if file_path:
            self.target_config_path = file_path
            self.target_config_input.setText(file_path)

    def _on_target_config_changed(self, path):
        """Handle target configuration file path changes"""
        self.target_config_path = path
        self.target_config_changed.emit(path)

    def get_target_config_path(self):
        """Get the target configuration file path"""
        return self.target_config_path


    def handle_target_configuration(self):
        """Copy the target configuration file to the device-specific destination."""
        if not self.target_config_path or not os.path.exists(self.target_config_path):
            return None

        from apps.qtgui.devices.register import get_target_config_dest_for_device
        rel_dest = get_target_config_dest_for_device(self.device or "")
        if not rel_dest:
            return None

        rel_parts = rel_dest.replace("\\", "/").split("/")

        if hasattr(sys, '_MEIPASS'):  # Running in PyInstaller package
            dest_file = os.path.join(sys._MEIPASS, *rel_parts)
            os.makedirs(os.path.dirname(dest_file), exist_ok=True)
            try:
                shutil.copy2(self.target_config_path, dest_file)
                print(f"Target configuration file copied to: {dest_file}")
                return dest_file
            except Exception as e:
                print(f"Error copying target configuration file: {str(e)}")
                return None
        else:  # Running in normal Python environment
            dest_file = os.path.join(os.getcwd(), *rel_parts)
            os.makedirs(os.path.dirname(dest_file), exist_ok=True)

            # Back up original if present and not yet backed up
            backup_file = dest_file + ".original"
            if os.path.exists(dest_file) and not os.path.exists(backup_file):
                try:
                    shutil.copy2(dest_file, backup_file)
                    print(f"Original target configuration file backed up to: {backup_file}")
                except Exception as e:
                    print(f"Error backing up original target configuration file: {str(e)}")

            try:
                shutil.copy2(self.target_config_path, dest_file)
                print(f"Target configuration file copied to: {dest_file}")
                return dest_file
            except Exception as e:
                print(f"Error copying target configuration file: {str(e)}")
                return None
    
    def _show_error(self, message):
        """Show error message dialog"""
        error_box = QMessageBox()
        error_box.setIcon(QMessageBox.Warning)
        error_box.setText(message)
        error_box.setWindowTitle("Error")
        error_box.exec_()
    
    def on_generate_keys_clicked(self):
        """Handle Generate & Save button click"""
        name = self.new_keys_name_input.text().strip()
        password = self.new_keys_password_input.text().strip()
        
        # Create key data
        self.new_keys_data = {
            "name": name,
            "password": password,
            "type": "new"
        }
        
        # Store key data
        self.key_data = self.new_keys_data
        
        # Emit key_generated signal to trigger actual generation in the controller
        self.key_generated.emit(self.new_keys_data)

        # Show success message
        QMessageBox.information(
            self,
            "Success",
            f"Keys have been successfully generated for session: {name}"
        )

        self._session_confirmed = True
        self._update_certificate_buttons_status()
        self.key_selected.emit()
    
    def on_load_existing_keys_clicked(self):
        """Handle Load Existing Keys button click"""
        name = self.existing_keys_combo.currentText()
        password = self.existing_keys_password.text().strip()
        
        # Create key data
        self.existing_keys_data = {
            "name": name,
            "password": password,
            "type": "existing"
        }
        
        # Store key data
        self.key_data = self.existing_keys_data
        
        # Emit key_loaded signal to trigger actual loading in the controller
        self.key_loaded.emit(self.existing_keys_data)

        # Show success message
        QMessageBox.information(
            self,
            "Success",
            f"Keys have been successfully loaded for session: {name}"
        )

        self._session_confirmed = True
        self._update_certificate_buttons_status()
        self.key_selected.emit()
    
    def on_generate_sdk_keys_clicked(self):
        """Handle Generate SDK Keys button click"""
        name = self.sdk_name_input.text().strip()
        password = self.sdk_password_input.text().strip()
        version = "v15" if self.radio_v15.isChecked() else "v22"
        
        # Create key data
        self.sdk_keys_data = {
            "name": name,
            "password": password,
            "version": version,
            "type": "sdk"
        }
        
        # Store key data
        self.key_data = self.sdk_keys_data
        
        # Emit key_generated signal to trigger actual generation in the controller
        self.key_generated.emit(self.sdk_keys_data)

        # Show success message
        QMessageBox.information(
            self,
            "Success",
            f"SDK keys have been successfully generated for session: {name}"
        )

        self._session_confirmed = True
        self._update_certificate_buttons_status()
        self.key_selected.emit()
    
    def on_generate_pkcs11_keys_clicked(self):
        """Handle Generate PKCS#11 Keys button click"""
        name = self.pkcs11_name_input.text().strip()
        password = self.pkcs11_password_input.text().strip()

        # Check if a session with this name already exists
        try:
            from tisecprov.session import SecureSession
            with SecureSession() as s:
                session_exists = s.does_session_exist(name)
        except Exception:
            session_exists = False

        if session_exists:
            msg = QMessageBox(self)
            msg.setWindowTitle("Session Already Exists")
            msg.setText(f"A session named '{name}' already exists with HSM keys.\n\n"
                        "Do you want to reuse the existing keys or generate new ones?")
            msg.setIcon(QMessageBox.Question)
            reuse_btn = msg.addButton("Reuse Existing Keys", QMessageBox.AcceptRole)
            overwrite_btn = msg.addButton("Generate New Keys (Overwrite)", QMessageBox.DestructiveRole)
            msg.addButton("Cancel", QMessageBox.RejectRole)
            msg.exec_()
            clicked = msg.clickedButton()

            if clicked == reuse_btn:
                self.pkcs11_keys_data = {"name": name, "password": password, "type": "pkcs11"}
                self.key_data = self.pkcs11_keys_data
                self.key_loaded.emit(self.pkcs11_keys_data)
                QMessageBox.information(self, "Success",
                    f"Existing PKCS#11 keys loaded for session: {name}")
                self._session_confirmed = True
                self._update_certificate_buttons_status()
                self.key_selected.emit()
                return
            elif clicked != overwrite_btn:
                return  # Cancel — do nothing

        # Session does not exist or user chose to overwrite — proceed with generation
        self.pkcs11_keys_data = {"name": name, "password": password, "type": "pkcs11"}
        self.key_data = self.pkcs11_keys_data
        self.key_generated.emit(self.pkcs11_keys_data)
        QMessageBox.information(self, "Success",
            f"PKCS#11 keys have been successfully generated for session: {name}")
        self._session_confirmed = True
        self._update_certificate_buttons_status()
        self.key_selected.emit()
    
    def on_development_session_clicked(self, key_type):
        """Handle Development Session button click for any device."""
        session_data = {"type": key_type}
        for field_key, widget in self._key_panel_widgets.items():
            if isinstance(widget, QComboBox):
                session_data[field_key] = widget.currentData()
            elif isinstance(widget, QLineEdit):
                session_data[field_key] = widget.text()
            elif isinstance(widget, QCheckBox):
                session_data[field_key] = widget.isChecked()

        self.key_data = session_data
        self._session_confirmed = True

        self.development_session_set.emit(session_data)
        if key_type == "f29_development":
            self.f29_development_session_set.emit(session_data)

        QMessageBox.information(self, "Success", "Development Session has been set up")
        self._update_certificate_buttons_status()
        self.key_selected.emit()
    
    def validate(self):
        """Validate the entire page before proceeding"""
        # Check if device is selected
        if not self.device_dropdown.currentText():
            self._show_error("Please select a device")
            return False

        # Check if key type is selected
        if not any(button.isChecked() for button in self.key_selection_button_group.buttons()):
            self._show_error("Please select a key type")
            return False

        # Check that the key setup was actually completed
        if not self._session_confirmed:
            self._show_error("Please complete the key setup before proceeding")
            return False

        # If a custom target configuration file is provided, apply it now
        if self.target_config_path and os.path.exists(self.target_config_path):
            try:
                result_path = self.handle_target_configuration()
                if result_path:
                    print(f"Target configuration file applied: {result_path}")
                    QMessageBox.information(
                        self,
                        "Target Configuration Applied",
                        "The custom target configuration file has been successfully applied and will be used for JTAG operations."
                    )
                else:
                    print("Target configuration file could not be applied")
                    QMessageBox.warning(
                        self,
                        "Target Configuration Not Applied",
                        "The target configuration file could not be applied. The default configuration will be used."
                    )
                    # We don't prevent moving to the next page if the configuration fails
            except Exception as e:
                print(f"Error applying target configuration: {str(e)}")
                QMessageBox.critical(
                    self,
                    "Error Applying Configuration",
                    f"An error occurred while applying the target configuration: {str(e)}\nThe default configuration will be used."
                )
                # We don't prevent moving to the next page if the configuration fails

        return True
    
    def is_valid(self):
        """Check if the page has valid data for enabling Next button"""
        # Device must be selected
        if not self.device_dropdown.currentText():
            return False
        
        # Key type must be selected
        if not any(button.isChecked() for button in self.key_selection_button_group.buttons()):
            return False
        
        # Key setup must have been completed
        if not self._session_confirmed:
            return False
        
        return True
    
    def get_selected_device(self):
        """Get the selected device"""
        return self.device_dropdown.currentText()
    
    def get_selected_key_type(self):
        """Get the selected key type"""
        return self.key_type
    
    def get_session_name(self):
        """Get the session name based on key type"""
        if self.key_type == "new" and hasattr(self, 'new_keys_data'):
            return self.new_keys_data.get("name", "")
        elif self.key_type == "existing" and hasattr(self, 'existing_keys_data'):
            return self.existing_keys_data.get("name", "")
        elif self.key_type == "sdk" and hasattr(self, 'sdk_keys_data'):
            return self.sdk_keys_data.get("name", "")
        elif self.key_type == "pkcs11" and hasattr(self, 'pkcs11_keys_data'):
            return self.pkcs11_keys_data.get("name", "")
        elif self._session_confirmed:
            return "Development"
        return ""
    
    def get_session_password(self):
        """Get the session password based on key type"""
        if self.key_type == "new" and hasattr(self, 'new_keys_data'):
            return self.new_keys_data.get("password", "")
        elif self.key_type == "existing" and hasattr(self, 'existing_keys_data'):
            return self.existing_keys_data.get("password", "")
        elif self.key_type == "sdk" and hasattr(self, 'sdk_keys_data'):
            return self.sdk_keys_data.get("password", "")
        elif self.key_type == "pkcs11" and hasattr(self, 'pkcs11_keys_data'):
            return self.pkcs11_keys_data.get("password", "")
        return ""
    
    def get_key_data(self):
        """Get the key data"""
        return self.key_data
        
    def get_ccs_path(self):
        """Get the CCS installation path"""
        return self.ccs_path

    # ------------------------------------------------------------------
    # Dynamic certificate UI builder
    # ------------------------------------------------------------------

    _TAB_STYLE = """
        QTabBar::tab {
            height: 30px;
            min-width: 140px;
            padding: 2px 15px;
            font-size: 14px;
        }
        QTabWidget::pane {
            border-top: 1px solid #C2C7CB;
            margin-top: -1px;
        }
    """

    _CERT_BTN_STYLE = """
        QPushButton {
            background-color: #CC0000;
            color: white;
            padding: 10px 25px;
            border: none;
            border-radius: 6px;
            min-width: 220px;
            font-size: 15px;
            font-weight: bold;
        }
        QPushButton:hover { background-color: #990000; }
        QPushButton:disabled { background-color: #cccccc; color: #666666; }
    """

    _CERT_BTN_SUCCESS_STYLE = """
        QPushButton {
            background-color: #28a745;
            color: white;
            padding: 8px 20px;
            border: none;
            border-radius: 4px;
            min-width: 180px;
        }
        QPushButton:hover { background-color: #218838; }
    """

    def _make_field_row(self, field):
        """Create a widget for a field spec and register it in _cert_widgets.

        Returns (data_widget, row_widget_or_layout) where row_widget_or_layout
        is what should be added to a form row.  data_widget is stored in
        self._cert_widgets[key] and is used to read the field value.
        """
        key = field['key']
        wtype = field['widget_type']
        default = field.get('default', '')

        if wtype == 'text':
            w = QLineEdit(str(default))
            w.setMinimumHeight(30)
            w.setStyleSheet("QLineEdit { font-size: 13px; }")
            if 'placeholder' in field:
                w.setPlaceholderText(field['placeholder'])
            self._cert_widgets[key] = w
            return w, w

        if wtype in ('file_browse', 'dir_browse'):
            w = QLineEdit(str(default))
            w.setMinimumHeight(30)
            self._cert_widgets[key] = w
            btn = QPushButton("Browse")
            btn.setMinimumHeight(30)
            btn.setMinimumWidth(100)
            if wtype == 'file_browse':
                btn.clicked.connect(lambda _checked, edit=w: self._browse_file(edit))
            else:
                btn.clicked.connect(lambda _checked, edit=w: self._browse_dir(edit))
            row = QHBoxLayout()
            row.setSpacing(10)
            row.addWidget(w)
            row.addWidget(btn)
            return w, row

        if wtype == 'combo':
            w = QComboBox()
            w.setMinimumHeight(30)
            w.setStyleSheet("QComboBox { font-size: 13px; }")
            for opt_label, opt_val in field.get('options', []):
                w.addItem(opt_label, opt_val)
            # Select default value
            for i in range(w.count()):
                if w.itemData(i) == str(default):
                    w.setCurrentIndex(i)
                    break
            self._cert_widgets[key] = w
            return w, w

        if wtype == 'checkbox':
            w = QCheckBox(field['label'])
            w.setChecked(bool(default))
            w.setMinimumHeight(30)
            w.setStyleSheet("QCheckBox { font-size: 14px; }")
            self._cert_widgets[key] = w
            return w, w

        if wtype == 'ext_otp_rows':
            w = ExtOtpRowsWidget(
                default_value=field.get('default_value', '0x80000001'),
                default_size=field.get('default_size', '128'),
                num_rows=int(field.get('num_rows', 13)),
                row_bits=int(field.get('row_bits', 128)),
            )
            self._cert_widgets[key] = w
            return w, w

        raise ValueError(f"Unknown widget_type: {wtype!r}")

    def _build_cert_group(self, device_name, cert_fields, cert_flags):
        """Build and return a QGroupBox for certificate generation.

        Stores all data widgets in self._cert_widgets and the always-on flags
        in self._cert_flags.  Sets self._cert_btn to the Generate button and
        self._current_cert_fields to the field spec list.
        """
        self._cert_widgets = {}
        self._cert_flags = list(cert_flags)
        self._current_cert_fields = cert_fields

        # Partition fields into top-level and tabbed
        top_fields = [f for f in cert_fields if f.get('tab') is None]
        tab_map = {}  # ordered dict: tab_name -> [field, ...]
        for f in cert_fields:
            tab = f.get('tab')
            if tab is not None:
                tab_map.setdefault(tab, []).append(f)

        group_box = QGroupBox(f"{device_name.upper()} Certificate Generation")
        group_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        main_layout = QVBoxLayout(group_box)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # Top-level fields (above Advanced Settings)
        for field in top_fields:
            _data_w, row = self._make_field_row(field)
            if field['widget_type'] == 'checkbox':
                cb_layout = QHBoxLayout()
                cb_layout.addWidget(_data_w)
                cb_layout.addStretch()
                main_layout.addLayout(cb_layout)
            else:
                h = QHBoxLayout()
                h.setSpacing(10)
                lbl = QLabel(field['label'] + ':')
                lbl.setMinimumWidth(120)
                lbl.setStyleSheet("font-size: 13px;")
                h.addWidget(lbl)
                if isinstance(row, QHBoxLayout):
                    h.addLayout(row)
                else:
                    h.addWidget(row)
                main_layout.addLayout(h)

        # Tabbed fields inside a CollapsibleSection
        if tab_map:
            main_layout.addSpacing(15)
            adv_section = CollapsibleSection("Advanced Settings")
            tab_widget = QTabWidget()
            tab_widget.setMaximumHeight(400)
            tab_widget.setStyleSheet(self._TAB_STYLE)

            for tab_name, fields in tab_map.items():
                tab_page = QWidget()
                form = QFormLayout(tab_page)
                form.setSpacing(15)
                form.setContentsMargins(15, 20, 15, 15)

                for field in fields:
                    if field['widget_type'] in ('checkbox', 'ext_otp_rows'):
                        _data_w, row = self._make_field_row(field)
                        form.addRow(row)
                    else:
                        _data_w, row = self._make_field_row(field)
                        lbl = QLabel(field['label'] + ':')
                        lbl.setStyleSheet("font-size: 13px;")
                        if isinstance(row, QHBoxLayout):
                            form.addRow(lbl, row)
                        else:
                            form.addRow(lbl, row)

                tab_widget.addTab(tab_page, tab_name)

            adv_section.add_widget(tab_widget)
            main_layout.addWidget(adv_section)
            main_layout.addSpacing(15)

        # Generate Certificate button
        cert_btn = QPushButton("Generate Certificate")
        cert_btn.setMinimumHeight(40)
        cert_btn.setToolTip(
            "Important: Select and generate/load keys first before generating a certificate"
        )
        cert_btn.setStyleSheet(self._CERT_BTN_STYLE)
        cert_btn.clicked.connect(self._on_generate_certificate)
        self._cert_btn = cert_btn

        main_layout.addWidget(cert_btn, 0, Qt.AlignCenter)
        return group_box

    def _update_certificate_ui(self, device):
        """Rebuild the certificate UI group for the selected device."""
        if not device:
            self.certificate_group.hide()
            return

        self.certificate_group.show()

        # Remove previous cert group widget from layout
        if self._cert_group_widget is not None:
            self.certificate_layout.removeWidget(self._cert_group_widget)
            self._cert_group_widget.deleteLater()
            self._cert_group_widget = None
            self._cert_btn = None

        # Get field specs for this device
        from apps.qtgui.devices.register import get_cert_fields_for_device
        fields, flags = get_cert_fields_for_device(device.lower())

        # Build and add new cert group
        self._cert_group_widget = self._build_cert_group(device.lower(), fields, flags)
        self.certificate_layout.addWidget(self._cert_group_widget)

        self._prepopulate_cert_defaults(device.lower())

        # Update button enabled state
        self._update_certificate_buttons_status()
    
    def _prepopulate_cert_defaults(self, device):
        """Set dynamic default values (paths, output dir) in the cert widgets."""
        from apps.qtgui.views.pages.automations import apply_cert_defaults
        apply_cert_defaults(device.lower(), self._cert_widgets)

    def _browse_file(self, edit_widget):
        """Generic browse-for-file handler; sets result into edit_widget."""
        file_filter = "Public Key Files (*.pem *.key);;All Files (*.*)"
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File", "", file_filter)
        if file_path:
            edit_widget.setText(file_path)

    def _browse_dir(self, edit_widget):
        """Generic browse-for-directory handler; sets result into edit_widget."""
        folder = QFileDialog.getExistingDirectory(self, "Select Directory")
        if folder:
            edit_widget.setText(folder)
    
    def _collect_cert_data(self):
        """Read all cert widget values into a flat dict."""
        data = {
            "device": self.device.lower() if self.device else "",
            "flags": list(self._cert_flags),
        }
        for key, widget in self._cert_widgets.items():
            if isinstance(widget, QCheckBox):
                data[key] = widget.isChecked()
            elif isinstance(widget, QComboBox):
                data[key] = widget.currentData()
            elif isinstance(widget, QLineEdit):
                data[key] = widget.text()
            elif isinstance(widget, ExtOtpRowsWidget):
                selected = widget.get_selected()
                if selected:
                    data['ext_otp'] = selected['value']
                    data['ext_otp_indx'] = selected['index']
                    data['ext_otp_size'] = selected['size']
        return data

    def _on_generate_certificate(self):
        """Unified certificate generation handler for all devices."""
        if not self.key_type or not self.key_data:
            self._show_error("Please select and generate/load keys before creating a certificate")
            return

        # Validate required fields
        for field_spec in self._current_cert_fields:
            if field_spec.get('required') and field_spec['key'] in self._cert_widgets:
                w = self._cert_widgets[field_spec['key']]
                if isinstance(w, QLineEdit) and not w.text().strip():
                    self._show_error(f"Please fill in: {field_spec['label']}")
                    return

        # Validate MSV format
        if 'msv' in self._cert_widgets:
            msv = self._cert_widgets['msv'].text()
            if not msv.startswith("0x") or len(msv) < 3:
                self._show_error("Invalid MSV format")
                return

        # Validate ext_otp if a row is selected
        if 'ext_otp_rows' in self._cert_widgets:
            otp_widget = self._cert_widgets['ext_otp_rows']
            sel = otp_widget.get_selected()
            if sel:
                if not sel['value']:
                    self._show_error("Extended OTP: please enter a value for the selected row")
                    return
                if not sel['size'].isdigit() or int(sel['size']) < 32 or int(sel['size']) % 8 != 0:
                    self._show_error("Extended OTP: size must be a multiple of 8 and at least 32 bits")
                    return
                import re as _re
                cleaned = sel['value'].replace('0x', '').replace('0X', '')
                if not _re.match(r'^[0-9a-fA-F]+$', cleaned):
                    self._show_error("Extended OTP: value must be a valid hexadecimal number")
                    return

        # Validate key revision does not exceed key count
        if 'keycnt' in self._cert_widgets and 'keyrev' in self._cert_widgets:
            keycnt_w = self._cert_widgets['keycnt']
            keyrev_w = self._cert_widgets['keyrev']
            if isinstance(keycnt_w, QComboBox) and isinstance(keyrev_w, QComboBox):
                try:
                    keycnt_val = int(keycnt_w.currentData())
                    keyrev_val = int(keyrev_w.currentData())
                    if keyrev_val > keycnt_val:
                        self._show_error(
                            f"Key Revision ({keyrev_val}) cannot be greater than the number of "
                            f"programmed keys ({keycnt_val}).\n"
                            "Select a Key Revision that does not exceed the number of keys being programmed."
                        )
                        return
                except (ValueError, TypeError):
                    pass

        cert_data = self._collect_cert_data()

        # Apply any key_data → cert_data field mappings defined in the key option spec
        if self.key_data:
            current_spec = next(
                (s for s in self._key_options if s.get("key_type") == self.key_type), {}
            )
            for cert_key, data_key in current_spec.get("cert_data_mappings", {}).items():
                if data_key in self.key_data:
                    cert_data[cert_key] = self.key_data[data_key]

        # Validate tifek file exists if provided
        pub_key_widget = self._cert_widgets.get('pub_key_path')
        if pub_key_widget and isinstance(pub_key_widget, QLineEdit):
            path = pub_key_widget.text().strip()
            if path and not os.path.isfile(path):
                self._show_error(f"TI FEK public key file not found:\n{path}")
                return

        print(f"Generate certificate: {cert_data}")
        try:
            self.certificate_request.emit(cert_data)
        except Exception as e:
            self._show_error(f"Certificate generation failed:\n{str(e)}")
            return

        self.certificate_data = cert_data
        QMessageBox.information(self, "Success", "Certificate has been successfully generated")

        if self._cert_btn is not None:
            self._cert_btn.setText("Certificate Generated ✓")
            self._cert_btn.setStyleSheet(self._CERT_BTN_SUCCESS_STYLE)
        
    def update_certificate_button(self):
        """Update the Generate Certificate button to reflect current state."""
        if self._cert_btn is None:
            return
        if hasattr(self, 'certificate_data') and self.certificate_data:
            self._cert_btn.setText("Certificate Generated ✓")
            self._cert_btn.setStyleSheet(self._CERT_BTN_SUCCESS_STYLE)
        else:
            self._cert_btn.setText("Generate Certificate")
            self._cert_btn.setStyleSheet(self._CERT_BTN_STYLE)
        self._update_certificate_buttons_status()
    
    def get_certificate_info(self):
        """Get certificate generation info"""
        return self.certificate_data if hasattr(self, 'certificate_data') else None
        
    def _update_certificate_buttons_status(self):
        """Enable/disable the Generate Certificate button based on keys and addon state."""
        has_keys = self.key_type is not None and self.key_data is not None
        if self._cert_btn is not None:
            enabled = has_keys and self._addon_installed
            self._cert_btn.setEnabled(enabled)
            if not self._addon_installed:
                tip = (f"Device addon not installed — certificate generation unavailable "
                       f"for {self.device or 'this device'}")
            elif has_keys:
                tip = "Generate certificate using the selected keys"
            else:
                tip = "Please select and generate/load keys first before generating a certificate"
            self._cert_btn.setToolTip(tip)