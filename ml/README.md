# 📊 Future Skills - ML Model Evaluation

This directory contains the ML model evaluation framework for comparing the Machine Learning model with the rule-based prediction engine.

## 📁 Files

### Core Files

| File                               | Description                                  |
| ---------------------------------- | -------------------------------------------- |
| `evaluate_future_skills_models.py` | Main evaluation script comparing ML vs Rules |
| `train_future_skills_model.py`     | Model training script                        |
| `future_skills_model.pkl`          | Trained ML pipeline (Random Forest)          |
| `future_skills_dataset.csv`        | Enriched dataset for training/evaluation     |
| `evaluation_results.json`          | Detailed metrics in JSON format              |

### Generated Reports

| File                                | Description                      |
| ----------------------------------- | -------------------------------- |
| `../docs/ML_VS_RULES_COMPARISON.md` | Markdown comparison report       |
| `../docs/MT3_COMPLETION.md`         | Complete MT-3 task documentation |

## 🚀 Quick Start

### 1. Train the Model

```bash
# Generate dataset from database
python manage.py export_future_skills_dataset

# Train the ML model
python ml/train_future_skills_model.py
```

**Output:**

- `ml/future_skills_model.pkl` - Trained pipeline
- Training metrics and confusion matrix printed to console

### 2. Evaluate Performance

```bash
# Run complete evaluation
python ml/evaluate_future_skills_models.py
```

**Output:**

- `docs/ML_VS_RULES_COMPARISON.md` - Comparison report
- `ml/evaluation_results.json` - Detailed metrics
- Console output with performance summaries

### 3. View Results

```bash
# View the markdown report
cat docs/ML_VS_RULES_COMPARISON.md

# Or open in VS Code
code docs/ML_VS_RULES_COMPARISON.md

# View JSON data
cat ml/evaluation_results.json | jq '.'
```

## 📊 Evaluation Metrics

The evaluation script calculates comprehensive metrics:

### Overall Metrics

- **Accuracy**: Proportion of correct predictions
- **F1-Score (Macro)**: Unweighted mean of F1 per class
- **F1-Score (Weighted)**: F1 weighted by class support

### Per-Class Metrics

For each class (LOW, MEDIUM, HIGH):

- **Precision**: TP / (TP + FP)
- **Recall**: TP / (TP + FN)
- **F1-Score**: Harmonic mean of precision and recall
- **Support**: Number of actual occurrences

### Confusion Matrix

Shows the distribution of predictions vs actual labels.

## 🎯 Results Summary

**Dataset:** 357 observations (0 LOW, 237 MEDIUM, 120 HIGH)

### Performance Comparison

| Metric            | Rule-Based | ML Model   | Improvement |
| ----------------- | ---------- | ---------- | ----------- |
| **Accuracy**      | 67.23%     | **99.72%** | +48.33%     |
| **F1 (Macro)**    | 28.36%     | **66.46%** | +134.33%    |
| **F1 (Weighted)** | 54.88%     | **99.72%** | +81.69%     |

### Key Findings

✅ **ML Model Wins on All Metrics**

🎯 **Biggest Improvement: HIGH Class**

- Rule-based: 4.88% F1-score (3/120 correct)
- ML Model: 99.58% F1-score (119/120 correct)
- **Improvement: +94.70 points** (+1941%!)

🤝 **MEDIUM Class: Both Perform Well**

- Rule-based: 80.20% F1-score
- ML Model: 99.79% F1-score
- **Improvement: +19.59 points** (+24%)

## 🔧 Advanced Usage

### Custom Dataset Evaluation

```bash
python ml/evaluate_future_skills_models.py \
  --dataset path/to/custom_dataset.csv \
  --model path/to/custom_model.pkl \
  --output docs/CUSTOM_REPORT.md \
  --json-output ml/custom_results.json
```

### Dataset Format

The CSV dataset must include:

**Required columns:**

- `future_need_level`: Target variable (LOW/MEDIUM/HIGH)
- `trend_score`: Market trend score (0-1)
- `internal_usage`: Internal skill usage (0-1)
- `training_requests`: Number of training requests

**Optional columns (for ML):**

