import re
from pathlib import Path

from app.models.master_resume import MasterResume
from app.models.tailored_resume import TailoredResume

TEMPLATE_RESUME_PATH = Path(
    "resumes/templates/resume_template.tex"
)

def escape_latex(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }

    pattern = re.compile("|".join(re.escape(char) for char in replacements))
    return pattern.sub(lambda match: replacements[match.group(0)], text)


def load_resume_template() -> str:
    if not TEMPLATE_RESUME_PATH.exists():
        raise FileNotFoundError(
            f"Resume template not found at: {TEMPLATE_RESUME_PATH}"
        )

    return TEMPLATE_RESUME_PATH.read_text(encoding="utf-8")


def render_summary(summary: str) -> str:
    return escape_latex(summary)


def render_experience(
    master_resume: MasterResume,
    tailored_resume: TailoredResume,
) -> str:
    if len(master_resume.experience) != len(tailored_resume.experience):
        raise ValueError(
            "Master and tailored experience counts do not match."
        )

    sections = []

    for master, tailored in zip(
        master_resume.experience,
        tailored_resume.experience,
    ):
        bullets = "\n".join(
            f"\\resumeItem{{{escape_latex(bullet.header)}}}"
            f"{{{escape_latex(bullet.content)}}}"
            for bullet in tailored.bullets
        )

        sections.append(
            f"""\\resumeSubheading
{{{escape_latex(master.company)}}}{{{escape_latex(master.location)}}}
{{{escape_latex(master.position)}}}{{{escape_latex(master.dates)}}}
\\resumeItemListStart
{bullets}
\\resumeItemListEnd"""
        )

    return f"""\\resumeSubHeadingListStart
{"\n".join(sections)}
\\resumeSubHeadingListEnd"""


def render_projects(
    tailored_resume: TailoredResume,
) -> str:
    projects = "\n".join(
        f"\\resumeSubItem{{{escape_latex(project.name)}:}}"
        f"{{{escape_latex(project.description)}}}"
        for project in tailored_resume.projects
    )

    return f"""\\resumeSubHeadingListStart
{projects}
\\resumeSubHeadingListEnd"""


def render_technical_skills(
    tailored_resume: TailoredResume,
) -> str:
    skills = tailored_resume.technical_skills

    sections = [
        f"\\textbf{{Programming:}} "
        f"{escape_latex(', '.join(skills.programming))} \\\\",

        f"\\textbf{{AI \\& Agent Development:}} "
        f"{escape_latex(', '.join(skills.ai_and_agent_development))} \\\\",

        f"\\textbf{{Frameworks \\& Technologies:}} "
        f"{escape_latex(', '.join(skills.frameworks_and_technologies))} \\\\",

        f"\\textbf{{Software Engineering:}} "
        f"{escape_latex(', '.join(skills.software_engineering))} \\\\",

        f"\\textbf{{Databases:}} "
        f"{escape_latex(', '.join(skills.databases))} \\\\",

        f"\\textbf{{Testing \\& Quality:}} "
        f"{escape_latex(', '.join(skills.testing_and_quality))} \\\\",

        f"\\textbf{{Development Tools:}} "
        f"{escape_latex(', '.join(skills.development_tools))} \\\\",

        f"\\textbf{{Cloud \\& Architecture:}} "
        f"{escape_latex(', '.join(skills.cloud_and_architecture))} \\\\",

        f"\\textbf{{Development Practices:}} "
        f"{escape_latex(', '.join(skills.development_practices))}",
    ]

    return "\n".join(sections)


def render_resume(
    template: str,
    master_resume_data: MasterResume,
    tailored_resume: TailoredResume,
) -> str:
    replacements = {
        "{{SUMMARY}}": render_summary(tailored_resume.summary),
        "{{EXPERIENCE}}": render_experience(
            master_resume_data,
            tailored_resume,
        ),
        "{{PROJECTS}}": render_projects(tailored_resume),
        "{{TECHNICAL_SKILLS}}": render_technical_skills(
            tailored_resume
        ),
    }

    latex = template

    for placeholder, content in replacements.items():
        if placeholder not in latex:
            raise ValueError(
                f"Placeholder '{placeholder}' not found in template."
            )

        latex = latex.replace(placeholder, content)

    return latex
