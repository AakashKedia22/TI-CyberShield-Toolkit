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

from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QPushButton

from apps.qtgui.views.pages.prov_tabs.base import ProvisioningTabBase
from common.device_utils import get_device_prebuilt_dir, get_device_output_dir, infer_device_family
from common.platform_utils import get_addon_root


class F29KeyJTAGTab(ProvisioningTabBase):
    """F29H85x key provisioning via JTAG."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._session_data = {}
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(3)

        # All fields live in the Advanced section
        adv_container, _adv_group, adv_layout, _hdr = self._make_adv_section()

        ccs_row, self._ccs_edit, _btn = self._make_dir_row("CCS Path")
        adv_layout.addWidget(ccs_row)

        kernel_row, self._kernel_edit, _btn = self._make_file_row("Flash Kernel")
        adv_layout.addWidget(kernel_row)

        otp_row, self._otp_edit, _btn = self._make_file_row("OTP Keywriter Binary")
        adv_layout.addWidget(otp_row)

        cert_row, self._cert_edit, _btn = self._make_file_row("Certificate")
        adv_layout.addWidget(cert_row)

        layout.addWidget(adv_container)

        self._prov_btn = QPushButton("Provision Keys (JTAG)")
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

        device_family = infer_device_family(device_name)

        conn = session_data.get('connection_info', {})
        if not self._ccs_edit.text() and conn.get('type') == 'jtag':
            ccs = conn.get('ccs_path', '')
            if ccs:
                self._ccs_edit.setText(ccs)

        if not self._kernel_edit.text():
            try:
                prebuilt = get_device_prebuilt_dir(device_name, device_family)
                self._kernel_edit.setText(
                    os.path.join(prebuilt, "secure_ram_based_jtag_kernel.out")
                )
            except Exception:
                pass

        if not self._otp_edit.text():
            try:
                addon_bin = get_addon_root(device_name) / "bin"
                self._otp_edit.setText(
                    str(addon_bin / f"otp_kw_{device_name}_hs_fs.hsmimage.bin")
                )
            except Exception:
                pass

        if not self._cert_edit.text():
            try:
                cert_info = session_data.get('certificate_info', {})
                if cert_info and 'output_dir_path' in cert_info:
                    cert_path = os.path.join(cert_info['output_dir_path'], "final_certificate.bin")
                else:
                    cert_dir = get_device_output_dir(device_name, "certificates")
                    cert_path = os.path.join(cert_dir, "final_certificate.bin")
                    os.makedirs(os.path.dirname(cert_path), exist_ok=True)
                self._cert_edit.setText(cert_path)
            except Exception:
                pass

    def validate(self) -> tuple:
        ccs = self._ccs_edit.text().strip()
        if not ccs:
            return False, "Please provide CCS Path"
        if not os.path.isdir(ccs):
            return False, f"CCS Path does not exist: {ccs}"
        kernel = self._kernel_edit.text().strip()
        if not kernel:
            return False, "Please provide Flash Kernel path"
        if not os.path.exists(kernel):
            return False, f"Flash Kernel not found: {kernel}"
        otp = self._otp_edit.text().strip()
        if not otp:
            return False, "Please provide OTP Keywriter Binary path"
        if not os.path.exists(otp):
            return False, f"OTP Keywriter Binary not found: {otp}"
        cert = self._cert_edit.text().strip()
        if not cert:
            return False, "Please provide Certificate path"
        if not os.path.exists(cert):
            return False, f"Certificate not found: {cert}"
        return True, ""

    def collect_params(self) -> dict:
        return {
            "ccs_path":    self._ccs_edit.text().strip(),
            "jtag_kernel": self._kernel_edit.text().strip(),
            "otp_kw_bin":  self._otp_edit.text().strip(),
            "certificate": self._cert_edit.text().strip(),
        }

    def get_task_meta(self) -> dict:
        return {
            "task_key":              "jtag_keyprov",
            "stream":                False,
            "requires_reset_before": False,
        }

    def on_provision_result(self, success: bool) -> None:
        if success:
            self._prov_btn.setText("Keys Provisioned ✓")
            self._prov_btn.setStyleSheet(self.SUCCESS_BTN_STYLE)
        else:
            self._prov_btn.setText("Provision Keys (JTAG)")
            self._prov_btn.setStyleSheet(self.PROVISION_BTN_STYLE)
