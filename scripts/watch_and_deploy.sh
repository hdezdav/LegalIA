#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# LegalIA - Watch and Auto-Deploy Script
# Watches frontend/ and backend/ for changes and runs deploy_remote.sh automatically
# ==============================================================================

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPLOY_SCRIPT="${PROJECT_DIR}/scripts/deploy_remote.sh"

echo "👀 Iniciando observador de cambios para auto-despliegue en LegalIA..."
echo "📁 Directorio base: ${PROJECT_DIR}"
echo "⚡ Cualquier cambio guardado en frontend/ o backend/ se desplegará automáticamente al VPS."
echo "Presiona Ctrl+C para detener."
echo ""

# Check fswatch or fallback loop
if command -v fswatch &> /dev/null; then
    fswatch -o -e "\.git" -e "\.venv" -e "__pycache__" -e "node_modules" -e "dist" -e "\.DS_Store" \
        "${PROJECT_DIR}/frontend/src" "${PROJECT_DIR}/backend/app" | while read -r _; do
        echo "🔄 Cambio detectado. Desplegando..."
        "$DEPLOY_SCRIPT" || echo "⚠️ Falló el despliegue automático, reintentando en el próximo cambio."
    done
else
    # Portable fallback loop using find mtime
    LAST_CHECK=$(date +%s)
    while true; do
        sleep 3
        CHANGED=$(find "${PROJECT_DIR}/frontend/src" "${PROJECT_DIR}/backend/app" -type f -newermt "@$LAST_CHECK" 2>/dev/null | head -n 1 || true)
        if [ -n "$CHANGED" ]; then
            echo "🔄 Cambio detectado en $CHANGED. Desplegando..."
            LAST_CHECK=$(date +%s)
            "$DEPLOY_SCRIPT" || echo "⚠️ Falló el despliegue automático."
        fi
    done
fi
