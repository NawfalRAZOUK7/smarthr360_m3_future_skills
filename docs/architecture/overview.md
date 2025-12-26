# Architecture Overview

- Diagram: Add a simple system diagram (web + worker + DB/cache + broker + optional monitoring/ML services). Place SVG/PNG in this folder and reference it here.
- Services: Django/DRF web app; Celery workers (training/maintenance queues); optional monitoring endpoints; ML pipeline invoked in-process.
- External deps: DB (SQLite in tests; Postgres/MySQL in prod), cache (locmem in tests; Redis/memcached recommended), message broker for Celery, MLflow backend if enabled.
- Versioning: v2 default, v1 deprecated; Accept-header and path-based; deprecation headers on v1.
- Auth: JWT/session in prod; anonymous only on specific list endpoints; throttled. Permissions in `future_skills/permissions.py`.
- Throttling/Caching: Per-view throttle classes; headers expose limits/countdown. Cache middleware adds `X-Cache-Hit`; configure real cache backend outside tests.
- Storage: App DB, cache, logs (`logs/` + `var/`), ML artifacts (`artifacts/`), MLflow registry/runs (`mlruns/`).
- Deploy topology: Compose bundles in `compose/`; Dockerfiles in root + `docker/`; web + worker + supporting services.
- Config toggles: Key settings in `config/settings/base.py`; test overrides set deterministic SECRET_KEY/DEBUG and disable global throttles. ML flags `FUTURE_SKILLS_USE_ML`, `FUTURE_SKILLS_ENABLE_MONITORING`; dataset fixture path `tests/fixtures/future_skills_dataset.csv` for tests.
