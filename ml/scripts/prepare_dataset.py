#!/usr/bin/env python3
"""
prepare_dataset.py - Export Future Skills dataset from Django ORM to CSV for ML workflows.

- Loads data from the Django database using the project root manage.py
- Exports to artifacts/datasets/future_skills_dataset.csv
- Can be run standalone (requires DJANGO_SETTINGS_MODULE)
"""
import os
import sys
from pathlib import Path

import django
import numpy as np
import pandas as pd

# --- Robustly find project root (directory containing manage.py) ---
current = Path(__file__).resolve()
for parent in current.parents:
    if (parent / "manage.py").exists() and (parent / "config").is_dir():
        PROJECT_ROOT = parent
        break
else:
    print(
        "[ERROR] Could not find project root (manage.py/config). Please check your project structure."
    )
    sys.exit(1)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.base")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    import django

    django.setup()
except Exception as e:
    print(f"[ERROR] Could not set up Django: {e}")
    sys.exit(1)

try:
    from future_skills.models import FutureSkillPrediction, JobRole, Skill
except ImportError:
    print(
        "[ERROR] Could not import FutureSkillPrediction model. Is Django app installed?"
    )
    sys.exit(1)


# Query all FutureSkillPrediction objects with select_related for joins
qs = FutureSkillPrediction.objects.select_related("job_role", "skill").all()
if not qs.exists():
    print("[WARN] No data found in FutureSkillPrediction table.")
    sys.exit(0)

# Build records with denormalized fields for ML
records = []
for obj in qs:
    record = {
        "id": obj.id,
        "job_role_id": obj.job_role_id,
        "job_role_name": obj.job_role.name if obj.job_role else None,
        "job_department": obj.job_role.department if obj.job_role else None,
        "skill_id": obj.skill_id,
        "skill_name": obj.skill.name if obj.skill else None,
        "skill_category": obj.skill.category if obj.skill else None,
        "horizon_years": obj.horizon_years,
        "score": obj.score,
        "future_need_level": obj.level,
        "rationale": obj.rationale,
        "explanation": obj.explanation,
        "created_at": obj.created_at,
    }
    # Placeholders for features not in model (for ML script compatibility)
    record["trend_score"] = None
    record["internal_usage"] = None
    record["training_requests"] = None
    record["scarcity_index"] = None
    record["hiring_difficulty"] = None
    record["avg_salary_k"] = None
    record["economic_indicator"] = None
    records.append(record)

df = pd.DataFrame(records)


# --- Fill numeric features with synthetic data for testing ---
numeric_features = [
    "trend_score",
    "internal_usage",
    "training_requests",
    "scarcity_index",
    "hiring_difficulty",
    "avg_salary_k",
    "economic_indicator",
]
np.random.seed(42)
for col in numeric_features:
    if col in df.columns:
        # Only fill if all values are missing or NaN
        if df[col].isnull().all():
            if col == "trend_score":
                df[col] = np.random.uniform(0, 1, size=len(df))
            elif col == "internal_usage":
                df[col] = np.random.uniform(0, 100, size=len(df))
            elif col == "training_requests":
                df[col] = np.random.poisson(10, size=len(df))
            elif col == "scarcity_index":
                df[col] = np.random.uniform(0, 1, size=len(df))
            elif col == "hiring_difficulty":
                df[col] = np.random.uniform(0, 10, size=len(df))
            elif col == "avg_salary_k":
                df[col] = np.random.normal(50, 10, size=len(df))
            elif col == "economic_indicator":
                df[col] = np.random.normal(1, 0.2, size=len(df))

# Output path
output_dir = PROJECT_ROOT / "artifacts" / "datasets"
output_dir.mkdir(parents=True, exist_ok=True)
output_path = output_dir / "future_skills_dataset.csv"

df.to_csv(output_path, index=False)
print(f"[SUCCESS] Exported dataset to {output_path}")
