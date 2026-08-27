#!/bin/bash
set -euo pipefail

# Legalia VPS Deployment Script for Debian 13
# Usage: ./deploy.sh [domain]

DOMAIN="${1:-legalia.example.com}"
REPO_URL="https://github.com/yourusername/LegalIA.git"
INSTALL_DIR="/opt/legalia"
DOCKER_COMPOSE_VERSION="2.24.5"

echo "🚀 Legalia Deployment Script"
echo "Domain: $DOMAIN"
echo ""

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "❌ This script must be run as root (use sudo)"
   exit 1
fi

# 1. Update system
echo "📦 Updating system packages..."
apt-get update
apt-get upgrade -y

# 2. Install dependencies
echo "📦 Installing dependencies..."
apt-get install -y \
    curl \
    git \
    ca-certificates \
    gnupg \
    lsb-release

# 3. Install Docker
if ! command -v docker &> /dev/null; then
    echo "🐳 Installing Docker..."

    # Add Docker's official GPG key
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
    chmod a+r /etc/apt/keyrings/docker.asc

    # Add Docker repository
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian \
      $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
      tee /etc/apt/sources.list.d/docker.list > /dev/null

    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    # Enable Docker
    systemctl enable docker
    systemctl start docker

    echo "✅ Docker installed"
else
    echo "✅ Docker already installed"
fi

# 4. Clone or update repository
if [ -d "$INSTALL_DIR" ]; then
    echo "📂 Updating repository..."
    cd "$INSTALL_DIR"
    git pull
else
    echo "📂 Cloning repository..."
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# 5. Create .env file
echo "⚙️  Creating .env file..."
cat > .env << EOF
# Database
DATABASE_URL=postgresql://legalia:$(openssl rand -hex 16)@postgres:5432/legalia
POSTGRES_USER=legalia
POSTGRES_PASSWORD=$(openssl rand -hex 16)
POSTGRES_DB=legalia

# JWT
SECRET_KEY=$(openssl rand -hex 32)
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# API Keys (you need to add these manually)
NODULE_PROVIDER_API_KEY=your_api_key_here

# Environment
ENVIRONMENT=production

# Domain
DOMAIN=$DOMAIN
EOF

echo "✅ .env created (you need to add API keys manually)"

# 6. Create necessary directories
mkdir -p data/postgres
mkdir -p data/caddy

# 7. Build and start services
echo "🏗️  Building services..."
docker compose build

echo "🚀 Starting services..."
docker compose up -d

# 8. Wait for services
echo "⏳ Waiting for services to be ready..."
sleep 10

# 9. Run database migrations
echo "📊 Running database migrations..."
docker compose exec -T legalia-api alembic upgrade head

# 10. Check service status
echo ""
echo "📊 Service Status:"
docker compose ps

# 11. Instructions
echo ""
echo "✅ Deployment complete!"
echo ""
echo "📝 Next steps:"
echo "1. Edit /opt/legalia/.env and add your API keys"
echo "2. Restart services: cd /opt/legalia && docker compose restart"
echo "3. Create admin user: docker compose exec legalia-api python -m app.scripts.create_admin"
echo "4. Configure DNS: Point $DOMAIN to this server's IP"
echo "5. SSL will be automatically provisioned by Caddy"
echo ""
echo "🔗 Your site will be available at: https://$DOMAIN"
echo "📊 Health check: https://$DOMAIN/api/v1/health"
echo ""
