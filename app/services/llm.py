import os
import logging

from dotenv import load_dotenv
from openai import OpenAI
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.models import JobAnalysisResponse
from app.models.tailored_resume import TailoredResume
from app.models.tailored_cover_letter import TailoredCoverLetter

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = "gpt-5.6-terra"
STRUCTURED_OUTPUT_ATTEMPTS = 2

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class StructuredOutputError(RuntimeError):
    """Raised when OpenAI does not return a complete structured response."""


def parse(
    prompt: str,
    response_model: type[T],
) -> T:
    for attempt in range(1, STRUCTURED_OUTPUT_ATTEMPTS + 1):
        try:
            response = client.responses.parse(
                model=MODEL,
                input=prompt,
                text_format=response_model,
            )
        except ValidationError:
            logger.warning(
                "OpenAI returned invalid structured output (attempt %s of %s)",
                attempt,
                STRUCTURED_OUTPUT_ATTEMPTS,
            )
            continue

        if response.output_parsed is not None:
            return response.output_parsed

        logger.warning(
            "OpenAI returned no parsed structured output (attempt %s of %s)",
            attempt,
            STRUCTURED_OUTPUT_ATTEMPTS,
        )

    raise StructuredOutputError(
        "OpenAI returned an incomplete or invalid structured response."
    )

def analyze_job(prompt: str) -> JobAnalysisResponse:
    return parse(prompt=prompt, response_model=JobAnalysisResponse)

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
- Write exactly three concise resume-style statements totaling roughly 45 to 70 words.
- Use a pronoun-free, implied-first-person voice throughout. Natural openings
  include "Software Engineer with...", "Experienced in...", "Skilled in...",
  and "Strong background in...".
- Do not use personal pronouns such as "I", "me", "my", "he", "she", or
  "they", the candidate's name, or third-person finite-verb constructions such
  as "builds", "brings", "contributes", or "delivers" to describe the candidate.
- Statement one should identify the candidate, years of experience, and the most
  relevant type of work.
- Statement two should naturally connect no more than four to six relevant
  technologies or capabilities to that experience.
- Statement three should describe relevant engineering strengths or contributions
  using a natural resume construction such as "Strong background in...".
- Make the summary read as a professional introduction, not a compressed skills
  inventory. Pronoun-free resume constructions such as "Experienced in..." are
  allowed. Do not use "proven", parenthetical keyword lists, or unsupported
  adjectives.
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
