#!/usr/bin/env python3
"""Official Colombian Legal Corpus Scraper.

Extracts official legislation directly from the Colombian State portals:
- Gestor Normativo de la Función Pública (funcionpublica.gov.co)
- Presidencia & Congreso de la República official publications

Outputs clean, structure-preserving legal texts ready for LegalIA's
LegalTextSplitter and embedding/indexing pipeline.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

try:
    import httpx
    from bs4 import BeautifulSoup
except ImportError:
    httpx = None  # type: ignore
    BeautifulSoup = None  # type: ignore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("colombia_corpus_scraper")

BASE_URL = "https://www.funcionpublica.gov.co/eva/gestornormativo"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36 LegalIA-CorpusIngest/1.0"
)


@dataclass(slots=True)
class NormCatalogEntry:
    id: int
    slug: str
    nombre: str
    categoria: str
    emisor: str
    tipo_norma: str
    numero_oficial: str
    status: str = "VIGENTE"
    descripcion: str = ""


# Catálogo curado de normas fundamentales de la República de Colombia
CATALOGO_NORMAS: list[NormCatalogEntry] = [
    NormCatalogEntry(
        id=4125,
        slug="constitucion_politica_1991",
        nombre="Constitución Política de Colombia de 1991",
        categoria="constitucional",
        emisor="Asamblea Nacional Constituyente",
        tipo_norma="CONSTITUCION",
        numero_oficial="Constitución Política de 1991",
        status="VIGENTE",
        descripcion="Norma de normas del ordenamiento jurídico colombiano con reformas acumuladas.",
    ),
    NormCatalogEntry(
        id=6388,
        slug="codigo_penal_ley_599_2000",
        nombre="Código Penal (Ley 599 de 2000)",
        categoria="penal",
        emisor="Congreso de la República",
        tipo_norma="LEY",
        numero_oficial="Ley 599 de 2000",
        status="VIGENTE",
        descripcion="Código Penal sustantivo colombiano y tipificación de conductas punibles.",
    ),
    NormCatalogEntry(
        id=14787,
        slug="codigo_procedimiento_penal_ley_906_2004",
        nombre="Código de Procedimiento Penal (Ley 906 de 2004)",
        categoria="penal",
        emisor="Congreso de la República",
        tipo_norma="LEY",
        numero_oficial="Ley 906 de 2004",
        status="VIGENTE",
        descripcion="Sistema Penal Acusatorio y garantías procesales penales.",
    ),
    NormCatalogEntry(
        id=48425,
        slug="codigo_general_proceso_ley_1564_2012",
        nombre="Código General del Proceso (Ley 1564 de 2012)",
        categoria="procesal",
        emisor="Congreso de la República",
        tipo_norma="LEY",
        numero_oficial="Ley 1564 de 2012",
        status="VIGENTE",
        descripcion="Régimen procesal civil, comercial, agrario y de familia en Colombia.",
    ),
    NormCatalogEntry(
        id=41249,
        slug="codigo_cpaca_ley_1437_2011",
        nombre="Código de Procedimiento Administrativo y de lo Contencioso Administrativo - CPACA (Ley 1437 de 2011)",
        categoria="administrativo",
        emisor="Congreso de la República",
        tipo_norma="LEY",
        numero_oficial="Ley 1437 de 2011",
        status="VIGENTE",
        descripcion="Procedimiento administrativo ante entidades públicas y jurisdicción contencioso administrativa.",
    ),
    NormCatalogEntry(
        id=199983,
        slug="codigo_sustantivo_trabajo_decreto_2663_1950",
        nombre="Código Sustantivo del Trabajo (Decreto Ley 2663 de 1950)",
        categoria="laboral",
        emisor="Presidencia de la República",
        tipo_norma="DECRETO_LEY",
        numero_oficial="Decreto Ley 2663 de 1950",
        status="VIGENTE",
        descripcion="Regulación integral de las relaciones laborales individuales y colectivas.",
    ),
    NormCatalogEntry(
        id=41102,
        slug="codigo_comercio_decreto_410_1971",
        nombre="Código de Comercio (Decreto 410 de 1971)",
        categoria="comercial",
        emisor="Presidencia de la República",
        tipo_norma="DECRETO_LEY",
        numero_oficial="Decreto 410 de 1971",
        status="VIGENTE",
        descripcion="Normativa mercantil, actos de comercio, sociedades comerciales y contratos mercantiles.",
    ),
    NormCatalogEntry(
        id=62704,
        slug="codigo_civil_ley_57_1887",
        nombre="Código Civil Colombiano (Ley 57 de 1887)",
        categoria="civil",
        emisor="Congreso de la República",
        tipo_norma="LEY",
        numero_oficial="Ley 57 de 1887",
        status="VIGENTE",
        descripcion="Derecho civil: personas, bienes, sucesiones, obligaciones y contratos.",
    ),
    NormCatalogEntry(
        id=93970,
        slug="codigo_disciplinario_ley_1952_2019",
        nombre="Código General Disciplinario (Ley 1952 de 2019)",
        categoria="disciplinario",
        emisor="Congreso de la República",
        tipo_norma="LEY",
        numero_oficial="Ley 1952 de 2019",
        status="VIGENTE",
        descripcion="Régimen disciplinario de los servidores públicos en Colombia.",
    ),
    NormCatalogEntry(
        id=5248,
        slug="ley_seguridad_social_ley_100_1993",
        nombre="Sistema de Seguridad Social Integral (Ley 100 de 1993)",
        categoria="laboral",
        emisor="Congreso de la República",
        tipo_norma="LEY",
        numero_oficial="Ley 100 de 1993",
        status="VIGENTE",
        descripcion="Sistema general de pensiones, salud y riesgos laborales.",
    ),
    NormCatalogEntry(
        id=49981,
        slug="ley_habeas_data_ley_1581_2012",
        nombre="Ley Estatutaria de Protección de Datos Personales (Ley 1581 de 2012)",
        categoria="constitucional",
        emisor="Congreso de la República",
        tipo_norma="LEY_ESTATUTARIA",
        numero_oficial="Ley 1581 de 2012",
        status="VIGENTE",
        descripcion="Régimen general de protección de datos personales y Habeas Data.",
    ),
    NormCatalogEntry(
        id=56882,
        slug="ley_transparencia_ley_1712_2014",
        nombre="Ley de Transparencia y Acceso a la Información (Ley 1712 de 2014)",
        categoria="administrativo",
        emisor="Congreso de la República",
        tipo_norma="LEY_ESTATUTARIA",
        numero_oficial="Ley 1712 de 2014",
        status="VIGENTE",
        descripcion="Derecho fundamental de acceso a la información pública nacional.",
    ),
    NormCatalogEntry(
        id=43292,
        slug="estatuto_anticorrupcion_ley_1474_2011",
        nombre="Estatuto Anticorrupción (Ley 1474 de 2011)",
        categoria="administrativo",
        emisor="Congreso de la República",
        tipo_norma="LEY",
        numero_oficial="Ley 1474 de 2011",
        status="VIGENTE",
        descripcion="Prevención, investigación y sanción de actos de corrupción pública.",
    ),
    NormCatalogEntry(
        id=22106,
        slug="codigo_infancia_ley_1098_2006",
        nombre="Código de la Infancia y la Adolescencia (Ley 1098 de 2006)",
        categoria="civil",
        emisor="Congreso de la República",
        tipo_norma="LEY",
        numero_oficial="Ley 1098 de 2006",
        status="VIGENTE",
        descripcion="Protección integral de los derechos de niños, niñas y adolescentes.",
    ),
    NormCatalogEntry(
        id=40200,
        slug="codigo_penal_militar_ley_1407_2010",
        nombre="Código Penal Militar (Ley 1407 de 2010)",
        categoria="penal",
        emisor="Congreso de la República",
        tipo_norma="LEY",
        numero_oficial="Ley 1407 de 2010",
        status="VIGENTE",
        descripcion="Código penal militar y procedimiento penal de la fuerza pública.",
    ),
]


@dataclass
class ScrapedDocument:
    id: int
    slug: str
    nombre: str
    categoria: str
    tipo_norma: str
    numero_oficial: str
    emisor: str
    status: str
    fuente_url: str
    fecha_expedicion: str | None = None
    fecha_vigencia: str | None = None
    medio_publicacion: str | None = None
    temas: list[str] = field(default_factory=list)
    texto_completo: str = ""
    caracteres_total: int = 0


async def fetch_norma(
    client: httpx.AsyncClient,
    catalog_entry: NormCatalogEntry | None = None,
    norma_id: int | None = None,
) -> ScrapedDocument | None:
    """Extrae el contenido y metadatos de una norma del Gestor Normativo."""
    target_id = catalog_entry.id if catalog_entry else norma_id
    if target_id is None:
        raise ValueError("Must provide either catalog_entry or norma_id")

    url = f"{BASE_URL}/norma.php?i={target_id}"
    logger.info(f"⏳ Extrayendo [ID {target_id}] desde {url}...")

    try:
        response = await client.get(url, timeout=45.0)
        if response.status_code != 200:
            logger.error(f"❌ Error HTTP {response.status_code} al consultar {url}")
            return None

        if "norma_error.php" in str(response.url):
            logger.error(f"❌ Norma ID {target_id} no disponible en el portal oficial")
            return None

        soup = BeautifulSoup(response.text, "html.parser")

        # 1. Extracción de Título
        title_el = soup.find("h2", class_="titulo-norma")
        title = title_el.get_text(strip=True) if title_el else None
        if not title:
            page_title = soup.find("title")
            title = page_title.get_text(strip=True) if page_title else f"Norma {target_id}"

        # 2. Extracción de Metadatos en panel lateral
        col_meta = soup.find("main").find("div", class_="col-lg-3") if soup.find("main") else None
        fecha_expedicion = None
        fecha_vigencia = None
        medio_publicacion = None
        temas: list[str] = []

        if col_meta:
            meta_text = col_meta.get_text(separator="\n", strip=True)
            for line in meta_text.split("\n"):
                line_str = line.strip()
                if "Fecha de Expedición:" in line_str:
                    fecha_expedicion = line_str.replace("Fecha de Expedición:", "").strip()
                elif "Fecha de Entrada en Vigencia:" in line_str:
                    fecha_vigencia = line_str.replace("Fecha de Entrada en Vigencia:", "").strip()
                elif "Medio de Publicación:" in line_str:
                    medio_publicacion = line_str.replace("Medio de Publicación:", "").strip()

            # Temas
            temas_items = col_meta.find_all("li")
            for item in temas_items:
                t = item.get_text(strip=True)
                if t and len(t) > 3 and not any(k in t.lower() for k in ["concepto", "vigencia", "fecha"]):
                    temas.append(t)

        # 3. Extracción de Contenido Principal
        col_content = soup.find("main").find("div", class_="col-lg-9") if soup.find("main") else None
        if not col_content:
            logger.error(f"❌ No se encontró el contenedor de texto de la norma ID {target_id}")
            return None

        # Limpiar elementos no textuales
        for tag in col_content(["script", "style", "button", "input", "form", "svg"]):
            tag.decompose()

        # Quitar disclaimer institucional inicial si existe
        raw_text = col_content.get_text(separator="\n", strip=True)
        disclaimer = "Los datos publicados tienen propósitos exclusivamente informativos."
        if disclaimer in raw_text:
            idx = raw_text.find(disclaimer)
            end_idx = raw_text.find("\n", idx + len(disclaimer))
            if end_idx != -1:
                raw_text = raw_text[end_idx:].strip()

        # Normalizar saltos de línea repetidos
        clean_text_content = re.sub(r"\n{3,}", "\n\n", raw_text)

        slug = catalog_entry.slug if catalog_entry else f"norma_{target_id}"
        nombre = catalog_entry.nombre if catalog_entry else title
        categoria = catalog_entry.categoria if catalog_entry else "general"
        tipo_norma = catalog_entry.tipo_norma if catalog_entry else "LEY"
        numero_oficial = catalog_entry.numero_oficial if catalog_entry else title
        emisor = catalog_entry.emisor if catalog_entry else "República de Colombia"
        status = catalog_entry.status if catalog_entry else "VIGENTE"

        doc = ScrapedDocument(
            id=target_id,
            slug=slug,
            nombre=nombre,
            categoria=categoria,
            tipo_norma=tipo_norma,
            numero_oficial=numero_oficial,
            emisor=emisor,
            status=status,
            fuente_url=url,
            fecha_expedicion=fecha_expedicion,
            fecha_vigencia=fecha_vigencia,
            medio_publicacion=medio_publicacion,
            temas=temas,
            texto_completo=clean_text_content,
            caracteres_total=len(clean_text_content),
        )

        logger.info(f"✅ Extraída exitosamente: {nombre} ({doc.caracteres_total:,} caracteres)")
        return doc

    except Exception as e:
        logger.error(f"❌ Excepción durante extracción de ID {target_id}: {e}")
        return None


def save_scraped_document(doc: ScrapedDocument, output_dir: Path) -> tuple[Path, Path]:
    """Guarda el documento en formato .txt e información estructurada en .json."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Guardar archivo .txt con encabezado canónico para ingesta en LegalIA
    txt_path = output_dir / f"{doc.slug}.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(f"{doc.nombre.upper()}\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Identificador Oficial: {doc.numero_oficial}\n")
        f.write(f"Emisor: {doc.emisor}\n")
        f.write(f"Estado de Vigencia: {doc.status}\n")
        f.write(f"Fuente Oficial: {doc.fuente_url}\n")
        if doc.fecha_expedicion:
            f.write(f"Fecha de Expedición: {doc.fecha_expedicion}\n")
        if doc.fecha_vigencia:
            f.write(f"Fecha de Entrada en Vigencia: {doc.fecha_vigencia}\n")
        if doc.medio_publicacion:
            f.write(f"Medio de Publicación: {doc.medio_publicacion}\n")
        f.write("\n" + "=" * 80 + "\n\n")
        f.write(doc.texto_completo)
        f.write("\n")

    # 2. Guardar archivo .json con metadatos completos
    json_path = output_dir / f"{doc.slug}.json"
    data = asdict(doc)
    # En JSON podemos excluir o resumir el texto completo si se desea, pero mantenerlo completo asegura persistencia íntegra
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return txt_path, json_path


