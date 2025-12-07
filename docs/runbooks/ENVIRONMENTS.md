# Environment Asset Matrix

This runbook explains which container definitions, Makefiles, and requirements sets map to each environment so you can activate the right stack without guesswork.

## Container Images (Dockerfile.\*)

| File                | Use Case                                                                                                                                     | Typical Command                                            |
| ------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| `Dockerfile`        | Production Django API image (multi-stage build with static collection, non-root user, Gunicorn entrypoint).                                  | `docker build -f Dockerfile -t smarthr360/api:latest .`    |
| `Dockerfile.simple` | Lightweight single-stage image for quick smoke tests in CI or local demos. Installs only base requirements and collects static files inline. | `docker build -f Dockerfile.simple -t smarthr360/demo .`   |
| `Dockerfile.celery` | Dedicated Celery worker image with ML + Celery dependencies preinstalled and worker entrypoint.                                              | `docker build -f Dockerfile.celery -t smarthr360/celery .` |
| `Dockerfile.nginx`  | Nginx reverse proxy for production/static hosting. Exposes 80/443 and expects config from `nginx/`.                                          | `docker build -f Dockerfile.nginx -t smarthr360/nginx .`   |

> **Compose stacks**: Use `docker-compose.yml` for local dev (web + db + redis) and `docker-compose.prod.yml` for the production-like stack that stitches the API, Celery, and Nginx images together.

## Makefiles

| File                | Focus                                                                                              | How to Invoke                                                                        |
| ------------------- | -------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| `Makefile`          | Primary developer workflows: installs, test suites, lint/format, Docker orchestration, ML helpers. | `make install-dev`, `make test-ml`, `make docker-up`, etc.                           |
| `Makefile.celery`   | Celery worker/beat/Flower management plus DLQ utilities and monitoring helpers.                    | `make -f Makefile.celery celery-worker`, `make -f Makefile.celery celery-beat`, etc. |
| `Makefile.logging`  | Logging, metrics, and health-check operations (tail logs, analyze, rotate, run APM tests).         | `make -f Makefile.logging logs-tail`, `... logging-help`.                            |
| `Makefile.security` | Security scans, JWT/rate-limit tests, incident-response shortcuts, dependency audits.              | `make -f Makefile.security security-scan`, `... security-test-jwt`.                  |

> You can either run these standalone via `make -f Makefile.<variant> <target>` or copy the targets into the primary Makefile if you want a single entrypoint.

## Python Requirements Sets

| File                        | Purpose                                                                                             | Install Command                            |
| --------------------------- | --------------------------------------------------------------------------------------------------- | ------------------------------------------ |
| `requirements.txt`          | Core production stack (Django, DRF, Celery, Prometheus, ML base libs).                              | `pip install -r requirements.txt`          |
| `requirements-dev.txt`      | Extends core stack with pytest, coverage, linting, typing, and dev-only tooling.                    | `pip install -r requirements-dev.txt`      |
| `requirements_ml.txt`       | Data-science extras for experiments (pandas, sklearn, SHAP/LIME, plotting).                         | `pip install -r requirements_ml.txt`       |
| `requirements_celery.txt`   | Monitoring/observability packages for Celery (Flower, django-celery-\*, Prometheus, redis tooling). | `pip install -r requirements_celery.txt`   |
| `requirements_logging.txt`  | Structured logging + APM integrations (structlog, Elastic APM, Sentry, log shipping).               | `pip install -r requirements_logging.txt`  |
| `requirements_security.txt` | Security scanning, JWT/cors headers, auth hardening, and incident-response helpers.                 | `pip install -r requirements_security.txt` |

## Quick Recipes

- **Local development**: `pip install -r requirements-dev.txt` → `make setup` → `make docker-up` (uses `docker-compose.yml` and the main `Dockerfile`).
- **Production build**: `docker build -f Dockerfile ...` then run via `docker-compose -f docker-compose.prod.yml up -d --build` or your deployment target.
- **Celery/async stack**: Build `Dockerfile.celery`, run workers via `make -f Makefile.celery celery-worker`, monitor with Flower (`make ... celery-flower`).
- **Logging & health checks**: Ensure `requirements_logging.txt` is installed (already covered by main image), then use `make -f Makefile.logging logs-setup` / `health-check` / `metrics-view` as needed.
- **Security hardening**: `pip install -r requirements_security.txt` (if not already) and run `make -f Makefile.security security-scan` before releases.
- **ML experimentation**: `pip install -r requirements_ml.txt`, then leverage `make test-ml` / `ml-prepare` / `ml-train` targets from the main Makefile or run notebooks/scripts under `ml/`.

Keep this matrix updated whenever a new Dockerfile, Makefile variant, or requirements file is introduced so everyone knows which artifact powers which environment.
