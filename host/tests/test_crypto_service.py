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

"""API tests for the Backend #1 (crypto) service sessions and artifact endpoints."""

import pytest
from fastapi.testclient import TestClient

from services.crypto.main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """TestClient with isolated session + artifact storage."""
    monkeypatch.setenv("TISECPROV_SESSION_DIR", str(tmp_path / "sessions"))
    monkeypatch.setenv("CST_ARTIFACT_DIR", str(tmp_path / "artifacts"))
    with TestClient(app) as c:
        yield c


def _create_session(client, name="t1", password="pw", algorithms=None):
    algorithms = algorithms or {
        "smpk_signing_algorithm": "rsa4k",
        "bmpk_signing_algorithm": "rsa4k",
    }
    return client.post(
        "/sessions", json={"name": name, "password": password, **algorithms}
    )


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["crypto"] == "up"
    assert "version" in body


def test_session_lifecycle(client):
    # Create
    r = _create_session(client)
    assert r.status_code == 201
    assert r.json()["name"] == "t1"

    # Duplicate -> 409 SESSION_EXISTS
    r = _create_session(client)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "SESSION_EXISTS"

    # List
    names = [s["name"] for s in client.get("/sessions").json()]
    assert "t1" in names

    # Get single
    assert client.get("/sessions/t1").status_code == 200
    assert client.get("/sessions/missing").status_code == 404

    # Open -> token; wrong password -> 401
    r = client.post("/sessions/t1/open", json={"password": "pw"})
    assert r.status_code == 200
    token = r.json()["token"]
    assert client.post("/sessions/t1/open", json={"password": "bad"}).status_code == 401
    assert client.post("/sessions/missing/open", json={"password": "pw"}).status_code == 404

    # Public keys require the token
    assert client.get("/sessions/t1/public-keys").status_code == 401
    r = client.get("/sessions/t1/public-keys", headers={"X-Session-Token": token})
    assert r.status_code == 200
    pk = r.json()
    assert pk["smpk_public_key"]["filename"] == "t1_smpk_public.pem"
    assert pk["bmpk_public_key"]["filename"] == "t1_bmpk_public.pem"
    assert pk["smpk_public_key"]["size"] > 0

    # Token is scoped to its session
    r2 = _create_session(client, name="t2", password="pw")
    assert r2.status_code == 201
    assert (
        client.get(
            "/sessions/t2/public-keys", headers={"X-Session-Token": token}
        ).status_code
        == 401
    )

    # Delete
    assert client.delete("/sessions/t1").status_code == 204
    assert client.get("/sessions/t1").status_code == 404


def test_artifacts_roundtrip(client):
    r = client.post(
        "/artifacts",
        files={"file": ("blob.bin", b"hello-artifact", "application/octet-stream")},
        data={"purpose": "image", "device": "f29h85x"},
    )
    assert r.status_code == 201
    ref = r.json()
    assert ref["size"] == len(b"hello-artifact")

    r = client.get(f"/artifacts/{ref['id']}")
    assert r.status_code == 200
    assert r.content == b"hello-artifact"

    # Unknown artifact -> 404
    assert (
        client.get("/artifacts/00000000-0000-0000-0000-000000000000").status_code
        == 404
    )
    # Path traversal attempt -> 404
    assert client.get("/artifacts/..%2F..%2Fetc%2Fpasswd").status_code == 404


def test_validation_error_envelope(client):
    r = client.post("/sessions", json={"name": "x"})  # missing password
    assert r.status_code == 400
    body = r.json()
    assert body["error"]["code"] == "INVALID_ARGUMENT"
    assert "details" in body["error"]


def test_development_session_endpoint(client):
    r = client.post(
        "/sessions/Development/development",
        json={
            "smpk_signing_algorithm": "rsa4k",
            "bmpk_signing_algorithm": "secp256r1",
        },
    )
    assert r.status_code == 201
    assert r.json()["name"] == "Development"

    # Only the Development session name is allowed
    r = client.post(
        "/sessions/Other/development",
        json={
            "smpk_signing_algorithm": "rsa4k",
            "bmpk_signing_algorithm": "secp256r1",
        },
    )
    assert r.status_code == 404