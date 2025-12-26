# Operations

Local dev:
- Install: `make install-dev` (uses `requirements/requirements-all.txt`). Run `make migrate` and seed as needed. Tests rely on dataset fixture `tests/fixtures/future_skills_dataset.csv`.
- Run: `make docker-up` (Compose files in `compose/`), or `make serve` for bare Django. Settings default to `config.settings.development`; tests use `config.settings.test` with deterministic SECRET_KEY/DEBUG.

Deployment:
- Compose bundles: `compose/docker-compose.yml` (dev), `docker-compose.prod.yml`, `docker-compose.staging.yml`.
- Dockerfiles: base in `docker/Dockerfile.base`; main build in root `Dockerfile`; role-specific images in `docker/`.
- Make targets: docker-* in main `Makefile`; celery/logging/security targets auto-included from `makefiles/`.

Observability:
- Request performance headers/logging middleware emit timings and DB counts; metrics endpoint is staff-only (Prometheus-friendly).
- Logs live under `logs/` and `var/`; rotate/clean as needed. Config in `config/logging_config.py`.

Security:
- Security scan targets live in `makefiles/Makefile.security` (included by main Makefile). Secrets via env; tests set defaults for SECRET_KEY/DEBUG.
- CORS is open in tests; tighten in production settings. Enable secure cookies/HTTPS in non-test environments.

Tuning:
- Throttling: per-view classes in `future_skills/api/throttling.py`; headers expose limits/countdown. Configure DRF throttle settings per env.
- Caching: middleware returns `X-Cache-Hit`; use Redis/memcached in real deployments (locmem in tests). Tune cache timeouts per path in middleware if needed.
