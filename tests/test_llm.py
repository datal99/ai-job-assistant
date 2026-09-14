import unittest
from unittest.mock import patch

from app.models.tailored_resume import TailoredResume
from app.services.llm import (
    build_resume_tailoring_prompt,
    generate_tailored_resume,
)


class ResumeTailoringPromptTests(unittest.TestCase):
    def test_summary_guidance_is_specific_and_grounded(self):
        prompt = build_resume_tailoring_prompt(
            "Build reliable payment services.",
            "Four years of supported software experience.",
        )

        self.assertIn("exactly three complete summary sentences", prompt)
        self.assertIn("45 to 70 words", prompt)
        self.assertIn("not a compressed skills", prompt)
        self.assertIn('first-person language, "proven"', prompt)
        self.assertIn("only when the job description makes it relevant", prompt)
        self.assertIn("Build reliable payment services.", prompt)
        self.assertIn("Four years of supported software experience.", prompt)

    @patch("app.services.llm.parse")
    def test_resume_generation_uses_the_constrained_prompt(self, parse):
        expected = TailoredResume.model_construct()
        parse.return_value = expected

        result = generate_tailored_resume("job description", "master resume")

        self.assertIs(result, expected)
        self.assertEqual(parse.call_args.kwargs["response_model"], TailoredResume)
        prompt = parse.call_args.kwargs["prompt"]
        self.assertIn("exactly three complete summary sentences", prompt)
        self.assertIn("JOB DESCRIPTION:\njob description", prompt)
        self.assertIn("MASTER CV:\nmaster resume", prompt)


if __name__ == "__main__":
    unittest.main()
