import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.services.resume_file_service import validate_master_resume
from app.services.template_service import create_resume_template


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC_RESUME = (
    PROJECT_ROOT / "examples" / "resumes" / "master_resume.example.tex"
)
SYNTHETIC_JOB = (
    PROJECT_ROOT / "examples" / "job_descriptions" / "software_engineer.txt"
)


class PublicExampleTests(unittest.TestCase):
    def test_synthetic_master_resume_is_compatible(self):
        content = SYNTHETIC_RESUME.read_text(encoding="utf-8")

        validate_master_resume(content)

    def test_synthetic_resume_keeps_headings_with_content(self):
        content = SYNTHETIC_RESUME.read_text(encoding="utf-8")

        self.assertIn(r"\usepackage{needspace}", content)
        self.assertIn(r"\Needspace{7\baselineskip}", content)

    def test_synthetic_master_resume_builds_a_template(self):
        with tempfile.TemporaryDirectory() as directory:
            template_path = Path(directory) / "resume_template.tex"
            with (
                patch(
                    "app.services.template_service.MASTER_CV_PATH",
                    SYNTHETIC_RESUME,
                ),
                patch(
                    "app.services.template_service.TEMPLATE_CV_PATH",
                    template_path,
                ),
            ):
                result = create_resume_template()

            template = result.read_text(encoding="utf-8")

        for placeholder in (
            "{{SUMMARY}}",
            "{{EXPERIENCE}}",
            "{{PROJECTS}}",
            "{{TECHNICAL_SKILLS}}",
        ):
            self.assertIn(placeholder, template)

    def test_synthetic_job_description_is_substantial(self):
        content = SYNTHETIC_JOB.read_text(encoding="utf-8")

        self.assertGreaterEqual(len(content.strip()), 40)
        self.assertIn("Northstar Analytics", content)


if __name__ == "__main__":
    unittest.main()
