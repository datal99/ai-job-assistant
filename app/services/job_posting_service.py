from pydantic import BaseModel, ConfigDict, Field

from app.models.job_posting import JobPosting
from app.services.llm import parse


class JobPostingIdentity(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    company: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=200)


def extract_job_posting(raw_job_posting: str) -> JobPosting:
    if not raw_job_posting.strip():
        raise ValueError("Job posting cannot be empty.")

    prompt = f"""
Extract the following information from the job posting.

Required fields:
- Company name
- Job title

Rules:
- Extract the company name exactly as stated.
- Extract the job title exactly as stated.
- Do not invent information.

JOB POSTING:
{raw_job_posting}
"""

    identity = parse(
        prompt=prompt,
        response_model=JobPostingIdentity,
    )
    return JobPosting(
        company=identity.company,
        title=identity.title,
        description=raw_job_posting,
    )
