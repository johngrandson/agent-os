.PHONY: help install install-dev dev run run-prod test test-coverage lint format clean clean-all
.PHONY: db-upgrade db-downgrade db-migration db-reset migrate migrate-create seed
.PHONY: docker-up docker-down docker-logs docker-logs-postgres docker-restart docker-db-shell docker-build docker-run docker-clean
.PHONY: env-setup env-down setup start restart health logs check ci-test

# Variables
POETRY := poetry
PYTHON := poetry run python
PIP := poetry add
UVICORN := poetry run uvicorn
APP_MODULE := app.server:app
HOST := 0.0.0.0
PORT := 8000
DOCKER_COMPOSE_FILE := infrastructure/docker/docker-compose.yml

help: ## Show this help message
	@echo "🚀 Agent OS - Available Commands:"
	@echo ""
	@echo "🌟 Quick Start:"
	@echo "  make env-setup     - Start complete environment (Docker + DB + Migrations)"
	@echo "  make docker-down   - Stop complete environment"
	@echo ""
	@echo "📡 API Server:"
	@echo "  make dev           - Start development server with auto-reload"
	@echo "  make run           - Start development server with auto-reload (alias)"
	@echo "  make run-prod      - Start production server"
	@echo ""
	@echo "🗃️  Database:"
	@echo "  make db-upgrade    - Apply latest migrations"
	@echo "  make db-downgrade  - Rollback one migration"
	@echo "  make db-migration  - Create new migration"
	@echo "  make db-reset      - Reset database (downgrade + upgrade)"
	@echo ""
	@echo "🐳 Docker Environment:"
	@echo "  make docker-up     - Start PostgreSQL and services"
	@echo "  make docker-down   - Stop all services"
	@echo "  make docker-logs   - View all service logs"
	@echo "  make docker-db-shell - Open PostgreSQL shell"
	@echo ""
	@echo "🧪 Testing & Quality:"
	@echo "  make test          - Run all tests"
	@echo "  make test-coverage - Run tests with coverage"
	@echo "  make lint          - Run linting (Ruff only)"
	@echo "  make lint-mypy     - Run MyPy type checking"
	@echo "  make lint-all      - Run all linting tools"
	@echo "  make format        - Format code"
	@echo "  make imports       - Organize imports"
	@echo "  make check         - Run all quality checks (lint + format + tests)"
	@echo ""
	@echo "🧹 Maintenance:"
	@echo "  make clean         - Clean build artifacts"
	@echo "  make install       - Install dependencies"
	@echo "  make health        - Check API health"
	@echo "  make seed-agents   - Seed database with agents and knowledge (pt-BR)"
	@echo "  make seed-agents-docker - Seed via Docker (when DB is in containers)"
	@echo ""
	@echo "📖 Access URLs:"
	@echo "  API Server: http://localhost:8000"
	@echo "  Swagger UI: http://localhost:8000/docs"

# Dependencies
install: ## Install dependencies
	$(POETRY) install

install-dev: ## Install development dependencies
	$(POETRY) install --with dev

# API Server Commands
dev: ## Start development server with auto-reload
	$(UVICORN) $(APP_MODULE) --host $(HOST) --port $(PORT) --reload

run: ## Start development server with auto-reload (alias for dev)
	$(UVICORN) $(APP_MODULE) --host $(HOST) --port $(PORT) --reload

run-prod: ## Start production server
	$(UVICORN) $(APP_MODULE) --host $(HOST) --port $(PORT)

# Testing & Quality
test: ## Run tests
	$(PYTHON) -m pytest

test-coverage: ## Run tests with coverage
	$(PYTHON) -m pytest --cov=app --cov-report=html --cov-report=term

lint: ## Run linting (Ruff only)
	@echo "🔍 Running Ruff linter..."
	$(PYTHON) -m ruff check .
	@echo "✅ Ruff linting completed"

lint-mypy: ## Run MyPy type checking
	@echo "🔍 Running MyPy type checker..."
	$(PYTHON) -m mypy --explicit-package-bases app/ || echo "⚠️  MyPy found issues (non-blocking)"
	@echo "✅ MyPy checking completed"

lint-all: ## Run all linting tools
	@echo "🔍 Running all linting tools..."
	$(MAKE) lint
	$(MAKE) lint-mypy
	@echo "✅ All linting completed"

format: ## Format code
	@echo "🎨 Formatting code..."
	$(PYTHON) -m ruff format .
	$(PYTHON) -m ruff check --fix .
	@echo "✅ Code formatting completed"

