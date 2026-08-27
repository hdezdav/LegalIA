"""Citation extraction: link answer text to the chunks that back it.

The CitationService creates Citation rows for every chunk used in the context,
ensuring every answer has traceable sources. This is what makes "every claim
has a source" machine-readable rather than prose.

Strategy: persist all context chunks as citations, since the answer was generated
from them. This is more reliable than pattern-matching references in generated
text, which depends on the LLM following a specific citation format.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.models.citation import Citation
from app.db.models.enums import CitationVerificationStatus
from app.schemas.retrieval import RetrievalCandidate

logger = get_logger(__name__)


class CitationService:
    """Extract and persist citations from generated answers."""

    def __init__(self, session: Session):
        self.session = session

    def extract_and_persist(
        self,
        *,
        message_id: str,
        answer: str,
        context_candidates: list[RetrievalCandidate],
    ) -> list[Citation]:
        """Persist all context chunks as citations.

        Strategy: every chunk handed to the LLM becomes a citation, since the
        answer was generated from them. This ensures traceable sources without
        depending on the LLM writing explicit "[1]" style references.

        Returns the created Citation rows. Empty list if no context provided.
        """
        if not context_candidates:
            logger.debug(
                "No context candidates to persist as citations",
                extra={"message_id": message_id},
            )
            return []

        try:
            # Create one citation per context chunk, ordered by relevance (rank)
            citations = []
            for position, candidate in enumerate(context_candidates, start=1):
                # Extract a readable excerpt from chunk (first 300 chars)
                excerpt = self._extract_excerpt_from_chunk(candidate.content)

                citation = Citation(
                    message_id=message_id,
                    document_id=candidate.document_id,
                    chunk_id=candidate.chunk_id,
                    position=position,
                    document_title=candidate.document_title,
                    section=candidate.section or "",  # Handle None
                    source_name=candidate.source_name,
                    source_url=candidate.source_url or "",  # Handle None
                    publication_date=candidate.publication_date,  # Already nullable in DB
                    status=candidate.status,
                    excerpt=excerpt,
                    excerpt_char_start=0,
                    excerpt_char_end=min(len(excerpt), len(candidate.content)),
                    relevance_score=candidate.score,
                    rank=candidate.rank,
                    retrieval_source=candidate.retrieval_source,
                    verification_status=CitationVerificationStatus.UNVERIFIED,
                )
                citations.append(citation)

            # Bulk insert for performance (avoids N+1)
            self.session.bulk_save_objects(citations, return_defaults=True)
            self.session.flush()

            logger.info(
                "Citations persisted from context",
                extra={
                    "message_id": message_id,
                    "citation_count": len(citations),
                },
            )

            return citations

        except Exception as e:
            logger.error(
                "Failed to persist citations",
                extra={
                    "message_id": message_id,
                    "error": str(e),
                    "candidate_count": len(context_candidates),
                },
                exc_info=True,
            )
            # Don't fail the entire chat if citations fail
            return []

    @staticmethod
    def _extract_excerpt_from_chunk(chunk_content: str) -> str:
        """Extract a readable excerpt from chunk content.

        Returns up to 300 chars, trimmed to sentence boundaries when possible.
        """
        max_excerpt_len = 300

        if len(chunk_content) <= max_excerpt_len:
            return chunk_content.strip()

        excerpt = chunk_content[:max_excerpt_len].strip()

        # Trim to last complete sentence if possible
        if ". " in excerpt:
            last_period = excerpt.rfind(". ")
            if last_period > max_excerpt_len // 2:  # Only if we keep >50%
                excerpt = excerpt[: last_period + 1]
        else:
            # No sentence boundary, add ellipsis
            excerpt = excerpt.rstrip() + "..."

        return excerpt
