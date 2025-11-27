# Makefile for SmartHR360 Module 3 - Future Skills

.PHONY: help install install-dev install-ml test test-unit test-integration test-e2e test-fast test-ml test-api coverage lint format check docker-build docker-up docker-down docker-prod docker-logs docker-shell ml-prepare ml-experiment ml-evaluate ml-train serve shell migrate createsuperuser clean

# Default Python interpreter and settings
PYTHON := python
MANAGE := $(PYTHON) manage.py
SETTINGS := config.settings.development
MODEL_VERSION := v1
N_ESTIMATORS := 200

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
NC := \033[0m # No Color

# Help target
help:
	@echo "=============================================="
	@echo "$(BLUE)SmartHR360 - Future Skills$(NC)"
	@echo "=============================================="
	@echo ""
	@echo "$(YELLOW)📦 Installation Commands:$(NC)"
	@echo "  make install              Install production dependencies"
	@echo "  make install-dev          Install development dependencies"
	@echo "  make install-ml           Install ML dependencies"
	@echo "  make setup                Complete development environment setup"
	@echo ""
	@echo "$(YELLOW)🧪 Testing Commands:$(NC)"
	@echo "  make test                 Run all tests with coverage"
	@echo "  make test-unit            Run unit tests only"
	@echo "  make test-integration     Run integration tests"
	@echo "  make test-e2e             Run end-to-end tests"
	@echo "  make test-fast            Run fast tests (exclude slow)"
	@echo "  make test-ml              Run ML-specific tests"
	@echo "  make test-api             Run API tests"
	@echo "  make test-failed          Re-run last failed tests"
	@echo "  make coverage             Generate detailed coverage report"
	@echo ""
	@echo "$(YELLOW)🎨 Code Quality Commands:$(NC)"
	@echo "  make lint                 Run all linters (black, flake8, isort)"
	@echo "  make format               Auto-format code (black, isort)"
	@echo "  make check                Run Django system checks"
	@echo "  make pre-commit           Run pre-commit hooks on all files"
	@echo ""
	@echo "$(YELLOW)🐳 Docker Commands:$(NC)"
	@echo "  make docker-build         Build Docker images"
	@echo "  make docker-up            Start development environment"
	@echo "  make docker-down          Stop Docker containers"
	@echo "  make docker-prod          Start production environment"
	@echo "  make docker-logs          Show Docker logs"
	@echo "  make docker-shell         Open shell in web container"
	@echo "  make docker-test          Run tests in Docker"
	@echo "  make docker-clean         Clean Docker resources"
	@echo ""
	@echo "$(YELLOW)🤖 Machine Learning Commands:$(NC)"
	@echo "  make ml-prepare           Prepare ML dataset"
	@echo "  make ml-experiment        Run model experiments"
	@echo "  make ml-evaluate          Evaluate trained models"
	@echo "  make ml-train             Train specific model"
	@echo "  make ml-compare           Compare model performance"
	@echo "  make ml-retrain           Full retraining pipeline"
	@echo "  make ml-explainability    Run explainability analysis"
	@echo ""
	@echo "$(YELLOW)🔧 Development Commands:$(NC)"
	@echo "  make serve                Run Django development server"
	@echo "  make shell                Open Django shell"
	@echo "  make migrate              Run database migrations"
	@echo "  make createsuperuser      Create Django superuser"
	@echo "  make seed-data            Load demo data"
	@echo ""
	@echo "$(YELLOW)🧹 Cleanup Commands:$(NC)"
	@echo "  make clean                Clean temporary files"
	@echo "  make clean-pyc            Remove Python cache files"
	@echo "  make clean-test           Remove test artifacts"
	@echo "  make clean-models         Remove ML model files"
	@echo ""
	@echo "Examples:"
	@echo "  make setup                # Complete dev setup"
	@echo "  make test-fast            # Quick test run"
	@echo "  make docker-up            # Start with Docker"
	@echo "  make ml-retrain           # Retrain ML models"
	@echo "=============================================="

# ============================================
# Installation Commands
# ============================================

install:
	@echo "$(GREEN)📦 Installing production dependencies...$(NC)"
	pip install -r requirements.txt
	@echo "$(GREEN)✓ Production dependencies installed$(NC)"

install-dev:
	@echo "$(GREEN)📦 Installing development dependencies...$(NC)"
	pip install -r requirements.txt
	pip install -r requirements-dev.txt
	@echo "$(GREEN)✓ Development dependencies installed$(NC)"

install-ml:
	@echo "$(GREEN)📦 Installing ML dependencies...$(NC)"
	pip install -r requirements_ml.txt
	@echo "$(GREEN)✓ ML dependencies installed$(NC)"

setup:
	@echo "$(BLUE)🚀 Setting up development environment...$(NC)"
	@bash scripts/setup_dev.sh

# ============================================
# Testing Commands
# ============================================

test:
	@echo "$(BLUE)🧪 Running all tests with coverage...$(NC)"
	pytest --cov=future_skills --cov-report=html --cov-report=term-missing -v

test-unit:
	@echo "$(BLUE)🧪 Running unit tests...$(NC)"
	pytest future_skills/tests/ -v -m "not slow"

test-integration:
	@echo "$(BLUE)🧪 Running integration tests...$(NC)"
	pytest tests/integration/ -v

test-e2e:
	@echo "$(BLUE)🧪 Running end-to-end tests...$(NC)"
	pytest tests/e2e/ -v

test-fast:
	@echo "$(BLUE)🧪 Running fast tests...$(NC)"
	pytest -v -m "not slow"

test-ml:
	@echo "$(BLUE)🧪 Running ML tests...$(NC)"
	pytest -v -m "ml"

test-api:
	@echo "$(BLUE)🧪 Running API tests...$(NC)"
	pytest -v -m "api"

test-failed:
	@echo "$(BLUE)🧪 Re-running last failed tests...$(NC)"
	pytest --lf -v

coverage:
	@echo "$(BLUE)📊 Generating detailed coverage report...$(NC)"
	pytest --cov=future_skills --cov-report=html --cov-report=term-missing --cov-report=json
	@echo "$(GREEN)✓ Coverage report: htmlcov/index.html$(NC)"

# ============================================
# Code Quality Commands
# ============================================

lint:
	@echo "$(BLUE)🔍 Running linters...$(NC)"
	@echo "Running Black..."
	black --check . || true
	@echo "Running Flake8..."
	flake8 future_skills/ config/ ml/ --max-line-length=120 --exclude=migrations,__pycache__,.venv || true
	@echo "Running isort..."
	isort --check-only . || true
	@echo "$(GREEN)✓ Linting complete$(NC)"

format:
	@echo "$(BLUE)🎨 Formatting code...$(NC)"
	black .
	isort .
	@echo "$(GREEN)✓ Code formatted$(NC)"

check:
	@echo "$(BLUE)🔍 Running Django system checks...$(NC)"
	$(MANAGE) check --settings=$(SETTINGS)
	@echo "$(GREEN)✓ System checks passed$(NC)"

pre-commit:
	@echo "$(BLUE)🔍 Running pre-commit hooks...$(NC)"
	pre-commit run --all-files

# ============================================
# Docker Commands
# ============================================

docker-build:
	@echo "$(BLUE)🐳 Building Docker images...$(NC)"
	docker-compose build
	@echo "$(GREEN)✓ Docker images built$(NC)"

docker-up:
	@echo "$(BLUE)🐳 Starting development environment...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)✓ Development environment running$(NC)"
	@docker-compose ps

docker-down:
	@echo "$(BLUE)🐳 Stopping Docker containers...$(NC)"
	docker-compose down
	@echo "$(GREEN)✓ Containers stopped$(NC)"

docker-prod:
	@echo "$(BLUE)🐳 Starting production environment...$(NC)"
	docker-compose -f docker-compose.prod.yml up -d --build
	@echo "$(GREEN)✓ Production environment running$(NC)"
	@docker-compose -f docker-compose.prod.yml ps

docker-logs:
	@echo "$(BLUE)📋 Docker logs:$(NC)"
	docker-compose logs -f

docker-shell:
	@echo "$(BLUE)🐚 Opening shell in web container...$(NC)"
	docker-compose exec web /bin/bash

docker-test:
	@echo "$(BLUE)🧪 Running tests in Docker...$(NC)"
	docker-compose exec web pytest --cov=future_skills

docker-clean:
	@echo "$(YELLOW)⚠️  Cleaning Docker resources...$(NC)"
	docker-compose down -v
	docker system prune -f

# ============================================
# Machine Learning Commands
# ============================================

ml-prepare:
	@echo "$(BLUE)📤 Preparing ML dataset...$(NC)"
	$(MANAGE) export_future_skills_dataset --settings=$(SETTINGS)
	@echo "$(GREEN)✓ Dataset prepared$(NC)"

ml-experiment:
	@echo "$(BLUE)🔬 Running model experiments...$(NC)"
	$(PYTHON) ml/experiment_future_skills_models.py
	@echo "$(GREEN)✓ Experiments complete: ml/results/experiment_results.json$(NC)"

ml-evaluate:
	@echo "$(BLUE)📊 Evaluating trained models...$(NC)"
	$(PYTHON) ml/evaluate_future_skills_models.py
	@echo "$(GREEN)✓ Evaluation complete: ml/results/evaluation_results.json$(NC)"

ml-train:
	@echo "$(BLUE)🎓 Training model (version: $(MODEL_VERSION))...$(NC)"
	$(PYTHON) ml/scripts/train_model.py --model random_forest --version $(MODEL_VERSION)
	@echo "$(GREEN)✓ Model training complete$(NC)"

ml-compare:
	@echo "$(BLUE)📊 Comparing model performance...$(NC)"
	@bash scripts/ml_train.sh compare

ml-retrain:
	@echo "$(BLUE)🔄 Full retraining pipeline...$(NC)"
	@bash scripts/ml_train.sh retrain

ml-explainability:
	@echo "$(BLUE)🔍 Running explainability analysis...$(NC)"
	jupyter nbconvert --execute ml/notebooks/explainability_analysis.ipynb --to html
	@echo "$(GREEN)✓ Analysis complete: ml/notebooks/explainability_analysis.html$(NC)"

# ============================================
# Development Commands
# ============================================

serve:
	@echo "$(BLUE)🚀 Starting Django development server...$(NC)"
	$(MANAGE) runserver --settings=$(SETTINGS)

shell:
	@echo "$(BLUE)🐚 Opening Django shell...$(NC)"
	$(MANAGE) shell --settings=$(SETTINGS)

migrate:
	@echo "$(BLUE)🗄️  Running database migrations...$(NC)"
	$(MANAGE) migrate --settings=$(SETTINGS)
	@echo "$(GREEN)✓ Migrations complete$(NC)"

makemigrations:
	@echo "$(BLUE)🗄️  Creating migrations...$(NC)"
	$(MANAGE) makemigrations --settings=$(SETTINGS)

createsuperuser:
	@echo "$(BLUE)👤 Creating Django superuser...$(NC)"
	$(MANAGE) createsuperuser --settings=$(SETTINGS)

seed-data:
	@echo "$(BLUE)📥 Loading demo data...$(NC)"
	$(MANAGE) seed_future_skills --settings=$(SETTINGS)
	@echo "$(GREEN)✓ Demo data loaded$(NC)"

recalculate:
	@echo "$(BLUE)🔮 Recalculating predictions...$(NC)"
	$(MANAGE) recalculate_future_skills --settings=$(SETTINGS)
	@echo "$(GREEN)✓ Predictions recalculated$(NC)"

# ============================================
# Cleanup Commands
# ============================================

clean:
	@echo "$(BLUE)🧹 Cleaning temporary files...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type f -name ".DS_Store" -delete 2>/dev/null || true
	@echo "$(GREEN)✓ Cleanup complete$(NC)"

clean-pyc:
	@echo "$(BLUE)🧹 Removing Python cache files...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true

clean-test:
	@echo "$(BLUE)🧹 Removing test artifacts...$(NC)"
	rm -rf htmlcov/ .coverage .pytest_cache/ 2>/dev/null || true
	@echo "$(GREEN)✓ Test artifacts removed$(NC)"

clean-models:
	@echo "$(YELLOW)⚠️  WARNING: This will delete all ML model files!$(NC)"
	@echo "Press Ctrl+C to cancel, Enter to continue..."
	@read dummy
	rm -rf ml/models/*.joblib ml/results/*.json 2>/dev/null || true
	@echo "$(GREEN)✓ Model files deleted$(NC)"

clean-all: clean clean-test
	@echo "$(GREEN)✓ Complete cleanup done$(NC)"

# ============================================
# Quick Workflows
# ============================================

# Quick test before commit
quick-check: format lint test-fast
	@echo "$(GREEN)✓ Quick check complete - ready to commit!$(NC)"

# Full CI simulation
ci: install-dev migrate lint test
	@echo "$(GREEN)✓ CI simulation complete$(NC)"

# Development cycle
dev: migrate seed-data serve

# Production deployment check
prod-check: lint test docker-build
	@echo "$(GREEN)✓ Production checks passed$(NC)"
