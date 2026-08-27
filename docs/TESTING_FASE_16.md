# Fase 16: LibreChat Integration - Testing Guide

## Estado de Implementación

✅ **Completado**:
- Chat service con retrieval + LLM integration
- Chat endpoint REST (`POST /api/v1/chat`)
- LibreChat configurado como custom endpoint
- Docker Compose con MongoDB + LibreChat
- Service token authentication
- External user mapping (LibreChat users → LegalIA users)

⚠️ **Limitaciones del MVP**:
- **No streaming**: respuestas completas (implementar en fase futura)
- **No citations display**: LibreChat muestra solo el texto (implementar Fase 14 primero)
- **No verification UI**: el backend verifica pero el frontend no lo muestra aún

## Arquitectura Implementada

```
Usuario
  ↓
LibreChat (localhost:3080)
  ↓ Authorization: Bearer <LEGALIA_SERVICE_TOKEN>
  ↓ X-LegalIA-User: <librechat-user-id>
  ↓
LegalIA API (legalia-api:8000)
  ↓
ChatService
  ↓
├─ RetrievalService (hybrid semantic + lexical)
├─ Reranker
└─ LLM (Anthropic)
  ↓
Response + Citations + Usage
```

## Testing Options

### Opción 1: Test Directo del Endpoint (sin LibreChat)

Más rápido para verificar que el backend funciona:

```bash
# Desde /tmp/legalIA

# 1. Levantar solo la API + PostgreSQL
docker compose up -d postgres legalia-api

# 2. Esperar a que esté healthy
docker compose logs -f legalia-api

# 3. Probar el endpoint
./scripts/test_chat_http.sh

# O manualmente:
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(grep LEGALIA_SERVICE_TOKEN .env | cut -d= -f2)" \
  -H "X-LegalIA-User: test-user-123" \
  -d '{
    "message": "¿Qué dice el artículo 13 de la Constitución?",
    "conversation_id": null
  }' | jq '.'
```

**Expected output**:
```json
{
  "response": "...",
  "citations": [...],
  "conversation_id": "uuid",
  "input_tokens": 150,
  "output_tokens": 300,
  "latency_ms": 2500,
  "retrieval_count": 5
}
```

### Opción 2: Test con LibreChat (experiencia de usuario completa)

```bash
# Desde /tmp/legalIA

# 1. Levantar todo el stack
docker compose up -d

# 2. Ver logs
docker compose logs -f

# 3. Esperar a que todos los servicios estén ready:
#    - postgres: healthy
#    - mongodb: healthy
#    - legalia-api: healthy
#    - librechat: started
#    - caddy: started

# 4. Abrir navegador
open http://localhost:3080

# 5. Registrarse en LibreChat
#    - Email: test@example.com
#    - Password: test123

# 6. Seleccionar modelo "LegalIA" en el dropdown

# 7. Hacer pregunta jurídica:
#    "¿Qué dice el artículo 13 de la Constitución sobre la libertad?"
```

## Verificación del Flujo

### 1. Service Token Authentication

Verifica que el service token funciona:

```bash
# Debería funcionar (con service token + X-LegalIA-User)
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Authorization: Bearer $(grep LEGALIA_SERVICE_TOKEN .env | cut -d= -f2)" \
  -H "X-LegalIA-User: test-user-123" \
  -d '{"message": "test"}' | jq '.response'

# Debería fallar (service token sin X-LegalIA-User)
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Authorization: Bearer $(grep LEGALIA_SERVICE_TOKEN .env | cut -d= -f2)" \
  -d '{"message": "test"}' 2>&1 | grep "X-LegalIA-User"
```

### 2. User Mapping

El primer request de un usuario crea su row en LegalIA:

```bash
# Primera llamada: crea el usuario
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Authorization: Bearer $(grep LEGALIA_SERVICE_TOKEN .env | cut -d= -f2)" \
  -H "X-LegalIA-User: nuevo-usuario-123" \
  -d '{"message": "test"}' | jq '.conversation_id'

# Segunda llamada: reutiliza el usuario
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Authorization: Bearer $(grep LEGALIA_SERVICE_TOKEN .env | cut -d= -f2)" \
  -H "X-LegalIA-User: nuevo-usuario-123" \
  -d '{"message": "test 2", "conversation_id": "<id-from-above>"}' | jq '.'
```

