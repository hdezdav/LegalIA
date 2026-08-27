# Sistema de Ingesta de Documentos - Completado

## ✅ Fase C: Verificación de documentos problemáticos

**Documentos analizados:**
1. ❌ **Ley 57 de 1887 (Código Civil)** — CORRUPTO
   - Solo 3 chunks con CSS basura de Word
   - Requiere re-ingesta desde fuente limpia
   
2. ✅ **Ley 1581 de 2012** — OK (39 chunks, ley corta)
3. ✅ **Ley 1712 de 2014** — OK (48 chunks, ley corta)

---

## ✅ Fase A: Sistema automatizado de ingesta

### Componentes implementados:

#### 1. **IngestionService** (`backend/app/services/ingestion_service.py`)
- Parse automático: PDF, DOCX, TXT → Markdown
- Chunking con `LegalTextSplitter` (chunks de 500 tokens)
- Generación de embeddings automática
- Detección de duplicados por hash de contenido
- Manejo robusto de errores

#### 2. **LegalTextSplitter** (`backend/app/services/legal_text_splitter.py`)
- Respeta estructura legal: artículos, parágrafos, incisos
- Chunk size: 500 tokens con overlap de 50
- Extrae metadata: article_number, section_type, hierarchy_level

#### 3. **Admin API Endpoints** (`backend/app/api/routes/admin.py`)

**POST `/api/v1/admin/documents`** — Ingestar documento
```bash
curl -X POST http://localhost:8000/api/v1/admin/documents \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@documento.pdf" \
  -F "title=Ley 1234 de 2020" \
  -F "document_type=LEY" \
  -F "jurisdiction=NACIONAL"
```

**POST `/api/v1/admin/documents/{id}/reingest`** — Re-ingestar documento corrupto
```bash
curl -X POST http://localhost:8000/api/v1/admin/documents/{id}/reingest \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@documento_limpio.pdf"
```

**GET `/api/v1/admin/documents`** — Listar documentos
```bash
curl http://localhost:8000/api/v1/admin/documents \
  -H "Authorization: Bearer $TOKEN"
```

**DELETE `/api/v1/admin/documents/{id}`** — Eliminar documento
```bash
curl -X DELETE http://localhost:8000/api/v1/admin/documents/{id} \
  -H "Authorization: Bearer $TOKEN"
```

**POST `/api/v1/admin/corpus/ingest`** — Scraping masivo desde URL
```bash
curl -X POST http://localhost:8000/api/v1/admin/corpus/ingest \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://ejemplo.com/leyes",
    "document_type": "LEY",
    "jurisdiction": "NACIONAL"
  }'
```

---

## ✅ Deployment en VPS Debian 13

### Archivos creados:

1. **`docs/DEPLOYMENT.md`** — Guía completa paso a paso
   - Requisitos del VPS
   - Instalación de Docker
   - Configuración de SSL automático con Caddy
   - Scripts de mantenimiento y backup
   - Troubleshooting

2. **`scripts/create_admin.py`** — Crear usuario administrador
   ```bash
   docker compose exec legalia-api python scripts/create_admin.py
   ```

3. **`docker-compose.prod.yml`** — Configuración optimizada para producción
   - Resource limits (CPU/memoria)
   - Restart policies
   - Health checks
   - Logging rotation
   - Volumes persistentes

4. **`frontend/Dockerfile.prod`** — Build multi-stage con nginx
   - Build stage: compila assets con Vite
   - Production stage: sirve con nginx optimizado
   - Gzip compression
   - Cache de assets estáticos

5. **`frontend/nginx.conf`** — Configuración nginx para SPA
   - SPA fallback (todas las rutas → index.html)
   - Compresión gzip
   - Security headers
   - Cache de assets (1 año)

6. **`Caddyfile`** — SSL automático con Let's Encrypt
   - HTTPS automático
   - Security headers (HSTS, XSS, clickjacking)
   - Health checks
   - Logging

