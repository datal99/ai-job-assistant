from fastapi import FastAPI
from pydantic import BaseModel

from app.services.llm import analyze_job
from app.models import JobAnalysisResponse

app = FastAPI()

class JobAnalysisRequest(BaseModel):
    job_description: str
    resume: str


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/analyze", response_model=JobAnalysisResponse)
def analyze(request: JobAnalysisRequest):

    prompt = f"""
You are a technical recruiter analyzing a candidate for a job.

Compare the candidate's resume against the job description.

JOB DESCRIPTION:
{request.job_description}

RESUME:
{request.resume}

Analyze the candidate and return:
- An overall match score from 0 to 100
- Skills that are strong matches
- Skills that are partial matches
- Required skills that are missing
- A short overall summary
"""

    return analyze_job(prompt)