Verifica en la BD:

```bash
docker compose exec postgres psql -U legalia -d legalia -c \
  "SELECT id, email, external_issuer, external_subject FROM users WHERE external_issuer = 'librechat';"
```

### 3. Conversation Persistence

```bash
# Primera pregunta (crea conversación)
CONV_ID=$(curl -sS -X POST http://localhost:8000/api/v1/chat \
  -H "Authorization: Bearer $(grep LEGALIA_SERVICE_TOKEN .env | cut -d= -f2)" \
  -H "X-LegalIA-User: test-user" \
  -d '{"message": "¿Qué es el habeas corpus?"}' | jq -r '.conversation_id')

echo "Conversation ID: $CONV_ID"

# Segunda pregunta (misma conversación)
curl -sS -X POST http://localhost:8000/api/v1/chat \
  -H "Authorization: Bearer $(grep LEGALIA_SERVICE_TOKEN .env | cut -d= -f2)" \
  -H "X-LegalIA-User: test-user" \
  -d "{\"message\": \"¿Cuándo se usa?\", \"conversation_id\": \"$CONV_ID\"}" | jq '.response'
```

Verifica en la BD:

```bash
docker compose exec postgres psql -U legalia -d legalia -c \
  "SELECT id, title, created_at FROM conversations WHERE id = '$CONV_ID';"

docker compose exec postgres psql -U legalia -d legalia -c \
  "SELECT role, substring(content, 1, 50) FROM messages WHERE conversation_id = '$CONV_ID' ORDER BY created_at;"
```

### 4. Usage Logging

Cada request debe generar un usage log:

```bash
docker compose exec postgres psql -U legalia -d legalia -c \
  "SELECT model, input_tokens, output_tokens, latency_ms, created_at FROM usage_logs ORDER BY created_at DESC LIMIT 5;"
```

## Troubleshooting

### LibreChat no muestra LegalIA como opción

1. Verifica que `librechat.yaml` está montado:
   ```bash
   docker compose exec librechat cat /app/librechat.yaml | grep LegalIA
   ```

2. Verifica que `LEGALIA_SERVICE_TOKEN` está en el environment:
   ```bash
   docker compose exec librechat printenv | grep LEGALIA
   ```

3. Restart LibreChat:
   ```bash
   docker compose restart librechat
   ```

### 401 Unauthorized

Verifica que el service token coincide:

```bash
# En .env
grep LEGALIA_SERVICE_TOKEN .env

# En librechat.yaml (debe usar la variable)
grep apiKey librechat/librechat.yaml
```

### LegalIA API no responde

```bash
# Check health
curl http://localhost:8000/api/v1/health

# Check logs
docker compose logs legalia-api | tail -50

# Check database connection
docker compose exec legalia-api python -c "
from app.db.session import SessionLocal
db = SessionLocal()
print('DB connection OK')
db.close()
"
```

### MongoDB connection failed

```bash
# Check MongoDB
docker compose logs mongodb | tail -20

# Check if LibreChat can reach it
docker compose exec librechat nc -zv mongodb 27017
```

## Próximos Pasos

Una vez que el testing básico funciona:

**Fase 14**: Citation System
- Extraer citations del LLM response
- Vincular citations a chunks reales
- Persistir citation audit trail

**Fase 15**: Verification Service
- Detectar unsupported claims
- Verificar excerpts contra source chunks
- Generar confidence scores

**Fase 17**: Evaluation Framework
- Recall@K metrics
- Citation accuracy
- Benchmark jurídico colombiano

---

## Estado Actual: Testing Manual Ready

Puedes probar LegalIA como usuario **ahora mismo** con:

```bash
cd /tmp/legalIA
docker compose up -d
open http://localhost:3080
```

El backend está completo para las Fases 9-13 + 16. Falta implementar Fases 14-15 para tener el sistema de citations visible en la UI.
