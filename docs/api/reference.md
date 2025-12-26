# API Reference (Concise)

Auth
- Prod: JWT (intended) and session; tests use session/basic. Anonymous allowed only on specific list endpoints; otherwise permission-protected.
- Permissions in `future_skills/permissions.py`; adjust roles/groups per deployment.

Versioning
- Default v2. v1 deprecated (deprecation headers). Accept-header (`Accept: application/json; version=2`) or path (`/api/v2/...`).

Key endpoints (happy paths)
- Predictions (v2): `GET /api/v2/predictions/`
- Recommendations (v2): `GET /api/v2/recommendations/`
- Training: `POST /api/training/train/` (requires dataset availability)
- Health: `GET /api/health/`, `GET /api/version/`; Metrics (staff-only): `GET /api/metrics/`

Headers/behavior
- Caching: `X-Cache-Hit` plus cache-control headers on cached GETs.
- Throttling: standard DRF rate-limit headers; rates configured per view in `future_skills/api/throttling.py`.
- Deprecation: v1 responses include deprecation headers.

Curl examples (v2)
- Predictions: `curl -H "Accept: application/json; version=2" http://localhost:8000/api/v2/predictions/`
- Recommendations: `curl -H "Accept: application/json; version=2" http://localhost:8000/api/v2/recommendations/`
- Training (minimal):
```bash
curl -X POST http://localhost:8000/api/training/train/ \
  -H "Content-Type: application/json" \
  -d '{"horizon": 3, "async": false}'
```
- Health: `curl http://localhost:8000/api/health/`
- Metrics (staff token): `curl -H "Authorization: Bearer <token>" http://localhost:8000/api/metrics/`

Status/error model (typical)
- 200/201 success; 400 invalid payload; 401/403 auth/perm; 404 unknown resource/version; 429 throttled; 5xx unexpected.
- Expect rate-limit headers on throttled responses; cache headers on cached GETs.

Postman
- Collection: `SmartHR360_M3_FutureSkills.postman_collection.json` (repo root).
