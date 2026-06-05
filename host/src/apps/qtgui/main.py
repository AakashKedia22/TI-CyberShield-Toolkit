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
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QTabWidget,
    QStatusBar,
    QLabel,
    QMenu,
    QMenuBar,
    QFrame,
    QSizePolicy,
)

from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import Qt

from importlib import resources

from apps.qtgui import settings
from apps.qtgui import console

import os


def get_image_path(image_name):
    with resources.path("apps.qtgui.assets", image_name) as image_path:
        return str(image_path)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("TI Cybershield Toolkit")
        logo_path = get_image_path("TI_square_bug.jpg")
        print(f"Logo path: {logo_path}")

        self.setWindowIcon(QIcon(logo_path))
        self.setStyleSheet(
            """
            QMainWindow {
                background-color: white;
            }
            QMenuBar {
                background-color: #CC0000;
                color: white;
                padding: 5px;
                font-size: 14px;
            }
            QLabel#headerLabel {
                color: #666666;
                font-size: 24px;
                padding: 10px;
            }
            QLabel#subHeaderLabel {
                color: #666666;
                font-size: 14px;
            }
            QTabWidget::pane {
                border: none;
                background: white;
            }
            QTabBar::tab {
                background: white;
                color: #666666;
                padding: 8px 20px;
                min-width: 150px;
                border: none;
            }
            QTabBar::tab:selected {
                color: #CC0000;
                border-bottom: 2px solid #CC0000;
            }
            QListWidget {
                border: 1px solid #DDDDDD;
                background-color: white;
                font-size: 14px;
            }
            QListWidget::item {
                padding: 8px;
                color: #666666;
            }
            QListWidget::item:selected {
                background-color: #F5F5F5;
                color: #CC0000;
            }
            QPushButton#generateButton {
                background-color: #CC0000;
                color: white;
                padding: 8px 20px;
                border: none;
                min-width: 120px;
                font-size: 14px;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #DDDDDD;
                background: white;
                color: #666666;
            }
            QLabel {
                color: #666666;
                font-size: 14px;
            }
        """
        )
        self.init_ui()
        self.setMinimumWidth(900)
        self.setMinimumHeight(900)

        # Set initial size
        self.resize(900, 900)
        
        # Use sizeHint for dynamic sizing
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Center window after setting size
        self.centerWindow()

    def init_ui(self):

        central_widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Add TI logo and title in header
        header_widget = QWidget()
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(10, 5, 10, 5)

        # TI Logo
        logo_label = QLabel()
        try:
            logo_path = get_image_path("TI_square_bug.jpg")
            logo_pixmap = QPixmap(logo_path)
            if not logo_pixmap.isNull():
                scaled_logo = logo_pixmap.scaled(
                    30, 30, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                logo_label.setPixmap(scaled_logo)
        except Exception as e:
            print(f"Error loading logo: {e}")
            logo_label.setText("TI")  # Fallback text if image fails to load

        # Application title next to logo
        app_title = QLabel("Texas Instruments Cybershield Toolkit")
        app_title.setStyleSheet("color: white; font-size: 16px;")

        header_layout.addWidget(logo_label)
        header_layout.addWidget(app_title)
        header_layout.addStretch()

        header_widget.setLayout(header_layout)
        header_widget.setStyleSheet("background-color: #CC0000;")
        
        # Create a container widget for our layout
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add header to container
        container_layout.addWidget(header_widget)
        
        # Create a placeholder widget since setup_key_cert was removed
        placeholder = QLabel("Key Certificate functionality has been moved to the wizard interface.")
        placeholder.setAlignment(Qt.AlignCenter)
        container_layout.addWidget(placeholder)
        
        # Set container as central widget
        self.setCentralWidget(container)

    def centerWindow(self):
        """Center the window on the screen"""
        screen_geometry = QApplication.desktop().availableGeometry()
        window_geometry = self.frameGeometry()
        center_point = screen_geometry.center()
        window_geometry.moveCenter(center_point)
        self.move(window_geometry.topLeft())


def create_gui():
    app = QApplication([])
    app.setApplicationName("Cybershield Toolkit")
    window = MainWindow()
    window.show()

    app.exec_()


def main():
    create_gui()


if __name__ == "__main__":
    main()
