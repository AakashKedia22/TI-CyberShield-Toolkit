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
A session is an abstraction that contains the password protected keys stored in the disk.
These keys are customer keys like SMEK, SMPK (private), BMEK and BMPK (private) which is
burned into the OTP area of the SoC. The session is stored in an application specific
directory in the user's home directory and can be given a name and description chosen
by the user, which is referred to later in the certificate generation phase. The user
needs to remember the session name and password that she used during the key generation
time to retrive these keys. If password is forgotten, the session is irretrievably lost
as it is stored at rest with strong encryption.
"""

import os
import base64
import json

from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Union

from appdirs import user_data_dir
from cryptography.fernet import Fernet

from tisecprov.crypto import derive_key
from tisecprov.cryptoutils import load_private_key
from tisecprov.crypto_interfaces import infer_signing_algorithm


class SecureSession:
    """
    SecureSession is responsible for creating, opening, saving and deleting
    sessions. Sessions are secure way to store keys and related data for a
    particular purpose into the disk. A user would start the provisioning
    process by generating keys and storing them into the session. Later invocations
    of key manipulation would never refer to any file paths of keys. Instead
    they would only refer to session names.
    """

    def __init__(
        self,
        storage_path: Path | None = None,
        use_hsm: bool = False,
        in_memory: bool = False,
    ) -> None:
        """
        Initialize the secure session manager.

        Args:
            storage_path: Directory to store the session files.
        """
        self.hsm = use_hsm
        self.in_memory = in_memory
        self.current_session: Dict[str, object] | None = None
        self.hsm_session = None
        self.memory_sessions: Dict[str, Dict] = {}

        if self.hsm:
            try:
                import pkcs11
                from pkcs11 import KeyType, ObjectClass, Mechanism
                from tisecprov.hsm_crypto import get_pkcs11_lib, HSMRSAPrivateKey

                # Initialize PKCS11 library Globally
                globals()["KeyType"] = KeyType
                globals()["ObjectClass"] = ObjectClass
                globals()["pkcs11"] = pkcs11
                globals()["HSMRSAPrivateKey"] = HSMRSAPrivateKey
                globals()["get_pkcs11_lib"] = get_pkcs11_lib
            except ImportError as e:
                raise RuntimeError(
                    "The 'pkcs11' library is required for HSM functionality. "
                    "Please install it using the optional dependency: "
                    "`pip install tisecprov[hsm]`"
                ) from e

        # Set default storage path to XDG_DATA_HOME/secure_Provisioning_Tool/sessions
        # (overridable with the TISECPROV_SESSION_DIR environment variable)
        appname = os.path.join("tisecprov", "sessions")
        app_author = "tisecprov"
        if storage_path is None:
            override = os.environ.get("TISECPROV_SESSION_DIR")
            if override:
                storage_path = Path(override)
            else:
                storage_path = Path(user_data_dir(appname, app_author))

        storage_path.mkdir(parents=True, exist_ok=True)
        self.storage_path = storage_path
        self.fernet: Fernet | None = None

    def __enter__(self) -> "SecureSession":
        return self

    def __exit__(
        self,
        exc_type: Optional[type],
        exc_value: Optional[BaseException],
        traceback: Optional[object],
    ) -> None:
        self.close_session()

    def does_session_exist(self, session_name: str) -> bool:
        """
        Check if the session with the given name exists.
        """
        if self.in_memory:
            return session_name in self.memory_sessions

        session_file = self.storage_path / f"{session_name}.session"
        return session_file.exists()

    def create_session(self, name: str, description: str, password: str) -> str:
        """
        Create a session with the given name and description.

        Args:
            name: Session name.
            description: Description of what the session is about.
            password: Password to encrypt the session.
        Returns:
            Session ID.
        Raises:
            RuntimeError: If the session already exists.
        """
        if not self.hsm and self.does_session_exist(name):
            raise RuntimeError(f"Session {name} already exists")

        session_id = base64.urlsafe_b64encode(os.urandom(24)).decode("ascii")

        if self.in_memory:
            session_data = {
                "id": session_id,
                "name": name,
                "description": description,
                "created_at": datetime.now().isoformat(),
                "keys": {},
                "password": password,
            }
            self.memory_sessions[name] = session_data
            return session_id

        key, salt = derive_key(password)

        # TODO: modify such that description/name is not encrypted.
        session_data = {
            "id": session_id,
            "name": name,
            "description": description,
            "created_at": datetime.now().isoformat(),
            "keys": {},
        }
        session_data_json = json.dumps(session_data).encode()
        fernet = Fernet(key)

        encrypted_data = {
            "salt": base64.b64encode(salt).decode("ascii"),
            "data": base64.b64encode(fernet.encrypt(session_data_json)).decode("ascii"),
        }

        session_file = self.storage_path / f"{name}.session"
        session_file.write_text(json.dumps(encrypted_data))

        return session_id

    def save_session(self) -> None:
        """
        save the current session into the session file.
        """
        if not self.current_session:
            raise RuntimeError("No session is currently open")

        if self.in_memory:
            self.memory_sessions[self.current_session["name"]] = self.current_session
            return

        if not self.fernet:
            raise RuntimeError("No encryption key available for disk-based session")

        encrypted_data = self.fernet.encrypt(json.dumps(self.current_session).encode())

        # create a temporary file
        session_file_tmp = self.storage_path / f"{self.current_session['name']}.tmp"

        # read back the saved session and get the salt
        # read the current session file
        session_file = self.storage_path / f"{self.current_session['name']}.session"
        session_data = json.loads(session_file.read_text())

        # write the encrypted data
        session_data["data"] = base64.b64encode(encrypted_data).decode("ascii")
        session_file_tmp.write_text(json.dumps(session_data))

        # remove the old existing file
        if session_file.exists():
            session_file.unlink()

        # rename the temporary file
        session_file_tmp.rename(
            self.storage_path / f"{self.current_session['name']}.session"
        )

    def list_sessions(self) -> List[Dict]:
        """
        List all available session with basic metadata.
        """
        if self.in_memory:
            return [
                {"name": name, "path": "memory://" + name}
                for name in self.memory_sessions.key()
            ]
        sessions = []
        for session_file in self.storage_path.glob("*.session"):
            session_name = (
                session_file.stem
            )  # the filename part alone without extension.

            sessions.append(
                {
                    "name": session_name,
                    "path": str(session_file),
                }
            )
        return sessions

    def open_session(self, session_name: str, password: str) -> Dict[str, object]:
        """Open an existing session using the provided password.

        Args:
            session_name: Session name to open
            password: Session password

        Returns:
            session_data: session_data is a dictionary containing the
            session data.

        Raises:
            RuntimeError: If the session does not exist or the password is incorrect.
        """
        if self.hsm:
            # Initialize PKCS#11 library
            lib = get_pkcs11_lib()
            try:
                print(f"opening PKCS#11 with token name: {session_name}")
                token = lib.get_token(token_label=session_name)
                self.hsm_session = token.open(user_pin=password, rw=True)
            except pkcs11.exceptions.NoSuchToken as e:
                raise RuntimeError(
                    "Please mention token name as the session name and user pin as password"
                ) from e

        if self.in_memory:
            if session_name not in self.memory_sessions:
                raise RuntimeError(f"Session {session_name} does not exist")

            session = self.memory_sessions[session_name]
            if session["password"] != password:
                raise RuntimeError("Invalid password")

            self.current_session = session
            return session

        session_file = self.storage_path / f"{session_name}.session"
        if not self.does_session_exist(session_name):
            raise RuntimeError(f"Session {session_name} does not exist")

        try:
            # load the session file.
            encrypted_data: Dict[str, str] = json.loads(session_file.read_text())

            # get salt
            salt = base64.b64decode(encrypted_data["salt"])

            # derive the key
            key, _ = derive_key(password, salt)
            self.fernet = Fernet(key)

            # decrypt the session data
            encrypted_session = base64.b64decode(encrypted_data["data"])
            decrypted_data = self.fernet.decrypt(encrypted_session)
            self.current_session = json.loads(decrypted_data)
            return self.current_session
        except json.JSONDecodeError as exc:
            print("corrupted session file")
            raise RuntimeError("Corrupt session file") from exc
        except Exception as e:
            raise RuntimeError(
                "invalid password or corrupt session file: " + str(e)
            ) from e

    def close_session(self) -> None:
        """
        Close the currently open session.
        """
        if self.hsm and self.hsm_session is not None:
            self.hsm_session = self.hsm_session.close()
        self.current_session = None
        self.fernet = None

    def delete_session(self, session_name: str) -> None:
        """
        Delete the session by deleting the file associated with the named session.
        """
        print(f"deleting the session {session_name}")
        if self.in_memory:
            self.memory_sessions.pop(session_name, None)
            return

        if not self.hsm and self.does_session_exist(session_name):
            # delete the session file
            session_file_path = self.storage_path / f"{session_name}.session"
            os.remove(session_file_path)

    def key_exists(self, key_name: str) -> bool:
        """
        Check if the key with the given exists in the current session.
        """
        if not self.current_session or not self.fernet:
            raise RuntimeError("No session is currently open")

        return self.current_session["keys"].get(key_name, None) is not None

    def _add_key(self, key_name: str, key_value: bytes) -> None:
        """
        Helper method to add a key to the current session.

        Args:
            key_name: Name of the key to add.
            key_value: Value of the key to add.

        Raises:
            ValueError: If no session is currently open or if the key name is invalid.
        """
        if not self.current_session:
            raise ValueError("No session is currently open")

        if not self.in_memory and not self.fernet:
            raise ValueError("No encryption key available for disk-based session")

        valid_keys = ["aes_key", "smek", "bmek", "smpk_priv", "bmpk_priv"]
        if key_name not in valid_keys:
            raise ValueError(f"Invalid key name: {key_name}")

        self.current_session["keys"][key_name] = {
            "value": base64.b64encode(key_value).decode("ascii"),
            "added_at": datetime.now().isoformat(),
        }

        # save the current session with the new key
        self.save_session()

    def add_meks(self, key_dict: Dict[str, bytes]) -> None:
        """
        Add manufacturer encryption keys into current session.

        Args:
            key_dict: key value pairs for each key to be added

        Raises:
            ValueError: If not session is currently open or if
            invalid key name.
        """
        for key_name, key_value in key_dict.items():
            self._add_key(key_name, key_value)

    def add_smek(self, smek: bytes) -> None:
        """
        Add SM encryption key to the current session.

        Args:
            smek: SM encryption key

        Raises:
            ValueError: If no session is currently open.
        """
        self._add_key("smek", smek)

    def add_bmek(self, bmek: bytes) -> None:
        """
        Add BM encryption key to the current session.

        Args:
            bmek: BM encryption key

        Raises:
            ValueError: If no session is currently open.
        """
        self._add_key("bmek", bmek)

    def add_mprivs(self, key_dict: Dict[str, bytes]) -> None:
        """
        Add manufacturer private keys into current session.

        Args:
            key_dict: key value pairs for each key to be added

        Raises:
            ValueError: If not session is currently open or if
            invalid key name.
        """
        for key_name, key_value in key_dict.items():
            self._add_key(key_name, key_value)

    def add_smpk_priv(self, smpk_priv: bytes) -> None:
        """
        Add Secondary Manufacturer private key to the current session.

        Args:
            smpk_priv: SM private key

        Raises:
            ValueError: If no session is currently open.
        """
        self._add_key("smpk_priv", smpk_priv)

    def add_bmpk_priv(self, bmpk_priv: bytes) -> None:
        """
        Add BM private key to the current session.

        Args:
            bmpk_priv: BM private key

        Raises:
            ValueError: If no session is currently open.
        """
        self._add_key("bmpk_priv", bmpk_priv)

    def get_private_key(self, key_type: str):
        """
        Get a manufacturer private key from the session.

        The key type (RSA vs EC) is detected automatically from the
        stored PEM/DER bytes — no algorithm string is needed.

        Args:
            key_type: 'smpk_priv' or 'bmpk_priv'

        Returns:
            The loaded private key (RSA or EC)

        Raises:
            ValueError: If no session is open or when key does not exist.
        """
        if self.hsm:
            key_to_label = {
                "smpk_priv": "SMKEYS",
                "bmpk_priv": "BMKEYS",
            }
            label = key_to_label.get(key_type, None)
            if label is None:
                raise ValueError(f"cannot find the label for {key_type}")

            private_key = self.hsm_session.get_key(
                key_type=KeyType.RSA,
                object_class=ObjectClass.PRIVATE_KEY,
                label=label,
            )
            public_key = self.hsm_session.get_key(
                key_type=KeyType.RSA,
                object_class=ObjectClass.PUBLIC_KEY,
                label=label,
            )
            return HSMRSAPrivateKey(private_key, public_key)

        if not self.current_session:
            raise ValueError("No active session")

        if key_type not in self.current_session["keys"]:
            raise ValueError(f"{key_type} not found in session")

        return load_private_key(self.get_key(key_type))

    def get_key(self, key_name: str) -> bytes:
        """
        Get the key corresponding to the given key_name.

        Returns:
            bytes: key value as bytes

        Raises:
            ValueError: if no session is open or when key does not exist.
        """
        if not self.current_session:
            raise ValueError("No active session")

        if key_name not in self.current_session["keys"]:
            raise ValueError(f"Key {key_name} not found in session")

        return base64.b64decode(self.current_session["keys"][key_name]["value"])


    def get_manufacturer_keys(self, crypto_backend):
        """Return [sm_keys, bm_keys] ManufacturerKeys from the current session.

        Centralises key extraction so every caller gets correctly-paired
        keys with the right per-key algorithm.  The signing algorithm is
        inferred from the private key itself — no stored algorithm string
        is needed.
        """
        if self.hsm_session:
            wrapped_smek = self.get_key("smek")   # RSA-wrapped blob (512 bytes)
            wrapped_bmek = self.get_key("bmek")
            return [
                crypto_backend(session=self, label="SMKEYS", wrapped_symmetric_key=wrapped_smek),
                crypto_backend(session=self, label="BMKEYS", wrapped_symmetric_key=wrapped_bmek),
            ]

        smek = self.get_key("smek")
        smpk_priv = self.get_private_key("smpk_priv")
        smpk_algo = infer_signing_algorithm(smpk_priv)

        bmek = self.get_key("bmek")
        bmpk_priv = self.get_private_key("bmpk_priv")
        bmpk_algo = infer_signing_algorithm(bmpk_priv)

        return [
            crypto_backend(smek, smpk_priv, smpk_algo),
            crypto_backend(bmek, bmpk_priv, bmpk_algo),
        ]