- `job_role_name`: Job role name
- `skill_name`: Skill name
- `skill_category`: Skill category
- `job_department`: Department
- `scarcity_index`: Skill scarcity (0-1)
- `hiring_difficulty`: Hiring difficulty (0-1)
- `avg_salary_k`: Average salary in thousands
- `economic_indicator`: Economic indicator (0-1)

### Python API Usage

```python
from pathlib import Path
import joblib
import pandas as pd

# Load model
pipeline = joblib.load("ml/future_skills_model.pkl")

# Load dataset
df = pd.read_csv("ml/future_skills_dataset.csv")

# Select features
features = [
    "job_role_name", "skill_name", "trend_score",
    "internal_usage", "training_requests", # ... etc
]
X = df[features]

# Predict
predictions = pipeline.predict(X)
probabilities = pipeline.predict_proba(X)

print(f"Predictions: {predictions[:5]}")
print(f"Probabilities: {probabilities[:5]}")
```

## 📈 Monitoring in Production

When deployed, monitor these metrics:

1. **Prediction Distribution**: Track LOW/MEDIUM/HIGH proportions
2. **Confidence Scores**: Monitor prediction probabilities
3. **Feature Values**: Check for out-of-range inputs
4. **Prediction Time**: Ensure < 100ms per prediction
5. **Model Drift**: Compare distributions over time

Example monitoring code:

```python
# Log predictions with metadata
def log_prediction(input_data, prediction, confidence):
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "input": input_data,
        "prediction": prediction,
        "confidence": float(confidence),
        "model_version": "1.0",
    }
    # Send to monitoring system (e.g., Prometheus, CloudWatch)
    metrics_logger.info(json.dumps(log_entry))
```

## 🧪 Testing

The evaluation script includes validation:

```bash
# Run with verbose output
python ml/evaluate_future_skills_models.py --verbose

# Check dataset integrity
python -c "
import pandas as pd
df = pd.read_csv('ml/future_skills_dataset.csv')
print(f'Rows: {len(df)}')
print(f'Columns: {list(df.columns)}')
print(f'Label distribution:')
print(df['future_need_level'].value_counts())
"
```

## 📝 Documentation

- **Complete MT-3 documentation**: `docs/MT3_COMPLETION.md`
- **ML implementation guide**: `docs/ML3_SUMMARY.md`
- **Monitoring setup**: `docs/MT2_MONITORING_COMPLETION.md`
- **API documentation**: `DOCUMENTATION_SUMMARY.md`

## ⚠️ Limitations

1. **Simulated Data**: Dataset generated algorithmically, not from real usage
2. **No Train/Test Split**: Current evaluation uses full dataset
3. **Class Imbalance**: 0 LOW samples in current dataset
4. **Small Sample Size**: 357 observations may not represent all edge cases

**Recommendation**: Validate on real production data before full deployment.

## 🔄 Retraining Workflow

```bash
# 1. Export fresh data from database
python manage.py export_future_skills_dataset

# 2. Train new model
python ml/train_future_skills_model.py \
  --output ml/future_skills_model_v2.pkl

# 3. Evaluate new model
python ml/evaluate_future_skills_models.py \
  --model ml/future_skills_model_v2.pkl \
  --output docs/EVALUATION_V2.md

# 4. Compare versions
diff docs/ML_VS_RULES_COMPARISON.md docs/EVALUATION_V2.md

# 5. If better, deploy new version
cp ml/future_skills_model_v2.pkl ml/future_skills_model.pkl
```

## 🤝 Contributing

To improve the evaluation framework:

1. **Add new metrics**: Edit `calculate_metrics()` function
2. **Custom visualizations**: Add plotting code to `generate_comparison_report()`
3. **Different models**: Modify `train_future_skills_model.py` to try other algorithms
4. **Better reporting**: Enhance markdown generation in `generate_comparison_report()`

## 📞 Support

For questions or issues:

- Check documentation in `docs/`
- Review `TESTING.md` for test examples
- Consult `QUICK_COMMANDS.md` for common operations

---

**Last Updated**: 2025-11-27  
**Model Version**: 1.0  
**Evaluation Framework Version**: 1.0
