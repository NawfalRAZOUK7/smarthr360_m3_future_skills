# MLflow Setup Guide

**SmartHR360 Future Skills - ML Operations**  
**Version**: 1.0.0  
**Last Updated**: 2025-11-28

---

## Table of Contents

1. [Overview](#overview)
2. [Local Development Setup](#local-development-setup)
3. [Production Setup](#production-setup)
4. [Configuration](#configuration)
5. [Usage Examples](#usage-examples)
6. [Troubleshooting](#troubleshooting)

---

## 1. Overview

MLflow provides:

- **Experiment Tracking**: Log parameters, metrics, and artifacts
- **Model Registry**: Version and stage models (Staging, Production)
- **Artifact Storage**: Store models, plots, and data
- **Run Comparison**: Compare experiments and find best models

---

## 2. Local Development Setup

### Quick Start (File-based Tracking)

**Step 1: Install Dependencies**

```bash
pip install -r requirements.txt
```

**Step 2: Run Django Application**

```bash
python manage.py runserver
```

**Step 3: View MLflow UI**

```bash
mlflow ui
```

Visit: http://localhost:5000

**That's it!** By default, SmartHR360 uses file-based tracking with artifacts stored in `./mlruns/`.

---

### Advanced: Local Tracking Server

For better performance and PostgreSQL backend:

**Step 1: Install PostgreSQL** (if not installed)

```bash
# macOS
brew install postgresql
brew services start postgresql

# Ubuntu
sudo apt-get install postgresql postgresql-contrib
sudo service postgresql start

# Windows (use installer from postgresql.org)
```

**Step 2: Create MLflow Database**

```bash
# Create database
createdb mlflow_db

# Or with psql
psql -U postgres
CREATE DATABASE mlflow_db;
\q
```

**Step 3: Configure Environment**

Create `.env` file:

```bash
# MLflow Tracking
MLFLOW_TRACKING_URI=http://localhost:5000
MLFLOW_BACKEND_STORE_URI=postgresql://username:password@localhost/mlflow_db
MLFLOW_ARTIFACT_LOCATION=/path/to/mlruns/artifacts

# Example with actual values
MLFLOW_TRACKING_URI=http://localhost:5000
MLFLOW_BACKEND_STORE_URI=postgresql://postgres:postgres@localhost/mlflow_db
MLFLOW_ARTIFACT_LOCATION=/Users/yourname/smarthr360/mlruns/artifacts
```

**Step 4: Start MLflow Server**

```bash
mlflow server \
    --backend-store-uri postgresql://postgres:postgres@localhost/mlflow_db \
    --default-artifact-root ./mlruns/artifacts \
    --host 0.0.0.0 \
    --port 5000
```

**Step 5: Run Django Application**

```bash
# In another terminal
python manage.py runserver
```

**Step 6: Train Model**

```bash
# Train and track with MLflow
python manage.py train_model \
    --dataset artifacts/datasets/training_data.csv \
    --version 1.0.0 \
    --n-estimators 200
```

---

## 3. Production Setup

### Option A: Self-Hosted MLflow Server

**Architecture**:

```
┌─────────────┐      ┌──────────────┐      ┌──────────────┐
│   Django    │─────▶│    MLflow    │─────▶│  PostgreSQL  │
│   App       │      │    Server    │      │  (Metadata)  │
└─────────────┘      └──────────────┘      └──────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │   S3/Azure   │
                     │  (Artifacts) │
                     └──────────────┘
```

**Step 1: Setup PostgreSQL**

```bash
# Install PostgreSQL on production server
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib

# Create production database
sudo -u postgres createdb mlflow_production
sudo -u postgres createuser mlflow_user
sudo -u postgres psql
  ALTER USER mlflow_user WITH PASSWORD 'your_secure_password';
  GRANT ALL PRIVILEGES ON DATABASE mlflow_production TO mlflow_user;
  \q
```

**Step 2: Setup Artifact Storage (AWS S3)**

```bash
# Install AWS CLI
pip install awscli boto3

# Configure AWS credentials
aws configure
# Enter:
# - AWS Access Key ID
# - AWS Secret Access Key
# - Default region (e.g., us-west-2)
# - Default output format (json)

# Create S3 bucket
aws s3 mb s3://smarthr360-mlflow-artifacts --region us-west-2

# Set bucket policy (optional, for secure access)
aws s3api put-bucket-versioning \
    --bucket smarthr360-mlflow-artifacts \
    --versioning-configuration Status=Enabled
```

**Step 3: Configure MLflow Server**

Create systemd service: `/etc/systemd/system/mlflow.service`

```ini
[Unit]
Description=MLflow Tracking Server
After=network.target

[Service]
Type=simple
User=mlflow
WorkingDirectory=/opt/mlflow
Environment="AWS_ACCESS_KEY_ID=YOUR_KEY"
Environment="AWS_SECRET_ACCESS_KEY=YOUR_SECRET"
Environment="AWS_DEFAULT_REGION=us-west-2"
ExecStart=/usr/local/bin/mlflow server \
    --backend-store-uri postgresql://mlflow_user:password@localhost/mlflow_production \
    --default-artifact-root s3://smarthr360-mlflow-artifacts \
    --host 0.0.0.0 \
    --port 5000
Restart=always

[Install]
WantedBy=multi-user.target
```

**Step 4: Start Service**

```bash
# Reload systemd
sudo systemctl daemon-reload

# Start MLflow
sudo systemctl start mlflow

# Enable on boot
sudo systemctl enable mlflow

# Check status
sudo systemctl status mlflow
```

**Step 5: Setup Nginx Reverse Proxy** (Optional)

Create `/etc/nginx/sites-available/mlflow`:

```nginx
server {
    listen 80;
    server_name mlflow.yourdomain.com;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable site:

```bash
sudo ln -s /etc/nginx/sites-available/mlflow /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

**Step 6: Configure Django Application**

Production `.env`:

```bash
# MLflow Production Configuration
MLFLOW_TRACKING_URI=http://mlflow.yourdomain.com
MLFLOW_BACKEND_STORE_URI=postgresql://mlflow_user:password@localhost/mlflow_production
MLFLOW_ARTIFACT_LOCATION=s3://smarthr360-mlflow-artifacts

# AWS Credentials (if not using IAM roles)
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_DEFAULT_REGION=us-west-2
```

---

### Option B: Managed MLflow (Databricks)

**Step 1: Create Databricks Account**

- Sign up at https://databricks.com/
- Create workspace

**Step 2: Get Connection Details**

```bash
# Databricks workspace URL
DATABRICKS_HOST=https://your-workspace.cloud.databricks.com

# Personal access token (from User Settings → Access Tokens)
DATABRICKS_TOKEN=dapi...
```

**Step 3: Configure Django**

`.env` file:

```bash
MLFLOW_TRACKING_URI=databricks
DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
DATABRICKS_TOKEN=dapi...
```

**Step 4: Install Databricks CLI**

```bash
pip install databricks-cli

# Configure
databricks configure --token
# Enter host and token when prompted
```

---

### Option C: Azure ML

**Step 1: Create Azure ML Workspace**

```bash
# Install Azure CLI
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Login
az login

# Create resource group
az group create --name smarthr360-ml --location westus2

# Create ML workspace
az ml workspace create \
    --name smarthr360-mlflow \
    --resource-group smarthr360-ml \
    --location westus2
```

**Step 2: Get Tracking URI**

```bash
# Get workspace details
az ml workspace show \
    --name smarthr360-mlflow \
    --resource-group smarthr360-ml \
    --query mlflow_tracking_uri
```

**Step 3: Configure Django**

`.env`:

```bash
MLFLOW_TRACKING_URI=azureml://your-workspace-uri
AZURE_STORAGE_CONNECTION_STRING=your_connection_string
```

---

## 4. Configuration

### Environment Variables

| Variable                   | Description              | Example                                    | Required                            |
| -------------------------- | ------------------------ | ------------------------------------------ | ----------------------------------- |
| `MLFLOW_TRACKING_URI`      | Tracking server URL      | `http://localhost:5000`                    | No (defaults to file://)            |
| `MLFLOW_BACKEND_STORE_URI` | Metadata database        | `postgresql://user:pass@host/db`           | No (defaults to file-based)         |
| `MLFLOW_ARTIFACT_LOCATION` | Artifact storage         | `s3://bucket/path`                         | No (defaults to ./mlruns/artifacts) |
| `AWS_ACCESS_KEY_ID`        | AWS credentials (for S3) | `AKIAIOSFODNN7EXAMPLE`                     | If using S3                         |
| `AWS_SECRET_ACCESS_KEY`    | AWS secret               | `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` | If using S3                         |
| `AWS_DEFAULT_REGION`       | AWS region               | `us-west-2`                                | If using S3                         |

### Django Settings

Add to `config/settings/base.py`:

```python
# MLflow Configuration
MLFLOW_TRACKING_URI = env(
    'MLFLOW_TRACKING_URI',
    default='file://mlruns'
)

MLFLOW_ARTIFACT_LOCATION = env(
    'MLFLOW_ARTIFACT_LOCATION',
    default='mlruns/artifacts'
)

MLFLOW_BACKEND_STORE_URI = env(
    'MLFLOW_BACKEND_STORE_URI',
    default=None  # Uses file-based if not set
)
```

### Automatic Initialization

In `config/__init__.py`:

```python
from ml.mlflow_config import initialize_mlflow

# Initialize MLflow on Django startup
initialize_mlflow()
```

---

## 5. Usage Examples

### Training with MLflow

```python
from future_skills.services.training_service import ModelTrainer

# Create trainer
trainer = ModelTrainer(
    dataset_path="artifacts/datasets/training_data.csv",
    test_split=0.2
)

# Load data
trainer.load_data()

# Train (automatically logs to MLflow)
metrics = trainer.train(
    n_estimators=200,
    max_depth=10,
    random_state=42
)

# Save model
model_path = "artifacts/models/model_v1.0.0.pkl"
trainer.save_model(model_path)

# Save training run (creates version, promotes if better)
training_run = trainer.save_training_run(
    model_version="1.0.0",
    model_path=model_path,
    notes="Initial production model",
    auto_promote=True
)

print(f"Training run ID: {training_run.id}")
print(f"MLflow run ID: {trainer.mlflow_run_id}")
```

### View Experiments in MLflow UI

```bash
# Start UI
mlflow ui --port 5000

# Or specify backend
mlflow ui \
    --backend-store-uri postgresql://user:pass@localhost/mlflow_db \
    --port 5000
```

Open browser: http://localhost:5000

### Load Production Model

```python
from ml.mlflow_config import get_mlflow_config
import mlflow.sklearn

# Get MLflow config
config = get_mlflow_config()

# Get production model URI
model_uri = config.get_production_model_uri()

# Load model
model = mlflow.sklearn.load_model(model_uri)

# Make predictions
predictions = model.predict(X)
```

### Search Runs

```python
from ml.mlflow_config import get_mlflow_config

config = get_mlflow_config()

# Search for best runs
runs = config.search_runs(
    experiment_names=["model-training"],
    filter_string="metrics.f1_score > 0.90",
    order_by=["metrics.f1_score DESC"],
    max_results=10
)

for run in runs:
    print(f"Run ID: {run.info.run_id}")
    print(f"F1 Score: {run.data.metrics['f1_score']}")
```

### Transition Model Stages

```python
from ml.mlflow_config import get_mlflow_config

config = get_mlflow_config()

# Promote model to production
config.transition_model_stage(
    model_name="future-skills-model",
    version="3",
    stage="Production",
    archive_existing=True  # Archive current production model
)
```

---

## 6. Troubleshooting

### Issue: Cannot Connect to Tracking Server

**Symptoms**:

```
mlflow.exceptions.MlflowException: Could not connect to tracking server
```

**Solutions**:

1. Check if MLflow server is running:

   ```bash
   curl http://localhost:5000/health
   ```

2. Verify `MLFLOW_TRACKING_URI` in `.env`:

   ```bash
   echo $MLFLOW_TRACKING_URI
   ```

3. Check server logs:

   ```bash
   # If using systemd
   sudo journalctl -u mlflow -f

   # Or check MLflow server output
   ```

4. Test connection:
   ```python
   import mlflow
   mlflow.set_tracking_uri("http://localhost:5000")
   print(mlflow.get_tracking_uri())
   ```

---

### Issue: Database Connection Failed

**Symptoms**:

```
sqlalchemy.exc.OperationalError: could not connect to server
```

**Solutions**:

1. Check PostgreSQL is running:

   ```bash
   sudo service postgresql status
   ```

2. Verify database exists:

   ```bash
   psql -U postgres -l | grep mlflow
   ```

3. Test connection string:

   ```bash
   psql postgresql://user:pass@localhost/mlflow_db
   ```

4. Check credentials in `.env`

---

### Issue: Artifact Upload Failed

**Symptoms**:

```
boto3.exceptions.S3UploadFailedError: Failed to upload
```

**Solutions**:

1. Check AWS credentials:

   ```bash
   aws s3 ls s3://smarthr360-mlflow-artifacts/
   ```

2. Verify bucket exists:

   ```bash
   aws s3 mb s3://smarthr360-mlflow-artifacts
   ```

3. Check IAM permissions (S3 read/write)

4. Test with local artifacts:
   ```bash
   export MLFLOW_ARTIFACT_LOCATION=./mlruns/artifacts
   ```

---

### Issue: Permission Denied

**Symptoms**:

```
PermissionError: [Errno 13] Permission denied: './mlruns'
```

**Solutions**:

1. Check directory permissions:

   ```bash
   ls -la mlruns/
   ```

2. Create directory with correct permissions:

   ```bash
   mkdir -p mlruns/artifacts
   chmod -R 755 mlruns/
   ```

3. Run as correct user:
   ```bash
   whoami
   # Should match MLflow service user
   ```

---

### Issue: Model Not Found

**Symptoms**:

```
mlflow.exceptions.RestException: Model 'future-skills-model' not found
```

**Solutions**:

1. List registered models:

   ```python
   from ml.mlflow_config import get_mlflow_client

   client = get_mlflow_client()
   models = client.search_registered_models()
   print([m.name for m in models])
   ```

2. Register model:

   ```python
   config.register_model(
       model_uri="runs:/run_id/model",
       model_name="future-skills-model"
   )
   ```

3. Check MLflow UI: http://localhost:5000/#/models

---

### Issue: Slow Performance

**Solutions**:

1. Use PostgreSQL backend instead of SQLite:

   ```bash
   MLFLOW_BACKEND_STORE_URI=postgresql://user:pass@localhost/mlflow_db
   ```

2. Enable caching in Django:

   ```python
   # config/settings/base.py
   CACHES = {
       'default': {
           'BACKEND': 'django.core.cache.backends.redis.RedisCache',
           'LOCATION': 'redis://127.0.0.1:6379/1',
       }
   }
   ```

3. Cleanup old runs:
   ```python
   config.cleanup_old_runs(
       experiment_name="model-training",
       older_than_days=90
   )
   ```

---

## Best Practices

### 1. Use Consistent Naming

```python
# Experiments
- "model-training"
- "model-evaluation"
- "production-monitoring"

# Runs
- "training_20251128_143000"
- "evaluation_v1.0.0"

# Models
- "future-skills-model"
```

### 2. Tag Everything

```python
with config.start_run() as run:
    mlflow.set_tag("version", "1.0.0")
    mlflow.set_tag("environment", "production")
    mlflow.set_tag("author", "data-team")
    mlflow.set_tag("purpose", "initial-deployment")
```

### 3. Log Comprehensively

```python
# Parameters
mlflow.log_params({
    "n_estimators": 200,
    "max_depth": 10,
    "algorithm": "RandomForest"
})

# Metrics
mlflow.log_metrics({
    "accuracy": 0.92,
    "f1_score": 0.91,
    "training_time": 45.2
})

# Artifacts
mlflow.log_artifact("confusion_matrix.png")
mlflow.log_artifact("feature_importance.csv")
```

### 4. Use Staging Before Production

```python
# First register in Staging
version_obj.metadata.stage = ModelStage.STAGING

# Test in staging environment

# Then promote to Production
if validation_passed:
    config.transition_model_stage(
        model_name="future-skills-model",
        version="3",
        stage="Production"
    )
```

### 5. Automate Cleanup

```python
# Scheduled task (cron/celery)
@periodic_task(run_every=timedelta(days=7))
def cleanup_old_mlflow_runs():
    config = get_mlflow_config()
    config.cleanup_old_runs(older_than_days=90)
```

---

## Resources

- **MLflow Documentation**: https://mlflow.org/docs/latest/
- **MLflow GitHub**: https://github.com/mlflow/mlflow
- **Tracking API**: https://mlflow.org/docs/latest/tracking.html
- **Model Registry**: https://mlflow.org/docs/latest/model-registry.html
- **MLflow Recipes**: https://mlflow.org/docs/latest/recipes.html

---

**Questions?** Contact the ML team or refer to [ML_SYSTEM_ARCHITECTURE.md](./ML_SYSTEM_ARCHITECTURE.md)
