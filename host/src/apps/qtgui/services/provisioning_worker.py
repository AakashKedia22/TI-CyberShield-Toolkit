#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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

"""
Thread worker classes for handling long-running provisioning operations.
"""
import os
import sys
import time
import threading
from queue import Queue
from io import StringIO
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, QRunnable, QThreadPool, Qt, QTimer
from PyQt5.QtWidgets import QProgressDialog, QPushButton, QMessageBox
from common.platform_utils import kill_proc_tree


# Global thread pool for managing worker threads
global_thread_pool = QThreadPool()

def create_progress_dialog(parent, title, message):
    """
    Create a progress dialog with consistent styling and settings.
    
    Args:
        parent: The parent widget
        title: The window title
        message: The message to display
        
    Returns:
        QProgressDialog: Configured progress dialog
    """
    progress = QProgressDialog(message, "Cancel", 0, 0, parent)
    progress.setWindowTitle(title)
    progress.setModal(True)  # Use setModal instead of WindowModal
    progress.setMinimumDuration(0)
    progress.setWindowFlags(progress.windowFlags() & ~Qt.WindowCloseButtonHint)
    
    # Connect cancel button (placeholder for future implementation)
    cancel_button = progress.findChild(QPushButton)
    if cancel_button:
        cancel_button.clicked.disconnect()
        # Connect to custom cancel handler if provided
    
    return progress


class WorkerSignals(QObject):
    """
    Defines the signals available for worker threads.
    """
    finished = pyqtSignal()
    error = pyqtSignal(str)
    result = pyqtSignal(bool, str)
    progress = pyqtSignal(int)
    output = pyqtSignal(str)  # New signal for streaming output


class StreamCapture:
    """
    A class to capture stdout and stderr and emit their contents as signals.
    """
    def __init__(self, emit_callback):
        self.emit_callback = emit_callback
        self.queue = Queue()
        self.old_stdout = None
        self.old_stderr = None
        self.capture_thread = None
        self.stop_event = threading.Event()
    
    def start_capture(self):
        """Start capturing stdout and stderr"""
        self.old_stdout = sys.stdout
        self.old_stderr = sys.stderr
        sys.stdout = self
        sys.stderr = self
        
        # Start the reader thread
        self.stop_event.clear()
        self.capture_thread = threading.Thread(target=self._read_queue)
        self.capture_thread.daemon = True
        self.capture_thread.start()
    
    def stop_capture(self):
        """Stop capturing and restore stdout and stderr"""
        if self.old_stdout:
            sys.stdout = self.old_stdout
            self.old_stdout = None
        if self.old_stderr:
            sys.stderr = self.old_stderr
            self.old_stderr = None
            
        # Stop the reader thread
        if self.capture_thread:
            self.stop_event.set()
            if self.capture_thread.is_alive():
                self.capture_thread.join(timeout=1.0)
    
    def write(self, text):
        """Write captured output to the queue"""
        # Write to the queue and to original stdout
        self.queue.put(text)
        if self.old_stdout:
            self.old_stdout.write(text)
    
    def flush(self):
        """Required to be file-like"""
        if self.old_stdout:
            self.old_stdout.flush()
    
    def _read_queue(self):
        """Read from the queue and emit signals"""
        buffer = ""
        while not self.stop_event.is_set():
            try:
                # Get text from queue with timeout to allow for checking stop_event
                if not self.queue.empty():
                    text = self.queue.get(block=False)
                    buffer += text
                    
                    # Only emit when we have a complete line or substantial content
                    if '\n' in buffer or len(buffer) > 100:
                        self.emit_callback(buffer)
                        buffer = ""
                else:
                    # If there's any remaining content in buffer, emit it
                    if buffer and (self.stop_event.is_set() or len(buffer) > 0):
                        self.emit_callback(buffer)
                        buffer = ""
                    time.sleep(0.1)  # Short sleep to prevent CPU hogging
            except Exception as e:
                # Just in case there's an error in the queue reading
                print(f"Error in stream capture: {str(e)}")
                time.sleep(0.5)  # Longer sleep on error


