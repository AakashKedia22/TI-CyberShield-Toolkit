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

import pytest
import os
import base64
import json
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from tisecprov.session import SecureSession
from tisecprov.crypto import gen_aes256_key, FixedSizeBytes


@pytest.fixture(scope="function")
def secure_session(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("data")
    s = SecureSession(storage_path=tmp_path)
    print(f"storage_path: {s.storage_path}")
    session_name = "Test"
    session_id = s.create_session(session_name, "This is a test session", "password123")
    s.open_session(session_name, "password123")
    return s


def test_add_key_with_provided_value(secure_session):
    key = gen_aes256_key()
    secure_session.add_smek(key.data)

    assert "smek" in secure_session.current_session["keys"]
    assert (
        base64.b64encode(key.data).decode("ascii")
        == secure_session.current_session["keys"]["smek"]["value"]
    )
    assert isinstance(key, FixedSizeBytes)


def test_add_meks_with_provided_value(secure_session):
    smek, bmek = os.urandom(32), os.urandom(32)
    secure_session.add_smek(smek)
    secure_session.add_bmek(bmek)

    assert "smek" in secure_session.current_session["keys"]
    assert "bmek" in secure_session.current_session["keys"]
    assert (
        base64.b64encode(smek).decode("ascii")
        == secure_session.current_session["keys"]["smek"]["value"]
    )
    assert (
        base64.b64encode(bmek).decode("ascii")
        == secure_session.current_session["keys"]["bmek"]["value"]
    )


def test_add_key_no_session_open(tmp_path_factory):
    s = SecureSession(storage_path=tmp_path_factory.mktemp("data"))
    with pytest.raises(ValueError, match="No session is currently open"):
        key = gen_aes256_key().data
        s.add_smek(key)


def test_key_exists(secure_session):
    # Add a key to the session
    key = gen_aes256_key().data
    key_value = secure_session.add_smek(key)

    # Check if the key exists
    assert secure_session.key_exists("smek") == True

    # Check for a non-existent key
    assert secure_session.key_exists("non_existent_key") == False


def test_list_sessions(tmp_path_factory):
    s = SecureSession(storage_path=tmp_path_factory.mktemp("data"))
    s.create_session("Session 1", "", "password123")
    s.create_session("Session 2", "", "password123")

    sessions = s.list_sessions()

    assert len(sessions) == 2


def test_save_session(secure_session):
    # add a key to the session
    key = gen_aes256_key()
    secure_session.add_smek(key.data)

    # save the current session
    session_data = secure_session.save_session()

    # open the session again
    secure_session.open_session(secure_session.current_session["name"], "password123")

    # verify if the saved session has the same key
    assert "smek" in secure_session.current_session["keys"]
    assert (
        base64.b64encode(key.data).decode("ascii")
        == secure_session.current_session["keys"]["smek"]["value"]
    )


def test_open_session_invalid_password(secure_session):
    with pytest.raises(RuntimeError, match="invalid password or corrupt session file"):
        secure_session.open_session(
            secure_session.current_session["name"], "wrongpassword"
        )


def test_open_session_not_found(secure_session):
    # if we try to open a non-existent session, it should create a new one
    with pytest.raises(RuntimeError, match="does not exist"):
        session_data = secure_session.open_session(
            "non_existent_session", "password123"
        )


def test_open_session_jsondecodeerror(secure_session):
    session_name = secure_session.current_session["name"]
    session_file = secure_session.storage_path / f"{session_name}.session"
    session_file.write_text("corrupt data")

    with pytest.raises(RuntimeError, match="Corrupt session file"):
        secure_session.open_session(f"{session_name}", "password123")


def test_get_key(secure_session):
    key = gen_aes256_key()
    secure_session.add_smek(key.data)

    retrieved_key = secure_session.get_key("smek")
    assert retrieved_key == key.data


def test_get_key_no_session_open():
    s = SecureSession()
    with pytest.raises(ValueError, match="No active session"):
        s.get_key("test_key")


def test_get_key_not_found(secure_session):
    with pytest.raises(ValueError, match="Key non_existent_key not found in session"):
        secure_session.get_key("non_existent_key")


def test_close_session(secure_session):
    secure_session.close_session()

    assert secure_session.current_session is None
    assert secure_session.fernet is None
