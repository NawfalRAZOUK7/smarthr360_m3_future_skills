# ML System Components

**SmartHR360 Future Skills - Machine Learning Operations**

---

## Overview

This directory contains the ML infrastructure for managing the complete lifecycle of machine learning models in SmartHR360:

- **Experiment Tracking**: MLflow integration for tracking training runs
- **Model Versioning**: Semantic versioning with metadata management
- **Monitoring**: Real-time performance tracking and drift detection
- **Model Registry**: Centralized model management with staging

---

## Directory Structure

```
ml/
├── __init__.py                 # Package initialization
├── requirements.txt            # ML-specific dependencies
├── mlflow_config.py           # MLflow configuration and integration (650+ lines)
├── model_versioning.py        # Semantic versioning system (750+ lines)
├── monitoring.py              # Performance monitoring & drift detection (680+ lines)
├── data/                      # Training datasets
│   └── training_data.csv
├── models/                    # Saved model files (.pkl)
│   └── model_v1.0.0.pkl
├── versions/                  # Version metadata (JSON)
│   └── versions.json
├── logs/                      # Prediction logs
│   └── predictions/
│       └── predictions_YYYYMMDD.jsonl
├── mlruns/                    # MLflow tracking (file-based)
│   ├── artifacts/
│   ├── .trash/
│   └── experiments/
└── docs/                      # ML documentation
    ├── ML_SYSTEM_ARCHITECTURE.md
    └── MLFLOW_SETUP_GUIDE.md
```

---

## Core Components

### 1. MLflow Configuration (`mlflow_config.py`)

**Purpose**: Centralized MLflow setup and integration

**Key Features**:

- Automatic tracking URI detection
- Experiment management (4 default experiments)
- Model Registry operations
- Run search and comparison
- Cleanup utilities

**Usage**:

```python
from ml.mlflow_config import get_mlflow_config

config = get_mlflow_config()
config.setup()

with config.start_run(run_name="training") as run:
    mlflow.log_param("n_estimators", 100)
    mlflow.log_metric("accuracy", 0.92)
    mlflow.sklearn.log_model(model, "model")
```

**Key Classes**:

- `MLflowConfig`: Main configuration class
- Global functions: `get_mlflow_config()`, `get_mlflow_client()`, `initialize_mlflow()`

**Default Experiments**:

1. `future-skills-prediction` - Prediction tracking
2. `model-training` - Training experiments
3. `model-evaluation` - Model evaluation
4. `production-monitoring` - Production monitoring

---

### 2. Model Versioning (`model_versioning.py`)

**Purpose**: Semantic versioning and model metadata management

**Key Features**:

- Semantic versioning (MAJOR.MINOR.PATCH)
- Comprehensive metadata tracking
- Version comparison and promotion logic
- Model lineage tracking
- JSON-based persistence

**Usage**:

```python
from ml.model_versioning import create_model_version, ModelVersionManager

# Create version
version = create_model_version(
    version_string="1.0.0",
    metrics={"accuracy": 0.92, "f1_score": 0.91},
    model_path="ml/models/model_v1.0.0.pkl",
    framework="scikit-learn",
    stage="Production"
)

# Manage versions
manager = ModelVersionManager()
manager.register_version(version)

# Check promotion
should_promote, reason = manager.should_promote(
    new_version=version,
    current_version=prod_version,
    metric_name="f1_score",
    improvement_threshold=0.01
)
```

**Key Classes**:

- `ModelVersion`: Semantic version dataclass
- `ModelMetadata`: Comprehensive model information
- `ModelMetrics`: Validated performance metrics
- `ModelVersionManager`: Version lifecycle management
- `ModelStage`: Enum (Development, Staging, Production, Archived, Failed)
- `ModelFramework`: Enum (scikit-learn, tensorflow, pytorch, etc.)

---

### 3. Monitoring (`monitoring.py`)

**Purpose**: Real-time model monitoring and performance tracking

**Key Features**:

- Prediction logging (daily JSONL files)
- Performance tracking with trend analysis
- Data drift detection (Evidently + KS fallback)
- Model health checks
- Prometheus metrics integration

