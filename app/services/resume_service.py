from pathlib import Path

from app.models import TailoredResume
from app.services.llm import generate_tailored_resume


MASTER_CV_PATH = Path("resumes/master/master_cv.tex")
GENERATED_CV_DIR = Path("resumes/generated")


def load_master_cv() -> str:
    """Load the private master CV."""
    if not MASTER_CV_PATH.exists():
        raise FileNotFoundError(
            f"Master CV not found at: {MASTER_CV_PATH}"
        )

    return MASTER_CV_PATH.read_text(encoding="utf-8")


def save_generated_cv(filename: str, content: str) -> Path:
    """Save a generated CV to the generated resumes directory."""
    GENERATED_CV_DIR.mkdir(parents=True, exist_ok=True)

    output_path = GENERATED_CV_DIR / filename
    output_path.write_text(content, encoding="utf-8")

    return output_path

def tailor_resume(job_description: str) -> TailoredResume:
    """Generate tailored resume content for a job description."""
    master_cv = load_master_cv()

    return generate_tailored_resume(
        job_description=job_description,
        master_cv=master_cv,
    )