import unittest

from app.models.master_resume import MasterExperience, MasterResume
from app.models.tailored_resume import (
    TailoredBullet,
    TailoredExperience,
    TailoredResume,
)
from app.services.resume_renderer import (
    align_experience,
    escape_latex,
    render_bullet_header,
    render_experience,
    render_summary,
)


class LatexEscapingTests(unittest.TestCase):
    def test_escapes_each_latex_control_character_once(self):
        source = r"Python & C\C++: 100%_ready #1 $5 {ok} ~ ^"

        escaped = escape_latex(source)

        self.assertEqual(
            escaped,
            r"Python \& C\textbackslash{}C++: 100\%\_ready \#1 \$5 "
            r"\{ok\} \textasciitilde{} \textasciicircum{}",
        )

    def test_summary_uses_latex_escaping(self):
        self.assertEqual(
            render_summary("AI & platform engineer"),
            r"AI \& platform engineer",
        )

    def test_bullet_header_gets_exactly_one_colon(self):
        self.assertEqual(
            render_bullet_header("Application Integration"),
            "Application Integration:",
        )
        self.assertEqual(
            render_bullet_header("Application Integration:"),
            "Application Integration:",
        )


class ExperienceAlignmentTests(unittest.TestCase):
    def setUp(self):
        self.master = MasterResume(
            experience=[
                MasterExperience(
                    company="First Employer",
                    location="Remote",
                    position="Developer",
                    dates="2022--Present",
                ),
                MasterExperience(
                    company="Second Employer",
                    location="Remote",
                    position="Support Engineer",
                    dates="2020--2022",
                ),
            ]
        )

    def test_reordered_generation_is_aligned_by_employer_and_position(self):
        tailored = TailoredResume.model_construct(
            experience=[
                TailoredExperience(
                    company="Second Employer",
                    position="Support Engineer",
                    bullets=[TailoredBullet(header="Support", content="Second")],
                ),
                TailoredExperience(
                    company="First Employer",
                    position="Developer",
                    bullets=[TailoredBullet(header="Development", content="First")],
                ),
            ]
        )

        aligned = align_experience(self.master, tailored)
        rendered = render_experience(self.master, tailored)

        self.assertEqual(
            [experience.company for _, experience in aligned],
            ["First Employer", "Second Employer"],
        )
        self.assertLess(rendered.index("First"), rendered.index("Second"))

    def test_unknown_experience_is_rejected(self):
        tailored = TailoredResume.model_construct(
            experience=[
                TailoredExperience(
                    company="Unknown Employer",
                    position="Developer",
                    bullets=[],
                )
            ]
        )

        with self.assertRaisesRegex(ValueError, "First Employer"):
            align_experience(self.master, tailored)


if __name__ == "__main__":
    unittest.main()
