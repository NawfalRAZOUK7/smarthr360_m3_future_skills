# 🚀 ML System Quick Start Guide

**Get started with MLflow tracking in 5 minutes!**

---

## Prerequisites

- Python 3.8+ installed
- Virtual environment activated
- SmartHR360 project cloned

---

## Option 1: Automated Setup (Recommended)

```bash
# Run the setup script
./scripts/setup_mlflow.sh
```

That's it! The script will:

- ✅ Install all ML dependencies
- ✅ Create directory structure
- ✅ Setup configuration
- ✅ Verify installation

---

## Option 2: Manual Setup

### Step 1: Install Dependencies (2 minutes)

```bash
# Install core ML dependencies
pip install mlflow>=2.10.0 \
    scikit-learn>=1.3.0 \
    pydantic>=2.0.0 \
    semver>=3.0.0 \
    prometheus-client>=0.19.0 \
    pandas>=2.0.0 \
    numpy>=1.24.0

# Optional: Install monitoring and explainability
pip install evidently>=0.4.0 shap>=0.44.0
```

### Step 2: Create Directory Structure (30 seconds)

```bash
mkdir -p ml/{data,models,versions,logs/predictions}
mkdir -p mlruns/artifacts
```

### Step 3: Configure Environment (1 minute)

Create/update `.env` file:

```bash
# Add these lines to your .env
MLFLOW_TRACKING_URI=file://mlruns
MLFLOW_ARTIFACT_LOCATION=mlruns/artifacts
```

### Step 4: Verify Installation (30 seconds)

```bash
python -c "
import mlflow
from ml.mlflow_config import get_mlflow_config
print('✅ MLflow installed:', mlflow.__version__)
config = get_mlflow_config()
print('✅ Configuration loaded successfully')
"
```

---

## Quick Test: Train Your First Model

### 1. Prepare Training Data

```bash
# Ensure you have training data
ls artifacts/datasets/training_data.csv

# If not, create sample data or export from database
python manage.py export_future_skills_dataset --output artifacts/datasets/training_data.csv
```

### 2. Train Model (Command Line)

```bash
# Train model with MLflow tracking
python manage.py train_model \
    --dataset artifacts/datasets/training_data.csv \
    --version 1.0.0 \
    --n-estimators 200 \
    --max-depth 10
```

### 3. Train Model (Python)

```python
from future_skills.services.training_service import ModelTrainer

# Initialize trainer
trainer = ModelTrainer(
    dataset_path="artifacts/datasets/training_data.csv",
    test_split=0.2
)

# Load data
print("Loading data...")
trainer.load_data()
print(f"✅ Loaded {len(trainer.df)} samples")

# Train model (auto-logs to MLflow)
print("\nTraining model...")
metrics = trainer.train(
    n_estimators=200,
    max_depth=10,
    random_state=42
)

print(f"""
✅ Training completed!
   Accuracy:  {metrics['accuracy']:.3f}
   Precision: {metrics['precision']:.3f}
   Recall:    {metrics['recall']:.3f}
   F1 Score:  {metrics['f1_score']:.3f}
""")

# Save model
model_path = "artifacts/models/model_v1.0.0.pkl"
trainer.save_model(model_path)
print(f"✅ Model saved to {model_path}")

# Save training run (creates version, auto-promotes)
training_run = trainer.save_training_run(
    model_version="1.0.0",
    model_path=model_path,
    notes="First production model",
    auto_promote=True
)

print(f"""
✅ Training run saved!
   Run ID:       {training_run.id}
   MLflow ID:    {trainer.mlflow_run_id}
   Status:       {training_run.status}
""")
```

### 4. View in MLflow UI

```bash
# Start MLflow UI
mlflow ui --port 5000

# Open browser: http://localhost:5000
```

You should see:

- ✅ Your training run in "model-training" experiment
- ✅ Logged parameters (n_estimators, max_depth, etc.)
- ✅ Logged metrics (accuracy, precision, recall, f1_score)
- ✅ Model artifact stored
- ✅ Model registered in Model Registry

---

## Verify Everything Works

### Check MLflow Tracking

```python
from ml.mlflow_config import get_mlflow_config

config = get_mlflow_config()

# Search recent runs
runs = config.search_runs(
    experiment_names=["model-training"],
    order_by=["start_time DESC"],
    max_results=5
)

for run in runs:
    print(f"Run: {run.info.run_id[:8]}...")
    print(f"  Accuracy: {run.data.metrics.get('accuracy', 'N/A'):.3f}")
    print(f"  F1 Score: {run.data.metrics.get('f1_score', 'N/A'):.3f}")
```

