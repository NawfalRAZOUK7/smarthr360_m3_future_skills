# 🚀 ModelTrainer Quick Reference

**File:** `future_skills/services/training_service.py`  
**Purpose:** OOP interface for ML training lifecycle

---

## 📦 Import

```python
from future_skills.services.training_service import (
    ModelTrainer,
    ModelTrainerError,
    DataLoadError,
    TrainingError
)
```

---

## 🎯 Quick Start

### **Basic Usage (4 steps):**

```python
# 1. Initialize
trainer = ModelTrainer("ml/data/future_skills_dataset.csv")

# 2. Load data
trainer.load_data()

# 3. Train
metrics = trainer.train(n_estimators=100)

# 4. Save
trainer.save_model("ml/models/my_model.pkl")
trainer.save_training_run("v1.0", "ml/models/my_model.pkl")
```

---

## 🔧 Constructor

```python
trainer = ModelTrainer(
    dataset_path="ml/data/future_skills_dataset.csv",  # Required
    test_split=0.2,                                     # Optional (default: 0.2)
    random_state=42                                     # Optional (default: 42)
)
```

**Parameters:**

- `dataset_path`: Path to CSV dataset
- `test_split`: Test set proportion (0.0-1.0)
- `random_state`: Random seed for reproducibility

---

## 📥 load_data()

**Purpose:** Load CSV, validate, split train/test

```python
trainer.load_data()
```

**After calling:**

- ✅ `trainer.X_train` available
- ✅ `trainer.X_test` available
- ✅ `trainer.y_train` available
- ✅ `trainer.y_test` available

**Raises:**

- `DataLoadError` if file not found
- `DataLoadError` if target column missing

---

## 🏋️ train()

**Purpose:** Train RandomForest with custom hyperparameters

```python
metrics = trainer.train(
    n_estimators=100,        # Default: 100
    max_depth=None,          # Default: None (unlimited)
    min_samples_split=2,     # Default: 2
    min_samples_leaf=1,      # Default: 1
    class_weight='balanced', # Default: 'balanced'
    random_state=42,         # Default: 42
    n_jobs=-1                # Default: -1 (all cores)
)
```

**Returns:**

```python
{
    'accuracy': 0.9861,
    'precision': 0.9864,
    'recall': 0.9861,
    'f1_score': 0.9860,
    'per_class_metrics': {
        'MEDIUM': {'accuracy': 1.0, 'support': 48},
        'HIGH': {'accuracy': 0.9583, 'support': 24}
    },
    'confusion_matrix': [[48, 0], [1, 23]]
}
```

**After calling:**

- ✅ `trainer.model` contains trained pipeline
- ✅ `trainer.metrics` contains evaluation results
- ✅ `trainer.training_duration_seconds` available
- ✅ `trainer.hyperparameters` contains params used

**Raises:**

- `TrainingError` if training fails

---

## 📊 evaluate()

**Purpose:** Calculate metrics on custom test set

```python
metrics = trainer.evaluate(X_custom_test, y_custom_test)
```

Returns same metrics dict as `train()`.

---

## 💾 save_model()

**Purpose:** Persist trained model to disk

```python
trainer.save_model("ml/models/my_model.pkl")
```

**Creates directory if needed**  
**Uses joblib for serialization**

**Raises:**

- `ModelTrainerError` if save fails

---

## 🔍 get_feature_importance()

**Purpose:** Extract feature importances from RandomForest

```python
importances = trainer.get_feature_importance()
```

**Returns:**

```python
{
    'scarcity_index': 0.2896,
    'hiring_difficulty': 0.2523,
    'skill_category_Soft Skill': 0.0912,
    ...
}
```

**Raises:**

- `ModelTrainerError` if model not trained

---

## 📝 save_training_run()

**Purpose:** Create TrainingRun record for successful training

```python
training_run = trainer.save_training_run(
    model_version="v1.0",                         # Required
    model_path="ml/models/my_model.pkl",          # Required
    user=request.user,                            # Optional
    notes="Production model with tuned params"    # Optional
)
```

**Creates TrainingRun with:**

- ✅ `status='COMPLETED'`
- ✅ All metrics from training
- ✅ Hyperparameters
- ✅ Training duration
- ✅ Feature importances

**Returns:** `TrainingRun` instance

**Raises:**

- `TrainingError` if database save fails

---

## ❌ save_failed_training_run()

**Purpose:** Log failed training attempts

