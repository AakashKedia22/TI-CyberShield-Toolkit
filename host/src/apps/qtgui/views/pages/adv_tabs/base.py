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

from PyQt5.QtWidgets import QWidget, QLineEdit, QPushButton, QLabel
from PyQt5.QtCore import pyqtSignal


class AdvancedTabBase(QWidget):
    """Base class for all advanced tab widgets."""

    completed = pyqtSignal(bool, str)   # (success, message)

    # --- Interface (subclasses implement) ---

    def set_model(self, model, key_type: str, key_data: dict, device: str = "") -> None:
        raise NotImplementedError

    def set_output_path(self, path) -> None:
        raise NotImplementedError

    # --- Optional hooks (subclasses may override) ---

    def set_ccs_path(self, path: str) -> None:
        pass

    def set_prebuilt_dir(self, path) -> None:
        """Receives prebuilt_images_dir (a Path) for default enc-key / kd-salt paths."""
        pass

    # --- Shared style constants ---

    INPUT_STYLE = """
        QLineEdit, QComboBox {
            padding: 8px; border: 1px solid #cccccc; border-radius: 4px; min-width: 150px;
        }
        QLineEdit:focus, QComboBox:focus { border: 1px solid #CC0000; }
        QComboBox::drop-down {
            subcontrol-origin: padding; subcontrol-position: center right;
            width: 20px; border-left: none;
        }
    """

    BROWSE_STYLE = (
        "QPushButton { background-color: #CC0000; color: white; padding: 8px 15px; "
        "border: none; border-radius: 4px; } "
        "QPushButton:hover { background-color: #990000; }"
    )

    ACTION_BTN_STYLE = """
        QPushButton {
            background-color: #CC0000; color: white; padding: 10px 20px;
            border: none; border-radius: 4px; font-weight: bold;
            min-width: 220px; margin-top: 10px;
        }
        QPushButton:hover { background-color: #bb0000; }
        QPushButton:pressed { background-color: #990000; }
        QPushButton:disabled { background-color: #cccccc; color: #666666; }
    """

    SUCCESS_BTN_STYLE = """
        QPushButton {
            background-color: #28a745; color: white; padding: 10px 20px;
            border: none; border-radius: 4px; font-weight: bold;
            min-width: 220px; margin-top: 10px;
        }
        QPushButton:hover { background-color: #218838; }
    """

    # --- Shared style helpers ---

    @staticmethod
    def _make_lineedit(placeholder: str = "") -> QLineEdit:
        w = QLineEdit()
        w.setStyleSheet(AdvancedTabBase.INPUT_STYLE)
        if placeholder:
            w.setPlaceholderText(placeholder)
        return w

    @staticmethod
    def _make_browse_btn(label: str = "Browse") -> QPushButton:
        btn = QPushButton(label)
        btn.setStyleSheet(AdvancedTabBase.BROWSE_STYLE)
        return btn

    @staticmethod
    def _make_action_btn(label: str) -> QPushButton:
        btn = QPushButton(label)
        btn.setStyleSheet(AdvancedTabBase.ACTION_BTN_STYLE)
        return btn

    @staticmethod
    def _make_desc_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setStyleSheet("font-size: 12px; color: #555555; padding-bottom: 10px;")
        return lbl
