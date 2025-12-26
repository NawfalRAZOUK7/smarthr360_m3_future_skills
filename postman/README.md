# Postman Collections

Base URL variable: set `base_url` in Postman (e.g., `http://localhost:8000`).
Auth: supply valid JWT/session headers for protected endpoints. Metrics is staff-only.

Collections:
- `collection_full.json` — full surface (Auth, Health/Monitoring, API v2, aliases for legacy paths now pointing to v2).
- `collection_api_v2.json` — slim set with Auth, Health/Monitoring, and API v2 endpoints only.
- `collection_smoke.json` — tiny smoke suite (auth token, health/version, v2 predictions/recommendations).

Import either file into Postman. Prefer `collection_api_v2.json` for current API; `collection_full.json` includes the alias groups if you still need them.

Environment:
- `environment.sample.json` — template with `base_url`, `access_token`, `refresh_token`.
- Per-env templates: `environment.dev.json`, `environment.staging.json`, `environment.prod.json` (fill in real URLs/tokens).
- Duplicate in Postman, set values per environment, and select it when running collections.

CLI runner:
- `scripts/run_postman.sh` wraps Newman. Defaults: `collection_api_v2.json` + `environment.dev.json`, reporters `cli,json`, uses `npx newman` when available.
- Examples:
  - `scripts/run_postman.sh` (dev env, v2 collection)
  - `scripts/run_postman.sh -c postman/collection_smoke.json -e postman/environment.staging.json`
  - `scripts/run_postman.sh -r cli,json -o var/newman`
- To install Newman globally: `scripts/install_newman.sh` (uses `npm install -g newman`).
