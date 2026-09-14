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
)
from app.services.resume_service import generate_resume_from_job_posting


logger = logging.getLogger(__name__)


@dataclass
class GenerationJob:
    job_id: str
    started_at: datetime
    status: GenerationStatus = "queued"
    stage: GenerationStage = "queued"
    result: GeneratedResumeResponse | None = None
    error: str | None = None


class GenerationJobManager:
    def __init__(self, max_jobs: int = 100) -> None:
        if max_jobs < 1:
            raise ValueError("max_jobs must be at least 1")

        self._jobs: dict[str, GenerationJob] = {}
        self._lock = Lock()
        self._max_jobs = max_jobs

    def create(self) -> str:
        job_id = uuid4().hex
        with self._lock:
            while len(self._jobs) >= self._max_jobs:
                oldest_job_id = next(iter(self._jobs))
                self._jobs.pop(oldest_job_id)
            self._jobs[job_id] = GenerationJob(
                job_id=job_id,
                started_at=datetime.now(timezone.utc),
            )
        return job_id

    def update_stage(self, job_id: str, stage: GenerationStage) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.status = "running"
            job.stage = stage

    def run(self, job_id: str, raw_job_posting: str) -> None:
        try:
            job_posting, output_path = generate_resume_from_job_posting(
                raw_job_posting,
                progress_callback=lambda stage: self.update_stage(job_id, stage),
            )
            result = GeneratedResumeResponse(
                company=job_posting.company,
                job_title=job_posting.title,
                filename=output_path.name,
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
        except FileNotFoundError:
            self.fail(
                job_id,
                "Upload a compatible master resume before generating.",
            )
            return
        except ValueError as error:
            self.fail(job_id, f"The resume could not be rendered: {error}")
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
