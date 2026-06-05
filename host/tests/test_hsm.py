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
from pathlib import Path
import tempfile
from pkcs11 import KeyType, ObjectClass

from tisecprov.session import SecureSession
from tisecprov.hsm_crypto import (
    HSMManufacturerKeys,
    get_pkcs11_lib,
)


def test_so_file():
    lib = get_pkcs11_lib()
    assert lib.get_slots()


@pytest.fixture
def test_session():
    """Fixture that provides an initialized test session"""

    class TestSession:
        def __init__(self):
            self.label = "pytest"
            self.initialize()

        def initialize(self):
            temp_dir = Path(tempfile.gettempdir())
            session = SecureSession(storage_path=temp_dir, use_hsm=True)
            session.create_session(
                name=self.label, description="This is a test session", password="123456"
            )
            self.session = session
            lib = get_pkcs11_lib()
            token = lib.get_token()
            hsm_session = token.open(user_pin="123456", rw=True)
            self.token = token
            self.hsm_session = hsm_session
            self.session.hsm_session = hsm_session

    test_sess = TestSession()
    for obj in test_sess.hsm_session.get_objects():
        obj.destroy()
    yield test_sess

    # Cleanup after tests
    test_sess.session.close_session()
    test_sess.session.delete_session(test_sess.label)


@pytest.fixture
def mkey(test_session):
    """Fixture that provides manufacturer keys"""
    return HSMManufacturerKeys(
        test_session.session, label=test_session.label,
    )


# @pytest.mark.skip(reason="test fails, will revisit later")
def test_manufacturer_key_generation(test_session, mkey):
    """Test manufacturer key generation"""
    assert mkey.get_public_key() is not None
    pub_key_pkcs11 = test_session.hsm_session.get_key(
        key_type=KeyType.RSA,
        object_class=ObjectClass.PUBLIC_KEY,
        label=test_session.label,
    )
    assert mkey.pub_key == pub_key_pkcs11


# @pytest.mark.skip(reason="test fails, will revisit later")
def test_hsm_sign(mkey):

    message = b"This is a test message."

    # Sign using HSM
    signature = mkey.sign(message)

    # Verify using public key
    public_key = mkey.pub_key

    try:
        public_key.verify(
            message,
            signature,
        )
        pass
    except Exception as e:
        pytest.fail(f"Signature verification failed: {e}")

# @pytest.mark.skip(reason="test fails, will revisit later")
def test_hsm_sign_pss(mkey):
    message = b"This is a test message."

    signature = mkey.sign_pss(message)

    public_key = mkey.pub_key

    try:
        public_key.verify(
            signature,
            message,
        )
        pass
    except Exception as e:
        pytest.fail(f"Signature verification failed: {e}")


@pytest.fixture(autouse=True)
def cleanup(test_session):
    """Automatic cleanup fixture that runs after each test"""
    yield
    # Find and destroy test keys
    for obj in test_session.hsm_session.get_objects():
        if obj.label and obj.label.startswith("pytest"):
            obj.destroy()


# TODO Add tests for HSM encryption/decryption

# TODO ADD tests for AES Key Generation

# TODO ADD tests for AES Encryption