```python
# Set hyperparameters before calling (if available)
trainer.hyperparameters = {"n_estimators": 100}

failed_run = trainer.save_failed_training_run(
    model_version="v1.0_failed",              # Required
    error_message="Training interrupted",     # Required
    user=request.user,                        # Optional
    notes="Attempted with 100 estimators"     # Optional
)
```

**Creates TrainingRun with:**

- ✅ `status='FAILED'`
- ✅ `error_message` populated
- ✅ Hyperparameters (if set)
- ✅ Zero metrics

**Returns:** `TrainingRun` instance

---

## ⚠️ Error Handling

### **Exception Hierarchy:**

```
ModelTrainerError (Base)
  ├── DataLoadError
  └── TrainingError
```

### **Example:**

```python
try:
    trainer = ModelTrainer("ml/data/future_skills_dataset.csv")
    trainer.load_data()
    metrics = trainer.train(n_estimators=100)
    trainer.save_model("ml/models/v1.pkl")
    trainer.save_training_run("v1.0", "ml/models/v1.pkl")

except DataLoadError as e:
    print(f"❌ Data loading failed: {e}")

except TrainingError as e:
    print(f"❌ Training failed: {e}")
    trainer.save_failed_training_run("v1.0_failed", str(e))

except ModelTrainerError as e:
    print(f"❌ Unexpected error: {e}")
```

---

## 📋 Complete Example

```python
from future_skills.services.training_service import (
    ModelTrainer, DataLoadError, TrainingError
)

def train_and_deploy(version: str, estimators: int = 100):
    """Train model and save to database."""

    trainer = ModelTrainer("ml/data/future_skills_dataset.csv")

    try:
        # Load & validate data
        trainer.load_data()
        print(f"✅ Loaded: {len(trainer.X_train)} train, {len(trainer.X_test)} test")

        # Train with custom params
        metrics = trainer.train(
            n_estimators=estimators,
            max_depth=15,
            min_samples_split=5
        )
        print(f"✅ Trained: {metrics['accuracy']:.2%} accuracy")

        # Analyze features
        importances = trainer.get_feature_importance()
        top_3 = list(importances.items())[:3]
        print(f"✅ Top features: {', '.join(f[0] for f in top_3)}")

        # Save model
        model_path = f"ml/models/future_skills_{version}.pkl"
        trainer.save_model(model_path)
        print(f"✅ Saved: {model_path}")

        # Track in database
        training_run = trainer.save_training_run(
            model_version=version,
            model_path=model_path,
            notes=f"Trained with {estimators} estimators"
        )
        print(f"✅ Tracked: TrainingRun ID={training_run.id}")

        return training_run

    except DataLoadError as e:
        print(f"❌ Data error: {e}")
        return None

    except TrainingError as e:
        print(f"❌ Training error: {e}")
        trainer.save_failed_training_run(
            model_version=f"{version}_failed",
            error_message=str(e)
        )
        return None

# Usage
if __name__ == "__main__":
    train_and_deploy("v2.0", estimators=200)
```

---

## 🔗 Django Shell Example

```bash
python manage.py shell
```

```python
from future_skills.services.training_service import ModelTrainer

# Quick test
trainer = ModelTrainer("ml/data/future_skills_dataset.csv")
trainer.load_data()
metrics = trainer.train(n_estimators=50)

print(f"Accuracy: {metrics['accuracy']:.2%}")
print(f"Training time: {trainer.training_duration_seconds:.3f}s")

trainer.save_model("ml/models/test.pkl")
trainer.save_training_run("test_v1", "ml/models/test.pkl")
```

---

## 🔍 View Training Runs

```bash
python manage.py shell
```

```python
from future_skills.models import TrainingRun

# All completed runs
for run in TrainingRun.objects.filter(status='COMPLETED'):
    print(f"{run.model_version}: {run.accuracy:.2%} accuracy")

# All failed runs
for run in TrainingRun.objects.filter(status='FAILED'):
    print(f"{run.model_version}: {run.error_message}")

# Latest run
latest = TrainingRun.objects.latest('run_date')
print(f"Latest: {latest.model_version} ({latest.status})")
```

---

## 📚 Related Documentation

- **Section 2.2:** TrainingRun model enhancements (status, error_message, hyperparameters)
- **Section 2.3 Full Docs:** `/docs/SECTION_2.3_COMPLETION_SUMMARY.md`
- **ML Architecture:** `/ml/ARCHITECTURE.md`
- **MLOps Guide:** `/ml/MLOPS_GUIDE.md`

---

**Last Updated:** 2025-11-27  
**Status:** ✅ Production Ready
