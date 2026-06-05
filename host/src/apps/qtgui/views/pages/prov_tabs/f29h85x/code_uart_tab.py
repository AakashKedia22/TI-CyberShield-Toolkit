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

from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit, QWidget,
)

from apps.qtgui.views.pages.prov_tabs.base import ProvisioningTabBase
from common.device_utils import get_device_output_dir


class F29CodeUARTTab(ProvisioningTabBase):
    """F29H85x code provisioning via UART."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._session_data = {}
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(3)

        # --- Advanced section (Serial Port + Flash Kernel) ---
        adv_container, _adv_group, adv_layout, _hdr = self._make_adv_section()

        port_row, self._port_combo, _btn = self._make_serial_row("Serial Port")
        adv_layout.addWidget(port_row)

        kernel_row, self._kernel_edit, _btn = self._make_file_row("Flash Kernel")
        adv_layout.addWidget(kernel_row)

        layout.addWidget(adv_container)

        # --- Main fields ---
        # HSM CP Image (required — no checkbox)
        hsm_cp_row = QWidget()
        hsm_cp_layout = QHBoxLayout(hsm_cp_row)
        hsm_cp_layout.setContentsMargins(0, 0, 0, 0)
        hsm_cp_layout.setSpacing(4)
        hsm_cp_layout.addWidget(QLabel("HSM CP Image:"))
        self._hsm_cp_edit = QLineEdit()
        hsm_cp_layout.addWidget(self._hsm_cp_edit)
        hsm_cp_btn = QPushButton("Browse")
        hsm_cp_btn.setStyleSheet(
            "background-color: #CC0000; color: white; padding: 4px 8px;"
            " border: none; border-radius: 3px;"
        )
        hsm_cp_btn.clicked.connect(
            lambda: self._browse_file(self._hsm_cp_edit, "HSM CP Image")
        )
        hsm_cp_layout.addWidget(hsm_cp_btn)
        layout.addWidget(hsm_cp_row)

        # Optional fields: (check_attr, edit_attr, label)
        _opt = [
            ("_hsm_cpu_check", "_hsm_cpu_edit", "HSM CPU Code"),
            ("_c29_cpu_check",  "_c29_cpu_edit",  "C29 CPU Code"),
            ("_c29_cpu3_check", "_c29_cpu3_edit", "C29 CPU1/3 Image"),
            ("_seccfg_check",   "_seccfg_edit",   "Security Config"),
        ]
        self._seccfg_mandatory_lbl = None
        for check_attr, edit_attr, label in _opt:
            row, check, edit, _btn2, mand_lbl = self._make_optional_file_row(label)
            setattr(self, check_attr, check)
            setattr(self, edit_attr, edit)
            if label == "Security Config":
                self._seccfg_mandatory_lbl = mand_lbl
            layout.addWidget(row)

        # --- Provision button ---
        self._prov_btn = QPushButton("Provision Code (UART)")
        self._prov_btn.setStyleSheet(self.PROVISION_BTN_STYLE)
        self._prov_btn.clicked.connect(self.provision_clicked.emit)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(self._prov_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)
        layout.addStretch(1)

    # --- Required interface ---

    def set_session_info(self, session_data: dict) -> None:
        self._session_data = session_data
        device = session_data.get('device', '')
        device_name = device.lower() if device else None
        if not device_name:
            return

        signed_images = get_device_output_dir(device_name, "signedImages")

        # Advanced: Flash kernel
        if not self._kernel_edit.text():
            try:
                os.makedirs(signed_images, exist_ok=True)
                self._kernel_edit.setText(
                    os.path.join(signed_images, "ram_based_uart_sbl.cert.bin")
                )
            except Exception:
                pass

        # Advanced: Serial port
        conn = session_data.get('connection_info', {})
        if conn.get('type') == 'uart' and 'port' in conn:
            idx = self._port_combo.findText(conn['port'])
            if idx >= 0:
                self._port_combo.setCurrentIndex(idx)

        # Main field defaults
        try:
            if not self._hsm_cp_edit.text():
                self._hsm_cp_edit.setText(os.path.join(
                    signed_images,
                    f"tifs_{device_name}_hs_se_code_provisioning.release.hs.hsmimage",
                ))

            if not self._hsm_cpu_edit.text():
                self._hsm_cpu_edit.setText(os.path.join(
                    signed_images, f"tifs_{device_name}_hs_se.release.hs.hsmimage"
                ))

            if not self._c29_cpu_edit.text():
                self._c29_cpu_edit.setText(os.path.join(
                    signed_images, "secure_boot_manager.cert.bin"
                ))

            if not self._c29_cpu3_edit.text():
                self._c29_cpu3_edit.setText(os.path.join(
                    signed_images, "combined_services_demo.cert.bin"
                ))

            if not self._seccfg_edit.text():
                self._seccfg_edit.setText(os.path.join(signed_images, "seccfg.bin"))

        except Exception:
            pass

        # Auto-check + lock Security Config when device is in HSKP state
        device_state = session_data.get('device_state', '').strip().upper()
        if device_state == "HSKP":
            self._seccfg_check.setChecked(True)
            self._seccfg_check.setEnabled(False)
            if self._seccfg_mandatory_lbl:
                self._seccfg_mandatory_lbl.setVisible(True)
        else:
            self._seccfg_check.setEnabled(True)
            if self._seccfg_mandatory_lbl:
                self._seccfg_mandatory_lbl.setVisible(False)

    def validate(self) -> tuple:
        hsm_cp = self._hsm_cp_edit.text().strip()
        if not hsm_cp:
            return False, "Please provide HSM CP Image path"
        if not os.path.exists(hsm_cp):
            return False, f"HSM CP Image not found: {hsm_cp}"

        for check_attr, edit_attr, label in [
            ("_hsm_cpu_check", "_hsm_cpu_edit", "HSM CPU Code"),
            ("_c29_cpu_check",  "_c29_cpu_edit",  "C29 CPU Code"),
            ("_c29_cpu3_check", "_c29_cpu3_edit", "C29 CPU1/3 Image"),
            ("_seccfg_check",   "_seccfg_edit",   "Security Config"),
        ]:
            if getattr(self, check_attr).isChecked():
                val = getattr(self, edit_attr).text().strip()
                if not val:
                    return False, f"Please provide {label} path"
                if not os.path.exists(val):
                    return False, f"{label} not found: {val}"

        if not self._get_input_parameter():
            return False, "Please select at least one component to provision"

        return True, ""

    def _get_input_parameter(self) -> str:
        """Return comma-joined parameter IDs for checked/required fields."""
        pids = ["3"]   # HSM CP Image always included (required)
        for check_attr, pid in [
            ("_hsm_cpu_check", "6"),
            ("_c29_cpu_check",  "7"),
            ("_c29_cpu3_check", "8"),
            ("_seccfg_check",   "5"),
        ]:
            if getattr(self, check_attr).isChecked():
                pids.append(pid)
        return ",".join(pids)

    def collect_params(self) -> dict:
        params: dict = {
            "port":            self._port_combo.currentText(),
            "uart_kernel":     self._kernel_edit.text().strip(),
            "hsm_image":       self._hsm_cp_edit.text().strip(),
            "input_parameter": self._get_input_parameter(),
        }
        if self._hsm_cpu_check.isChecked():
            params["hsm_cpu_code"] = self._hsm_cpu_edit.text().strip()
        if self._c29_cpu_check.isChecked():
            params["c29_cpu_code"] = self._c29_cpu_edit.text().strip()
        if self._c29_cpu3_check.isChecked():
            params["c29_cpu3_code"] = self._c29_cpu3_edit.text().strip()
        if self._seccfg_check.isChecked():
            params["seccfg"] = self._seccfg_edit.text().strip()
        return params

    def get_task_meta(self) -> dict:
        return {
            "task_key":              "uart_codeprov",
            "stream":                True,
            "requires_reset_before": True,
            "progress_stages": [
                {
                    "trigger":      "!! HSM Run Time Loading is successful !!",
                    "status_text":  "HSM Run Time Loading completed successfully",
                    "overall_text": "Proceeding to HSM Code Provisioning...",
                },
                {
                    "trigger":      "!! HSM Run Time Code Provisioning is successful !!",
                    "status_text":  "HSM Run Time Code Provisioning completed successfully",
                    "overall_text": "Proceeding to C29 CPU Code Provisioning...",
                },
                {
                    "trigger":      "!! C29 CPU1 Code Provisioning is successful !!",
                    "status_text":  "C29 CPU1 Code Provisioning completed successfully",
                    "overall_text": "Code provisioning completed successfully!",
                    "final":        True,
                },
            ],
        }

    def on_provision_result(self, success: bool) -> None:
        if success:
            self._prov_btn.setText("Code Provisioned ✓")
            self._prov_btn.setStyleSheet(self.SUCCESS_BTN_STYLE)
        else:
            self._prov_btn.setText("Provision Code (UART)")
            self._prov_btn.setStyleSheet(self.PROVISION_BTN_STYLE)
