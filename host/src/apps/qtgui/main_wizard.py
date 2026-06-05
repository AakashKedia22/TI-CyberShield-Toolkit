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
    QSplashScreen
)
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import Qt, QTimer
import sys
import os
import pathlib
from importlib import resources

from apps.qtgui.views.wizard_view import WizardView
from apps.qtgui.controllers.wizard_controller import WizardController

def get_image_path(image_name):
    with resources.path("apps.qtgui.assets", image_name) as image_path:
        return str(image_path)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("TI Cybershield Toolkit")
        logo_path = get_image_path("TI_square_bug.jpg")
        self.setWindowIcon(QIcon(logo_path))
        
        # Create wizard view
        self.wizard_view = WizardView()
        
        # Create wizard controller
        self.controller = WizardController(self.wizard_view)
        
        # Set as central widget
        self.setCentralWidget(self.wizard_view)
        
        # Set window properties
        self.setMinimumSize(1200, 800)  
        self.resize(1200, 900)  # Set default size larger than minimum
        self.centerWindow()

    def closeEvent(self, event):
        """Kill any running UART subprocesses before the window is destroyed."""
        self.wizard_view.config_page.cleanup_active_operations()
        self.wizard_view.provisioning_page.cleanup_active_operations()
        super().closeEvent(event)

    def centerWindow(self):
        """Center the window on the screen"""
        screen_geometry = QApplication.desktop().availableGeometry()
        window_geometry = self.frameGeometry()
        center_point = screen_geometry.center()
        window_geometry.moveCenter(center_point)
        self.move(window_geometry.topLeft())

def create_gui():
    app = QApplication([])
    app.setApplicationName("CyberShield Toolkit")
    
    # Create and show splash screen
    splash_pixmap = QPixmap(get_image_path("TI_square_bug.jpg")).scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    splash = QSplashScreen(splash_pixmap)
    splash.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
    splash.show()
    app.processEvents()
    
    # Create main window
    window = MainWindow()
    
    # Close splash and show main window after a delay
    def show_main_window():
        splash.finish(window)
        window.show()
        
    # Use timer to show splash for 1 second
    QTimer.singleShot(1000, show_main_window)
    
    app.exec_()

def main():
    import argparse
    from tisecprov import __version__
    parser = argparse.ArgumentParser(description="TI Cybershield Toolkit GUI", add_help=False)
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--help", "-h", action="help")
    parser.parse_known_args()
    create_gui()

if __name__ == "__main__":
    main()