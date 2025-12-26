# API

AuthN/AuthZ:
- Supports session/basic in tests; JWT is the intended production auth. Anonymous is allowed only on specific list endpoints validated by tests; everything else is permission-protected.
- Custom DRF permissions live in `future_skills/permissions.py`; align roles/groups before exposing externally.

Versioning:
- v2 is default; v1 is deprecated. Accept-header and path-based versioning are both supported. Deprecation headers are returned on v1 responses.
- Health/version endpoints: `/api/health`, `/api/version`; metrics endpoint is staff-only.

Core endpoints (high level):
- Predictions/Recommendations: list/retrieve via versioned URLs/headers. Caching enabled; warm responses include `X-Cache-Hit`.
- Training: POST to train model; tests use the fixture dataset. Returns 201 on success; fails with clear errors if data missing/imbalanced.
- Health/metrics: liveness/readiness/metrics endpoints; metrics require staff permission.

Headers/behavior:
- Caching: `X-Cache-Hit` plus standard cache-control headers from middleware.
- Throttling: rate-limit headers present; throttle classes in `future_skills/api/throttling.py`.
- Deprecation: v1 responses include deprecation headers.

Usage/examples:
- Postman collections: `postman/collection_api_v2.json` (preferred current surface) or `postman/collection_full.json` (includes alias groups).
- Curl: include Accept version header (`Accept: application/json; version=2`) or use `/api/v2/...` paths.
