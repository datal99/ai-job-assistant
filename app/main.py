from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException
from openai import APIConnectionError, OpenAIError
from pydantic import BaseModel, ConfigDict, Field
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.services.llm import analyze_job
from app.models import JobAnalysisResponse
from app.models.generated_resume import (
    GeneratedResumeResponse,
    GenerateResumeRequest,
    GenerationJobCreated,
    GenerationJobStatus,
    MasterResumeStatus,
    MasterResumeUploadRequest,
)
from app.services.generation_job_service import generation_jobs
from app.services.resume_file_service import (
    LatexCompilationError,
    LatexCompilerUnavailable,
    compile_resume_pdf,
    find_latex_engine,
    replace_master_resume,
)
from app.services.resume_service import (
    GENERATED_RESUME_DIR,
    MASTER_RESUME_PATH,
    generate_resume_from_job_posting,
)

app = FastAPI()

APP_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")

class JobAnalysisRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    job_description: str = Field(min_length=40, max_length=50_000)
    resume: str = Field(min_length=40, max_length=1_000_000)


@app.get("/", include_in_schema=False)
def web_ui():
    return FileResponse(APP_DIR / "web" / "index.html")


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/analyze", response_model=JobAnalysisResponse)
def analyze(request: JobAnalysisRequest):

    prompt = f"""
You are a technical recruiter analyzing a candidate for a job.

Compare the candidate's resume against the job description.

JOB DESCRIPTION:
{request.job_description}

RESUME:
{request.resume}

Analyze the candidate and return:
- An overall match score from 0 to 100
- Skills that are strong matches
- Skills that are partial matches
- Required skills that are missing
- A short overall summary
"""

    try:
        return analyze_job(prompt)
    except APIConnectionError as error:
        raise HTTPException(
            status_code=503,
            detail="The app could not connect to OpenAI. Check the network and try again.",
        ) from error
    except OpenAIError as error:
        raise HTTPException(
            status_code=502,
            detail="OpenAI could not complete the request. Please try again.",
        ) from error


@app.post("/resumes/tailor", response_model=GeneratedResumeResponse)
def generate_resume(request: GenerateResumeRequest):
    try:
        job_posting, output_path = generate_resume_from_job_posting(
            request.job_posting
        )
    except APIConnectionError as error:
        raise HTTPException(
            status_code=503,
            detail="The app could not connect to OpenAI. Check the network and try again.",
        ) from error
    except OpenAIError as error:
        raise HTTPException(
            status_code=502,
            detail="OpenAI could not complete the request. Please try again.",
        ) from error
    except FileNotFoundError as error:
        raise HTTPException(
            status_code=409,
            detail="Upload a compatible master resume before generating.",
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=f"The resume could not be rendered: {error}",
        ) from error

    return GeneratedResumeResponse(
        company=job_posting.company,
        job_title=job_posting.title,
        filename=output_path.name,
    )


@app.post("/resumes/tailor/jobs", response_model=GenerationJobCreated)
def start_resume_generation(
    request: GenerateResumeRequest,
    background_tasks: BackgroundTasks,
):
    job_id = generation_jobs.create()
    background_tasks.add_task(
        generation_jobs.run,
        job_id,
        request.job_posting,
    )
    return GenerationJobCreated(job_id=job_id)


@app.get(
    "/resumes/tailor/jobs/{job_id}",
    response_model=GenerationJobStatus,
)
def resume_generation_status(job_id: str):
    status = generation_jobs.get(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Generation job not found.")
    return status


@app.get("/resumes/master", response_model=MasterResumeStatus)
def master_resume_status():
    return MasterResumeStatus(
        exists=MASTER_RESUME_PATH.is_file(),
        filename=MASTER_RESUME_PATH.name,
        pdf_supported=find_latex_engine() is not None,
    )


@app.post("/resumes/master", response_model=MasterResumeStatus)
def upload_master_resume(request: MasterResumeUploadRequest):
    if (
        Path(request.filename).name != request.filename
        or Path(request.filename).suffix.lower() != ".tex"
    ):
        raise HTTPException(status_code=400, detail="Upload a .tex file.")

    try:
        replace_master_resume(request.content)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except OSError as error:
        raise HTTPException(
            status_code=500,
            detail="The master resume could not be saved.",
        ) from error

    return master_resume_status()


def serve_resume_file(
    tex_path: Path,
    file_format: str,
    download: bool,
):
    if not tex_path.is_file():
        raise HTTPException(status_code=404, detail="Resume not found.")

    if file_format == "latex":
        output_path = tex_path
        media_type = "text/plain; charset=utf-8"
    elif file_format == "pdf":
        try:
            output_path = compile_resume_pdf(tex_path)
        except LatexCompilerUnavailable as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        except LatexCompilationError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        media_type = "application/pdf"
    else:
        raise HTTPException(status_code=404, detail="Format not found.")

    if download:
        return FileResponse(
            output_path,
            media_type=media_type,
            filename=output_path.name,
        )

    return FileResponse(
        output_path,
        media_type=media_type,
        headers={"Content-Disposition": f'inline; filename="{output_path.name}"'},
    )


@app.get("/resumes/master/{file_format}", include_in_schema=False)
def get_master_resume(file_format: str, download: bool = False):
    return serve_resume_file(MASTER_RESUME_PATH, file_format, download)


@app.get(
    "/resumes/generated/{filename}/{file_format}",
    include_in_schema=False,
)
def get_generated_resume(
    filename: str,
    file_format: str,
    download: bool = False,
):
    output_path = GENERATED_RESUME_DIR / filename

    if Path(filename).name != filename or output_path.suffix != ".tex":
        raise HTTPException(status_code=404, detail="Resume not found.")

    return serve_resume_file(output_path, file_format, download)
