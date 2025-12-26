# Observability

Request visibility
- Middleware adds performance headers (timings, DB queries) and logging.
- Rate-limit headers from throttle classes; cache middleware adds `X-Cache-Hit`.

Metrics
- `/api/metrics/` is staff-only; Prometheus-friendly output.
- Prediction logging/monitoring hooks record features and model version when enabled.

Logs
- Default log paths: `logs/` and `var/` (app/worker/health/security/performance depending on config).
- Config: `config/logging_config.py`; tests reduce verbosity to ERROR.

Where to look first
- Slow requests: performance logs + response headers; check cache hit/miss and DB query count.
- Throttling issues: rate-limit headers + throttle classes in `future_skills/api/throttling.py`.
- Cache misses: ensure cache backend configured (Redis/memcached), inspect `X-Cache-Hit`.
- ML issues: artifacts/logs under `artifacts/`, `mlruns/`; monitoring/logging hooks in prediction/monitoring modules.
