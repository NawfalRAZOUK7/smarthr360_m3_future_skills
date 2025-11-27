# 🚀 MLOps Quick Reference - Future Skills

Quick command reference for daily MLOps operations.

---

## 📋 Most Used Commands

```bash
# Show all available commands
make help

# Full retraining pipeline
make retrain-future-skills MODEL_VERSION=v2

# Export dataset only
make export-dataset

# Train model only
make train-model MODEL_VERSION=v2

# View model registry
make registry

# Run ML tests
make test-ml
```

---

## 📂 Important Files

| File                                | Purpose                      |
| ----------------------------------- | ---------------------------- |
| `ml/MODEL_REGISTRY.md`              | Version history table        |
| `ml/MLOPS_GUIDE.md`                 | Complete MLOps documentation |
| `ml/future_skills_model_vX.pkl`     | Model binary                 |
| `ml/future_skills_model_vX.json`    | Model metadata               |
| `logs/predictions_monitoring.jsonl` | Prediction logs for drift    |
| `config/settings.py`                | Production config            |
| `Makefile`                          | All available commands       |

---

## 🔄 Typical Workflows

### New Model Version

```bash
# Step 1: Retrain with new version
make retrain-future-skills MODEL_VERSION=v2 N_ESTIMATORS=300

# Step 2: Check metrics
cat ml/future_skills_model_v2.json | grep accuracy

# Step 3: If good, it's already deployed (with --auto-update-settings)
# Otherwise, manually update config/settings.py

# Step 4: Restart server
make serve
```

### Compare Two Versions

```bash
# View registry
make registry

# Compare metadata
diff ml/future_skills_model_v1.json ml/future_skills_model_v2.json

# Evaluate
make evaluate-model
```

### Check for Drift

```bash
# View recent predictions
tail -50 logs/predictions_monitoring.jsonl

# Analyze (future script)
python ml/analyze_drift.py --window 30days
```

---

## ⚙️ Settings Configuration

```python
# config/settings.py

FUTURE_SKILLS_USE_ML = True
FUTURE_SKILLS_MODEL_PATH = BASE_DIR / "ml" / "future_skills_model_v2.pkl"
FUTURE_SKILLS_MODEL_VERSION = "ml_random_forest_v2"
FUTURE_SKILLS_ENABLE_MONITORING = True
FUTURE_SKILLS_MONITORING_LOG = BASE_DIR / "logs" / "predictions_monitoring.jsonl"
```

---

## 🆘 Quick Troubleshooting

| Problem               | Solution                                     |
| --------------------- | -------------------------------------------- |
| Model not loading     | Check `FUTURE_SKILLS_MODEL_PATH` in settings |
| Low accuracy          | Check class distribution in metadata JSON    |
| Import error          | Verify scikit-learn version matches training |
| No predictions logged | Set `FUTURE_SKILLS_ENABLE_MONITORING = True` |

---

## 📞 Need Help?

1. Check `ml/MLOPS_GUIDE.md` for detailed info
2. View `MODEL_REGISTRY.md` for version history
3. Inspect metadata JSON files
4. Contact Data Science team

---

**Last updated**: 2025-11-27
