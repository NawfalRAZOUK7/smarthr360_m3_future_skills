# API Architecture Guide

## Overview

The SmartHR360 Future Skills API has been architected with enterprise-grade features for scalability, performance, and maintainability. This guide covers the complete API architecture including versioning, rate limiting, caching, monitoring, and best practices.

**Implementation Date**: 2025-11-28  
**Current API Version**: v2  
**Status**: Production Ready

---

## Table of Contents

1. [API Versioning](#api-versioning)
2. [Rate Limiting & Throttling](#rate-limiting--throttling)
3. [Performance Optimization](#performance-optimization)
4. [Caching Strategy](#caching-strategy)
5. [Monitoring & Health Checks](#monitoring--health-checks)
6. [API Endpoints](#api-endpoints)
7. [Best Practices](#best-practices)
8. [Migration Guide](#migration-guide)

---

## 1. API Versioning

### 1.1 Versioning Strategy

The API uses **URL path versioning** as the primary method:

```
/api/v1/...  (Deprecated, sunset: 2026-06-01)
/api/v2/...  (Current)
```

**Alternative methods** (also supported):

- Accept header: `Accept: application/vnd.smarthr360.v2+json`
- Query parameter: `?version=v2` (not recommended for production)

### 1.2 Version Information

| Version | Status     | Released   | Deprecated | Sunset Date |
| ------- | ---------- | ---------- | ---------- | ----------- |
| v1      | Deprecated | 2024-01-01 | 2025-12-01 | 2026-06-01  |
| v2      | Current    | 2025-01-01 | -          | -           |

### 1.3 V2 Improvements

**Enhanced Features**:

- Improved pagination with cursor support
- Better error responses with detailed codes
- Optimized bulk operations
- Consistent ISO 8601 datetime formatting
- Enhanced filtering and search capabilities
- Better URL organization (namespaced ML operations)

**URL Changes (v1 → v2)**:

```
# Predictions
/api/v1/future-skills/           → /api/v2/predictions/
/api/v1/future-skills/recalculate/ → /api/v2/predictions/recalculate/

# Recommendations
/api/v1/hr-investment-recommendations/ → /api/v2/recommendations/

# ML Operations (now namespaced)
/api/v1/predict-skills/          → /api/v2/ml/predict/
/api/v1/recommend-skills/        → /api/v2/ml/recommend/
/api/v1/bulk-predict/            → /api/v2/ml/bulk-predict/
/api/v1/train-model/             → /api/v2/ml/train/
/api/v1/training-runs/           → /api/v2/ml/training-runs/

# Bulk Operations
/api/v1/bulk-import/employees/   → /api/v2/bulk/employees/import/
/api/v1/bulk-upload/employees/   → /api/v2/bulk/employees/upload/
```

### 1.4 Using API Versions

**URL Path Versioning** (Recommended):

```bash
# v2 (current)
curl https://api.smarthr360.com/api/v2/predictions/

# v1 (deprecated)
curl https://api.smarthr360.com/api/v1/future-skills/
```

**Accept Header Versioning**:

```bash
curl -H "Accept: application/vnd.smarthr360.v2+json" \
     https://api.smarthr360.com/api/predictions/
```

**Query Parameter Versioning** (Not recommended):

```bash
curl https://api.smarthr360.com/api/predictions/?version=v2
```

### 1.5 Deprecation Warnings

When using deprecated versions, responses include:

**Headers**:

```
X-API-Deprecation: API version v1 is deprecated. Please migrate to v2. v1 will be sunset on 2026-06-01.
X-API-Sunset-Date: 2026-06-01
Link: </api/docs/migration/>; rel="deprecation"
```

**Response Body** (for JSON responses):

```json
{
  "data": {...},
  "_deprecation": {
    "warning": "API version v1 is deprecated. Please migrate to v2. v1 will be sunset on 2026-06-01.",
    "sunset_date": "2026-06-01",
    "migration_guide": "/api/docs/migration/"
  }
}
```

### 1.6 Backward Compatibility

**Default behavior**: Requests to `/api/` without version prefix route to v2:

```bash
# These are equivalent:
/api/predictions/
/api/v2/predictions/
```

**For v1 clients**: Explicitly use `/api/v1/` prefix until migration is complete.

---

## 2. Rate Limiting & Throttling

### 2.1 Throttling Tiers

The API implements multiple throttling strategies:

| Tier                | Rate Limit | Scope         | Description                   |
| ------------------- | ---------- | ------------- | ----------------------------- |
| **Anonymous**       | 100/hour   | Global        | Unauthenticated requests      |
| **User**            | 1000/hour  | Global        | Authenticated users (default) |
| **Burst**           | 60/minute  | Global        | Short-term spike protection   |
| **Sustained**       | 10000/day  | Global        | Long-term abuse prevention    |
| **Premium**         | 5000/hour  | Staff/Premium | Staff and premium users       |
| **ML Operations**   | 10/hour    | Per-endpoint  | Training, predictions         |
| **Bulk Operations** | 30/hour    | Per-endpoint  | Imports, uploads              |
| **Health Check**    | 300/minute | Per-endpoint  | Monitoring endpoints          |

### 2.2 Rate Limit Headers

Every API response includes rate limit information:

```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 847
X-RateLimit-Reset: 1735401600
```

**Header Meanings**:

- `X-RateLimit-Limit`: Total requests allowed in current window
- `X-RateLimit-Remaining`: Requests remaining in current window
- `X-RateLimit-Reset`: Unix timestamp when current window resets

### 2.3 Throttled Response

When rate limit is exceeded:

```http
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1735401600
Retry-After: 3600

{
  "detail": "Request was throttled. Expected available in 3600 seconds."
}
```

### 2.4 Bypassing Throttles

**Whitelisted IPs**: Configure in settings:

```python
THROTTLE_BYPASS_IPS = ['10.0.0.1', '192.168.1.100']
```

**Superusers**: Automatically bypass all throttles.

**Premium Users**: Staff and users with `is_premium=True` get higher limits.

### 2.5 Endpoint-Specific Throttling

Some endpoints have custom throttling:

```python
# ML Operations (resource-intensive)
/api/v2/ml/train/           → 10 requests/hour
/api/v2/ml/bulk-predict/    → 10 requests/hour

# Bulk Operations (database-intensive)
/api/v2/bulk/employees/import/ → 30 requests/hour

# Health Checks (monitoring)
/api/health/                → 300 requests/minute
```

---

## 3. Performance Optimization

### 3.1 Response Time Headers

Every response includes performance metrics:

```http
HTTP/1.1 200 OK
X-Response-Time: 142ms
X-DB-Queries: 3
X-Cache-Hit: false
```

**Headers Explained**:

- `X-Response-Time`: Total request processing time
- `X-DB-Queries`: Number of database queries executed
- `X-Cache-Hit`: Whether response was served from cache

### 3.2 Database Query Optimization

**Implemented optimizations**:

- 38 strategic database indexes across 9 models
- Automatic `select_related()` for ForeignKeys
- Bulk operations optimized with `bulk_create()`
- Database connection pooling

**Performance gains**:

- Simple queries: 70-80% faster
- Complex queries: 60-85% faster
- Bulk operations: 50-70% faster

See [Database Optimization Guide](DATABASE_OPTIMIZATION.md) for details.

### 3.3 Pagination

**Default pagination**:

```
?page=1&page_size=10
```

**Customizable page size** (max 100):

```
?page=1&page_size=50
```

**Response format**:

```json
{
  "count": 250,
  "next": "https://api.smarthr360.com/api/v2/predictions/?page=2",
  "previous": null,
  "results": [...]
}
```

### 3.4 Monitoring Slow Requests

Requests taking over 1 second are automatically logged:

```
[WARNING] Slow API request: GET /api/v2/predictions/ took 1523ms
```

**Targets**:

- Average response time: < 200ms
- P95 response time: < 500ms
- P99 response time: < 1000ms

---

## 4. Caching Strategy

### 4.1 Cache Configuration

**Development**: Local memory cache

```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'TIMEOUT': 300,  # 5 minutes
    }
}
```

**Production**: Redis cache

```python
CACHE_URL=redis://localhost:6379/1

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://localhost:6379/1',
        'TIMEOUT': 300,
    }
}
```

### 4.2 Cache Timeouts by Endpoint

| Endpoint                    | Cache Duration | Reason             |
| --------------------------- | -------------- | ------------------ |
| `/api/v2/predictions/`      | 5 minutes      | Frequently updated |
| `/api/v2/recommendations/`  | 5 minutes      | Dynamic data       |
| `/api/v2/employees/`        | 3 minutes      | User-managed data  |
| `/api/v2/market-trends/`    | 10 minutes     | Relatively static  |
| `/api/v2/economic-reports/` | 10 minutes     | Relatively static  |
| Skills, Job Roles           | 1 hour         | Reference data     |

### 4.3 Cache Invalidation

**Automatic invalidation** on:

- POST, PUT, PATCH, DELETE requests
- Recalculation operations
- Model training completion

**Manual cache clearing**:

```bash
python manage.py shell
>>> from django.core.cache import cache
>>> cache.clear()
```

### 4.4 Cache Headers

Responses include cache control headers:

```http
Cache-Control: max-age=300
X-Cache-Hit: true
```

### 4.5 Bypassing Cache

To bypass cache for debugging:

```bash
# Add unique query parameter
curl https://api.smarthr360.com/api/v2/predictions/?_nocache=true
```

---

## 5. Monitoring & Health Checks

### 5.1 Health Check Endpoints

| Endpoint        | Purpose                | Response Time |
| --------------- | ---------------------- | ------------- |
| `/api/health/`  | Overall system health  | < 100ms       |
| `/api/ready/`   | Readiness for traffic  | < 200ms       |
| `/api/alive/`   | Liveness check         | < 50ms        |
| `/api/version/` | API version info       | < 50ms        |
| `/api/metrics/` | System metrics (staff) | < 500ms       |

### 5.2 Health Check Response

**GET /api/health/**

```json
{
  "status": "healthy",
  "timestamp": "2025-11-28T14:30:00Z",
  "checks": {
    "database": {
      "status": "healthy",
      "type": "django.db.backends.postgresql"
    },
    "cache": {
      "status": "healthy"
    }
  }
}
```

**Status codes**:

- `200 OK`: All systems healthy
- `503 Service Unavailable`: System degraded

### 5.3 Readiness Check

**GET /api/ready/**

Checks if service is ready to accept traffic:

- Database connectivity
- Migrations applied
- Cache availability

```json
{
  "ready": true,
  "timestamp": "2025-11-28T14:30:00Z",
  "checks": {
    "database": "passed",
    "migrations": "passed",
    "cache": "passed"
  }
}
```

### 5.4 Metrics Endpoint

**GET /api/metrics/** (Staff only)

```json
{
  "timestamp": "2025-11-28T14:30:00Z",
  "system": {
    "platform": "Darwin-21.6.0",
    "python_version": "3.12.0"
  },
  "database": {
    "status": "connected",
    "engine": "postgresql",
    "table_count": 25
  },
  "cache": {
    "status": "available",
    "backend": "django_redis.cache.RedisCache"
  },
  "api": {
    "models": {
      "skills": 150,
      "job_roles": 45,
      "predictions": 8934,
      "employees": 523
    },
    "rate_limits": {
      "anon": "100/hour",
      "user": "1000/hour",
      ...
    }
  }
}
```

### 5.5 Request Logging

All API requests are logged with:

- Method and path
- User information
- Response status
- Duration
- Query parameters (sanitized)

Example log entry:

```
[INFO] API Request: GET /api/v2/predictions/ | User: user:42(john.doe) | Status: 200 | Duration: 142ms | Params: {'page': ['1'], 'page_size': ['10']}
```

---

## 6. API Endpoints

### 6.1 Endpoint Structure (v2)

```
/api/v2/
├── predictions/              # Future skill predictions
│   ├── GET                  # List predictions
│   └── recalculate/         # POST - Trigger recalculation
├── recommendations/         # HR investment recommendations
│   └── GET                  # List recommendations
├── employees/               # Employee management
│   ├── GET, POST           # List, create
│   ├── {id}/               # GET, PUT, PATCH, DELETE
│   ├── {id}/predictions/   # GET - Employee predictions
│   └── {id}/skill-gap-report/ # GET - Skill gap analysis
├── market-trends/           # Market trend data
│   └── GET                  # List trends
├── economic-reports/        # Economic indicators
│   └── GET                  # List reports
├── ml/                      # ML operations (namespaced)
│   ├── predict/            # POST - Single prediction
│   ├── recommend/          # POST - Skill recommendations
│   ├── bulk-predict/       # POST - Batch predictions
│   ├── train/              # POST - Train model
│   └── training-runs/      # GET - Training history
│       └── {id}/           # GET - Training details
└── bulk/                    # Bulk operations
    └── employees/
        ├── import/         # POST - JSON import
        └── upload/         # POST - File upload
```

### 6.2 Common Query Parameters

**Filtering**:

```
?job_role=5
?skill=10
?horizon=3
?level=HIGH
?priority_level=MEDIUM
```

**Ordering**:

```
?ordering=-created_at
?ordering=score
```

**Search**:

```
?search=python
```

**Pagination**:

```
?page=1
?page_size=20
```

### 6.3 Response Format

**Success Response**:

```json
{
  "count": 250,
  "next": "...",
  "previous": null,
  "results": [...]
}
```

**Error Response**:

```json
{
  "error": "Validation failed",
  "detail": "Invalid job_role ID",
  "code": "invalid_input"
}
```

---

## 7. Best Practices

### 7.1 API Client Best Practices

**1. Always use versioned URLs**:

```python
# ✅ Good
base_url = "https://api.smarthr360.com/api/v2/"

# ❌ Bad (implicit version)
base_url = "https://api.smarthr360.com/api/"
```

**2. Handle rate limit headers**:

```python
response = requests.get(url)
remaining = int(response.headers.get('X-RateLimit-Remaining', 0))
if remaining < 10:
    time.sleep(60)  # Back off when approaching limit
```

**3. Implement exponential backoff for 429 responses**:

```python
for attempt in range(max_retries):
    response = requests.get(url)
    if response.status_code != 429:
        break
    retry_after = int(response.headers.get('Retry-After', 60))
    time.sleep(retry_after * (2 ** attempt))
```

**4. Cache responses client-side**:

```python
# Respect Cache-Control headers
max_age = parse_cache_control(response.headers.get('Cache-Control'))
cache.set(url, response.data, timeout=max_age)
```

**5. Use pagination efficiently**:

```python
# Don't fetch all pages at once
# Process results incrementally
page = 1
while True:
    response = fetch_page(page)
    process_results(response['results'])
    if not response['next']:
        break
    page += 1
```

### 7.2 Error Handling

**Common HTTP Status Codes**:

| Code | Meaning             | Action                        |
| ---- | ------------------- | ----------------------------- |
| 200  | Success             | Process response              |
| 201  | Created             | Resource created successfully |
| 400  | Bad Request         | Fix request parameters        |
| 401  | Unauthorized        | Check authentication          |
| 403  | Forbidden           | Check permissions             |
| 404  | Not Found           | Check resource ID             |
| 429  | Too Many Requests   | Implement backoff             |
| 500  | Server Error        | Retry with backoff            |
| 503  | Service Unavailable | Check health endpoint         |

**Example error handling**:

```python
try:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.json()
except requests.exceptions.Timeout:
    logger.error(f"Request timeout: {url}")
    # Retry with exponential backoff
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 429:
        # Handle rate limiting
        retry_after = int(e.response.headers.get('Retry-After', 60))
        time.sleep(retry_after)
    elif e.response.status_code >= 500:
        # Server error - retry
        time.sleep(5)
    else:
        # Client error - don't retry
        raise
```

### 7.3 Performance Optimization

**1. Use bulk operations when possible**:

```python
# ✅ Good - bulk operation
POST /api/v2/ml/bulk-predict/
{
  "employees": [1, 2, 3, 4, 5],
  "horizon": 3
}

# ❌ Bad - multiple single requests
for employee_id in [1, 2, 3, 4, 5]:
    POST /api/v2/ml/predict/
```

**2. Request only needed fields** (when supported):

```python
# Future enhancement: field selection
GET /api/v2/predictions/?fields=id,score,level
```

**3. Use appropriate page sizes**:

```python
# Balance between request count and response size
GET /api/v2/predictions/?page_size=50  # Good for most cases
```

**4. Leverage caching**:

```python
# Reference data (skills, job roles) changes infrequently
# Cache locally for 1 hour
cache.set('skills', fetch_skills(), timeout=3600)
```

---

## 8. Migration Guide

### 8.1 Migrating from v1 to v2

**Step 1: Update Base URL**

```python
# Old
BASE_URL = "https://api.smarthr360.com/api/v1/"

# New
BASE_URL = "https://api.smarthr360.com/api/v2/"
```

**Step 2: Update Endpoint Paths**

See [Section 1.3](#13-v2-improvements) for complete mapping.

**Key changes**:

```python
# Predictions
"future-skills/" → "predictions/"

# Recommendations
"hr-investment-recommendations/" → "recommendations/"

# ML Operations (now under /ml/)
"predict-skills/" → "ml/predict/"
"recommend-skills/" → "ml/recommend/"
"train-model/" → "ml/train/"

# Bulk Operations (now under /bulk/)
"bulk-import/employees/" → "bulk/employees/import/"
```

**Step 3: Update Response Handling**

v2 uses consistent ISO 8601 datetime formatting:

```python
# v1
"created_at": "2025-11-28 14:30:00"

# v2
"created_at": "2025-11-28T14:30:00Z"

# Parsing
from datetime import datetime
dt = datetime.fromisoformat(response['created_at'].replace('Z', '+00:00'))
```

**Step 4: Test Thoroughly**

1. Run integration tests against v2 endpoints
2. Compare v1 and v2 responses for consistency
3. Monitor error rates after deployment

**Step 5: Gradual Rollout**

```python
# Feature flag approach
if use_api_v2:
    client = APIv2Client()
else:
    client = APIv1Client()
```

### 8.2 Migration Timeline

| Date       | Milestone                     |
| ---------- | ----------------------------- |
| 2025-11-28 | v2 released, v1 deprecated    |
| 2026-01-01 | v2 becomes default            |
| 2026-03-01 | v1 sunset warning intensifies |
| 2026-06-01 | v1 removed, v2 only           |

### 8.3 Support During Migration

- v1 will continue to function until 2026-06-01
- Deprecation warnings added to v1 responses
- Migration guide available at `/api/docs/migration/`
- Support team available for migration assistance

---

## 9. Security Considerations

### 9.1 Authentication

Currently supports:

- Session Authentication
- Basic Authentication

**Future enhancements**:

- JWT tokens
- OAuth 2.0
- API key authentication

### 9.2 HTTPS

**Always use HTTPS in production**:

```python
# ✅ Good
BASE_URL = "https://api.smarthr360.com"

# ❌ Bad (development only)
BASE_URL = "http://api.smarthr360.com"
```

### 9.3 Sensitive Data

Never include sensitive data in URL parameters:

```python
# ❌ Bad
GET /api/v2/predictions/?api_key=secret123

# ✅ Good
GET /api/v2/predictions/
Authorization: Bearer <token>
```

### 9.4 CORS

CORS is configured for API endpoints:

```http
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST, PUT, PATCH, DELETE, OPTIONS
Access-Control-Allow-Headers: Content-Type, Authorization
```

**Production**: Configure specific allowed origins in settings.

---

## 10. Troubleshooting

### 10.1 Common Issues

**Issue: 429 Too Many Requests**

- **Cause**: Rate limit exceeded
- **Solution**: Implement exponential backoff, check `Retry-After` header
- **Prevention**: Monitor `X-RateLimit-Remaining` header

**Issue: Slow Response Times**

- **Cause**: Large page size, complex queries
- **Solution**: Reduce page size, add filters, use caching
- **Check**: `X-Response-Time` and `X-DB-Queries` headers

**Issue: 503 Service Unavailable**

- **Cause**: Database or cache failure
- **Solution**: Check `/api/health/` endpoint for details
- **Prevention**: Implement circuit breaker pattern

**Issue: Stale Data**

- **Cause**: Cached responses
- **Solution**: Wait for cache expiry or trigger recalculation
- **Check**: `X-Cache-Hit` header

### 10.2 Debugging Tips

**1. Enable verbose logging**:

```bash
export LOG_LEVEL=DEBUG
python manage.py runserver
```

**2. Check response headers**:

```python
print(response.headers)
```

**3. Monitor metrics**:

```bash
curl -H "Authorization: ..." https://api.smarthr360.com/api/metrics/
```

**4. Test health endpoints**:

```bash
curl https://api.smarthr360.com/api/health/
curl https://api.smarthr360.com/api/ready/
```

---

## 11. Summary

### Key Features Implemented

✅ **API Versioning**

- URL path versioning (v1/v2)
- Accept header support
- Deprecation warnings
- Backward compatibility

✅ **Rate Limiting**

- Multiple throttling tiers
- Rate limit headers
- Endpoint-specific limits
- Bypass options for superusers

✅ **Performance Optimization**

- Response time tracking
- Database query optimization
- Pagination
- Cache-friendly URLs

✅ **Caching**

- Redis-ready configuration
- Automatic cache invalidation
- Configurable timeouts
- Cache hit/miss tracking

✅ **Monitoring**

- Health check endpoints
- Readiness/liveness checks
- Metrics collection
- Request logging

### Quick Reference

| Feature         | Endpoint/Header     | Value        |
| --------------- | ------------------- | ------------ |
| Current Version | `/api/v2/`          | v2           |
| Health Check    | `/api/health/`      | 200 OK       |
| Rate Limit      | `X-RateLimit-Limit` | 1000/hour    |
| Response Time   | `X-Response-Time`   | ~150ms avg   |
| Cache Hit       | `X-Cache-Hit`       | true/false   |
| Version Info    | `/api/version/`     | Full details |

---

**Last Updated**: 2025-11-28  
**Author**: SmartHR360 Development Team  
**Status**: Production Ready
