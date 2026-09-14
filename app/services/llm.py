import os

from dotenv import load_dotenv
from openai import OpenAI
from typing import TypeVar

from pydantic import BaseModel

from app.models import JobAnalysisResponse
from app.models.tailored_resume import TailoredResume
from app.models.tailored_cover_letter import TailoredCoverLetter

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = "gpt-5.6-terra"

T = TypeVar("T", bound=BaseModel)


def parse(
    prompt: str,
    response_model: type[T],
) -> T:
    response = client.responses.parse(
        model=MODEL,
        input=prompt,
        text_format=response_model,
    )

    return response.output_parsed

def analyze_job(prompt: str) -> JobAnalysisResponse:
    response = client.responses.parse(
        model=MODEL,
        input=prompt,
        text_format=JobAnalysisResponse
    )

    return response.output_parsed

def generate_tailored_resume(
    job_description: str,
    master_resume: str,
) -> TailoredResume:
    prompt = build_resume_tailoring_prompt(job_description, master_resume)

    return parse(prompt=prompt, response_model=TailoredResume)


def build_resume_tailoring_prompt(
    job_description: str,
    master_resume: str,
) -> str:
    return f"""
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
- Rebuild the summary from the supported facts; treat the master summary as
  evidence, not as a writing template.
- Write exactly three complete summary sentences totaling roughly 45 to 70 words.
- Sentence one should identify the candidate, years of experience, and the most
  relevant type of work.
- Sentence two should naturally connect no more than four to six relevant
  technologies or capabilities to that experience.
- Sentence three should state the candidate's relevant engineering strengths or
  contribution without generic marketing language.
- Make the summary read as a professional introduction, not a compressed skills
  inventory. Do not use sentence fragments, first-person language, "proven",
  parenthetical keyword lists, or unsupported adjectives.
- Mention AI or LLM work only when the job description makes it relevant.
- Rewrite experience bullets to emphasize relevant responsibilities and technologies without changing their factual meaning.
- Select and tailor the most relevant projects.
- Preserve factual accuracy.
- Do not change employment dates, company names, positions, degree information, or other fixed factual information.

JOB DESCRIPTION:
{job_description}

MASTER CV:
{master_resume}
"""


def generate_tailored_cover_letter(
    job_description: str,
    company: str,
    job_title: str,
    master_resume: str,
) -> TailoredCoverLetter:
    prompt = f"""
You are an expert technical cover letter writer.

Use the master resume below as the only source of truth. Write a concise,
specific cover letter for the role. Return three to five polished paragraphs.

Structure:
- Open with interest in the exact role and the strongest supported fit.
- Connect current and earlier experience to the role's responsibilities.
- Explain specific interest in the company without inventing company facts.
- Close with a brief statement of interest in an interview.

Rules:
- Do not invent experience, skills, projects, qualifications, metrics, or facts.
- Do not repeat contact details, a date, greeting, or signature.
- Do not use bullet points, headings, placeholders, or LaTeX commands.
- Avoid generic enthusiasm, exaggerated claims, and unsupported assertions.
- Keep the complete letter body under 500 words.

COMPANY:
{company}

JOB TITLE:
{job_title}

JOB DESCRIPTION:
{job_description}

MASTER RESUME:
{master_resume}
"""

    return parse(prompt=prompt, response_model=TailoredCoverLetter)
