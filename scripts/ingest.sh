#!/usr/bin/env bash
# =============================================================================
# LegalIA - document ingestion wrapper
# =============================================================================
# Thin wrapper around `python -m ingestion.main` that runs inside the API
# container, so ingestion always uses the same providers and database as the
# running system.
#
#   ./scripts/ingest.sh --file corpus/constitucion.pdf
#   ./scripts/ingest.sh --directory corpus/constitucional/
#
# Paths are interpreted inside the container. The repository root is mounted at
# /app, so repository-relative paths work as-is.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$ROOT_DIR"

API_SERVICE="${API_SERVICE:-legalia-api}"

if [[ $# -eq 0 ]]; then
  echo "usage: $0 --file <path> | --directory <path> [ingestion options]" >&2
  echo >&2
  echo "Examples:" >&2
  echo "  $0 --file corpus/constitucion.pdf" >&2
  echo "  $0 --directory corpus/constitucional/ --document-type LEY" >&2
  exit 2
fi

echo "[ingest] service=${API_SERVICE} args=$*"

docker compose exec -T "$API_SERVICE" python -m ingestion.main "$@"

echo "[ingest] done"
