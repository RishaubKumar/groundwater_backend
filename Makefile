# Groundwater Monitoring System - Makefile

.PHONY: help install test lint format clean build run dev docker-up docker-down init-db seed-data

# Default target
help:
	@echo "Groundwater Monitoring System - Available Commands:"
	@echo ""
	@echo "Development:"
	@echo "  install     Install dependencies"
	@echo "  dev         Run development server"
	@echo "  test        Run tests"
	@echo "  lint        Run linting checks"
	@echo "  format      Format code with black and isort"
	@echo "  clean       Clean up temporary files"
	@echo ""
	@echo "Database:"
	@echo "  init-db     Initialize database with tables and default data"
	@echo "  seed-data   Seed database with sample data"
	@echo "  migrate     Run database migrations"
	@echo ""
	@echo "Docker:"
	@echo "  docker-up   Start all services with Docker Compose"
	@echo "  docker-down Stop all Docker services"
	@echo "  build       Build Docker image"
	@echo ""
	@echo "Production:"
	@echo "  run         Run production server"
	@echo "  deploy      Deploy to production"

# Development commands
install:
	pip install -r requirements.txt

dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest tests/ -v --cov=app --cov-report=html --cov-report=term-missing

test-fast:
	pytest tests/ -v -x

lint:
	flake8 app/ tests/
	mypy app/
	black --check app/ tests/
	isort --check-only app/ tests/

format:
	black app/ tests/
	isort app/ tests/

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .coverage htmlcov/ .pytest_cache/ .mypy_cache/

# Database commands
init-db:
	python scripts/init_db.py

seed-data:
	python scripts/seed_data.py

migrate:
	alembic upgrade head

migrate-create:
	alembic revision --autogenerate -m "$(message)"

# Docker commands
docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

docker-build:
	docker-compose build

# Production commands
run:
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

deploy:
	@echo "Deployment would happen here"
	@echo "This could include:"
	@echo "- Building Docker image"
	@echo "- Pushing to registry"
	@echo "- Updating Kubernetes manifests"
	@echo "- Running database migrations"

# Utility commands
check-deps:
	pip check

update-deps:
	pip install --upgrade -r requirements.txt

security-check:
	bandit -r app/
	safety check

# Full setup for new environment
setup: install init-db seed-data
	@echo "Setup completed! Run 'make dev' to start the development server."

# CI/CD commands
ci-test: install test lint security-check

ci-build: docker-build

# Documentation
docs:
	@echo "API documentation available at: http://localhost:8000/api/v1/docs"
	@echo "ReDoc documentation available at: http://localhost:8000/api/v1/redoc"

# Health check
health:
	curl -f http://localhost:8000/health || echo "Service is not running"

# Database backup (PostgreSQL)
backup-db:
	pg_dump $(DATABASE_URL) > backup_$(shell date +%Y%m%d_%H%M%S).sql

# Database restore (PostgreSQL)
restore-db:
	psql $(DATABASE_URL) < $(backup_file)

# Show logs
logs:
	tail -f logs/app.log

# Show system status
status:
	@echo "=== System Status ==="
	@echo "API Health:"
	@curl -s http://localhost:8000/health | jq . || echo "API not responding"
	@echo ""
	@echo "Docker Services:"
	@docker-compose ps
	@echo ""
	@echo "Database Connections:"
	@echo "PostgreSQL: $(shell pg_isready -d $(DATABASE_URL) 2>/dev/null && echo 'OK' || echo 'FAILED')"
	@echo "Redis: $(shell redis-cli -u $(REDIS_URL) ping 2>/dev/null || echo 'FAILED')"
