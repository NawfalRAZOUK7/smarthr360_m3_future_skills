# Runbook: ML Retrain/Recovery

Goal: retrain models, recover from failed runs, and promote results.

1) Prep dataset
- Ensure dataset is available (tests use `tests/fixtures/future_skills_dataset.csv`; production should point to real data under `artifacts/`).

2) Retrain
- CLI: `make ml-retrain` (or `make ml-train` for a specific run).
- API: POST `/api/training/train/` with appropriate payload.

3) Check outputs
- Artifacts under `artifacts/` (model files) and `mlruns/` (MLflow runs/registry).
- Logs/monitoring for errors (imbalanced data, missing classes, etc.).

4) Promote
- Use registry rules in `ml/model_versioning.py`; ensure metrics meet thresholds before promotion.

5) Rollback
- Revert to prior promoted version in registry; restore previous artifacts if needed.

Notes
- Monitoring/logging capture model version and features when enabled.
- Ensure storage paths (`artifacts/`, `mlruns/`) have write access in the target environment.
