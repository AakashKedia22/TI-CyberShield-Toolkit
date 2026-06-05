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

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt, pyqtSignal


class ProvisioningProgressDialog(QDialog):
    """Generic streaming provisioning progress dialog.

    Driven by stage definitions supplied by the active tab via
    get_task_meta()["progress_stages"].  Each entry is a dict:

        {
            "trigger":      str,   # substring to match in streaming output
            "status_text":  str,   # text for the upper (bold) status label
            "overall_text": str,   # text for the lower (centred) overall label
            "final":        bool,  # optional; applies green style when True
        }

    If progress_stages is empty the dialog shows a plain "Waiting to start…"
    indicator and update_from_output() is a no-op.
    """

    cancel_requested = pyqtSignal()

    def __init__(self, prov_type: str, boot_mode: str,
                 progress_stages: list, parent=None):
        super().__init__(parent)
        self._stages = progress_stages

        self.setWindowTitle("Provisioning")
        self.setMinimumWidth(500)
        self.setMinimumHeight(300)

        layout = QVBoxLayout(self)

        self.progress_status_label = QLabel(
            f"Initializing {prov_type} provisioning via {boot_mode}..."
        )
        self.progress_status_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.progress_status_label)

        self.overall_status_label = QLabel("Waiting to start...")
        self.overall_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.overall_status_label)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.cancel_requested.emit)
        layout.addWidget(cancel_btn, alignment=Qt.AlignmentFlag.AlignCenter)

    def update_from_output(self, output: str) -> None:
        """Apply stage triggers and update labels.

        Iterates progress_stages in order; the first matching trigger wins.
        Replaces ProvisioningPage._update_progress_from_output.
        """
        if not output or not self._stages:
            return

        for stage in self._stages:
            trigger = stage.get("trigger", "")
            if trigger and trigger in output:
                self.progress_status_label.setText(stage.get("status_text", ""))
                overall = stage.get("overall_text", "")
                self.overall_status_label.setText(overall)
                if stage.get("final"):
                    self.overall_status_label.setStyleSheet(
                        "color: #28a745; font-weight: bold;"
                    )
                break
