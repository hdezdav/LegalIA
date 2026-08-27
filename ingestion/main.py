"""Ingestion CLI.

    python -m ingestion.main --file corpus/constitucion.txt
    python -m ingestion.main --directory corpus/ --source-name "Corpus de prueba"
    python -m ingestion.main --file ley_1437.pdf --status VIGENTE --dry-run

Runs the full pipeline for each file:

    load -> clean -> extract metadata -> split -> embed -> store

Two defaults worth knowing about:

**`--status` defaults to DESCONOCIDO.** Vigencia is never inferred from a
document's text, because a norm almost never states that it was repealed.
Assuming VIGENTE from silence is exactly the failure the unknown state exists to
prevent, so marking a document current is an explicit operator decision.

**One document per transaction.** A malformed file in a directory of 200 does not
roll back the 199 that succeeded, and it is reported rather than swallowed.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.db.models.enums import DocumentStatus
from app.db.session import SessionLocal
from app.providers.embeddings import get_embedding_provider
from app.providers.embeddings.base import EmbeddingError
from ingestion.embeddings.generator import EmbeddingGenerator
from ingestion.indexer import CitedDocumentError, DocumentIndexer, IngestionError
from ingestion.loaders import LoaderError, load, supported_suffixes
from ingestion.processors.cleaner import clean_text
from ingestion.processors.legal_splitter import LegalTextSplitter
from ingestion.processors.metadata import extract_metadata

logger = get_logger(__name__)

#: Cleaning that removes more than this fraction of a document usually means the
#: extraction was mostly page furniture. Warned about, not blocked: some sources
#: legitimately carry that much boilerplate.
_SUSPICIOUS_REMOVAL_RATIO = 0.5


@dataclass(slots=True)
class FileResult:
    path: Path
    ok: bool
    detail: str
    chunk_count: int = 0
    skipped: bool = False


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m ingestion.main",
        description="Ingest legal documents into the LegalIA corpus.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Supported file types: " + ", ".join(supported_suffixes()) + "\n\n"
            "Vigencia (--status) is never guessed from document text. Leave it "
            "unset to store DESCONOCIDO, which is surfaced to users as "
            "'vigencia no verificada'."
        ),
    )

    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--file", type=Path, help="Ingest a single file.")
    target.add_argument("--directory", type=Path, help="Ingest every supported file in a directory.")

    parser.add_argument(
        "--recursive",
        action="store_true",
        help="With --directory, descend into subdirectories.",
    )
    parser.add_argument(
        "--source-name",
        default="Ingesta manual",
        help="Provenance label stored on each document (default: %(default)s).",
    )
    parser.add_argument(
        "--source-url",
        default=None,
        help="Official URL for the document, shown in citations.",
    )
    parser.add_argument(
        "--status",
        choices=[s.value for s in DocumentStatus],
        default=DocumentStatus.DESCONOCIDO.value,
        help="Vigencia to record (default: %(default)s).",
    )
    parser.add_argument(
        "--status-note",
        default=None,
        help="Explanation shown alongside a non-VIGENTE status.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-ingest even when content and embedding model are unchanged.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run load, clean, metadata and split; skip embedding and writes.",
    )
    return parser


async def main(argv: list[str] | None = None) -> int:
    configure_logging()
    args = build_parser().parse_args(argv)

    paths = _collect_paths(args)
    if not paths:
        print("No supported files found.", file=sys.stderr)
        return 1

    print(f"Files to process: {len(paths)}")
    print(f"Embedding provider: {settings.EMBEDDING_PROVIDER} "
          f"(dimension {settings.embedding_dimension})")
    if settings.EMBEDDING_PROVIDER == "mock":
        print(
            "WARNING: the mock embedding provider is active. Retrieval will run "
            "but its quality is not meaningful and must not be evaluated."
        )
    print(f"Vigencia to record: {args.status}")
    if args.dry_run:
        print("DRY RUN: nothing will be embedded or written.")
    print()

    splitter = LegalTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
        min_chunk_size=settings.MIN_CHUNK_SIZE,
    )

    generator: EmbeddingGenerator | None = None
    indexer: DocumentIndexer | None = None
    if not args.dry_run:
        provider = get_embedding_provider()
        generator = EmbeddingGenerator(provider)
        indexer = DocumentIndexer(embedding_model=provider.model_id)

    results = [
        await _process_file(path, args, splitter, generator, indexer) for path in paths
    ]

    return _report(results)


#: Filenames skipped by a directory scan. These are repository documentation that
#: happens to sit next to the corpus, and ingesting them is actively harmful: a
#: README describing the corpus mentions the same norms it documents, so metadata
#: extraction reads it as that norm and assigns it the same external_id, colliding
#: with the real document on the (source_name, external_id) UNIQUE constraint.
#:
#: An explicit --file always wins: this only guards the scan.
_SKIPPED_STEMS = frozenset({"readme", "license", "licence", "changelog", "contributing", "notice"})


def _collect_paths(args: argparse.Namespace) -> list[Path]:
    suffixes = set(supported_suffixes())

    if args.file:
        if not args.file.is_file():
            print(f"Not a file: {args.file}", file=sys.stderr)
            return []
        return [args.file]

    directory: Path = args.directory
    if not directory.is_dir():
        print(f"Not a directory: {directory}", file=sys.stderr)
        return []

    pattern = "**/*" if args.recursive else "*"
    paths: list[Path] = []
    skipped: list[Path] = []

    for path in sorted(directory.glob(pattern)):
        if not path.is_file() or path.suffix.lower() not in suffixes:
            continue
        if path.stem.lower() in _SKIPPED_STEMS:
            skipped.append(path)
            continue
        paths.append(path)

    # Reported rather than silent: a file the operator expected to ingest and that
    # was skipped must not simply be absent from the results.
    for path in skipped:
        print(f"Skipping documentation file: {path.name} (pass --file to force)")

    return paths


async def _process_file(
    path: Path,
    args: argparse.Namespace,
    splitter: LegalTextSplitter,
    generator: EmbeddingGenerator | None,
    indexer: DocumentIndexer | None,
) -> FileResult:
    print(f"-> {path.name}")

    try:
        loaded = load(path)
    except LoaderError as exc:
        print(f"   FAILED: {exc}")
        return FileResult(path, False, str(exc))

    cleaned, report = clean_text(loaded.text)
    if not cleaned:
        detail = "cleaning removed all content"
        print(f"   FAILED: {detail}")
        return FileResult(path, False, detail)

    if report.removed_ratio > _SUSPICIOUS_REMOVAL_RATIO:
        print(
            f"   WARNING: cleaning removed {report.removed_ratio:.0%} of the text "
            f"({report.dropped_lines} lines dropped). Check the extraction."
        )

    metadata = extract_metadata(
        cleaned, fallback_title=path.stem, loader_title=loaded.title
    )
    chunks = splitter.split(cleaned)

    if not chunks:
        detail = "splitter produced no chunks"
        print(f"   FAILED: {detail}")
        return FileResult(path, False, detail)

    located = sum(1 for chunk in chunks if chunk.section)
    print(f"   {metadata.document_type.value}: {metadata.title}")
    if metadata.external_id:
        print(f"   external_id: {metadata.external_id}")
    print(
        f"   chunks: {len(chunks)} ({located} with a section label), "
        f"~{sum(c.token_count for c in chunks)} tokens"
    )

    if args.dry_run or generator is None or indexer is None:
        return FileResult(path, True, "dry run", chunk_count=len(chunks))

    try:
        embedded = await generator.embed_chunks([chunk.content for chunk in chunks])
    except EmbeddingError as exc:
        print(f"   FAILED: embedding error: {exc}")
        return FileResult(path, False, f"embedding: {exc}")

    # One transaction per document: a failure here leaves previously ingested
    # documents intact.
    session = SessionLocal()
    try:
        outcome = indexer.store(
            session,
            metadata=metadata,
            chunks=chunks,
            vectors=embedded.vectors,
            content_hash=loaded.content_hash,
            source_name=args.source_name,
            source_path=path,
            source_url=args.source_url or loaded.raw_metadata.get("source_url"),
            status=DocumentStatus(args.status),
            status_note=args.status_note,
            force=args.force,
        )
        session.commit()
    except CitedDocumentError as exc:
        session.rollback()
        print(f"   REFUSED: {exc}")
        return FileResult(path, False, "cited chunks would be destroyed")
    except IngestionError as exc:
        session.rollback()
        print(f"   FAILED: {exc}")
        return FileResult(path, False, str(exc))
    except Exception as exc:  # noqa: BLE001 - report and continue to the next file
        session.rollback()
        logger.exception("unexpected ingestion failure", extra={"file": path.name})
        print(f"   FAILED: {type(exc).__name__}")
        return FileResult(path, False, type(exc).__name__)
    finally:
        session.close()

    if outcome.skipped:
        print(f"   SKIPPED: {outcome.reason}")
        return FileResult(
            path, True, outcome.reason, chunk_count=outcome.chunk_count, skipped=True
        )

    action = "replaced" if outcome.replaced else "stored"
    print(f"   {action}: document {outcome.document_id}, {outcome.chunk_count} chunks")
    return FileResult(path, True, action, chunk_count=outcome.chunk_count)


def _report(results: list[FileResult]) -> int:
    stored = [r for r in results if r.ok and not r.skipped]
    skipped = [r for r in results if r.skipped]
    failed = [r for r in results if not r.ok]

    print()
    print("=" * 60)
    print(f"Processed : {len(results)}")
    print(f"Stored    : {len(stored)} ({sum(r.chunk_count for r in stored)} chunks)")
    print(f"Skipped   : {len(skipped)}")
    print(f"Failed    : {len(failed)}")

    if failed:
        print()
        print("Failures:")
        for result in failed:
            print(f"  {result.path.name}: {result.detail}")

    # Non-zero on any failure, so a scripted ingest can be gated on it.
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
