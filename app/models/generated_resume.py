from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class GenerateResumeRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    job_posting: str = Field(min_length=40, max_length=50_000)
    include_cover_letter: bool = False


class GeneratedResumeResponse(BaseModel):
    company: str
    job_title: str
    filename: str
    cover_letter_filename: str | None = None


class MasterResumeUploadRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1, max_length=1_000_000)


class MasterResumeStatus(BaseModel):
    exists: bool
    filename: str
    pdf_supported: bool


GenerationStage = Literal[
    "queued",
    "reading_job_posting",
    "tailoring_resume",
    "validating_resume",
    "rendering_resume",
    "tailoring_cover_letter",
    "rendering_cover_letter",
    "complete",
]

GenerationStatus = Literal["queued", "running", "completed", "failed"]

class GenerationJobCreated(BaseModel):
    job_id: str


class GenerationJobStatus(BaseModel):
    job_id: str
    status: GenerationStatus
    stage: GenerationStage
    elapsed_seconds: int
    result: GeneratedResumeResponse | None = None
    error: str | None = None
