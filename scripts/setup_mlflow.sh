#!/bin/bash

# SmartHR360 MLflow Local Setup Script
# This script is for LOCAL Python onboarding only (not for Docker onboarding).
# For Docker onboarding, use scripts/docker-setup.sh instead.

set -e  # Exit on error

# ==========================================
echo "🚀 SmartHR360 MLflow Local Setup"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_error() { echo -e "${RED}✗ $1${NC}"; }
print_info() { echo -e "${YELLOW}ℹ $1${NC}"; }

# --- Always use project venv for all Python commands ---
PYTHON_CMD=".venv312/bin/python"
if [ ! -x ".venv312/bin/python" ]; then
    PYTHON_CMD=".venv314/bin/python"
fi

# --- Check Python version ---
print_info "Checking Python version..."
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed. Please install Python 3.11 or higher."
    exit 1
fi
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
print_success "Python $PYTHON_VERSION detected"

# --- Check for virtual environment ---
if [ -z "$VIRTUAL_ENV" ]; then
    print_info "You are not in a virtual environment."
    echo "It's recommended to activate one: source .venv/bin/activate"
    read -p "Continue anyway? (y/n): " continue_anyway
    if [[ ! $continue_anyway =~ ^[Yy]$ ]]; then
        print_error "Aborting setup. Activate a venv and rerun."
        exit 1
    fi
else
    print_success "Virtual environment: $VIRTUAL_ENV"
fi

# --- Install ML dependencies ---
print_info "Installing ML dependencies from requirements_ml.txt..."
if [ -f "requirements_ml.txt" ]; then
    pip install -r requirements_ml.txt
    print_success "ML dependencies installed"
else
    print_error "requirements_ml.txt not found. Please provide it."
    exit 1
fi

# --- Setup secrets.env for MLflow (if needed) ---
print_info "Checking for secrets.env (needed for remote artifact storage)..."
if [ ! -f "secrets.env" ]; then
    if [ -f "secrets.example" ]; then
        cp secrets.example secrets.env
        print_success "secrets.env created from secrets.example"
        print_info "Update secrets.env with your S3 or remote storage credentials if needed."
    else
        print_info "No secrets.example found. Skipping secrets.env setup."
    fi
else
    print_info "secrets.env already exists."
fi

# --- Create required directories ---
print_info "Creating required directories..."
mkdir -p artifacts/datasets artifacts/models artifacts/results artifacts/logs/predictions artifacts/cache/joblib mlruns/artifacts
print_success "Directories created"

# --- .env Creation and MLflow Configuration ---
print_info "Checking for .env file..."
if [ ! -f ".env" ]; then
    cat > .env << EOF
# MLflow Configuration
MLFLOW_TRACKING_URI=file://mlruns
MLFLOW_ARTIFACT_LOCATION=mlruns/artifacts
# Optional: Use these for remote tracking server
# MLFLOW_TRACKING_URI=http://localhost:5000
# MLFLOW_BACKEND_STORE_URI=postgresql://user:pass@localhost/mlflow_db
# MLFLOW_ARTIFACT_LOCATION=s3://your-bucket/mlflow-artifacts
# Optional: AWS credentials for S3 artifacts
# AWS_ACCESS_KEY_ID=your_key
# AWS_SECRET_ACCESS_KEY=your_secret
# AWS_DEFAULT_REGION=us-west-2
EOF
    print_success ".env file created for MLflow config"
    print_info "Update .env with your actual configuration as needed."
else
    print_info ".env already exists. Not modified."
fi

# --- MLflow Initialization and Experiment Setup ---
print_info "Testing MLflow import and version..."
${PYTHON_CMD} -c "import mlflow; print('MLflow version:', mlflow.__version__)" 2>/dev/null
if [ $? -eq 0 ]; then
    print_success "MLflow imported successfully"
else
    print_error "Failed to import MLflow. Check your installation."
    exit 1
fi

print_info "Initializing MLflow experiments (if needed)..."
${PYTHON_CMD} << EOF
try:
    import mlflow
    from ml.mlflow_config import get_mlflow_config
    config = get_mlflow_config()
    config.setup()
    print('✓ MLflow experiments created')
except Exception as e:
    print(f"Warning: Could not create experiments: {e}")
    print("This is okay - experiments will be created on first use")
EOF

# --- Verify Installation ---
print_info "Verifying MLflow and dependencies..."
${PYTHON_CMD} << EOF
import sys
try:
    import mlflow; print("✓ MLflow: OK")
except ImportError:
    print("✗ MLflow: FAILED"); sys.exit(1)
try:
    import pydantic; print("✓ Pydantic: OK")
except ImportError:
    print("✗ Pydantic: FAILED"); sys.exit(1)
try:
    import semver; print("✓ Semver: OK")
except ImportError:
    print("✗ Semver: FAILED"); sys.exit(1)
try:
    from prometheus_client import Counter; print("✓ Prometheus Client: OK")
except ImportError:
    print("✗ Prometheus Client: FAILED"); sys.exit(1)
try:
    from sklearn.ensemble import RandomForestClassifier; print("✓ Scikit-learn: OK")
except ImportError:
    print("✗ Scikit-learn: FAILED"); sys.exit(1)
try:
    import evidently; print("✓ Evidently: OK (optional)")
except ImportError:
    print("⚠ Evidently: Not installed (optional)")
try:
    import shap; print("✓ SHAP: OK (optional)")
except ImportError:
    print("⚠ SHAP: Not installed (optional)")
print("\nAll required components verified!")
EOF
if [ $? -ne 0 ]; then
    print_error "Verification failed"
    exit 1
fi

# --- Final Summary and Next Steps ---
echo ""
echo "=========================================="
print_success "MLflow local setup complete!"
echo ""
echo "Next steps:"
echo "  1. Activate virtual environment: source .venv/bin/activate"
echo "  2. Update .env and secrets.env with your configuration"
echo "  3. Start MLflow UI: mlflow ui --port 5000"
echo "     Then visit: http://localhost:5000"
echo "  4. Train your first model:"
echo "     python manage.py train_model --dataset artifacts/datasets/training_data.csv --version 1.0.0 --n-estimators 200"
echo "  5. View documentation:"
echo "     - Architecture: docs/ML_SYSTEM_ARCHITECTURE.md"
echo "     - Setup Guide: docs/MLFLOW_SETUP_GUIDE.md"
echo "     - Quick Reference: ml/README.md"
echo "=========================================="
echo ""
echo "If you want to use Docker for onboarding, use: scripts/docker-setup.sh"
echo "=========================================="
