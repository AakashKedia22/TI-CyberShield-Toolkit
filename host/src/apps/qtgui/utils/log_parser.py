#!/usr/bin/env python3
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
Log parser module for tisecprov.

This module provides functionality for parsing and analyzing provisioning logs
from both Key Provisioning (KP) and Code Provisioning (CP) operations.
"""

import os
import re
import pathlib
from collections import OrderedDict
import datetime
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union, Any, OrderedDict as OrderedDictType

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LogManager:
    """Manages log files for provisioning operations."""
    
    # Default log directory and filename template
    DEFAULT_LOG_DIR = os.path.join("host", "src", "apps", "tifs", "kp_cp_f29h85x")
    DEFAULT_LOG_FILENAME = "logs.txt"
    KP_LOG_FILENAME = "kp_logs.txt"
    CP_LOG_FILENAME = "cp_logs.txt"
    
    def __init__(self, repo_base=None):
        """Initialize the LogManager.
        
        Args:
            repo_base: Base path of the repository. If None, will attempt to auto-detect.
        """
        self.repo_base = repo_base or self._find_repo_base()
        self.log_dir = os.path.join(self.repo_base, self.DEFAULT_LOG_DIR)
        os.makedirs(self.log_dir, exist_ok=True)
        
    def _find_repo_base(self):
        """Find the base directory of the repository."""
        current_dir = os.getcwd()
        repo_path = pathlib.Path(current_dir)
        
        # Traverse up until we find the 'tisecprov' directory
        while repo_path.name != "tisecprov":
            parent = repo_path.parent
            if parent == repo_path:  # Reached root
                # Fall back to current directory if can't find repo base
                logger.warning("Could not find repository base, using current directory")
                return current_dir
            repo_path = parent
            
        return str(repo_path)
        
    def get_default_log_path(self):
        """Get the path to the default log file."""
        return os.path.join(self.log_dir, self.DEFAULT_LOG_FILENAME)
        
    def get_kp_log_path(self):
        """Get the path to the key provisioning log file."""
        return os.path.join(self.log_dir, self.KP_LOG_FILENAME)
        
    def get_cp_log_path(self):
        """Get the path to the code provisioning log file."""
        return os.path.join(self.log_dir, self.CP_LOG_FILENAME)
    
    def create_timestamped_log_path(self, prefix="provisioning", suffix=".log"):
        """Create a timestamped log filename.
        
        Args:
            prefix: Prefix for the log file
            suffix: Suffix for the log file
            
        Returns:
            Path to the timestamped log file
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{timestamp}{suffix}"
        return os.path.join(self.log_dir, filename)
    
    def archive_current_log(self):
        """Archive the current log file with a timestamp."""
        current_log = self.get_default_log_path()
        if os.path.exists(current_log):
            # Only archive if the file exists and has content
            if os.path.getsize(current_log) > 0:
                archived_log = self.create_timestamped_log_path()
                try:
                    import shutil
                    shutil.copy2(current_log, archived_log)
                    logger.info(f"Archived log to {archived_log}")
                    return archived_log
                except Exception as e:
                    logger.error(f"Failed to archive log: {str(e)}")
        return None


@dataclass
class KeyProvisioningData:
    """Data structure for Key Provisioning information."""
    key_programming: Dict[str, str] = field(default_factory=dict)
    otp_status: List[str] = field(default_factory=list)
    success_messages: List[str] = field(default_factory=list)
    final_state: Optional[str] = None

@dataclass
class CodeProvisioningStage:
    """Data structure for a Code Provisioning stage."""
    progress: List[Dict[str, Any]] = field(default_factory=list)
    final_percentage: int = 0

@dataclass
class CodeProvisioningData:
    """Data structure for Code Provisioning information."""
    stages: OrderedDictType[str, CodeProvisioningStage] = field(default_factory=OrderedDict)
    progress: List[Dict[str, Any]] = field(default_factory=list)
    success_messages: List[str] = field(default_factory=list)

