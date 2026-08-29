"""Decoupled background generation manager.

Provides asynchronous, persistent AI generation tasks that continue executing
and saving to PostgreSQL even if the client disconnects or closes the browser tab.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import time
from typing import AsyncIterator, Literal
import uuid

from app.core.logging import get_logger
from app.db.models.conversation import Conversation
from app.db.models.enums import MessageRole
from app.db.models.message import Message
from app.db.models.user import User
from app.db.session import SessionLocal
from app.providers.llm.base import LLMMessage, Role
from app.services.chat_service import ChatService

logger = get_logger(__name__)


@dataclass
class ActiveGenerationJob:
    job_id: str
    conversation_id: str
    user_id: str
    model: str
    question: str
    status: Literal["generating", "completed", "failed"] = "generating"
    accumulated_text: str = ""
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    subscribers: set[asyncio.Queue[str | None]] = field(default_factory=set)
    task: asyncio.Task | None = None


class GenerationManager:
    """Manages decoupled, server-side AI generation jobs."""

    def __init__(self) -> None:
        self._jobs: dict[str, ActiveGenerationJob] = {}
        self._convo_to_job: dict[str, str] = {}
        self._lock = asyncio.Lock()

    def get_job(self, job_id: str) -> ActiveGenerationJob | None:
        return self._jobs.get(job_id)

    def get_active_job_for_conversation(self, conversation_id: str) -> ActiveGenerationJob | None:
        job_id = self._convo_to_job.get(conversation_id)
        if not job_id:
            return None
        job = self._jobs.get(job_id)
        if job and job.status == "generating":
            return job
        return None

    async def start_job(
        self,
        *,
        service_factory,
        user_id: uuid.UUID,
        question: str,
        history: list[LLMMessage] | None = None,
        model: str | None = None,
        external_conversation_id: str | None = None,
    ) -> ActiveGenerationJob:
        """Create and launch a background generation task."""
        job_id = f"gen-{uuid.uuid4().hex[:12]}"
        convo_id = external_conversation_id or f"convo-{uuid.uuid4().hex[:12]}"

        job = ActiveGenerationJob(
            job_id=job_id,
            conversation_id=convo_id,
            user_id=str(user_id),
            model=model or "legalia",
            question=question,
        )

        async with self._lock:
            self._jobs[job_id] = job
            self._convo_to_job[convo_id] = job_id

        # Launch decoupled background task
        task = asyncio.create_task(
            self._run_generation(
                job=job,
                service_factory=service_factory,
                user_id=user_id,
                question=question,
                history=history or [],
                model=model,
                external_conversation_id=convo_id,
            )
        )
        job.task = task
        return job

    async def _run_generation(
        self,
        *,
        job: ActiveGenerationJob,
        service_factory,
        user_id: uuid.UUID,
        question: str,
        history: list[LLMMessage],
        model: str | None,
        external_conversation_id: str,
    ) -> None:
        """Background execution worker: streams tokens and persists to DB."""
        logger.info(
            "Starting decoupled background generation",
            extra={"job_id": job.job_id, "conversation_id": external_conversation_id},
        )

        # Dedicated database session for background persistence
        db = SessionLocal()
        service: ChatService = service_factory()

        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError(f"User {user_id} not found for background generation")

            async for token in service.answer_stream(
                db,
                user=user,
                question=question,
                history=history,
                external_conversation_id=external_conversation_id,
                model=model if model and model != "legalia" else None,
            ):
                job.accumulated_text += token

                # Broadcast token to all active listeners/subscribers
                for q in list(job.subscribers):
                    try:
                        q.put_nowait(token)
                    except Exception:
                        pass

            # Commit the session to ensure all turns and citations are persisted
            db.commit()
            job.status = "completed"
            logger.info(
                "Background generation completed successfully and persisted to DB",
                extra={"job_id": job.job_id, "conversation_id": external_conversation_id},
            )

        except asyncio.CancelledError:
            logger.warning(
                "Background generation task received cancellation signal",
                extra={"job_id": job.job_id},
            )
            job.status = "failed"
            job.error = "Generation cancelled"
        except Exception as exc:
            logger.error(
                "Background generation failed with error",
                extra={"job_id": job.job_id, "error": str(exc)},
            )
            job.status = "failed"
            job.error = str(exc)
            try:
                db.rollback()
            except Exception:
                pass
        finally:
            # Notify all subscribers of EOF
            for q in list(job.subscribers):
                try:
                    q.put_nowait(None)
                except Exception:
                    pass

            db.close()

            # Schedule job cleanup from memory after 10 minutes
            asyncio.create_task(self._cleanup_job(job.job_id, delay_seconds=600))

    async def _cleanup_job(self, job_id: str, delay_seconds: int = 600) -> None:
        await asyncio.sleep(delay_seconds)
        async with self._lock:
            job = self._jobs.pop(job_id, None)
            if job and self._convo_to_job.get(job.conversation_id) == job_id:
                self._convo_to_job.pop(job.conversation_id, None)

    async def subscribe(self, job: ActiveGenerationJob) -> AsyncIterator[str]:
        """Subscribe to token stream. Cleanly detaches if client disconnects."""
        queue: asyncio.Queue[str | None] = asyncio.Queue()
        job.subscribers.add(queue)

        try:
            while True:
                token = await queue.get()
                if token is None:
                    break
                yield token
        finally:
            job.subscribers.discard(queue)


# Process-wide singleton
generation_manager = GenerationManager()
