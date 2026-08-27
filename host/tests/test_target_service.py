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

"""API tests for the Backend #2 (target) service."""

import time

import pytest
from fastapi.testclient import TestClient

from services.jobs import job_manager
from services.target.main import app

MISSING = {"id": "00000000-0000-0000-0000-000000000000", "filename": "f.bin"}


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("TISECPROV_SESSION_DIR", str(tmp_path / "sessions"))
    monkeypatch.setenv("CST_ARTIFACT_DIR", str(tmp_path / "artifacts"))
    with TestClient(app) as c:
        yield c


def _terminal(job_id, timeout=10.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = job_manager.get(job_id)
        if job and job["status"] in ("succeeded", "failed", "cancelled"):
            return job
        time.sleep(0.02)
    raise AssertionError("job did not reach a terminal state")


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["target"] == "up"


def test_ports(client):
    r = client.get("/ports")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_devices(client):
    r = client.get("/devices")
    assert r.status_code == 200
    names = [d["name"] for d in r.json()]
    assert "f29h85x" in names


def test_job_lifecycle_via_api(client):
    job = job_manager.submit(
        "target", "test", lambda ctx: (ctx.log("hello-job"), {"ok": True})[1]
    )

    r = client.get(f"/jobs/{job['id']}")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == job["id"]
    assert body["logs_url"].endswith(f"/jobs/{job['id']}/logs")

    assert any(j["id"] == job["id"] for j in client.get("/jobs").json())
    assert client.get(f"/jobs/{job['id']}/logs").status_code == 200

    r = client.get(f"/jobs/{job['id']}/stream")
    assert r.status_code == 200
    assert "event:" in r.text

    assert client.get("/jobs/unknown").status_code == 404
    assert client.delete("/jobs/unknown").status_code == 404


def test_device_type_uart_returns_202_and_cancellable(client):
    body = {"port": "/dev/null", "targetbaud": 921600, "uart_kernel": MISSING}
    r = client.post("/targets/type/uart", json=body)
    assert r.status_code == 202, r.text
    job_id = r.json()["id"]
    assert client.delete(f"/jobs/{job_id}").status_code == 202
    job = _terminal(job_id)
    assert job["status"] in ("cancelled", "failed")


def test_validation_error_envelope(client):
    r = client.post("/targets/type/uart", json={})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "INVALID_ARGUMENT"


def test_provisioning_endpoints_create_jobs(client):
    for path, body in [
        (
            "/targets/f29h85x/key-provisioning",
            {
                "interface": "uart",
                "otp_kw_bin": MISSING,
                "certificate": MISSING,
                "uart_kernel": MISSING,
                "uart": {"port": "/dev/null"},
            },
        ),
        (
            "/targets/f29h85x/code-provisioning",
            {
                "interface": "uart",
                "hsm_image": MISSING,
                "hsm_cpu_code": MISSING,
                "c29_cpu_code": MISSING,
                "seccfg": MISSING,
                "uart_kernel": MISSING,
                "uart": {"port": "/dev/null"},
            },
        ),
        ("/targets/recovery/enable", {"ccs_path": "/nonexistent"}),
        ("/targets/recovery/uid-secap", {"ccs_path": "/nonexistent"}),
        (
            "/targets/recovery/validate",
            {"ccs_path": "/nonexistent", "dev_recov_cert": MISSING},
        ),
        ("/targets/download", {"port": "/dev/null", "bootloader": MISSING}),
    ]:
        r = client.post(path, json=body)
        assert r.status_code == 202, (path, r.text)
        job_id = r.json()["id"]
        assert client.delete(f"/jobs/{job_id}").status_code == 202


def test_interface_mismatch_validation(client):
    # interface=uart without the uart connection is a 400 (validated in ops)
    body = {"interface": "uart", "otp_kw_bin": MISSING, "certificate": MISSING}
    r = client.post("/targets/f29h85x/key-provisioning", json=body)
    assert r.status_code == 202  # job accepted; fails later with INVALID_ARGUMENT
    job_id = r.json()["id"]
    job = _terminal(job_id)
    assert job["status"] == "failed"
    assert job["error"]["error"]["code"] == "INVALID_ARGUMENT"