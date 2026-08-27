"""LegalTextSplitter tests.

The properties asserted here are the ones citation precision rests on:

* chunks are cut at the document's own structural boundaries, not at a character
  count;
* every chunk carries a `section` label that names its location;
* `char_start`/`char_end` are exact offsets, so a quoted excerpt can be located in
  the source;
* content is never rewritten — every chunk is a verbatim substring of the input.

If any of these break, a citation stops being verifiable, which is the one thing
the product cannot lose.
"""

from __future__ import annotations

import pytest
from ingestion.processors.legal_splitter import (
    LegalTextSplitter,
    SectionKind,
)

CONSTITUCION = """TÍTULO II
DE LOS DERECHOS, LAS GARANTÍAS Y LOS DEBERES

CAPÍTULO I
DE LOS DERECHOS FUNDAMENTALES

ARTÍCULO 11. El derecho a la vida es inviolable. No habrá pena de muerte.

ARTÍCULO 12. Nadie será sometido a desaparición forzada, a torturas ni a tratos o penas crueles, inhumanos o degradantes.

ARTÍCULO 90. El Estado responderá patrimonialmente por los daños antijurídicos que le sean imputables, causados por la acción o la omisión de las autoridades públicas.

PARÁGRAFO. En el evento de ser condenado el Estado a la reparación patrimonial de uno de tales daños, que haya sido consecuencia de la conducta dolosa o gravemente culposa de un agente suyo, aquél deberá repetir contra éste.
"""


@pytest.fixture
def splitter() -> LegalTextSplitter:
    return LegalTextSplitter(chunk_size=1000, chunk_overlap=200, min_chunk_size=20)


# --- Structural detection ---------------------------------------------------


def test_finds_articles(splitter: LegalTextSplitter) -> None:
    sections = splitter.find_sections(CONSTITUCION)

    articles = [s for s in sections if s.kind is SectionKind.ARTICULO]
    assert [s.number for s in articles] == ["11", "12", "90"]


def test_finds_containers_and_nested_paragraph(splitter: LegalTextSplitter) -> None:
    kinds = {s.kind for s in splitter.find_sections(CONSTITUCION)}

    assert SectionKind.TITULO in kinds
    assert SectionKind.CAPITULO in kinds
    assert SectionKind.PARAGRAFO in kinds


@pytest.mark.parametrize(
    "heading",
    [
        "ARTÍCULO 90. El Estado responderá.",
        "Artículo 90. El Estado responderá.",
        "ARTICULO 90. El Estado responderá.",
        "ARTÍCULO 90º. El Estado responderá.",
        "ARTÍCULO 90.- El Estado responderá.",
        "ART. 90. El Estado responderá.",
        "Art. 90.- El Estado responderá.",
    ],
)
def test_recognizes_article_heading_variants(
    splitter: LegalTextSplitter, heading: str
) -> None:
    """The same norm is transcribed differently across official sources; all of
    these appear in real Colombian material."""
    sections = splitter.find_sections(heading)

    assert len(sections) == 1
    assert sections[0].kind is SectionKind.ARTICULO
    assert sections[0].number == "90"


@pytest.mark.parametrize(
    "heading",
    ["ARTÍCULO ÚNICO. Esta ley rige.", "ARTÍCULO TRANSITORIO. Mientras se expida."],
)
def test_recognizes_named_articles(splitter: LegalTextSplitter, heading: str) -> None:
    sections = splitter.find_sections(heading)

    assert sections[0].kind is SectionKind.ARTICULO
    assert sections[0].number in ("ÚNICO", "TRANSITORIO")


def test_does_not_mistake_a_year_for_a_numeral(splitter: LegalTextSplitter) -> None:
    """A line starting with a number is not automatically a heading; otherwise
    ordinary prose would be shredded into fragments."""
    text = "El contrato se firmó en 2019. Las partes acordaron lo siguiente."

    sections = splitter.find_sections(text)

    assert sections == []


def test_does_not_treat_an_inline_article_reference_as_a_heading(
    splitter: LegalTextSplitter,
) -> None:
    """"...conforme al artículo 90..." mid-sentence is a citation, not a section."""
    text = "La Corte aplicó lo dispuesto en el artículo 90 de la Constitución."

    assert splitter.find_sections(text) == []


# --- Chunk addressing -------------------------------------------------------


