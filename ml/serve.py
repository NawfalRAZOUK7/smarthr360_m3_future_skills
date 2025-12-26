# Minimal FastAPI ML serving app for Future Skills model
import os

import joblib
import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

MODEL_PATH = os.environ.get("MODEL_PATH", "/app/ml/models_v1.pkl")


class InputData(BaseModel):
    job_role_name: str
    skill_name: str
    skill_category: str
    job_department: str
    trend_score: float
    internal_usage: float
    training_requests: float
    scarcity_index: float
    hiring_difficulty: float
    avg_salary_k: float
    economic_indicator: float


@app.on_event("startup")
def load_model():
    global model
    model = joblib.load(MODEL_PATH)


@app.post("/predict")
def predict(data: InputData):
    columns = [
        "job_role_name",
        "skill_name",
        "skill_category",
        "job_department",
        "trend_score",
        "internal_usage",
        "training_requests",
        "scarcity_index",
        "hiring_difficulty",
        "avg_salary_k",
        "economic_indicator",
    ]
    X = pd.DataFrame([[getattr(data, col) for col in columns]], columns=columns)
    y_pred = model.predict(X)
    return {"prediction": y_pred[0]}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)  # nosec B104
