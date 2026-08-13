from pathlib import Path

from app.models.resume import TailoredResume


TEMPLATE_CV_PATH = Path(
    "resumes/templates/resume_template.tex"
)


def load_resume_template() -> str:
    if not TEMPLATE_CV_PATH.exists():
        raise FileNotFoundError(
            f"Resume template not found at: {TEMPLATE_CV_PATH}"
        )

    return TEMPLATE_CV_PATH.read_text(encoding="utf-8")


def render_summary(summary: str) -> str:
    return summary


def render_experience(resume: TailoredResume) -> str:
    sections = []

    for experience in resume.experience:
        bullets = "\n".join(
            f"\\resumeItem{{}}{{{bullet}}}"
            for bullet in experience.bullets
        )

        sections.append(
            f"""\\resumeSubheading
{{{experience.company}}}{{}}
{{{experience.position}}}{{}}
\\resumeItemListStart
{bullets}
\\resumeItemListEnd"""
        )

    return "\n".join(sections)


def render_projects(resume: TailoredResume) -> str:
    return "\n".join(
        f"\\resumeSubItem{{{project.name}:}}{{{project.description}}}"
        for project in resume.projects
    )


def render_technical_skills(resume: TailoredResume) -> str:
    skills = resume.technical_skills

    sections = [
        f"\\textbf{{Programming:}} {', '.join(skills.programming)}",
        f"\\textbf{{AI & Agent Development:}} "
        f"{', '.join(skills.ai_and_agent_development)}",
        f"\\textbf{{Frameworks & Technologies:}} "
        f"{', '.join(skills.frameworks_and_technologies)}",
        f"\\textbf{{Software Engineering:}} "
        f"{', '.join(skills.software_engineering)}",
        f"\\textbf{{Databases:}} {', '.join(skills.databases)}",
        f"\\textbf{{Testing & Quality:}} "
        f"{', '.join(skills.testing_and_quality)}",
        f"\\textbf{{Development Tools:}} "
        f"{', '.join(skills.development_tools)}",
        f"\\textbf{{Cloud & Architecture:}} "
        f"{', '.join(skills.cloud_and_architecture)}",
        f"\\textbf{{Development Practices:}} "
        f"{', '.join(skills.development_practices)}",
    ]

    return " \\\\\n".join(sections)


def render_resume(
    template: str,
    resume: TailoredResume,
) -> str:
    replacements = {
        "{{SUMMARY}}": render_summary(resume.summary),
        "{{EXPERIENCE}}": render_experience(resume),
        "{{PROJECTS}}": render_projects(resume),
        "{{TECHNICAL_SKILLS}}": render_technical_skills(resume),
    }

    latex = template

    for placeholder, content in replacements.items():
        if placeholder not in latex:
            raise ValueError(
                f"Placeholder '{placeholder}' not found in template."
            )

        latex = latex.replace(placeholder, content)

    return latex