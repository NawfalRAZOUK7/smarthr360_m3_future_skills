# ML System Features (Add to README.md)

## 🤖 ML System Architecture

SmartHR360 now includes a comprehensive ML Operations (MLOps) infrastructure for managing the complete lifecycle of machine learning models.

### Key Features

#### 🔬 **Experiment Tracking with MLflow**

- Automatic tracking of training runs
- Parameter and metric logging
- Model artifact storage
- Run comparison and search
- 4 organized experiments (prediction, training, evaluation, monitoring)

#### 📦 **Model Versioning**

- Semantic versioning (MAJOR.MINOR.PATCH)
- Comprehensive metadata tracking
- Automatic promotion logic
- Model lifecycle stages (Development → Staging → Production → Archived)
- Version comparison and lineage tracking

#### 📊 **Real-time Monitoring**

- Prediction logging with daily JSONL files
- Performance tracking with trend analysis
- Data drift detection (Evidently)
- Model health checks
- Prometheus metrics integration

#### 🔄 **Model Registry**

- Centralized model management
- Stage transitions (Staging/Production)
- Production model retrieval
- Version management
- Model URI resolution

### Quick Setup

```bash
# 1. Run setup script
./scripts/setup_mlflow.sh

# 2. Start MLflow UI (optional)
mlflow ui --port 5000

# 3. Train first model
python manage.py train_model \
    --dataset artifacts/datasets/training_data.csv \
    --version 1.0.0 \
    --n-estimators 200

# 4. View in MLflow UI
# Visit: http://localhost:5000
```

### Training Workflow

```python
from future_skills.services.training_service import ModelTrainer

# Create trainer
trainer = ModelTrainer(
    dataset_path="artifacts/datasets/training_data.csv",
    test_split=0.2
)

# Load data
trainer.load_data()

# Train (auto-logs to MLflow)
metrics = trainer.train(
    n_estimators=200,
    max_depth=10,
    random_state=42
)

# Save model
trainer.save_model("artifacts/models/model_v1.0.0.pkl")

# Save run (creates version, auto-promotes if better)
training_run = trainer.save_training_run(
    model_version="1.0.0",
    model_path="artifacts/models/model_v1.0.0.pkl",
    notes="Production model",
    auto_promote=True
)
```

### Documentation

- **[ML System Architecture](docs/ML_SYSTEM_ARCHITECTURE.md)** - Complete system overview, architecture diagrams, API reference
- **[MLflow Setup Guide](docs/MLFLOW_SETUP_GUIDE.md)** - Detailed setup for local and production environments
- **[ML Components README](ml/README.md)** - Quick reference for ML components
- **[Implementation Summary](docs/ML_IMPLEMENTATION_SUMMARY.md)** - Complete implementation details

### ML Dependencies

Core ML libraries:

- `mlflow>=2.10.0` - Experiment tracking and model registry
- `scikit-learn>=1.3.0` - ML framework
- `pydantic>=2.0.0` - Data validation
- `semver>=3.0.0` - Semantic versioning
- `prometheus-client>=0.19.0` - Metrics collection
- `evidently>=0.4.0` - Drift detection

For complete list, see [ml/requirements.txt](ml/requirements.txt)

### Configuration

Add to `.env`:

```bash
# MLflow Configuration
MLFLOW_TRACKING_URI=http://localhost:5000
MLFLOW_ARTIFACT_LOCATION=./mlruns/artifacts

# Optional: PostgreSQL backend
MLFLOW_BACKEND_STORE_URI=postgresql://user:pass@localhost/mlflow_db

# Optional: S3 artifacts
MLFLOW_ARTIFACT_LOCATION=s3://your-bucket/mlflow-artifacts
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
```

### Monitoring

```python
from ml.monitoring import ModelMonitor

# Initialize monitor
monitor = ModelMonitor(model_name="future-skills-model")

# Check health
health = monitor.check_model_health()
print(f"Status: {health['status']}")

# Detect drift
monitor.set_reference_data(training_data)
drift_detected, report = monitor.detect_data_drift(production_data)

# Generate report
report = monitor.generate_monitoring_report()
```

### MLflow UI

Start the MLflow tracking UI:

```bash
mlflow ui --port 5000
```

Visit: http://localhost:5000

View:

- Experiments and runs
- Metrics and parameters
- Model registry
- Artifact storage

### Production Setup

For production deployment with PostgreSQL and S3:

```bash
# Start MLflow server
mlflow server \
    --backend-store-uri postgresql://user:pass@localhost/mlflow_db \
    --default-artifact-root s3://your-bucket/mlflow-artifacts \
    --host 0.0.0.0 \
    --port 5000
```

See [MLflow Setup Guide](docs/MLFLOW_SETUP_GUIDE.md) for complete production setup instructions.

---

**Add this section to your README.md after the "Configuration" section**
