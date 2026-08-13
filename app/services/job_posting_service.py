from app.models.job_posting import JobPosting
from app.services.llm import parse


def extract_job_posting(raw_job_posting: str) -> JobPosting:
    prompt = f"""
Extract the following information from the job posting.

Required fields:
- Company name
- Job title
- Job description

Rules:
- Extract the company name exactly as stated.
- Extract the job title exactly as stated.
- Preserve the job description as faithfully as possible.
- Do not invent information.
- Do not summarize or rewrite the job description.

JOB POSTING:
{raw_job_posting}
"""

    return parse(
        prompt=prompt,
        response_model=JobPosting,
    )