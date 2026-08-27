# Estado de Fase 16: Integración LibreChat

**Fecha**: 2026-08-26  
**Estado**: Implementación completa, pendiente de corpus y primer test

---

## ✅ Completado

### 1. API OpenAI-compatible
- `POST /api/v1/chat/completions` — responde preguntas con contexto recuperado
- `GET /api/v1/models` — anuncia el modelo `legalia`
- Contrato wire 100% compatible con clientes OpenAI (LibreChat incluido)

### 2. ChatService
- Orquesta: retrieval → budget de contexto → generación → verificación stub
- Presupuesto de contexto: 90% de la ventana del modelo, menos historial, menos instrucciones, menos espacio reservado de salida
- Refusal contract: `NO EVIDENCE → NO ANSWER` cuando retrieval no encuentra suficiente evidencia
- Mock LLM con 8 comportamientos para testing (GROUNDED, REFUSE, FABRICATE_CITATION, etc.)

### 3. Autenticación dual
- **User token** (JWT): funciona como el resto de los endpoints
- **Service token** (LEGALIA_SERVICE_TOKEN): LibreChat lo presenta junto con la identidad del usuario final en:
  - Header `X-LegalIA-User`, o
  - Campo `user` del request body (estándar OpenAI)
- `ChatCaller.resolve_subject()` mapea identidades externas a usuarios LegalIA (crea uno on-demand si no existe)

### 4. Schemas OpenAI
- `ChatCompletionRequest` / `ChatCompletionResponse`
- `ChatCompletionMessage` / `ChatCompletionChoice`
- Campo extendido `legalia` con metadata:
  - `refused_for_lack_of_evidence`
  - `verification_status`
  - `retrieval_candidate_count`
  - `context_chunk_count`
  - `top_evidence_score`
  - `reranked`
  - `embedding_provider` / `reranker_provider`
  - `latency_ms`

### 5. Pipeline de ingestion completo
- **Loaders**: PDF, HTML, TXT
- **Cleaner**: normalización, líneas vacías, confusables
- **Metadata extractor**: identifica tipo de documento, external_id, fechas, emisor, corte, área legal
- **LegalTextSplitter**: respeta estructura jurídica (artículos, parágrafos, numerales)
- **EmbeddingGenerator**: genera vectores, valida dimensión/count
- **DocumentIndexer**: 
  - Change detection (content_hash + embedding_model)
  - Citation-aware: rechaza re-ingerir documentos citados (ON DELETE RESTRICT)
  - Chunks replaced, never mutated
- **CLI**: `python -m ingestion.main --file X` / `--directory Y` / `--dry-run`

### 6. Docker Compose actualizado
- Servicio `librechat` configurado
- MongoDB para persistencia de LibreChat
- Red interna Docker conectando todo
- Caddy ruteando `/` → LibreChat, `/api` → LegalIA

### 7. Variables de entorno
- `.env.example` actualizado con todas las variables LibreChat
- `.env` generado con secrets reales (gitignored)
- Service token generado: `LEGALIA_SERVICE_TOKEN`

### 8. Tests
- 135 tests pasando
- 29 skipped (auth tests requieren DB real)
- Imports verificados desde `~/Documents/GitHub/LegalIA`

---

## ❌ Pendiente para testing como usuario

### 1. Corpus de demostración
**Bloqueante**: sin documentos cargados, cada pregunta devuelve "no hay evidencia suficiente".

**Solución**:
```bash
# Crear archivos de texto en corpus/
# Ejemplo: corpus/constitucion_extracto.txt con artículos de la CP

# Ingerir
PYTHONPATH=backend:. .venv/bin/python -m ingestion.main \
  --directory corpus/ \
  --status VIGENTE \
  --source-name "Corpus de prueba"
```

### 2. Stack levantado
```bash
docker compose up -d
```

Verifica:
- PostgreSQL: `docker compose ps postgres`
- LegalIA API: `curl http://localhost:8000/api/v1/health`
- LibreChat: `curl http://localhost:3080`

### 3. Primer request de prueba

**Con user token** (requiere registro previo):
```bash
# Registrar usuario
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@legalia.co","password":"test1234","full_name":"Test User"}'

# Login (obtener token)
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@legalia.co","password":"test1234"}' | jq -r .access_token)

# Preguntar
curl -X POST http://localhost:8000/api/v1/chat/completions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "legalia",
    "messages": [{"role":"user","content":"¿Qué dice el artículo 1 de la Constitución?"}]
  }'
```

