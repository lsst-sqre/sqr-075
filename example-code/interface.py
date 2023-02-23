"""JSON message models for the /v1/ API endpoints."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional, Union

from arq.jobs import JobStatus
from pydantic import AnyHttpUrl, BaseModel, Field

kernel_name_field = Field(
    "LSST",
    title="The name of the Jupyter kernel the kernel is executed with",
    example="LSST",
    description=(
        "The default kernel, LSST, contains the full Rubin Python "
        "environment, [rubinenv](https://anaconda.org/conda-forge/rubin-env), "
        "which includes the LSST Science Pipelines."
    ),
)


class NotebookResponse(BaseModel):
    """Information about a notebook execution job, possibly including the
    result and source notebooks.
    """

    job_id: str = Field(title="The job ID")

    kernel_name: str = kernel_name_field

    enqueue_time: datetime = Field(
        title="Time when the job was added to the queue (UTC)"
    )

    status: JobStatus = Field(
        title="The current status of the notebook execution job"
    )

    self_url: AnyHttpUrl = Field(title="The URL of this resource")

    source: Optional[str] = Field(
        None,
        title="The content of the source ipynb file (JSON-encoded string)",
        description="This field is null unless the source is requested.",
    )

    start_time: Optional[datetime] = Field(
        None,
        title="Time when the notebook execution started (UTC)",
        description="This field is present if the result is available.",
    )

    finish_time: Optional[datetime] = Field(
        None,
        title="Time when the notebook execution completed (UTC)",
        description="This field is present only if the result is available.",
    )

    success: Optional[bool] = Field(
        None,
        title="Whether the execution was successful or not",
        description="This field is present if the result is available.",
    )

    ipynb: Optional[str] = Field(
        None,
        title="The contents of the executed Jupyter notebook",
        description="The ipynb is a JSON-encoded string. This field is "
        "present if the result is available.",
    )


class PostNotebookRequest(BaseModel):
    """The ``POST /notebooks/`` request body."""

    ipynb: Union[str, dict[str, Any]] = Field(
        ...,
        title="The contents of a Jupyter notebook",
        description="If a string, the content is parsed as JSON. "
        "Alternatively, the content can be submitted pre-parsed as "
        "an object.",
    )

    kernel_name: str = kernel_name_field

    enable_retry: bool = Field(
        True,
        title="Enable retries on failures",
        description=(
            "If true (default), noteburst will retry notebook "
            "execution if the notebook fails, with an increasing back-off "
            "time between tries. This is useful for dealing with transient "
            "issues. However, if you are using Noteburst for continuous "
            "integration of notebooks, disabling retries provides faster "
            "feedback."
        ),
    )

    def get_ipynb_as_str(self) -> str:
        if isinstance(self.ipynb, str):
            return self.ipynb
        else:
            return json.dumps(self.ipynb)
