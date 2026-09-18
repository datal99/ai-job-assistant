import shutil
from datetime import date
from pathlib import Path
from typing import Callable

from app.models.generated_resume import GenerationStage
from app.models.job_posting import JobPosting
from app.models.tailored_cover_letter import TailoredCoverLetter
from app.services.llm import generate_tailored_cover_letter
from app.services.resume_renderer import escape_latex
from app.services.resume_service import build_resume_filename, load_master_resume


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MASTER_COVER_LETTER_PATH = (
    PROJECT_ROOT / "cover_letters" / "master" / "master_cover_letter.tex"
)
GENERATED_COVER_LETTER_DIR = PROJECT_ROOT / "cover_letters" / "generated"

REQUIRED_COVER_LETTER_MARKERS = (
    r"\documentclass",
    "{{RECIPIENT}}",
    "{{COMPANY}}",
    "{{BODY}}",
    r"\end{document}",
)


class MissingCoverLetterTemplate(FileNotFoundError):
    pass


def validate_master_cover_letter(content: str) -> None:
    missing = [
        marker for marker in REQUIRED_COVER_LETTER_MARKERS if marker not in content
    ]
    if missing:
        raise ValueError(
            "The uploaded file is not a compatible cover letter template. "
            f"Missing required markers: {', '.join(missing)}"
        )

    positions = [content.index(marker) for marker in REQUIRED_COVER_LETTER_MARKERS]
    if positions != sorted(positions):
        raise ValueError("The cover letter placeholders are in an unexpected order.")


def replace_master_cover_letter(content: str) -> Path:
    validate_master_cover_letter(content)
    MASTER_COVER_LETTER_PATH.parent.mkdir(parents=True, exist_ok=True)

    temporary_path = MASTER_COVER_LETTER_PATH.with_suffix(".uploading.tex")
    backup_path = MASTER_COVER_LETTER_PATH.with_suffix(".backup.tex")
    had_existing_template = MASTER_COVER_LETTER_PATH.exists()

    temporary_path.write_text(content, encoding="utf-8")
    if had_existing_template:
        shutil.copy2(MASTER_COVER_LETTER_PATH, backup_path)
    temporary_path.replace(MASTER_COVER_LETTER_PATH)

    return MASTER_COVER_LETTER_PATH


def load_master_cover_letter() -> str:
    if not MASTER_COVER_LETTER_PATH.is_file():
        raise MissingCoverLetterTemplate(
            "Upload a compatible master cover letter before generating one."
        )

    return MASTER_COVER_LETTER_PATH.read_text(encoding="utf-8")


def render_cover_letter(
    template: str,
    company: str,
    tailored_cover_letter: TailoredCoverLetter,
    recipient: str = "Hiring Team",
) -> str:
    paragraphs = "\n\n".join(
        escape_latex(paragraph.strip())
        for paragraph in tailored_cover_letter.paragraphs
    )
    replacements = {
        "{{RECIPIENT}}": escape_latex(recipient),
        "{{COMPANY}}": escape_latex(company),
        "{{BODY}}": paragraphs,
    }

    latex = template
    for placeholder, content in replacements.items():
        if placeholder not in latex:
            raise ValueError(
                f"Placeholder '{placeholder}' not found in cover letter template."
            )
        latex = latex.replace(placeholder, content)

    return latex


def build_cover_letter_filename(company: str, job_title: str) -> str:
    resume_filename = build_resume_filename(company, job_title)
    stem = resume_filename.removesuffix("_CV_Submitted.tex")
    return f"{stem}_Cover_Letter.tex"


def save_generated_cover_letter(filename: str, content: str) -> Path:
    GENERATED_COVER_LETTER_DIR.mkdir(parents=True, exist_ok=True)
    output_path = GENERATED_COVER_LETTER_DIR / filename
    output_path.write_text(content, encoding="utf-8")
    return output_path


def generate_cover_letter(
    job_posting: JobPosting,
    template: str | None = None,
    progress_callback: Callable[[GenerationStage], None] | None = None,
    revision_feedback: str | None = None,
) -> Path:
    def report(stage: GenerationStage) -> None:
        if progress_callback:
            progress_callback(stage)

    cover_letter_template = template or load_master_cover_letter()
    master_resume = load_master_resume()

    report("tailoring_cover_letter")
    generation_kwargs = dict(
        job_description=job_posting.description,
        company=job_posting.company,
        job_title=job_posting.title,
        master_resume=master_resume,
    )
    if revision_feedback:
        generation_kwargs["revision_feedback"] = revision_feedback
    tailored_cover_letter = generate_tailored_cover_letter(**generation_kwargs)

    report("rendering_cover_letter")
    rendered = render_cover_letter(
        template=cover_letter_template,
        company=job_posting.company,
        tailored_cover_letter=tailored_cover_letter,
    )
    filename = build_cover_letter_filename(
        company=job_posting.company,
        job_title=job_posting.title,
    )
    return save_generated_cover_letter(filename, rendered)
