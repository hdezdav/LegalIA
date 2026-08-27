#!/bin/bash
set -e

echo "🚀 LegalIA - Inicio rápido"
echo "=========================="
echo ""

# Verificar Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker no está instalado. Instala Docker Desktop primero."
    exit 1
fi

if ! command -v docker compose &> /dev/null; then
    echo "❌ Docker Compose no está disponible."
    exit 1
fi

# Verificar archivo .env
if [ ! -f .env ]; then
    echo "⚠️  Archivo .env no encontrado. Copiando desde .env.example..."
    cp .env.example .env
    echo ""
    echo "📝 Por favor edita .env y configura:"
    echo "   - POSTGRES_PASSWORD"
    echo "   - JWT_SECRET"
    echo "   - ANTHROPIC_API_KEY"
    echo "   - ALIBABA_API_KEY"
    echo "   - ALIBABA_RERANKER_API_KEY"
    echo ""
    read -p "¿Ya configuraste las variables? (y/N) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Configura .env y vuelve a ejecutar este script."
        exit 1
    fi
fi

echo "🐳 Construyendo imágenes Docker..."
docker compose build

echo ""
echo "🚀 Iniciando servicios..."
docker compose up -d

echo ""
echo "⏳ Esperando a que PostgreSQL esté listo..."
sleep 10

echo ""
echo "📊 Ejecutando migraciones de base de datos..."
docker compose exec legalia-api alembic upgrade head

echo ""
echo "✅ LegalIA está corriendo!"
echo ""
echo "📍 Accesos:"
echo "   Frontend:  http://localhost"
echo "   API:       http://localhost/api/v1"
echo "   Health:    http://localhost/api/v1/health"
echo ""
echo "🔧 Comandos útiles:"
echo "   Ver logs:           docker compose logs -f"
echo "   Detener servicios:  docker compose down"
echo "   Reiniciar:          docker compose restart"
echo ""
echo "📚 Próximos pasos:"
echo "   1. Abre http://localhost en tu navegador"
echo "   2. Regístrate con un email y contraseña"
echo "   3. Ingesta documentos con: docker compose exec legalia-api python -m ingestion.main --file /path/to/doc.pdf"
echo ""
