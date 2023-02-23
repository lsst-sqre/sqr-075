from __future__ import annotations

import json
from typing import Optional

from fastapi import Request
from safir.arq import JobMetadata, JobResult

from lsst.rsp.noteburst.models import (
    NotebookResponse as BaseNotebookResponse,
    PostNotebookRequest as BasePostNotebookRequest,
)


class NotebookResponse(BaseNotebookResponse):
    """Information about a notebook execution job, possibly including the
    result and source notebooks.
    """

    @classmethod
    async def from_job_metadata(
        cls,
        *,
        job: JobMetadata,
        request: Request,
        include_source: bool = False,
        job_result: Optional[JobResult] = None,
    ) -> NotebookResponse:
        """Create a notebook response from domain models.

        Parameters
        ----------
        job
            The notebook execution job.
        request
            The client request.
        include_source
            A toggle set by the client to include the notebook's source in the
            response.
        job_result
            The result of the job, if available. `None` if the job is not
            complete.

        Returns
        -------
        NotebookResponse
            The response dataset to send to the client.
        """
        return cls(
            job_id=job.id,
            enqueue_time=job.enqueue_time,
            status=job.status,
            kernel_name=job.kwargs["kernel_name"],
            source=job.kwargs["ipynb"] if include_source else None,
            self_url=request.url_for("get_nbexec_job", job_id=job.id),
            start_time=job_result.start_time if job_result else None,
            finish_time=job_result.finish_time if job_result else None,
            success=job_result.success if job_result else None,
            ipynb=job_result.result if job_result else None,
        )


class PostNotebookRequest(BasePostNotebookRequest):
    """The ``POST /notebooks/`` request body."""

    def get_ipynb_as_str(self) -> str:
        """Get the notebook as a JSON-encoded string."""
        if isinstance(self.ipynb, str):
            return self.ipynb
        else:
            return json.dumps(self.ipynb)
