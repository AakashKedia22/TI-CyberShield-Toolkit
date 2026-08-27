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
Shared job lifecycle router.

Both services expose the same ``/jobs`` surface via ``make_jobs_router``; the
job store itself is the shared ``job_manager`` singleton.
"""

from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from services.api import APIError
from services.jobs import job_manager, to_job_response


def make_jobs_router(api_key_dependency) -> APIRouter:
    """Build the ``/jobs`` router, guarded by *api_key_dependency*."""
    router = APIRouter(
        prefix="/jobs",
        tags=["jobs"],
        dependencies=[Depends(api_key_dependency)],
    )

    @router.get(
        "",
        response_model=list,
        operation_id="listJobs",
        summary="List jobs (optionally filtered by service and status)",
    )
    def list_jobs(
        service: Optional[str] = None, status: Optional[str] = None
    ) -> list:
        return [
            to_job_response(j) for j in job_manager.list(service=service, status=status)
        ]

    @router.get(
        "/{id}",
        response_model=dict,
        operation_id="getJob",
        summary="Get job status and result",
    )
    def get_job(id: str) -> dict:
        job = job_manager.get(id)
        if job is None:
            raise APIError(404, "JOB_NOT_FOUND", f"Job {id} not found")
        return to_job_response(job)

    @router.delete(
        "/{id}",
        status_code=202,
        operation_id="cancelJob",
        summary="Cancel a running job",
    )
    def cancel_job(id: str) -> None:
        if job_manager.get(id) is None:
            raise APIError(404, "JOB_NOT_FOUND", f"Job {id} not found")
        job_manager.cancel(id)  # best-effort: already-terminal jobs are unaffected

    @router.get(
        "/{id}/logs",
        operation_id="getJobLogs",
        summary="Get paginated job log tail",
    )
    def get_job_logs(id: str, offset: int = 0, limit: int = 200) -> dict:
        job, lines = job_manager.logs(id, offset=offset, limit=limit)
        if job is None:
            raise APIError(404, "JOB_NOT_FOUND", f"Job {id} not found")
        return {"lines": lines, "next_offset": offset + len(lines)}

    @router.get(
        "/{id}/stream",
        response_class=StreamingResponse,
        operation_id="streamJobLogs",
        summary="Stream job logs over SSE",
    )
    def stream_job_logs(id: str) -> StreamingResponse:
        if job_manager.get(id) is None:
            raise APIError(404, "JOB_NOT_FOUND", f"Job {id} not found")
        return StreamingResponse(
            job_manager.stream(id),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return router