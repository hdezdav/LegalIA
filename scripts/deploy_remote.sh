#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# LegalIA - Remote Production Deployment Script
# Target: $VPS_IP ($REMOTE_DIR)
# ==============================================================================

VPS_IP="${VPS_IP:-}"
if [ -z "$VPS_IP" ]; then
    echo "❌ VPS_IP environment variable is required (e.g. export VPS_IP=x.x.x.x)"
    exit 1
fi
VPS_USER="${VPS_USER:-root}"
VPS_PASS="${VPS_PASS:-}"
REMOTE_DIR="${REMOTE_DIR:-/opt/legalia}"
LOCAL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "🚀 Iniciando despliegue automático a LegalIA VPS (${VPS_IP})..."

# 1. Check sshpass
if ! command -v sshpass &> /dev/null; then
    echo "❌ sshpass no está instalado. Instálalo con 'brew install sshpass'"
    exit 1
fi

export SSHPASS="$VPS_PASS"

# 2. Sync codebase to remote /opt/legalia (excluding git, node_modules, caches, local venv)
echo "📦 Sincronizando archivos del proyecto..."
sshpass -e rsync -avz --delete \
    -e "ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10" \
    --exclude '.git' \
    --exclude '.venv' \
    --exclude '__pycache__' \
    --exclude '.pytest_cache' \
    --exclude '.ruff_cache' \
    --exclude 'node_modules' \
    --exclude 'frontend/dist' \
    --exclude '.DS_Store' \
    --exclude 'backups' \
    --exclude 'data/postgres' \
    --exclude 'data/caddy' \
    --exclude '.env' \
    "${LOCAL_DIR}/" "${VPS_USER}@${VPS_IP}:${REMOTE_DIR}/"

# 3. Build & update containers on remote VPS
echo "🏗️  Reconstruyendo y reiniciando contenedores en el servidor..."
sshpass -e ssh -o StrictHostKeyChecking=no "${VPS_USER}@${VPS_IP}" << 'EOF'
cd /opt/legalia

# Rebuild and recreate cleanly without container name collisions
docker compose -f docker-compose.prod.yml build legalia-frontend legalia-api
docker rm -f legalia-frontend legalia-api 2>/dev/null || true
docker compose -f docker-compose.prod.yml up -d --remove-orphans legalia-frontend legalia-api

echo "⏳ Esperando confirmación de salud de los servicios..."
sleep 4
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
EOF

# 4. Verify remote endpoint
echo ""
echo "🔍 Verificando salud del endpoint público..."
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://${VPS_IP}/health" || echo "000")

if [ "$HTTP_STATUS" = "200" ]; then
    echo "✅ Despliegue completado con ÉXITO."
    echo "   - Endpoint Health: HTTP 200 OK"
    echo "   - URL: http://${VPS_IP}/"
else
    echo "⚠️  Atención: El endpoint devolvió status ${HTTP_STATUS}."
fi
