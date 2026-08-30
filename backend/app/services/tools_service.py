"""Legal calculation and drafting tools for Legalia."""

from __future__ import annotations

import io
import re
from datetime import date, datetime
from typing import Any
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from pydantic import BaseModel, Field


class DocxExportRequest(BaseModel):
    title: str = Field(..., description="Título del documento legal")
    content: str = Field(..., description="Contenido en markdown del documento")


class LaborSettlementInput(BaseModel):
    fecha_inicio: str = Field(..., description="Fecha de inicio (YYYY-MM-DD)")
    fecha_fin: str = Field(..., description="Fecha de terminación (YYYY-MM-DD)")
    salario_base: float = Field(..., description="Salario mensual base en COP")
    motivo_terminacion: str = Field(
        default="despido_sin_justa_causa",
        description="despido_sin_justa_causa | despido_con_justa_causa | renuncia | mutuo_acuerdo",
    )
    tipo_contrato: str = Field(
        default="indefinido",
        description="indefinido | termino_fijo | obra_labor",
    )
    dias_vacaciones_tomadas: int = Field(default=0, description="Días de vacaciones ya disfrutadas")
    auxilio_transporte: bool = Field(default=True, description="Si devenga hasta 2 SMMLV aplica auxilio de transporte")


class LaborSettlementResult(BaseModel):
    dias_laborados_totales: int
    salario_base_liquidacion: float
    auxilio_transporte_monto: float
    base_prestacional: float
    cesantias: float
    intereses_cesantias: float
    prima_servicios: float
    vacaciones_compensadas: float
    indemnizacion_despido: float
    total_liquidacion: float
    desglose_normativo: dict[str, str]


SMMLV_2026 = 1500000.0  # Valor de referencia
AUX_TRANSPORTE_2026 = 180000.0


def calculate_labor_settlement(data: LaborSettlementInput) -> LaborSettlementResult:
    """Calcula la liquidación de prestaciones sociales e indemnizaciones laborales según el CST."""
    d_inicio = datetime.strptime(data.fecha_inicio, "%Y-%m-%d").date()
    d_fin = datetime.strptime(data.fecha_fin, "%Y-%m-%d").date()

    # Cálculo laboral comercial (30 días por mes)
    dias_totales = max(1, (d_fin.year - d_inicio.year) * 360 + (d_fin.month - d_inicio.month) * 30 + (d_fin.day - d_inicio.day) + 1)

    # Auxilio de transporte (aplica si gana <= 2 SMMLV)
    aux_transporte = AUX_TRANSPORTE_2026 if (data.auxilio_transporte and data.salario_base <= (2 * SMMLV_2026)) else 0.0
    base_prestacional = data.salario_base + aux_transporte

    # Días del año corriente para cesantías y prima (máximo 360 al año o fracción del año de retiro)
    dias_ano_retiro = min(360, ((d_fin.month - 1) * 30 + d_fin.day))

    # Cesantías (Art. 249 CST)
    cesantias = round((base_prestacional * dias_ano_retiro) / 360, 2)

    # Intereses sobre Cesantías (Ley 52 de 1975: 12% anual o proporcional)
    intereses_cesantias = round((cesantias * dias_ano_retiro * 0.12) / 360, 2)

    # Prima de Servicios (Art. 306 CST: semestre en curso)
    dias_semestre = ((d_fin.month - 1) % 6) * 30 + d_fin.day
    prima_servicios = round((base_prestacional * dias_semestre) / 360, 2)

    # Vacaciones (Art. 186 CST: 15 días hábiles por año, sobre salario básico sin auxilio de transporte)
    dias_vac_pendientes = max(0, ((dias_totales * 15) / 360) - data.dias_vacaciones_tomadas)
    vacaciones = round((data.salario_base * dias_vac_pendientes) / 30, 2)

    # Indemnización por despido sin justa causa (Art. 64 CST)
    indemnizacion = 0.0
    if data.motivo_terminacion == "despido_sin_justa_causa":
        if data.tipo_contrato == "indefinido":
            anos_trabajados = dias_totales / 360.0
            if data.salario_base < (10 * SMMLV_2026):
                # Menos de 10 SMMLV: 30 días primer año + 20 días por cada año siguiente
                if anos_trabajados <= 1.0:
                    indemnizacion = data.salario_base
                else:
                    dias_indem = 30 + ((anos_trabajados - 1.0) * 20)
                    indemnizacion = (data.salario_base / 30) * dias_indem
            else:
                # 10 SMMLV o más: 20 días primer año + 15 días por cada año siguiente
                if anos_trabajados <= 1.0:
                    indemnizacion = (data.salario_base / 30) * 20
                else:
                    dias_indem = 20 + ((anos_trabajados - 1.0) * 15)
                    indemnizacion = (data.salario_base / 30) * dias_indem
        elif data.tipo_contrato == "termino_fijo":
            # Salarios correspondientes al tiempo que falte para vencer el plazo
            indemnizacion = data.salario_base * 3  # Estimado 3 meses o fracción

    indemnizacion = round(indemnizacion, 2)
    total = round(cesantias + intereses_cesantias + prima_servicios + vacaciones + indemnizacion, 2)

    return LaborSettlementResult(
        dias_laborados_totales=dias_totales,
        salario_base_liquidacion=data.salario_base,
        auxilio_transporte_monto=aux_transporte,
        base_prestacional=base_prestacional,
        cesantias=cesantias,
        intereses_cesantias=intereses_cesantias,
        prima_servicios=prima_servicios,
        vacaciones_compensadas=vacaciones,
        indemnizacion_despido=indemnizacion,
        total_liquidacion=total,
        desglose_normativo={
            "cesantias": "Art. 249 CST: 1 mes de salario por año laborado o proporcional.",
            "intereses_cesantias": "Ley 52 de 1975: 12% anual sobre el saldo de cesantías.",
            "prima_servicios": "Art. 306 CST: 15 días por semestre o proporcional.",
            "vacaciones": "Art. 186 CST: 15 días hábiles por año de servicio compensados en dinero.",
            "indemnizacion": "Art. 64 CST (modificado por Ley 789 de 2002): Tabla según salario y tiempo de servicio.",
        },
    )


