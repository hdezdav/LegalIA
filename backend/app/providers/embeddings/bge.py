"""BGE-M3 provider: local, CPU-only embedding.

Prepared as the alternative to a remote provider, per sections 13 and 14 of the
brief. Two things about it are deliberate:

**The import is lazy.** `sentence-transformers` pulls in torch, ~2.5 GB of wheels.
It is NOT in `requirements.txt` (see `requirements-local-embeddings.txt`), so the
API image stays small and a deployment that never selects BGE never pays for it.
Selecting `EMBEDDING_PROVIDER=bge` without that extra installed fails at startup
with an actionable message rather than at the first user question.

**The model loads on first use, not at construction.** An 8 GB VPS running the API,
PostgreSQL, LibreChat and MongoDB has no headroom to hold BGE-M3 resident
(~2.3 GB in fp32) just in case. The intended shape on that box is batch ingestion:
run the embed pass, let the process exit, reclaim the memory. Serving live queries
from BGE on the MVP VPS is not recommended and is called out in docs/RAG.md.

BGE-M3 is natively 1024-dimensional. Truncating to a smaller width is supported by
the model (Matryoshka-style) but changes the vectors, so it is treated as a
different provider configuration requiring a re-embed.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from app.core.logging import get_logger
from app.providers.embeddings.base import EmbeddingError, EmbeddingProvider

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

logger = get_logger(__name__)

NATIVE_DIMENSION = 1024

_INSTALL_HINT = (
    "BGE-M3 requires the local-embeddings extra. Install it with:\n"
    "    pip install -r backend/requirements-local-embeddings.txt\n"
    "or select a remote provider with EMBEDDING_PROVIDER=alibaba."
)


class BGEEmbeddingProvider(EmbeddingProvider):
    def __init__(
        self,
        model_path: str = "BAAI/bge-m3",
        dimension: int = NATIVE_DIMENSION,
        batch_size: int = 32,
        device: str = "cpu",
        normalize: bool = True,
    ) -> None:
        if dimension > NATIVE_DIMENSION:
            raise ValueError(
                f"BGE-M3 produces {NATIVE_DIMENSION} dimensions; "
                f"{dimension} was requested"
            )

        self.model_path = model_path
        self._dimension = dimension
        self.batch_size = batch_size
        self.device = device
        self.normalize = normalize
        self._model: SentenceTransformer | None = None

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def model_id(self) -> str:
        # The model path is normalized: a local directory and a hub id for the
        # same weights must produce the same identity, or a re-download would
        # orphan every existing vector.
        name = self.model_path.rstrip("/").split("/")[-1]
        return f"bge/{name}-{self._dimension}"

    @staticmethod
    def is_available() -> bool:
        """True when the local-embeddings extra is installed.

        Called by the factory at startup so a misconfiguration surfaces there.
        """
        import importlib.util

        return importlib.util.find_spec("sentence_transformers") is not None

    def _load(self) -> SentenceTransformer:
        """Load the model, once, on first use."""
        if self._model is not None:
            return self._model

        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise EmbeddingError(_INSTALL_HINT) from exc

        logger.info(
            "loading local embedding model",
            extra={"model_path": self.model_path, "device": self.device},
        )
        try:
            self._model = SentenceTransformer(self.model_path, device=self.device)
        except Exception as exc:
            raise EmbeddingError(
                f"Could not load BGE model from {self.model_path!r}: "
                f"{type(exc).__name__}"
            ) from exc

        return self._model

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if any(not text.strip() for text in texts):
            raise EmbeddingError("Cannot embed empty text")

        # Inference is CPU-bound and releases the GIL inside torch, but the call
        # itself blocks. Off-thread so it cannot stall the event loop and every
        # other in-flight request with it.
        return await asyncio.to_thread(self._encode, texts)

    def _encode(self, texts: list[str]) -> list[list[float]]:
        model = self._load()

        try:
            raw: Any = model.encode(
                texts,
                batch_size=self.batch_size,
                normalize_embeddings=self.normalize,
                show_progress_bar=False,
                convert_to_numpy=True,
            )
        except Exception as exc:
            raise EmbeddingError(f"Local embedding failed: {type(exc).__name__}") from exc

        vectors = [[float(component) for component in row] for row in raw]

        for vector in vectors:
            if len(vector) < self._dimension:
                raise EmbeddingError(
                    f"Model produced {len(vector)} dimensions, "
                    f"{self._dimension} configured"
                )

        if self._dimension == NATIVE_DIMENSION:
            return vectors

        # Truncation changes the vectors, so a database embedded at full width
        # cannot be mixed with a truncated one. Renormalized to keep cosine
        # distance meaningful.
        return [_truncate(vector, self._dimension, self.normalize) for vector in vectors]

    def unload(self) -> None:
        """Release the model.

        Called by the ingestion CLI after a batch pass, so a long-running process
        does not hold ~2.3 GB resident on an 8 GB box.
        """
        self._model = None


def _truncate(vector: list[float], dimension: int, normalize: bool) -> list[float]:
    import math

    truncated = vector[:dimension]
    if not normalize:
        return truncated

    norm = math.sqrt(sum(component * component for component in truncated))
    if norm == 0.0:
        return truncated
    return [component / norm for component in truncated]
