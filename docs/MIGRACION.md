# Migración del Proyecto desde /tmp/legalIA

## ⚠️ IMPORTANTE: Mover el proyecto AHORA

El proyecto está actualmente en `/tmp/legalIA`, que puede perderse al reiniciar el sistema.

**Debes moverlo a una ubicación permanente antes de continuar.**

## Pasos de Migración

### Opción 1: Mover a ~/Documents/GitHub/LegalIA (Recomendado)

```bash
# 1. Crear el directorio destino si no existe
mkdir -p ~/Documents/GitHub

# 2. Mover el proyecto completo
mv /tmp/legalIA ~/Documents/GitHub/LegalIA

# 3. Cambiar al nuevo directorio
cd ~/Documents/GitHub/LegalIA

# 4. Verificar que todo está en su lugar
ls -la
docker compose config > /dev/null && echo "✓ docker-compose.yml válido"
```

### Opción 2: Copiar (conserva el original en /tmp)

```bash
# 1. Copiar todo
cp -R /tmp/legalIA ~/Documents/GitHub/LegalIA

# 2. Cambiar al nuevo directorio
cd ~/Documents/GitHub/LegalIA

# 3. Verificar
ls -la
```

## Después de Mover

### 1. Inicializar Git (Recomendado)

```bash
cd ~/Documents/GitHub/LegalIA

# Inicializar repo
git init

# Verificar que .gitignore está presente
cat .gitignore

# Primer commit
git add .
git commit -m "Initial commit: LegalIA MVP - Fases 1-13 + 16 completadas

- PostgreSQL + pgvector
- FastAPI backend con auth, health, chat
- Hybrid retrieval (semantic + lexical)
- Embedding providers (Alibaba, BGE-M3)
- Reranker providers (Alibaba, NoOp)
- LLM providers (Anthropic, Mock)
- LibreChat integration
- Docker Compose stack completo
- 135 tests pasando
"

# Crear branch para desarrollo
git checkout -b develop
```

### 2. Verificar Variables de Entorno

El `.env` generado tiene valores reales que **NO DEBES COMMITEAR**:

```bash
# Verificar que .env está en .gitignore
grep "^\.env$" .gitignore

# Ver qué archivos Git va a ignorar
git status --ignored | grep .env

# Debería mostrar:
# .env (ignored)
# .env.local (si existe, ignored)
```

### 3. Primera Prueba después de Mover

```bash
cd ~/Documents/GitHub/LegalIA

# Verificar que docker-compose funciona
docker compose config

# Levantar solo la API + PostgreSQL
docker compose up -d postgres legalia-api

# Esperar a que esté healthy
docker compose ps

# Probar el endpoint
./scripts/test_chat_http.sh
```

## Qué está Incluido

### Código Fuente (~/Documents/GitHub/LegalIA/)
```
backend/          → API FastAPI + servicios + providers
ingestion/        → Pipeline de documentos
evaluation/       → Framework de evaluación
librechat/        → Configuración de LibreChat
infrastructure/   → Caddy, PostgreSQL init
scripts/          → Utilities, backups, tests
docs/             → Documentación técnica
```

### Configuración
```
docker-compose.yml     → Stack completo
.env                   → Variables con valores REALES (no commitear)
.env.example           → Template para producción
.gitignore             → Git ignore rules
Makefile               → Comandos comunes
```

### Estado del Código
- **135 tests pasando** (backend/tests/)
- **Linters OK** (black, isort, mypy configurados)
- **Docker builds OK** (backend/Dockerfile probado)
- **Health endpoint OK** (verificado en fase 4)

## Qué NO está Incluido (Fases Pendientes)

❌ **Fase 14**: Citation system (extracción + verificación)
❌ **Fase 15**: Verification service (confidence scoring)
❌ **Fase 17**: Evaluation (benchmark colombiano)
❌ **Fase 18**: Tests end-to-end completos
❌ **Fase 19**: Deployment en VPS
❌ **Fase 20**: Documentación final

## Siguiente Paso Sugerido

Una vez movido el proyecto:

**1. Probar que funciona desde la nueva ubicación**:
```bash
cd ~/Documents/GitHub/LegalIA
docker compose up -d
open http://localhost:3080
```

**2. Decidir qué implementar siguiente**:
- **Fase 14 (Citations)**: Para que las respuestas muestren fuentes verificables
- **Fase 15 (Verification)**: Para detectar claims sin evidencia
- **Ingestar documentos reales**: Poblar el corpus con normativa colombiana

## Seguridad: API Keys en .env

Tu `.env` actual contiene:

✅ **Generados automáticamente** (seguros):
- `LIBRECHAT_CREDS_KEY`
- `LIBRECHAT_CREDS_IV`
- `LIBRECHAT_JWT_SECRET`
- `LIBRECHAT_JWT_REFRESH_SECRET`
- `LEGALIA_SERVICE_TOKEN`

⚠️ **Pendientes de actualizar** (están como placeholders):
- `POSTGRES_PASSWORD` → cambiar antes de producción
- `JWT_SECRET` → cambiar antes de producción
- `ANTHROPIC_API_KEY` → añadir tu key real para usar Claude
- `ALIBABA_API_KEY` → ya tienes una (workspace ws-2trsorjqmzwfn5ss)

⚠️ **Nota sobre Alibaba**: Tu workspace actual **NO tiene modelos de embeddings ni reranking**. El provider está implementado correctamente pero necesitas un workspace diferente o usar `EMBEDDING_PROVIDER=mock` y `RERANKER_PROVIDER=mock` para testing.

## Rotación de la API Key de Alibaba

**CRÍTICO**: La API key de Alibaba que compartiste quedó expuesta en esta conversación:

```
apiKey: sk-ws-H.IMMYHXD.cuTA.MEMCHzQ2LmEx9XTjsh4tmUT4ktPNvyq7iDSvk8lW7YPeCq8CIEjkSWUqcK-KYpY8h8m7zAqXhDbf8hRxEoZHn0h4UC6P
```

**Después de mover el proyecto, rótala**:
1. Ve a https://bailian.console.aliyun.com/
2. Workspace → Default Workspace → API Keys
3. Revoke la key expuesta
4. Genera una nueva
5. Actualiza `.env` con la nueva key

---

## Resumen

```bash
# Mover proyecto
mv /tmp/legalIA ~/Documents/GitHub/LegalIA
cd ~/Documents/GitHub/LegalIA

# Inicializar Git
git init
git add .
git commit -m "Initial commit: LegalIA MVP"

# Verificar
docker compose up -d postgres legalia-api
./scripts/test_chat_http.sh

# Probar UI
docker compose up -d
open http://localhost:3080
```

**El proyecto está listo para testing como usuario. Las Fases 9-13 + 16 están completadas.**
