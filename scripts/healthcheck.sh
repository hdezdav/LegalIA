#!/usr/bin/env bash
# =============================================================================
# LegalIA - system health check
# =============================================================================
# Probes the API health endpoint and reports per-dependency status. Exits
# non-zero when any dependency is not "ok", so it can be used from cron or a
# deployment gate.
#
#   ./scripts/healthcheck.sh
#   API_BASE_URL=https://legalia.example.com ./scripts/healthcheck.sh
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

API_BASE_URL="${API_BASE_URL:-http://localhost:${API_PORT:-8000}}"
ENDPOINT="${API_BASE_URL%/}/api/v1/health"

echo "[health] GET ${ENDPOINT}"

HTTP_BODY_FILE="$(mktemp)"
trap 'rm -f "$HTTP_BODY_FILE"' EXIT

HTTP_CODE="$(curl -sS -o "$HTTP_BODY_FILE" -w '%{http_code}' --max-time 10 "$ENDPOINT" || echo "000")"
BODY="$(cat "$HTTP_BODY_FILE")"

if [[ "$HTTP_CODE" == "000" ]]; then
  echo "[health] UNREACHABLE: no response from ${ENDPOINT}" >&2
  exit 1
fi

if command -v jq >/dev/null 2>&1; then
  echo "$BODY" | jq .
else
  echo "$BODY"
fi

# 503 is the documented response when a dependency is degraded; the body still
# carries the per-component detail printed above.
if [[ "$HTTP_CODE" != "200" ]]; then
  echo "[health] DEGRADED: HTTP ${HTTP_CODE}" >&2
  exit 1
fi

echo "[health] ok"
