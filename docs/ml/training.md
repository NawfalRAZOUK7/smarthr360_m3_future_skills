# Training

Datasets
- Tests use `tests/fixtures/future_skills_dataset.csv` (path set in `config/settings/test.py`).
- Runtime datasets/artifacts: `artifacts/` for models/results; `mlruns/` for MLflow runs/registry (often ignored in git).

Commands/targets
- Prepare dataset: `make ml-prepare`
- Train: `make ml-train` (or API POST to `/api/training/train/`)
- Retrain pipeline: `make ml-retrain`
- Experiments/eval: `make ml-experiment`, `make ml-evaluate`
- Scripts: `ml/scripts/` and `scripts/ml_train.sh`

Behavior
- Training API returns 201 on success; fails with clear errors on missing/imbalanced data (covered by tests).
- Explainability/logging integrated in `future_skills/services/prediction_engine.py` and monitoring modules.

Model registry
- Versioning/promotion rules in `ml/model_versioning.py`; registry data under `mlruns/`. Promotion depends on metrics/stage transitions.

Monitoring
- Prediction logging captures features/model version; Prometheus metrics available when monitoring enabled (`FUTURE_SKILLS_ENABLE_MONITORING`).

Testing
- Fast suite: `pytest ml/tests -m 'not slow'`
- Full suite adds slow/integration as needed; ML flags default off in tests unless overridden.