**Usage**:

```python
from ml.monitoring import PredictionLogger, ModelMonitor

# Log predictions
logger = PredictionLogger()
logger.log_prediction(
    model_name="future-skills-model",
    model_version="1.0.0",
    features={"job_role": "Data Scientist"},
    prediction="HIGH",
    probability=0.95
)

# Monitor model
monitor = ModelMonitor(model_name="future-skills-model")
monitor.set_reference_data(training_data)

# Check for drift
drift_detected, report = monitor.detect_data_drift(current_data)

# Check health
health = monitor.check_model_health()
print(f"Status: {health['status']}")
```

**Key Classes**:

- `PredictionLogger`: Buffered prediction logging
- `PredictionLog`: Prediction data structure
- `ModelMonitor`: Performance and drift monitoring

**Prometheus Metrics**:

- `ml_predictions_total`: Total predictions counter
- `ml_prediction_latency_seconds`: Latency histogram
- `ml_model_accuracy`: Accuracy gauge
- `ml_drift_detections_total`: Drift counter
- `ml_prediction_errors_total`: Error counter

---

## Integration with Training Service

The training service (`future_skills/services/training_service.py`) is fully integrated with ML infrastructure:

```python
from future_skills.services.training_service import ModelTrainer

# Create trainer
trainer = ModelTrainer(
    dataset_path="ml/data/training_data.csv",
    test_split=0.2
)

# Load data
trainer.load_data()

# Train (automatically logs to MLflow)
metrics = trainer.train(
    n_estimators=200,
    max_depth=10
)

# Save model
trainer.save_model("ml/models/model_v1.0.0.pkl")

# Save run (creates version, auto-promotes if better)
training_run = trainer.save_training_run(
    model_version="1.0.0",
    model_path="ml/models/model_v1.0.0.pkl",
    notes="Production model",
    auto_promote=True
)
```

**What happens during training:**

1. MLflow run starts automatically
2. Hyperparameters logged to MLflow
3. Model trained and evaluated
4. Metrics logged to MLflow
5. Model artifact saved to MLflow
6. Model registered in MLflow Model Registry
7. Version created with metadata
8. Automatic promotion check (if enabled)
9. Django TrainingRun record created
10. Monitoring initialized for model

---

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start MLflow UI (Optional)

```bash
mlflow ui --port 5000
```

### 3. Train Model

```bash
python manage.py train_model \
    --dataset ml/data/training_data.csv \
    --version 1.0.0 \
    --n-estimators 200
```

### 4. View in MLflow

Open browser: http://localhost:5000

---

## Configuration

### Environment Variables

```bash
# .env file

# MLflow Configuration
MLFLOW_TRACKING_URI=http://localhost:5000
MLFLOW_ARTIFACT_LOCATION=./mlruns/artifacts
MLFLOW_BACKEND_STORE_URI=postgresql://user:pass@localhost/mlflow_db

# AWS S3 (for production artifacts)
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_DEFAULT_REGION=us-west-2
```

### Django Settings

Add to `config/settings/base.py`:

```python
# MLflow
MLFLOW_TRACKING_URI = env('MLFLOW_TRACKING_URI', default='file://mlruns')
MLFLOW_ARTIFACT_LOCATION = env('MLFLOW_ARTIFACT_LOCATION', default='mlruns/artifacts')
```

Initialize in `config/__init__.py`:

```python
from ml.mlflow_config import initialize_mlflow
initialize_mlflow()
```

---

## Monitoring Dashboard

### View Predictions

```python
from ml.monitoring import PredictionLogger

logger = PredictionLogger()
recent = logger.get_recent_predictions(limit=100)
print(f"Recent predictions: {len(recent)}")
```

### Check Model Health

```python
from ml.monitoring import ModelMonitor

monitor = ModelMonitor(model_name="future-skills-model")
health = monitor.check_model_health()

if health['status'] != 'healthy':
    print(f"Issues: {health['issues']}")
```

### Generate Report

```python
report = monitor.generate_monitoring_report()
print(json.dumps(report, indent=2))
```

### Prometheus Metrics

