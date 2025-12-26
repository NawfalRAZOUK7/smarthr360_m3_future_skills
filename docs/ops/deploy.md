# Deploy

Compose
- Dev: `compose/docker-compose.yml`
- Staging: `compose/docker-compose.staging.yml`
- Prod: `compose/docker-compose.prod.yml`

Dockerfiles
- Base image: `docker/Dockerfile.base`
- Main app build: root `Dockerfile`
- Role-specific images: `docker/` (e.g., worker, nginx, etc.)

Secrets/env (per env)
- `SECRET_KEY`, DB connection, cache/broker URLs, JWT settings, allowed hosts, CORS, logging level, throttle/cache rates.

Commands
- Build: `make docker-build`
- Up/down: `make docker-up` / `make docker-down`
- Prod stack: `docker compose -f compose/docker-compose.prod.yml up -d --build`

Verification checklist after deploy
- Health: `GET /api/health/` (200), `GET /api/version/`
- Metrics (staff): `GET /api/metrics/`
- Sample prediction call returns 200 with expected payload
- Rate-limit headers present; `X-Cache-Hit` appears after second cached GET
- Logs writable under `logs/`/`var/`
