# Runbook: Health & Metrics

Goal: verify service health and metrics exposure.

1) Health/version
- `GET /api/health/` -> 200
- `GET /api/version/` -> 200 with version info

2) Metrics (staff-only)
- `GET /api/metrics/` with staff credentials/token
- Verify Prometheus format and expected gauges/counters are present

3) Smoke API checks
- Predictions/recommendations endpoints return 200 with sample payload
- Rate-limit and cache headers present on GETs

4) If failing
- Check logs (`logs/`, `var/`), DB/cache/broker connectivity, and throttling/caching configs
- Confirm correct settings file loaded and secrets present

5) After fixes
- Re-run health/metrics checks and one sample API flow