@dataclass
class LogData:
    """Container for all log parsing data."""
    device_info: Dict[str, str] = field(default_factory=dict)
    key_provisioning: KeyProvisioningData = field(default_factory=KeyProvisioningData)
    code_provisioning: CodeProvisioningData = field(default_factory=CodeProvisioningData)
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the LogData to a dictionary format compatible with existing code."""
        return {
            'device_info': self.device_info,
            'key_provisioning': {
                'key_programming': self.key_provisioning.key_programming,
                'otp_status': self.key_provisioning.otp_status,
                'success_messages': self.key_provisioning.success_messages,
                'final_state': self.key_provisioning.final_state
            },
            'code_provisioning': {
                'stages': {
                    name: {'progress': stage.progress, 'final_percentage': stage.final_percentage}
                    for name, stage in self.code_provisioning.stages.items()
                },
                'progress': self.code_provisioning.progress,
                'success_messages': self.code_provisioning.success_messages
            },
            'errors': self.errors
        }


def parse_provisioning_logs(log_text: str) -> Union[Dict[str, Any], LogData]:
    """Parse provisioning logs to extract relevant information.
    
    Args:
        log_text: String containing the log text to parse
        
    Returns:
        LogData object containing parsed data from both key and code provisioning,
        or an empty dictionary if no log text is provided
    """
    if not log_text:
        return {}
    
    # Create a LogData object to store parsed data
    parsed_data = LogData()
    
    try:
        # Extract device information
        device_info_patterns = {
            'SOC Type': r'\[Soc Type\]\s*=\s*([^\n]+)',
            'Device Type': r'\[Device Type\]\s*=\s*([^\n]+)',
            'HSM Type': r'\[HSM Type\]\s*=\s*([^\n]+)',
            'Binary Type': r'\[Bin Type\]\s*=\s*([^\n]+)'
        }
        
        # Check for either OTP-KW Version or TIFS-MCU Version
        otp_kw_version = re.search(r'\[OTP-KW Version\]\s*=\s*([^\n]+)', log_text)
        if otp_kw_version:
            device_info_patterns['OTP-KW Version'] = r'\[OTP-KW Version\]\s*=\s*([^\n]+)'
        
        tifs_version = re.search(r'\[TIFS-MCU Version\]\s*=\s*([^\n]+)', log_text)
        if tifs_version:
            device_info_patterns['TIFS-MCU Version'] = r'\[TIFS-MCU Version\]\s*=\s*([^\n]+)'
        
        for label, pattern in device_info_patterns.items():
            match = re.search(pattern, log_text)
            if match:
                parsed_data.device_info[label] = match.group(1).strip()
        
        # Extract certificate processing time
        cert_time_match = re.search(r'\[HSM CLIENT_PROFILE\] Time taken to Process Key Certificate (\d+)us', log_text)
        if cert_time_match:
            parsed_data.device_info['Certificate Processing Time'] = f"{cert_time_match.group(1)}μs"
            
        # Extract key types
        key_type_patterns = {
            'BMPK Key Type': r'BMPK Key Type : ([^\n]+)',
            'SMPK Key Type': r'SMPK Key Type : ([^\n]+)'
        }
        
        for label, pattern in key_type_patterns.items():
            match = re.search(pattern, log_text)
            if match:
                parsed_data.device_info[label] = match.group(1).strip()
        
        # Extract OTP-KW status
        error_match = re.search(r'\[HSM CLIENT\] OTP-KW Error encountered in OTP Keywriter', log_text)
        if error_match:
            # Extract error details
            debug_response = re.search(r'\[HSM CLIENT\] OTP-KW debugResponse = (0x[0-9a-fA-F]+)', log_text)
            error_phase = re.search(r'\[HSM CLIENT\] OTP-KW Error phase = (0x[0-9a-fA-F]+)', log_text)
            error_module = re.search(r'\[HSM CLIENT\] OTP-KW Error module = (0x[0-9a-fA-F]+)', log_text)
            error_stage = re.search(r'\[HSM CLIENT\] OTP-KW Error stage = (0x[0-9a-fA-F]+)', log_text)
            
            # When debug response is 0x00000000, it indicates success despite the error message
            if debug_response and debug_response.group(1) == '0x00000000':
                # This is actually a success case
                parsed_data.device_info['OTP-KW Status'] = 'Success (debugResponse: 0x00000000)'
            else:
                error_info = "OTP-KW Error encountered"
                if debug_response:
                    error_info += f", Debug Response: {debug_response.group(1)}"
                if error_phase:
                    error_info += f", Phase: {error_phase.group(1)}"
                if error_module:
                    error_info += f", Module: {error_module.group(1)}"
                if error_stage:
                    error_info += f", Stage: {error_stage.group(1)}"
                    
                parsed_data.errors.append(error_info)
    except Exception as e:
        logger.error(f"Error parsing device information: {str(e)}")
        parsed_data.errors.append(f"Error parsing device information: {str(e)}")
    
    # Parse key provisioning logs
    parse_key_provisioning_logs(log_text, parsed_data)
    
    # Parse code provisioning logs
    parse_code_provisioning_logs(log_text, parsed_data)
    
    # For backward compatibility, return either the LogData object or its dictionary form
    return parsed_data


# UART CP stage definitions — ordered list of (stage_name, start_marker, success_pattern).
# Each stage's segment runs from start_marker to the next start_marker (or end of log).
_UART_CP_STAGES = [
    ("SecCfg Loading is successful",
     "Executing command option 5",
     r"SecCfg Loading is successful\."),
    ("HSM Flash Loading is successful",
     "Executing command option 6",
     r"HSM Flash Loading is successful\."),
    ("CPU1 APP Loading is successful",
     "Executing command option 7",
     r"CPU APP Loading is successful\."),
    ("CPU3 APP Loading is successful",
     "Executing command option 8",
     r"CPU APP Loading is successful\."),
]


_KEY_COMPONENTS = [
    'MSV', 'MSV_BCH', 'SWREV SSU', 'SWREV SBL', 'SWREV HSMRT', 'SWREV APP',
    'EXT OTP', 'SMPKH', 'SMEK', 'BMPKH', 'BMEK', 'KEY COUNT', 'KEY REV'
]

_JTAG_KP_FIELD_PATTERNS = [
    # Policy / options fields
    ('MPK Options',   r'\*\s*MPK Options\s*:\s*(0x[0-9a-fA-F]+)'),
    ('MEK Options',   r'\*\s*MEK Options\s*:\s*(0x[0-9a-fA-F]+)'),
    ('MPK Opt P1',    r'\*\s*MPK Opt P1\s*:\s*(0x[0-9a-fA-F]+)'),
    ('MPK Opt P2',    r'\*\s*MPK Opt P2\s*:\s*(0x[0-9a-fA-F]+)'),
    ('MEK Opt',       r'\*\s*MEK Opt\s*:\s*(0x[0-9a-fA-F]+)'),
    # Key hash fields
    ('SMPKH',         r'\*\s*SMPKH Part 1 BCH code\s*:\s*(0x[0-9a-fA-F]+)'),
    ('SMEK',          r'\*\s*SMEK Hash\s*:\s*\n?\s*(0x[0-9a-fA-F]+)'),
    ('BMPKH',         r'\*\s*BMPKH Part 1 BCH code\s*:\s*(0x[0-9a-fA-F]+)'),
    ('BMEK',          r'\*\s*BMEK Hash\s*:\s*\n?\s*(0x[0-9a-fA-F]+)'),
    # Other OTP fields
    ('MSV',           r'\[uint32_t\]\s*MSV\s*:\s*(0x[0-9a-fA-F]+)'),
    ('MSV_BCH',       r'\[uint32_t\]\s*MSV_BCH\s*:\s*(0x[0-9a-fA-F]+)'),
    ('EXT OTP',       r'\*\s*EXT OTP Hash\s*:\s*\n?\s*([0-9a-fA-F]+)'),
    ('SWREV APP',     r'\*\s*APP SWREV\s*:\s*(0x[0-9a-fA-F]+)'),
    ('SWREV SBL',     r'\*\s*SBL SWREV\s*:\s*(0x[0-9a-fA-F]+)'),
    ('SWREV HSMRT',   r'\*\s*HSM SWREV\s*:\s*(0x[0-9a-fA-F]+)'),
    ('SWREV SSU',     r'\*\s*(?:SSU SWREV|APP SSU)\s*:\s*(0x[0-9a-fA-F]+)'),
    ('KEY COUNT',     r'\[u32\]\s*key_cnt\s*:\s*(0x[0-9a-fA-F]+)'),
    ('KEY REV',       r'OTP Programming Status\s*:\s*Key Revision Programming is successful'),
]


def _parse_uart_key_provisioning_logs(log_text: str, parsed_data: LogData) -> None:
    """Parse key provisioning component status from UART boot-mode logs."""
    key_prog_section = re.search(
        r'Programming Keys\.\.(.*?)(?:OTP Programming Status|$)', log_text, re.DOTALL
    )
    if not key_prog_section:
        return

    component_full_text = key_prog_section.group(1)
    for component in _KEY_COMPONENTS:
        try:
            component_pattern = component.replace(' ', r'\s*')
            # UART logs have blank lines within sections; use uppercase-word boundary as delimiter.
            # Multi-word names (e.g. "SWREV SSU") require space in the character class.
            component_sections = re.findall(
                f'{component_pattern}:(.*?)(?=\\n[A-Z][A-Z _]+:|\\n#|$)',
                component_full_text, re.DOTALL
            )
            if not component_sections:
                continue

            success = False
            for section in component_sections:
                m = re.search(r'Programmed (\d+)/(\d+) rows successfully', section)
                if m and m.group(1) == m.group(2):
                    success = True
                    break

            if not success and component.lower() in ('key rev', 'keyrev'):
                if re.search(r'OTP Programming Status\s*:\s*Key Revision Programming is successful', log_text):
                    success = True

            if not success and component.lower() == 'msv':
                if re.search(r'MSV:[\s\S]*HSM KeyStore:\s*0,\s*Offset:\s*236\s*data:\s*0x[0-9a-fA-F]+', log_text):
                    success = True

            parsed_data.key_provisioning.key_programming[component] = 'Success' if success else 'Failed'
        except Exception as e:
            logger.warning(f"Error processing key component {component}: {str(e)}")
            parsed_data.key_provisioning.key_programming[component] = 'Error'


def _parse_jtag_key_provisioning_logs(log_text: str, parsed_data: LogData) -> None:
    """Parse key provisioning component status from JTAG boot-mode logs."""
    # Prefer searching within the decrypting section; fall back to full log.
    section_match = re.search(
        r'# Decrypting extensions\.\..*?(?=Key provisioning completed|$)',
        log_text, re.DOTALL
    )
    search_text = section_match.group(0) if section_match else log_text

    for display_name, pattern in _JTAG_KP_FIELD_PATTERNS:
        if re.search(pattern, search_text):
            parsed_data.key_provisioning.key_programming[display_name] = 'Success'


def parse_key_provisioning_logs(log_text: str, parsed_data: LogData) -> None:
    """Parse key provisioning sections from the log text.

    Detects the boot mode (UART or JTAG) and delegates to the appropriate
    per-mode parser, then extracts mode-agnostic OTP status and final
    device state information.

    Args:
        log_text: The full log text
        parsed_data: LogData object to store parsed data (modified in place)
    """
    try:
        is_jtag = 'JTAG FLASH KERNEL' in log_text or 'Starting DSS script' in log_text
        is_uart = ('UART Firmware Programmer' in log_text or
                   'Serial Port:' in log_text or
                   'getPacket success' in log_text)

        if is_jtag:
            _parse_jtag_key_provisioning_logs(log_text, parsed_data)
            # Fallback: if the JTAG KP log has no detailed component data at all
            # (e.g. HS-FS minimal log with no # Decrypting extensions section),
            # infer success from debugResponse = 0x00000000.
            # Do NOT trigger when key_programming is already populated — that means
            # the decryption section was parsed and we have real per-component data.
            if (not parsed_data.key_provisioning.success_messages
                    and not parsed_data.key_provisioning.otp_status
                    and not parsed_data.key_provisioning.key_programming):
                debug_resp = re.search(r'OTP-KW debugResponse = (0x[0-9a-fA-F]+)', log_text)
                if debug_resp and debug_resp.group(1) == '0x00000000':
                    parsed_data.key_provisioning.success_messages.append(
                        "Key provisioning completed successfully"
                    )
        elif is_uart:
            _parse_uart_key_provisioning_logs(log_text, parsed_data)

        # OTP Programming Status messages — mode-agnostic
        for match in re.finditer(r'OTP Programming Status\s*:\s*(.*?)$', log_text, re.MULTILINE):
            status_msg = match.group(1).strip()
            parsed_data.key_provisioning.otp_status.append(status_msg)
            if 'is successful' in status_msg.lower() or 'successful' in status_msg.lower():
                parsed_data.key_provisioning.success_messages.append(status_msg)

        # Final device state — mode-agnostic
        # JTAG format: "Device is in HS_KP state" / "Device is in HS-KP state"
        # UART SoC-ID format: "Device type : EMU_KP (Key Provisioned)"
        final_state_match = re.search(r'Device is in (HS[_-]KP|HS[_-]SE) state', log_text, re.IGNORECASE)
        if final_state_match:
            state = final_state_match.group(1).upper().replace('-', '_')
            parsed_data.key_provisioning.final_state = 'HSKP' if state == 'HS_KP' else 'HSSE'
        else:
            soc_id_match = re.search(r'Device type\s*:\s*EMU_(KP|SE)', log_text, re.IGNORECASE)
            if soc_id_match:
                code = soc_id_match.group(1).upper()
                parsed_data.key_provisioning.final_state = 'HSKP' if code == 'KP' else 'HSSE'
    except Exception as e:
        logger.error(f"Error parsing key provisioning logs: {str(e)}")
        parsed_data.errors.append(f"Error parsing key provisioning logs: {str(e)}")


def parse_code_provisioning_logs(log_text: str, parsed_data: LogData) -> None:
    """Parse the code provisioning specific sections of the logs.
    
    Args:
        log_text: The full log text
        parsed_data: LogData object to store parsed data (will be modified in place)
    
    Returns:
        None, modifies parsed_data in place
    """
    try:
        # Check if we can find code provisioning logs marker
        code_start_index = log_text.find('!! HSM Run Time Loading is successful !!')
        code_log_text = log_text
        
        if code_start_index == -1:
            # Try alternative markers
            code_start_index = log_text.find('HSM Run Time Code Provisioning')
        
        # If we found a marker, use only the logs after that point for code provisioning
        if code_start_index > 0:
            code_log_text = log_text[code_start_index:]
        
        # Check for failure messages first
        failure_patterns = [
            r'!! SecCfg Loading FAILED !!',
            r'!! SecCfg CPU \d+ CertProcess FAILED !!',
            r'!! HSM Run Time Loading FAILED !!',
            r'!! HSM Run Time Code Provisioning FAILED !!',
            r'!! C29 CPU1 Code Provisioning FAILED !!',
            r'!! C29 CPU3 Code Provisioning FAILED !!',
            r'!! SecCfg programming FAILED !!',
        ]

        for pattern in failure_patterns:
            matches = re.finditer(pattern, code_log_text)
            for match in matches:
                failure_msg = match.group(0).strip('!').strip()
                if failure_msg not in parsed_data.errors:  # Avoid duplicates
                    parsed_data.errors.append(failure_msg)
                    logger.error(f"Code provisioning failure detected: {failure_msg}")

        # Extract code provisioning success messages.
        # NOTE: "HSM Run Time Loading is successful" is intentionally excluded — it also
        # appears in JTAG key provisioning logs (kernel load) and is not a CP completion marker.
        success_patterns = [
            # JTAG-format markers
            r'!! HSM Run Time Code Provisioning is successful !!',
            r'!! C29 CPU1 Code Provisioning is successful !!',
            r'!! C29 CPU3 Code Provisioning is successful !!',
            r'!! SecCfg programming successful !!',
            r'!! SecCfg Loading is successful\.',
            # UART-format markers (no !! prefix)
            r'HSM Flash Loading is successful\.',
            r'CPU APP Loading is successful\.',
            r'SecCfg Loading is successful\.',
        ]

        for pattern in success_patterns:
            if re.search(pattern, code_log_text):
                parsed_data.code_provisioning.success_messages.append(
                    re.sub(r'^!!?\s*|\s*!!?\.?$', '', pattern.replace(r'\.', '.').strip('!')).strip()
                )

        is_uart_cp = ('UART Firmware Programmer' in code_log_text or
                      'Serial Port:' in code_log_text or
                      'getPacket success' in code_log_text)

        if is_uart_cp:
            # UART CP: stages are delimited by "Executing command option N" markers.
            # Find each stage's segment and check for the success pattern within it.
            start_indices = [(name, code_log_text.find(start))
                             for name, start, _ in _UART_CP_STAGES]
            for i, (name, start, success_pat) in enumerate(_UART_CP_STAGES):
                if start_indices[i][1] < 0:
                    continue  # this option was not run
                seg_start = start_indices[i][1]
                # Segment ends at the next stage's start marker (or end of log)
                seg_end = len(code_log_text)
                for _, next_idx in start_indices[i + 1:]:
                    if next_idx > seg_start:
                        seg_end = next_idx
                        break
                segment = code_log_text[seg_start:seg_end]
                if re.search(success_pat, segment):
                    parsed_data.code_provisioning.stages[name] = CodeProvisioningStage(
                        progress=[], final_percentage=100,
                    )
        else:
            # JTAG CP: stages are marked by progress bars between start/end markers.
            progress_pattern = r'Progress: \[(#*)\s*\]\s*(\d+)%'
            stage_definitions = [
                {
                    "name": "HSM Run Time Code Provisioning is successful",
                    "start": "!! HSM Run Time Loading is successful !!",
                    "end":   "!! HSM Run Time Code Provisioning is successful !!",
                },
                {
                    "name": "C29 CPU1 Code Provisioning is successful",
                    "start": "!! HSM Run Time Code Provisioning is successful !!",
                    "end":   "!! C29 CPU1 Code Provisioning is successful !!",
                },
                {
                    "name": "C29 CPU3 Code Provisioning is successful",
                    "start": "!! C29 CPU1 Code Provisioning is successful !!",
                    "end":   "!! C29 CPU3 Code Provisioning is successful !!",
                },
            ]

            all_progress = []
            for stage_def in stage_definitions:
                start_idx = code_log_text.find(stage_def["start"])
                end_idx   = code_log_text.find(stage_def["end"])
                if start_idx < 0 or end_idx < 0 or end_idx <= start_idx:
                    continue
                segment = code_log_text[start_idx:end_idx]
                entries = [
                    {'bar': m.group(1), 'percentage': int(m.group(2))}
                    for m in re.finditer(progress_pattern, segment)
                ]
                if not entries:
                    continue
                all_progress.extend(entries)
                parsed_data.code_provisioning.stages[stage_def["name"]] = CodeProvisioningStage(
                    progress=entries,
                    final_percentage=entries[-1]['percentage'],
                )

            parsed_data.code_provisioning.progress = all_progress
    except Exception as e:
        logger.error(f"Error parsing code provisioning logs: {str(e)}")
        parsed_data.errors.append(f"Error parsing code provisioning logs: {str(e)}")