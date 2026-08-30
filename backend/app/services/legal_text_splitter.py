"""Legal text splitter optimized for Colombian legal documents.

Splits by article boundaries and structural headings, preserving hierarchy
(Libro > Título > Capítulo > Artículo > Parágrafo) for precise citations and
accurate hybrid retrieval.
"""

from __future__ import annotations

import re
from typing import Any


class LegalTextSplitter:
    """Splits legal text into semantically coherent chunks with hierarchy metadata.

    Prioritizes:
    1. Article boundaries (Artículo, Art., ARTÍCULO)
    2. Jurisprudential sections (CONSIDERACIONES, RESUELVE, ANTECEDENTES)
    3. Structural headers (LIBRO, TÍTULO, CAPÍTULO, SECCIÓN)
    4. Paragraph boundaries when units exceed chunk_size
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        # Patterns for legal norms
        self.article_pattern = re.compile(
            r"(?:^|\n)((?:ART[IÍ]CULO|Art[íi]culo|Art\.)\s+[0-9]+[A-Za-z\-]*\.?(?:\s+[^\n.]+)?(?:\.|\n))",
            re.IGNORECASE | re.MULTILINE,
        )
        self.structural_header_pattern = re.compile(
            r"(?:^|\n)((?:LIBRO|PARTE|T[IÍ]TULO|CAP[IÍ]TULO|SECCI[ÓO]N)\s+[IVXLCDM0-9]+[^\n]*)",
            re.IGNORECASE | re.MULTILINE,
        )
        self.jurisprudence_pattern = re.compile(
            r"(?:^|\n)((?:I{1,3}|IV|V)\.?\s+(?:ANTECEDENTES|CONSIDERACIONES|DECISI[ÓO]N|RESUELVE|FUNDAMENTOS)[^\n]*)",
            re.IGNORECASE | re.MULTILINE,
        )
        self.paragraph_pattern = re.compile(
            r"(?:^|\n)((?:Par[áa]grafo|PARÁGRAFO|Inciso)\s+[0-9]*\.?)",
            re.IGNORECASE | re.MULTILINE,
        )

    def extract_section(self, text: str) -> str | None:
        """Extract the primary section identifier from text (e.g. 'Artículo 29')."""
        match = self.article_pattern.search(text)
        if match:
            raw = match.group(1).strip().rstrip(".:\n")
            # Truncate long header lines
            return raw[:120]

        match = self.jurisprudence_pattern.search(text)
        if match:
            return match.group(1).strip().rstrip(".:\n")[:120]

        match = self.structural_header_pattern.search(text)
        if match:
            return match.group(1).strip().rstrip(".:\n")[:120]

        return None

    def extract_article_number(self, section: str | None) -> str | None:
        """Extract clean article number from section string (e.g., '29', '15-A')."""
        if not section:
            return None

        match = re.search(r"[Aa]rt[íiÍI]culo\s+([0-9]+[A-Za-z\-]*)", section, re.IGNORECASE)
        if match:
            return match.group(1)

        match = re.search(r"\bArt\.\s*([0-9]+[A-Za-z\-]*)", section, re.IGNORECASE)
        if match:
            return match.group(1)

        return None

    def split_by_articles(self, text: str) -> list[dict[str, Any]]:
        """Split text by article boundaries while tracking structural hierarchy."""
        chunks: list[dict[str, Any]] = []

        # Find all article matches and structural markers
        combined_pattern = re.compile(
            r"(?:^|\n)((?:(?:LIBRO|PARTE|T[IÍ]TULO|CAP[IÍ]TULO|SECCI[ÓO]N)\s+[IVXLCDM0-9]+[^\n]*)|(?:(?:ART[IÍ]CULO|Art[íi]culo|Art\.)\s+[0-9]+[A-Za-z\-]*\.?)|(?:(?:I{1,3}|IV|V)\.?\s+(?:ANTECEDENTES|CONSIDERACIONES|DECISI[ÓO]N|RESUELVE|FUNDAMENTOS)[^\n]*))",
            re.IGNORECASE | re.MULTILINE,
        )

        matches = list(combined_pattern.finditer(text))

        if not matches:
            # Fallback for plain text or unstructured decisions
            sub_chunks = self._split_long_text(text)
            for idx, sc in enumerate(sub_chunks):
                chunks.append(
                    {
                        "content": sc.strip(),
                        "section": f"Sección {idx + 1}" if len(sub_chunks) > 1 else None,
                        "article_number": None,
                        "hierarchy_path": None,
                        "token_count": max(1, len(sc) // 4),
                    }
                )
            return chunks

        # Track hierarchical state
        current_hierarchy: dict[str, str] = {}
        
        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            block_text = text[start:end].strip()

            if not block_text:
                continue

            marker = match.group(1).strip()

            # Check if this marker is a structural header (Libro/Título/Capítulo)
            upper_marker = marker.upper()
            if any(upper_marker.startswith(k) for k in ["LIBRO", "PARTE"]):
                current_hierarchy = {"libro": marker}
                continue
            elif upper_marker.startswith("TÍTULO") or upper_marker.startswith("TITULO"):
                current_hierarchy = {k: v for k, v in current_hierarchy.items() if k in ["libro"]}
                current_hierarchy["titulo"] = marker
                continue
            elif upper_marker.startswith("CAPÍTULO") or upper_marker.startswith("CAPITULO"):
                current_hierarchy = {k: v for k, v in current_hierarchy.items() if k in ["libro", "titulo"]}
                current_hierarchy["capitulo"] = marker
                continue
            elif upper_marker.startswith("SECCIÓN") or upper_marker.startswith("SECCION"):
                current_hierarchy = {k: v for k, v in current_hierarchy.items() if k in ["libro", "titulo", "capitulo"]}
                current_hierarchy["seccion"] = marker
                continue

            # Build hierarchy path string
            hierarchy_parts = [v for k, v in current_hierarchy.items()]
            section = self.extract_section(block_text)
            if section and section not in hierarchy_parts:
                hierarchy_parts.append(section)
            hierarchy_path = " > ".join(hierarchy_parts) if hierarchy_parts else None

            article_number = self.extract_article_number(section)

            # If block is too long, split it further
            if len(block_text) > self.chunk_size * 4:
                sub_chunks = self._split_long_text(block_text)
                for j, sub_chunk in enumerate(sub_chunks):
                    chunks.append(
                        {
                            "content": sub_chunk,
                            "section": f"{section} (parte {j+1})" if section else None,
                            "article_number": article_number,
                            "hierarchy_path": hierarchy_path,
                            "token_count": max(1, len(sub_chunk) // 4),
                        }
                    )
            else:
                chunks.append(
                    {
                        "content": block_text,
                        "section": section,
                        "article_number": article_number,
                        "hierarchy_path": hierarchy_path,
                        "token_count": max(1, len(block_text) // 4),
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
        - hierarchy_path: full breadcrumb path (e.g. "Título I > Capítulo II > Artículo 15")
        - token_count: estimated token count
        """
        if not text or not text.strip():
            return []

        chunks = self.split_by_articles(text)
        return [c for c in chunks if c["content"].strip()]
