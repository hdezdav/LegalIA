#!/usr/bin/env bash
# =============================================================================
# LegalIA - PostgreSQL backup
# =============================================================================
# Creates a compressed pg_dump of the LegalIA database and prunes backups older
# than BACKUP_RETENTION_DAYS. Intended to run from the repository root, either
# manually or from cron.
#
#   ./scripts/backup.sh
#
# Off-site replication is NOT handled here. See docs/SECURITY.md.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$ROOT_DIR"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

POSTGRES_DB="${POSTGRES_DB:-legalia}"
POSTGRES_USER="${POSTGRES_USER:-legalia}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
COMPOSE_SERVICE="${POSTGRES_SERVICE:-postgres}"

mkdir -p "$BACKUP_DIR"

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
TARGET="${BACKUP_DIR}/legalia_${TIMESTAMP}.sql.gz"

echo "[backup] database=${POSTGRES_DB} target=${TARGET}"

# --clean --if-exists makes the dump restorable over an existing database.
# Streamed straight into gzip so the uncompressed dump never touches disk.
docker compose exec -T "$COMPOSE_SERVICE" \
  pg_dump \
    --username="$POSTGRES_USER" \
    --dbname="$POSTGRES_DB" \
    --clean \
    --if-exists \
    --no-owner \
    --no-privileges \
  | gzip -9 > "$TARGET"

if [[ ! -s "$TARGET" ]]; then
  echo "[backup] FAILED: dump is empty, removing ${TARGET}" >&2
  rm -f "$TARGET"
  exit 1
fi

SIZE="$(du -h "$TARGET" | cut -f1)"
echo "[backup] ok size=${SIZE}"

echo "[backup] pruning backups older than ${BACKUP_RETENTION_DAYS} days"
find "$BACKUP_DIR" -name 'legalia_*.sql.gz' -type f -mtime "+${BACKUP_RETENTION_DAYS}" -print -delete

echo "[backup] done"
echo
echo "Restore with:"
echo "  gunzip -c ${TARGET} | docker compose exec -T ${COMPOSE_SERVICE} psql -U ${POSTGRES_USER} -d ${POSTGRES_DB}"