class ProvisioningWorker(QRunnable):
    """
    Worker thread for handling provisioning operations.
    
    Inherits from QRunnable to handle worker thread setup, signals and wrap-up.
    """
    
    def __init__(self, operation_type, params, stream_output=False):
        """
        Initialize the worker thread.

        Args:
            operation_type (str): Type of operation ('jtag_keyprov', 'uart_keyprov',
                                 'jtag_codeprov', 'uart_codeprov')
            params (dict): Parameters needed for the operation
            stream_output (bool): Whether to stream output during execution
        """
        super(ProvisioningWorker, self).__init__()
        self.operation_type = operation_type
        self.params = params
        self.signals = WorkerSignals()
        self.stream_output = stream_output
        self.stdout_capture = None
        self._cancel_event = threading.Event()
        self._active_proc = None
        self._proc_lock = threading.Lock()

        if stream_output:
            # Set up the stdout/stderr capture
            self.stdout_capture = StreamCapture(self._emit_output)
        
    def cancel(self) -> None:
        """Signal cancellation and kill any running subprocess immediately."""
        self._cancel_event.set()
        with self._proc_lock:
            if self._active_proc is not None and self._active_proc.poll() is None:
                kill_proc_tree(self._active_proc)

    def _register_proc(self, proc) -> None:
        """Store subprocess reference so cancel() can kill it."""
        with self._proc_lock:
            self._active_proc = proc

    def _emit_output(self, text):
        """Helper method to emit captured output"""
        self.signals.output.emit(text)
    
    @pyqtSlot()
    def run(self):
        """
        Run the worker thread.
        
        This is the method that will be executed when the thread starts.
        It will run the appropriate provisioning function based on the operation_type.
        """
        # Start output capture if streaming is enabled
        if self.stream_output and self.stdout_capture:
            self.stdout_capture.start_capture()
            
        try:
            # Execute the appropriate operation based on type
            from apps.qtgui.devices.register import get_task_fn_for_device
            device = self.params.get("device", "")
            task_fn = get_task_fn_for_device(device, self.operation_type)
            if task_fn is not None:
                params = dict(self.params)
                params["_cancel_event"] = self._cancel_event
                params["_register_proc"] = self._register_proc
                success, output = task_fn(params)
            else:
                success = False
                output = f"Unknown operation type: {self.operation_type}"
                
            # Emit the result signal
            self.signals.result.emit(success, output)
        except Exception as e:
            # Emit an error signal if something goes wrong
            self.signals.error.emit(str(e))
        finally:
            # Stop output capture if it was enabled
            if self.stream_output and self.stdout_capture:
                self.stdout_capture.stop_capture()
                
            # Always emit the finished signal
            self.signals.finished.emit()


def stream_provisioning_output(operation_type, params, output_callback=None, 
                           finished_callback=None, result_callback=None, error_callback=None):
    """
    Start a provisioning task in a background thread with output streaming.
    
    Args:
        operation_type (str): Type of operation ('jtag_keyprov', 'uart_keyprov',
                            'jtag_codeprov', 'uart_codeprov')
        params (dict): Parameters needed for the operation
        output_callback (function): Callback for streaming output during operation
        finished_callback (function): Callback for when the operation finishes
        result_callback (function): Callback for when the operation produces a result
        error_callback (function): Callback for when the operation encounters an error
        
    Returns:
        ProvisioningWorker: The worker instance that was created and started
    """
    # Create worker instance with streaming enabled
    worker = ProvisioningWorker(operation_type, params, stream_output=True)
    
    # Connect signals
    if finished_callback:
        worker.signals.finished.connect(finished_callback)
    if result_callback:
        worker.signals.result.connect(result_callback)
    if error_callback:
        worker.signals.error.connect(error_callback)
    if output_callback:
        worker.signals.output.connect(output_callback)
        
    # Start the worker
    global_thread_pool.start(worker)
    
    return worker