imports: ## Organize imports
	@echo "📦 Organizing imports..."
	$(PYTHON) -m ruff check --select I --fix .
	@echo "✅ Import organization completed"

check: ## Run all quality checks (lint + format + tests)
	@echo "🔍 Running all quality checks..."
	$(MAKE) lint
	$(MAKE) format
	$(MAKE) test
	@echo "✅ All quality checks completed"

# Cleanup Commands
clean: ## Clean build artifacts
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/
	rm -rf dist/
	rm -rf .coverage
	rm -rf htmlcov/

clean-all: clean docker-clean ## Clean all artifacts (build + docker)

# Database Commands
db-upgrade: ## Apply latest migrations
	$(PYTHON) -m alembic upgrade head

db-downgrade: ## Rollback one migration
	$(PYTHON) -m alembic downgrade -1

db-migration: ## Create a new migration
	@read -p "Enter migration message: " message; \
	$(PYTHON) -m alembic revision --autogenerate -m "$$message"

db-reset: ## Reset database (downgrade base + upgrade head)
	$(PYTHON) -m alembic downgrade base
	$(PYTHON) -m alembic upgrade head

# Legacy aliases
migrate: db-upgrade ## (Legacy) Run database migrations
migrate-create: db-migration ## (Legacy) Create a new migration

seed: ## Seed the database with initial data
	$(PYTHON) scripts/seeders/prompt_seeder.py

seed-agents: ## Seed the database with agents and knowledge (pt-BR)
	$(PYTHON) scripts/seeders/agent_seeder.py

seed-agents-docker: ## Seed the database with agents (pt-BR) via Docker
	docker exec fastapi-api python scripts/seeders/agent_seeder.py

reset-db-docker: ## Reset database tables via Docker (WARNING: deletes all data)
	docker exec fastapi-api python -c "import asyncio; from infrastructure.database.session import engines, EngineType; from infrastructure.database import Base; asyncio.run(Base.metadata.drop_all(engines[EngineType.WRITER].sync_engine)); print('🗑️  Database reset complete')"

health: ## Check API health
	curl -f http://localhost:$(PORT)/api/v1/health || (echo "API is not running" && exit 1)

logs: ## Show recent logs (if using docker)
	docker logs agent-os --tail=100 -f


# Docker Environment
docker-up: ## Start PostgreSQL and services
	docker compose -f $(DOCKER_COMPOSE_FILE) up --build
	@echo "🚀 Development environment started!"
	@echo "📊 API Server: http://localhost:8000"
	@echo "📊 Swagger UI: http://localhost:8000/docs"
	@echo "🗄️  PostgreSQL: localhost:5432"

docker-down: ## Stop all services
	docker compose -f $(DOCKER_COMPOSE_FILE) down
	@echo "🛑 Environment stopped"

docker-logs: ## View all service logs
	docker compose -f $(DOCKER_COMPOSE_FILE) logs -f

docker-logs-postgres: ## View PostgreSQL logs only
	docker compose -f $(DOCKER_COMPOSE_FILE) logs -f postgres

docker-restart: ## Restart all services
	docker compose -f $(DOCKER_COMPOSE_FILE) restart

docker-db-shell: ## Open PostgreSQL shell
	docker compose -f $(DOCKER_COMPOSE_FILE) exec postgres psql -U fastapi -d fastapi

docker-build: ## Build Docker image
	docker build -t agent-os .

docker-run: ## Run with Docker
	docker run -p $(PORT):$(PORT) --env-file .env agent-os

docker-clean: ## Clean Docker resources
	docker compose -f $(DOCKER_COMPOSE_FILE) down -v
	docker system prune -f

# Environment Management
env-setup: docker-up ## Start complete environment (Docker + DB + Migrations)
	@echo "⏳ Waiting for database to be ready..."
	@sleep 5
	$(PYTHON) -m alembic upgrade head
	@echo "🚀 Development environment setup complete!"

env-down: docker-down ## Stop complete environment

# Development workflow
setup: install db-upgrade seed ## Complete setup for new developers

start: run ## Alias for run

restart: ## Restart the development server
	pkill -f "uvicorn.*$(APP_MODULE)" || true
	sleep 2
	$(MAKE) run &

# CI/CD helpers
ci-test: ## Run all CI tests
	@echo "🤖 Running CI pipeline..."
	$(MAKE) lint
	$(MAKE) test-coverage
	@echo "✅ CI pipeline completed"

ci-test-full: ## Run full CI tests including MyPy
	@echo "🤖 Running full CI pipeline..."
	$(MAKE) lint-all
	$(MAKE) test-coverage
	@echo "✅ Full CI pipeline completed"