```bash
# Expose metrics endpoint
# Visit: http://localhost:8000/metrics

curl http://localhost:8000/metrics | grep ml_
```

---

## Model Lifecycle

```
┌──────────────┐
│ Development  │ ← Initial training
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   Staging    │ ← Testing and validation
└──────┬───────┘
       │
       │ (Promotion check)
       │
       ▼
┌──────────────┐
│  Production  │ ← Active serving
└──────┬───────┘
       │
       │ (Replaced by better model)
       │
       ▼
┌──────────────┐
│   Archived   │ ← Historical record
└──────────────┘
```

---

## Dependencies

### Core ML Libraries

- `mlflow>=2.10.0` - Experiment tracking and model registry
- `scikit-learn>=1.3.0` - ML framework
- `pandas>=2.0.0`, `numpy>=1.24.0` - Data processing
- `joblib>=1.3.0` - Model serialization

### Versioning

- `pydantic>=2.0.0` - Data validation
- `semver>=3.0.0` - Semantic versioning

### Monitoring

- `prometheus-client>=0.19.0` - Metrics collection
- `evidently>=0.4.0` - Drift detection

### Explainability (Optional)

- `shap>=0.44.0` - SHAP values
- `lime>=0.2.0.1` - LIME explanations

### Cloud Storage (Optional)

- `boto3>=1.34.0` - AWS S3
- `azure-storage-blob>=12.19.0` - Azure Blob
- `google-cloud-storage>=2.14.0` - GCS

---

## Best Practices

### 1. Always Use Semantic Versioning

```
1.0.0 - Initial production model
1.1.0 - Added new features
1.1.1 - Bug fix
2.0.0 - Major architecture change
```

### 2. Test in Staging First

```python
# Never deploy directly to production
version_obj.metadata.stage = ModelStage.STAGING

# Test thoroughly, then promote
config.transition_model_stage(
    model_name="future-skills-model",
    version="3",
    stage="Production"
)
```

### 3. Monitor Continuously

```python
# Set up automated health checks
monitor.check_model_health()

# Check for drift regularly
monitor.detect_data_drift(current_data)
```

### 4. Log Everything

```python
# Parameters, metrics, artifacts
mlflow.log_params(hyperparameters)
mlflow.log_metrics(metrics)
mlflow.log_artifacts(artifact_dir)
```

### 5. Cleanup Regularly

```python
# Archive old runs
config.cleanup_old_runs(older_than_days=90)

# Archive old versions
manager.archive_old_versions(keep_latest=5)
```

---

## Troubleshooting

### Common Issues

**MLflow Connection Failed**:

```bash
# Check if server is running
curl http://localhost:5000/health

# Restart server
mlflow ui --port 5000
```

**Database Locked (SQLite)**:

```bash
# Use PostgreSQL for production
export MLFLOW_BACKEND_STORE_URI=postgresql://user:pass@localhost/mlflow_db
```

**Permission Denied**:

```bash
# Fix permissions
chmod -R 755 mlruns/
mkdir -p mlruns/artifacts
```

**Drift Detection Fails**:

```bash
# Install evidently
pip install evidently

# System automatically falls back to KS test if unavailable
```

---

## Documentation

- **[ML System Architecture](../docs/ML_SYSTEM_ARCHITECTURE.md)** - Complete system overview
- **[MLflow Setup Guide](../docs/MLFLOW_SETUP_GUIDE.md)** - Detailed setup instructions
- **[Training Service](../future_skills/services/training_service.py)** - Training implementation

---

## Version History

| Version | Date       | Changes                                             |
| ------- | ---------- | --------------------------------------------------- |
| 1.0.0   | 2025-11-28 | Initial release with MLflow, versioning, monitoring |

---

## Support

For questions or issues:

1. Check [ML_SYSTEM_ARCHITECTURE.md](../docs/ML_SYSTEM_ARCHITECTURE.md)
2. Review [MLFLOW_SETUP_GUIDE.md](../docs/MLFLOW_SETUP_GUIDE.md)
3. Contact ML team

---

**Status**: Production Ready  
**Maintained by**: SmartHR360 ML Team  
**Last Updated**: 2025-11-28
