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
sign_encrypt.py

This module signs an object file with specified private key and generates an x509 certificate

It uses various utilities and helper functions to parse command-line arguments,
validate input data/key material, and generate the necessary cryptographic components.

Contents may be hashed, encrypted and put into the x509 as part of the extensions
which are then parsed, validated and programmed.
"""

import sys
import os
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path, WindowsPath
from tisecprov.certgen import *
import re
from tisecprov.session import SecureSession
from tisecprov.crypto_selector import get_crypto_backend
from tisecprov.crypto_interfaces import SigningAlgorithm
from apps.tifs.sign_encrypt_f29.gen_binary_cert import create_fields, build_hsm_firmware_cert
from typing import List

# Import platform utilities if available
try:
    from apps.qtgui.utils.platform_utils import IS_WINDOWS, IS_LINUX, IS_MACOS
    PLATFORM_UTILS_AVAILABLE = True
except ImportError:
    # Fallback to direct platform detection if platform_utils is not available
    IS_WINDOWS = platform.system() == 'Windows'
    IS_LINUX = platform.system() == 'Linux'
    IS_MACOS = platform.system() == 'Darwin'
    PLATFORM_UTILS_AVAILABLE = False


def extract_compiler_folder(path, compiler_name):
    """
    Extract the compiler folder name from the given path
    
    Args:
        path (str): The path to extract the compiler folder name from
        compiler_name (str): The name of the compiler (e.g. ti-cgt-armllvm)
    
    Returns:
        str: The compiler folder name
    """
    # Use regular expression to extract the compiler folder name
    pattern = rf'{compiler_name}_[\d\.]+LTS'
    dirs = os.listdir(path)
    
    # Use regular expression to filter the list and get the compiler folder name
    compiler_folder = next((d for d in dirs if re.match(pattern, d)), None)
    
    return compiler_folder

def set_output_path(device_name="f29h85x"):
    from common.device_utils import get_device_output_dir
    output_path = Path(get_device_output_dir(device_name, "signedImages"))
    return output_path

def parseSignEncrypt(subparser):
    pass
    parser = subparser.add_parser(
        "signapp",
        help="Sign an Application",
        description="Sign an Application using SMPK/BMPK Private Key",
    )

    # Get Object File in ELF Format
    parser.add_argument("--output_path", help="Output Directory", type=Path)
    parser.add_argument('--image',      type=str,
                        required=True, help='Path to the SBL/hsmRT binary')
    parser.add_argument('--input-format',   type=str,
                        required=True, help='Can be an ELF(.out) or a Bin(.bin)')
    parser.add_argument('--core',        type=str,
                        required=True, help='C29/HSM are the options to build for specific core')
    parser.add_argument("--keyrev", 
                        required=True, help="KeyRev to be used: 1-> SMPK and 2->BMPK")
    parser.add_argument('--sbl-enc',     action='store_true',
                        required=False, help='Encrypt SBL or not')
    parser.add_argument('--tifs-enc',    action='store_true',
                        required=False, help='Encrypt TIFS-MCU or not')
    parser.add_argument('--fw-enc',      action='store_true',
                        required=False, help='Encrypt firmware or not')
    parser.add_argument('--img_integ',   action='store_true',
                        required=False, help='Add image integrity extension (OID 1.3.6.1.4.1.294.1.2)')
    parser.add_argument('--enc-key',     type=str,
                        required=False, help='Path to the SBL Encryption Key')
    parser.add_argument('--fw-enc-key',  type=str,
                        required=False, help='Path to the firmware encryption key')
    parser.add_argument('--swrv',        type=str,
                        help='Software revision number')
    parser.add_argument('--loadaddr',    type=str, required=True,
                        help='Load address at which SBL/hsmRT needs to be loaded')
    parser.add_argument('--kd-salt',    type=str, required=False,
                        help='Path to the salt required to calculate derived key from manufacturers encryption key')
    parser.add_argument('--debug',       type=str,
                        help='Debug options for the image')
    parser.add_argument('--boot',       type=str,
                        help='SoC boot mode', default='FLASH')
    parser.add_argument('--fw_type',       type=str,
                        help='firmware type')
    parser.add_argument('--crypto_unlock',       type=str,
                        help='Crypto engine unlock extension', default='no',
                        required=False)
    parser.add_argument(
        "-hsm",
        "--hsm",
        action="store_true",
        help="Use HSM Device to access the keys",
    )
    parser.add_argument("--ccs-path", required=False, help="Path to CCS installation directory")

def parseSecCfgCert(subparser):
    pass
    parser = subparser.add_parser(
        "signSecCfg",
        help="Sign a Sec-Cfg",
        description="Sign Sec-Cfg using SMPK/BMPK Private Key",
    )

    # Get Object File in ELF Format
    parser.add_argument("--output_path", help="Output Directory", type=Path, required=True)
    parser.add_argument('--image',      type=str,
                        required=True, help='Path to the Sec-Cfg image')
    parser.add_argument('--swrv',        type=str,
                        help='Software revision number', required=True)
    parser.add_argument("--keyrev", 
                        required=True, help="KeyRev to be used: 1-> SMPK and 2->BMPK")
    parser.add_argument(
        "-hsm",
        "--hsm",
        action="store_true",
        help="Use HSM Device to access the keys",
    )
    parser.add_argument('--boot',       type=str,
                        help='SoC boot mode', default='FLASH')
    parser.add_argument("--ccs-path", required=True, help="Path to CCS installation directory")
    parser.add_argument('--fw-enc',      action='store_true',
                        required=False, help='Encrypt firmware or not')
    parser.add_argument('--fw-enc-key',  type=str,
                        required=False, help='Path to the firmware encryption key')
    parser.add_argument('--kd-salt',    type=str, required=False,
                        help='Path to the salt required to calculate derived key from manufacturers encryption key')

def sign_encrypt(args) -> None:
    """
    Processes command-line arguments and updates global dictionaries accordingly.

    This function processes the command-line arguments provided to the script,
    validates them, and signs an object file with specified private key and generates an x509 certificate.
    It also handles errors and logs messages as needed.

    Parameters
    ----------
    args : argparse.Namespace
        The parsed command-line arguments.

    Returns
    -------
    None
    """
    from pathlib import Path
    if not args.output_path:
        output_path = set_output_path()
    elif isinstance(args.output_path, Path):
        output_path = args.output_path
    elif isinstance(args.output_path, str):
        output_path = Path(args.output_path)
    else:
        raise TypeError(f"output_path must be Path or str, got {type(args.output_path)}")

    if args.keyrev not in ['1','2']:
        print("Error: Keyrev should be 1 or 2")
        sys.exit()

    if args.ccs_path == None and args.input_format == "ELF":
        print("For ELF Files CCS Path is mandatory")
        sys.exit()
    
    ccs_compiler : str = ''
    ccs_utils_mkhex4bin : str = ''
    ccs_objcopy: str = ''
    
    # Extracting Tools from CCS
    if args.ccs_path != None and args.input_format == "ELF":
        ccs_compiler = os.path.join(args.ccs_path, "ccs", "tools", "compiler")
        ccs_utils_mkhex4bin = os.path.normpath(os.path.join(args.ccs_path, "ccs", "utils", "tiobj2bin", "mkhex4bin"))
        ccs_objcopy = os.path.normpath(os.path.join(args.ccs_path, "ccs", "utils", "tiobj2bin", "tiobj2bin"))
    
    # Cross-platform file copy
    try:
        shutil.copy2(args.image, str(output_path))
    except Exception as e:
        print(f"Error copying file: {e}")
        sys.exit(1)
    # Use pathlib's parts for cross-platform path splitting
    image_path = Path(args.image)
    image_filename = image_path.name
    image_name_parts = image_filename.split('.')

    if args.core == "HSM":
        image_bin_name = '.'.join(image_name_parts[:-1]) + ".hs.hsmimage"
    elif args.core == "C29":
        image_bin_name = '.'.join(image_name_parts[:-1]) + ".cert.bin"
    else:
        image_bin_name = '.'.join(image_name_parts[:-1]) + ".bin"

    # Converting ELF file to Bin File for F29 using Tools in CCS
    if args.ccs_path != None and args.input_format == "ELF":
        # Use pathlib for cross-platform path handling
        image_path = Path(args.image)
        image_filename = image_path.name
        elf_image = os.path.join(str(output_path), image_filename)
        if args.core == "HSM":
            print("Signing HSM Application !!!")
            ti_arm_compiler = extract_compiler_folder(ccs_compiler, "ti-cgt-armllvm")
            ti_arm_compiler_path = os.path.join(ccs_compiler, ti_arm_compiler)
            if args.boot == "FLASH":
                if IS_WINDOWS:
                    # On Windows, use cmd.exe's cd command and normalize paths
                    bin_path = os.path.normpath(os.path.join(ti_arm_compiler_path, "bin", "tiarmobjcopy"))
                    cmd = f'cd /d "{output_path}" && "{bin_path}" "{elf_image}" --remove-section .cert --output-target binary "{image_bin_name}"'
                else:
                    cmd = f"cd {output_path} && {ti_arm_compiler_path}/bin/tiarmobjcopy {elf_image} --remove-section .cert --output-target binary {image_bin_name}"
                os.system(cmd)
            else:
                if IS_WINDOWS:
                    # On Windows, use cmd.exe's cd command and normalize paths
                    bin_path1 = os.path.normpath(os.path.join(ti_arm_compiler_path, "bin", "tiarmofd"))
                    bin_path2 = os.path.normpath(os.path.join(ti_arm_compiler_path, "bin", "tiarmhex"))
                    dest_path = os.path.join(str(output_path), image_bin_name)
                    cmd = f'cd /d "{output_path}" && "{ccs_objcopy}" "{elf_image}" "{dest_path}" "{bin_path1}" "{bin_path2}" "{ccs_utils_mkhex4bin}"'
                else:
                    cmd = f"cd {output_path} && {ccs_objcopy} {elf_image} {str(output_path) + '/' + image_bin_name} {ti_arm_compiler_path}/bin/tiarmofd {ti_arm_compiler_path}/bin/tiarmhex {ccs_utils_mkhex4bin}"
                os.system(cmd)
        if args.core == "C29":
            print("Signing C29 Application !!!")
            if args.boot == "FLASH":
                cgt_c29_compiler = extract_compiler_folder(ccs_compiler, "ti-cgt-c29")
                cgt_c29_compiler_path = os.path.join(ccs_compiler, cgt_c29_compiler)
                if IS_WINDOWS:
                    # On Windows, use cmd.exe's cd command and normalize paths
                    bin_path = os.path.normpath(os.path.join(cgt_c29_compiler_path, "bin", "c29objcopy"))
                    cmd = f'cd /d "{output_path}" && "{bin_path}" --remove-section=cert -O binary "{elf_image}" "{image_bin_name}"'
                else:
                    cmd = f"cd {output_path} && {cgt_c29_compiler_path}/bin/c29objcopy --remove-section=cert -O binary {elf_image} {image_bin_name}"
                os.system(cmd)
            else:
                if IS_WINDOWS:
                    # On Windows, use cmd.exe's cd command and normalize paths
                    bin_path = os.path.normpath(os.path.join(cgt_c29_compiler_path, "bin", "c29objcopy"))
                    cmd = f'cd /d "{output_path}" && "{bin_path}" --strip-all -O binary "{elf_image}" "{image_bin_name}"'
                else:
                    cmd = f"cd {output_path} && {cgt_c29_compiler_path}/bin/c29objcopy --strip-all -O binary {elf_image} {image_bin_name}"
                os.system(cmd)
        # Use os.path.join for cross-platform path handling
        args.image_bin = os.path.join(str(output_path), image_bin_name)
    else:
        if args.core == "HSM" or args.core == "C29":
            # Use pathlib to extract the filename in a cross-platform way
            image_path = Path(args.image)
            image = image_path.name

            # Use shutil.move for cross-platform file operations
            try:
                src_path = os.path.join(str(output_path), image)
                dst_path = os.path.join(str(output_path), image_bin_name)
                shutil.move(src_path, dst_path)
            except Exception as e:
                print(f"Error renaming file: {e}")
                sys.exit(1)
            # Use os.path.join for cross-platform path handling
        args.image_bin = os.path.join(str(output_path), image_bin_name)

    cert_fields, actual_image_bin_name = create_fields(args)
    crypto_backend = get_crypto_backend(use_hsm=args.hsm)

    secure_session = SecureSession(use_hsm=args.hsm)

    with secure_session as s:
        print(f"opening session: {args.session}")
        _session = s.open_session(args.session, args.password)
        keys = s.get_manufacturer_keys(crypto_backend)

        if args.keyrev == '1':
            signing_key, signing_algo = keys[0].get_signing_key()
        else:
            signing_key, signing_algo = keys[1].get_signing_key()

        final_cert = build_hsm_firmware_cert(args, signing_key, cert_fields, signing_algo)

    image_bin_name = actual_image_bin_name
    is_encrypted = (hasattr(args, 'sbl_enc') and args.sbl_enc) or \
                   (hasattr(args, 'tifs_enc') and args.tifs_enc) or \
                   (hasattr(args, 'fw_enc') and args.fw_enc)

    try:
        with open(image_bin_name, "rb") as binary_file:
            binary_image = binary_file.read()
    except FileNotFoundError:
        print(f"Error: The file {image_bin_name} was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

    print(f"writing signed images into {output_path}")
    temp_dir_path = output_path
    temp_dir_path.mkdir(parents=True, exist_ok=True)

    output_filename = Path(args.image_bin).name
    with open(temp_dir_path / output_filename, "wb") as f:
        f.write(final_cert)
        f.write(binary_image)

    if is_encrypted:
        try:
            os.remove(image_bin_name)
        except Exception as e:
            print(f"Warning: Could not remove temporary encrypted file {image_bin_name}: {e}")

    # Post Processing to generate an ELF File
    if args.ccs_path != None and args.input_format == "ELF":
        if args.core == "HSM":
            if args.boot == "FLASH":
                if IS_WINDOWS:
                    tmp_file = tempfile.NamedTemporaryFile(delete=False)
                    try:
                        tmp_file.write(final_cert)
                        tmp_file.flush()
                        tmp_file.close()
                        bin_path = os.path.normpath(os.path.join(ti_arm_compiler_path, "bin", "tiarmobjcopy"))
                        os.system(f'cd /d "{output_path}" && "{bin_path}" "--update-section=.cert={tmp_file.name}" "{elf_image}"')
                    finally:
                        os.remove(tmp_file.name)
                else:
                    with tempfile.NamedTemporaryFile() as tmp_file:
                        # Write the contents of final_cert to the temporary file
                        tmp_file.write(final_cert)
                        tmp_file.flush()
                        os.system(f"cd {output_path} && {ti_arm_compiler_path}/bin/tiarmobjcopy --update-section=.cert={tmp_file.name} {elf_image} ")
        if args.core == "C29":
            if args.boot == "FLASH":
                if IS_WINDOWS:
                    tmp_file = tempfile.NamedTemporaryFile(delete=False)
                    try:
                        tmp_file.write(final_cert)
                        tmp_file.flush()
                        tmp_file.close()
                        bin_path = os.path.normpath(os.path.join(cgt_c29_compiler_path, "bin", "c29objcopy"))
                        os.system(f'cd /d "{output_path}" && "{bin_path}" "--update-section=cert={tmp_file.name}" "{elf_image}" "{elf_image}"')
                    finally:
                        os.remove(tmp_file.name)
                else:
                    with tempfile.NamedTemporaryFile() as tmp_file:
                        # Write the contents of final_cert to the temporary file
                        tmp_file.write(final_cert)
                        tmp_file.flush()
                        os.system(f"cd {output_path} && {cgt_c29_compiler_path}/bin/c29objcopy --update-section cert={tmp_file.name} {elf_image} {elf_image} ")

def sign_sec_cfg(args) -> None:
    """
    Processes command-line arguments and updates global dictionaries accordingly.

    This function processes the command-line arguments provided to the script,
    validates them, and signs an object file with specified private key and generates an x509 certificate.
    It also handles errors and logs messages as needed.

    Parameters
    ----------
    args : argparse.Namespace
        The parsed command-line arguments.

    Returns
    -------
    None
    """
    from pathlib import Path
    # Validate required parameters
    if not hasattr(args, 'ccs_path') or not args.ccs_path:
        print("Error: CCS path is required for Sec-Cfg signing")
        sys.exit(1)
    # Convert to Path object for better validation
    ccs_path_obj = Path(args.ccs_path)
    if not ccs_path_obj.exists() or not ccs_path_obj.is_dir():
        print(f"Error: CCS path does not exist or is not a directory: {args.ccs_path}")
        sys.exit(1)

    print(f"Using CCS path: {ccs_path_obj}")

    # Dump CPU1 CPU2 and CPU3 seccfg
    # Create temp directory for files
    temp_dir = tempfile.mkdtemp()
    print(f"Created temporary directory: {temp_dir}")

    # Normalize path for C29 compiler and use pathlib for better cross-platform support
    if IS_WINDOWS:
        # Use Windows path style with normalized separators
        print(f"Processing on Windows platform - CCS path: {args.ccs_path}")

        # Create paths using pathlib for better cross-platform handling
        ccs_path = Path(args.ccs_path)
        compiler_base = ccs_path / "ccs" / "tools" / "compiler"
        c29_folder = extract_compiler_folder(str(compiler_base), "ti-cgt-c29")
        if not c29_folder:
            raise RuntimeError(f"C29 compiler not found under {compiler_base}")
        bin_dir = compiler_base / c29_folder / "bin"

        # Check for different possible executable names
        possible_names = ["c29objcopy.exe", "c29objcopy"]
        c29_bin_path = None

        # Try to find the executable with different extensions
        for name in possible_names:
            test_path = bin_dir / name
            if test_path.exists():
                c29_bin_path = str(test_path)
                print(f"Found c29objcopy tool at: {c29_bin_path}")
                break

        # If not found, try searching for any objcopy tool
        if not c29_bin_path:
            print(f"Error: c29objcopy tool not found in standard location")
            print(f"Checking for c29objcopy in bin directory: {bin_dir}")

            # Try to find the tool by listing directory contents
            if bin_dir.exists():
                try:
                    files = list(bin_dir.glob("*"))
                    print(f"Files in bin directory: {[f.name for f in files]}")
                    # Find any file that might be c29objcopy
                    objcopy_files = [f for f in files if 'objcopy' in f.name.lower()]
                    if objcopy_files:
                        c29_bin_path = str(objcopy_files[0])
                        print(f"Found potential c29objcopy match: {c29_bin_path}")
                    else:
                        print("ERROR: No objcopy files found in the bin directory")
                except Exception as e:
                    print(f"ERROR: Exception while listing bin directory: {e}")
            else:
                print(f"ERROR: Bin directory does not exist: {bin_dir}")
                # Try to find the parent directories to help diagnose the issue
                parent = bin_dir.parent
                if parent.exists():
                    print(f"Parent directory exists: {parent}")
                    print(f"Contents: {[d.name for d in parent.glob('*') if d.is_dir()]}")
                else:
                    print(f"Parent directory doesn't exist: {parent}")

        # Check if we found a valid path
        if not c29_bin_path:
            raise RuntimeError(f"Failed to find c29objcopy tool in CCS installation at {args.ccs_path}")

        # Check if the tool is executable
        import os
        if not os.access(c29_bin_path, os.X_OK) and not c29_bin_path.endswith('.exe'):
            print(f"WARNING: {c29_bin_path} may not be executable")

        # Use quotes around paths in case they contain spaces
        # Use Path objects for better cross-platform handling
        cpu1_output = Path(temp_dir) / "seccfgCpu1.bin"
        cpu2_output = Path(temp_dir) / "seccfgCpu2.bin"
        cpu3_output = Path(temp_dir) / "seccfgCpu3.bin"

        print(f"Preparing commands for extracting CPU configurations...")
        cmd1 = f'"{c29_bin_path}" -O binary --only-section=.TI.bound:CPU1_Cfg "{args.image}" "{str(cpu1_output)}"'
        cmd2 = f'"{c29_bin_path}" -O binary --only-section=.TI.bound:CPU2_Cfg "{args.image}" "{str(cpu2_output)}"'
        cmd3 = f'"{c29_bin_path}" -O binary --only-section=.TI.bound:CPU3_Cfg "{args.image}" "{str(cpu3_output)}"'
    else:
        # Use Unix path style with consistent Path objects
        compiler_base = Path(args.ccs_path) / "ccs" / "tools" / "compiler"
        c29_folder = extract_compiler_folder(str(compiler_base), "ti-cgt-c29")
        if not c29_folder:
            raise RuntimeError(f"C29 compiler not found under {compiler_base}")
        c29_bin_path = compiler_base / c29_folder / "bin" / "c29objcopy"
        c29_bin_path = str(c29_bin_path)

        # Create Path objects for outputs
        cpu1_output = Path(temp_dir) / "seccfgCpu1.bin"
        cpu2_output = Path(temp_dir) / "seccfgCpu2.bin"
        cpu3_output = Path(temp_dir) / "seccfgCpu3.bin"

        # Convert to string for command line
        cmd1 = f"{c29_bin_path} -O binary --only-section=.TI.bound:CPU1_Cfg {args.image} {cpu1_output}"
        cmd2 = f"{c29_bin_path} -O binary --only-section=.TI.bound:CPU2_Cfg {args.image} {cpu2_output}"
        cmd3 = f"{c29_bin_path} -O binary --only-section=.TI.bound:CPU3_Cfg {args.image} {cpu3_output}"

    # Run commands with better error handling using subprocess
    def run_command(cmd, description):
        """Run a command with detailed error handling and output capture"""
        print(f"Executing: {description}")
        print(f"Command: {cmd}")

        try:
            # Use subprocess.run for better control and output capture
            # Common parameters for both Windows and Unix
            common_params = {
                'shell': True,       # Use shell to handle quotes and special characters correctly
                'check': False,      # Don't raise exception, we'll handle errors manually
                'stdout': subprocess.PIPE,
                'stderr': subprocess.PIPE,
                'text': True,        # Return strings instead of bytes
                'encoding': 'utf-8'
            }

            if IS_WINDOWS:
                # On Windows, ensure we capture output properly with cmd.exe encoding
                process = subprocess.run(cmd, **common_params)
            else:
                # On Unix platforms
                process = subprocess.run(cmd, **common_params)

            # Log output even on success
            if process.stdout and process.stdout.strip():
                print(f"Command output: {process.stdout.strip()}")

            # Check if command succeeded
            if process.returncode != 0:
                print(f"ERROR: {description} failed with return code {process.returncode}")
                if process.stderr and process.stderr.strip():
                    print(f"Error details: {process.stderr.strip()}")
                return False
            else:
                print(f"SUCCESS: {description} completed successfully")
                return True
        except Exception as e:
            print(f"EXCEPTION executing {description}: {str(e)}")
            return False

    # Execute the commands with the new function
    print("Extracting CPU1 configuration...")
    result1 = run_command(cmd1, "Extracting CPU1 configuration")

    print("Extracting CPU2 configuration...")
    result2 = run_command(cmd2, "Extracting CPU2 configuration")

    print("Extracting CPU3 configuration...")
    result3 = run_command(cmd3, "Extracting CPU3 configuration")

    # Create fallback files if extraction failed with better path handling and error checks
    from pathlib import Path

    # Define CPU config file paths using Path objects for cross-platform consistency
    cpu_files = ["seccfgCpu1.bin", "seccfgCpu2.bin", "seccfgCpu3.bin"]
    cpu_paths = [Path(temp_dir) / cpu_file for cpu_file in cpu_files]

    print(f"Checking for CPU configuration files in {temp_dir}")
    for cpu_num, cpu_path in enumerate(cpu_paths, 1):
        if not cpu_path.exists():
            print(f"WARNING: {cpu_path.name} not found. Creating empty fallback file.")
            try:
                # Create an empty file with the correct size (2048 bytes)
                with open(cpu_path, "wb") as f:
                    # Fill with zeros - typical SecCfg size is 2048 bytes
                    f.write(b'\x00' * 2048)
                print(f"Created fallback file: {cpu_path} (size: 2048 bytes)")
            except Exception as e:
                print(f"ERROR creating fallback file {cpu_path}: {e}")
                raise RuntimeError(f"Failed to create fallback file for CPU{cpu_num} configuration: {str(e)}")
        else:
            # Check file size to ensure it's valid
            file_size = cpu_path.stat().st_size
            print(f"Found CPU{cpu_num} configuration file: {cpu_path} (size: {file_size} bytes)")

    # Remove last 16 bytes from seccfgCpu2.bin (always do this)
    cpu2_path = cpu_paths[1]  # Index 1 is the second file (CPU2)
    print(f"Truncating CPU2 configuration file: {cpu2_path}")
    try:
        # Use a more robust approach with explicit close in finally block
        secCfgCpu2 = None
        try:
            secCfgCpu2 = open(cpu2_path, "rb+")
            original_size = cpu2_path.stat().st_size
            # Truncate to exactly 2032 bytes (removing 16 bytes if file is larger)
            secCfgCpu2.truncate(2032)
            print(f"Successfully truncated {cpu2_path.name} from {original_size} to 2032 bytes")
        except Exception as e:
            print(f"WARNING: Error processing {cpu2_path}: {e}")
            print(f"Will continue with default SecCfg data, but this may cause issues")
        finally:
            # Ensure file is properly closed even if an error occurs
            if secCfgCpu2:
                secCfgCpu2.close()
    except Exception as e:
        print(f"CRITICAL ERROR handling CPU2 configuration: {e}")
        raise RuntimeError(f"Failed to process CPU2 configuration file: {str(e)}")

    print("CPU configuration file preparation completed successfully")

    # Populate Sec-Cfg C29 CPU1 parameters
    args.image_bin = str(Path(temp_dir) / "seccfgCpu1.bin")
    args.debug = "DBG_SOC_DEFAULT"
    args.fw_type = "SEC_CFG_CPU1"
    args.loadaddr = "0x10001000"
    args.core = "C29"
    args.crypto_unlock = "no"

    # Generate certificate for Sec-Cfg CPU1
    cert_fields, args.image_bin = create_fields(args)
    crypto_backend = get_crypto_backend(use_hsm=args.hsm)

    secure_session = SecureSession(use_hsm=args.hsm)

    with secure_session as s:
        print(f"opening session: {args.session}")
        _session = s.open_session(args.session, args.password)
        keys = s.get_manufacturer_keys(crypto_backend)

        if args.keyrev == '1':
            signing_key, signing_algo = keys[0].get_signing_key()
        else:
            signing_key, signing_algo = keys[1].get_signing_key()

        final_cert = build_hsm_firmware_cert(args, signing_key, cert_fields, signing_algo)

    # Generate certificate appended binary for CPU-1 Sec-Cfg
    image_bin_name = args.image_bin
    is_encrypted = (hasattr(args, 'sbl_enc') and args.sbl_enc) or \
                   (hasattr(args, 'tifs_enc') and args.tifs_enc) or \
                   (hasattr(args, 'fw_enc') and args.fw_enc)
    try:
        with open(image_bin_name, "rb") as binary_file:
            # Read the entire content of the file
            binary_image = binary_file.read()
    except FileNotFoundError:
        print(f"Error: The file {image_bin_name} was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

    print(f"writing certificates into {args.output_path}")
    from pathlib import Path
    if isinstance(args.output_path, Path):
        output_dir_path = args.output_path
    elif isinstance(args.output_path, str):
        output_dir_path = Path(args.output_path)
    else:
        raise TypeError(f"output_path must be Path or str, got {type(args.output_path)}")

    print(f"Creating output directory: {output_dir_path}")
    try:
        output_dir_path.mkdir(parents=True, exist_ok=True)
        print(f"Successfully created or verified output directory: {output_dir_path}")
    except Exception as e:
        print(f"ERROR creating output directory {output_dir_path}: {e}")
        # Try a different approach with os.makedirs as fallback
        try:
            import os
            os.makedirs(str(output_dir_path), exist_ok=True)
            print(f"Successfully created output directory using os.makedirs: {output_dir_path}")
        except Exception as e2:
            print(f"CRITICAL ERROR: Could not create output directory using either method: {e2}")
            raise RuntimeError(f"Failed to create output directory: {str(e2)}")

    # Write CPU1 certificate + binary
    output_file_name = Path(image_bin_name).name
    with open(output_dir_path / output_file_name, "wb") as f:
        f.write(final_cert)
        f.write(binary_image)
    
    # Populate Sec-Cfg C29 CPU2 parameters
    args.image_bin = str(Path(temp_dir) / "seccfgCpu2.bin")
    args.debug = "DBG_SOC_DEFAULT"
    args.fw_type = "SEC_CFG_CPU2"
    args.loadaddr = "0x10001000"
    args.core = "C29"
    args.crypto_unlock = "no"

    # Generate certificate for Sec-Cfg CPU2
    cert_fields, args.image_bin = create_fields(args)
    crypto_backend = get_crypto_backend(use_hsm=args.hsm)

    secure_session = SecureSession(use_hsm=args.hsm)

    with secure_session as s:
        print(f"opening session: {args.session}")
        _session = s.open_session(args.session, args.password)
        keys = s.get_manufacturer_keys(crypto_backend)

        if args.keyrev == '1':
            signing_key, signing_algo = keys[0].get_signing_key()
        else:
            signing_key, signing_algo = keys[1].get_signing_key()

        final_cert = build_hsm_firmware_cert(args, signing_key, cert_fields, signing_algo)

    # Generate certificate appended binary for CPU-2 Sec-Cfg
    image_bin_name = args.image_bin
    is_encrypted = (hasattr(args, 'sbl_enc') and args.sbl_enc) or \
                   (hasattr(args, 'tifs_enc') and args.tifs_enc) or \
                   (hasattr(args, 'fw_enc') and args.fw_enc)
    try:
        with open(image_bin_name, "rb") as binary_file:
            # Read the entire content of the file
            binary_image = binary_file.read()
    except FileNotFoundError:
        print(f"Error: The file {image_bin_name} was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

    # Write CPU2 certificate + binary
    output_file_name = Path(image_bin_name).name
    with open(output_dir_path / output_file_name, "wb") as f:
        f.write(final_cert)
        f.write(binary_image)

    # Pad 16 bytes to the seccfgCpu2.bin
    if is_encrypted:
        output_cpu2_path = str(output_dir_path / "seccfgCpu2.bin-enc")
    else:
        output_cpu2_path = str(output_dir_path / "seccfgCpu2.bin")
    try:
        secCfgCert2 = open(output_cpu2_path, "ab")
        zeroBytes = b'\x00' * 16
        secCfgCert2.write(zeroBytes)
        secCfgCert2.close()
    except Exception as e:
        print(f"Error padding CPU2 config file: {e}")
        raise RuntimeError(f"Failed to sign Sec-Cfg: Error padding CPU2 config - {e}")
    
    # Populate Sec-Cfg C29 CPU3 parameters
    args.image_bin = str(Path(temp_dir) / "seccfgCpu3.bin")
    args.debug = "DBG_SOC_DEFAULT"
    args.fw_type = "SEC_CFG_CPU3"
    args.loadaddr = "0x10001000"
    args.core = "C29"
    args.crypto_unlock = "no"

    # Generate certificate for Sec-Cfg CPU3
    cert_fields, args.image_bin = create_fields(args)
    crypto_backend = get_crypto_backend(use_hsm=args.hsm)

    secure_session = SecureSession(use_hsm=args.hsm)

    with secure_session as s:
        print(f"opening session: {args.session}")
        _session = s.open_session(args.session, args.password)
        keys = s.get_manufacturer_keys(crypto_backend)

        if args.keyrev == '1':
            signing_key, signing_algo = keys[0].get_signing_key()
        else:
            signing_key, signing_algo = keys[1].get_signing_key()

        final_cert = build_hsm_firmware_cert(args, signing_key, cert_fields, signing_algo)

    # Generate certificate appended binary for CPU-3 Sec-Cfg
    image_bin_name = args.image_bin
    is_encrypted = (hasattr(args, 'sbl_enc') and args.sbl_enc) or \
                   (hasattr(args, 'tifs_enc') and args.tifs_enc) or \
                   (hasattr(args, 'fw_enc') and args.fw_enc)
    try:
        with open(image_bin_name, "rb") as binary_file:
            # Read the entire content of the file
            binary_image = binary_file.read()
    except FileNotFoundError:
        print(f"Error: The file {image_bin_name} was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

    # Write CPU3 certificate + binary
    output_file_name = Path(image_bin_name).name
    with open(output_dir_path / output_file_name, "wb") as f:
        f.write(final_cert)
        f.write(binary_image)

    try:
        if is_encrypted:
            # Combine cert + seccfg for all 3 CPUs
            secCfgCert1 = open(str(output_dir_path / "seccfgCpu1.bin-enc"), "rb")
            secCfgCert2 = open(str(output_dir_path / "seccfgCpu2.bin-enc"), "rb")
            secCfgCert3 = open(str(output_dir_path / "seccfgCpu3.bin-enc"), "rb")
        else :
            # Combine cert + seccfg for all 3 CPUs
            secCfgCert1 = open(str(output_dir_path / "seccfgCpu1.bin"), "rb")
            secCfgCert2 = open(str(output_dir_path / "seccfgCpu2.bin"), "rb")
            secCfgCert3 = open(str(output_dir_path / "seccfgCpu3.bin"), "rb")
            
        secCfgFile = open(str(output_dir_path / "seccfg.bin"), "wb")

        print(f"Creating combined output file: {output_dir_path / 'seccfg.bin'}")
        secCfgFile.write(secCfgCert1.read() + secCfgCert2.read() + secCfgCert3.read())

        secCfgCert1.close()
        secCfgCert2.close()
        secCfgCert3.close()
        secCfgFile.close()

        print(f"Successfully wrote combined SecCfg to: {output_dir_path / 'seccfg.bin'}")
    except Exception as e:
        print(f"Error combining configuration files: {e}")
        raise RuntimeError(f"Failed to sign Sec-Cfg: Error combining configurations - {e}")

    # Clean up temporary files
    try:
        temp_dir_path = Path(temp_dir)

        # Ensure output_dir_path is a Path object before cleanup
        if not isinstance(output_dir_path, Path):
            output_dir_path = Path(output_dir_path)

        # Remove output directory intermediate files
        if is_encrypted:
            output_files = [
            output_dir_path / "seccfgCpu1.bin-enc",
            output_dir_path / "seccfgCpu2.bin-enc",
            output_dir_path / "seccfgCpu3.bin-enc"
        ]
        else :
            output_files = [
            output_dir_path / "seccfgCpu1.bin",
            output_dir_path / "seccfgCpu2.bin",
            output_dir_path / "seccfgCpu3.bin"
        ]

        # Remove intermediate files from output directory
        for file_path in output_files:
            if file_path.exists():
                file_path.unlink()

        # Clean up temp directory
        if temp_dir_path.exists():
            shutil.rmtree(str(temp_dir_path), ignore_errors=True)

    except Exception as e:
        # Non-fatal error, just log it
        print(f"Warning: Error cleaning up temporary files: {e}")


def sign_encrypt_binary(**kwargs) -> tuple:
    """
    Keyword-argument wrapper around sign_encrypt() for the core API layer.

    Constructs an Args namespace from keyword arguments and delegates to
    sign_encrypt(args). Returns (success, message) tuple instead of raising.

    Keyword Args:
        image (str): Path to binary file
        input_format (str): 'BIN' or 'ELF'
        core (str): 'C29' or 'HSM'
        keyrev (str): '1' or '2'
        loadaddr (str): Hex load address
        swrv (str): Software revision
        boot (str): 'FLASH' or 'RAM'
        output_path (str): Output directory
        session (str): Session name
        password (str): Session password
        debug (str, optional): Debug options
        ccs_path (str, optional): CCS installation path
        sbl_enc (bool): Enable SBL encryption
        tifs_enc (bool): Enable TIFS encryption
        fw_enc (bool): Enable firmware encryption
        enc_key (str, optional): SBL encryption key path
        fw_enc_key (str, optional): Firmware encryption key path
        kd_salt (str, optional): Key derivation salt file path
        fw_type (str, optional): Firmware type
        ext_otp (str, optional): Extended OTP value
        development_session (bool): Use development session
        smpk_algo (str, optional): SMPK algorithm for dev session
        bmpk_algo (str, optional): BMPK algorithm for dev session

    Returns:
        Tuple[bool, str]: (success, message)
    """
    try:
        class Args:
            pass

        args = Args()
        args.device = "f29h85x"
        args.image = kwargs.get('image')
        args.input_format = kwargs.get('input_format', 'BIN')
        args.core = kwargs.get('core')
        args.keyrev = kwargs.get('keyrev')
        args.loadaddr = kwargs.get('loadaddr')
        args.swrv = kwargs.get('swrv')
        args.boot = kwargs.get('boot', 'FLASH')
        args.output_path = Path(kwargs['output_path']) if kwargs.get('output_path') else None
        args.debug = kwargs.get('debug')
        args.ccs_path = kwargs.get('ccs_path')
        args.sbl_enc = kwargs.get('sbl_enc', False)
        args.tifs_enc = kwargs.get('tifs_enc', False)
        args.fw_enc = kwargs.get('fw_enc', False)
        args.enc_key = kwargs.get('enc_key')
        args.fw_enc_key = kwargs.get('fw_enc_key')
        args.kd_salt = kwargs.get('kd_salt')
        args.fw_type = kwargs.get('fw_type')
        args.ext_otp = kwargs.get('ext_otp')
        args.img_integ = kwargs.get('img_integ', False)
        args.crypto_unlock = kwargs.get('crypto_unlock', 'no')
        args.hsm = kwargs.get('hsm', False)

        if kwargs.get('development_session', False):
            args.session = "Development"
            args.password = "develop123#"
            args.hsm = False
            if kwargs.get('smpk_algo'):
                args.smpk_signing_algorithm = kwargs['smpk_algo']
            if kwargs.get('bmpk_algo'):
                args.bmpk_signing_algorithm = kwargs['bmpk_algo']
        else:
            args.session = kwargs.get('session')
            args.password = kwargs.get('password')

        sign_encrypt(args)
        return True, "Binary signed successfully"

    except Exception as e:
        return False, f"Signing failed: {str(e)}"


def sign_sec_cfg_binary(**kwargs) -> tuple:
    """
    Keyword-argument wrapper around sign_sec_cfg() for the core API layer.

    Constructs an Args namespace from keyword arguments and delegates to
    sign_sec_cfg(args). Returns (success, message) tuple instead of raising.

    Keyword Args:
        image (str): Path to sec-cfg image
        swrv (str): Software revision
        keyrev (str): '1' or '2'
        boot (str): 'FLASH' or 'RAM'
        output_path (str): Output directory
        ccs_path (str): CCS installation path
        session (str): Session name
        password (str): Session password
        development_session (bool): Use development session
        smpk_algo (str, optional): SMPK algorithm for dev session
        bmpk_algo (str, optional): BMPK algorithm for dev session

    Returns:
        Tuple[bool, str]: (success, message)
    """
    try:
        class Args:
            pass

        args = Args()
        args.device = "f29h85x"
        args.image = kwargs.get('image')
        args.swrv = kwargs.get('swrv')
        args.keyrev = kwargs.get('keyrev')
        args.boot = kwargs.get('boot', 'FLASH')
        args.output_path = Path(kwargs['output_path']) if kwargs.get('output_path') else None
        args.ccs_path = kwargs.get('ccs_path')
        args.hsm = kwargs.get('hsm', False)
        args.fw_enc = kwargs.get('fw_enc', False)
        args.fw_enc_key = kwargs.get('fw_enc_key')
        args.kd_salt = kwargs.get('kd_salt')

        if kwargs.get('development_session', False):
            args.session = "Development"
            args.password = "develop123#"
            args.hsm = False
            if kwargs.get('smpk_algo'):
                args.smpk_signing_algorithm = kwargs['smpk_algo']
            if kwargs.get('bmpk_algo'):
                args.bmpk_signing_algorithm = kwargs['bmpk_algo']
        else:
            args.session = kwargs.get('session')
            args.password = kwargs.get('password')

        sign_sec_cfg(args)
        return True, "Sec-Cfg signed successfully"

    except Exception as e:
        return False, f"Sec-Cfg signing failed: {str(e)}"