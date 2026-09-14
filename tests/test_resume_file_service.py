import tempfile
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from app.services.resume_file_service import (
    LatexCompilerUnavailable,
    compile_resume_pdf,
    validate_master_resume,
)


VALID_MASTER_RESUME = r"""
\documentclass{article}
%-----------SUMMARY-----------------
Summary
%-----------EDUCATION-----------------
Education
%-----------EXPERIENCE-----------------
Experience
%-----------PROJECTS-----------------
Projects
%--------TECHNICAL SKILLS------------
Skills
%-----------LANGUAGES-----------------
Languages
\end{document}
"""


class MasterResumeValidationTests(unittest.TestCase):
    def test_accepts_compatible_master_resume(self):
        validate_master_resume(VALID_MASTER_RESUME)

    def test_rejects_file_without_required_sections(self):
        with self.assertRaisesRegex(ValueError, "Missing required markers"):
            validate_master_resume(r"\documentclass{article}\end{document}")


class PdfCompilationTests(unittest.TestCase):
    def test_reports_when_no_latex_engine_is_available(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch(
                "app.services.resume_file_service.find_latex_engine",
                return_value=None,
            ),
        ):
            tex_path = Path(directory) / "resume.tex"
            tex_path.write_text("latex", encoding="utf-8")

            with self.assertRaises(LatexCompilerUnavailable):
                compile_resume_pdf(tex_path)

    def test_uses_tectonic_output_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            tex_path = Path(directory) / "resume.tex"
            pdf_path = tex_path.with_suffix(".pdf")
            tex_path.write_text("latex", encoding="utf-8")

            def run_compiler(command, **kwargs):
                pdf_path.write_bytes(b"%PDF-1.4 test")
                return CompletedProcess(command, 0, stdout="", stderr="")

            with (
                patch(
                    "app.services.resume_file_service.find_latex_engine",
                    return_value="tectonic",
                ),
                patch(
                    "app.services.resume_file_service.subprocess.run",
                    side_effect=run_compiler,
                ) as run,
            ):
                result = compile_resume_pdf(tex_path)

        self.assertEqual(result, pdf_path)
        command = run.call_args.args[0]
        self.assertEqual(command[:2], ["tectonic", "--outdir"])

    def test_tectonic_normalizes_legacy_hyperref_driver(self):
        with tempfile.TemporaryDirectory() as directory:
            tex_path = Path(directory) / "resume.tex"
            pdf_path = tex_path.with_suffix(".pdf")
            tex_path.write_text(
                r"\usepackage[pdftex]{hyperref}",
                encoding="utf-8",
            )

            def run_compiler(command, **kwargs):
                compilation_path = Path(command[-1])
                self.assertEqual(
                    compilation_path.read_text(encoding="utf-8"),
                    r"\usepackage{hyperref}",
                )
                compilation_path.with_suffix(".pdf").write_bytes(
                    b"%PDF-1.4 test"
                )
                return CompletedProcess(command, 0, stdout="", stderr="")

            with (
                patch(
                    "app.services.resume_file_service.find_latex_engine",
                    return_value="tectonic",
                ),
                patch(
                    "app.services.resume_file_service.subprocess.run",
                    side_effect=run_compiler,
                ),
            ):
                result = compile_resume_pdf(tex_path)

            self.assertEqual(result, pdf_path)
            self.assertTrue(pdf_path.is_file())
            self.assertFalse(
                tex_path.with_name(".resume.tectonic.tex").exists()
            )
            self.assertEqual(
                tex_path.read_text(encoding="utf-8"),
                r"\usepackage[pdftex]{hyperref}",
            )


if __name__ == "__main__":
    unittest.main()
