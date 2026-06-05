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
    QWidget, QVBoxLayout, QFormLayout, QGroupBox, QLabel, QFrame, QSizePolicy,
)
from PyQt5.QtCore import Qt


class SessionInfoPanel(QWidget):
    """Session information display panel — labels + DeviceStateIndicator.

    Owns all the labels that were previously inline in
    ProvisioningPage.init_ui / set_session_info.  provisioning_page.py
    creates ProvisioningDetailsPanel separately, passes a reference here so
    update() / set_device_state() can call configure_states() /
    set_current_state() on it.
    """

    def __init__(self, details_panel, parent=None):
        """
        Args:
            details_panel: ProvisioningDetailsPanel instance.  A reference only —
                           the widget is owned by provisioning_page.py and added to
                           a separate group box in the main layout.
        """
        super().__init__(parent)
        self._details_panel = details_panel

        # Lazy import breaks the potential circular dependency with provisioning_page.py
        from apps.qtgui.views.pages.provisioning_page import DeviceStateIndicator

        self._group = QGroupBox("Session Information")
        self._group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        self._layout = QFormLayout()
        self._layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        # --- Labels ---
        self.device_label = QLabel("")
        self._layout.addRow("Device:", self.device_label)

        self.device_state_label = QLabel("")
        self._layout.addRow("Device State:", self.device_state_label)

        # Visual separator before the state progression widget
        _sep = QFrame()
        _sep.setFrameShape(QFrame.HLine)
        _sep.setFrameShadow(QFrame.Sunken)
        _sep.setStyleSheet("background-color: #CCCCCC;")
        self._layout.addRow("", _sep)

        self.state_indicator = DeviceStateIndicator()
        self.state_indicator.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._layout.addRow("Provisioning Progress:", self.state_indicator)

        self.boot_mode_label = QLabel("")
        self._layout.addRow("Boot Mode:", self.boot_mode_label)

        self.connection_info_label = QLabel("")
        self._layout.addRow("Connection:", self.connection_info_label)

        self.key_type_label = QLabel("")
        self._layout.addRow("Key Type:", self.key_type_label)

        self.session_name_label = QLabel("")
        self._layout.addRow("Session Name:", self.session_name_label)

        self.certificate_label = QLabel("")
        self.certificate_label.setStyleSheet(
            "QLabel { color: #28a745; font-weight: bold; }"
        )
        self._layout.addRow("Certificate (Optional):", self.certificate_label)

        self.key_prov_status_label = QLabel("Not Started")
        self.key_prov_status_label.setStyleSheet("color: #FF9800; font-weight: bold;")
        self._layout.addRow("Key Provisioning:", self.key_prov_status_label)

        self.code_prov_status_label = QLabel("Not Started")
        self.code_prov_status_label.setStyleSheet("color: #FF9800; font-weight: bold;")
        self._layout.addRow("Code Provisioning:", self.code_prov_status_label)

        self._group.setLayout(self._layout)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self._group)

    # ------------------------------------------------------------------
    # Primary updater — replaces the label block in set_session_info
    # ------------------------------------------------------------------

    def update(self, session_data: dict, prov_spec: dict, key_options: list) -> None:
        """Set all session labels and configure the details panel state list.

        Args:
            session_data: The session dict passed to ProvisioningPage.set_session_info.
            prov_spec:    Result of get_provisioning_spec_for_device().
            key_options:  Result of get_key_options_for_device().
        """
        device          = session_data.get('device', '')
        device_state    = session_data.get('device_state', '')
        boot_mode       = session_data.get('boot_mode', '')
        connection_info = session_data.get('connection_info', {})
        key_type        = session_data.get('key_type', '')
        key_data        = session_data.get('key_data', {})
        certificate_info = session_data.get('certificate_info', {})

        self.device_label.setText(device)
        self.device_state_label.setText(device_state)
        self.boot_mode_label.setText(boot_mode)

        # Connection string
        connection_text = ""
        if connection_info:
            if connection_info.get('type') == 'uart':
                connection_text = f"UART: {connection_info.get('port', '')}"
            elif connection_info.get('type') == 'jtag':
                connection_text = f"JTAG: {connection_info.get('ccs_path', '')}"
        self.connection_info_label.setText(connection_text)

        # Key type display
        key_type_display = {opt["key_type"]: opt["label"] for opt in key_options}
        key_type_display.setdefault("new",      "New Keys")
        key_type_display.setdefault("existing", "Existing Keys")
        key_type_display.setdefault("sdk",      "SDK Dummy Keys")
        key_type_display.setdefault("pkcs11",   "PKCS#11 Smart Card")
        self.key_type_label.setText(key_type_display.get(key_type, "Unknown"))

        # Session name
        if key_data and "name" in key_data:
            self.session_name_label.setText(key_data["name"])
        else:
            self.session_name_label.setText("")

        # Certificate status
        if certificate_info:
            self.certificate_label.setText("Generated ✓")
            self.certificate_label.setStyleSheet(
                "QLabel { color: #28a745; font-weight: bold; }"
            )
        else:
            self.certificate_label.setText("Not Generated (Optional)")
            self.certificate_label.setStyleSheet("color: #ff9800; font-weight: bold;")

        # Configure the state indicator and details panel
        self.state_indicator.set_states(
            prov_spec.get("device_states", []),
            prov_spec.get("device_state_labels", {}),
        )
        self._details_panel.configure_states(
            prov_spec.get("device_states", []),
            prov_spec.get("device_state_labels", {}),
        )

    # ------------------------------------------------------------------
    # Fine-grained setters (called from result handlers)
    # ------------------------------------------------------------------

    def set_key_prov_status(self, text: str, style: str) -> None:
        self.key_prov_status_label.setText(text)
        self.key_prov_status_label.setStyleSheet(style)

    def set_code_prov_status(self, text: str, style: str) -> None:
        self.code_prov_status_label.setText(text)
        self.code_prov_status_label.setStyleSheet(style)

    def set_device_state(self, state_text: str, indicator_state) -> None:
        """Update the device state label, indicator, and details panel current state.

        Args:
            state_text:      Text to show in the Device State label.
            indicator_state: State key for DeviceStateIndicator and
                             ProvisioningDetailsPanel; pass None to clear.
        """
        self.device_state_label.setText(state_text or "")
        self.state_indicator.set_current_state(indicator_state or None)
        self._details_panel.set_current_state(indicator_state or None)

    # ------------------------------------------------------------------
    # Lazy summary rows (called from update_session_info_from_logs)
    # ------------------------------------------------------------------

    def add_provisioning_summary(self, log_data: dict) -> None:
        """Lazily add the provisioning summary label (idempotent).

        Exposes the label as self.provisioning_summary_label after the first call.
        """
        if hasattr(self, 'provisioning_summary_label'):
            return
        self.provisioning_summary_label = QLabel("")
        self.provisioning_summary_label.setStyleSheet("""
            QLabel {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 8px;
                color: #28a745;
            }
        """)
        self.provisioning_summary_label.setWordWrap(True)
        self._layout.addRow("Provisioning Details:", self.provisioning_summary_label)

    def add_seccfg_status(self) -> QLabel:
        """Lazily add the SecCfg status label and return it (idempotent)."""
        if hasattr(self, '_seccfg_label'):
            return self._seccfg_label
        self._seccfg_label = QLabel("")
        self._seccfg_label.setStyleSheet("color: #28a745; font-weight: bold;")
        self._layout.addRow("SecCfg Status:", self._seccfg_label)
        return self._seccfg_label
