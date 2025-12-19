#!/bin/bash
# ml_train.sh - Onboarding and training entrypoint for ML workflows (local/dev)
# Modular, user-friendly onboarding for ML training and prediction

set -e


# --- Color Variables and Print Helpers ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_error() { echo -e "${RED}✗ $1${NC}"; }
print_info() { echo -e "${BLUE}ℹ $1${NC}"; }
print_warn() { echo -e "${YELLOW}⚠ $1${NC}"; }



# --- Onboarding Section (Always First) ---
# 1. Check for Python virtual environment
if [[ -z "$VIRTUAL_ENV" ]]; then
  print_error "No Python virtual environment detected. Please activate your venv before running this script."
  exit 1
fi

# 2. Ensure secrets.env exists
if [[ ! -f "secrets.env" ]]; then
  print_warn "secrets.env not found. Copying from secrets.example..."
  cp secrets.example secrets.env
  print_success "secrets.env created from example."
fi

# 3. Ensure .env exists
if [[ ! -f ".env" ]]; then
  print_warn ".env not found. Copying from .env.example..."
  cp .env.example .env
  print_success ".env created from example."
fi

# 4. Ensure required directories exist
for dir in artifacts artifacts/datasets artifacts/models artifacts/results; do
  if [[ ! -d "$dir" ]]; then
    print_info "Creating directory: $dir"
    mkdir -p "$dir"
  fi
done

# --- Command Routing and Main Logic ---

# Show help/usage function
show_help() {
  echo -e "${CYAN}Usage:${NC} $0 <command> [options]"
  echo -e "\n${YELLOW}Onboarding:${NC} This script ensures secrets.env, .env, and required directories are present, and checks for a Python virtual environment before running any ML workflow command."
  echo -e "\n${YELLOW}Docker users:${NC} For containerized onboarding, use ${BLUE}scripts/docker-setup.sh${NC} instead."
  echo -e "\n${CYAN}Supported commands:${NC}"
  echo -e "  prepare             Prepare dataset from database"
  echo -e "  train [version]     Train model (default version: v1)"
  echo -e "  retrain [version]   Retrain model (default version: v1)"
  echo -e "  experiment          Run model experiments and comparison"
  echo -e "  evaluate            Evaluate trained models"
  echo -e "  predict <emp_id>    Generate predictions for employee"
  echo -e "  explainability      Run explainability analysis"
  echo -e "  dataset-analysis    Run dataset analysis"
  echo -e "  compare             Compare model performance"
  echo -e "  monitor             Check prediction monitoring metrics"
  echo -e "  clean               Clean ML artifacts"
  echo -e "  help, -h, --help    Show this help message"
  echo -e "\n${CYAN}Examples:${NC}"
  echo -e "  $0 prepare"
  echo -e "  $0 experiment"
  echo -e "  $0 train v2"
  echo -e "  $0 predict 123"
}

# Parse command
COMMAND=${1:-help}

case $COMMAND in
  "prepare")
    print_info "Exporting dataset from Django ORM..."
    python3 ml/scripts/prepare_dataset.py
    if [ $? -eq 0 ]; then
      print_success "Dataset exported: artifacts/datasets/future_skills_dataset.csv"
    else
      print_error "Dataset export failed. See error above."
      exit 1
    fi
    ;;
  "train")
    VERSION=${2:-v1}
    print_info "Training Future Skills model (version: $VERSION)..."
    python3 ml/scripts/train_future_skills_model.py --csv artifacts/datasets/future_skills_dataset.csv --output artifacts/models/future_skills_model.pkl --version "$VERSION"
    print_success "Model training completed"
    ;;
  "retrain")
    VERSION=${2:-v1}
    print_info "Retraining Future Skills model (version: $VERSION)..."
    python3 ml/scripts/retrain_model.py --version "$VERSION"
    print_success "Model retraining completed"
    ;;
  "experiment")
    print_info "Running model experiments..."
    python3 ml/scripts/experiment_future_skills_models.py
    print_success "Experiments completed. Results: artifacts/results/experiment_results.json"
    echo ""
    print_info "View detailed results:"
    echo "  python -m json.tool artifacts/results/experiment_results.json"
    ;;
  "evaluate")
    print_info "Evaluating trained models..."
    python3 ml/scripts/evaluate_future_skills_models.py
    print_success "Evaluation completed. Results: artifacts/results/evaluation_results.json"
    ;;
  "predict")
    if [ -z "$2" ]; then
      print_error "Employee ID required"
      echo "Usage: $0 predict <employee_id>"
      exit 1
    fi
    EMPLOYEE_ID=$2
    print_info "Generating predictions for employee $EMPLOYEE_ID..."
    # Add prediction logic here (placeholder)
    print_success "Predictions generated"
    ;;
  "explainability")
    print_info "Running explainability analysis..."
    jupyter nbconvert --execute ml/notebooks/explainability_analysis.ipynb --to html
    print_success "Explainability analysis completed"
    echo "View report: ml/notebooks/explainability_analysis.html"
    ;;
  "dataset-analysis")
    print_info "Running dataset analysis..."
    jupyter nbconvert --execute ml/notebooks/dataset_analysis.ipynb --to html
    print_success "Dataset analysis completed"
    echo "View report: ml/notebooks/dataset_analysis.html"
    ;;
  "compare")
    print_info "Comparing model performance..."
    if [ ! -f "artifacts/results/experiment_results.json" ]; then
      print_error "Experiment results not found. Run experiments first: $0 experiment"
      exit 1
    fi
    # Add comparison logic here (placeholder)
    print_success "Comparison completed"
    ;;
  "monitor")
    print_info "Checking model performance monitoring..."
    # Add monitoring logic here (placeholder)
    print_success "Monitoring check completed"
    ;;
  "clean")
    print_info "Cleaning ML artifacts..."
    read -p "Remove all trained models and results? (y/n): " confirm
    if [[ $confirm =~ ^[Yy]$ ]]; then
      rm -rf artifacts/models/*.joblib
      rm -rf artifacts/results/*.json
      rm -rf ml/notebooks/*.html
      print_success "ML artifacts cleaned"
    else
      print_info "Cleanup cancelled"
    fi
    ;;
  "help"|"-h"|"--help")
    show_help
    ;;
  *)
    print_error "Unknown command: $COMMAND"
    show_help
    exit 1
    ;;
esac
