.PHONY: help install dev test lint format clean
.PHONY: db-upgrade db-migration docker-up docker-down

# Variables
POETRY := poetry
PYTHON := poetry run python
UVICORN := poetry run uvicorn
APP_MODULE := app.server:app
HOST := 0.0.0.0
PORT := 8000
DOCKER_COMPOSE_FILE := infrastructure/docker/docker-compose.yml

help: ## Show this help message
	@echo "🚀 Agent OS - Essential Commands:"
	@echo ""
	@echo "🌟 Quick Start:"
	@echo "  make install       - Install dependencies"
	@echo "  make docker-up     - Start PostgreSQL via Docker"
	@echo "  make db-upgrade    - Apply database migrations"
	@echo "  make dev           - Start development server"
	@echo ""
	@echo "📡 Development:"
	@echo "  make dev           - Start development server with auto-reload"
	@echo "  make test          - Run all tests"
	@echo "  make lint          - Run code linting"
	@echo "  make type-check    - Run type checking"
	@echo "  make format        - Format code"
	@echo ""
	@echo "🗃️  Database:"
	@echo "  make db-upgrade    - Apply latest migrations"
	@echo "  make db-migration  - Create new migration"
	@echo ""
	@echo "🐳 Docker:"
	@echo "  make docker-up     - Start PostgreSQL and services"
	@echo "  make docker-down   - Stop all services"
	@echo ""
	@echo "🧹 Maintenance:"
	@echo "  make clean         - Clean build artifacts"
	@echo ""
	@echo "📖 Access URLs:"
	@echo "  API Server: http://localhost:8000"
	@echo "  Swagger UI: http://localhost:8000/docs"

# Essential Dependencies
install: ## Install dependencies
	$(POETRY) install

# Development Server
dev: ## Start development server with auto-reload
	$(UVICORN) $(APP_MODULE) --host $(HOST) --port $(PORT) --reload

# Testing & Quality
test: ## Run tests
	$(PYTHON) -m pytest

lint: ## Run code linting
	@echo "🔍 Running linter..."
	$(PYTHON) -m ruff check .

type-check: ## Run type checking
	@echo "🔍 Running type checking..."
	$(PYTHON) -m mypy app/ --ignore-missing-imports --explicit-package-bases

format: ## Format code
	@echo "🎨 Formatting code..."
	$(PYTHON) -m ruff format .
	$(PYTHON) -m ruff check --fix .

# Database
db-upgrade: ## Apply latest migrations
	$(PYTHON) -m alembic upgrade head

db-migration: ## Create a new migration
	@read -p "Enter migration message: " message; \
	$(PYTHON) -m alembic revision --autogenerate -m "$$message"

# Docker
docker-up: ## Start PostgreSQL and services
	docker compose -f $(DOCKER_COMPOSE_FILE) up -d
	@echo "🚀 PostgreSQL started!"
	@echo "🗄️  PostgreSQL: localhost:5432"

docker-down: ## Stop all services
	docker compose -f $(DOCKER_COMPOSE_FILE) down

# Cleanup
clean: ## Clean build artifacts
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/ dist/ .coverage htmlcov/ .pytest_cache/
