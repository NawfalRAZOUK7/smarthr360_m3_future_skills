#!/usr/bin/env bash
set -euo pipefail

# Ensure a sample employee exists for Postman/ML tests.
# Defaults: name=Postman Demo, email=postman.employee@example.com, job_role=1 (or first available)

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -x ".venv312/bin/python" ]]; then
  PY_CMD=".venv312/bin/python"
elif [[ -x ".venv/bin/python" ]]; then
  PY_CMD=".venv/bin/python"
else
  PY_CMD="${PYTHON:-python}"
fi

SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.settings.development}"

${PY_CMD} manage.py shell --settings="${SETTINGS_MODULE}" <<'PYCODE'
from future_skills.models import Employee, JobRole, Skill
from django.db import transaction

name = "Postman Demo"
email = "postman.employee@example.com"

with transaction.atomic():
    job_role = JobRole.objects.order_by("id").first()
    if job_role is None:
        print("No JobRole found; skipping employee creation.")
    else:
        emp, created = Employee.objects.get_or_create(
            email=email,
            defaults={
                "name": name,
                "department": job_role.department or "IT",
                "position": job_role.name,
                "job_role": job_role,
                "current_skills": ["Python", "Data Processing"],
            },
        )
        if created:
            # Attach first two skills if available
            skills = list(Skill.objects.all()[:2])
            if skills:
                emp.skills.set(skills)
            emp.save()
            print(f"✅ Created sample employee '{emp}' with job_role '{job_role}'.")
        else:
            print(f"ℹ️  Sample employee already exists: '{emp}'.")
PYCODE
