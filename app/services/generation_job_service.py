import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock
from uuid import uuid4

from openai import APIConnectionError, OpenAIError

from app.models.generated_resume import (
    GeneratedResumeResponse,
    GenerationJobStatus,
    GenerationStage,
    GenerationStatus,
    RevisionReason,
)
from app.services.cover_letter_service import (
    MissingCoverLetterTemplate,
    generate_cover_letter,
    load_master_cover_letter,
)
from app.services.resume_service import (
    ResumeGroundingError,
    generate_resume_from_job_posting,
)
from app.services.llm import StructuredOutputError


logger = logging.getLogger(__name__)


REVISION_GUIDANCE: dict[RevisionReason, str] = {
    "summary_focus": (
        "Make the professional summary more directly reflect the posting's "
        "central responsibilities and required qualifications."
    ),
    "emphasize_programming": (
        "Retain and emphasize supported programming and application-development "
        "work in the employment history."
    ),
    "project_selection": (
        "Reassess project selection and prefer the projects most directly "
        "relevant to this job."
    ),
    "reduce_keyword_density": (
        "Use natural resume prose and reduce keyword-list phrasing."
    ),
    "preserve_source_detail": (
        "Preserve more useful, supported detail from the master resume while "
        "remaining concise."
    ),
    "strengthen_ai_relevance": (
        "When supported by the master resume and relevant to the posting, make "
        "AI, LLM, and agent work more visible."
    ),
    "cover_letter_specificity": (
        "Make the cover letter more specific to the role and the candidate's "
        "supported experience."
    ),
}


def build_revision_feedback(revision_reasons: list[RevisionReason] | None) -> str | None:
    if not revision_reasons:
        return None
    return "\n".join(
        f"- {REVISION_GUIDANCE[reason]}" for reason in revision_reasons
    )


@dataclass
class GenerationJob:
    job_id: str
    started_at: datetime
    status: GenerationStatus = "queued"
    stage: GenerationStage = "queued"
    result: GeneratedResumeResponse | None = None
    error: str | None = None
    raw_job_posting: str = ""
    include_cover_letter: bool = False


class GenerationJobManager:
    def __init__(self, max_jobs: int = 100) -> None:
        if max_jobs < 1:
            raise ValueError("max_jobs must be at least 1")

        self._jobs: dict[str, GenerationJob] = {}
        self._lock = Lock()
        self._max_jobs = max_jobs

    def create(
        self,
        raw_job_posting: str = "",
        include_cover_letter: bool = False,
    ) -> str:
        job_id = uuid4().hex
        with self._lock:
            while len(self._jobs) >= self._max_jobs:
                oldest_job_id = next(iter(self._jobs))
                self._jobs.pop(oldest_job_id)
            self._jobs[job_id] = GenerationJob(
                job_id=job_id,
                started_at=datetime.now(timezone.utc),
                raw_job_posting=raw_job_posting,
                include_cover_letter=include_cover_letter,
            )
        return job_id

    def retry_inputs(self, job_id: str) -> tuple[str, bool] | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job or job.status not in ("completed", "failed"):
                return None
            return job.raw_job_posting, job.include_cover_letter

    def update_stage(self, job_id: str, stage: GenerationStage) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.status = "running"
            job.stage = stage

    def run(
        self,
        job_id: str,
        raw_job_posting: str,
        include_cover_letter: bool = False,
        revision_reasons: list[RevisionReason] | None = None,
    ) -> None:
        try:
            revision_feedback = build_revision_feedback(revision_reasons)
            cover_letter_template = (
                load_master_cover_letter() if include_cover_letter else None
            )
            resume_kwargs = {
                "progress_callback": lambda stage: self.update_stage(job_id, stage)
            }
            if revision_feedback:
                resume_kwargs["revision_feedback"] = revision_feedback
            job_posting, output_path = generate_resume_from_job_posting(
                raw_job_posting,
                **resume_kwargs,
            )
            cover_letter_path = None
            if include_cover_letter:
                cover_letter_kwargs = {
                    "template": cover_letter_template,
                    "progress_callback": (
                        lambda stage: self.update_stage(job_id, stage)
                    ),
                }
                if revision_feedback:
                    cover_letter_kwargs["revision_feedback"] = revision_feedback
                cover_letter_path = generate_cover_letter(
                    job_posting,
                    **cover_letter_kwargs,
                )
            result = GeneratedResumeResponse(
                company=job_posting.company,
                job_title=job_posting.title,
                filename=output_path.name,
                cover_letter_filename=(
                    cover_letter_path.name if cover_letter_path else None
                ),
            )
        except APIConnectionError:
            self.fail(
                job_id,
                "The app could not connect to OpenAI. Check the network and try again.",
            )
            return
        except OpenAIError:
            self.fail(
                job_id,
                "OpenAI could not complete the request. Please try again.",
            )
            return
        except StructuredOutputError:
            self.fail(
                job_id,
                "OpenAI returned an incomplete response. Please try again.",
            )
            return
        except ResumeGroundingError as error:
            self.fail(job_id, str(error))
            return
        except MissingCoverLetterTemplate:
            self.fail(
                job_id,
                "Upload a compatible master cover letter before generating one.",
            )
            return
        except FileNotFoundError:
            self.fail(
                job_id,
                "Upload a compatible master resume before generating.",
            )
            return
        except ValueError as error:
            self.fail(
                job_id,
                f"The application materials could not be rendered: {error}",
            )
            return
        except Exception:
            logger.exception(
                "Unexpected resume generation failure",
                extra={"job_id": job_id},
            )
            self.fail(
                job_id,
                "The resume could not be generated. Check the server log and try again.",
            )
            return

        with self._lock:
            job = self._jobs[job_id]
            job.status = "completed"
            job.stage = "complete"
            job.result = result

    def fail(self, job_id: str, message: str) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.status = "failed"
            job.error = message

    def get(self, job_id: str) -> GenerationJobStatus | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None

            elapsed = datetime.now(timezone.utc) - job.started_at
            return GenerationJobStatus(
                job_id=job.job_id,
                status=job.status,
                stage=job.stage,
                elapsed_seconds=max(0, int(elapsed.total_seconds())),
                result=job.result,
                error=job.error,
            )


generation_jobs = GenerationJobManager()
