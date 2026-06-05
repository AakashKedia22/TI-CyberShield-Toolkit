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

from PyQt5.QtCore import QThread, pyqtSignal, QTimer
from serial.tools.list_ports import comports
import serial
import time
from xmodem import XMODEM


class SerialThread(QThread):
    data_received = pyqtSignal(str)
    flashing_done = pyqtSignal(int)
    flashing_fail = pyqtSignal(int)
    enable_export = pyqtSignal(bool)
    update_progress_signal = pyqtSignal(int)

    def __init__(self, file_name, port, baudrate):
        super().__init__()

        try:
            self.serial_port = serial.Serial(port, baudrate)
            self.percentage = 0
            self.file_name = file_name
            self.modem = XMODEM(self.getc, self.putc)
            self.running = True

            with open(self.file_name, "rb") as f:
                self.file_size = len(f.read())
                self.total_packets = (self.file_size + 127) // 128
        except serial.SerialException as e:
            critical_message("Error opening serial port:" + str(self.port))
        except FileNotFoundError:
            critical_message("The file {file_name} was not found" + str(self.file_name))
        except PermissionError:
            critical_message(
                "Permission denied to read the file " + str(self.file_name)
            )
        except Exception as e:
            critical_message("An error occurred")

    def stop(self):
        self.running = False
        if hasattr(self, "serial_port"):
            self.serial_port.close()
        self.wait()

    def getc(self, size, timeout=1):
        return self.serial_port.read(size) or None

    def putc(self, data, timeout=1):
        return self.serial_port.write(data)

    def progress_callback(self, total_packets, success_packets, error_packets):
        if total_packets > 0:
            self.percentage = int((success_packets * 128 / self.file_size) * 100)
            self.percentage = min(100, self.percentage)
        self.update_progress_signal.emit(self.percentage)

    def run(self):
        try:
            with open(self.file_name, "rb") as image:
                status = self.modem.send(image, callback=self.progress_callback)
                # Raise exception if flashing failed
                if status != True:
                    self.percentage = 0
                    self.update_progress_signal.emit(self.percentage)
                    self.flashing_fail.emit(1)
                    return
            soc_id_sm_timeout_sec = 1
            soc_id_sm_end_time = time.time() + soc_id_sm_timeout_sec

            while True:
                if time.time() >= soc_id_sm_end_time:
                    self.serial_port.close()
                    if self.percentage == 100:
                        self.flashing_done.emit(1)
                        self.enable_export.emit(True)
                        self.percentage = 0
                        return
                    else:
                        return

                if self.serial_port.in_waiting > 1:
                    data = self.serial_port.readline().decode("utf-8").strip()
                    soc_id_sm_end_time = time.time() + soc_id_sm_timeout_sec
                    self.data_received.emit(data)

        except serial.SerialTimeoutException as e:
            print(f"Serial timeout error: {e}")
            self.error_message = f"Serial timeout error: {e}"

        except serial.SerialException as e:
            print(f"Serial error: {e}")
            self.error_message = f"Serial error: {e}"

        except IOError as e:
            print(f"I/O error: {e}")
            self.error_message = f"I/O error: {e}"

        except XMODEM.Error as e:
            print(f"XMODEM error: {e}")
            self.error_message = f"XMODEM error: {e}"

        except Exception as e:
            print(f"An error occurred: {e}")
            self.error_message = f"An error occurred: {e}"


def get_serial_ports():
    ports = []
    for port in comports():
        ports.append(port[0])
    return ports


def print_console(
    file_name,
    progress_bar,
    console_log_frame,
    port,
    console_log_text,
    state_layout,
    export_button,
):
    progress_bar.setVisible(True)
    progress_bar.setValue(0)
    console_log_text.clear()

    print("Print console_reached")
    serial_thread = SerialThread(file_name, port, 115200)
    console_log_frame.serial_thread = serial_thread
    serial_thread.data_received.connect(
        lambda msg: update_text_edit(console_log_text, msg)
    )
    serial_thread.enable_export.connect(lambda msg: enable_export(export_button))
    serial_thread.update_progress_signal.connect(progress_bar.setValue)

    timer = QTimer()
    timer.timeout.connect(lambda: None)
    timer.start(100)

    serial_thread.start()


def update_text_edit(console_log_text, data):
    console_log_text.append(data)


def enable_export(export_button):
    export_button.setEnabled(True)
