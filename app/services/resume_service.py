import re
from datetime import date
from pathlib import Path
from typing import Callable

from app.models import TailoredResume
from app.models.generated_resume import GenerationStage
from app.models.job_posting import JobPosting
from app.services.job_posting_service import extract_job_posting
from app.services.llm import (
    generate_tailored_resume,
    validate_resume_experience,
)
from app.services.master_resume_parser import extract_master_resume_data
from app.services.resume_renderer import render_resume
from app.services.template_service import load_resume_template


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MASTER_RESUME_PATH = PROJECT_ROOT / "resumes/master/master_resume.tex"
GENERATED_RESUME_DIR = PROJECT_ROOT / "resumes/generated"


class ResumeGroundingError(RuntimeError):
    """Raised when generated experience contains unsupported claims."""


def load_master_resume() -> str:
    """Load the private master CV."""
    if not MASTER_RESUME_PATH.exists():
        raise FileNotFoundError(
            f"Master CV not found at: {MASTER_RESUME_PATH}"
        )

    return MASTER_RESUME_PATH.read_text(encoding="utf-8")


def save_generated_resume(filename: str, content: str) -> Path:
    """Save a generated CV to the generated resumes directory."""
    GENERATED_RESUME_DIR.mkdir(parents=True, exist_ok=True)

    output_path = GENERATED_RESUME_DIR / filename
    output_path.write_text(content, encoding="utf-8")

    return output_path

def tailor_resume(job_description: str) -> TailoredResume:
    """Generate tailored resume content for a job description."""
    master_resume = load_master_resume()

    return generate_tailored_resume(
        job_description=job_description,
        master_resume=master_resume,
    )


def validate_tailored_resume(tailored_resume: TailoredResume) -> None:
    """Block generated experience that is not grounded in the master resume."""
    master_resume = load_master_resume()
    result = validate_resume_experience(
        master_resume=master_resume,
        tailored_resume=tailored_resume,
    )
    if result.is_valid and not result.issues:
        return

    reasons = "; ".join(
        f"{issue.experience}: {issue.reason}"
        for issue in result.issues[:3]
    )
    detail = f" Issues: {reasons}" if reasons else ""
    raise ResumeGroundingError(
        "Generated experience was not saved because it could not be verified "
        f"against the master resume.{detail}"
    )


def build_resume_filename(
    company: str,
    job_title: str,
) -> str:
    def sanitize(value: str) -> str:
        value = re.sub(r"[^A-Za-z0-9]+", "-", value)
        return value.strip("-")

    company = sanitize(company)
    job_title = sanitize(job_title)

    return (
        f"{date.today().isoformat()}"
        f"_{company}"
        f"_{job_title}"
        f"_CV_Submitted.tex"
    )


def generate_resume_from_job_posting(
    raw_job_posting: str,
    progress_callback: Callable[[GenerationStage], None] | None = None,
) -> tuple[JobPosting, Path]:
    """Create and save a tailored resume from a raw job posting."""
    def report(stage: GenerationStage) -> None:
        if progress_callback:
            progress_callback(stage)

    report("reading_job_posting")
    job_posting = extract_job_posting(raw_job_posting)

    report("tailoring_resume")
    tailored_resume = tailor_resume(job_posting.description)

    report("validating_resume")
    validate_tailored_resume(tailored_resume)

    report("rendering_resume")
    master_resume_data = extract_master_resume_data()
    template = load_resume_template()

    rendered_resume = render_resume(
        template=template,
        master_resume_data=master_resume_data,
        tailored_resume=tailored_resume,
    )
    filename = build_resume_filename(
        company=job_posting.company,
        job_title=job_posting.title,
    )
    output_path = save_generated_resume(filename, rendered_resume)

    return job_posting, output_path
