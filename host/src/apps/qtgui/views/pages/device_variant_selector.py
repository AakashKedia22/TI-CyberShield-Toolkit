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
    QLabel,
    QComboBox,
    QFrame
)
from PyQt5.QtCore import pyqtSignal

from apps.qtgui import settings

class DeviceVariantSelector(QWidget):
    """
    A widget for selecting a device and its variant.
    
    This widget provides dropdowns for both device and variant selection,
    with the variant dropdown being updated dynamically based on the
    selected device.
    """
    
    # Signals
    device_variant_changed = pyqtSignal(str, str)  # (device, variant)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI components"""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # Device selection row
        device_layout = QHBoxLayout()
        device_label = QLabel("Device:")
        self.device_dropdown = QComboBox()
        self.device_dropdown.setPlaceholderText("Select Device")
        
        # Add devices from settings
        self.device_dropdown.addItem("")  # Empty first item
        self.device_dropdown.addItems(settings.devices)
        
        device_layout.addWidget(device_label)
        device_layout.addWidget(self.device_dropdown)
        layout.addLayout(device_layout)
        
        # Variant selection row
        variant_layout = QHBoxLayout()
        variant_label = QLabel("Variant:")
        self.variant_dropdown = QComboBox()
        self.variant_dropdown.setPlaceholderText("Select Variant")
        self.variant_dropdown.setEnabled(False)  # Disabled until device selected
        
        variant_layout.addWidget(variant_label)
        variant_layout.addWidget(self.variant_dropdown)
        layout.addLayout(variant_layout)
        
        # Add a separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)
        
        # Connect signals
        self.device_dropdown.currentTextChanged.connect(self._on_device_changed)
        self.variant_dropdown.currentTextChanged.connect(self._on_variant_changed)
    
    def _on_device_changed(self, device):
        """
        Handle device selection changes.
        
        Args:
            device (str): The selected device name
        """
        # Clear the variant dropdown
        self.variant_dropdown.clear()
        
        if not device:
            self.variant_dropdown.setEnabled(False)
            return
        
        # Get variants for the selected device
        variants = settings.get_variants_for_device(device)
        
        # Enable/disable variant dropdown based on available variants
        has_variants = len(variants) > 0
        self.variant_dropdown.setEnabled(has_variants)
        
        if has_variants:
            # Add variants to the dropdown with display names
            for variant in variants:
                display_name = settings.get_display_name(device, variant)
                self.variant_dropdown.addItem(display_name, variant)
                
            # Select the first variant by default
            if self.variant_dropdown.count() > 0:
                self.variant_dropdown.setCurrentIndex(0)
                self._emit_device_variant_changed()
        else:
            # If no variants available, emit with empty variant
            self.device_variant_changed.emit(device, "")
    
    def _on_variant_changed(self, _):
        """
        Handle variant selection changes.
        
        Args:
            _ (str): The display name (ignored, we use userData instead)
        """
        self._emit_device_variant_changed()
    
    def _emit_device_variant_changed(self):
        """Emit device_variant_changed signal with current selection"""
        device = self.device_dropdown.currentText()
        if not device:
            return
            
        # Get the variant from userData to handle display names
        variant = self.variant_dropdown.currentData()
        
        if variant:
            self.device_variant_changed.emit(device, variant)
    
    def get_selected_device(self):
        """Get the selected device name"""
        return self.device_dropdown.currentText()
    
    def get_selected_variant(self):
        """Get the selected variant name"""
        return self.variant_dropdown.currentData()
    
    def set_device_variant(self, device, variant):
        """
        Set the device and variant selection.
        
        Args:
            device (str): Device name to select
            variant (str): Variant name to select
        """
        # Set device first (this will update the variant dropdown)
        index = self.device_dropdown.findText(device)
        if index >= 0:
            self.device_dropdown.setCurrentIndex(index)
            
            # Now set the variant
            variant_index = -1
            for i in range(self.variant_dropdown.count()):
                if self.variant_dropdown.itemData(i) == variant:
                    variant_index = i
                    break
                    
            if variant_index >= 0:
                self.variant_dropdown.setCurrentIndex(variant_index)
                
    def is_valid(self):
        """Check if a valid device and variant are selected"""
        device = self.device_dropdown.currentText()
        variant = self.variant_dropdown.currentData()
        return bool(device) and bool(variant)