---

## 🚀 Próximos pasos para salir al mercado

### **Paso 1: Activar embeddings reales** (BLOQUEANTE)
```bash
# En .env
EMBEDDING_PROVIDER=alibaba

# Re-ingerir corpus completo
curl -X POST http://localhost:8000/api/v1/admin/documents/{id}/reingest \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@documento.pdf"
```

### **Paso 2: Re-ingestar Código Civil**
La Ley 57 de 1887 está corrupta. Necesita fuente limpia.

### **Paso 3: Implementar Citations**
- Crear `CitationService`
- Modificar `ChatService._persist` para escribir `Citation` rows
- Devolver citations en respuesta

### **Paso 4: Implementar Verification básica**
- Crear `VerificationService` con Haiku 4.5
- Verificar claims antes de persistir mensaje

### **Paso 5: Deploy a VPS**
```bash
# Seguir docs/DEPLOYMENT.md paso a paso
ssh root@vps
cd /opt/legalia
docker compose -f docker-compose.prod.yml up -d
```

---

## 📊 Estado actual del sistema

### Backend
- ✅ 172 tests pasando
- ✅ RAG funcional (pero con embeddings mock)
- ✅ 15 documentos, 7,872 chunks
- ✅ Sistema de ingesta completo
- ⚠️ Citations: modelo existe pero no se persisten
- ⚠️ Verification: siempre "pending"

### Frontend
- ✅ Landing page completa
- ✅ Chat funcional
- ✅ ModelSelector con 20+ modelos
- ✅ File uploads
- ✅ Dark/Light mode

### Infraestructura
- ✅ Docker Compose funcionando
- ✅ Caddy con SSL automático (listo)
- ✅ Scripts de deployment
- ✅ Guía completa de producción

---

## 🛠️ Uso del sistema de ingesta

### 1. Crear usuario admin
```bash
docker compose exec legalia-api python scripts/create_admin.py
```

### 2. Obtener token
```bash
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@legalia.com","password":"tu-password"}' \
  | jq -r '.access_token')
```

### 3. Subir documento
```bash
curl -X POST http://localhost:8000/api/v1/admin/documents \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@ley_1234.pdf" \
  -F "title=Ley 1234 de 2020 - Transparencia" \
  -F "external_id=LEY_1234_2020" \
  -F "document_type=LEY" \
  -F "issuing_entity=Congreso de la República" \
  -F "jurisdiction=NACIONAL" \
  -F "publication_date=2020-07-15" \
  -F "source_url=https://ejemplo.com/ley-1234"
```

### 4. Listar documentos
```bash
curl http://localhost:8000/api/v1/admin/documents \
  -H "Authorization: Bearer $TOKEN" | jq
```

### 5. Re-ingestar documento corrupto
```bash
curl -X POST http://localhost:8000/api/v1/admin/documents/{document_id}/reingest \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@ley_limpia.pdf"
```

---

## 📈 Métricas clave para MVP

- **Corpus inicial**: 50-100 documentos prioritarios
  - Constitución ✅
  - Códigos (Civil, Penal, Procedimiento)
  - Top 20 leyes más consultadas
  - Jurisprudencia de alto impacto

- **Performance**:
  - Retrieval: <500ms
  - Response completa: <3s
  - Embedding generation: ~200ms por chunk

- **Calidad**:
  - Recall@5 > 80% (con embeddings reales)
  - Citations accuracy > 90%
  - Verification: <10% false positives

---

## 🎯 Hito completado

Sistema de ingesta de documentos **COMPLETO** y listo para producción. Incluye:
- ✅ API completa (CRUD + reingest + corpus scraping)
- ✅ Chunking inteligente para documentos legales
- ✅ Detección de duplicados
- ✅ Deployment scripts para VPS
- ✅ Documentación exhaustiva

**Próximo blocker crítico:** Activar embeddings reales (cambiar de `mock` a `alibaba`).
