import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from openai import APIConnectionError
from httpx2 import Request

from app.main import app
from app.models.job_posting import JobPosting


class WebUiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_home_page_loads_resume_form(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Tailor your application to the role", response.text)
        self.assertIn('id="resume-form"', response.text)
        self.assertIn('id="include-cover-letter"', response.text)

    @patch("app.main.generate_resume_from_job_posting")
    def test_generate_endpoint_returns_downloadable_filename(self, generate):
        job = JobPosting(
            company="Example Labs",
            title="Software Engineer",
            description="Build Python services.",
        )
        generate.return_value = (
            job,
            Path("resumes/generated/example.tex"),
        )

        response = self.client.post(
            "/resumes/tailor",
            json={
                "job_posting": (
                    "Example Labs needs a Python engineer to build reliable APIs."
                )
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "company": "Example Labs",
                "job_title": "Software Engineer",
                "filename": "example.tex",
                "cover_letter_filename": None,
            },
        )

    @patch(
        "app.services.generation_job_service.generate_resume_from_job_posting"
    )
    def test_background_generation_job_can_be_polled(self, generate):
        def generate_resume(raw_posting, progress_callback):
            progress_callback("reading_job_posting")
            progress_callback("tailoring_resume")
            progress_callback("rendering_resume")
            return (
                JobPosting(
                    company="Example Labs",
                    title="Software Engineer",
                    description="Build Python services.",
                ),
                Path("resumes/generated/example.tex"),
            )

        generate.side_effect = generate_resume

        created = self.client.post(
            "/resumes/tailor/jobs",
            json={
                "job_posting": (
                    "Example Labs needs a Python engineer to build reliable APIs."
                )
            },
        )
        status = self.client.get(
            f"/resumes/tailor/jobs/{created.json()['job_id']}"
        )

        self.assertEqual(created.status_code, 200)
        self.assertEqual(status.status_code, 200)
        self.assertEqual(status.json()["status"], "completed")
        self.assertEqual(status.json()["stage"], "complete")
        self.assertEqual(status.json()["result"]["filename"], "example.tex")

    @patch("app.main.generate_resume_from_job_posting")
    def test_generation_connection_error_has_helpful_response(self, generate):
        generate.side_effect = APIConnectionError(
            request=Request("POST", "https://api.openai.com/v1/responses")
        )

        response = self.client.post(
            "/resumes/tailor",
            json={
                "job_posting": (
                    "Example Labs needs a Python engineer to build reliable APIs."
                )
            },
        )

        self.assertEqual(response.status_code, 503)
        self.assertIn("could not connect to OpenAI", response.json()["detail"])

    def test_generate_endpoint_rejects_short_job_posting(self):
        response = self.client.post(
            "/resumes/tailor",
            json={"job_posting": "Too short"},
        )

        self.assertEqual(response.status_code, 422)

    @patch("app.main.analyze_job")
    def test_analysis_connection_error_has_helpful_response(self, analyze):
        analyze.side_effect = APIConnectionError(
            request=Request("POST", "https://api.openai.com/v1/responses")
        )

        response = self.client.post(
            "/analyze",
            json={
                "job_description": (
                    "Build reliable Python services and collaborate across teams."
                ),
                "resume": (
                    "Software engineer who builds reliable Python services and APIs."
                ),
            },
        )

        self.assertEqual(response.status_code, 503)
        self.assertIn("could not connect to OpenAI", response.json()["detail"])

    @patch("app.main.generate_resume_from_job_posting")
    def test_missing_master_resume_has_helpful_response(self, generate):
        generate.side_effect = FileNotFoundError("missing")

        response = self.client.post(
            "/resumes/tailor",
            json={
                "job_posting": (
                    "Example Labs needs a Python engineer to build reliable APIs."
                )
            },
        )

        self.assertEqual(response.status_code, 409)
        self.assertIn("Upload a compatible master resume", response.json()["detail"])

    def test_generated_resume_can_be_downloaded(self):
        with tempfile.TemporaryDirectory() as directory:
            resume_dir = Path(directory)
            (resume_dir / "example.tex").write_text(
                "generated resume",
                encoding="utf-8",
            )

            with patch("app.main.GENERATED_RESUME_DIR", resume_dir):
                response = self.client.get(
                    "/resumes/generated/example.tex/latex?download=true"
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "generated resume")
        self.assertIn(
            'filename="example.tex"',
            response.headers["content-disposition"],
        )

    def test_missing_resume_has_friendly_page(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch(
                "app.main.GENERATED_RESUME_DIR",
                Path(directory),
            ):
                response = self.client.get(
                    "/resumes/generated/missing.tex/latex"
                )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Resume not found.")

    def test_master_resume_status_reports_pdf_capability(self):
        with tempfile.TemporaryDirectory() as directory:
            resume_path = Path(directory) / "master_resume.tex"
            resume_path.write_text("resume", encoding="utf-8")

            with (
                patch("app.main.MASTER_RESUME_PATH", resume_path),
                patch("app.main.find_latex_engine", return_value="pdflatex"),
            ):
                response = self.client.get("/resumes/master")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "exists": True,
                "filename": "master_resume.tex",
                "pdf_supported": True,
            },
        )

    def test_master_resume_can_be_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            resume_path = Path(directory) / "master_resume.tex"

            def save_resume(content):
                resume_path.write_text(content, encoding="utf-8")
                return resume_path

            with (
                patch("app.main.MASTER_RESUME_PATH", resume_path),
                patch("app.main.replace_master_resume", side_effect=save_resume),
                patch("app.main.find_latex_engine", return_value=None),
            ):
                response = self.client.post(
                    "/resumes/master",
                    json={"filename": "resume.tex", "content": "latex source"},
                )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["exists"])

    def test_master_resume_rejects_filename_with_path_segments(self):
        response = self.client.post(
            "/resumes/master",
            json={"filename": "../resume.tex", "content": "latex source"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Upload a .tex file.")

    def test_master_cover_letter_status_reports_availability(self):
        with tempfile.TemporaryDirectory() as directory:
            cover_letter_path = Path(directory) / "master_cover_letter.tex"
            cover_letter_path.write_text("template", encoding="utf-8")

            with (
                patch("app.main.MASTER_COVER_LETTER_PATH", cover_letter_path),
                patch("app.main.find_latex_engine", return_value="tectonic"),
            ):
                response = self.client.get("/cover-letters/master")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "exists": True,
                "filename": "master_cover_letter.tex",
                "pdf_supported": True,
            },
        )

    @patch("app.main.generate_cover_letter")
    @patch("app.main.load_master_cover_letter", return_value="cover template")
    @patch("app.main.generate_resume_from_job_posting")
    def test_generate_endpoint_can_include_cover_letter(
        self,
        generate_resume,
        load_cover_letter,
        generate_cover_letter,
    ):
        job = JobPosting(
            company="Example Labs",
            title="Software Engineer",
            description="Build Python services.",
        )
        generate_resume.return_value = (
            job,
            Path("resumes/generated/example.tex"),
        )
        generate_cover_letter.return_value = Path(
            "cover_letters/generated/letter.tex"
        )

        response = self.client.post(
            "/resumes/tailor",
            json={
                "job_posting": (
                    "Example Labs needs a Python engineer to build reliable APIs."
                ),
                "include_cover_letter": True,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["cover_letter_filename"], "letter.tex")
        load_cover_letter.assert_called_once_with()
        generate_cover_letter.assert_called_once_with(
            job,
            template="cover template",
        )

    def test_master_cover_letter_can_be_uploaded(self):
        with tempfile.TemporaryDirectory() as directory:
            cover_letter_path = Path(directory) / "master_cover_letter.tex"

            def save_cover_letter(content):
                cover_letter_path.write_text(content, encoding="utf-8")
                return cover_letter_path

            with (
                patch("app.main.MASTER_COVER_LETTER_PATH", cover_letter_path),
                patch(
                    "app.main.replace_master_cover_letter",
                    side_effect=save_cover_letter,
                ),
                patch("app.main.find_latex_engine", return_value=None),
            ):
                response = self.client.post(
                    "/cover-letters/master",
                    json={"filename": "cover-letter.tex", "content": "template"},
                )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["exists"])

    def test_generated_cover_letter_can_be_downloaded(self):
        with tempfile.TemporaryDirectory() as directory:
            cover_letter_dir = Path(directory)
            (cover_letter_dir / "letter.tex").write_text(
                "generated cover letter",
                encoding="utf-8",
            )

            with patch(
                "app.main.GENERATED_COVER_LETTER_DIR",
                cover_letter_dir,
            ):
                response = self.client.get(
                    "/cover-letters/generated/letter.tex/latex?download=true"
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "generated cover letter")
        self.assertIn(
            'filename="letter.tex"',
            response.headers["content-disposition"],
        )

    def test_pdf_route_compiles_and_serves_inline(self):
        with tempfile.TemporaryDirectory() as directory:
            resume_dir = Path(directory)
            tex_path = resume_dir / "example.tex"
            pdf_path = resume_dir / "example.pdf"
            tex_path.write_text("latex", encoding="utf-8")
            pdf_path.write_bytes(b"%PDF-1.4 test")

            with (
                patch("app.main.GENERATED_RESUME_DIR", resume_dir),
                patch("app.main.compile_resume_pdf", return_value=pdf_path),
            ):
                response = self.client.get(
                    "/resumes/generated/example.tex/pdf"
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "application/pdf")
        self.assertEqual(
            response.headers["content-disposition"],
            'inline; filename="example.pdf"',
        )


if __name__ == "__main__":
    unittest.main()
