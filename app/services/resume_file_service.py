import os
import shutil
import subprocess
from pathlib import Path

from app.services.resume_service import MASTER_RESUME_PATH
from app.services.template_service import create_resume_template


class LatexCompilerUnavailable(RuntimeError):
    pass


class LatexCompilationError(RuntimeError):
    pass


REQUIRED_MASTER_MARKERS = (
    r"\documentclass",
    "%-----------SUMMARY-----------------",
    "%-----------EDUCATION-----------------",
    "%-----------EXPERIENCE-----------------",
    "%-----------PROJECTS-----------------",
    "%--------TECHNICAL SKILLS------------",
    "%-----------LANGUAGES-----------------",
    r"\end{document}",
)


def find_latex_engine() -> str | None:
    configured_engine = os.getenv("LATEX_ENGINE")
    local_tectonic = (
        MASTER_RESUME_PATH.parents[2] / "tools" / "tectonic" / "tectonic.exe"
    )
    candidates = (
        [configured_engine]
        if configured_engine
        else [
            str(local_tectonic),
            "tectonic",
            "pdflatex",
            "xelatex",
            "lualatex",
        ]
    )

    for candidate in candidates:
        if candidate and shutil.which(candidate):
            return candidate

    return None


def validate_master_resume(content: str) -> None:
    missing = [marker for marker in REQUIRED_MASTER_MARKERS if marker not in content]
    if missing:
        raise ValueError(
            "The uploaded file is not a compatible master resume. "
            f"Missing required markers: {', '.join(missing)}"
        )

    positions = [content.index(marker) for marker in REQUIRED_MASTER_MARKERS]
    if positions != sorted(positions):
        raise ValueError("The master resume sections are in an unexpected order.")


def replace_master_resume(content: str) -> Path:
    validate_master_resume(content)
    MASTER_RESUME_PATH.parent.mkdir(parents=True, exist_ok=True)

    temporary_path = MASTER_RESUME_PATH.with_suffix(".uploading.tex")
    backup_path = MASTER_RESUME_PATH.with_suffix(".backup.tex")
    had_existing_resume = MASTER_RESUME_PATH.exists()

    temporary_path.write_text(content, encoding="utf-8")
    if had_existing_resume:
        shutil.copy2(MASTER_RESUME_PATH, backup_path)

    temporary_path.replace(MASTER_RESUME_PATH)

    try:
        create_resume_template()
    except Exception:
        if had_existing_resume and backup_path.exists():
            shutil.copy2(backup_path, MASTER_RESUME_PATH)
        else:
            MASTER_RESUME_PATH.unlink(missing_ok=True)
        raise

    return MASTER_RESUME_PATH


def compile_resume_pdf(tex_path: Path) -> Path:
    engine = find_latex_engine()
    if not engine:
        raise LatexCompilerUnavailable(
            "PDF export requires Tectonic, pdflatex, xelatex, or lualatex. "
            "Install a LaTeX distribution or set LATEX_ENGINE to its executable."
        )

    output_path = tex_path.with_suffix(".pdf")
    engine_name = Path(engine).stem.lower()
    compilation_path = tex_path
    temporary_source: Path | None = None
    if engine_name == "tectonic":
        source = tex_path.read_text(encoding="utf-8")
        compatible_source = source.replace(
            r"\usepackage[pdftex]{hyperref}",
            r"\usepackage{hyperref}",
        )
        if compatible_source != source:
            temporary_source = tex_path.with_name(
                f".{tex_path.stem}.tectonic.tex"
            )
            temporary_source.write_text(compatible_source, encoding="utf-8")
            compilation_path = temporary_source

        command = [
            engine,
            "--outdir",
            str(tex_path.parent),
            str(compilation_path),
        ]
    else:
        command = [
            engine,
            "-no-shell-escape",
            "-interaction=nonstopmode",
            "-halt-on-error",
            f"-output-directory={tex_path.parent}",
            str(tex_path),
        ]

    try:
        result = subprocess.run(
            command,
            cwd=tex_path.parent,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        if temporary_source:
            temporary_source.unlink(missing_ok=True)
        raise LatexCompilationError(
            "LaTeX compilation timed out after 120 seconds."
        ) from error
    except OSError as error:
        if temporary_source:
            temporary_source.unlink(missing_ok=True)
        raise LatexCompilationError(
            "The configured LaTeX engine could not be started."
        ) from error

    for suffix in (".aux", ".log", ".out", ".xdv"):
        compilation_path.with_suffix(suffix).unlink(missing_ok=True)

    compiled_output = compilation_path.with_suffix(".pdf")
    if temporary_source:
        temporary_source.unlink(missing_ok=True)
        if compiled_output.is_file():
            compiled_output.replace(output_path)

    if result.returncode != 0 or not output_path.is_file():
        details = "\n".join(
            output
            for output in (result.stdout, result.stderr)
            if output
        )[-2500:]
        raise LatexCompilationError(
            "LaTeX could not compile this resume. "
            f"Compiler output: {details.strip()}"
        )

    return output_path
