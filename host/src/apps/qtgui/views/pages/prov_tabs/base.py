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
import serial.tools.list_ports

from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QCheckBox,
    QGroupBox, QFileDialog,
)
from PyQt5.QtCore import pyqtSignal

from apps.qtgui.utils.platform_utils import format_serial_port_name


class ProvisioningTabBase(QWidget):
    """Base class for device-specific provisioning tab widgets.

    Subclasses implement the four required methods and emit provision_clicked
    from their own Provision button.  provisioning_page.py connects that signal
    to on_provision_clicked(prov_type, boot_mode) and calls validate(),
    collect_params(), get_task_meta() before dispatching to the backend.
    """

    provision_clicked = pyqtSignal()   # tab's own Provision button emits this

    # --- Required interface (subclasses must implement) ---

    def set_session_info(self, session_data: dict) -> None:
        raise NotImplementedError

    def validate(self) -> tuple:
        raise NotImplementedError   # returns (bool, str)

    def collect_params(self) -> dict:
        raise NotImplementedError

    def get_task_meta(self) -> dict:
        raise NotImplementedError
        # must return {"task_key": str, "stream": bool, "requires_reset_before": bool}

    # --- Optional hook ---

    def on_provision_result(self, success: bool) -> None:
        """Called after provisioning completes; tab may update its button here."""
        pass

    # --- Style constants (compact rows matching provisioning_page) ---

    COMPACT_INPUT_STYLE = "font-size: 10px; height: 18px;"
    COMPACT_LABEL_STYLE = "font-size: 10px;"
    COMPACT_BTN_STYLE   = "font-size: 10px; height: 18px;"

    PROVISION_BTN_STYLE = """
        QPushButton {
            background-color: #CC0000; color: white;
            padding: 6px 15px; border: none; border-radius: 3px; min-width: 160px;
        }
        QPushButton:hover { background-color: #990000; }
        QPushButton:disabled { background-color: #cccccc; color: #666666; }
    """

    SUCCESS_BTN_STYLE = """
        QPushButton {
            background-color: #28a745; color: white;
            padding: 8px 20px; border: none; border-radius: 4px; min-width: 180px;
        }
        QPushButton:hover { background-color: #218838; }
    """

    _ADV_HDR_COLLAPSED = """
        QPushButton {
            text-align: left; padding: 5px 8px; font-weight: bold; font-size: 11px;
            background-color: #CC0000; color: white; border: 1px solid #990000; border-radius: 4px;
        }
        QPushButton:hover { background-color: #990000; }
    """

    _ADV_HDR_EXPANDED = """
        QPushButton {
            text-align: left; padding: 5px 8px; font-weight: bold; font-size: 11px;
            background-color: #CC0000; color: white; border: 1px solid #990000;
            border-radius: 4px 4px 0 0; border-bottom: none;
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

    # --- Shared row helpers ---

    def _make_file_row(self, label: str) -> tuple:
        """Return (row_widget, line_edit, browse_btn) — compact file-browse row."""
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        lbl = QLabel(f"{label}:")
        lbl.setStyleSheet(self.COMPACT_LABEL_STYLE)
        layout.addWidget(lbl)
        edit = QLineEdit()
        edit.setStyleSheet(self.COMPACT_INPUT_STYLE)
        layout.addWidget(edit)
        btn = QPushButton("Browse")
        btn.setStyleSheet(self.COMPACT_BTN_STYLE)
        btn.clicked.connect(lambda _checked, e=edit, t=label: self._browse_file(e, t))
        layout.addWidget(btn)
        return row, edit, btn

    def _make_dir_row(self, label: str) -> tuple:
        """Return (row_widget, line_edit, browse_btn) — compact dir-browse row."""
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        lbl = QLabel(f"{label}:")
        lbl.setStyleSheet(self.COMPACT_LABEL_STYLE)
        layout.addWidget(lbl)
        edit = QLineEdit()
        edit.setStyleSheet(self.COMPACT_INPUT_STYLE)
        layout.addWidget(edit)
        btn = QPushButton("Browse")
        btn.setStyleSheet(self.COMPACT_BTN_STYLE)
        btn.clicked.connect(lambda _checked, e=edit, t=label: self._browse_dir(e, t))
        layout.addWidget(btn)
        return row, edit, btn

    def _make_serial_row(self, label: str) -> tuple:
        """Return (row_widget, combo, refresh_btn) — compact serial-port row."""
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        lbl = QLabel(f"{label}:")
        lbl.setStyleSheet(self.COMPACT_LABEL_STYLE)
        layout.addWidget(lbl)
        combo = QComboBox()
        combo.setStyleSheet(self.COMPACT_INPUT_STYLE)
        layout.addWidget(combo)
        btn = QPushButton("Refresh")
        btn.setStyleSheet(self.COMPACT_BTN_STYLE)
        btn.clicked.connect(lambda _checked, c=combo: self._populate_serial_ports(c))
        layout.addWidget(btn)
        self._populate_serial_ports(combo)
        return row, combo, btn

    def _make_optional_file_row(self, label: str) -> tuple:
        """Return (row_widget, checkbox, line_edit, browse_btn, mandatory_label)."""
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        check = QCheckBox("")
        check.setChecked(False)
        check.setToolTip(f"Include {label}")
        layout.addWidget(check)
        lbl = QLabel(f"{label}:")
        layout.addWidget(lbl)
        edit = QLineEdit()
        layout.addWidget(edit)
        btn = QPushButton("Browse")
        btn.setStyleSheet(
            "background-color: #CC0000; color: white; padding: 4px 8px;"
            " border: none; border-radius: 3px;"
        )
        btn.clicked.connect(lambda _checked, e=edit, t=label: self._browse_file(e, t))
        layout.addWidget(btn)
        mandatory_lbl = QLabel("(Mandatory)")
        mandatory_lbl.setStyleSheet("color: #CC0000; font-size: 10px;")
        mandatory_lbl.setVisible(False)
        layout.addWidget(mandatory_lbl)
        return row, check, edit, btn, mandatory_lbl

    def _make_adv_section(self) -> tuple:
        """Return (adv_container, adv_group, adv_layout, header_btn).

        Builds a collapsed '▶ Advanced Settings' section; toggle is wired internally.
        Add field rows to adv_layout, then add adv_container to the tab's main layout.
        """
        adv_container = QWidget()
        container_layout = QVBoxLayout(adv_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        header_btn = QPushButton("▶ Advanced Settings")
        header_btn.setStyleSheet(self._ADV_HDR_COLLAPSED)
        container_layout.addWidget(header_btn)

        adv_group = QGroupBox()
        adv_group.setStyleSheet(self._ADV_GRP_STYLE)
        adv_group.setVisible(False)
        adv_layout = QVBoxLayout(adv_group)
        adv_layout.setContentsMargins(5, 5, 5, 5)
        adv_layout.setSpacing(2)
        container_layout.addWidget(adv_group)

        header_btn.clicked.connect(
            lambda _checked, g=adv_group, h=header_btn: self._toggle_adv(g, h)
        )
        return adv_container, adv_group, adv_layout, header_btn

    def _toggle_adv(self, group: QGroupBox, header: QPushButton) -> None:
        visible = group.isVisible()
        group.setVisible(not visible)
        if not visible:
            header.setText("▼ Advanced Settings")
            header.setStyleSheet(self._ADV_HDR_EXPANDED)
        else:
            header.setText("▶ Advanced Settings")
            header.setStyleSheet(self._ADV_HDR_COLLAPSED)

    def _populate_serial_ports(self, combo: QComboBox) -> None:
        """Populate a QComboBox with all available serial ports."""
        combo.clear()
        ports = serial.tools.list_ports.comports()
        if ports:
            for port in ports:
                combo.addItem(format_serial_port_name(port.device))
        else:
            combo.addItem("No ports found")

    # --- Internal browse helpers ---

    def _browse_file(self, edit: QLineEdit, label: str) -> None:
        path, _ = QFileDialog.getOpenFileName(self, f"Select {label}")
        if path:
            edit.setText(path)

    def _browse_dir(self, edit: QLineEdit, label: str) -> None:
        path = QFileDialog.getExistingDirectory(self, f"Select {label}")
        if path:
            edit.setText(path)
