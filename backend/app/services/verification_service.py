"""Verification: check that generated answers are backed by retrieved chunks.

The VerificationService takes an answer and the chunks it was generated from,
and classifies whether each claim in the answer has support in those chunks.

Strategy: use a small, fast model (Haiku 4.5) to independently verify that the
answer doesn't invent facts beyond what the context says. This is Legalia's
core promise: "every claim has a source" must be machine-checkable.
"""

from __future__ import annotations

from app.core.logging import get_logger
from app.db.models.enums import VerificationStatus
from app.providers.llm.base import LLMProvider
from app.schemas.retrieval import RetrievalCandidate

logger = get_logger(__name__)


class VerificationService:
    """Verify generated answers against their source chunks."""

    def __init__(self, verifier_llm: LLMProvider):
        """Initialize with a small, fast LLM (typically Haiku 4.5)."""
        self.verifier = verifier_llm

    async def verify(
        self,
        *,
        answer: str,
        context_candidates: list[RetrievalCandidate],
    ) -> VerificationStatus:
        """Verify that answer is backed by the given context chunks.

        Returns:
            SUPPORTED: every claim has clear support in context
            PARTIALLY_SUPPORTED: most claims supported, some not
            UNSUPPORTED: answer invents facts beyond context
            INSUFFICIENT_EVIDENCE: no context provided (shouldn't happen)
            NOT_VERIFIED: verification errored or was skipped
        """
        if not context_candidates:
            logger.warning("Verification called with no context candidates")
            return VerificationStatus.INSUFFICIENT_EVIDENCE

        if not answer.strip():
            logger.warning("Verification called with empty answer")
            return VerificationStatus.NOT_VERIFIED

        # Build verification prompt
        prompt = self._build_verification_prompt(answer, context_candidates)

        try:
            # Call verifier LLM
            from app.providers.llm.base import LLMMessage, Role

            messages = [LLMMessage(role=Role.USER, content=prompt)]
            completion = await self.verifier.complete(
                system="You are a legal fact-checker. Be precise and concise.",
                messages=messages,
                temperature=0.0,  # Deterministic for verification
                max_tokens=100,  # We only need one word: SUPPORTED/PARTIALLY_SUPPORTED/UNSUPPORTED
            )

            # Parse response to determine status
            status = self._parse_verification_response(completion.text)

            logger.info(
                "Answer verification completed",
                extra={
                    "status": status.value,
                    "answer_length": len(answer),
                    "context_count": len(context_candidates),
                },
            )

            return status

        except Exception as e:
            logger.error(
                "Verification failed with error",
                extra={"error": str(e), "answer_length": len(answer)},
                exc_info=True,
            )
            return VerificationStatus.NOT_VERIFIED

    @staticmethod
    def _build_verification_prompt(
        answer: str, context: list[RetrievalCandidate]
    ) -> str:
        """Build the verification prompt for the verifier LLM."""
        # Format context chunks
        context_blocks = []
        for i, candidate in enumerate(context, 1):
            block = f"[{i}] {candidate.document_title}"
            if candidate.section:
                block += f" — {candidate.section}"
            block += f"\n{candidate.content}"
            context_blocks.append(block)

        context_text = "\n\n".join(context_blocks)

        # Verification prompt
        prompt = f"""You are a legal fact-checker. Your job is to verify if an AI-generated answer is fully backed by the provided legal sources.

CONTEXT (legal sources that were given to the AI):
{context_text}

ANSWER TO VERIFY:
{answer}

TASK:
Classify the answer's support level:

- SUPPORTED: Every factual claim in the answer has clear support in the context. The answer may summarize or paraphrase, but does not add facts beyond what the sources say.

- PARTIALLY_SUPPORTED: Most claims are supported, but some assertions go beyond what the context explicitly states.

- UNSUPPORTED: The answer invents facts, cites articles not in the context, or makes claims contradicting the sources.

Respond with ONLY ONE WORD: SUPPORTED, PARTIALLY_SUPPORTED, or UNSUPPORTED.
"""
        return prompt

    @staticmethod
    def _parse_verification_response(response: str) -> VerificationStatus:
        """Parse the verifier LLM's response into a VerificationStatus.

        The verifier is instructed to respond with a single word, but we're
        defensive: extract the status from anywhere in the response.
        """
        response_upper = response.strip().upper()

        if "SUPPORTED" in response_upper and "PARTIALLY" not in response_upper:
            return VerificationStatus.SUPPORTED

        if "PARTIALLY_SUPPORTED" in response_upper or "PARTIALLY SUPPORTED" in response_upper:
            return VerificationStatus.PARTIALLY_SUPPORTED

        if "UNSUPPORTED" in response_upper:
            return VerificationStatus.UNSUPPORTED

        # Default: if we can't parse, mark as not verified
        logger.warning(
            "Could not parse verification response",
            extra={"response": response[:200]},
        )
        return VerificationStatus.NOT_VERIFIED