### Check Model Versioning

```python
from ml.model_versioning import ModelVersionManager

manager = ModelVersionManager()

# Get latest version
latest = manager.get_latest_version()
print(f"Latest version: {latest}")

# Get production version
prod = manager.get_production_version()
if prod:
    print(f"Production version: {prod.version_string}")
    print(f"  Accuracy: {prod.metadata.metrics.accuracy:.3f}")
    print(f"  F1 Score: {prod.metadata.metrics.f1_score:.3f}")
else:
    print("No production model yet")
```

### Check Monitoring

```python
from ml.monitoring import ModelMonitor

monitor = ModelMonitor(model_name="future-skills-model")

# Check health
health = monitor.check_model_health()
print(f"Model health: {health['status']}")

if health['issues']:
    print("Issues detected:")
    for issue in health['issues']:
        print(f"  - {issue}")
```

---

## Common Commands

### Start MLflow UI

```bash
mlflow ui --port 5000
# Visit: http://localhost:5000
```

### List Experiments

```bash
mlflow experiments list
```

### Search Runs

```bash
mlflow runs search --experiment-name "model-training"
```

### View Model Registry

```bash
# Open MLflow UI and go to "Models" tab
# Or use Python API:
python -c "
from ml.mlflow_config import get_mlflow_client
client = get_mlflow_client()
models = client.search_registered_models()
for model in models:
    print(f'Model: {model.name}')
    for version in model.latest_versions:
        print(f'  Version {version.version} - {version.current_stage}')
"
```

---

## Production Setup

### Use PostgreSQL Backend

```bash
# 1. Create database
createdb mlflow_db

# 2. Update .env
echo "MLFLOW_BACKEND_STORE_URI=postgresql://user:pass@localhost/mlflow_db" >> .env

# 3. Start server
mlflow server \
    --backend-store-uri postgresql://user:pass@localhost/mlflow_db \
    --default-artifact-root ./mlruns/artifacts \
    --host 0.0.0.0 \
    --port 5000
```

### Use S3 for Artifacts

```bash
# 1. Install AWS CLI
pip install boto3

# 2. Configure AWS
aws configure

# 3. Update .env
echo "MLFLOW_ARTIFACT_LOCATION=s3://your-bucket/mlflow-artifacts" >> .env
echo "AWS_ACCESS_KEY_ID=your_key" >> .env
echo "AWS_SECRET_ACCESS_KEY=your_secret" >> .env
```

---

## Troubleshooting

### Import Error: No module named 'mlflow'

```bash
pip install mlflow>=2.10.0
```

### MLflow UI won't start

```bash
# Check if port is already in use
lsof -i :5000

# Use different port
mlflow ui --port 5001
```

### Database locked (SQLite)

```bash
# Use PostgreSQL for production
export MLFLOW_BACKEND_STORE_URI=postgresql://user:pass@localhost/mlflow_db
```

### Permission denied on mlruns/

```bash
chmod -R 755 mlruns/
mkdir -p mlruns/artifacts
```

---

## Next Steps

1. ✅ **Train your first model** (see above)
2. 📚 **Read the documentation**:
   - [ML System Architecture](./ML_SYSTEM_ARCHITECTURE.md) - Complete overview
   - [MLflow Setup Guide](./MLFLOW_SETUP_GUIDE.md) - Detailed setup
   - [Implementation Summary](./ML_IMPLEMENTATION_SUMMARY.md) - Technical details
3. 🧪 **Experiment with different hyperparameters**
4. 📊 **Setup monitoring dashboards** (Prometheus + Grafana)
5. 🚀 **Deploy to production**

---

## Useful Resources

- **MLflow Docs**: https://mlflow.org/docs/latest/
- **SmartHR360 ML Docs**: [docs/ML_SYSTEM_ARCHITECTURE.md](./ML_SYSTEM_ARCHITECTURE.md)
- **Quick Reference**: [ml/README.md](../ml/README.md)

---

## Support

For questions or issues:

1. Check [ML System Architecture](./ML_SYSTEM_ARCHITECTURE.md) documentation
2. Review [Troubleshooting](./MLFLOW_SETUP_GUIDE.md#troubleshooting) section
3. Check MLflow UI for run details: http://localhost:5000

---

**Ready to train your first model? Run the setup script and you're good to go!** 🚀

```bash
./scripts/setup_mlflow.sh
```
