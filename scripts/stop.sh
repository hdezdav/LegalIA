#!/bin/bash
set -e

echo "🛑 LegalIA - Detener servicios"
echo "==============================="
echo ""

if [ "$1" == "--clean" ]; then
    echo "⚠️  Esto eliminará TODOS los datos (base de datos, volumes, etc.)"
    read -p "¿Estás seguro? (y/N) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🗑️  Deteniendo y eliminando todo..."
        docker compose down -v --remove-orphans
        echo "✅ Servicios detenidos y datos eliminados"
    else
        echo "❌ Operación cancelada"
        exit 0
    fi
else
    echo "🛑 Deteniendo servicios (los datos se preservan)..."
    docker compose down
    echo "✅ Servicios detenidos"
    echo ""
    echo "💡 Para eliminar también los datos usa: ./scripts/stop.sh --clean"
fi

echo ""
echo "🔧 Para reiniciar: docker compose up -d"
echo ""
