# Runbook: Throttling & Caching

Goal: adjust throttles and verify cache behavior safely.

1) Identify target views/rates
- Throttle classes live in `future_skills/api/throttling.py`; per-view assignment in views.
- Cache behavior via middleware (adds `X-Cache-Hit`).

2) Change rates (example)
- Update rate strings in throttle classes or DRF settings.
- Deploy/reload service.

3) Verify
- Make repeated requests to targeted endpoint.
- Expect rate-limit headers; confirm 429 after threshold if applicable.
- For caching: first GET should set cache, second GET should return `X-Cache-Hit: true`.

4) Rollback
- Revert rate changes and redeploy.

Notes
- Use a real cache backend (Redis/memcached) in non-test environments.
- Anonymous access is limited and throttled intentionally; avoid broadening without review.
