"""Legal tools and calculations router."""

from __future__ import annotations

import io
import re
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.services.tools_service import (
    DocxExportRequest,
    LaborSettlementInput,
    LaborSettlementResult,
    calculate_labor_settlement,
    create_docx_from_markdown,
)

router = APIRouter(prefix="/tools", tags=["tools"])


@router.post("/calculate-labor-settlement", response_model=LaborSettlementResult)
async def api_calculate_labor_settlement(payload: LaborSettlementInput):
    """Calcula la liquidación laboral oficial de prestaciones e indemnizaciones (CST)."""
    return calculate_labor_settlement(payload)


@router.post("/export-docx")
async def api_export_docx(payload: DocxExportRequest):
    """Genera y descarga un archivo .docx nativo y válido de Microsoft Word."""
    docx_bytes = create_docx_from_markdown(payload.title, payload.content)
    slug = re.sub(r"[^a-zA-Z0-9_\-]+", "_", payload.title).strip("_") or "documento_legalia"
    filename = f"{slug}.docx"

    return StreamingResponse(
        io.BytesIO(docx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )
