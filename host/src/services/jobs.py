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
Shared asynchronous job manager.

Long-running operations (hardware provisioning, batch signing) run in a thread
pool as *jobs*. Each job carries status, progress, a cancellable event and an
append-only log. Core functions are CLI-style: they print to stdout, and while
a job runs we swap ``sys.stdout``/``sys.stderr`` for a capture that forwards
lines into the job log -- the same hook the Qt GUI uses (``StreamCapture``),
so we reuse rather than fork the core's streaming.

Only one job may capture stdout at a time (a process-wide resource), so
stdout-capturing jobs are serialized via ``_STDOUT_LOCK``.
"""

import json
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Callable, Dict, Iterator, List, Optional

from services.api import APIError

_STDOUT_LOCK = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class JobContext:
    """Handed to a job function: logging, progress and cancellation."""

    def __init__(self, manager: "JobManager", job: Dict) -> None:
        self._manager = manager
        self._job = job

    @property
    def id(self) -> str:
        return self._job["id"]

    @property
    def cancel_event(self) -> threading.Event:
        return self._job["_cancel_event"]

    def log(self, message: str, level: str = "info") -> None:
        """Append a log line to the job."""
        self._manager.append_log(self._job["id"], message, level)

    def set_progress(self, value: int) -> None:
        """Set the job progress percentage (0-100)."""
        self._manager.set_progress(self._job["id"], value)

    def check_cancel(self) -> None:
        """Raise ``OPERATION_CANCELLED`` if the job was cancelled."""
        if self.cancel_event.is_set():
            raise APIError(409, "OPERATION_CANCELLED", "Operation cancelled")


class StdoutCapture:
    """Replaces ``sys.stdout``/``sys.stderr`` and routes lines to the job log."""

    def __init__(self, manager: "JobManager", job_id: str) -> None:
        self._manager = manager
        self._job_id = job_id
        self._old_out = None
        self._old_err = None

    def start(self) -> None:
        self._old_out = sys.stdout
        self._old_err = sys.stderr
        sys.stdout = self
        sys.stderr = self

    def stop(self) -> None:
        sys.stdout = self._old_out
        sys.stderr = self._old_err

    def write(self, text: str) -> None:
        if self._old_out:
            self._old_out.write(text)
            self._old_out.flush()
        if text:
            for line in text.splitlines():
                self._manager.append_log(self._job_id, line)

    def flush(self) -> None:
        if self._old_out:
            self._old_out.flush()

    def isatty(self) -> bool:
        return False


class JobManager:
    """Tracks and executes jobs."""

    def __init__(self, max_workers: int = 2) -> None:
        self._jobs: Dict[str, Dict] = {}
        self._lock = threading.RLock()
        self._pool = ThreadPoolExecutor(max_workers=max_workers)
        self._seq = 0

    def _next_seq(self) -> int:
        with self._lock:
            self._seq += 1
            return self._seq

    def create(self, service: str, type_: str) -> Dict:
        """Create a job without scheduling it."""
        job: Dict = {
            "id": str(uuid.uuid4()),
            "service": service,
            "type": type_,
            "status": "queued",
            "progress": 0,
            "exit_code": None,
            "result": None,
            "error": None,
            "created_at": _now(),
            "started_at": None,
            "finished_at": None,
            "logs": [],
            "_cancel_event": threading.Event(),
        }
        with self._lock:
            self._jobs[job["id"]] = job
        return job

    def submit(self, service: str, type_: str, fn: Callable[[JobContext], Dict]) -> Dict:
        """Create and schedule a job running ``fn`` in the thread pool."""
        job = self.create(service, type_)
        self._pool.submit(self._run, job, fn)
        return job

    def _run(self, job: Dict, fn: Callable[[JobContext], Dict]) -> None:
        with self._lock:
            job["started_at"] = _now()
            job["status"] = "running"
        ctx = JobContext(self, job)
        capture = StdoutCapture(self, job["id"])
        with _STDOUT_LOCK:
            capture.start()
            try:
                result = fn(ctx)
                with self._lock:
                    if job["_cancel_event"].is_set():
                        job["status"] = "cancelled"
                    else:
                        job["result"] = (
                            result if isinstance(result, dict) else {"result": result}
                        )
                        job["status"] = "succeeded"
                        job["progress"] = 100
            except APIError as exc:
                with self._lock:
                    job["status"] = "failed"
                    job["error"] = {
                        "error": {
                            "code": exc.code,
                            "message": exc.message,
                            "details": exc.details,
                        }
                    }
            except Exception as exc:  # noqa: BLE001 - job must never die silently
                with self._lock:
                    job["status"] = "failed"
                    job["error"] = {
                        "error": {
                            "code": "INTERNAL",
                            "message": f"{type(exc).__name__}: {exc}",
                        }
                    }
            finally:
                capture.stop()
                with self._lock:
                    job["finished_at"] = _now()

    def get(self, job_id: str) -> Optional[Dict]:
        with self._lock:
            return self._jobs.get(job_id)

    def list(self, service: Optional[str] = None, status: Optional[str] = None) -> List[Dict]:
        with self._lock:
            jobs = list(self._jobs.values())
        if service:
            jobs = [j for j in jobs if j["service"] == service]
        if status:
            jobs = [j for j in jobs if j["status"] == status]
        return sorted(jobs, key=lambda j: j["created_at"])

    def cancel(self, job_id: str) -> bool:
        """Signal cancellation. Returns True if the job can still be affected."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return False
            job["_cancel_event"].set()
            if job["status"] == "queued":
                job["status"] = "cancelled"
                job["finished_at"] = _now()
            return job["status"] in ("queued", "running")

    def append_log(self, job_id: str, message: str, level: str = "info") -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job["logs"].append(
                {
                    "seq": self._next_seq(),
                    "timestamp": _now(),
                    "level": level,
                    "message": message,
                }
            )

    def set_progress(self, job_id: str, value: int) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is not None:
                job["progress"] = min(100, max(0, int(value)))

    def logs(self, job_id: str, offset: int = 0, limit: int = 200) -> tuple:
        """Return ``(job, log_lines[offset:offset+limit])`` or ``(None, [])``."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None, []
            lines = list(job["logs"])
        return job, lines[offset : offset + limit]

    def stream(self, job_id: str) -> Iterator[str]:
        """Yield SSE frames for a job (replays stored logs, tails live ones)."""
        return self._stream_gen(job_id)

    def _stream_gen(self, job_id: str) -> Iterator[str]:
        last_seq = 0
        job = self.get(job_id)
        if job is None:
            yield self._sse("error", {"message": "job not found"})
            return
        yield self._sse("status", {"status": job["status"], "progress": job["progress"]})
        while True:
            job, lines = self.logs(job_id, offset=0)
            for line in lines:
                if line["seq"] > last_seq:
                    last_seq = line["seq"]
                    yield self._sse("log", line)
            with self._lock:
                status = job["status"]
                progress = job["progress"]
            if status in ("succeeded", "failed", "cancelled"):
                yield self._sse("status", {"status": status, "progress": progress})
                if job.get("result") is not None:
                    yield self._sse("result", job["result"])
                if job.get("error") is not None:
                    yield self._sse("error", job["error"])
                return
            time.sleep(0.3)

    @staticmethod
    def _sse(event: str, data) -> str:
        payload = json.dumps(data) if not isinstance(data, str) else data
        return f"event: {event}\ndata: {payload}\n\n"


def to_job_response(job: Dict) -> Dict:
    """Build the API response model for a job dict."""
    job_id = job["id"]
    return {
        "id": job_id,
        "service": job["service"],
        "type": job["type"],
        "status": job["status"],
        "progress": job["progress"],
        "exit_code": job["exit_code"],
        "result": job["result"],
        "error": job["error"],
        "created_at": job["created_at"],
        "started_at": job["started_at"],
        "finished_at": job["finished_at"],
        "logs_url": f"/jobs/{job_id}/logs",
        "stream_url": f"/jobs/{job_id}/stream",
    }


job_manager = JobManager()