import unittest
from pathlib import Path
from unittest.mock import patch

from app.models.job_posting import JobPosting
from app.services.generation_job_service import GenerationJobManager


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
                "rendering_resume",
            ],
        )

    def test_unknown_job_returns_none(self):
        self.assertIsNone(GenerationJobManager().get("missing"))

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


if __name__ == "__main__":
    unittest.main()
