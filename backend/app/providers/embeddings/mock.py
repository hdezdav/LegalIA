"""Deterministic embedding provider for tests and offline development.

Not a stub that returns zeros. Vectors are derived from the text's token hashes,
so the geometry is meaningful in one specific way: texts sharing vocabulary land
closer together than texts that share none. That is enough for retrieval tests to
assert real ordering — "the article about responsabilidad patrimonial ranks above
the one about vacaciones" — without an API key.

It is NOT a semantic model. It cannot match paraphrases, and it must never be
used to judge retrieval quality; that is what `evaluation/` and a real provider
are for.
"""

from __future__ import annotations

import hashlib
import math
import re

from app.providers.embeddings.base import EmbeddingProvider

_TOKEN = re.compile(r"\w+", re.UNICODE)


class MockEmbeddingProvider(EmbeddingProvider):
    def __init__(self, dimension: int = 1024) -> None:
        if dimension <= 0:
            raise ValueError("dimension must be positive")
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def model_id(self) -> str:
        # Namespaced so mock-embedded chunks can never be mistaken for, or
        # searched alongside, vectors from a real model.
        return f"mock/hashed-{self._dimension}"

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def _embed(self, text: str) -> list[float]:
        """Hash each token into a fixed set of dimensions, then L2-normalize.

        Every occurrence of a token contributes to the same coordinates, so shared
        vocabulary produces a higher dot product. Normalizing makes cosine
        distance behave the way pgvector's `<=>` expects.
        """
        vector = [0.0] * self._dimension
        tokens = _TOKEN.findall(text.lower())

        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            # Four coordinates per token: enough to keep distinct tokens apart at
            # 1024 dimensions, cheap enough to stay fast on long chunks.
            for offset in range(0, 16, 4):
                index = int.from_bytes(digest[offset : offset + 2], "big") % self._dimension
                sign = 1.0 if digest[offset + 2] & 1 else -1.0
                vector[index] += sign

        norm = math.sqrt(sum(component * component for component in vector))
        if norm == 0.0:
            # Empty or punctuation-only text. A zero vector has undefined cosine
            # distance in pgvector, so return a valid unit vector instead.
            vector[0] = 1.0
            return vector

        return [component / norm for component in vector]
