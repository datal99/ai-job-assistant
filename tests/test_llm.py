import unittest
from types import SimpleNamespace
from unittest.mock import patch

from pydantic import ValidationError

from app.models import JobAnalysisResponse
from app.models.resume_validation import ResumeValidationResult
from app.models.tailored_resume import TailoredResume
from app.services.llm import (
    MODEL,
    analyze_job,
    build_resume_tailoring_prompt,
    generate_tailored_resume,
    parse,
    StructuredOutputError,
    validate_tailored_resume_content,
)


class ResumeTailoringPromptTests(unittest.TestCase):
    def test_summary_guidance_is_specific_and_grounded(self):
        prompt = build_resume_tailoring_prompt(
            "Build reliable payment services.",
            "Four years of supported software experience.",
        )

        self.assertIn("exactly three concise resume-style statements", prompt)
        self.assertIn("45 to 70 words", prompt)
        self.assertIn("not a compressed skills", prompt)
        self.assertIn("pronoun-free, implied-first-person voice", prompt)
        self.assertIn('"builds", "brings", "contributes", or "delivers"', prompt)
        self.assertIn('resume construction such as "Strong background in..."', prompt)
        self.assertNotIn("sentence fragments, first-person language", prompt)
        self.assertIn("two to four core technical areas", prompt)
        self.assertIn("job posting makes them central responsibilities", prompt)
        self.assertIn("DevOps, platform, build/release", prompt)
        self.assertIn('Avoid slash-separated tool clusters such as "Git/GitLab CI/CD"', prompt)
        self.assertIn("only when the job description makes it relevant", prompt)
        self.assertIn("the summary must explicitly mention", prompt)
        self.assertIn("Preserve the primary nature of every employment role", prompt)
        self.assertIn("include all projects from the master CV", prompt)
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
        self.assertIn("exactly three concise resume-style statements", prompt)
        self.assertIn("JOB DESCRIPTION:\njob description", prompt)
        self.assertIn("MASTER CV:\nmaster resume", prompt)

    @patch("app.services.llm.parse")
    def test_resume_revision_includes_validation_feedback(self, parse):
        expected = TailoredResume.model_construct()
        parse.return_value = expected

        result = generate_tailored_resume(
            "AI enablement role",
            "master resume",
            validation_feedback="Summary omitted supported AI project work.",
        )

        self.assertIs(result, expected)
        prompt = parse.call_args.kwargs["prompt"]
        self.assertIn("REVISION REQUIRED", prompt)
        self.assertIn("Summary omitted supported AI project work.", prompt)
        self.assertIn("Do not copy claims from", prompt)


class ModelConfigurationTests(unittest.TestCase):
    def test_model_is_gpt_5_6_terra(self):
        self.assertEqual(MODEL, "gpt-5.6-terra")

    @patch("app.services.llm.client.responses.parse")
    def test_structured_generation_uses_configured_model(self, responses_parse):
        expected = TailoredResume.model_construct()
        responses_parse.return_value = SimpleNamespace(output_parsed=expected)

        result = parse("prompt", TailoredResume)

        self.assertIs(result, expected)
        self.assertEqual(responses_parse.call_args.kwargs["model"], MODEL)


class ResumeExperienceValidationPromptTests(unittest.TestCase):
    @patch("app.services.llm.parse")
    def test_validation_requires_employer_specific_grounding(self, parse):
        tailored = TailoredResume.model_construct(
            summary="Software Engineer focused on AI systems.",
            experience=[],
            projects=[],
        )
        expected = ResumeValidationResult(is_valid=True, issues=[])
        parse.return_value = expected

        result = validate_tailored_resume_content(
            "AI platform role",
            "master source",
            tailored,
        )

        self.assertIs(result, expected)
        self.assertIs(
            parse.call_args.kwargs["response_model"],
            ResumeValidationResult,
        )
        prompt = parse.call_args.kwargs["prompt"]
        self.assertIn("generated experience and project selections", prompt)
        self.assertIn("when the posting centers on DevOps", prompt)
        self.assertIn('merged labels such as "Git/GitLab CI/CD"', prompt)
        self.assertIn("correct employer and position", prompt)
        self.assertIn("does not prove", prompt)
        self.assertIn("Do not accept a plausible inference", prompt)
        self.assertIn("application-development evidence", prompt)
        self.assertIn("less relevant non-AI project", prompt)
        self.assertIn("AI platform role", prompt)
        self.assertIn("master source", prompt)


class StructuredOutputParsingTests(unittest.TestCase):
    @patch("app.services.llm.client.responses.parse")
    def test_structured_generation_retries_invalid_json(self, responses_parse):
        invalid = ValidationError.from_exception_data("Test", [])
        expected = TailoredResume.model_construct()
        responses_parse.side_effect = [
            invalid,
            SimpleNamespace(output_parsed=expected),
        ]

        result = parse("prompt", TailoredResume)

        self.assertIs(result, expected)
        self.assertEqual(responses_parse.call_count, 2)

    @patch("app.services.llm.client.responses.parse")
    def test_structured_generation_has_clear_error_after_retries(
        self,
        responses_parse,
    ):
        responses_parse.return_value = SimpleNamespace(output_parsed=None)

        with self.assertRaisesRegex(
            StructuredOutputError,
            "incomplete or invalid structured response",
        ):
            parse("prompt", TailoredResume)

        self.assertEqual(responses_parse.call_count, 2)

    @patch("app.services.llm.client.responses.parse")
    def test_job_analysis_uses_configured_model(self, responses_parse):
        expected = JobAnalysisResponse.model_construct()
        responses_parse.return_value = SimpleNamespace(output_parsed=expected)

        result = analyze_job("prompt")

        self.assertIs(result, expected)
        self.assertEqual(responses_parse.call_args.kwargs["model"], MODEL)


if __name__ == "__main__":
    unittest.main()
