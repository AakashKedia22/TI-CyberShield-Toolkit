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
from pathlib import Path

from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFormLayout,
    QComboBox, QCheckBox,
    QMessageBox, QProgressDialog,
)
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QFileDialog

from apps.qtgui.views.pages.adv_tabs.base import AdvancedTabBase


class CustomSignTab(AdvancedTabBase):
    """Custom Binary Signing tab."""

    BROWSE_DISABLED_STYLE = (
        AdvancedTabBase.BROWSE_STYLE.rstrip()
        + " QPushButton:disabled { background-color: #cccccc; color: #666666; }"
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self._key_type = None
        self._key_data = {}
        self._prebuilt_dir = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        layout.addWidget(self._make_desc_label(
            "Sign any custom binary file with SMPK or BMPK keys."
            " Specify your own configuration parameters for signing."
        ))

        form = QFormLayout()
        form.setSpacing(15)
        form.setLabelAlignment(Qt.AlignLeft)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        bin_row = QHBoxLayout()
        self.binary_path_edit = self._make_lineedit("Path to binary file (.bin)")
        bin_browse = self._make_browse_btn()
        bin_browse.clicked.connect(self._browse_binary)
        bin_row.addWidget(self.binary_path_edit)
        bin_row.addWidget(bin_browse)
        form.addRow("<b>Binary File:</b>", bin_row)

        self.core_combo = QComboBox()
        self.core_combo.addItems(["C29", "HSM"])
        self.core_combo.setStyleSheet(self.INPUT_STYLE)
        form.addRow("<b>Target Core:</b>", self.core_combo)

        self.boot_combo = QComboBox()
        self.boot_combo.addItems(["FLASH", "RAM"])
        self.boot_combo.setStyleSheet(self.INPUT_STYLE)
        form.addRow("<b>Boot Mode:</b>", self.boot_combo)

        self.keyrev_combo = QComboBox()
        self.keyrev_combo.addItems(["Use SMPK (1)", "Use BMPK (2)"])
        self.keyrev_combo.setStyleSheet(self.INPUT_STYLE)
        form.addRow("<b>Key Revision:</b>", self.keyrev_combo)

        self.swrv_input = self._make_lineedit()
        self.swrv_input.setText("1")
        form.addRow("<b>Software Revision:</b>", self.swrv_input)

        self.loadaddr_input = self._make_lineedit()
        self.loadaddr_input.setText("0x10000000")
        form.addRow("<b>Load Address:</b>", self.loadaddr_input)

        self.fw_type_combo = QComboBox()
        self.fw_type_combo.addItems(["None", "CPU1_APP", "CPU3"])
        self.fw_type_combo.setStyleSheet(self.INPUT_STYLE)
        self.fw_type_combo.setItemData(0, "Default - No specific firmware type", Qt.ToolTipRole)
        self.fw_type_combo.setItemData(1, "CPU1 Application firmware", Qt.ToolTipRole)
        self.fw_type_combo.setItemData(2, "CPU3 firmware", Qt.ToolTipRole)
        form.addRow("<b>Firmware Type:</b>", self.fw_type_combo)

        out_row = QHBoxLayout()
        self.output_folder_edit = self._make_lineedit()
        out_browse = self._make_browse_btn()
        out_browse.clicked.connect(self._browse_output)
        out_row.addWidget(self.output_folder_edit)
        out_row.addWidget(out_browse)
        form.addRow("<b>Output Folder:</b>", out_row)

        self.debug_combo = QComboBox()
        self.debug_combo.addItems(["DBG_PERM_DISABLE", "DBG_SOC_DEFAULT", "DBG_PUBLIC_ENABLE"])
        self.debug_combo.setStyleSheet(self.INPUT_STYLE)
        self.debug_combo.setItemData(0, "Disable debug ports for all cores", Qt.ToolTipRole)
        self.debug_combo.setItemData(1, "Maintain debug ports to device type defaults", Qt.ToolTipRole)
        self.debug_combo.setItemData(2, "C29x core open for debug", Qt.ToolTipRole)
        form.addRow("<b>Debug Options:</b>", self.debug_combo)

        self.encrypt_checkbox = QCheckBox("Enable Encryption (AES-256-CBC)")
        self.encrypt_checkbox.setStyleSheet("""
            QCheckBox { font-size: 12px; padding: 5px; }
            QCheckBox::indicator { width: 18px; height: 18px; }
        """)
        self.encrypt_checkbox.setChecked(False)
        self.encrypt_checkbox.stateChanged.connect(self._on_encryption_changed)
        form.addRow("<b>Encryption:</b>", self.encrypt_checkbox)

        enc_row = QHBoxLayout()
        self.enc_key_path_edit = self._make_lineedit("Path to encryption key file (.key)")
        self.enc_key_path_edit.setEnabled(False)
        self.enc_key_browse_btn = self._make_browse_btn()
        self.enc_key_browse_btn.setStyleSheet(self.BROWSE_DISABLED_STYLE)
        self.enc_key_browse_btn.setEnabled(False)
        self.enc_key_browse_btn.clicked.connect(self._browse_enc_key)
        enc_row.addWidget(self.enc_key_path_edit)
        enc_row.addWidget(self.enc_key_browse_btn)
        form.addRow("<b>Encryption Key:</b>", enc_row)

        salt_row = QHBoxLayout()
        self.kd_salt_path_edit = self._make_lineedit("Path to key derivation salt file (.txt)")
        self.kd_salt_path_edit.setEnabled(False)
        self.kd_salt_browse_btn = self._make_browse_btn()
        self.kd_salt_browse_btn.setStyleSheet(self.BROWSE_DISABLED_STYLE)
        self.kd_salt_browse_btn.setEnabled(False)
        self.kd_salt_browse_btn.clicked.connect(self._browse_kd_salt)
        salt_row.addWidget(self.kd_salt_path_edit)
        salt_row.addWidget(self.kd_salt_browse_btn)
        form.addRow("<b>Key Derivation Salt:</b>", salt_row)

        ccs_row = QHBoxLayout()
        self.ccs_path_edit = self._make_lineedit()
        ccs_browse = self._make_browse_btn()
        ccs_browse.clicked.connect(self._browse_ccs)
        ccs_row.addWidget(self.ccs_path_edit)
        ccs_row.addWidget(ccs_browse)
        form.addRow("<b>CCS Path:</b>", ccs_row)

        layout.addLayout(form)

        self.generate_btn = self._make_action_btn("Generate Signed Binary")
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
        # Update load address default based on currently selected core
        if self.core_combo.currentText() == "C29":
            if not self.loadaddr_input.text():
                self.loadaddr_input.setText("0x10000000")
        else:
            if not self.loadaddr_input.text():
                self.loadaddr_input.setText("0x00000000")

    def set_output_path(self, path) -> None:
        if not self.output_folder_edit.text():
            self.output_folder_edit.setText(str(path))

    def set_ccs_path(self, path: str) -> None:
        if path:
            self.ccs_path_edit.setText(path)

    def set_prebuilt_dir(self, path) -> None:
        self._prebuilt_dir = path
        if path:
            enc_key = path / "mcu_custMek.key"
            kd_salt = path / "kd_salt.txt"
            if enc_key.exists() and not self.enc_key_path_edit.text():
                self.enc_key_path_edit.setText(str(enc_key))
            if kd_salt.exists() and not self.kd_salt_path_edit.text():
                self.kd_salt_path_edit.setText(str(kd_salt))

    # --- Slots ---

    def _on_encryption_changed(self):
        enabled = self.encrypt_checkbox.isChecked()
        self.enc_key_path_edit.setEnabled(enabled)
        self.enc_key_browse_btn.setEnabled(enabled)
        self.kd_salt_path_edit.setEnabled(enabled)
        self.kd_salt_browse_btn.setEnabled(enabled)

        if enabled and self._prebuilt_dir:
            enc_key = self._prebuilt_dir / "mcu_custMek.key"
            kd_salt = self._prebuilt_dir / "kd_salt.txt"
            if enc_key.exists():
                self.enc_key_path_edit.setText(str(enc_key))
            if kd_salt.exists():
                self.kd_salt_path_edit.setText(str(kd_salt))

    def _browse_binary(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Binary File to Sign", "",
            "Binary Files (*.bin);;ELF Files (*.out);;All Files (*.*)",
        )
        if file_path:
            self.binary_path_edit.setText(file_path)
            if self.core_combo.currentText() == "C29":
                self.loadaddr_input.setText("0x10000000")
            else:
                self.loadaddr_input.setText("0x00000000")

    def _browse_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if folder:
            self.output_folder_edit.setText(folder)

    def _browse_ccs(self):
        path = QFileDialog.getExistingDirectory(self, "Browse CCS Path")
        if path:
            self.ccs_path_edit.setText(path)

    def _browse_enc_key(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Encryption Key File", "",
            "Key Files (*.key);;All Files (*.*)",
        )
        if file_path:
            self.enc_key_path_edit.setText(file_path)

    def _browse_kd_salt(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Key Derivation Salt File", "",
            "Text Files (*.txt);;All Files (*.*)",
        )
        if file_path:
            self.kd_salt_path_edit.setText(file_path)

    def _on_generate(self):
        session_name = self._key_data.get("name", "")
        session_password = self._key_data.get("password", "")

        if not self.binary_path_edit.text():
            QMessageBox.warning(self.window(), "Error", "Please select a binary file to sign")
            return

        if not self.output_folder_edit.text():
            QMessageBox.warning(self.window(), "Error", "Please specify an output folder")
            return

        binary_path = self.binary_path_edit.text()
        if binary_path.lower().endswith(".out"):
            input_format = "ELF"
            if not self.ccs_path_edit.text():
                QMessageBox.warning(self.window(), "Error", "CCS path is required when signing ELF files")
                return
        else:
            input_format = "BIN"

        debug_option = self.debug_combo.currentText()

        fw_type = self.fw_type_combo.currentText()
        if fw_type == "None":
            fw_type = None

        if self.encrypt_checkbox.isChecked():
            if not self.enc_key_path_edit.text():
                QMessageBox.warning(self.window(), "Error", "Please specify an encryption key file")
                return
            if not self.kd_salt_path_edit.text():
                QMessageBox.warning(self.window(), "Error", "Please specify a key derivation salt file")
                return

        custom_params = {
            "image": binary_path,
            "input_format": input_format,
            "core": self.core_combo.currentText(),
            "boot": self.boot_combo.currentText(),
            "keyrev": self.keyrev_combo.currentText()[-2:-1],
            "swrv": self.swrv_input.text(),
            "loadaddr": self.loadaddr_input.text(),
            "output_path": Path(self.output_folder_edit.text()),
            "debug": debug_option,
            "fw_type": fw_type,
            "ccs_path": self.ccs_path_edit.text() or None,
        }

        if self.encrypt_checkbox.isChecked():
            core = self.core_combo.currentText()
            if core == "HSM":
                custom_params["fw_enc"] = True
                custom_params["fw_enc_key"] = self.enc_key_path_edit.text()
            else:
                custom_params["sbl_enc"] = True
                custom_params["enc_key"] = self.enc_key_path_edit.text()
            custom_params["kd_salt"] = self.kd_salt_path_edit.text()

        confirm = QMessageBox.question(
            self.window(),
            "Confirm Custom Binary Signing",
            f"This will sign '{os.path.basename(binary_path)}' using"
            f" {self.core_combo.currentText()} core configuration with key revision"
            f" {self.keyrev_combo.currentText()}.\n\n"
            f"The signed binary will be saved to {self.output_folder_edit.text()}.\n\nContinue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if confirm == QMessageBox.No:
            return

        progress = QProgressDialog(
            f"Signing binary {os.path.basename(binary_path)}...", "Cancel", 0, 100, self.window()
        )
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

            success, message = model.sign_binary(**custom_params)

            progress.setValue(100)
            progress.close()

            if success:
                self.generate_btn.setText("Binary Signed ✓")
                self.generate_btn.setStyleSheet(self.SUCCESS_BTN_STYLE)
                self.completed.emit(True, f"Binary has been successfully signed.\n\n{message}")
            else:
                self.completed.emit(False, f"Failed to sign binary.\n\nError: {message}")

        except Exception as e:
            progress.close()
            print(f"Exception in custom binary signing: {str(e)}")
            self.completed.emit(False, f"Error signing binary: {str(e)}")