def test_every_chunk_has_a_section_label(splitter: LegalTextSplitter) -> None:
    """A chunk with no address can only ever be cited as "somewhere in the PDF"."""
    chunks = splitter.split(CONSTITUCION)

    assert chunks
    assert all(chunk.section for chunk in chunks)


def test_article_chunks_are_separate(splitter: LegalTextSplitter) -> None:
    chunks = splitter.split(CONSTITUCION)

    numbers = [c.article_number for c in chunks if c.article_number]
    assert "11" in numbers
    assert "90" in numbers


def test_article_90_is_retrievable_as_its_own_chunk(
    splitter: LegalTextSplitter,
) -> None:
    chunks = splitter.split(CONSTITUCION)

    article_90 = next(c for c in chunks if c.article_number == "90")
    assert "responderá patrimonialmente" in article_90.content
    assert article_90.section is not None
    assert "90" in article_90.section


def test_nested_paragraph_is_addressed_through_its_article(
    splitter: LegalTextSplitter,
) -> None:
    """"Parágrafo 1" alone is ambiguous across a whole code; prefixing the article
    is what makes the citation unambiguous."""
    chunks = splitter.split(CONSTITUCION)

    paragraph = next(c for c in chunks if "deberá repetir contra éste" in c.content)
    assert paragraph.section is not None
    assert "90" in paragraph.section
    assert "arágrafo" in paragraph.section


def test_hierarchy_path_records_the_ancestor_chain(
    splitter: LegalTextSplitter,
) -> None:
    chunks = splitter.split(CONSTITUCION)

    article_90 = next(c for c in chunks if c.article_number == "90")
    assert article_90.hierarchy_path is not None
    assert "Título II" in article_90.hierarchy_path
    assert "Capítulo I" in article_90.hierarchy_path


def test_chunk_indexes_are_sequential(splitter: LegalTextSplitter) -> None:
    """`chunks.chunk_index` is UNIQUE per document and restores reading order."""
    chunks = splitter.split(CONSTITUCION)

    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))


# --- Offsets and verbatim content -------------------------------------------


def test_offsets_locate_the_chunk_in_the_source(splitter: LegalTextSplitter) -> None:
    """Exact offsets are what let a cited excerpt be highlighted in the original."""
    chunks = splitter.split(CONSTITUCION)

    for chunk in chunks:
        assert CONSTITUCION[chunk.char_start : chunk.char_end] == chunk.content


def test_content_is_never_rewritten(splitter: LegalTextSplitter) -> None:
    """Every chunk must be a verbatim substring: an altered quote would make the
    citation lie."""
    chunks = splitter.split(CONSTITUCION)

    for chunk in chunks:
        assert chunk.content in CONSTITUCION


def test_accents_survive_splitting(splitter: LegalTextSplitter) -> None:
    chunks = splitter.split(CONSTITUCION)

    joined = " ".join(c.content for c in chunks)
    assert "antijurídicos" in joined
    assert "PARÁGRAFO" in joined or "arágrafo" in joined


# --- Oversized sections -----------------------------------------------------


def test_long_article_is_divided_into_parts() -> None:
    """A single article can exceed any context budget; it must be divisible while
    still reporting which article it came from."""
    long_body = " ".join(
        f"El numeral {i} establece una obligación específica que debe cumplirse "
        "conforme a la reglamentación vigente." for i in range(1, 120)
    )
    text = f"ARTÍCULO 15. {long_body}"

    splitter = LegalTextSplitter(chunk_size=150, chunk_overlap=20, min_chunk_size=10)
    chunks = splitter.split(text)

    assert len(chunks) > 1
    assert all(c.article_number == "15" for c in chunks)
    assert all(c.is_partial for c in chunks)
    assert [c.part_index for c in chunks] == list(range(1, len(chunks) + 1))
    assert all(c.part_total == len(chunks) for c in chunks)


def test_divided_parts_keep_exact_offsets() -> None:
    long_body = " ".join(
        f"Disposición {i} sobre el cumplimiento de la obligación legal." for i in range(80)
    )
    text = f"ARTÍCULO 15. {long_body}"

    splitter = LegalTextSplitter(chunk_size=120, chunk_overlap=15, min_chunk_size=10)
    chunks = splitter.split(text)

    for chunk in chunks:
        assert text[chunk.char_start : chunk.char_end] == chunk.content


