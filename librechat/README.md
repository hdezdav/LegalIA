# LibreChat Integration

Este directorio contiene la configuración de LibreChat como frontend de LegalIA.

## Arquitectura

```
Usuario
  ↓
LibreChat (puerto 3080)
  ↓
LegalIA API (puerto 8000)
  ↓
PostgreSQL + pgvector
  ↓
Anthropic API
```

## Configuración

LibreChat se comunica con LegalIA mediante un **custom endpoint** compatible con el protocolo OpenAI Chat Completions:

- **Endpoint Base**: `http://legalia-api:8000/api/v1`
- **Ruta de Completions**: `POST /api/v1/chat/completions`
- **Ruta de Modelos**: `GET /api/v1/models`
- **Autenticación**: Service token (`LEGALIA_SERVICE_TOKEN`)
- **Modelo**: `legalia`

## Flujo de Autenticación y Auditoría

LibreChat tiene su propio sistema de usuarios y almacenamiento MongoDB. Cuando un usuario de LibreChat realiza una consulta:

1. LibreChat envía el service token en el header `Authorization: Bearer <LEGALIA_SERVICE_TOKEN>`
2. LibreChat envía el identificador de usuario (`body.user` o header `X-LegalIA-User`)
3. LegalIA valida el service token en tiempo constante
4. LegalIA mapea o crea automáticamente el usuario externo (`external_issuer="librechat"`) en PostgreSQL
5. La consulta ejecuta el pipeline RAG híbrido (semántico + léxico + reranking + verificación)
6. La respuesta se retorna con metadatos de auditoría `legalia` y se registra en `usage_logs`

## Uso

Una vez levantado el stack (`docker compose up -d`):

1. Abre `http://localhost` (o tu dominio configurado en Caddy)
2. Regístrate o inicia sesión en LibreChat
3. En el selector de modelos, elige **LegalIA** (`legalia`)
4. Haz consultas jurídicas

## Desarrollo y Verificación Directa (sin LibreChat)

```bash
# Probar endpoint OpenAI-compatible directamente
curl -X POST http://localhost:8000/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $LEGALIA_SERVICE_TOKEN" \
  -H "X-LegalIA-User: test-user-123" \
  -d '{
    "model": "legalia",
    "messages": [
      {
        "role": "user",
        "content": "¿Qué dice el artículo 13 de la Constitución?"
      }
    ]
  }'
```

## Próximos Pasos

**Fase 14**: Citation system para extraer y verificar citas
**Fase 15**: Verification service para detectar unsupported claims
**Fase 17**: Evaluation framework para medir retrieval quality

---

**IMPORTANTE**: La configuración actual es para MVP local. Para producción necesitas:
- HTTPS mediante Caddy
- Service token fuerte
- Rate limiting configurado
- MongoDB con autenticación
- Backups de PostgreSQL y MongoDB
