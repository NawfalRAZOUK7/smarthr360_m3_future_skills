#!/bin/sh
# Entrypoint for ML service
# - Starts ML model server (adjust as needed)

set -e

echo "[Entrypoint] Running dynamic model training..."
python ml/scripts/train_future_skills_model.py --output /app/ml/models
echo "[Entrypoint] Model training complete. Starting ML model server..."
# Example: exec uvicorn ml.serve:app --host 0.0.0.0 --port 5000
exec python ml/serve.py