def test_division_never_cuts_mid_word() -> None:
    """A truncated word would corrupt both the embedding and any excerpt quoted
    from it."""
    long_body = " ".join(
        "responsabilidad patrimonial extracontractual del Estado colombiano"
        for _ in range(120)
    )
    text = f"ARTÍCULO 90. {long_body}"

    splitter = LegalTextSplitter(chunk_size=100, chunk_overlap=10, min_chunk_size=10)
    chunks = splitter.split(text)

    for chunk in chunks:
        assert not chunk.content.startswith("dad ")
        assert chunk.content == chunk.content.strip()
        # No chunk may begin or end inside a word.
        if chunk.char_start > 0:
            assert text[chunk.char_start - 1] in " \n"


def test_short_article_is_not_divided(splitter: LegalTextSplitter) -> None:
    chunks = splitter.split("ARTÍCULO 11. El derecho a la vida es inviolable.")

    assert len(chunks) == 1
    assert not chunks[0].is_partial


# --- Container merging ------------------------------------------------------


def test_bare_container_heading_is_merged_forward() -> None:
    """"CAPÍTULO II" on its own line introduces the articles beneath it; on its own
    it is not a retrievable unit."""
    text = (
        "CAPÍTULO II\nDE LAS GARANTÍAS\n\n"
        "ARTÍCULO 20. Se garantiza a toda persona la libertad de expresar "
        "su pensamiento y opiniones."
    )

    splitter = LegalTextSplitter(chunk_size=1000, chunk_overlap=100, min_chunk_size=30)
    chunks = splitter.split(text)

    assert len(chunks) == 1
    assert "CAPÍTULO II" in chunks[0].content
    assert "libertad de expresar" in chunks[0].content


# --- Jurisprudence ----------------------------------------------------------


def test_splits_a_judgment_into_considerandos_and_resolutivos() -> None:
    """Judgments are structured differently from statutes: the operative part is
    what gets cited, and it must be addressable on its own."""
    text = """SENTENCIA C-355 DE 2006

CONSIDERANDO

La Corte encuentra que la penalización absoluta del aborto vulnera los derechos
fundamentales de la mujer.

RESUELVE

PRIMERO.- Declarar EXEQUIBLE el artículo 122 del Código Penal, en el entendido
de que no se incurre en delito en los casos señalados.

SEGUNDO.- Declarar INEXEQUIBLE la expresión demandada.
"""

    splitter = LegalTextSplitter(chunk_size=1000, chunk_overlap=100, min_chunk_size=15)
    chunks = splitter.split(text)

    labels = " | ".join(c.section or "" for c in chunks)
    assert "Considerando" in labels
    assert "Resuelve" in labels or "Primero" in labels

    operative = next(c for c in chunks if "EXEQUIBLE el artículo 122" in c.content)
    assert operative.section is not None


# --- Unstructured fallback --------------------------------------------------


def test_text_without_structure_still_produces_chunks(
    splitter: LegalTextSplitter,
) -> None:
    """A doctrinal note or a concepto may have no headings at all; it must remain
    ingestible."""
    text = " ".join(
        "La doctrina nacional ha sostenido que la carga de la prueba corresponde "
        "a quien alega el incumplimiento contractual." for _ in range(5)
    )

    chunks = splitter.split(text)

    assert chunks
    assert all(c.section is None for c in chunks)
    assert all(c.content in text for c in chunks)


def test_empty_input_produces_no_chunks(splitter: LegalTextSplitter) -> None:
    assert splitter.split("") == []
    assert splitter.split("   \n\n  ") == []


# --- Configuration ----------------------------------------------------------


def test_overlap_must_be_smaller_than_chunk_size() -> None:
    with pytest.raises(ValueError, match="chunk_overlap"):
        LegalTextSplitter(chunk_size=100, chunk_overlap=100)


def test_min_chunk_size_must_be_smaller_than_chunk_size() -> None:
    with pytest.raises(ValueError, match="min_chunk_size"):
        LegalTextSplitter(chunk_size=100, chunk_overlap=10, min_chunk_size=100)


def test_token_counts_are_positive(splitter: LegalTextSplitter) -> None:
    """`chunks.token_count` carries a CHECK (token_count > 0)."""
    chunks = splitter.split(CONSTITUCION)

    assert all(c.token_count > 0 for c in chunks)
