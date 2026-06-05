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
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QCheckBox,
    QDialogButtonBox,
)
import json


class ChecklistDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Certificate Configuration")
        self.setMinimumSize(600, 300)
        main_layout = QHBoxLayout()

        key_section_layout = QVBoxLayout()
        protection_section_layout = QVBoxLayout()

        key_group = QGroupBox("Key")
        key_group.setLayout(key_section_layout)

        protection_group = QGroupBox("Protection")
        protection_group.setLayout(protection_section_layout)

        self.options_file = "options.txt"
        self.fields = []
        self.field_checkboxes = []
        self.read_checkboxes = []
        self.write_checkboxes = []
        self.load_options()

        for field in self.fields:
            key_layout = QHBoxLayout()
            field_checkbox = QCheckBox(field)
            self.field_checkboxes.append(field_checkbox)

            key_layout.addWidget(field_checkbox)
            key_section_layout.addLayout(key_layout)

            protection_layout = QHBoxLayout()
            read_checkbox = QCheckBox("Read")
            write_checkbox = QCheckBox("Write")
            self.read_checkboxes.append(read_checkbox)
            self.write_checkboxes.append(write_checkbox)

            protection_layout.addWidget(read_checkbox)
            protection_layout.addWidget(write_checkbox)
            protection_section_layout.addLayout(protection_layout)

        main_layout.addWidget(key_group)
        main_layout.addWidget(protection_group)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Close
        )
        self.button_box.accepted.connect(self.save_configuration)
        self.button_box.rejected.connect(self.reject)

        main_layout.addWidget(self.button_box)

        self.setLayout(main_layout)

    def load_options(self):
        with open(self.options_file, "r") as file:
            lines = file.readlines()

        for line in lines:
            stripped_line = line.strip()
            if (
                stripped_line != "Field Options:"
                and stripped_line != "Read/Write Protection:"
            ):
                self.fields.append(stripped_line)

    def save_configuration(self):
        selected_fields = [
            checkbox.text()
            for checkbox in self.field_checkboxes
            if checkbox.isChecked()
        ]
        selected_read = [
            self.fields[i]
            for i, checkbox in enumerate(self.read_checkboxes)
            if checkbox.isChecked()
        ]
        selected_write = [
            self.fields[i]
            for i, checkbox in enumerate(self.write_checkboxes)
            if checkbox.isChecked()
        ]

        config_data = {
            "Field Options": selected_fields,
            "Read Options": selected_read,
            "Write Options": selected_write,
        }

        with open("configuration.json", "w") as json_file:
            json.dump(config_data, json_file, indent=4)

        print(f"Selected Field Options: {selected_fields}")
        print(f"Selected Read Options: {selected_read}")
        print(f"Selected Write Options: {selected_write}")
        self.accept()
