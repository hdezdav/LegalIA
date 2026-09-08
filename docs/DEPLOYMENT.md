# Deployment Guide - Legalia en VPS Debian 13

## Requisitos del VPS

- **OS**: Debian 13 (bookworm o testing)
- **RAM**: mínimo 4GB (recomendado 8GB)
- **Storage**: mínimo 50GB SSD
- **CPU**: 2+ cores
- **Network**: IP pública estática
- **DNS**: dominio apuntando al VPS (A record)

---

## 1. Preparación inicial del servidor

```bash
# Conectarse al VPS
ssh root@your-vps-ip

# Actualizar sistema
apt update && apt upgrade -y

# Instalar dependencias base
apt install -y curl git ufw fail2ban

# Configurar firewall
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow http
ufw allow https
ufw enable

# Configurar fail2ban (protección contra brute-force)
systemctl enable fail2ban
systemctl start fail2ban
```

---

## 2. Instalar Docker y Docker Compose

```bash
# Instalar Docker
curl -fsSL https://get.docker.com | sh

# Agregar usuario al grupo docker (opcional, para no usar sudo)
usermod -aG docker $USER

# Instalar Docker Compose v2
apt install -y docker-compose-plugin

# Verificar instalación
docker --version
docker compose version
```

---

## 3. Clonar el repositorio

```bash
# Crear directorio para la aplicación
mkdir -p /opt/legalia
cd /opt/legalia

# Clonar repo (ajustar URL según corresponda)
git clone https://github.com/hdezdav/LegalIA.git .

# O si ya lo tienes localmente, usar rsync:
# rsync -avz --exclude 'node_modules' --exclude '.venv' /ruta/local/ root@vps:/opt/legalia/
```

---

## 4. Configurar variables de entorno

```bash
cd /opt/legalia

# Copiar ejemplo de .env
cp .env.example .env

# Editar .env con tus valores REALES
nano .env
```

**Variables críticas que DEBES cambiar:**

```bash
# PostgreSQL
POSTGRES_PASSWORD=cambiar-por-password-seguro-aleatorio

# JWT Secret
JWT_SECRET_KEY=cambiar-por-secret-largo-aleatorio-64-chars

# Embeddings (mantener alibaba si ya tienes keys válidas)
EMBEDDING_PROVIDER=alibaba
ALIBABA_API_KEY=tu-key-real

# Dominio (para SSL automático con Caddy)
DOMAIN=legalia.tudominio.com
```

**Generar secrets seguros:**
```bash
# Para POSTGRES_PASSWORD
openssl rand -base64 32

# Para JWT_SECRET_KEY
openssl rand -base64 48
```

---

## 5. Configurar Caddy para SSL automático

Editar `Caddyfile`:

```bash
nano Caddyfile
```

Cambiar `localhost` por tu dominio real:

```
legalia.tudominio.com {
    reverse_proxy legalia-frontend:5173
    
    handle /api/* {
        reverse_proxy legalia-api:8000
    }
}
```

---

## 6. Desplegar con Docker Compose

```bash
# Construir imágenes
docker compose -f docker-compose.prod.yml build

# Levantar servicios
docker compose -f docker-compose.prod.yml up -d

# Ver logs
docker compose -f docker-compose.prod.yml logs -f

# Verificar que todo esté corriendo
docker compose -f docker-compose.prod.yml ps
```

**Esperado:**
```
NAME               STATUS
legalia-api        Up (healthy)
legalia-caddy      Up
legalia-frontend   Up
legalia-postgres   Up (healthy)
```

---

## 7. Inicializar base de datos

```bash
# Ejecutar migraciones
docker compose -f docker-compose.prod.yml exec legalia-api \
  alembic upgrade head

# Crear usuario admin
docker compose -f docker-compose.prod.yml exec legalia-api \
  python scripts/create_admin.py

# Seguir las instrucciones en pantalla para email/password
```

---

## 8. Verificar deployment

