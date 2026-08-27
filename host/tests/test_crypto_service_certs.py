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

"""API tests for the Backend #1 (crypto) certificate and image endpoints."""

import os

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from services.crypto.main import app

DEVICE = "f29h85x"
AUTH_HEADERS = {"X-Session-Token": ""}
DEV_UID = "A" * 128  # 64-byte device UID in hex


@pytest.fixture(scope="module")
def ctx(tmp_path_factory):
    """Shared module context: isolated storage, one session + token, FEK artifact."""
    old_s = os.environ.get("TISECPROV_SESSION_DIR")
    old_a = os.environ.get("CST_ARTIFACT_DIR")
    os.environ["TISECPROV_SESSION_DIR"] = str(tmp_path_factory.mktemp("sessions"))
    os.environ["CST_ARTIFACT_DIR"] = str(tmp_path_factory.mktemp("artifacts"))
    try:
        with TestClient(app) as client:
            # A realistic TI FEK public key (RSA 4096).
            priv = rsa.generate_private_key(public_exponent=65537, key_size=4096)
            fek_pem = priv.public_key().public_bytes(
                serialization.Encoding.PEM,
                serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            fek = client.post(
                "/artifacts",
                files={"file": ("ti_fek_public.pem", fek_pem, "application/x-pem-file")},
                data={"purpose": "tifek", "device": DEVICE},
            ).json()

            # Create an RSA4K/RSA4K session and open it for a token.
            r = client.post(
                "/sessions",
                json={
                    "name": "CertTest",
                    "password": "pw",
                    "smpk_signing_algorithm": "rsa4k",
                    "bmpk_signing_algorithm": "rsa4k",
                },
            )
            assert r.status_code == 201
            token = client.post(
                "/sessions/CertTest/open", json={"password": "pw"}
            ).json()["token"]

            # Upload a small dummy image and an AES key.
            img = client.post(
                "/artifacts",
                files={"file": ("app.bin", b"\x01\x02\x03\x04", "application/octet-stream")},
                data={"purpose": "image", "device": DEVICE},
            ).json()
            key = client.post(
                "/artifacts",
                files={"file": ("aes.key", b"\x2b" * 32, "application/octet-stream")},
                data={"purpose": "aes_key", "device": DEVICE},
            ).json()

            AUTH_HEADERS["X-Session-Token"] = token
            yield client, {"token": token, "fek": fek, "img": img, "key": key}
    finally:
        if old_s is None:
            os.environ.pop("TISECPROV_SESSION_DIR", None)
        else:
            os.environ["TISECPROV_SESSION_DIR"] = old_s
        if old_a is None:
            os.environ.pop("CST_ARTIFACT_DIR", None)
        else:
            os.environ["CST_ARTIFACT_DIR"] = old_a


def test_generate_certificate(ctx):
    client, refs = ctx
    body = {
        "devSrVer": "SR_20",
        "tifek_artifact": refs["fek"],
        "msv": "0x1E22D",
        "msv_protect": True,
        "sr_sbl": "1",
        "sr_hsmRT": "1",
        "sr_app": "1",
        "sr_ssu": "1",
        "keycnt": 2,
        "keycnt_protect": True,
        "keyrev": 1,
        "b_protect": True,
        "s_protect": True,
    }
    r = client.post(
        f"/devices/{DEVICE}/certificates", json=body, headers=AUTH_HEADERS
    )
    assert r.status_code == 200, r.text
    result = r.json()
    bundle = result["certificates"][0]
    assert bundle["primary_cert"] is not None
    assert bundle["final_cert"] is not None
    # Downloadable roundtrip
    r = client.get(f"/artifacts/{bundle['primary_cert']['id']}")
    assert r.status_code == 200
    assert len(r.content) > 0


def test_generate_rot_cert(ctx):
    client, _ = ctx
    r = client.post(
        f"/devices/{DEVICE}/certificates/rot", headers=AUTH_HEADERS
    )
    assert r.status_code == 200, r.text
    assert r.json()["rot_switching_cert"]["filename"] == "rot_switching.cert"


def test_generate_debug_cert(ctx):
    client, _ = ctx
    body = {"keyrev": 1, "swrv": 1, "dev_dbg_type": 4, "dev_uid": DEV_UID}
    r = client.post(
        f"/devices/{DEVICE}/certificates/debug", json=body, headers=AUTH_HEADERS
    )
    assert r.status_code == 200, r.text
    assert r.json()["debug_cert"]["filename"] == "debug_auth.cert"


def test_generate_recovery_cert(ctx):
    client, _ = ctx
    body = {"keyrev": 1, "dev_uid": DEV_UID}
    r = client.post(
        f"/devices/{DEVICE}/certificates/recovery", json=body, headers=AUTH_HEADERS
    )
    assert r.status_code == 200, r.text
    assert r.json()["recovery_cert"]["filename"] == "device_recovery.bin"


def test_cert_requires_token(ctx):
    client, _ = ctx
    body = {"devSrVer": "SR_20", "tifek_artifact": None}
    r = client.post(f"/devices/{DEVICE}/certificates", json=body)
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "UNAUTHORIZED"


def test_sign_image(ctx):
    client, refs = ctx
    body = {
        "image_artifact": refs["img"],
        "input_format": "BIN",
        "core": "C29",
        "keyrev": "1",
        "loadaddr": "0x10001000",
        "swrv": "1",
        "boot": "FLASH",
    }
    r = client.post(f"/devices/{DEVICE}/images/sign", json=body, headers=AUTH_HEADERS)
    assert r.status_code == 200, r.text
    ref = r.json()["signed_image"]
    assert ref["filename"] == "app.cert.bin"
    r = client.get(f"/artifacts/{ref['id']}")
    assert r.status_code == 200
    assert len(r.content) > 0


def test_encrypt_image(ctx):
    client, refs = ctx
    body = {"image_artifact": refs["img"], "key": refs["key"], "encryption_mode": "sbl_enc"}
    r = client.post(f"/devices/{DEVICE}/images/encrypt", json=body, headers=AUTH_HEADERS)
    assert r.status_code == 200, r.text
    ref = r.json()["encrypted_image"]
    assert ref["filename"] == "encrypted.bin"
    r = client.get(f"/artifacts/{ref['id']}")
    assert r.status_code == 200
    assert len(r.content) > 0


def test_sign_seccfg_requires_valid_ccs(ctx):
    client, refs = ctx
    body = {
        "image_artifact": refs["img"],
        "swrv": "1",
        "keyrev": "1",
        "boot": "FLASH",
        "ccs_path": "/nonexistent/ccs",
    }
    r = client.post(f"/devices/{DEVICE}/images/sign-seccfg", json=body, headers=AUTH_HEADERS)
    # Structured 500 envelope (CCS is mandatory for seccfg signing)
    assert r.status_code == 500
    assert "error" in r.json()


def test_sign_batch(ctx):
    import time

    from services.jobs import job_manager

    client, _ = ctx
    r = client.post(f"/devices/{DEVICE}/images/sign-batch", headers=AUTH_HEADERS)
    assert r.status_code == 202, r.text
    job_id = r.json()["id"]

    deadline = time.time() + 60
    while time.time() < deadline:
        job = job_manager.get(job_id)
        if job and job["status"] in ("succeeded", "failed", "cancelled"):
            break
        time.sleep(0.2)
    assert job["status"] == "succeeded", job["error"]
    result = job["result"]
    assert result["total"] >= 1
    assert result["succeeded"] >= 1