import unittest
from pathlib import Path
from unittest.mock import patch

from app.models.job_posting import JobPosting
from app.models.master_resume import MasterExperience, MasterResume
from app.models.tailored_resume import (
    TailoredBullet,
    TailoredExperience,
    TailoredProject,
    TailoredResume,
    TailoredSkills,
)
from app.services.resume_service import generate_resume_from_job_posting


class GenerateResumeFromJobPostingTests(unittest.TestCase):
    def setUp(self):
        self.job = JobPosting(
            company="Example & Co.",
            title="Senior Python Engineer",
            description="Build Python services.",
        )
        self.master = MasterResume(
            experience=[
                MasterExperience(
                    company="Example Employer",
                    location="Remote",
                    position="Engineer",
                    dates="2020--Present",
                )
            ]
        )
        self.tailored = TailoredResume(
            summary="Python engineer",
            experience=[
                TailoredExperience(
                    company="Example Employer",
                    position="Engineer",
                    bullets=[
                        TailoredBullet(
                            header="APIs",
                            content="Built reliable services.",
                        )
                    ],
                )
            ],
            projects=[
                TailoredProject(
                    name="Service",
                    description="A Python API.",
                )
            ],
            technical_skills=TailoredSkills(
                programming=["Python"],
                ai_and_agent_development=[],
                frameworks_and_technologies=[],
                software_engineering=[],
                databases=[],
                testing_and_quality=[],
                development_tools=[],
                cloud_and_architecture=[],
                development_practices=[],
            ),
        )

    @patch("app.services.resume_service.save_generated_resume")
    @patch("app.services.resume_service.render_resume")
    @patch("app.services.resume_service.load_resume_template")
    @patch("app.services.resume_service.extract_master_resume_data")
    @patch("app.services.resume_service.tailor_resume")
    @patch("app.services.resume_service.extract_job_posting")
    def test_runs_the_complete_generation_pipeline(
        self,
        extract_job_posting,
        tailor_resume,
        extract_master_resume_data,
        load_resume_template,
        render_resume,
        save_generated_resume,
    ):
        extract_job_posting.return_value = self.job
        tailor_resume.return_value = self.tailored
        extract_master_resume_data.return_value = self.master
        load_resume_template.return_value = "template"
        render_resume.return_value = "rendered latex"
        save_generated_resume.return_value = Path("resumes/generated/output.tex")

        job, output_path = generate_resume_from_job_posting("raw posting")

        self.assertEqual(job, self.job)
        self.assertEqual(output_path.name, "output.tex")
        extract_job_posting.assert_called_once_with("raw posting")
        tailor_resume.assert_called_once_with(self.job.description)
        render_resume.assert_called_once_with(
            template="template",
            master_resume_data=self.master,
            tailored_resume=self.tailored,
        )
        saved_filename, saved_content = save_generated_resume.call_args.args
        self.assertRegex(
            saved_filename,
            r"^\d{4}-\d{2}-\d{2}_Example-Co_Senior-Python-Engineer_CV_Submitted\.tex$",
        )
        self.assertEqual(saved_content, "rendered latex")


if __name__ == "__main__":
    unittest.main()
