from pathlib import Path

from app.models import TailoredResume
from app.services.llm import generate_tailored_resume


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