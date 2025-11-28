#!/bin/bash

# MLflow Setup Script for SmartHR360
# This script sets up MLflow tracking for local development

set -e  # Exit on error

echo "======================================"
echo "SmartHR360 MLflow Setup"
echo "======================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Python is installed
if ! command -v python &> /dev/null; then
    echo -e "${RED}Error: Python is not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Python found: $(python --version)"

# Check if in virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}Warning: Not in a virtual environment${NC}"
    echo "It's recommended to use a virtual environment"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo -e "${GREEN}✓${NC} Virtual environment: $VIRTUAL_ENV"
fi

echo ""
echo "Step 1: Installing ML dependencies..."
echo "--------------------------------------"

# Install dependencies
pip install -q mlflow>=2.10.0 \
    pydantic>=2.0.0 \
    semver>=3.0.0 \
    prometheus-client>=0.19.0 \
    evidently>=0.4.0 \
    shap>=0.44.0 \
    scikit-learn>=1.3.0 \
    pandas>=2.0.0 \
    numpy>=1.24.0

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Dependencies installed successfully"
else
    echo -e "${RED}✗${NC} Failed to install dependencies"
    exit 1
fi

echo ""
echo "Step 2: Creating directory structure..."
echo "--------------------------------------"

# Create directories
mkdir -p ml/data
mkdir -p ml/models
mkdir -p ml/versions
mkdir -p ml/logs/predictions
mkdir -p mlruns/artifacts

echo -e "${GREEN}✓${NC} Directories created"

echo ""
echo "Step 3: Setting up configuration..."
echo "--------------------------------------"

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env file..."
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
    echo -e "${GREEN}✓${NC} .env file created"
else
    echo -e "${YELLOW}⚠${NC}  .env file already exists (not modified)"
fi

echo ""
echo "Step 4: Initializing MLflow..."
echo "--------------------------------------"

# Test MLflow import
python -c "import mlflow; print('MLflow version:', mlflow.__version__)" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} MLflow initialized successfully"
else
    echo -e "${RED}✗${NC} Failed to initialize MLflow"
    exit 1
fi

# Initialize MLflow experiments
python << EOF
import mlflow
from ml.mlflow_config import get_mlflow_config

try:
    config = get_mlflow_config()
    config.setup()
    print("✓ MLflow experiments created")
except Exception as e:
    print(f"Warning: Could not create experiments: {e}")
    print("This is okay - experiments will be created on first use")
EOF

echo ""
echo "Step 5: Verifying installation..."
echo "--------------------------------------"

# Verify components
python << EOF
import sys

try:
    import mlflow
    print("✓ MLflow: OK")
except ImportError:
    print("✗ MLflow: FAILED")
    sys.exit(1)

try:
    import pydantic
    print("✓ Pydantic: OK")
except ImportError:
    print("✗ Pydantic: FAILED")
    sys.exit(1)

try:
    import semver
    print("✓ Semver: OK")
except ImportError:
    print("✗ Semver: FAILED")
    sys.exit(1)

try:
    from prometheus_client import Counter
    print("✓ Prometheus Client: OK")
except ImportError:
    print("✗ Prometheus Client: FAILED")
    sys.exit(1)

try:
    from sklearn.ensemble import RandomForestClassifier
    print("✓ Scikit-learn: OK")
except ImportError:
    print("✗ Scikit-learn: FAILED")
    sys.exit(1)

# Optional imports (won't fail if missing)
try:
    import evidently
    print("✓ Evidently: OK (optional)")
except ImportError:
    print("⚠ Evidently: Not installed (optional)")

try:
    import shap
    print("✓ SHAP: OK (optional)")
except ImportError:
    print("⚠ SHAP: Not installed (optional)")

print("\nAll required components verified!")
EOF

if [ $? -ne 0 ]; then
    echo -e "${RED}✗${NC} Verification failed"
    exit 1
fi

echo ""
echo "======================================"
echo -e "${GREEN}✓ Setup Complete!${NC}"
echo "======================================"
echo ""
echo "Next steps:"
echo ""
echo "1. Start MLflow UI (optional):"
echo "   mlflow ui --port 5000"
echo "   Then visit: http://localhost:5000"
echo ""
echo "2. Train your first model:"
echo "   python manage.py train_model \\"
echo "       --dataset ml/data/training_data.csv \\"
echo "       --version 1.0.0 \\"
echo "       --n-estimators 200"
echo ""
echo "3. View documentation:"
echo "   - Architecture: docs/ML_SYSTEM_ARCHITECTURE.md"
echo "   - Setup Guide: docs/MLFLOW_SETUP_GUIDE.md"
echo "   - Quick Reference: ml/README.md"
echo ""
echo "For more information, see docs/ML_SYSTEM_ARCHITECTURE.md"
echo ""
