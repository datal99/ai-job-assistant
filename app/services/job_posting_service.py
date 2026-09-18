from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.job_posting import JobPosting
from app.services.llm import parse


class JobPostingIdentity(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    company: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=200)

    @field_validator("company", "title")
    @classmethod
    def reject_missing_labels(cls, value: str) -> str:
        missing_labels = {
            "n/a",
            "na",
            "none",
            "not found",
            "not provided",
            "not specified",
            "not stated",
            "unknown",
        }
        if value.casefold().strip(" .:-") in missing_labels:
            raise ValueError("A usable company and role title are required.")
        return value


def extract_job_posting(raw_job_posting: str) -> JobPosting:
    if not raw_job_posting.strip():
        raise ValueError("Job posting cannot be empty.")

    prompt = f"""
Extract the following information from the job posting.

Required fields:
- Company name
- Job title

Rules:
- Look first for labeled metadata such as "Job Title", "Position", "Role",
  or a prominent heading near the beginning of the posting.
- Extract the company name and job title exactly as stated when present.
- Do not confuse a job category, department, business unit, location, requisition
  number, or section heading with the job title.
- If the posting genuinely omits an explicit title, return a concise conventional
  title that best represents its dominant responsibilities and seniority.
- Never return placeholders such as "Not stated", "Not provided", "Unknown",
  "N/A", or an empty value.
- Do not invent a company, qualifications, or posting details. The title fallback
  above is the only permitted inference.

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
