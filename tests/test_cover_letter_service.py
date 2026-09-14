import unittest
from pathlib import Path
from unittest.mock import patch

from app.models.job_posting import JobPosting
from app.models.tailored_cover_letter import TailoredCoverLetter
from app.services.cover_letter_service import (
    build_cover_letter_filename,
    generate_cover_letter,
    render_cover_letter,
    validate_master_cover_letter,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC_TEMPLATE_PATH = (
    PROJECT_ROOT
    / "examples"
    / "cover_letters"
    / "master_cover_letter.example.tex"
)


class CoverLetterTemplateTests(unittest.TestCase):
    def test_public_template_is_compatible(self):
        validate_master_cover_letter(
            SYNTHETIC_TEMPLATE_PATH.read_text(encoding="utf-8")
        )

    def test_rejects_template_without_generation_placeholders(self):
        with self.assertRaisesRegex(ValueError, "Missing required markers"):
            validate_master_cover_letter(
                r"\documentclass{letter}\begin{document}\end{document}"
            )

    def test_render_replaces_placeholders_and_escapes_latex(self):
        rendered = render_cover_letter(
            template="{{RECIPIENT}}|{{COMPANY}}|{{BODY}}",
            company="Example & Co.",
            tailored_cover_letter=TailoredCoverLetter(
                paragraphs=[
                    "A substantial first paragraph.",
                    "Built reliable APIs & services.",
                    "Thank you for considering my application.",
                ]
            ),
        )

        self.assertEqual(
            rendered,
            "Hiring Team|Example \\& Co.|"
            "A substantial first paragraph.\n\n"
            "Built reliable APIs \\& services.\n\n"
            "Thank you for considering my application.",
        )
        self.assertNotIn("{{", rendered)

    def test_builds_portable_filename(self):
        filename = build_cover_letter_filename(
            "Example & Co.",
            "Senior Python Engineer",
        )

        self.assertRegex(
            filename,
            r"^\d{4}-\d{2}-\d{2}_Example-Co_Senior-Python-Engineer_Cover_Letter\.tex$",
        )


class CoverLetterGenerationTests(unittest.TestCase):
    @patch("app.services.cover_letter_service.save_generated_cover_letter")
    @patch("app.services.cover_letter_service.generate_tailored_cover_letter")
    @patch("app.services.cover_letter_service.load_master_resume")
    def test_generates_and_saves_cover_letter(
        self,
        load_resume,
        tailor,
        save,
    ):
        load_resume.return_value = "master resume"
        tailor.return_value = TailoredCoverLetter(
            paragraphs=[
                "A substantial opening paragraph.",
                "A substantial experience paragraph.",
                "A substantial closing paragraph.",
            ]
        )
        save.return_value = Path("cover_letters/generated/letter.tex")
        stages = []
        job = JobPosting(
            company="Example Labs",
            title="Software Engineer",
            description="Build reliable Python services.",
        )

        output = generate_cover_letter(
            job,
            template="{{RECIPIENT}} {{COMPANY}} {{BODY}}",
            progress_callback=stages.append,
        )

        self.assertEqual(output.name, "letter.tex")
        self.assertEqual(
            stages,
            ["tailoring_cover_letter", "rendering_cover_letter"],
        )
        tailor.assert_called_once_with(
            job_description=job.description,
            company=job.company,
            job_title=job.title,
            master_resume="master resume",
        )
        self.assertIn("Example Labs", save.call_args.args[1])


if __name__ == "__main__":
    unittest.main()
