import os

from dotenv import load_dotenv
from openai import OpenAI

from app.models import JobAnalysisResponse
from app.models.resume import TailoredResume

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def analyze_job(prompt: str) -> JobAnalysisResponse:
    response = client.responses.parse(
        model="gpt-5-mini",
        input=prompt,
        text_format=JobAnalysisResponse
    )

    return response.output_parsed

def generate_tailored_resume(
    job_description: str,
    master_cv: str,
) -> TailoredResume:
    prompt = f"""
You are an expert technical resume writer.

Use the master CV below as the source of truth.

Tailor the candidate's resume for the provided job description.

Important rules:
- Do not invent experience, skills, projects, qualifications, or responsibilities.
- Use only information explicitly supported by the master CV.
- Do not infer that a technology or skill was used for a specific employer, project, or responsibility unless the master CV explicitly associates it with that experience.
- Technical skills listed in the Technical Skills section may be emphasized in the summary or skills section, but must not be added to individual experience bullets unless supported by that specific experience.
- Do not upgrade "familiar with", "concepts", or similar wording into professional hands-on experience.
- Prioritize experience, projects, and skills that are relevant to the job description.
- Rewrite the summary to emphasize relevant qualifications and experience.
- Rewrite experience bullets to emphasize relevant responsibilities and technologies without changing their factual meaning.
- Select and tailor the most relevant projects.
- Preserve factual accuracy.
- Do not change employment dates, company names, positions, degree information, or other fixed factual information.

JOB DESCRIPTION:
{job_description}

MASTER CV:
{master_cv}
"""

    response = client.responses.parse(
        model="gpt-5-mini",
        input=prompt,
        text_format=TailoredResume,
    )

    return response.output_parsed