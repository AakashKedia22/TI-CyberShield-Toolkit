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

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import os

def read_sym_key(key_file_path):
    """
    Reads an AES key from a specified file.

    Args:
        key_file_path (str): The path to the file containing the AES key.

    Returns:
        bytes: The AES key as a bytes object, or None if the file cannot be read.
    """
    try:
        with open(key_file_path, 'rb') as key_file:
            aes_key = key_file.read()
            return aes_key
    except FileNotFoundError:
        print(f"Error: Key file not found at '{key_file_path}'")
        return None
    except Exception as e:
        print(f"An error occurred while reading the key file: {e}")
        return None

# Example usage:
# key_filename = 'aes.key'
# key = read_aes_key(key_filename)

# if key:
#     print(f"AES Key read successfully: {key.hex()}")
#     # You can now use 'key' for AES encryption/decryption operations
# else:
#     print("Failed to read AES key.")


def read_private_key(path, password=None):
    """
    Reads a private key from a PEM file.

    Args:
        path: The path to the PEM file.
        password: The password to decrypt the key (optional).

    Returns:
        A cryptography.hazmat.primitives.asymmetric.rsa.RSAPrivateKey or
        cryptography.hazmat.primitives.asymmetric.ec.EllipticCurvePrivateKey object.

    Raises:
        FileNotFoundError: If the file does not exist.
        Exception: If the key cannot be loaded due to an invalid format or password.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")

    with open(path, "rb") as key_file:
        try:
            private_key = serialization.load_pem_private_key(
                key_file.read(),
                password=password,
                backend=default_backend()
            )
            return private_key
        except Exception as e:
            raise Exception(f"Error loading private key: {e}")

# Example usage:
# key_path = "path/to/your/private_key.pem"
# try:
#     private_key = read_private_key(key_path, password=b"your_password")  # Replace with actual password if encrypted
#     print(f"Successfully loaded private key from {key_path}")
#     # You can now use the private_key object for cryptographic operations
# except FileNotFoundError as e:
#     print(f"Error: {e}")
# except Exception as e:
#     print(f"Error: {e}")

def load_develop_keys(algorithm_smpk: str = "rsa4k",algorithm_bmpk: str = "rsa4k"):   
    script_dir = str(os.path.dirname(__file__)) + "/"
    smpk_private_key = read_private_key(script_dir + algorithm_smpk +  "/smpk.pem",password=None)
    bmpk_private_key = read_private_key(script_dir + algorithm_bmpk +  "/bmpk.pem",password=None)
    aes_key = read_sym_key(script_dir + "/aes256.key")
    smek_key = read_sym_key(script_dir + "/smek.key")
    bmek_key = read_sym_key(script_dir + "/bmek.key")
    return [smek_key, smpk_private_key, bmek_key, bmpk_private_key, aes_key]
