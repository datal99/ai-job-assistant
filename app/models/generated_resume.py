from pydantic import BaseModel


class GenerateResumeRequest(BaseModel):
    job_posting: str


class GeneratedResumeResponse(BaseModel):
    company: str
    job_title: str
    filename: str
