import re
from pathlib import Path

from app.models.master_resume import MasterExperience, MasterResume


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MASTER_RESUME_PATH = PROJECT_ROOT / "resumes/master/master_resume.tex"


def extract_master_resume_data() -> MasterResume:
    if not MASTER_RESUME_PATH.exists():
        raise FileNotFoundError(
            f"Master CV not found at: {MASTER_RESUME_PATH}"
        )

    latex = MASTER_RESUME_PATH.read_text(encoding="utf-8")

    experience_section = latex.split(
        "%-----------EXPERIENCE-----------------",
        1,
    )[1].split(
        "%-----------PROJECTS-----------------",
        1,
    )[0]

    pattern = re.compile(
        r"\\resumeSubheading\s*"
        r"\{([^}]*)\}\s*"
        r"\{([^}]*)\}\s*"
        r"\{([^}]*)\}\s*"
        r"\{([^}]*)\}",
        re.DOTALL,
    )

    experiences = [
        MasterExperience(
            company=match.group(1).strip(),
            location=match.group(2).strip(),
            position=match.group(3).strip(),
            dates=match.group(4).strip(),
        )
        for match in pattern.finditer(experience_section)
    ]

    return MasterResume(experience=experiences)
