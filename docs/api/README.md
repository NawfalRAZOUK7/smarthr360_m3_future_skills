# API

AuthN/AuthZ:
- Supports session/basic in tests; production expects JWT from `auth` via JWKS (`AUTH_JWKS_URL`) or shared secret (`AUTH_JWT_SHARED_SECRET`).
- If using shared secret, keep `AUTH_LOCAL_ENABLED=False` to avoid ambiguity.
- Local auth endpoints are gated by `AUTH_LOCAL_ENABLED`.
- Tokens must provide `email` + `role` (or `AUTH_USERINFO_URL` must be configured to fetch them).
- Anonymous is allowed only on specific list endpoints validated by tests; everything else is permission-protected.
- Custom DRF permissions live in `future_skills/permissions.py`; align roles/groups before exposing externally.

Versioning:
- v2 is default; v1 is deprecated. Accept-header and path-based versioning are both supported. Deprecation headers are returned on v1 responses.
- Health/version endpoints: `/api/health`, `/api/version`; metrics endpoints are security-admin only.

Core endpoints (high level):
- Predictions/Recommendations: list/retrieve via versioned URLs/headers. Caching enabled; warm responses include `X-Cache-Hit`.
- Training: POST to train model; tests use the fixture dataset. Returns 201 on success; fails with clear errors if data missing/imbalanced.
- Health/metrics: liveness/readiness/metrics endpoints; metrics require security-admin permission.

Headers/behavior:
- Caching: `X-Cache-Hit` plus standard cache-control headers from middleware.
- Throttling: rate-limit headers present; throttle classes in `future_skills/api/throttling.py`.
- Deprecation: v1 responses include deprecation headers.
- Response envelope (optional): add `X-Response-Envelope: 1` or `?envelope=1` to receive `{"data": ..., "meta": {"success": true}}` (auth-compatible).

Usage/examples:
- Postman collections: `postman/collection_api_v2.json` (preferred current surface) or `postman/collection_full.json` (includes alias groups).
- Curl: include Accept version header (`Accept: application/json; version=2`) or use `/api/v2/...` paths.
- Top-N rankings: `GET /api/v2/predictions/top-rankings/` supports `group_by`, `top_n`, `as_of_date`, `normalize`, and `include_relevance` (adds `relevance` payload).
- Slice metrics refresh: `POST /api/metrics/slice-performance/refresh/` (security-admin only) pushes latest slice metrics into Prometheus gauges.

Env setup (local quickstart):
- `cp .env.template .env` puis remplacer `SECRET_KEY` et `AUTH_JWT_SHARED_SECRET` (SECRET_KEY de auth) si vous consommez les tokens auth en HS256.
- Port auth par défaut: `http://127.0.0.1:8000` → `AUTH_USERINFO_URL=http://127.0.0.1:8000/api/auth/me/`.
