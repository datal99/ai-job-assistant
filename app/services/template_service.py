from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MASTER_CV_PATH = PROJECT_ROOT / "resumes/master/master_resume.tex"
TEMPLATE_CV_PATH = PROJECT_ROOT / "resumes/templates/resume_template.tex"


def create_resume_template() -> Path:
    """Create a resume template from the private master CV."""

    if not MASTER_CV_PATH.exists():
        raise FileNotFoundError(
            f"Master CV not found at: {MASTER_CV_PATH}"
        )

    master_cv = MASTER_CV_PATH.read_text(encoding="utf-8")

    template = master_cv

    template = replace_section(
        template,
        "%-----------SUMMARY-----------------",
        "%-----------EDUCATION-----------------",
        "{{SUMMARY}}",
    )

    template = replace_section(
        template,
        "%-----------EXPERIENCE-----------------",
        "%-----------PROJECTS-----------------",
        "{{EXPERIENCE}}",
    )

    template = replace_section(
        template,
        "%-----------PROJECTS-----------------",
        "%--------TECHNICAL SKILLS------------",
        "{{PROJECTS}}",
    )

    template = replace_section(
        template,
        "%--------TECHNICAL SKILLS------------",
        "%-----------LANGUAGES-----------------",
        "{{TECHNICAL_SKILLS}}",
    )

    TEMPLATE_CV_PATH.parent.mkdir(parents=True, exist_ok=True)

    TEMPLATE_CV_PATH.write_text(
        template,
        encoding="utf-8",
    )

    return TEMPLATE_CV_PATH

def load_resume_template() -> str:
    """Load the resume template."""

    if not TEMPLATE_CV_PATH.exists():
        raise FileNotFoundError(
            f"Resume template not found at: {TEMPLATE_CV_PATH}"
        )

    return TEMPLATE_CV_PATH.read_text(encoding="utf-8")

def replace_section(
    latex: str,
    start_marker: str,
    end_marker: str,
    replacement: str,
) -> str:
    """Replace section contents while preserving the section header."""

    start = latex.index(start_marker)
    end = latex.index(end_marker)

    section = latex[start:end]

    section_header_end = section.find("\n\n")

    if section_header_end == -1:
        raise ValueError(
            f"Could not determine section header for: {start_marker}"
        )

    section_header = section[:section_header_end]

    return (
        latex[:start]
        + section_header
        + "\n\n"
        + replacement
        + "\n"
        + latex[end:]
    )
