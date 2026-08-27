# Migración: LibreChat → Frontend React Nativo

## Fecha: 2026-08-26

## Motivación

LibreChat era una dependencia externa pesada (Node.js + MongoDB) que agregaba:
- ~2GB de images Docker adicionales
- MongoDB como dependencia innecesaria
- Complejidad de configuración (librechat.yaml, secrets múltiples)
- Marca y UI difícil de personalizar completamente

## Cambios realizados

### Eliminado
- ❌ Servicio `librechat` del docker-compose.yml
- ❌ Servicio `mongodb` (ya no es necesario)
- ❌ Network `librechat_data`
- ❌ Volumes: `mongodb_data`, `librechat_images`, `librechat_uploads`
- ❌ Directorio `librechat/` con configuración
- ❌ Variables de entorno LibreChat del `.env.example`

### Agregado
- ✅ `frontend/` - SPA moderno con React 18 + TypeScript + Vite
- ✅ Servicio `legalia-frontend` en docker-compose.yml
- ✅ Nginx para servir el frontend en producción
- ✅ Autenticación integrada (login/registro)
- ✅ Chat UI completamente personalizada
- ✅ Tema oscuro profesional con branding LegalIA
- ✅ Scripts de inicio rápido (`scripts/start.sh`, `scripts/stop.sh`)

### Modificado
- 🔄 `docker-compose.yml` - simplificado de 6 servicios a 4
- 🔄 `infrastructure/caddy/Caddyfile` - actualizado para servir frontend en `/`
- 🔄 `.env.example` - removidas variables LibreChat
- 🔄 `README.md` - actualizada arquitectura y stack

## Stack del nuevo frontend

```
React 18           - Framework UI
TypeScript         - Type safety
Vite              - Build tool ultra-rápido
React Markdown    - Rendering de respuestas
Nginx Alpine      - Servidor estático en producción
```

**Total:** ~150KB de dependencias runtime (vs ~2GB de LibreChat + MongoDB)

## Características del nuevo frontend

1. **Autenticación nativa**
   - Login y registro integrados
   - JWT con refresh automático
   - Sin dependencias externas

2. **Chat moderno**
   - Markdown rendering completo
   - Typing indicators
   - Metadata de verificación visible
   - Welcome screen con ejemplos
   - Scroll automático

3. **Diseño profesional**
   - Tema oscuro slate + amber accent
   - Responsive mobile-first
   - Iconografía consistente
   - Sin marca de terceros

4. **Performance**
   - Build optimizado < 500KB
   - Hot reload en desarrollo
   - Code splitting automático
   - Assets con cache 1 año

## Migración para usuarios existentes

### Si usabas LibreChat:

1. **Tus conversaciones NO se migran** (estaban en MongoDB de LibreChat)
2. **Los usuarios NO se migran** (diferentes sistemas de auth)
3. **Los documentos indexados SÍ se preservan** (están en PostgreSQL)

### Pasos para migrar:

```bash
# 1. Detener stack anterior
docker compose down

# 2. Limpiar servicios viejos (opcional - elimina conversaciones)
docker compose down -v

# 3. Actualizar .env (remover variables LIBRECHAT_*)
# Usa el nuevo .env.example como referencia

# 4. Reconstruir
docker compose build

# 5. Iniciar nuevo stack
docker compose up -d

# 6. Ejecutar migraciones
docker compose exec legalia-api alembic upgrade head
```

### Usuarios nuevos:

Simplemente ejecuta:
```bash
./scripts/start.sh
```

## API sin cambios

El backend LegalIA API **NO cambió**. Los endpoints son idénticos:

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `GET /api/v1/auth/me`
- `POST /api/v1/chat/completions`
- `GET /api/v1/models`

## Ventajas

1. **Simplicidad**: 4 servicios en vez de 6
2. **Menos dependencias**: sin Node.js ni MongoDB
3. **Más rápido**: build < 30s, arranque < 10s
4. **100% personalizable**: código fuente completo bajo control
5. **Más ligero**: ~500KB bundle vs ~2GB de imágenes
6. **Mejor UX**: diseñado específicamente para LegalIA

## Testing

```bash
# Desarrollo local del frontend
cd frontend
npm install
npm run dev
# Abre http://localhost:3000

# Build de producción
npm run build
```

## Rollback (si es necesario)

Si necesitas volver a LibreChat temporalmente:

```bash
git checkout <commit-anterior-a-esta-migracion>
docker compose up -d
```

## Notas técnicas

- El frontend usa el mismo endpoint `/api/v1/chat/completions` (OpenAI-compatible)
- CORS configurado para `http://localhost` en desarrollo
- Nginx hace proxy de `/api/*` al backend internamente
- JWT tokens en localStorage con refresh automático
- Sin streaming aún (respuestas completas)

## Próximos pasos

- [ ] Streaming de respuestas (SSE)
- [ ] Conversaciones persistentes en backend
- [ ] Export de conversaciones
- [ ] Feedback inline en mensajes
- [ ] Shortcuts de teclado
- [ ] Dark/Light theme toggle
