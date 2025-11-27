# 🔬 Quick Reference: Model Experimentation

## Fast Commands

```bash
# Run model comparison experiment
python ml/experiment_future_skills_models.py

# View results
cat ml/MODEL_COMPARISON.md

# View JSON metrics
cat ml/experiment_results.json | jq '.results[] | {model: .model_name, f1: .metrics.f1_weighted, time: .training_time_seconds}'
```

## Current Results Summary

| Model              | F1-Score | Accuracy | Time  |
| ------------------ | -------- | -------- | ----- |
| LogisticRegression | 0.9862   | 0.9861   | 0.02s |
| RandomForest       | 0.9860   | 0.9861   | 0.19s |
| RandomForest_tuned | 0.9860   | 0.9861   | 0.31s |

## Install Optional Models

```bash
# macOS
brew install libomp
pip install xgboost lightgbm

# Linux
pip install xgboost lightgbm

# Then re-run
python ml/experiment_future_skills_models.py
```

## Change Model in Production

```bash
# 1. Edit training script
vim ml/train_future_skills_model.py
# Change: clf = RandomForestClassifier(...)
# To:     clf = LogisticRegression(...)

# 2. Retrain
python ml/train_future_skills_model.py --version v2 --output ml/future_skills_model_v2.pkl

# 3. Evaluate
python ml/evaluate_future_skills_models.py

# 4. Deploy (if better)
cp ml/future_skills_model_v2.pkl ml/future_skills_model.pkl

# 5. Restart app (model auto-reloads)
```

## Key Files

- **Experiment Script**: `ml/experiment_future_skills_models.py`
- **Results Report**: `ml/MODEL_COMPARISON.md`
- **JSON Metrics**: `ml/experiment_results.json`
- **Documentation**: `docs/LT3_COMPLETION_SUMMARY.md`
- **Architecture**: `ml/ARCHITECTURE.md` (extensibility section)
- **README**: `ml/README.md` (model selection policy)