def create_docx_from_markdown(title: str, markdown_content: str) -> bytes:
    """Genera un archivo nativo .docx de Microsoft Word con formato legal profesional."""
    doc = Document()

    # Márgenes legales estándar (2.54 cm / 1 pulgada)
    for section in doc.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)
        section.header_distance = Inches(0.5)
        section.footer_distance = Inches(0.5)

    # Estilo Normal
    style = doc.styles["Normal"]
    font = style.font
    font.name = "Arial"
    font.size = Pt(11)
    font.color.rgb = RGBColor(15, 23, 42)

    # Título principal del documento
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_before = Pt(6)
    p_title.paragraph_format.space_after = Pt(18)
    r_title = p_title.add_run(title.upper())
    r_title.bold = True
    r_title.font.name = "Arial"
    r_title.font.size = Pt(14)
    r_title.font.color.rgb = RGBColor(15, 23, 42)

    lines = markdown_content.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue

        # Evitar repetir el título si viene en la primera línea
        if stripped.lower() == title.lower() or stripped.lower() == f"# {title.lower()}":
            i += 1
            continue

        # Detección de Tablas en Markdown
        if stripped.startswith("|") and stripped.endswith("|") and i + 1 < len(lines) and "|" in lines[i + 1] and "---" in lines[i + 1]:
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|") and lines[i].strip().endswith("|"):
                table_lines.append(lines[i].strip())
                i += 1
            
            # Parsear filas y columnas
            rows_data = []
            for tl in table_lines:
                # Omitir fila separadora
                if re.match(r"^\|(\s*:?-+:?\s*\|)+$", tl):
                    continue
                cells = [c.strip() for c in tl.strip("|").split("|")]
                rows_data.append(cells)

            if rows_data:
                col_count = max(len(r) for r in rows_data)
                table = doc.add_table(rows=len(rows_data), cols=col_count)
                table.style = "Table Grid"
                for row_idx, r_data in enumerate(rows_data):
                    is_header = (row_idx == 0)
                    for col_idx in range(col_count):
                        cell_val = r_data[col_idx] if col_idx < len(r_data) else ""
                        cell = table.cell(row_idx, col_idx)
                        p_cell = cell.paragraphs[0]
                        p_cell.paragraph_format.space_before = Pt(3)
                        p_cell.paragraph_format.space_after = Pt(3)
                        p_cell.paragraph_format.line_spacing = 1.15
                        if is_header:
                            r = p_cell.add_run(cell_val)
                            r.bold = True
                            r.font.name = "Arial"
                            r.font.size = Pt(10)
                            r.font.color.rgb = RGBColor(15, 23, 42)
                        else:
                            _add_formatted_runs(p_cell, cell_val)
                p_spacer = doc.add_paragraph()
                p_spacer.paragraph_format.space_after = Pt(6)
            continue

        # Encabezado Nivel 1
        if stripped.startswith("# "):
            h_text = stripped[2:].strip()
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(14)
            p.paragraph_format.space_after = Pt(6)
            p.paragraph_format.keep_with_next = True
            r = p.add_run(h_text)
            r.bold = True
            r.font.name = "Arial"
            r.font.size = Pt(13)
            r.font.color.rgb = RGBColor(30, 58, 138)
            i += 1

        # Encabezado Nivel 2
        elif stripped.startswith("## "):
            h_text = stripped[3:].strip()
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(12)
            p.paragraph_format.space_after = Pt(4)
            p.paragraph_format.keep_with_next = True
            r = p.add_run(h_text)
            r.bold = True
            r.font.name = "Arial"
            r.font.size = Pt(12)
            r.font.color.rgb = RGBColor(37, 99, 235)
            i += 1

        # Encabezado Nivel 3
        elif stripped.startswith("### "):
            h_text = stripped[4:].strip()
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(10)
            p.paragraph_format.space_after = Pt(3)
            p.paragraph_format.keep_with_next = True
            r = p.add_run(h_text)
            r.bold = True
            r.font.name = "Arial"
            r.font.size = Pt(11)
            r.font.color.rgb = RGBColor(15, 23, 42)
            i += 1

        # Elementos de lista (viñetas)
        elif stripped.startswith("- ") or stripped.startswith("* "):
            b_text = stripped[2:].strip()
            p = doc.add_paragraph(style="List Bullet")
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing = 1.15
            _add_formatted_runs(p, b_text)
            i += 1

        # Elementos de lista numerada
        elif re.match(r"^\d+\.\s+", stripped):
            num_match = re.match(r"^\d+\.\s+", stripped)
            n_text = stripped[num_match.end():].strip() if num_match else stripped
            p = doc.add_paragraph(style="List Number")
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing = 1.15
            _add_formatted_runs(p, n_text)
            i += 1

        # Líneas divisorias
        elif stripped in ("---", "***", "___"):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(8)
            p.paragraph_format.space_after = Pt(8)
            r = p.add_run("―" * 40)
            r.font.color.rgb = RGBColor(148, 163, 184)
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            i += 1

        # Cláusulas judiciales / contractuales
        elif re.match(r"^(CLÁUSULA|CLAUSULA|ARTÍCULO|ARTICULO|PRIMERO|SEGUNDO|TERCERO|CUARTO|QUINTO|SEXTO|SÉPTIMO|SEPTIMO|OCTAVO|NOVENO|DÉCIMO|DECIMO)\b", stripped, re.IGNORECASE):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(6)
            p.paragraph_format.space_after = Pt(4)
            p.paragraph_format.line_spacing = 1.15
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            _add_formatted_runs(p, stripped)
            i += 1

        # Párrafos ordinarios
        else:
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(3)
            p.paragraph_format.space_after = Pt(6)
            p.paragraph_format.line_spacing = 1.15
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            _add_formatted_runs(p, stripped)
            i += 1

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.getvalue()


def _add_formatted_runs(paragraph: Any, text: str) -> None:
    """Parsea markdown básico (**negrita**, *cursiva*) a runs con formato de Word."""
    tokens = re.split(r"(\*\*.*?\*\*)", text)
    for token in tokens:
        if not token:
            continue
        if token.startswith("**") and token.endswith("**"):
            bold_text = token[2:-2]
            r = paragraph.add_run(bold_text)
            r.bold = True
            r.font.name = "Arial"
            r.font.size = Pt(11)
        else:
            sub_tokens = re.split(r"(\*.*?\*)", token)
            for st in sub_tokens:
                if not st:
                    continue
                if st.startswith("*") and st.endswith("*"):
                    r = paragraph.add_run(st[1:-1])
                    r.italic = True
                    r.font.name = "Arial"
                    r.font.size = Pt(11)
                else:
                    r = paragraph.add_run(st)
                    r.font.name = "Arial"
                    r.font.size = Pt(11)
