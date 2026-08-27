# LegalIA

**AI jurídica especializada en el ordenamiento colombiano**

LegalIA es un asistente jurídico basado en RAG (Retrieval-Augmented Generation) que proporciona respuestas fundamentadas exclusivamente en documentos jurídicos colombianos verificables.

## Principio fundamental

**NO EVIDENCE → NO ANSWER**

Si el sistema no encuentra evidencia suficiente en el corpus disponible, lo indica explícitamente. Cada respuesta jurídica es rastreable hasta sus fuentes concretas.

## Características

- **Trazabilidad completa**: cada afirmación jurídica está vinculada a su fuente
- **Verificación de vigencia**: distingue normas vigentes de derogadas
- **Hybrid Retrieval**: búsqueda semántica + lexical
- **Reranking**: priorización inteligente de contexto relevante
- **Citations verificables**: referencias precisas a documentos, artículos y fragmentos
- **Arquitectura modular**: providers intercambiables (embeddings, LLM, reranker)

## Arquitectura

```
React Frontend (SPA)
        ↓
LegalIA API (FastAPI)
        ↓
    ┌───┴───┐
    ↓       ↓
PostgreSQL  Anthropic
pgvector    Claude
```

### Responsabilidades

- **React Frontend**: interfaz moderna, autenticación, conversaciones
- **LegalIA API**: lógica jurídica, RAG, retrieval, reranking, citations, verification
- **PostgreSQL/pgvector**: documentos, chunks, embeddings, metadata
- **Anthropic Claude**: generación y razonamiento

## Stack tecnológico

- **Backend**: Python 3.12+, FastAPI, SQLAlchemy 2, Alembic
- **Database**: PostgreSQL 16+, pgvector
- **LLM**: Anthropic API (Claude)
- **Embeddings**: Alibaba text-embedding-v4 / BGE-M3 (preparado)
- **Reranking**: Alibaba Qwen reranker
- **Frontend**: React 18, TypeScript, Vite
- **Infrastructure**: Docker, Docker Compose, Caddy, Nginx

## Requisitos

- Docker y Docker Compose
- 8 GB RAM mínimo
- 120 GB disco (NVMe recomendado)
- API key de Anthropic
- API key del proveedor de embeddings

## Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/tu-usuario/legalIA.git
cd legalIA
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
```

Editar `.env` con tus credenciales:

```env
# PostgreSQL
POSTGRES_DB=legalia
POSTGRES_USER=legalia
POSTGRES_PASSWORD=tu_password_seguro

# JWT
JWT_SECRET=tu_jwt_secret_largo_y_aleatorio

# Anthropic
ANTHROPIC_API_KEY=tu_api_key
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022

# Embeddings
EMBEDDING_PROVIDER=alibaba
EMBEDDING_API_KEY=tu_embedding_api_key
EMBEDDING_MODEL=text-embedding-v4

# Reranker
RERANKER_PROVIDER=alibaba
RERANKER_API_KEY=tu_reranker_api_key
```

### 3. Levantar los servicios

```bash
docker compose up -d
```

### 4. Ejecutar migraciones

```bash
docker compose exec legalia-api alembic upgrade head
```

### 5. Ingerir documentos de prueba

```bash
docker compose exec legalia-api python -m ingestion.main --file /path/to/documento.pdf
```

### 6. Verificar salud del sistema

```bash
curl http://localhost:8000/api/v1/health
```

## Uso

### Acceso a la aplicación

```
http://localhost
```

Registrarse con email y contraseña. La interfaz es completamente autocontenida y no requiere configuración adicional.

### API directa

```bash
# Registrar usuario
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "usuario@example.com", "password": "password123"}'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "usuario@example.com", "password": "password123"}'

# Chat
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"message": "¿Cuál es el artículo 90 de la Constitución?"}'
```

## Ingestion pipeline

```bash
# Ingerir un documento
python -m ingestion.main --file documento.pdf

# Ingerir múltiples documentos
python -m ingestion.main --directory ./corpus/constitucional/
```

## Evaluación

```bash
# Ejecutar evaluación completa
python -m evaluation.run_evaluation

# Comparar providers de embeddings
python -m evaluation.run_evaluation --compare-embeddings
```

## Tests

```bash
# Ejecutar todos los tests
docker compose exec legalia-api pytest

# Tests con cobertura
docker compose exec legalia-api pytest --cov=app --cov-report=html

# Test específico
docker compose exec legalia-api pytest tests/test_retrieval.py
```

## Backup

```bash
# Backup manual
./scripts/backup.sh

# Restaurar backup
docker compose exec postgres psql -U legalia -d legalia < backup_YYYYMMDD_HHMMSS.sql
```

## Estructura del proyecto

Ver [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) para documentación detallada de la arquitectura.

```
legalIA/
├── backend/          # API FastAPI
├── frontend/         # React + TypeScript SPA
├── ingestion/        # Pipeline de ingestion
├── evaluation/       # Métricas y benchmarks
├── infrastructure/   # Caddy, PostgreSQL
├── scripts/          # Scripts de utilidad
└── docs/             # Documentación técnica
```

## Documentación

- [Arquitectura](docs/ARCHITECTURE.md)
- [Base de datos](docs/DATABASE.md)
- [Sistema RAG](docs/RAG.md)
- [Evaluación](docs/EVALUATION.md)
- [Seguridad](docs/SECURITY.md)
- [Roadmap](docs/ROADMAP.md)

## Roadmap

### MVP (Actual)

- ✅ Arquitectura base
- ✅ PostgreSQL + pgvector
- ✅ Hybrid retrieval
- ✅ Reranking
- ✅ Citations verificables
- ✅ Frontend moderno React + TypeScript
- ✅ Evaluación básica

### Fase 2

- [ ] Corpus SUIN-Juriscol
- [ ] Scraping Corte Constitucional
- [ ] Scraping Consejo de Estado
- [ ] Benchmark derecho colombiano
- [ ] Fine-tuning embeddings
- [ ] BGE-M3 local

### Fase 3

- [ ] Búsqueda de procesos
- [ ] Análisis de contratos
- [ ] Integración SECOP
- [ ] Multi-tenancy
- [ ] Dashboard analytics

## Contribuir

Este proyecto está en fase MVP. Las contribuciones son bienvenidas una vez la arquitectura base esté consolidada.

## Licencia

[MIT License](LICENSE)

## Contacto

Para consultas técnicas o comerciales: contacto@legalia.co

---

**Advertencia legal**: LegalIA es una herramienta de asistencia. Las respuestas no constituyen asesoría jurídica formal. Siempre consulta con un abogado titulado para decisiones legales.
