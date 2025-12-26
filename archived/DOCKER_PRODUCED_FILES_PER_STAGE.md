# Multi-Stage Build: Produced Files Documentation

This document details the files and artifacts produced in each stage of the multi-stage Dockerfiles for all main services.

## 1. web (Django/Gunicorn)

**builder stage:**

- /app/staticfiles/ (collected static files)
- (optional) /app/frontend/dist/ (built frontend assets, if any)
- All app code and config (for build context)

**final stage:**

- /app/manage.py, /app/pyproject.toml, /app/pytest.ini
- /app/config/, /app/future_skills/
- /app/staticfiles/ (from builder)

## 2. celery (Celery Worker)

**builder stage:**

- /app/ml/models/ (trained ML models or artifacts, if built at image build time)
- All app code and config (for build context)

**final stage:**

- /app/manage.py, /app/pyproject.toml, /app/pytest.ini
- /app/config/, /app/future_skills/, /app/celery_monitoring/
- /app/ml/models/ (from builder)

## 3. ML Service

**builder stage:**

- /app/ml/models/ (trained ML models/artifacts)
- /app/ml/ (ML code, requirements, scripts)

**final stage:**

- /app/ml/models/ (from builder)
- /app/ml/ (serving code, requirements, scripts)

## 4. nginx

**builder stage:**

- /build/nginx.conf (custom config)
- (optional) /build/static/ (built static assets, if any)

**final stage:**

- /etc/nginx/nginx.conf (from builder)
- /usr/share/nginx/html/ (static assets, if any, from builder)

---

For each Dockerfile, the final image contains only the files needed for runtime. All build dependencies and intermediate files remain in the builder stage, keeping the runtime image minimal and secure.
