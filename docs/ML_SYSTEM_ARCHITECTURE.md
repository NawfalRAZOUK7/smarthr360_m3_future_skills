# ML System Architecture - MLflow, Versioning & Monitoring

**SmartHR360 Future Skills Prediction**  
**Last Updated**: 2025-11-28  
**Status**: Production Ready

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [MLflow Integration](#mlflow-integration)
4. [Model Versioning](#model-versioning)
5. [Monitoring System](#monitoring-system)
6. [Setup & Configuration](#setup--configuration)
7. [Usage Guide](#usage-guide)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)

---

## 1. Overview

SmartHR360's ML system provides a comprehensive infrastructure for managing machine learning models throughout their lifecycle:

### Key Features

- **MLflow Integration**: Experiment tracking, model registry, artifact management
- **Semantic Versioning**: Automated model versioning with metadata tracking
- **Real-time Monitoring**: Performance tracking, drift detection, prediction logging
- **Model Governance**: Stage transitions (Development → Staging → Production)
- **Reproducibility**: Full experiment tracking with parameters, metrics, and artifacts

### Technology Stack

| Component           | Technology       | Version     |
| ------------------- | ---------------- | ----------- |
| Experiment Tracking | MLflow           | 2.10+       |
| Model Versioning    | semver, pydantic | 3.0+, 2.0+  |
| Drift Detection     | Evidently        | 0.4+        |
| Metrics             | Prometheus       | 0.19+       |
| Model Framework     | scikit-learn     | 1.3+        |
| Data Processing     | pandas, numpy    | 2.0+, 1.24+ |

---

## 2. Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ML System Components                       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌────────────┐     ┌──────────────┐     ┌──────────────┐  │
│  │  Training  │────▶│    MLflow    │────▶│    Model     │  │
│  │  Service   │     │   Tracking   │     │  Registry    │  │
│  └────────────┘     └──────────────┘     └──────────────┘  │
│        │                    │                     │          │
│        │                    │                     │          │
│        ▼                    ▼                     ▼          │
│  ┌────────────┐     ┌──────────────┐     ┌──────────────┐  │
│  │  Version   │     │  Monitoring  │     │  Prediction  │  │
│  │  Manager   │     │    System    │     │    Engine    │  │
│  └────────────┘     └──────────────┘     └──────────────┘  │
│        │                    │                     │          │
│        └────────────────────┴─────────────────────┘          │
│                           │                                   │
└───────────────────────────┼───────────────────────────────────┘
                            │
                            ▼
                   ┌─────────────────┐
                   │   Django ORM    │
                   │ (TrainingRun,   │
                   │  Predictions)   │
                   └─────────────────┘
```

### Component Responsibilities

#### 1. **Training Service** (`future_skills/services/training_service.py`)

- Model training with hyperparameter tuning
- Data validation and preprocessing
- Integration with MLflow for experiment tracking
- Automatic model versioning

#### 2. **MLflow Configuration** (`ml/mlflow_config.py`)

- Tracking server setup
- Experiment management
- Model registry operations
- Artifact storage

#### 3. **Model Versioning** (`ml/model_versioning.py`)

- Semantic version management (MAJOR.MINOR.PATCH)
- Model metadata tracking
- Version comparison and promotion logic
- Model lineage tracking

#### 4. **Monitoring System** (`ml/monitoring.py`)

- Prediction logging
- Performance tracking
- Data drift detection
- Model health checks
- Prometheus metrics

#### 5. **Prediction Engine** (`future_skills/services/prediction_engine.py`)

- Production inference
- Feature engineering
- Fallback to rule-based engine
- Integration with monitoring

---

## 3. MLflow Integration

### MLflow Components

#### A. Tracking Server

MLflow tracks experiments, parameters, metrics, and artifacts.

**Configuration**:

```python
# Environment variables
MLFLOW_TRACKING_URI=http://localhost:5000
MLFLOW_ARTIFACT_LOCATION=/path/to/artifacts
MLFLOW_BACKEND_STORE_URI=sqlite:///mlruns/mlflow.db
```

**Or in Django settings.py**:

```python
# config/settings/base.py
MLFLOW_TRACKING_URI = env('MLFLOW_TRACKING_URI', default='file://mlruns')
MLFLOW_ARTIFACT_LOCATION = env('MLFLOW_ARTIFACT_LOCATION', default='mlruns/artifacts')
```

#### B. Model Registry

Centralized model versioning and staging.

**Stages**:

- **Development**: Initial training and experimentation
- **Staging**: Testing and validation
- **Production**: Active serving
- **Archived**: Deprecated versions

#### C. Experiments

Organized tracking of training runs:

| Experiment                 | Purpose                                  |
| -------------------------- | ---------------------------------------- |
| `future-skills-prediction` | Default experiment for predictions       |
| `model-training`           | Model training and hyperparameter tuning |
| `model-evaluation`         | Model evaluation and validation          |
| `production-monitoring`    | Production model monitoring              |

### MLflow API Usage

#### Initialize MLflow

```python
from ml.mlflow_config import get_mlflow_config

# Get configuration
config = get_mlflow_config()
config.setup()
```

#### Start Tracking Run

```python
with config.start_run(run_name="training_v1.0.0") as run:
    # Log parameters
    mlflow.log_param("n_estimators", 100)
    mlflow.log_param("max_depth", 10)

    # Train model
    model.fit(X_train, y_train)

    # Log metrics
    accuracy = model.score(X_test, y_test)
    mlflow.log_metric("accuracy", accuracy)
    mlflow.log_metric("f1_score", f1)

    # Log model
    mlflow.sklearn.log_model(model, "model")
```

#### Register Model

```python
# Register model in registry
model_uri = f"runs:/{run.info.run_id}/model"
config.register_model(
    model_uri=model_uri,
    model_name="future-skills-model",
    tags={"version": "1.0.0", "framework": "scikit-learn"},
    description="Future skills prediction model"
)
```

#### Transition Model Stage

```python
# Promote to production
config.transition_model_stage(
    model_name="future-skills-model",
    version="3",
    stage="Production",
    archive_existing=True
)
```

#### Load Production Model

```python
# Load latest production model
model_uri = config.get_production_model_uri()
model = mlflow.sklearn.load_model(model_uri)
```

---

## 4. Model Versioning

### Semantic Versioning

Version format: **MAJOR.MINOR.PATCH**

- **MAJOR**: Breaking changes, architecture changes
- **MINOR**: New features, improvements (backward-compatible)
- **PATCH**: Bug fixes, small improvements

**Example versions**:

- `1.0.0` - Initial production model
- `1.1.0` - Added new features
- `1.1.1` - Bug fix
- `2.0.0` - Major architecture change

### Version Management

#### Create Version

```python
from ml.model_versioning import create_model_version

version = create_model_version(
    version_string="1.0.0",
    metrics={
        "accuracy": 0.92,
        "precision": 0.91,
        "recall": 0.90,
        "f1_score": 0.905
    },
    model_path="ml/models/model_v1.0.0.pkl",
    framework="scikit-learn",
    algorithm="RandomForestClassifier",
    hyperparameters={
        "n_estimators": 100,
        "max_depth": 10,
        "random_state": 42
    },
    stage="Production"
)
```

#### Version Manager

```python
from ml.model_versioning import ModelVersionManager

manager = ModelVersionManager()

# Register version
manager.register_version(version)

# Get latest version
latest = manager.get_latest_version()
print(f"Latest version: {latest}")

# Get production version
prod_version = manager.get_production_version()

# Check if should promote
should_promote, reason = manager.should_promote(
    new_version=new_version,
    current_version=prod_version,
    metric_name="accuracy",
    improvement_threshold=0.01  # 1% improvement required
)

if should_promote:
    print(f"Promote model: {reason}")
```

#### Auto-versioning

```python
# Automatically bump version
new_version = manager.auto_version(change_type="minor")
print(f"New version: {new_version}")  # e.g., 1.1.0
```

### Model Metadata

Comprehensive metadata tracked for each version:

```python
metadata = {
    "model_id": "model_1.0.0",
    "version_string": "1.0.0",
    "framework": "scikit-learn",
    "algorithm": "RandomForestClassifier",
    "model_path": "/path/to/model.pkl",
    "model_size_mb": 12.5,
    "training_dataset_size": 10000,
    "training_features": ["experience", "skill_level", ...],
    "target_classes": ["LOW", "MEDIUM", "HIGH"],
    "hyperparameters": {...},
    "metrics": {
        "accuracy": 0.92,
        "precision": 0.91,
        "recall": 0.90,
        "f1_score": 0.905,
        "training_time": 45.2,
        "inference_time": 2.1
    },
    "created_at": "2025-11-28T10:00:00",
    "stage": "Production",
    "parent_version": "0.9.5",
    "mlflow_run_id": "abc123...",
}
```

---

## 5. Monitoring System

### Components

#### A. Prediction Logging

Every prediction is logged for analysis:

```python
from ml.monitoring import PredictionLogger

logger = PredictionLogger()

logger.log_prediction(
    model_name="future-skills-model",
    model_version="1.0.0",
    features={
        "job_role": "Data Scientist",
        "skill": "Python",
        "experience": 5
    },
    prediction="HIGH",
    probability=0.95,
    prediction_time_ms=15.3,
    user_id="user123"
)
```

#### B. Performance Tracking

Track model performance over time:

```python
from ml.monitoring import ModelMonitor

monitor = ModelMonitor(model_name="future-skills-model")

# Track performance
monitor.track_model_performance(
    y_true=actual_labels,
    y_pred=predictions,
    metrics={
        "accuracy": 0.92,
        "f1_score": 0.91
    }
)

# Get recent metrics
metrics = monitor.get_performance_metrics(window_size=100)
print(f"Average accuracy: {metrics['average']['accuracy']:.3f}")
```

#### C. Drift Detection

Detect data drift between training and production data:

```python
# Set reference data (training data)
monitor.set_reference_data(training_data)

# Check for drift in production data
drift_detected, drift_report = monitor.detect_data_drift(production_data)

if drift_detected:
    print(f"Drift detected! {drift_report['drifted_features']} features drifted")
    # Trigger retraining
```

#### D. Model Health Checks

Automated health monitoring:

```python
health = monitor.check_model_health()

print(f"Status: {health['status']}")
if health['issues']:
    print("Issues:")
    for issue in health['issues']:
        print(f"  - {issue}")
```

**Health checks include**:

- Performance degradation
- Accuracy decline
- High prediction latency
- Error rate spikes

#### E. Prometheus Metrics

Real-time metrics exposed for Prometheus:

```python
# Metrics automatically collected
- ml_predictions_total{model_name, model_version, prediction_class}
- ml_prediction_latency_seconds{model_name, model_version}
- ml_model_accuracy{model_name, model_version}
- ml_drift_detections_total{model_name, drift_type}
- ml_prediction_errors_total{model_name, error_type}
```

### Monitoring Dashboard

**Generate monitoring report**:

```python
report = monitor.generate_monitoring_report()

print(json.dumps(report, indent=2))
# Output:
# {
#   "model_name": "future-skills-model",
#   "model_version": "1.0.0",
#   "health": {"status": "healthy", "issues": []},
#   "performance": {
#     "average": {"accuracy": 0.92, "f1_score": 0.91},
#     "trend": {"accuracy": {"direction": "stable"}}
#   },
#   "prediction_stats": {
#     "total_predictions": 15000,
#     "avg_prediction_time_ms": 12.5,
#     "p95_prediction_time_ms": 25.0
#   }
# }
```

---

## 6. Setup & Configuration

### Installation

#### 1. Install Dependencies

```bash
# Core dependencies
pip install -r requirements.txt

# ML-specific dependencies (optional, for development)
pip install -r ml/requirements.txt
```

#### 2. Configure Environment

Create `.env` file:

```bash
# MLflow Configuration
MLFLOW_TRACKING_URI=http://localhost:5000
MLFLOW_ARTIFACT_LOCATION=/path/to/artifacts
MLFLOW_BACKEND_STORE_URI=sqlite:///mlruns/mlflow.db

# Optional: Remote tracking server
# MLFLOW_TRACKING_URI=https://mlflow.example.com
# MLFLOW_TRACKING_USERNAME=user
# MLFLOW_TRACKING_PASSWORD=pass
```

#### 3. Initialize MLflow

**Option A: Local File-based Tracking**

```bash
# Default - uses local file system
# No additional setup needed
```

**Option B: MLflow Tracking Server**

```bash
# Start MLflow server
mlflow server \
    --backend-store-uri sqlite:///mlruns/mlflow.db \
    --default-artifact-root ./mlruns/artifacts \
    --host 0.0.0.0 \
    --port 5000
```

**Option C: Remote Tracking Server**

```bash
# Use hosted MLflow (Databricks, AWS, etc.)
export MLFLOW_TRACKING_URI=https://your-mlflow-server.com
```

#### 4. Initialize in Django

Add to `config/__init__.py`:

```python
from ml.mlflow_config import initialize_mlflow

# Initialize MLflow on startup
initialize_mlflow()
```

### Database Setup

MLflow requires a backend database for tracking.

**SQLite** (Development):

```bash
# Automatic - created in mlruns/mlflow.db
```

**PostgreSQL** (Production):

```bash
# Set in environment
export MLFLOW_BACKEND_STORE_URI=postgresql://user:pass@localhost/mlflow

# Or in settings
MLFLOW_BACKEND_STORE_URI=postgresql://user:pass@localhost/mlflow
```

### Storage Configuration

#### Local Storage

```python
MLFLOW_ARTIFACT_LOCATION=/path/to/mlruns/artifacts
```

#### Cloud Storage (Production)

**AWS S3**:

```python
MLFLOW_ARTIFACT_LOCATION=s3://my-bucket/mlflow-artifacts
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
```

**Azure Blob**:

```python
MLFLOW_ARTIFACT_LOCATION=wasbs://container@account.blob.core.windows.net/mlflow
AZURE_STORAGE_CONNECTION_STRING=your-connection-string
```

**Google Cloud Storage**:

```python
MLFLOW_ARTIFACT_LOCATION=gs://my-bucket/mlflow-artifacts
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
```

---

## 7. Usage Guide

### Training Workflow

#### Complete Training Example

```python
from future_skills.services.training_service import ModelTrainer
from ml.mlflow_config import get_mlflow_config
from ml.model_versioning import create_model_version, ModelVersionManager

# 1. Initialize MLflow
config = get_mlflow_config()

# 2. Create trainer
trainer = ModelTrainer(
    dataset_path="ml/data/training_data.csv",
    test_split=0.2
)

# 3. Load and validate data
trainer.load_data()

# 4. Train with MLflow tracking
with config.start_run(run_name="training_v1.0.0", experiment_name="model-training"):
    # Train model
    metrics = trainer.train(
        n_estimators=100,
        max_depth=10,
        random_state=42
    )

    # MLflow auto-logs parameters and metrics
    # (integrated in trainer)

    # Save model
    model_path = "ml/models/model_v1.0.0.pkl"
    trainer.save_model(model_path)

    # Log model to MLflow
    mlflow.sklearn.log_model(trainer.model, "model")

    # Get run ID
    run_id = mlflow.active_run().info.run_id

# 5. Register model
model_uri = f"runs:/{run_id}/model"
mlflow_version = config.register_model(
    model_uri=model_uri,
    model_name="future-skills-model",
    description="Future skills prediction model v1.0.0"
)

# 6. Create version metadata
version = create_model_version(
    version_string="1.0.0",
    metrics=metrics,
    model_path=model_path,
    framework="scikit-learn",
    algorithm="RandomForestClassifier",
    mlflow_run_id=run_id,
    stage="Staging"
)

# 7. Register in version manager
manager = ModelVersionManager()
manager.register_version(version)

# 8. Promote to production if better
should_promote, reason = manager.should_promote(version)
if should_promote:
    config.transition_model_stage(
        model_name="future-skills-model",
        version=mlflow_version.version,
        stage="Production"
    )
    print(f"Promoted to production: {reason}")
```

### Prediction Workflow

```python
from future_skills.services.prediction_engine import PredictionEngine
from ml.monitoring import PredictionLogger, ModelMonitor

# 1. Initialize
engine = PredictionEngine()
logger = PredictionLogger()
monitor = ModelMonitor(model_name="future-skills-model")

# 2. Make prediction
import time
start = time.time()

score, level, rationale, explanation = engine.predict(
    job_role_id=1,
    skill_id=5,
    horizon_years=5
)

prediction_time_ms = (time.time() - start) * 1000

# 3. Log prediction
logger.log_prediction(
    model_name="future-skills-model",
    model_version="1.0.0",
    features={
        "job_role_id": 1,
        "skill_id": 5,
        "horizon_years": 5
    },
    prediction=level,
    probability=score / 100.0,
    prediction_time_ms=prediction_time_ms
)

# 4. Periodically check model health
health = monitor.check_model_health()
if health['status'] != 'healthy':
    # Alert or trigger retraining
    print(f"Model health issue: {health['issues']}")
```

### Monitoring Workflow

```python
from ml.monitoring import ModelMonitor
from datetime import datetime, timedelta

# Initialize monitor
monitor = ModelMonitor(model_name="future-skills-model")

# Load reference data for drift detection
training_data = pd.read_csv("ml/data/training_data.csv")
monitor.set_reference_data(training_data)

# Check for drift daily
production_data = get_recent_predictions_data()  # Your function
drift_detected, drift_report = monitor.detect_data_drift(production_data)

if drift_detected:
    # Trigger alert
    send_alert(f"Data drift detected: {drift_report}")

    # Trigger retraining
    trigger_retraining_job()

# Generate weekly report
report = monitor.generate_monitoring_report()
save_report(report)
```

---

## 8. Best Practices

### Training

1. **Always use MLflow tracking** for experiments
2. **Tag runs appropriately** with metadata
3. **Log all hyperparameters** for reproducibility
4. **Use consistent naming** for experiments and runs
5. **Version datasets** alongside models
6. **Document model changes** in descriptions

### Versioning

1. **Follow semantic versioning** strictly
2. **Increment MAJOR** for breaking changes
3. **Increment MINOR** for improvements
4. **Increment PATCH** for bug fixes
5. **Use prereleases** (alpha, beta, rc) for testing
6. **Archive old versions** after promotion

### Monitoring

1. **Set up drift detection** for production models
2. **Monitor key metrics** continuously
3. **Define alert thresholds** for health checks
4. **Log all predictions** for analysis
5. **Review monitoring reports** weekly
6. **Establish retraining triggers**

### Model Promotion

1. **Test in Staging** before Production
2. **Require minimum improvement** for promotion
3. **Archive existing Production** models
4. **Document promotion decisions**
5. **Have rollback plan** ready
6. **A/B test** when possible

---

## 9. Troubleshooting

### Common Issues

#### MLflow Connection Issues

**Problem**: Cannot connect to MLflow tracking server

**Solution**:

```bash
# Check tracking URI
echo $MLFLOW_TRACKING_URI

# Test connection
mlflow ui --backend-store-uri sqlite:///mlruns/mlflow.db

# Verify server is running
curl http://localhost:5000/health
```

#### Model Registration Fails

**Problem**: Model registration fails with permission error

**Solution**:

```python
# Ensure artifact location is writable
import os
artifact_path = "/path/to/artifacts"
os.makedirs(artifact_path, exist_ok=True)

# Check permissions
os.access(artifact_path, os.W_OK)  # Should return True
```

#### Drift Detection Not Working

**Problem**: Evidently not available or errors

**Solution**:

```bash
# Install evidently
pip install evidently

# If still issues, use basic drift detection
# (automatically falls back)
```

#### High Prediction Latency

**Problem**: Predictions taking too long

**Solutions**:

- Cache model in memory
- Use smaller model
- Optimize feature engineering
- Profile code for bottlenecks

```python
# Profile prediction
import cProfile
cProfile.run('engine.predict(...)')
```

#### Memory Issues

**Problem**: Out of memory during training

**Solutions**:

- Reduce batch size
- Use incremental learning
- Sample data for development
- Increase system memory

---

## Quick Reference

### MLflow Commands

```bash
# Start UI
mlflow ui

# Start server
mlflow server --host 0.0.0.0 --port 5000

# View experiments
mlflow experiments list

# View runs
mlflow runs list --experiment-name "model-training"

# Search runs
mlflow runs search --filter "metrics.accuracy > 0.9"
```

### Python API

```python
# Initialize
from ml.mlflow_config import get_mlflow_config
config = get_mlflow_config()

# Start run
with config.start_run(run_name="experiment"):
    mlflow.log_param("param", value)
    mlflow.log_metric("metric", value)

# Register model
config.register_model(model_uri, model_name)

# Transition stage
config.transition_model_stage(model_name, version, "Production")
```

### Monitoring

```python
# Check health
monitor.check_model_health()

# Detect drift
monitor.detect_data_drift(current_data)

# Generate report
monitor.generate_monitoring_report()
```

---

## Resources

- **MLflow Documentation**: https://mlflow.org/docs/latest/
- **Evidently Documentation**: https://docs.evidentlyai.com/
- **Semantic Versioning**: https://semver.org/
- **Prometheus Client**: https://prometheus.io/docs/

---

**Last Updated**: 2025-11-28  
**Version**: 1.0.0  
**Status**: Production Ready  
**Maintained by**: SmartHR360 ML Team
