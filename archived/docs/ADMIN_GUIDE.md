# SmartHR360 Future Skills - Administrator Guide

**Audience:** HR Staff (DRH/Responsable RH)  
**Last Updated:** November 28, 2025  
**Version:** 1.0

---

## Table of Contents

1. [Overview](#overview)
2. [Getting Started](#getting-started)
3. [Prediction Management](#prediction-management)
4. [Model Training](#model-training)
5. [Monitoring & Analytics](#monitoring--analytics)
6. [Engine Configuration](#engine-configuration)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)
9. [API Reference](#api-reference)

---

## Overview

### What is SmartHR360 Future Skills?

SmartHR360 Future Skills is an AI-powered prediction system that helps HR teams:

- **Predict future skill demands** for all job roles in the organization
- **Generate personalized recommendations** for employee skill development
- **Identify training investment priorities** based on data-driven insights
- **Monitor skill trends** and market dynamics
- **Track prediction accuracy** and model performance

### Administrator Capabilities

As an HR Staff member, you have full access to:

✅ **Trigger prediction recalculations** for all job roles  
✅ **Train and deploy ML models** with custom hyperparameters  
✅ **Switch between ML and rules-based engines**  
✅ **Monitor prediction quality** and model performance  
✅ **Manage employees and bulk operations**  
✅ **View comprehensive analytics** and training history  
✅ **Access API documentation** and testing tools

---

## Getting Started

### Accessing the System

#### 1. Django Admin Interface

**URL:** `http://localhost:8000/admin/`

Login with your HR Staff credentials to access:

- Employee management
- Skill and job role configuration
- Prediction history
- Training run records
- Market trends and recommendations

#### 2. API Documentation (Swagger UI)

**URL:** `http://localhost:8000/api/docs/`

Interactive API documentation with:

- Try-it-out functionality
- Request/response examples
- Authentication testing
- Complete endpoint listing

#### 3. ReDoc Documentation

**URL:** `http://localhost:8000/api/redoc/`

Clean, searchable API documentation for reference.

### Understanding Your Role

**HR Staff Permissions:**

- **Full Read Access:** View all predictions, employees, trends, recommendations
- **Full Write Access:** Create/update/delete employees, trigger recalculations
- **Training Access:** Train models, manage training runs
- **Bulk Operations:** Import/export employees, batch predictions
- **Configuration:** Switch prediction engines, adjust settings

**What Managers Can Do:**

- View predictions (filtered by their teams)
- View market trends and analytics
- Read-only access to employees in their departments

**What Regular Users Can Do:**

- View their own employee profile
- View public trends and recommendations

---

## Prediction Management

### Understanding Predictions

Each prediction consists of:

- **Job Role:** The position (e.g., "Data Engineer")
- **Skill:** The specific skill (e.g., "Python", "Machine Learning")
- **Horizon Years:** Prediction timeframe (3, 5, or 10 years)
- **Predicted Level:** HIGH, MEDIUM, or LOW importance
- **Score:** Numeric confidence score (0-100)
- **Rationale:** Human-readable explanation of why this prediction was made
- **Engine:** Whether ML model or rules engine generated the prediction

### Viewing Predictions

#### Via Django Admin

1. Navigate to **Future Skills > Future Skill Predictions**
2. Use filters:
   - Job role
   - Skill
   - Predicted level
   - Horizon years
   - Created date range

#### Via API

```bash
# List all predictions
curl -X GET "http://localhost:8000/api/future-skills/" \
  -u admin:password

# Filter by job role
curl -X GET "http://localhost:8000/api/future-skills/?job_role_id=1" \
  -u admin:password

# Filter by horizon and level
curl -X GET "http://localhost:8000/api/future-skills/?horizon_years=5&predicted_level=HIGH" \
  -u admin:password
```

#### Via Swagger UI

1. Go to `/api/docs/`
2. Find **GET /api/future-skills/** under "Predictions"
3. Click "Try it out"
4. Enter filter parameters
5. Click "Execute"

### Recalculating Predictions

#### When to Recalculate

Trigger recalculation when:

- ✅ New market trends are added
- ✅ Employee skill profiles are updated
- ✅ Job role requirements change
- ✅ Economic reports indicate shifts
- ✅ A new ML model is trained
- ✅ Quarterly planning cycles
- ✅ After major organizational changes

**Frequency:** Recommended quarterly or when significant data changes occur.

#### How to Recalculate

##### Method 1: Via API (Recommended)

```bash
# Recalculate with 5-year horizon
curl -X POST http://localhost:8000/api/future-skills/recalculate/ \
  -H "Content-Type: application/json" \
  -u admin:password \
  -d '{"horizon_years": 5}'

# Recalculate with 10-year strategic horizon
curl -X POST http://localhost:8000/api/future-skills/recalculate/ \
  -H "Content-Type: application/json" \
  -u admin:password \
  -d '{"horizon_years": 10}'
```

**Response:**

```json
{
  "horizon_years": 5,
  "total_predictions": 357,
  "total_recommendations": 42
}
```

##### Method 2: Via Swagger UI

1. Go to `/api/docs/`
2. Find **POST /api/future-skills/recalculate/** under "Predictions"
3. Click "Try it out"
4. Enter request body: `{"horizon_years": 5}`
5. Click "Execute"
6. Review response showing total predictions created

##### Method 3: Via Django Management Command

```bash
# Activate virtual environment
source .venv/bin/activate

# Run recalculation command
python manage.py recalculate_future_skills --horizon 5
```

#### What Happens During Recalculation

1. **Delete Old Predictions:** Clears existing predictions for the specified horizon
2. **Generate New Predictions:** Creates predictions for all job_role × skill combinations
3. **Select Engine:** Uses ML model if available and trained, otherwise uses rules engine
4. **Calculate Scores:** Applies prediction logic based on:
   - Market trend scores
   - Internal skill usage metrics
   - Training request frequency
   - Skill scarcity indexes
   - Hiring difficulty data
   - Salary trends
5. **Generate Rationales:** Creates explanations for each prediction
6. **Create Recommendations:** Generates HR investment recommendations for HIGH predictions
7. **Track Execution:** Creates a PredictionRun record for audit trail

**Performance:** Typically takes 5-15 seconds for 300-500 predictions.

#### Understanding Prediction Runs

Each recalculation creates a `PredictionRun` record tracking:

- **Created At:** Timestamp of execution
- **Horizon Years:** Prediction timeframe used
- **Total Predictions:** Number of predictions generated
- **Engine Used:** ML or RULES
- **Model Version:** If ML was used, which model version
- **Execution Time:** Duration in seconds
- **Triggered By:** Admin who initiated the recalculation

View in Django Admin: **Future Skills > Prediction Runs**

---

## Model Training

### Understanding ML Models

The system uses **Random Forest Classifiers** to predict skill importance levels (HIGH, MEDIUM, LOW).

**Features Used (11 total):**

- Market trend score
- Internal skill usage count
- Training requests count
- Skill scarcity index
- Hiring difficulty score
- Average salary (in thousands)
- Years to prediction horizon
- Job role growth rate
- Industry demand score
- Educational requirements level
- Automation risk score

**Output:** Classification into HIGH, MEDIUM, or LOW levels with confidence scores.

### When to Train a Model

Train a new model when:

✅ **Initial Setup:** First time deploying the system  
✅ **Data Growth:** Accumulated 50+ new data points  
✅ **Performance Decline:** Current model accuracy drops below 95%  
✅ **New Features:** Added new skills or job roles  
✅ **Quarterly Review:** Regular model refresh cycles  
✅ **Strategy Changes:** Updated business priorities or skill frameworks

**Recommended:** Train models quarterly or when you have 100+ new training samples.

### Training Process

#### Option 1: Synchronous Training (Small Datasets)

**Use when:**

- Dataset < 1000 rows
- Need immediate results
- Testing hyperparameters
- Development environment

**API Request:**

```bash
curl -X POST http://localhost:8000/api/training/train/ \
  -H "Content-Type: application/json" \
  -u admin:password \
  -d '{
    "dataset_path": "artifacts/datasets/future_skills_dataset.csv",
    "test_split": 0.2,
    "hyperparameters": {
      "n_estimators": 100,
      "max_depth": 15,
      "min_samples_split": 5,
      "random_state": 42
    },
    "model_version": "v2.3_quarterly",
    "notes": "Q4 2024 model with updated market trends",
    "async_training": false
  }'
```

**Response (Immediate):**

```json
{
  "training_run_id": 15,
  "status": "COMPLETED",
  "message": "Training completed successfully in 12.45s",
  "model_version": "v2.3_quarterly",
  "metrics": {
    "accuracy": 0.9861,
    "precision": 0.9855,
    "recall": 0.9861,
    "f1_score": 0.986,
    "training_duration_seconds": 12.45
  }
}
```

#### Option 2: Asynchronous Training (Large Datasets, Production)

**Use when:**

- Dataset > 1000 rows
- Production environment
- Training may take > 30 seconds
- Don't want to block the API

**API Request:**

```bash
curl -X POST http://localhost:8000/api/training/train/ \
  -H "Content-Type: application/json" \
  -u admin:password \
  -d '{
    "dataset_path": "artifacts/datasets/future_skills_dataset.csv",
    "test_split": 0.2,
    "hyperparameters": {
      "n_estimators": 150,
      "max_depth": 20
    },
    "model_version": "v2.4_production",
    "notes": "Production model for Q1 2025",
    "async_training": true
  }'
```

**Response (Immediate):**

```json
{
  "training_run_id": 16,
  "status": "RUNNING",
  "message": "Training started in background",
  "model_version": "v2.4_production",
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

**Check Status:**

```bash
# Check training run status
curl -X GET http://localhost:8000/api/training/runs/16/ \
  -u admin:password
```

#### Training via Swagger UI

1. Go to `/api/docs/`
2. Find **POST /api/training/train/** under "Training"
3. Click "Try it out"
4. Enter request body (see examples above)
5. Click "Execute"
6. Review response and training_run_id

### Hyperparameter Tuning

#### Key Hyperparameters

**1. n_estimators (Default: 100)**

- Number of decision trees in the forest
- **Higher = More accurate but slower**
- Recommended range: 50-200
- Start with 100, increase to 150 if accuracy < 97%

**2. max_depth (Default: 15)**

- Maximum depth of each tree
- **Higher = More complex, risk overfitting**
- Recommended range: 10-25
- Start with 15, increase to 20 for complex patterns

**3. min_samples_split (Default: 5)**

- Minimum samples required to split a node
- **Higher = More conservative, prevents overfitting**
- Recommended range: 2-10
- Start with 5, increase to 8 for noisy data

**4. min_samples_leaf (Default: 2)**

- Minimum samples required at leaf node
- **Higher = Smoother predictions**
- Recommended range: 1-5

**5. random_state (Default: 42)**

- Random seed for reproducibility
- Keep at 42 for consistent results

#### Recommended Configurations

**Balanced (Default):**

```json
{
  "n_estimators": 100,
  "max_depth": 15,
  "min_samples_split": 5,
  "random_state": 42
}
```

**High Accuracy:**

```json
{
  "n_estimators": 150,
  "max_depth": 20,
  "min_samples_split": 3,
  "random_state": 42
}
```

**Fast Training:**

```json
{
  "n_estimators": 50,
  "max_depth": 10,
  "min_samples_split": 10,
  "random_state": 42
}
```

**Production (Balanced + Fast):**

```json
{
  "n_estimators": 120,
  "max_depth": 18,
  "min_samples_split": 5,
  "random_state": 42
}
```

### Evaluating Model Performance

#### Key Metrics

**1. Accuracy (Target: > 95%)**

- Overall correctness of predictions
- Formula: (Correct Predictions) / (Total Predictions)
- **Interpretation:** 98% accuracy = 98 out of 100 predictions are correct

**2. Precision (Target: > 95%)**

- Correctness of positive predictions
- Formula: True Positives / (True Positives + False Positives)
- **Interpretation:** When model predicts HIGH, it's correct 98% of the time

**3. Recall (Target: > 95%)**

- Coverage of actual positives
- Formula: True Positives / (True Positives + False Negatives)
- **Interpretation:** Model catches 98% of actual HIGH skills

**4. F1 Score (Target: > 95%)**

- Harmonic mean of precision and recall
- Balanced measure of model quality
- **Interpretation:** 98% F1 = excellent balance between precision and recall

#### Per-Class Metrics

View performance for each level:

```json
{
  "per_class_metrics": {
    "HIGH": {
      "precision": 0.99,
      "recall": 0.98,
      "f1": 0.99,
      "support": 45
    },
    "MEDIUM": {
      "precision": 0.98,
      "recall": 0.99,
      "f1": 0.98,
      "support": 60
    },
    "LOW": {
      "precision": 0.99,
      "recall": 0.99,
      "f1": 0.99,
      "support": 55
    }
  }
}
```

**Interpreting:**

- HIGH predictions are 99% precise (rarely false positives)
- HIGH recall of 98% means we catch most HIGH skills
- All classes perform well (balanced model)

#### Viewing Training History

##### Via API

```bash
# List all training runs
curl -X GET "http://localhost:8000/api/training/runs/" \
  -u admin:password

# Filter by status
curl -X GET "http://localhost:8000/api/training/runs/?status=COMPLETED" \
  -u admin:password

# Get detailed run information
curl -X GET "http://localhost:8000/api/training/runs/15/" \
  -u admin:password
```

##### Via Django Admin

1. Navigate to **Future Skills > Training Runs**
2. View list of all training attempts
3. Filter by status (RUNNING, COMPLETED, FAILED)
4. Click on a run to see full details:
   - Metrics (accuracy, precision, recall, F1)
   - Hyperparameters used
   - Dataset information
   - Training duration
   - Error messages (if failed)

##### Via Swagger UI

1. Go to `/api/docs/`
2. Find **GET /api/training/runs/** under "Training"
3. Try filters: `status=COMPLETED`, `trained_by=admin`
4. Click specific run ID for detailed metrics

### Model Versioning

#### Version Naming Convention

**Format:** `v{major}.{minor}_{environment}_{description}`

**Examples:**

- `v1.0_production` - First production model
- `v2.1_quarterly` - Q1 2025 quarterly update
- `v2.3_experimental` - Testing new features
- `v3.0_prod_retrained` - Major update with retraining

**Best Practice:** Use semantic versioning:

- Major (v1 → v2): Significant changes (new features, algorithm changes)
- Minor (v2.1 → v2.2): Incremental improvements (hyperparameter tuning)
- Environment: `production`, `staging`, `dev`, `test`

#### Model Registry

View all trained models: **ml/MODEL_REGISTRY.md**

Each entry includes:

- Version number
- Training date
- Dataset used
- Number of samples
- Performance metrics
- Model file path
- Notes on changes

#### Activating a Model

After training, the model is automatically saved and can be activated:

1. **Automatic Activation:** Latest successfully trained model is used automatically
2. **Manual Activation:** Update `FUTURE_SKILLS_ML_MODEL_PATH` in settings to point to specific model version
3. **Verification:** Check `artifacts/models/` directory for `.pkl` or `.joblib` files

```bash
# List available models
ls -lh artifacts/models/

# Example output:
# future_skills_model_v2.1_quarterly.pkl
# future_skills_model_v2.3_experimental.pkl
# future_skills_model_v2.4_production.pkl
```

---

## Monitoring & Analytics

### Prediction Monitoring

#### Tracking Prediction Quality

The system logs predictions to **logs/predictions.jsonl** when monitoring is enabled.

**Enable Monitoring:**

```python
# In Django settings or .env
FUTURE_SKILLS_ENABLE_MONITORING=true
```

**Log Format:**

```json
{
  "timestamp": "2024-11-28T10:15:30Z",
  "job_role": "Data Engineer",
  "skill": "Python",
  "horizon_years": 5,
  "prediction": "HIGH",
  "score": 85.5,
  "engine": "ML",
  "model_version": "v2.4_production",
  "features": {
    "trend_score": 0.85,
    "internal_usage": 12,
    "training_requests": 8
  }
}
```

**Analyzing Logs:**

```bash
# Count predictions per level
grep -o '"prediction": "[^"]*"' logs/predictions.jsonl | sort | uniq -c

# Check which engine is being used
grep -o '"engine": "[^"]*"' logs/predictions.jsonl | sort | uniq -c

# View recent HIGH predictions
grep '"prediction": "HIGH"' logs/predictions.jsonl | tail -20
```

#### Viewing Analytics Dashboard

**Via Django Admin:**

1. Navigate to **Future Skills > Analytics Dashboard** (if custom admin view configured)
2. View charts and statistics:
   - Predictions by level
   - Predictions by job role
   - Predictions by skill category
   - Trend over time
   - Engine usage distribution

**Via API (Custom Endpoints):**

```bash
# Get prediction statistics
curl -X GET "http://localhost:8000/api/analytics/predictions-summary/" \
  -u admin:password

# Get training run trends
curl -X GET "http://localhost:8000/api/analytics/training-trends/" \
  -u admin:password
```

### HR Investment Recommendations

#### Viewing Recommendations

Recommendations are automatically generated for HIGH predictions during recalculation.

**Via Django Admin:**

1. Navigate to **Future Skills > HR Investment Recommendations**
2. Filter by:
   - Priority (HIGH, MEDIUM, LOW)
   - Skill
   - Expected ROI
   - Created date

**Via API:**

```bash
# List all recommendations
curl -X GET "http://localhost:8000/api/hr-recommendations/" \
  -u admin:password

# Filter by priority
curl -X GET "http://localhost:8000/api/hr-recommendations/?priority=HIGH" \
  -u admin:password
```

#### Understanding Recommendations

Each recommendation includes:

- **Skill:** What skill to invest in
- **Priority:** HIGH, MEDIUM, or LOW urgency
- **Expected ROI:** Estimated return on investment (%)
- **Estimated Cost:** Training program cost estimate
- **Affected Employees:** Number of employees who need this skill
- **Rationale:** Why this investment is recommended
- **Action Items:** Specific steps to take

**Example:**

```
Skill: Python
Priority: HIGH
Expected ROI: 150%
Estimated Cost: $50,000
Affected Employees: 25
Rationale: Critical for 3 job roles (Data Engineer, ML Engineer, Backend Developer).
           High market demand (+85% trend) and internal usage gap.
Action Items:
- Launch Python bootcamp for 25 employees
- Partner with online learning platform
- Budget for certification programs
```

### Market Trends Analysis

#### Viewing Trends

**Via Django Admin:**

1. Navigate to **Future Skills > Market Trends**
2. Filter by:
   - Skill
   - Year
   - Trend direction (UP, STABLE, DOWN)

**Via API:**

```bash
# List market trends
curl -X GET "http://localhost:8000/api/market-trends/" \
  -u admin:password

# Filter by year
curl -X GET "http://localhost:8000/api/market-trends/?year=2025" \
  -u admin:password
```

#### Analyzing Trends

**Key Metrics:**

- **Trend Score (0-1):** Market demand intensity
- **Growth Rate (%):** Year-over-year change
- **Demand Level:** LOW, MEDIUM, HIGH, CRITICAL
- **Source:** Industry reports, job postings, surveys

**Interpreting:**

- **Trend Score > 0.8:** Very high demand, invest immediately
- **Trend Score 0.5-0.8:** Moderate demand, plan training
- **Trend Score < 0.5:** Low priority, monitor only
- **Growth Rate > 20%:** Rapidly growing skill, strategic priority
- **Growth Rate < 0%:** Declining skill, deprioritize

---

## Engine Configuration

### Understanding Prediction Engines

The system supports two prediction engines:

#### 1. ML Engine (Machine Learning)

**How it works:**

- Uses trained Random Forest model
- Analyzes 11 features per prediction
- Provides confidence scores
- Generates SHAP/LIME explanations

**Advantages:**

- ✅ High accuracy (95-98%)
- ✅ Adapts to new data
- ✅ Explainable predictions
- ✅ Handles complex patterns

**Disadvantages:**

- ❌ Requires training data
- ❌ Needs periodic retraining
- ❌ More complex to maintain

**When to use:**

- Production systems with historical data
- When accuracy is critical
- After training multiple models
- When you have 500+ training samples

#### 2. Rules Engine (Rules-Based)

**How it works:**

- Uses predefined business rules
- Calculates weighted scores from features
- No training required
- Deterministic and transparent

**Advantages:**

- ✅ No training required
- ✅ Works immediately
- ✅ Fully transparent
- ✅ Consistent and predictable

**Disadvantages:**

- ❌ Lower accuracy (~85-90%)
- ❌ Less adaptive to changes
- ❌ Manual rule updates needed
- ❌ May miss complex patterns

**When to use:**

- Initial setup before training data
- Backup/fallback when ML unavailable
- Simple, transparent predictions
- When explainability is priority over accuracy

### Switching Engines

#### Check Current Engine

```bash
# Via Django shell
python manage.py shell -c "
from django.conf import settings
print(f'Use ML: {settings.FUTURE_SKILLS_USE_ML}')
print(f'Model Path: {settings.FUTURE_SKILLS_ML_MODEL_PATH}')
"
```

#### Switch to ML Engine

**Method 1: Environment Variable**

```bash
# In .env file
FUTURE_SKILLS_USE_ML=true
FUTURE_SKILLS_ML_MODEL_PATH=artifacts/models/future_skills_model_v2.4_production.pkl
```

**Method 2: Django Settings**

```python
# In config/settings/base.py
FUTURE_SKILLS_USE_ML = True
FUTURE_SKILLS_ML_MODEL_PATH = 'artifacts/models/future_skills_model_v2.4_production.pkl'
```

**Restart server after changes**

#### Switch to Rules Engine

**Method 1: Environment Variable**

```bash
# In .env file
FUTURE_SKILLS_USE_ML=false
```

**Method 2: Django Settings**

```python
# In config/settings/base.py
FUTURE_SKILLS_USE_ML = False
```

**Restart server after changes**

#### Automatic Fallback

The system automatically falls back to rules engine if:

- ML model file doesn't exist
- Model loading fails
- Prediction errors occur
- Model not trained yet

**Check logs for fallback events:**

```bash
grep "Falling back to rules" logs/future_skills.log
```

### Engine Performance Comparison

Run comparison script to evaluate both engines:

```bash
# Activate virtual environment
source .venv/bin/activate

# Run evaluation
python ml/scripts/evaluate_future_skills_models.py
```

**Output:** `ml/evaluation_results.json`

```json
{
  "ml_engine": {
    "accuracy": 0.9861,
    "precision": 0.9855,
    "recall": 0.9861,
    "f1_score": 0.986,
    "predictions_per_second": 1250
  },
  "rules_engine": {
    "accuracy": 0.875,
    "precision": 0.8712,
    "recall": 0.875,
    "f1_score": 0.8729,
    "predictions_per_second": 2100
  },
  "recommendation": "Use ML engine for higher accuracy"
}
```

---

## Best Practices

### Daily Operations

#### Morning Routine

1. **Check Training Status**

   - Visit `/api/training/runs/?status=RUNNING`
   - Verify no failed training jobs
   - Review completed runs from overnight

2. **Monitor Predictions**

   - Scan prediction logs: `tail -100 logs/predictions.jsonl`
   - Check for errors in: `logs/future_skills.log`
   - Verify engine usage distribution

3. **Review Recommendations**
   - Check new HIGH priority recommendations
   - Share urgent items with leadership
   - Plan training programs

#### Weekly Tasks

1. **Data Quality Review**

   - Update market trends with latest reports
   - Verify employee skill profiles
   - Add new skills or job roles as needed

2. **Performance Analysis**

   - Review prediction accuracy trends
   - Compare ML vs rules engine performance
   - Identify areas for improvement

3. **User Support**
   - Answer manager questions about predictions
   - Provide interpretation guidance
   - Collect feedback on recommendations

#### Monthly Tasks

1. **Model Maintenance**

   - Retrain model with latest data (if 100+ new samples)
   - Update hyperparameters if performance declined
   - Version and archive old models

2. **Strategic Planning**

   - Generate prediction summary reports
   - Present HIGH priority skills to leadership
   - Budget for recommended training programs

3. **Documentation**
   - Update model registry with new versions
   - Document any configuration changes
   - Update training procedures if modified

#### Quarterly Tasks

1. **Full System Audit**

   - Comprehensive model retraining
   - Recalculate all predictions with new horizons
   - Update market trend data from industry reports

2. **Performance Review**

   - Compare predictions vs actual hiring needs
   - Measure ROI of implemented recommendations
   - Adjust prediction parameters if needed

3. **Stakeholder Reporting**
   - Present quarterly skill trends
   - Show prediction accuracy metrics
   - Demonstrate business impact

### Data Management

#### Keep Data Fresh

**Market Trends:**

- Update monthly from industry reports
- Sources: LinkedIn Talent Insights, Gartner, Forrester
- Add new emerging skills promptly

**Employee Skills:**

- Regular skill assessments (quarterly)
- Update after training completions
- Track certification acquisitions

**Economic Reports:**

- Quarterly industry outlooks
- Salary benchmarks
- Hiring difficulty indexes

#### Data Quality Checks

```bash
# Check for missing data
python manage.py shell -c "
from future_skills.models import Skill, JobRole, MarketTrend
print(f'Skills: {Skill.objects.count()}')
print(f'Job Roles: {JobRole.objects.count()}')
print(f'Market Trends: {MarketTrend.objects.count()}')
print(f'Trends in last 30 days: {MarketTrend.objects.filter(created_at__gte=datetime.now()-timedelta(days=30)).count()}')
"
```

### Security Best Practices

1. **Protect Training Data**

- Store datasets in secure `artifacts/datasets/` directory
- Don't commit sensitive employee data to Git
- Use `.gitignore` for `*.csv` files with PII

2. **API Security**

   - Always use HTTPS in production
   - Rotate authentication tokens regularly
   - Monitor API access logs

3. **Model Security**

   - Version control model registry
   - Backup trained models regularly
   - Test models in staging before production

4. **Access Control**
   - Limit HR Staff role to trusted personnel
   - Audit admin actions periodically
   - Use Django's permission system

### Performance Optimization

#### Database

```bash
# Create indexes for frequent queries
python manage.py shell -c "
from django.db import connection
cursor = connection.cursor()
cursor.execute('CREATE INDEX IF NOT EXISTS idx_predictions_job_role ON future_skills_futureskillprediction(job_role_id);')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_predictions_skill ON future_skills_futureskillprediction(skill_id);')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_predictions_level ON future_skills_futureskillprediction(predicted_level);')
"
```

#### Caching

Enable caching for API responses:

```python
# In config/settings/production.py
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}
```

#### Async Training

Always use `async_training=true` in production to avoid timeouts.

---

## Troubleshooting

### Common Issues

#### 1. Training Fails

**Symptoms:**

- Training run status = FAILED
- Error in training run details
- No model file created

**Solutions:**

**Check dataset format:**

```bash
# Verify CSV has required columns
head -1 artifacts/datasets/future_skills_dataset.csv
```

Required columns: `job_role`, `skill`, `level`, `trend_score`, `internal_usage`, `training_requests`, `scarcity_index`, `hiring_difficulty`, `avg_salary_k`, `horizon_years`

**Check file permissions:**

```bash
ls -l artifacts/datasets/future_skills_dataset.csv
# Should be readable
```

**Check logs:**

```bash
tail -100 logs/future_skills.log | grep ERROR
```

**Verify dataset size:**

```bash
wc -l artifacts/datasets/future_skills_dataset.csv
# Should have at least 100 rows
```

#### 2. Predictions Return Empty

**Symptoms:**

- `/api/future-skills/` returns `{"results": []}`
- No predictions in database

**Solutions:**

**Trigger recalculation:**

```bash
curl -X POST http://localhost:8000/api/future-skills/recalculate/ \
  -H "Content-Type: application/json" \
  -u admin:password \
  -d '{"horizon_years": 5}'
```

**Check data exists:**

```bash
python manage.py shell -c "
from future_skills.models import Skill, JobRole
print(f'Skills: {Skill.objects.count()}')
print(f'Job Roles: {JobRole.objects.count()}')
"
```

**Run seed command if empty:**

```bash
python manage.py seed_future_skills
```

#### 3. ML Model Not Loading

**Symptoms:**

- System uses rules engine despite `USE_ML=true`
- Error: "Model file not found"
- Log: "Falling back to rules engine"

**Solutions:**

**Check model file exists:**

```bash
ls -l artifacts/models/*.pkl artifacts/models/*.joblib
```

**Verify settings:**

```bash
python manage.py shell -c "
from django.conf import settings
print(f'Use ML: {settings.FUTURE_SKILLS_USE_ML}')
print(f'Model Path: {settings.FUTURE_SKILLS_ML_MODEL_PATH}')
import os
print(f'File exists: {os.path.exists(settings.FUTURE_SKILLS_ML_MODEL_PATH)}')
"
```

**Train a new model:**

```bash
curl -X POST http://localhost:8000/api/training/train/ \
  -H "Content-Type: application/json" \
  -u admin:password \
  -d '{"dataset_path": "artifacts/datasets/future_skills_dataset.csv", "async_training": false}'
```

#### 4. Slow API Responses

**Symptoms:**

- API requests take > 5 seconds
- Timeout errors
- High CPU usage

**Solutions:**

**Enable pagination:**

```bash
# Add page_size parameter
curl -X GET "http://localhost:8000/api/future-skills/?page_size=20"
```

**Use async training:**

```json
{ "async_training": true }
```

**Add database indexes** (see Performance Optimization section)

**Check database size:**

```bash
python manage.py shell -c "
from future_skills.models import FutureSkillPrediction
print(f'Total Predictions: {FutureSkillPrediction.objects.count()}')
"
# If > 10,000, consider archiving old predictions
```

#### 5. Permission Denied

**Symptoms:**

- 403 Forbidden errors
- "You do not have permission" messages

**Solutions:**

**Verify user role:**

```bash
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
user = User.objects.get(username='admin')
print(f'Groups: {list(user.groups.values_list(\"name\", flat=True))}')
print(f'Is Staff: {user.is_staff}')
print(f'Is Superuser: {user.is_superuser}')
"
```

**Add to HR Staff group:**

```bash
python manage.py shell -c "
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
User = get_user_model()
user = User.objects.get(username='your_username')
hr_group, _ = Group.objects.get_or_create(name='HR_Staff')
user.groups.add(hr_group)
print('User added to HR_Staff group')
"
```

### Getting Help

#### Log Files

**Application logs:**

```bash
tail -f logs/future_skills.log
```

**Prediction logs:**

```bash
tail -f logs/predictions.jsonl
```

**Django logs:**

```bash
tail -f logs/django.log
```

#### Debug Mode

Enable debug mode for detailed error messages:

```python
# In config/settings/development.py
DEBUG = True
```

**⚠️ Never enable DEBUG in production!**

#### Support Channels

1. **Documentation:** Review `docs/` directory
2. **API Docs:** Check `/api/docs/` for endpoint details
3. **GitHub Issues:** Report bugs or request features
4. **Team Lead:** Escalate critical issues
5. **Developer:** Contact for technical issues

---

## API Reference

### Quick Reference

#### Predictions

- `GET /api/future-skills/` - List predictions
- `GET /api/future-skills/{id}/` - Get prediction detail
- `POST /api/future-skills/recalculate/` - Recalculate predictions

#### Training

- `POST /api/training/train/` - Train new model
- `GET /api/training/runs/` - List training runs
- `GET /api/training/runs/{id}/` - Get training run details

#### Employees

- `GET /api/employees/` - List employees
- `POST /api/employees/` - Create employee
- `GET /api/employees/{id}/` - Get employee detail
- `PUT /api/employees/{id}/` - Update employee
- `DELETE /api/employees/{id}/` - Delete employee

#### Market Trends

- `GET /api/market-trends/` - List market trends
- `GET /api/market-trends/{id}/` - Get trend detail

#### Recommendations

- `GET /api/hr-recommendations/` - List recommendations
- `GET /api/hr-recommendations/{id}/` - Get recommendation detail

### Complete Documentation

For full API documentation with examples:

- **Swagger UI:** `/api/docs/`
- **ReDoc:** `/api/redoc/`
- **Documentation Guide:** `docs/API_DOCUMENTATION.md`

---

## Appendix

### Glossary

**Future Skill:** A skill predicted to be important for a job role in the future

**Horizon Years:** The number of years into the future for a prediction (3, 5, or 10)

**Predicted Level:** Classification of skill importance (HIGH, MEDIUM, LOW)

**Score:** Numeric confidence value for a prediction (0-100)

**Rationale:** Human-readable explanation for why a prediction was made

**Engine:** The system used to generate predictions (ML or RULES)

**Training Run:** A single execution of the model training process

**Hyperparameter:** Configuration setting for the ML model

**Accuracy:** Percentage of correct predictions

**Precision:** Percentage of positive predictions that are correct

**Recall:** Percentage of actual positives that were predicted

**F1 Score:** Balanced measure combining precision and recall

**PredictionRun:** Record tracking a recalculation execution

**Model Version:** Unique identifier for a trained ML model

**ROI:** Return on Investment for training programs

### Keyboard Shortcuts

**Swagger UI:**

- `Ctrl/Cmd + K` - Search endpoints
- `Ctrl/Cmd + Enter` - Execute request
- `Escape` - Close modals

**Django Admin:**

- `Ctrl/Cmd + S` - Save changes
- `Ctrl/Cmd + Enter` - Save and continue editing

### Contact Information

**Technical Support:** Contact development team  
**HR Questions:** Contact HR leadership  
**Emergency Issues:** Check on-call schedule

---

**End of Administrator Guide**  
_For updates to this guide, check the Git repository or contact the development team._
