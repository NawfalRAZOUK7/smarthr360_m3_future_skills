# SmartHR360 Future Skills Docs

This folder is the slim, current doc set. Long-form/historical material is in `archived/docs/`.

Start here:
- Dev flow: install (`make install-dev`), run (`make docker-up` or `make serve`), test (`scripts/run_tests.sh ci` or `pytest ...`), deploy (Compose in `compose/`, Dockerfiles in root/`docker/`).
- Ops flow: check health (`/api/health`, `/api/version`), metrics (staff-only), logs (`logs/`, `var/`), throttling/caching headers, alarms.
- ML flow: datasets in `tests/fixtures` for tests; artifacts in `artifacts/`/`mlruns/`; train via Make or API; promote via registry rules.

Structure (kept intentionally small):
- `architecture/` — services, data flows, versioning/authn/authz, storage, key settings.
- `api/` — endpoints, auth model, versioning, headers, examples.
- `ops/` — local/dev/prod steps, observability, security knobs, tuning guidance.
- `ml/` — datasets, training/eval pipeline, model registry, monitoring/logging.
- `runbooks/` — actionable playbooks (throttling/caching, ML recovery, logs/disk, auth/secrets, health/metrics).

Guidelines:
- Keep concise; link to `archived/docs/` for deep dives (legacy architecture diagrams, long checklists).
- Reflect current code: Dockerfiles in root+`docker/`, Compose in `compose/`, requirements in `requirements/`, runtime artifacts in `var/`/`logs/`.
- v1 API is deprecated; v2 default. Anonymous access is limited and throttled. Throttling/caching headers should appear on API responses where applicable.