**Con service token** (lo que usará LibreChat):
```bash
curl -X POST http://localhost:8000/api/v1/chat/completions \
  -H "Authorization: Bearer $(grep LEGALIA_SERVICE_TOKEN .env | cut -d= -f2)" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "legalia",
    "user": "librechat_user_123",
    "messages": [{"role":"user","content":"¿Qué dice el artículo 1 de la Constitución?"}]
  }'
```

### 4. LibreChat UI

1. Abre `http://localhost:3080`
2. Crea una cuenta en LibreChat (su propia base de datos, no LegalIA)
3. En el selector de modelos, busca "LegalIA"
4. Escribe una pregunta jurídica

**Nota**: LibreChat enviará el service token automáticamente si está configurado en `librechat.yaml`.

---

## 🚧 Fases restantes (14, 15, 17-20)

### Fase 14: Citation system
- Extraer citations del texto generado
- Vincular a chunks reales
- Persistir en tabla `citations`
- Devolver metadata de fuentes en respuesta

### Fase 15: Verification service
- Verificar que cada claim está soportado por contexto
- Clasificar: SUPPORTED / PARTIALLY_SUPPORTED / UNSUPPORTED / INSUFFICIENT_EVIDENCE
- Identificar claims no soportados
- Preparar arquitectura para modelo verificador económico

### Fase 17: Evaluation
- Dataset con preguntas + expected chunks
- Métricas: Recall@k, MRR, NDCG
- Benchmark para comparar Alibaba vs BGE-M3 (cuando se consigan modelos)

### Fase 18: Tests end-to-end
- Test completo: documento → ingestion → retrieval → generación → citations
- Tests de integración LibreChat

### Fase 19: Deployment
- Scripts de backup
- Healthcheck automatizado
- Documentación de deployment en VPS

### Fase 20: Documentation
- ARCHITECTURE.md completo
- DATABASE.md con schema detallado
- RAG.md explicando retrieval híbrido
- EVALUATION.md con metodología
- SECURITY.md con consideraciones

---

## 📊 Métricas del proyecto

- **Archivos Python**: 56
- **Líneas de código**: ~8,500
- **Tests**: 135 pasando, 29 skipped
- **Coverage**: (pendiente de medición)
- **Tamaño del proyecto**: 186 archivos (sin venv)

---

## 🔑 Decisiones técnicas clave

1. **OpenAI wire format**: LibreChat custom endpoints requieren este contrato, no uno propietario.
2. **Service token + user identity**: permite que LibreChat autentique sin exponer tokens de usuario final.
3. **Citation-aware indexer**: ON DELETE RESTRICT previene destruir audit trail de respuestas ya entregadas.
4. **Mock providers por defecto**: desarrollo local sin API keys externas.
5. **Vigencia nunca inferida**: DESCONOCIDO por defecto, operador debe marcar VIGENTE explícitamente.
6. **Chunks inmutables**: re-ingerir reemplaza, nunca muta (citation excerpts deben ser estables).
7. **NO EVIDENCE → NO ANSWER**: refusal es un outcome correcto, no un failure.

---

## 🚨 Blockers conocidos

1. **Alibaba workspace sin embeddings/rerank**: el workspace `ws-2trsorjqmzwfn5ss` expone 92 modelos generativos pero 0 embeddings y 0 rerank. Mock providers activos para desarrollo.
2. **API key expuesta**: la key de Alibaba está en un transcript de chat y debe rotarse.
3. **Corpus vacío**: sin documentos, toda pregunta devuelve refusal.
4. **Citations no implementadas**: respuestas no tienen trazabilidad aún (Fase 14).
5. **Verification stub**: `verification_status` siempre es "pending" (Fase 15).

---

## 📝 Próximos pasos

1. **Crear corpus mínimo**: 3-5 documentos jurídicos en `corpus/`
2. **Ingerir corpus**: `python -m ingestion.main --directory corpus/`
3. **Levantar stack**: `docker compose up -d`
4. **Test manual**: request curl directo a `/api/v1/chat/completions`
5. **Test UI**: pregunta en LibreChat
6. **Si funciona**: continuar con Fase 14 (Citations)
7. **Si falla**: diagnosticar y corregir antes de avanzar

---

**Estado actual**: La infraestructura está lista. El blocker para testing es el corpus vacío.
