import unittest
from pathlib import Path
from unittest.mock import patch

from app.models.job_posting import JobPosting
from app.services.cover_letter_service import MissingCoverLetterTemplate
from app.services.generation_job_service import (
    GenerationJobManager,
    build_revision_feedback,
)
from app.services.llm import StructuredOutputError
from app.services.resume_service import ResumeGroundingError


class GenerationJobManagerTests(unittest.TestCase):
    @patch(
        "app.services.generation_job_service.generate_resume_from_job_posting"
    )
    def test_completed_job_includes_result_and_progress(self, generate):
        observed_stages = []

        def generate_resume(raw_posting, progress_callback):
            for stage in (
                "reading_job_posting",
                "tailoring_resume",
                "validating_resume",
                "rendering_resume",
            ):
                progress_callback(stage)
                observed_stages.append(stage)

            return (
                JobPosting(
                    company="Example Labs",
                    title="Software Engineer",
                    description="Build services.",
                ),
                Path("resumes/generated/example.tex"),
            )

        generate.side_effect = generate_resume
        manager = GenerationJobManager()
        job_id = manager.create()

        manager.run(job_id, "raw posting")
        status = manager.get(job_id)

        self.assertIsNotNone(status)
        self.assertEqual(status.status, "completed")
        self.assertEqual(status.stage, "complete")
        self.assertEqual(status.result.filename, "example.tex")
        self.assertEqual(
            observed_stages,
            [
                "reading_job_posting",
                "tailoring_resume",
                "validating_resume",
                "rendering_resume",
            ],
        )

    def test_unknown_job_returns_none(self):
        self.assertIsNone(GenerationJobManager().get("missing"))

    def test_failed_job_retains_inputs_for_manual_retry(self):
        manager = GenerationJobManager()
        job_id = manager.create("original posting", include_cover_letter=True)
        manager.fail(job_id, "Try again.")

        self.assertEqual(
            manager.retry_inputs(job_id),
            ("original posting", True),
        )

    def test_running_job_cannot_be_retried(self):
        manager = GenerationJobManager()
        job_id = manager.create("original posting")
        manager.update_stage(job_id, "tailoring_resume")

        self.assertIsNone(manager.retry_inputs(job_id))

    def test_revision_reasons_become_bounded_prompt_guidance(self):
        feedback = build_revision_feedback(
            ["summary_focus", "project_selection"]
        )

        self.assertIn("professional summary", feedback)
        self.assertIn("project selection", feedback)

    def test_job_history_is_bounded(self):
        manager = GenerationJobManager(max_jobs=2)
        first_job = manager.create()
        second_job = manager.create()
        third_job = manager.create()

        self.assertIsNone(manager.get(first_job))
        self.assertIsNotNone(manager.get(second_job))
        self.assertIsNotNone(manager.get(third_job))

    def test_job_limit_must_be_positive(self):
        with self.assertRaisesRegex(ValueError, "at least 1"):
            GenerationJobManager(max_jobs=0)

    @patch(
        "app.services.generation_job_service.generate_resume_from_job_posting",
        side_effect=FileNotFoundError("missing"),
    )
    def test_missing_master_resume_has_actionable_failure(self, generate):
        manager = GenerationJobManager()
        job_id = manager.create()

        manager.run(job_id, "raw posting")

        self.assertEqual(
            manager.get(job_id).error,
            "Upload a compatible master resume before generating.",
        )

    @patch(
        "app.services.generation_job_service.generate_resume_from_job_posting",
        side_effect=StructuredOutputError("invalid structured response"),
    )
    def test_incomplete_openai_response_has_actionable_failure(self, generate):
        manager = GenerationJobManager()
        job_id = manager.create()

        manager.run(job_id, "raw posting")

        self.assertEqual(
            manager.get(job_id).error,
            "OpenAI returned an incomplete response. Please try again.",
        )

    @patch(
        "app.services.generation_job_service.generate_resume_from_job_posting",
        side_effect=ResumeGroundingError("Unsupported experience claim."),
    )
    def test_unsupported_experience_has_actionable_failure(self, generate):
        manager = GenerationJobManager()
        job_id = manager.create()

        manager.run(job_id, "raw posting")

        self.assertEqual(
            manager.get(job_id).error,
            "Unsupported experience claim.",
        )

    @patch(
        "app.services.generation_job_service.generate_cover_letter"
    )
    @patch(
        "app.services.generation_job_service.load_master_cover_letter",
        return_value="cover template",
    )
    @patch(
        "app.services.generation_job_service.generate_resume_from_job_posting"
    )
    def test_job_can_generate_resume_and_cover_letter(
        self,
        generate_resume,
        load_cover_letter,
        generate_cover_letter,
    ):
        job = JobPosting(
            company="Example Labs",
            title="Software Engineer",
            description="Build services.",
        )
        generate_resume.return_value = (
            job,
            Path("resumes/generated/resume.tex"),
        )

        def generate_letter(job_posting, template, progress_callback):
            progress_callback("tailoring_cover_letter")
            progress_callback("rendering_cover_letter")
            return Path("cover_letters/generated/letter.tex")

        generate_cover_letter.side_effect = generate_letter
        manager = GenerationJobManager()
        job_id = manager.create()

        manager.run(job_id, "raw posting", include_cover_letter=True)
        status = manager.get(job_id)

        self.assertEqual(status.status, "completed")
        self.assertEqual(status.result.filename, "resume.tex")
        self.assertEqual(status.result.cover_letter_filename, "letter.tex")
        load_cover_letter.assert_called_once_with()
        generate_cover_letter.assert_called_once()

    @patch(
        "app.services.generation_job_service.load_master_cover_letter",
        side_effect=MissingCoverLetterTemplate("missing"),
    )
    def test_missing_cover_letter_fails_before_resume_generation(self, load):
        manager = GenerationJobManager()
        job_id = manager.create()

        manager.run(job_id, "raw posting", include_cover_letter=True)

        self.assertEqual(
            manager.get(job_id).error,
            "Upload a compatible master cover letter before generating one.",
        )

    @patch(
        "app.services.generation_job_service.generate_resume_from_job_posting"
    )
    def test_manual_retry_guidance_is_passed_to_resume_generation(self, generate):
        generate.return_value = (
            JobPosting(
                company="Example Labs",
                title="Software Engineer",
                description="Build services.",
            ),
            Path("resumes/generated/example.tex"),
        )
        manager = GenerationJobManager()
        job_id = manager.create("raw posting")

        manager.run(job_id, "raw posting", revision_reasons=["summary_focus"])

        feedback = generate.call_args.kwargs["revision_feedback"]
        self.assertIn("professional summary", feedback)


if __name__ == "__main__":
    unittest.main()
