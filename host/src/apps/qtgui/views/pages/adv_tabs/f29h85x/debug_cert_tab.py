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

from pathlib import Path

from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFormLayout,
    QComboBox, QLineEdit,
    QMessageBox, QProgressDialog,
)
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QFileDialog

from apps.qtgui.views.pages.adv_tabs.base import AdvancedTabBase


class DebugCertTab(AdvancedTabBase):
    """Debug Authentication Certificate tab."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._key_type = None
        self._key_data = {}
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        layout.addWidget(self._make_desc_label(
            "Generate a Debug Authentication certificate to enable debugging features."
            " This certificate requires specific device information."
        ))

        form = QFormLayout()
        form.setSpacing(15)
        form.setLabelAlignment(Qt.AlignLeft)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        self.keyrev_combo = QComboBox()
        self.keyrev_combo.addItems(["Use SMPK (1)", "Use BMPK (2)"])
        self.keyrev_combo.setStyleSheet(self.INPUT_STYLE)
        form.addRow("<b>Key Revision:</b>", self.keyrev_combo)

        self.swrv_input = self._make_lineedit()
        self.swrv_input.setText("1")
        form.addRow("<b>Software Revision:</b>", self.swrv_input)

        self.debug_type_combo = QComboBox()
        self.debug_type_combo.addItems(["DBG_PUBLIC_ENABLE (2)", "DBG_SOC_DEFAULT (1)", "DBG_PERM_DISABLE (0)" , "DBG_FULL_ENABLE (4)"])
        self.debug_type_combo.setCurrentIndex(0)
        self.debug_type_combo.setStyleSheet(self.INPUT_STYLE)
        self.debug_type_combo.setItemData(0, "C29x core open for debug", Qt.ToolTipRole)
        self.debug_type_combo.setItemData(1, "Maintain debug ports to device type defaults", Qt.ToolTipRole)
        self.debug_type_combo.setItemData(2, "Disable debug ports for all cores", Qt.ToolTipRole)
        self.debug_type_combo.setItemData(3, "C29x and HSM core open for debug", Qt.ToolTipRole) 
        form.addRow("<b>Debug Type:</b>", self.debug_type_combo)

        self.uid_input = self._make_lineedit("Enter 64-byte hexadecimal Device UID")
        self.uid_input.setToolTip(
            "You can get device UID by checking logs of UART Flow (11 - Get SoC ID Info)"
        )
        form.addRow("<b>Device UID:</b>", self.uid_input)

        out_row = QHBoxLayout()
        out_row.setSpacing(10)
        self.output_folder_edit = self._make_lineedit()
        browse_btn = self._make_browse_btn()
        browse_btn.clicked.connect(self._browse_output)
        out_row.addWidget(self.output_folder_edit)
        out_row.addWidget(browse_btn)
        form.addRow("<b>Output Folder:</b>", out_row)

        layout.addLayout(form)

        self.generate_btn = self._make_action_btn("Generate Debug Certificate")
        self.generate_btn.clicked.connect(self._on_generate)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(self.generate_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    # --- Interface implementation ---

    def set_model(self, model, key_type: str, key_data: dict, device: str = "") -> None:
        self._key_type = key_type
        self._key_data = key_data or {}

    def set_output_path(self, path) -> None:
        if not self.output_folder_edit.text():
            self.output_folder_edit.setText(str(path))

    # --- Slots ---

    def _browse_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Debug Certificate Output Directory")
        if folder:
            self.output_folder_edit.setText(folder)

    def _on_generate(self):
        session_name = self._key_data.get("name", "")
        session_password = self._key_data.get("password", "")

        if not self.output_folder_edit.text():
            QMessageBox.warning(self.window(), "Error", "Please select an output folder for Debug certificate")
            return

        debug_uid = self.uid_input.text().strip()
        if debug_uid.lower().startswith("0x"):
            debug_uid = debug_uid[2:]
        if not debug_uid:
            QMessageBox.warning(self.window(), "Error", "Please enter a Device UID")
            return

        try:
            int(debug_uid, 16)
        except ValueError:
            QMessageBox.warning(self.window(), "Error", "Device UID must contain only hexadecimal characters (0-9, a-f)")
            return

        if len(debug_uid) != 128:
            QMessageBox.warning(
                self.window(), "Error",
                f"Device UID must be exactly 64 bytes (128 hex characters).\n"
                f"You entered {len(debug_uid)} hex character(s)."
            )
            return

        keyrev_text = self.keyrev_combo.currentText()
        if "1" in keyrev_text:
            keyrev = "1"
        elif "2" in keyrev_text:
            keyrev = "2"
        else:
            keyrev = "1"

        swrv = self.swrv_input.text()
        debug_type = self.debug_type_combo.currentText().split("(")[-1].rstrip(")")

        confirm = QMessageBox.question(
            self.window(),
            "Confirm Debug Certificate Generation",
            f"This will generate a Debug certificate using session '{session_name}' and save it to"
            f" {self.output_folder_edit.text()}. Continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if confirm == QMessageBox.No:
            return

        progress = QProgressDialog("Generating Debug certificate...", "Cancel", 0, 100, self.window())
        progress.setWindowTitle("Please Wait")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(10)
        QApplication.processEvents()

        try:
            from apps.qtgui.models.F29H85xDeviceModel import F29H85xDeviceModel

            model = F29H85xDeviceModel()

            if self._key_type == "f29_development":
                model.development_session_checkbox = True
                model.sessionName = "Development"
                model.sessionPassword = "develop123#"
                model.smpk = self._key_data.get("smpk_algo", "rsa4k")
                model.bmpk = self._key_data.get("bmpk_algo", "rsa4k")
            else:
                model.development_session_checkbox = False
                model.sessionName = session_name
                model.sessionPassword = session_password

            progress.setValue(30)
            QApplication.processEvents()

            success, message = model.gen_debug_cert(
                keyrev=keyrev,
                swrv=swrv,
                dev_uid=debug_uid,
                dev_dbg_type=debug_type,
                output_path=Path(self.output_folder_edit.text()),
            )

            progress.setValue(100)
            progress.close()

            if success:
                self.generate_btn.setText("Debug Certificate Generated ✓")
                self.generate_btn.setStyleSheet(self.SUCCESS_BTN_STYLE)
                self.completed.emit(
                    True,
                    f"Debug certificate has been generated and saved to"
                    f" {self.output_folder_edit.text()}/debug_auth.cert",
                )
            else:
                self.completed.emit(False, f"Failed to generate Debug certificate.\n\nError: {message}")

        except Exception as e:
            progress.close()
            print(f"Exception in debug certificate generation: {str(e)}")
            self.completed.emit(False, f"Error generating Debug certificate: {str(e)}")