def start_provisioning_task(operation_type, params, on_finished=None, on_result=None, on_error=None):
    """
    Start a provisioning task in a background thread.

    Args:
        operation_type (str): Type of operation ('jtag_keyprov', 'uart_keyprov',
                             'jtag_codeprov', 'uart_codeprov')
        params (dict): Parameters needed for the operation
        on_finished (function): Callback for when the operation finishes
        on_result (function): Callback for when the operation produces a result (success, output)
        on_error (function): Callback for when the operation encounters an error

    Returns:
        ProvisioningWorker: The worker instance that was created and started
    """
    # Create worker instance
    worker = ProvisioningWorker(operation_type, params)

    # Connect signals
    if on_finished:
        worker.signals.finished.connect(on_finished)
    if on_result:
        worker.signals.result.connect(on_result)
    if on_error:
        worker.signals.error.connect(on_error)

    # Start the worker
    global_thread_pool.start(worker)

    return worker


class _DetectorSignals(QObject):
    complete = pyqtSignal(dict)


class PostProvisioningDetector(QRunnable):
    """Device-agnostic post-provisioning state detector.

    Dispatches via get_detect_spec_for_device (registry-first).
    Falls back to binary SoC ID (UART) or run_get_device_type_jtag (JTAG)
    for devices without a registered spec.
    """

    def __init__(self, device_name: str, boot_mode: str, connection_info: dict):
        super().__init__()
        self.signals = _DetectorSignals()
        self._device_name = device_name
        self._boot_mode = boot_mode          # 'UART' or 'JTAG'
        self._connection_info = connection_info

    def run(self):
        from apps.qtgui.devices.register import get_detect_spec_for_device
        from apps.qtgui.soc_id_detector import detect_device_from_port
        from apps.spt.f29_spt import run_get_device_type_jtag

        spec = get_detect_spec_for_device(self._device_name, self._boot_mode)

        try:
            if spec:
                # Registry path — e.g. _detect_uart / _detect_jtag from tasks.py
                success, state, error = spec['fn'](self._connection_info)
                if success and state:
                    self.signals.complete.emit({
                        'success': True,
                        'device': self._device_name,
                        'device_state': state,
                    })
                else:
                    self.signals.complete.emit({
                        'success': False,
                        'device': None,
                        'device_state': None,
                        'error': error or 'Detection failed',
                    })
            elif self._boot_mode == 'UART':
                # Fallback: binary SoC ID (non-f29h85x devices)
                result = detect_device_from_port(self._connection_info.get('port', ''))
                self.signals.complete.emit(result)
            else:
                # Fallback: inline JTAG (non-f29h85x devices)
                ccs_path = self._connection_info.get('ccs_path', '')
                tcp = self._connection_info.get('target_config_path', '')
                ccxml = tcp if tcp and os.path.exists(tcp) else None
                success, output = run_get_device_type_jtag(
                    ccs_path, verbose=True, ccxml_path=ccxml
                )
                if success:
                    state = 'HSFS'
                    if 'HS_KP' in output:   state = 'HSKP'
                    elif 'HS_SE' in output: state = 'HSSE'
                    self.signals.complete.emit({
                        'success': True,
                        'device': self._device_name,
                        'device_state': state,
                    })
                else:
                    self.signals.complete.emit({
                        'success': False,
                        'device': None,
                        'device_state': None,
                        'error': output,
                    })
        except Exception as e:
            self.signals.complete.emit({
                'success': False,
                'device': None,
                'device_state': None,
                'error': str(e),
            })


def run_post_provisioning_detection(
    device_name: str,
    boot_mode: str,
    connection_info: dict,
    on_complete,
) -> PostProvisioningDetector:
    """Start post-provisioning state detection on the global thread pool.

    Args:
        device_name:     Device name (e.g. 'f29h85x').
        boot_mode:       'UART' or 'JTAG'.
        connection_info: connection_info dict from session_info.
        on_complete:     Callable(dict) — receives result when detection finishes.

    Returns the detector instance (caller must hold a reference).
    """
    detector = PostProvisioningDetector(device_name, boot_mode, connection_info)
    detector.signals.complete.connect(on_complete)
    global_thread_pool.start(detector)
    return detector