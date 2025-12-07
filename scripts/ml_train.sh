#!/bin/bash

# SmartHR360 ML Model Training and Evaluation Script
# Simplifies ML workflow operations

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Activate virtual environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Parse command
COMMAND=${1:-help}

ARTIFACTS_DIR=${ARTIFACTS_DIR:-artifacts}
MODELS_DIR="${ARTIFACTS_DIR}/models"
RESULTS_DIR="${ARTIFACTS_DIR}/results"
DATASETS_DIR="${ARTIFACTS_DIR}/datasets"

case $COMMAND in
    "prepare")
        print_info "Preparing dataset..."
        python ml/scripts/prepare_dataset.py
        print_success "Dataset prepared: ${DATASETS_DIR}/future_skills_dataset.csv"
        ;;

    "experiment")
        print_info "Running model experiments..."
        python ml/experiment_future_skills_models.py
        print_success "Experiments completed. Results: ${RESULTS_DIR}/experiment_results.json"
        echo ""
        print_info "View detailed results:"
        echo "  python -m json.tool ${RESULTS_DIR}/experiment_results.json"
        ;;

    "evaluate")
        print_info "Evaluating trained models..."
        python ml/evaluate_future_skills_models.py
        print_success "Evaluation completed. Results: ${RESULTS_DIR}/evaluation_results.json"
        ;;

    "train")
        MODEL=${2:-random_forest}
        print_info "Training $MODEL model..."
        python ml/scripts/train_model.py --model "$MODEL"
        print_success "Model training completed"
        ;;

    "predict")
        if [ -z "$2" ]; then
            print_error "Employee ID required"
            echo "Usage: $0 predict <employee_id>"
            exit 1
        fi
        EMPLOYEE_ID=$2
        print_info "Generating predictions for employee $EMPLOYEE_ID..."
        python manage.py shell <<EOF
from future_skills.models import Employee
from future_skills.services.prediction_engine import PredictionEngine
employee = Employee.objects.get(id=$EMPLOYEE_ID)
predictions = PredictionEngine.predict_for_employee(employee)
for pred in predictions[:5]:
    print(f"Skill: {pred['future_skill_name']}, Score: {pred['prediction_score']:.2f}")
EOF
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
        if [ ! -f "${RESULTS_DIR}/experiment_results.json" ]; then
            print_error "Experiment results not found. Run experiments first: $0 experiment"
            exit 1
        fi
        python <<EOF
import json
with open('${RESULTS_DIR}/experiment_results.json') as f:
    results = json.load(f)
print("\nModel Performance Comparison:")
print("-" * 70)
print(f"{'Model':<30} {'Accuracy':<15} {'F1 Score':<15}")
print("-" * 70)
for model_name, metrics in results.items():
    if 'test_accuracy' in metrics:
        acc = metrics['test_accuracy']
        f1 = metrics.get('test_f1_weighted', 'N/A')
        print(f"{model_name:<30} {acc:<15.4f} {f1:<15}")
print("-" * 70)
EOF
        print_success "Comparison completed"
        ;;

    "monitor")
        print_info "Checking model performance monitoring..."
        python manage.py shell <<EOF
from future_skills.models import PredictionLog
from datetime import datetime, timedelta
recent = datetime.now() - timedelta(days=7)
logs = PredictionLog.objects.filter(timestamp__gte=recent)
print(f"\nPredictions in last 7 days: {logs.count()}")
if logs.exists():
    avg_score = logs.aggregate(avg=models.Avg('prediction_score'))['avg']
    print(f"Average prediction score: {avg_score:.2f}")
EOF
        print_success "Monitoring check completed"
        ;;

    "retrain")
        print_info "Retraining models with latest data..."
        python ml/scripts/prepare_dataset.py
        python ml/experiment_future_skills_models.py
        python ml/evaluate_future_skills_models.py
        print_success "Retraining completed"
        echo ""
        print_info "Next steps:"
        echo "  1. Review evaluation results: ${RESULTS_DIR}/evaluation_results.json"
        echo "  2. Update production model if performance improved"
        echo "  3. Run explainability analysis: $0 explainability"
        ;;

    "clean")
        print_info "Cleaning ML artifacts..."
        read -p "Remove all trained models and results? (y/n): " confirm
        if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
            rm -rf ${MODELS_DIR}/*.joblib
            rm -rf ${RESULTS_DIR}/*.json
            rm -rf ml/notebooks/*.html
            print_success "ML artifacts cleaned"
        else
            print_info "Cleanup cancelled"
        fi
        ;;

    "help"|"-h"|"--help")
        echo "SmartHR360 ML Management Script"
        echo ""
        echo "Usage: $0 [COMMAND] [OPTIONS]"
        echo ""
        echo "Commands:"
        echo "  prepare           - Prepare dataset from database"
        echo "  experiment        - Run model experiments and comparison"
        echo "  evaluate          - Evaluate trained models"
        echo "  train [model]     - Train specific model"
        echo "  predict <emp_id>  - Generate predictions for employee"
        echo "  explainability    - Run explainability analysis"
        echo "  dataset-analysis  - Run dataset analysis"
        echo "  compare           - Compare model performance"
        echo "  monitor           - Check prediction monitoring metrics"
        echo "  retrain           - Retrain all models with latest data"
        echo "  clean             - Clean ML artifacts"
        echo "  help              - Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0 prepare                # Prepare dataset"
        echo "  $0 experiment             # Run experiments"
        echo "  $0 train random_forest    # Train Random Forest"
        echo "  $0 predict 123            # Predict for employee 123"
        exit 0
        ;;

    *)
        print_error "Unknown command: $COMMAND"
        echo "Run '$0 help' for usage information"
        exit 1
        ;;
esac
