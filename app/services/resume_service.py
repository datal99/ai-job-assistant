import re
from datetime import date
from pathlib import Path

from app.models import TailoredResume
from app.models.job_posting import JobPosting
from app.services.job_posting_service import extract_job_posting
from app.services.llm import generate_tailored_resume
from app.services.master_resume_parser import extract_master_resume_data
from app.services.resume_renderer import render_resume
from app.services.template_service import load_resume_template


MASTER_RESUME_PATH = Path("resumes/master/master_resume.tex")
GENERATED_RESUME_DIR = Path("resumes/generated")


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
) -> tuple[JobPosting, Path]:
    """Create and save a tailored resume from a raw job posting."""
    job_posting = extract_job_posting(raw_job_posting)
    tailored_resume = tailor_resume(job_posting.description)
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
