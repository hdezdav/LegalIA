"""Legal text splitter optimized for Colombian legal documents.

Splits by article boundaries when possible, preserving structural hierarchy
(Título > Capítulo > Artículo > Parágrafo) for precise citations.
"""

from __future__ import annotations

import re
from typing import Any


class LegalTextSplitter:
    """Splits legal text into semantically coherent chunks.

    Prioritizes:
    1. Article boundaries (Artículo, Art., ARTÍCULO)
    2. Section headers (TÍTULO, CAPÍTULO, Sección)
    3. Character limit when articles are too long
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        # Patterns for legal structure
        self.article_pattern = re.compile(
            r"(?:^|\n)((?:ART[IÍ]CULO|Art[íi]culo|Art\.)\s+[0-9]+[A-Za-z]?\.?)",
            re.IGNORECASE | re.MULTILINE,
        )
        self.section_pattern = re.compile(
            r"(?:^|\n)((?:T[IÍ]TULO|CAP[IÍ]TULO|Secci[óo]n)\s+[IVXLCDM0-9]+\.?)",
            re.IGNORECASE | re.MULTILINE,
        )
        self.paragraph_pattern = re.compile(
            r"(?:^|\n)((?:Par[áa]grafo|PARÁGRAFO|Inciso)\s+[0-9]+\.?)",
            re.IGNORECASE | re.MULTILINE,
        )

    def extract_section(self, text: str) -> str | None:
        """Extract the section identifier from text (e.g. 'Artículo 90')."""
        match = self.article_pattern.search(text)
        if match:
            return match.group(1).strip()

        match = self.section_pattern.search(text)
        if match:
            return match.group(1).strip()

        return None

    def extract_article_number(self, section: str | None) -> str | None:
        """Extract article number from section string."""
        if not section:
            return None

        match = re.search(r"[Aa]rt[íiÍI]culo\s+([0-9]+[A-Za-z]?)", section, re.IGNORECASE)
        if match:
            return match.group(1)

        return None

    def split_by_articles(self, text: str) -> list[dict[str, Any]]:
        """Split text by article boundaries."""
        chunks: list[dict[str, Any]] = []

        # Find all article positions
        article_matches = list(self.article_pattern.finditer(text))

        if not article_matches:
            # No articles found, return whole text as one chunk
            return [
                {
                    "content": text.strip(),
                    "section": None,
                    "article_number": None,
                    "token_count": len(text) // 4,
                }
            ]

        # Process each article
        for i, match in enumerate(article_matches):
            start = match.start()
            end = article_matches[i + 1].start() if i + 1 < len(article_matches) else len(text)

            article_text = text[start:end].strip()

            if not article_text:
                continue

            section = self.extract_section(article_text)
            article_number = self.extract_article_number(section)

            # If article is too long, split it further
            if len(article_text) > self.chunk_size * 4:  # 4 chars per token estimate
                sub_chunks = self._split_long_text(article_text)
                for j, sub_chunk in enumerate(sub_chunks):
                    chunks.append(
                        {
                            "content": sub_chunk,
                            "section": f"{section} (parte {j+1})" if section else None,
                            "article_number": article_number,
                            "token_count": len(sub_chunk) // 4,
                        }
                    )
            else:
                chunks.append(
                    {
                        "content": article_text,
                        "section": section,
                        "article_number": article_number,
                        "token_count": len(article_text) // 4,
                    }
                )

        return chunks

    def _split_long_text(self, text: str) -> list[str]:
        """Split long text by paragraphs, respecting chunk_size."""
        chunks: list[str] = []
        current_chunk = ""

        # Split by double newlines (paragraphs)
        paragraphs = text.split("\n\n")

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # If adding this paragraph exceeds chunk_size, start new chunk
            if len(current_chunk) + len(para) > self.chunk_size * 4:
                if current_chunk:
                    chunks.append(current_chunk)

                # If single paragraph is too long, split by sentences
                if len(para) > self.chunk_size * 4:
                    sentences = re.split(r"(?<=[.!?])\s+", para)
                    for sentence in sentences:
                        if len(current_chunk) + len(sentence) > self.chunk_size * 4:
                            if current_chunk:
                                chunks.append(current_chunk)
                            current_chunk = sentence
                        else:
                            current_chunk += " " + sentence if current_chunk else sentence
                else:
                    current_chunk = para
            else:
                current_chunk += "\n\n" + para if current_chunk else para

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def split_text(self, text: str) -> list[dict[str, Any]]:
        """Split text into chunks optimized for legal documents.

        Returns list of chunks with metadata:
        - content: chunk text
        - section: section identifier (e.g. "Artículo 90")
        - article_number: extracted article number (e.g. "90")
        - token_count: estimated token count
        """
        if not text or not text.strip():
            return []

        # Try splitting by articles first
        chunks = self.split_by_articles(text)

        # Filter empty chunks
        chunks = [c for c in chunks if c["content"].strip()]

        return chunks
