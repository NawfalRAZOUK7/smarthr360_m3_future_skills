# Machine Learning

Datasets & artifacts:
- Tests use `tests/fixtures/future_skills_dataset.csv` (set in `config/settings/test.py`).
- Runtime artifacts: `artifacts/` for models/results, `mlruns/` for MLflow runs/registry (often ignored in git). Ensure storage paths exist in deployments.

Training & evaluation:
- Scripts: `ml/scripts/` and helper `scripts/ml_train.sh`. Make targets: `ml-prepare`, `ml-train`, `ml-retrain`, `ml-experiment`, `ml-evaluate`.
- Training API relies on dataset availability; tests verify success and expected failures on missing/imbalanced data.
- Explainability/logging integrated in `future_skills/services/prediction_engine.py` and monitoring modules.

Model registry:
- Versioning/promotion rules in `ml/model_versioning.py`; registry data under `mlruns/`. Promotion depends on metrics and stage transitions.

Monitoring:
- Prediction logging captures features/model version; Prometheus metrics exposed when monitoring is enabled. Toggles in settings (`FUTURE_SKILLS_ENABLE_MONITORING`, `FUTURE_SKILLS_USE_ML`).

Testing:
- Fast ML suite: `pytest ml/tests -m 'not slow'`.
- Full/slow tests and integration can be added as needed; ML flags default off in tests but can be enabled via settings overrides.
