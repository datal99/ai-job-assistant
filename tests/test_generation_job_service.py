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


if __name__ == "__main__":
    unittest.main()
