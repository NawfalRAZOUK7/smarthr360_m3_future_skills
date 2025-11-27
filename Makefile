# Makefile for SmartHR360 Module 3 - Future Skills ML Operations

.PHONY: help export-dataset train-model retrain-future-skills evaluate-model test coverage install-ml serve shell migrate createsuperuser

# Default Python interpreter (adjust if needed)
PYTHON := python
MANAGE := $(PYTHON) manage.py

# Default model version for training
MODEL_VERSION := v1
N_ESTIMATORS := 200

# Help target
help:
	@echo "=============================================="
	@echo "SmartHR360 - Future Skills ML Operations"
	@echo "=============================================="
	@echo ""
	@echo "📊 Machine Learning Commands:"
	@echo "  make export-dataset           Export future skills dataset to CSV"
	@echo "  make train-model              Train ML model (specify MODEL_VERSION=vX)"
	@echo "  make retrain-future-skills    Full retraining pipeline (export + train + update)"
	@echo "  make evaluate-model           Evaluate trained models"
	@echo ""
	@echo "🧪 Testing Commands:"
	@echo "  make test                     Run all tests"
	@echo "  make test-ml                  Run ML-specific tests"
	@echo "  make coverage                 Run tests with coverage report"
	@echo ""
	@echo "🔧 Development Commands:"
	@echo "  make install-ml               Install ML dependencies"
	@echo "  make serve                    Run Django development server"
	@echo "  make shell                    Open Django shell"
	@echo "  make migrate                  Run database migrations"
	@echo "  make createsuperuser          Create Django superuser"
	@echo "  make load-demo-data           Load demo fixtures"
	@echo ""
	@echo "📝 Documentation Commands:"
	@echo "  make docs-ml                  Open ML documentation"
	@echo "  make registry                 View model registry"
	@echo ""
	@echo "🧹 Cleanup Commands:"
	@echo "  make clean                    Clean temporary files"
	@echo "  make clean-models             Remove all model files (careful!)"
	@echo ""
	@echo "Examples:"
	@echo "  make retrain-future-skills MODEL_VERSION=v2 N_ESTIMATORS=300"
	@echo "  make train-model MODEL_VERSION=v3"
	@echo "=============================================="

# ============================================
# Machine Learning Commands
# ============================================

export-dataset:
	@echo "📤 Exporting Future Skills dataset to CSV..."
	$(MANAGE) export_future_skills_dataset

train-model:
	@echo "🎓 Training Future Skills model (version: $(MODEL_VERSION))..."
	$(PYTHON) ml/train_future_skills_model.py \
		--version $(MODEL_VERSION) \
		--n-estimators $(N_ESTIMATORS) \
		--output ml/future_skills_model_$(MODEL_VERSION).pkl

retrain-future-skills:
	@echo "🔄 Full retraining pipeline (version: $(MODEL_VERSION))..."
	$(PYTHON) ml/retrain_model.py \
		--version $(MODEL_VERSION) \
		--n-estimators $(N_ESTIMATORS) \
		--auto-update-settings

retrain-future-skills-manual:
	@echo "🔄 Full retraining pipeline without auto-update (version: $(MODEL_VERSION))..."
	$(PYTHON) ml/retrain_model.py \
		--version $(MODEL_VERSION) \
		--n-estimators $(N_ESTIMATORS)

evaluate-model:
	@echo "📊 Evaluating Future Skills models..."
	$(PYTHON) ml/evaluate_future_skills_models.py

# ============================================
# Testing Commands
# ============================================

test:
	@echo "🧪 Running all tests..."
	$(MANAGE) test

test-ml:
	@echo "🧪 Running ML-specific tests..."
	$(MANAGE) test future_skills.tests.test_prediction_engine

coverage:
	@echo "📊 Running tests with coverage..."
	coverage run --source='future_skills' $(MANAGE) test
	coverage report
	coverage html
	@echo "✅ Coverage report generated in htmlcov/index.html"

# ============================================
# Development Commands
# ============================================

install-ml:
	@echo "📦 Installing ML dependencies..."
	pip install -r requirements_ml.txt

serve:
	@echo "🚀 Starting Django development server..."
	$(MANAGE) runserver

shell:
	@echo "🐚 Opening Django shell..."
	$(MANAGE) shell

migrate:
	@echo "🗄️  Running database migrations..."
	$(MANAGE) migrate

createsuperuser:
	@echo "👤 Creating Django superuser..."
	$(MANAGE) createsuperuser

load-demo-data:
	@echo "📥 Loading demo fixtures..."
	$(MANAGE) loaddata future_skills/fixtures/future_skills_demo.json

recalculate-predictions:
	@echo "🔮 Recalculating all future skills predictions..."
	$(MANAGE) recalculate_future_skills

# ============================================
# Documentation Commands
# ============================================

docs-ml:
	@echo "📚 Opening ML documentation..."
	@cat ml/README.md

registry:
	@echo "📋 Model Registry:"
	@cat ml/MODEL_REGISTRY.md

mlops-guide:
	@echo "📖 MLOps Guide:"
	@cat ml/MLOPS_GUIDE.md

# ============================================
# Cleanup Commands
# ============================================

clean:
	@echo "🧹 Cleaning temporary files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".DS_Store" -delete
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .pytest_cache/
	@echo "✅ Cleanup complete"

clean-models:
	@echo "⚠️  WARNING: This will delete all model files!"
	@echo "Press Ctrl+C to cancel, or Enter to continue..."
	@read dummy
	rm -f ml/future_skills_model*.pkl
	rm -f ml/future_skills_model*.json
	@echo "✅ Model files deleted"

# ============================================
# Quick Development Workflows
# ============================================

# Full setup for new developers
setup: install-ml migrate load-demo-data
	@echo "✅ Development environment setup complete!"
	@echo "Next steps:"
	@echo "  1. Create superuser: make createsuperuser"
	@echo "  2. Train initial model: make retrain-future-skills MODEL_VERSION=v1"
	@echo "  3. Start server: make serve"

# Quick test cycle
quick-test: test-ml
	@echo "✅ Quick test cycle complete"

# Full ML pipeline (for production updates)
ml-pipeline: export-dataset train-model evaluate-model
	@echo "✅ ML pipeline complete"
	@echo "Review results and update settings.py if satisfied"
