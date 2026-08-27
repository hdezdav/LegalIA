"""HTML loader.

Written for how Colombian legal portals actually serve documents: the norm's text
sits inside a page full of navigation, breadcrumbs, related-links panels and
footers. Those must be stripped before chunking, because boilerplate that survives
into a chunk gets embedded, retrieved, and can end up quoted in a citation.

Extraction therefore prefers the page's main content container and only falls back
to the whole body when no such container exists.
"""

from __future__ import annotations

from pathlib import Path

from bs4 import BeautifulSoup, Tag

from ingestion.loaders.base import DocumentLoader, LoadedDocument, LoaderError

# Removed outright: these never carry legal text.
_DROP_TAGS = (
    "script",
    "style",
    "nav",
    "header",
    "footer",
    "aside",
    "form",
    "button",
    "noscript",
    "iframe",
    "svg",
)

# Tried in order to locate the document body. Ordered most to least specific.
_CONTENT_SELECTORS = (
    "main",
    "article",
    "[role=main]",
    "#contenido",
    "#content",
    ".contenido",
    ".content",
    "#texto",
    ".texto-norma",
    ".documento",
)

# Block-level tags whose boundaries must survive as newlines. Without this,
# BeautifulSoup runs an article's heading into its first sentence and the splitter
# can no longer see the structure.
_BLOCK_TAGS = (
    "p",
    "div",
    "br",
    "li",
    "tr",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "section",
    "blockquote",
)


class HTMLLoader(DocumentLoader):
    suffixes = (".html", ".htm", ".xhtml")

    def __init__(self, max_bytes: int) -> None:
        self.max_bytes = max_bytes

    def load(self, path: Path) -> LoadedDocument:
        raw = self.read_bytes(path, self.max_bytes)

        # lxml handles the malformed markup these portals emit, and honours the
        # document's own meta charset rather than assuming UTF-8.
        soup = BeautifulSoup(raw, "lxml")

        title = _document_title(soup)
        source_url = _canonical_url(soup)

        for tag in soup.find_all(_DROP_TAGS):
            tag.decompose()

        container, selector = _content_container(soup)
        _mark_block_boundaries(container)

        text = container.get_text("\n")
        text = "\n".join(line.strip() for line in text.splitlines())

        if not text.strip():
            raise LoaderError(f"No text content found in {path}")

        return LoadedDocument(
            text=text,
            source_path=path,
            content_hash=self.hash_file(path),
            title=title,
            raw_metadata={
                "loader": "html",
                # Which container was used, so an operator can tell a clean
                # extraction from a whole-page fallback that may retain menus.
                "content_selector": selector,
                # Carried through to Document.source_url when the caller did not
                # supply one: the page knows its own canonical address.
                "source_url": source_url,
            },
        )


def _content_container(soup: BeautifulSoup) -> tuple[Tag, str]:
    """Locate the element holding the document text.

    Falls back to <body>, then to the whole tree, and reports which was used.
    """
    for selector in _CONTENT_SELECTORS:
        found = soup.select_one(selector)
        # Guard against a decorative <main> that holds almost nothing.
        if found is not None and len(found.get_text(strip=True)) > 200:
            return found, selector

    if soup.body is not None:
        return soup.body, "body"

    return soup, "document"


def _mark_block_boundaries(container: Tag) -> None:
    """Append a newline after every block element.

    Done before `get_text` so paragraph and heading breaks are preserved as line
    breaks, which is what LegalTextSplitter keys on.
    """
    for tag in container.find_all(_BLOCK_TAGS):
        tag.append("\n")


def _document_title(soup: BeautifulSoup) -> str | None:
    """Prefer a visible <h1>; fall back to <title>.

    <title> is often decorated with the portal's name, so an <h1> inside the
    document is closer to the legal title.
    """
    if (h1 := soup.find("h1")) is not None:
        text = h1.get_text(" ", strip=True)
        if 10 <= len(text) <= 512:
            return text

    if soup.title is not None and soup.title.string:
        text = " ".join(soup.title.string.split())
        if 10 <= len(text) <= 512:
            return text

    return None


def _canonical_url(soup: BeautifulSoup) -> str | None:
    """The page's own canonical or og:url, when present."""
    if (link := soup.find("link", rel="canonical")) is not None:
        href = link.get("href")
        if isinstance(href, str) and href.startswith("http"):
            return href

    if (meta := soup.find("meta", property="og:url")) is not None:
        content = meta.get("content")
        if isinstance(content, str) and content.startswith("http"):
            return content

    return None
