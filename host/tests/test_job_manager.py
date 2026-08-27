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

"""Unit tests for the shared async job manager."""

import threading
import time

import pytest

from services.api import APIError
from services.jobs import JobManager, to_job_response


@pytest.fixture()
def manager():
    """A fresh JobManager with a pool size of 1 for deterministic tests."""
    return JobManager(max_workers=1)


def _wait_status(manager, job_id, timeout=10.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = manager.get(job_id)
        if job["status"] in ("succeeded", "failed", "cancelled"):
            return job
        time.sleep(0.02)
    raise AssertionError("job did not reach a terminal state")


def test_successful_job(manager):
    def fn(ctx):
        ctx.log("started")
        ctx.set_progress(50)
        return {"value": 42}

    job = manager.submit("target", "test", fn)
    done = _wait_status(manager, job["id"])
    assert done["status"] == "succeeded"
    assert done["progress"] == 100
    assert done["result"] == {"value": 42}
    assert any("started" in line["message"] for line in done["logs"])


def test_failed_job_maps_apierror(manager):
    def fn(ctx):
        raise APIError(502, "TARGET_ERROR", "boom")

    job = manager.submit("target", "test", fn)
    done = _wait_status(manager, job["id"])
    assert done["status"] == "failed"
    assert done["error"]["error"]["code"] == "TARGET_ERROR"
    assert done["error"]["error"]["message"] == "boom"


def test_failed_job_maps_generic_exception(manager):
    def fn(ctx):
        raise ValueError("oops")

    job = manager.submit("target", "test", fn)
    done = _wait_status(manager, job["id"])
    assert done["status"] == "failed"
    assert done["error"]["error"]["code"] == "INTERNAL"
    assert "oops" in done["error"]["error"]["message"]


def test_cancel_running_job(manager):
    def fn(ctx):
        # Loop until the cancel event is observed.
        while not ctx.cancel_event.is_set():
            ctx.check_cancel()
            time.sleep(0.01)
        return {"value": 1}

    job = manager.submit("target", "test", fn)
    time.sleep(0.1)
    assert manager.cancel(job["id"]) is True
    done = _wait_status(manager, job["id"])
    assert done["status"] == "cancelled"


def test_cancel_unknown_job(manager):
    assert manager.cancel("nope") is False


def test_list_and_filter(manager):
    job = manager.submit("target", "a", lambda ctx: {"ok": True})
    _wait_status(manager, job["id"])
    assert any(j["id"] == job["id"] for j in manager.list(service="target"))
    assert manager.list(service="crypto") == []
    assert any(j["id"] == job["id"] for j in manager.list(status="succeeded"))


def test_logs_pagination(manager):
    def fn(ctx):
        for i in range(10):
            ctx.log(f"line {i}")
        return {}

    job = manager.submit("target", "test", fn)
    _wait_status(manager, job["id"])
    _job, lines = manager.logs(job["id"], offset=3, limit=4)
    assert [l["message"] for l in lines] == ["line 3", "line 4", "line 5", "line 6"]


def test_stream_yields_sse_frames(manager):
    def fn(ctx):
        ctx.log("hello")
        return {"done": True}

    job = manager.submit("target", "test", fn)
    frames = list(manager.stream(job["id"]))
    joined = "\n".join(frames)
    assert "event: status" in joined
    assert "event: log" in joined
    assert "hello" in joined
    assert "event: result" in joined


def test_to_job_response_shape(manager):
    job = manager.submit("target", "test", lambda ctx: {"ok": True})
    resp = to_job_response(job)
    assert resp["id"] == job["id"]
    assert resp["status"] in ("queued", "running", "succeeded", "failed", "cancelled")
    assert resp["logs_url"] == f"/jobs/{job['id']}/logs"
    assert resp["stream_url"] == f"/jobs/{job['id']}/stream"