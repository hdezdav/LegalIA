.PHONY: help build up down restart logs ps clean test lint format migrate backup restore

help:
	@echo "LegalIA - Makefile commands"
	@echo ""
	@echo "Development:"
	@echo "  make build          Build Docker images"
	@echo "  make up             Start all services"
	@echo "  make down           Stop all services"
	@echo "  make restart        Restart all services"
	@echo "  make logs           Show logs"
	@echo "  make ps             Show running services"
	@echo ""
	@echo "Database:"
	@echo "  make migrate        Run database migrations"
	@echo "  make migrate-create Create new migration"
	@echo "  make backup         Backup database"
	@echo "  make restore        Restore database"
	@echo ""
	@echo "Testing:"
	@echo "  make test           Run tests"
	@echo "  make test-cov       Run tests with coverage"
	@echo "  make lint           Run linters"
	@echo "  make format         Format code"
	@echo ""
	@echo "Deployment:"
	@echo "  make deploy         Deploy changes directly to remote VPS"
	@echo "  make watch-deploy   Watch local changes and auto-deploy to VPS"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean          Clean temporary files"
	@echo "  make shell          Open API shell"
	@echo "  make health         Check system health"

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

restart:
	docker compose restart

logs:
	docker compose logs -f

ps:
	docker compose ps

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +

test:
	docker compose exec legalia-api pytest

test-cov:
	docker compose exec legalia-api pytest --cov=app --cov-report=html --cov-report=term

lint:
	docker compose exec legalia-api ruff check app/

format:
	docker compose exec legalia-api ruff format app/

migrate:
	docker compose exec legalia-api alembic upgrade head

migrate-create:
	@read -p "Migration message: " msg; \
	docker compose exec legalia-api alembic revision --autogenerate -m "$$msg"

backup:
	./scripts/backup.sh

restore:
	@read -p "Backup file: " file; \
	docker compose exec -T postgres psql -U legalia -d legalia < $$file

shell:
	docker compose exec legalia-api python

health:
	@curl -s http://localhost:8000/api/v1/health | jq .

deploy:
	@./scripts/deploy_remote.sh

watch-deploy:
	@./scripts/watch_and_deploy.sh
