# Architecture

Current shape (based on recent code/config):
- **Services**: Django/DRF web app; Celery workers (training/maintenance queues); optional monitoring endpoints; ML pipeline invoked in-process. Supporting containers defined in `compose/docker-compose*.yml`.
- **Versioning**: v1 is deprecated; v2 is the default. Header-based versioning accepted; path-based v1/v2 supported for backward compatibility. Deprecation headers emitted on v1.
- **AuthN/AuthZ**: DRF permissions default to `AllowAny` in tests; production uses explicit view permissions. Anonymous access is intentionally limited and throttled (AnonRateThrottle) only on specific list endpoints exercised in tests. Custom permissions in `future_skills/permissions.py`.
- **Throttling/Caching**: Per-view throttle classes in `future_skills/api/throttling.py`; headers returned for limits/countdown. Cache middleware adds `X-Cache-Hit`/control headers. Caches use locmem in tests; configure Redis/memcached in real deploys.
- **Data storage**: Primary DB (SQLite in tests; configure Postgres/MySQL in prod). Cache backend configurable. ML artifacts under `artifacts/` and registry/runs under `mlruns/`. Logs under `logs/` and `var/`.
- **Deployment topology**: Dockerfiles in root + `docker/`; Compose bundles in `compose/` for dev/prod/staging. Web + worker + (optional) monitoring/ML services; external deps: DB, cache, message broker (for Celery), MLflow backend if enabled.
- **Config toggles**: Key settings in `config/settings/base.py`; test overrides in `config/settings/test.py` (sets deterministic SECRET_KEY/DEBUG defaults and disables global throttles). ML flags: `FUTURE_SKILLS_USE_ML`, `FUTURE_SKILLS_ENABLE_MONITORING`; dataset path `tests/fixtures/future_skills_dataset.csv` used in tests.
