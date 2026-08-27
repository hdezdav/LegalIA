"""Corpus web scraper service."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import httpx
from bs4 import BeautifulSoup

from app.core.logging import get_logger
from app.db.models.enums import DocumentStatus, DocumentType, Jurisdiction
from app.providers.embeddings import get_embedding_provider
from app.services.ingestion_service import IngestionService

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = get_logger(__name__)


class CorpusScraper:
    """Scrapes legal corpus from Colombian government sites."""

    def __init__(self, db: Session):
        self.db = db
        self.embedding_provider = get_embedding_provider()
        self.ingestion_service = IngestionService(
            session=db,
            embedding_provider=self.embedding_provider,
        )

    async def scrape_and_ingest(
        self,
        url: str,
        source_name: str,
        document_type: DocumentType,
        jurisdiction: Jurisdiction,
    ) -> int:
        """Scrape a URL and ingest all found legal documents."""
        
        # Detectar tipo de fuente
        if "constitucioncolombia.com" in url:
            return await self._scrape_constitucion(url, source_name)
        elif "funcionpublica.gov.co" in url:
            return await self._scrape_funcion_publica(url, source_name, document_type, jurisdiction)
        else:
            raise ValueError(f"URL source not supported: {url}")

    async def _scrape_constitucion(self, url: str, source_name: str) -> int:
        """Scrape Constitución from constitucioncolombia.com."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        
        # Extraer artículos (estructura específica de constitucioncolombia.com)
        articles = soup.find_all("div", class_="articulo")
        
        if not articles:
            logger.warning(f"No articles found at {url}")
            return 0

        # Agrupar artículos en documento completo
        full_text = f"# Constitución Política de Colombia 1991\n\n"
        full_text += f"Fuente: {url}\n\n"

        for article in articles[:50]:  # Limitar a primeros 50 artículos para empezar
            article_num = article.find("span", class_="numero")
            article_text = article.find("div", class_="texto")
            
            if article_num and article_text:
                full_text += f"## {article_num.get_text(strip=True)}\n\n"
                full_text += f"{article_text.get_text(strip=True)}\n\n"

        # Convertir a bytes para ingestion
        file_bytes = full_text.encode("utf-8")

        # Ingerir como documento único
        document, chunk_count = await self.ingestion_service.ingest_document(
            file_bytes=file_bytes,
            filename="constitucion_1991.txt",
            content_type="text/plain",
            title="Constitución Política de Colombia 1991",
            external_id="CONST_1991",
            document_type=DocumentType.CONSTITUCION,
            issuing_entity="Asamblea Nacional Constituyente",
            jurisdiction=Jurisdiction.NACIONAL,
            publication_date=None,
            status=DocumentStatus.VIGENTE,
            source_name=source_name,
            source_url=url,
            skip_if_duplicate=True,
        )

        logger.info(f"Ingested Constitution with {chunk_count} chunks")
        return 1

    async def _scrape_funcion_publica(
        self,
        url: str,
        source_name: str,
        document_type: DocumentType,
        jurisdiction: Jurisdiction,
    ) -> int:
        """Scrape from funcionpublica.gov.co."""
        # TODO: Implementar scraper específico para función pública
        raise NotImplementedError("Función Pública scraper not yet implemented")