async def run_scraper(
    catalog: list[NormCatalogEntry],
    output_dir: Path,
    delay: float = 1.5,
) -> list[ScrapedDocument]:
    """Ejecuta la extracción de una lista de normas con rate limiting respetuoso."""
    scraped: list[ScrapedDocument] = []

    headers = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    }

    async with httpx.AsyncClient(headers=headers, verify=False, follow_redirects=True) as client:
        total = len(catalog)
        for idx, entry in enumerate(catalog, 1):
            logger.info(f"[{idx}/{total}] Procesando {entry.nombre}...")
            doc = await fetch_norma(client, catalog_entry=entry)
            if doc:
                txt_path, json_path = save_scraped_document(doc, output_dir)
                logger.info(f"   💾 TXT: {txt_path.name} | JSON: {json_path.name}")
                scraped.append(doc)
            else:
                logger.warning(f"   ⚠️ No se pudo extraer la norma {entry.nombre}")

            if idx < total:
                await asyncio.sleep(delay)

    return scraped


def main():
    parser = argparse.ArgumentParser(
        description="Scraper oficial de legislación colombiana para el corpus LegalIA."
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Extraer todas las normas y códigos del catálogo oficial curado.",
    )
    parser.add_argument(
        "--category",
        choices=["constitucional", "penal", "procesal", "administrativo", "laboral", "comercial", "civil", "disciplinario"],
        help="Filtrar extracción por categoría jurídica.",
    )
    parser.add_argument(
        "--id",
        type=int,
        help="Extraer una norma específica por su ID del Gestor Normativo.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Listar el catálogo de normas disponibles.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("corpus/oficial"),
        help="Directorio de destino para los archivos extraídos (default: %(default)s).",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.2,
        help="Pausa en segundos entre peticiones para respetar los servidores del Estado (default: %(default)s).",
    )

    args = parser.parse_args()

    if args.list:
        print("\n🏛️  CATÁLOGO OFICIAL DE LEGISLACIÓN COLOMBIANA (LegalIA)")
        print("=" * 85)
        for n in CATALOGO_NORMAS:
            print(f"[{n.id:6d}] {n.categoria.upper():14s} | {n.numero_oficial:30s} | {n.nombre}")
        print("=" * 85)
        print(f"Total normas catalogadas: {len(CATALOGO_NORMAS)}\n")
        return

    if httpx is None or BeautifulSoup is None:
        print("\n❌ Dependencias requeridas (`httpx`, `beautifulsoup4`) no encontradas en este entorno.")
        print("💡 Ejecuta el script dentro del contenedor Docker (donde ya están instaladas):")
        print("   docker compose exec legalia-api python scripts/scrape_corpus.py --all")
        print("\n💡 O instálalas en tu entorno local:")
        print("   pip install httpx beautifulsoup4 lxml\n")
        sys.exit(1)

    if args.id:
        # Buscar en catálogo o construir entrada genérica
        entry = next((e for e in CATALOGO_NORMAS if e.id == args.id), None)
        to_scrape = [entry] if entry else [NormCatalogEntry(
            id=args.id,
            slug=f"norma_{args.id}",
            nombre=f"Norma Oficial {args.id}",
            categoria="general",
            emisor="República de Colombia",
            tipo_norma="LEY",
            numero_oficial=f"Norma {args.id}",
        )]
    elif args.category:
        to_scrape = [e for e in CATALOGO_NORMAS if e.categoria.lower() == args.category.lower()]
        if not to_scrape:
            logger.error(f"No hay normas bajo la categoría '{args.category}'")
            sys.exit(1)
    elif args.all:
        to_scrape = CATALOGO_NORMAS
    else:
        parser.print_help()
        print("\n💡 Ejemplo: python scripts/scrape_corpus.py --all")
        print("💡 Ejemplo: python scripts/scrape_corpus.py --category constitucional")
        print("💡 Ejemplo: python scripts/scrape_corpus.py --list\n")
        return

    output_dir = args.output_dir.resolve()
    logger.info(f"🚀 Iniciando extracción de {len(to_scrape)} norma(s) oficial(es) hacia {output_dir}")
    
    results = asyncio.run(run_scraper(to_scrape, output_dir, delay=args.delay))

    total_chars = sum(d.caracteres_total for d in results)
    print("\n" + "━" * 60)
    print("📊 RESUMEN DE EXTRACCIÓN DE CORPUS OFICIAL")
    print(f"✅ Normas extraídas con éxito: {len(results)} de {len(to_scrape)}")
    print(f"📝 Total caracteres normativos: {total_chars:,}")
    print(f"📁 Directorio de salida: {output_dir}")
    print("━" * 60 + "\n")
    print("Para ingestar el corpus en la base de datos vectorial:")
    print(f"   PYTHONPATH=backend:. python -m ingestion.main --directory {output_dir} --status VIGENTE\n")


if __name__ == "__main__":
    main()