```bash
# Healthcheck del backend
curl https://legalia.tudominio.com/api/v1/health

# Esperado: {"status":"ok"}

# Verificar SSL
curl -I https://legalia.tudominio.com
# Debe responder 200 OK con certificado válido
```

Abrir navegador: `https://legalia.tudominio.com`

---

## 9. Ingestar corpus inicial

```bash
# Obtener token de admin
TOKEN=$(curl -X POST https://legalia.tudominio.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@legalia.com","password":"tu-password"}' \
  | jq -r '.access_token')

# Subir documento
curl -X POST https://legalia.tudominio.com/api/v1/admin/documents \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@constitucion.pdf" \
  -F "title=Constitución Política de Colombia 1991" \
  -F "document_type=CONSTITUCION" \
  -F "jurisdiction=NACIONAL"

# Ver documentos ingresados
curl https://legalia.tudominio.com/api/v1/admin/documents \
  -H "Authorization: Bearer $TOKEN" | jq
```

---

## 10. Mantenimiento

### Backups automáticos

```bash
# Configurar cron para backup diario
crontab -e

# Agregar línea:
0 3 * * * /opt/legalia/scripts/backup.sh
```

### Ver logs

```bash
cd /opt/legalia
docker compose -f docker-compose.prod.yml logs -f legalia-api
docker compose -f docker-compose.prod.yml logs -f legalia-frontend
```

### Actualizar aplicación

```bash
cd /opt/legalia

# Pull nuevos cambios
git pull origin main

# Rebuild y redeploy
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d

# Ejecutar migraciones si hay cambios en DB
docker compose -f docker-compose.prod.yml exec legalia-api alembic upgrade head
```

### Restart servicios

```bash
docker compose -f docker-compose.prod.yml restart legalia-api
docker compose -f docker-compose.prod.yml restart legalia-frontend
```

---

## 11. Monitoreo

### Healthchecks

```bash
# Ver estado de contenedores
docker compose -f docker-compose.prod.yml ps

# Ver uso de recursos
docker stats
```

### Logs de Caddy (SSL)

```bash
docker compose -f docker-compose.prod.yml logs caddy | grep certificate
```

---

## Troubleshooting

### Backend crashea

```bash
docker compose -f docker-compose.prod.yml logs legalia-api | tail -50
```

**Problemas comunes:**
- `POSTGRES_PASSWORD` incorrecto → verificar `.env`
- `EMBEDDING_PROVIDER` sin keys → cambiar a `mock` temporalmente
- Puerto 8000 ocupado → cambiar en `docker-compose.prod.yml`

### SSL no funciona

```bash
# Verificar que DNS apunte al VPS
dig legalia.tudominio.com +short
# Debe devolver la IP del VPS

# Verificar logs de Caddy
docker compose -f docker-compose.prod.yml logs caddy

# Verificar puertos 80/443 abiertos
ufw status
```

### Base de datos corrupta

```bash
# Restaurar desde backup
docker compose -f docker-compose.prod.yml down
docker volume rm legalia_postgres_data
docker compose -f docker-compose.prod.yml up -d
# Luego restaurar backup con psql
```

---

## Seguridad adicional

### Configurar rate limiting en Caddy

Editar `Caddyfile`:

```
legalia.tudominio.com {
    rate_limit {
        zone dynamic {
            key {remote_host}
            events 100
            window 1m
        }
    }
    
    reverse_proxy legalia-frontend:5173
    handle /api/* {
        reverse_proxy legalia-api:8000
    }
}
```

### Habilitar HTTPS-only

En `.env`:

```bash
SECURE_COOKIES=true
CORS_ORIGINS=https://legalia.tudominio.com
```

---

## Costos estimados

- **VPS 4GB RAM**: ~$12-20/mes (Hetzner, DigitalOcean, Vultr)
- **Dominio**: ~$10-15/año
- **SSL**: Gratis (Let's Encrypt vía Caddy)
- **Embeddings API**: según uso (Alibaba ~$0.0001/1k tokens)

**Total**: ~$15-25/mes para MVP
