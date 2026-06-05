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
    QStackedWidget,
    QPushButton,
    QLabel,
    QFrame,
    QProgressBar,
    QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon, QPixmap
from importlib import resources

try:
    from .pages.landing_page import LandingPage
    from .pages.config_page import ConfigPage
    from .pages.provisioning_page import ProvisioningPage
    from .pages.automations import has_config_page_enter_automation, run_config_page_enter_automation
except ImportError:
    # Handle package structure for direct imports
    from apps.qtgui.views.pages.landing_page import LandingPage
    from apps.qtgui.views.pages.config_page import ConfigPage
    from apps.qtgui.views.pages.provisioning_page import ProvisioningPage
    from apps.qtgui.views.pages.automations import has_config_page_enter_automation, run_config_page_enter_automation

def get_image_path(image_name):
    with resources.path("apps.qtgui.assets", image_name) as image_path:
        return str(image_path)

class WizardView(QWidget):
    """Main wizard container that manages all pages and navigation between them"""

    wizard_completed = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.session_data = {}  # Dictionary to store shared data between pages
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI components"""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Add header with TI logo and title
        header_widget = self.create_header()
        main_layout.addWidget(header_widget)
        
        # Progress indicator
        self.progress_widget = self.create_progress_indicator()
        main_layout.addWidget(self.progress_widget)
        
        # Stacked widget to hold pages
        self.stacked_widget = QStackedWidget()
        
        # Create pages
        self.landing_page = LandingPage()
        self.config_page = ConfigPage()
        self.provisioning_page = ProvisioningPage()
        
        # Add pages to stacked widget
        self.stacked_widget.addWidget(self.landing_page)
        self.stacked_widget.addWidget(self.config_page)
        self.stacked_widget.addWidget(self.provisioning_page)
        
        # Add stacked widget to main layout (stretch=1 keeps nav buttons always visible)
        main_layout.addWidget(self.stacked_widget, 1)
        
        # Navigation buttons
        nav_layout = QHBoxLayout()
        nav_layout.setContentsMargins(10, 10, 10, 10)
        
        # Back button
        self.back_button = QPushButton("Back")
        self.back_button.setFixedWidth(100)
        self.back_button.clicked.connect(self.go_back)
        self.back_button.setEnabled(False)  # Disabled on first page
        
        # Next button
        self.next_button = QPushButton("Next")
        self.next_button.setFixedWidth(100)
        self.next_button.clicked.connect(self.go_next)
        
        # Add buttons to nav layout
        nav_layout.addStretch()
        nav_layout.addWidget(self.back_button)
        nav_layout.addWidget(self.next_button)
        
        # Add nav layout to main layout
        main_layout.addLayout(nav_layout)
        
        # Set initial page
        self.stacked_widget.setCurrentIndex(0)
        self.update_ui_for_current_page()
        
        # Connect page signals
        self.landing_page.device_changed.connect(self.handle_device_changed)
        self.landing_page.key_selected.connect(self.handle_key_selected)
        self.landing_page.ccs_path_changed.connect(self.handle_ccs_path_changed)
        self.landing_page.certificate_request.connect(self.handle_certificate_request)
        self.config_page.boot_mode_changed.connect(self.handle_boot_mode_changed)
        
        # Set styling
        self.setStyleSheet("""
            QPushButton {
                background-color: #CC0000;
                color: white;
                padding: 8px 20px;
                border: none;
                min-width: 100px;
                font-size: 14px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #990000;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
    
    def create_header(self):
        """Create the header with logo and title"""
        header_widget = QWidget()
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(10, 5, 10, 5)
        
        # TI Logo
        logo_label = QLabel()
        try:
            logo_path = get_image_path("TI_square_bug.jpg")
            logo_pixmap = QPixmap(logo_path)
            if not logo_pixmap.isNull():
                scaled_logo = logo_pixmap.scaled(
                    30, 30, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                logo_label.setPixmap(scaled_logo)
        except Exception as e:
            print(f"Error loading logo: {e}")
            logo_label.setText("TI")  # Fallback text if image fails to load
        
        # Application title next to logo
        app_title = QLabel("Texas Instruments Cybershield Toolkit")
        app_title.setStyleSheet("color: white; font-size: 16px;")
        
        header_layout.addWidget(logo_label)
        header_layout.addWidget(app_title)
        header_layout.addStretch()
        
        header_widget.setLayout(header_layout)
        header_widget.setStyleSheet("background-color: #CC0000;")
        header_widget.setFixedHeight(40)
        
        return header_widget
    
    def create_progress_indicator(self):
        """Create progress indicator with step labels"""
        progress_widget = QWidget()
        progress_layout = QVBoxLayout(progress_widget)
        
        # Steps container
        steps_layout = QHBoxLayout()
        
        # Step 1: Device & Key Selection
        self.step1_label = QLabel("1. Device & Key Selection")
        self.step1_label.setStyleSheet("font-weight: bold; color: #CC0000;")
        
        # Step 2: Configuration
        self.step2_label = QLabel("2. Configuration")
        self.step2_label.setStyleSheet("font-weight: normal; color: #666666;")
        
        # Step 3: Provisioning
        self.step3_label = QLabel("3. Provisioning")
        self.step3_label.setStyleSheet("font-weight: normal; color: #666666;")
        
        # Add steps to layout with spacers
        steps_layout.addWidget(self.step1_label)
        steps_layout.addStretch()
        steps_layout.addWidget(self.step2_label)
        steps_layout.addStretch()
        steps_layout.addWidget(self.step3_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 2)  # 3 steps (0-based)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                background-color: #EEEEEE;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #CC0000;
                border-radius: 3px;
            }
        """)
        
        # Add to progress layout
        progress_layout.addLayout(steps_layout)
        progress_layout.addWidget(self.progress_bar)
        
        # Add separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background-color: #CCCCCC;")
        progress_layout.addWidget(separator)
        
        return progress_widget
    
    def update_progress_indicator(self, current_step):
        """Update progress indicator based on current step"""
        # Reset all steps to normal
        self.step1_label.setStyleSheet("font-weight: normal; color: #666666;")
        self.step2_label.setStyleSheet("font-weight: normal; color: #666666;")
        self.step3_label.setStyleSheet("font-weight: normal; color: #666666;")
        
        # Highlight current step
        if current_step == 0:
            self.step1_label.setStyleSheet("font-weight: bold; color: #CC0000;")
        elif current_step == 1:
            self.step2_label.setStyleSheet("font-weight: bold; color: #CC0000;")
        elif current_step == 2:
            self.step3_label.setStyleSheet("font-weight: bold; color: #CC0000;")
        
        # Update progress bar
        self.progress_bar.setValue(current_step)
    
    def update_ui_for_current_page(self):
        """Update UI based on current page index"""
        current_index = self.stacked_widget.currentIndex()
        
        # Enable/disable back button
        self.back_button.setEnabled(current_index > 0)
        
        # Update next button text for last page
        if current_index == self.stacked_widget.count() - 1:
            self.next_button.setText("Finish")
        else:
            self.next_button.setText("Next")
        
        # Update progress indicator
        self.update_progress_indicator(current_index)
        
        # Update next button enabled state based on page validation
        if current_index == 0:
            self.next_button.setEnabled(self.landing_page.is_valid())
        elif current_index == 1:
            # Next button is always enabled, but we'll validate when it's clicked
            self.next_button.setEnabled(True)
            
    def go_next(self):
        """Handle next button click"""
        current_index = self.stacked_widget.currentIndex()
        current_widget = self.stacked_widget.currentWidget()
        
        # Validate current page before proceeding
        if current_index == 0 and not self.landing_page.validate():
            return
        elif current_index == 1:
            # Validate boot mode - it's required regardless of device state
            if not self.config_page.get_boot_mode():
                self._show_error("Please select a boot mode")
                return
            
            # Device state is also required
            if not self.config_page.get_device_state():
                self._show_error("Please detect or enter a device state")
                return
            
        # If on last page, finish the wizard
        if current_widget in [self.provisioning_page]:
            self.finish_wizard()
            return
            
        # If this is the first page, pass data to second page
        if current_index == 0:
            self.prepare_config_page()
            self.stacked_widget.setCurrentWidget(self.config_page)
        
        # If this is the second page, pass data to third page
        elif current_index == 1:
            self.prepare_provisioning_page()
            # The prepare_provisioning_page method will set the appropriate page
            # based on the device state, so we don't need to set it here
        
        self.update_ui_for_current_page()
    
    def go_back(self):
        """Handle back button click"""
        current_index = self.stacked_widget.currentIndex()
        if current_index > 0:
            self.stacked_widget.setCurrentIndex(current_index - 1)
            self.update_ui_for_current_page()
    
    def prepare_config_page(self):
        """Prepare the config page with data from landing page"""
        # Get data from landing page
        device = self.landing_page.get_selected_device()
        key_type = self.landing_page.get_selected_key_type()
        key_data = self.landing_page.get_key_data()
        ccs_path = self.landing_page.get_ccs_path()
        certificate_info = self.landing_page.get_certificate_info()
        target_config_path = self.landing_page.get_target_config_path()

        # Store in session data
        self.session_data['device'] = device
        self.session_data['key_type'] = key_type
        self.session_data['key_data'] = key_data
        self.session_data['ccs_path'] = ccs_path
        self.session_data['certificate_info'] = certificate_info
        self.session_data['target_config_path'] = target_config_path
        
        # Update config page
        self.config_page.set_device(device)
        self.config_page.set_key_info(key_type, key_data)
        self.config_page.set_ccs_path(ccs_path)
        self.config_page.set_target_config_path(target_config_path)
        self.config_page.set_certificate_info(certificate_info)
        
        # Run config-page-enter automation if one is registered and addon is installed.
        controller = getattr(self.parent(), "controller", None)
        if controller is not None and has_config_page_enter_automation(device):
            from PyQt5.QtCore import QCoreApplication
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setText("Please wait...")
            msg.setWindowTitle("Processing")
            msg.setStandardButtons(QMessageBox.NoButton)
            msg.setModal(True)
            msg.show()
            QCoreApplication.processEvents()

            success, message = run_config_page_enter_automation(device, self.session_data, controller)

            msg.close()

            if not success:
                QMessageBox.warning(
                    self,
                    "Binary Signing Error",
                    f"Error signing binaries: {message}",
                )
    
    def prepare_provisioning_page(self):
        """Prepare the provisioning page with data from config page"""
        # Get data from config page
        boot_mode = self.config_page.get_boot_mode()
        connection_info = self.config_page.get_connection_info()
        device_state = self.config_page.get_device_state()
        certificate_info = self.config_page.get_certificate_info()
        
        # Store in session data
        self.session_data['boot_mode'] = boot_mode
        self.session_data['connection_info'] = connection_info
        self.session_data['device_state'] = device_state
        self.session_data['certificate_info'] = certificate_info
        
        # Trim whitespace and uppercase device state for consistent comparison
        device_state = device_state.strip().upper() if device_state else ''
        
        self.stacked_widget.setCurrentWidget(self.provisioning_page)
        self.provisioning_page.set_session_info(self.session_data)
    
    def finish_wizard(self):
        """Handle finish button click"""
        kp_data = self.provisioning_page.provisioning_data       # None if KP was not run
        cp_data = self.provisioning_page.code_provisioning_data  # None if CP was not run

        # Keep provisioning_data for backward compatibility
        self.session_data['provisioning_data'] = cp_data if cp_data is not None else kp_data
        self.session_data['kp_data'] = kp_data
        self.session_data['cp_data'] = cp_data

        print("Wizard completed with data:", self.session_data)
        self.wizard_completed.emit(self.session_data)
        
    # Signal handlers
    def handle_device_changed(self, device):
        """Handle device changed signal from landing page"""
        self.next_button.setEnabled(self.landing_page.is_valid())
        
    def handle_key_selected(self):
        """Handle key selection signal from landing page"""
        self.next_button.setEnabled(self.landing_page.is_valid())
        
    def handle_device_state_changed(self, new_state):
        """Handle device state change (e.g., HSFS -> HSKP after conversion)"""
        # Update the session data
        self.session_data['device_state'] = new_state
        # Update provisioning page with new state
        self.provisioning_page.set_session_info(self.session_data)
        # Ensure provisioning page is visible and UI is updated
        self.stacked_widget.setCurrentWidget(self.provisioning_page)
        self.update_ui_for_current_page()
    
    def _show_error(self, message):
        """Show error message dialog"""
        error_box = QMessageBox()
        error_box.setIcon(QMessageBox.Warning)
        error_box.setText(message)
        error_box.setWindowTitle("Error")
        error_box.exec_()
    def handle_boot_mode_changed(self):
        """Handle boot mode changed signal from config page"""
        # Next button is always enabled for the config page
        self.next_button.setEnabled(True)
        
    def handle_certificate_generated(self):
        """Handle certificate generated signal - no longer used"""
        # This method is kept for backward compatibility but is no longer active
        pass
        
    def handle_ccs_path_changed(self, path):
        """Handle CCS path changed signal from landing page"""
        # Update session data with the new CCS path
        self.session_data['ccs_path'] = path
        
        # If config page is already created and stacked_widget exists, update it
        if hasattr(self, 'config_page') and hasattr(self, 'stacked_widget'):
            # Only update if config_page is already initialized
            # This prevents errors during startup sequence
            if self.stacked_widget.indexOf(self.config_page) >= 0:
                self.config_page.set_ccs_path(path)
    
    def handle_certificate_request(self, certificate_data):
        """Handle certificate request from landing page"""
        # Update session data with the new certificate info
        self.session_data['certificate_info'] = certificate_data
        
        # If config page is already created, update it
        if hasattr(self, 'config_page') and hasattr(self, 'stacked_widget'):
            if self.stacked_widget.indexOf(self.config_page) >= 0:
                self.config_page.set_certificate_info(certificate_data)
        
    def handle_operation_result(self, success, message):
        """Handle operation result signal from controller"""
        current_widget = self.stacked_widget.currentWidget()
        
        # Forward the operation result to the current page if it has a handle_operation_result method
        if hasattr(current_widget, 'handle_operation_result'):
            current_widget.handle_operation_result(success, message)
            
