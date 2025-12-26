# Runbooks

Use these as short, actionable playbooks (no prose):

- **Throttling/caching**: How to adjust throttle rates in `future_skills/api/throttling.py` and DRF settings; clear caches; verify rate-limit and `X-Cache-Hit` headers after changes.
- **ML retrain/recovery**: Steps to retrain via Make targets or API, refresh datasets, recover from failed runs, and re-promote models in the registry (`mlruns/`).
- **Logs/disk**: Rotate/clean `logs/` and `var/`, handle disk pressure, and re-point log paths if needed.
- **Auth/secrets**: Rotate JWT/SECRET_KEY, handle auth failures, and ensure secure settings in non-test environments.
- **Health/metrics**: Validate health/readiness/metrics endpoints, required roles for metrics, and common checks during incidents.
