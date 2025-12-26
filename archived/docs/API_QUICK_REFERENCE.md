# API Quick Reference Guide

## Current API Version: v2

---

## Base URLs

```bash
# Development
http://localhost:8000/api/v2/

# Production
https://api.smarthr360.com/api/v2/
```

---

## Authentication

```bash
# Using session authentication (after login)
curl -b cookies.txt http://localhost:8000/api/v2/predictions/

# Using basic authentication
curl -u username:password http://localhost:8000/api/v2/predictions/

# Using token (future)
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/v2/predictions/
```

---

## Core Endpoints

### 1. Predictions (Future Skills)

**List all predictions**:

```bash
curl http://localhost:8000/api/v2/predictions/
```

**With pagination**:

```bash
curl "http://localhost:8000/api/v2/predictions/?page=1&page_size=20"
```

**Filter by job role**:

```bash
curl "http://localhost:8000/api/v2/predictions/?job_role=5"
```

**Trigger recalculation**:

```bash
curl -X POST http://localhost:8000/api/v2/predictions/recalculate/
```

### 2. Recommendations (HR Investments)

**List all recommendations**:

```bash
curl http://localhost:8000/api/v2/recommendations/
```

**Filter by priority**:

```bash
curl "http://localhost:8000/api/v2/recommendations/?priority_level=HIGH"
```

### 3. Employees

**List employees**:

```bash
curl http://localhost:8000/api/v2/employees/
```

**Get employee details**:

```bash
curl http://localhost:8000/api/v2/employees/42/
```

**Create employee**:

```bash
curl -X POST http://localhost:8000/api/v2/employees/ \
  -H "Content-Type: application/json" \
  -d '{
    "employee_id": "EMP001",
    "name": "John Doe",
    "job_role": 5,
    "years_of_experience": 8,
    "current_skill_level": 7
  }'
```

**Update employee**:

```bash
curl -X PATCH http://localhost:8000/api/v2/employees/42/ \
  -H "Content-Type: application/json" \
  -d '{"current_skill_level": 8}'
```

**Delete employee**:

```bash
curl -X DELETE http://localhost:8000/api/v2/employees/42/
```

**Get employee predictions**:

```bash
curl http://localhost:8000/api/v2/employees/42/predictions/
```

**Get skill gap report**:

```bash
curl http://localhost:8000/api/v2/employees/42/skill-gap-report/
```

### 4. ML Operations

**Single skill prediction**:

```bash
curl -X POST http://localhost:8000/api/v2/ml/predict/ \
  -H "Content-Type: application/json" \
  -d '{
    "job_role": 5,
    "skill": 10,
    "horizon": 3,
    "market_conditions": {...}
  }'
```

**Skill recommendations**:

```bash
curl -X POST http://localhost:8000/api/v2/ml/recommend/ \
  -H "Content-Type: application/json" \
  -d '{
    "employee_id": 42,
    "job_role": 5,
    "max_recommendations": 5
  }'
```

**Bulk predictions**:

```bash
curl -X POST http://localhost:8000/api/v2/ml/bulk-predict/ \
  -H "Content-Type: application/json" \
  -d '{
    "employees": [1, 2, 3, 4, 5],
    "horizon": 3
  }'
```

**Train model**:

```bash
curl -X POST http://localhost:8000/api/v2/ml/train/ \
  -H "Content-Type: application/json" \
  -d '{
    "model_type": "random_forest",
    "parameters": {
      "n_estimators": 100,
      "max_depth": 10
    }
  }'
```

**List training runs**:

```bash
curl http://localhost:8000/api/v2/ml/training-runs/
```

**Training run details**:

```bash
curl http://localhost:8000/api/v2/ml/training-runs/1/
```

### 5. Bulk Operations

**Bulk import employees (JSON)**:

```bash
curl -X POST http://localhost:8000/api/v2/bulk/employees/import/ \
  -H "Content-Type: application/json" \
  -d '{
    "employees": [
      {"employee_id": "EMP001", "name": "John Doe", ...},
      {"employee_id": "EMP002", "name": "Jane Smith", ...}
    ]
  }'
```

**Bulk upload employees (CSV)**:

```bash
curl -X POST http://localhost:8000/api/v2/bulk/employees/upload/ \
  -F "file=@employees.csv"
```

### 6. Market Trends

**List market trends**:

```bash
curl http://localhost:8000/api/v2/market-trends/
```

**Filter by skill**:

```bash
curl "http://localhost:8000/api/v2/market-trends/?skill=10"
```

### 7. Economic Reports

**List economic reports**:

```bash
curl http://localhost:8000/api/v2/economic-reports/
```

---

## Monitoring & Health

### Health Check

```bash
curl http://localhost:8000/api/health/
```

Response:

```json
{
  "status": "healthy",
  "timestamp": "2025-11-28T14:30:00Z",
  "checks": {
    "database": { "status": "healthy" },
    "cache": { "status": "healthy" }
  }
}
```

### Readiness Check

```bash
curl http://localhost:8000/api/ready/
```

### Liveness Check

```bash
curl http://localhost:8000/api/alive/
```

### Version Info

```bash
curl http://localhost:8000/api/version/
```

Response:

```json
{
  "current_version": "v2",
  "available_versions": ["v1", "v2"],
  "deprecated_versions": {
    "v1": {
      "deprecated_date": "2025-12-01",
      "sunset_date": "2026-06-01"
    }
  }
}
```

### Metrics (Staff Only)

```bash
curl -H "Authorization: ..." http://localhost:8000/api/metrics/
```

---

## Rate Limits

| User Type       | Rate Limit |
| --------------- | ---------- |
| Anonymous       | 100/hour   |
| Authenticated   | 1000/hour  |
| Staff/Premium   | 5000/hour  |
| ML Operations   | 10/hour    |
| Bulk Operations | 30/hour    |

**Check rate limit status**:

```bash
curl -I http://localhost:8000/api/v2/predictions/
```

Response headers:

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 847
X-RateLimit-Reset: 1735401600
```

---

## Common Query Parameters

### Pagination

```bash
?page=1&page_size=20
```

### Filtering

```bash
# By job role
?job_role=5

# By skill
?skill=10

# By level
?level=HIGH

# By priority
?priority_level=MEDIUM

# By horizon
?horizon=3
```

### Ordering

```bash
# Ascending
?ordering=score

# Descending
?ordering=-created_at
```

### Search

```bash
?search=python
```

---

## Response Format

### Success Response (List)

```json
{
  "count": 250,
  "next": "http://localhost:8000/api/v2/predictions/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "job_role": 5,
      "skill": 10,
      "score": 0.85,
      "level": "HIGH",
      "created_at": "2025-11-28T14:30:00Z"
    }
  ]
}
```

### Success Response (Detail)

```json
{
  "id": 1,
  "job_role": 5,
  "skill": 10,
  "score": 0.85,
  "level": "HIGH",
  "horizon": 3,
  "created_at": "2025-11-28T14:30:00Z",
  "updated_at": "2025-11-28T14:35:00Z"
}
```

### Error Response

```json
{
  "error": "Validation failed",
  "detail": "Invalid job_role ID",
  "code": "invalid_input"
}
```

---

## HTTP Status Codes

| Code | Meaning             | Action                |
| ---- | ------------------- | --------------------- |
| 200  | OK                  | Request successful    |
| 201  | Created             | Resource created      |
| 204  | No Content          | Delete successful     |
| 400  | Bad Request         | Check request data    |
| 401  | Unauthorized        | Authenticate          |
| 403  | Forbidden           | Check permissions     |
| 404  | Not Found           | Check resource ID     |
| 429  | Too Many Requests   | Wait and retry        |
| 500  | Server Error        | Contact support       |
| 503  | Service Unavailable | Check health endpoint |

---

## Response Headers

Every response includes:

```http
X-Response-Time: 142ms         # Request processing time
X-DB-Queries: 3                # Database queries executed
X-Cache-Hit: true              # Cache hit/miss
X-RateLimit-Limit: 1000        # Total allowed requests
X-RateLimit-Remaining: 847     # Requests remaining
X-RateLimit-Reset: 1735401600  # Reset timestamp
```

---

## Error Handling Examples

### Python Example

```python
import requests

def fetch_predictions(page=1):
    url = f"http://localhost:8000/api/v2/predictions/?page={page}"

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        print("Request timeout")
        return None
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            retry_after = int(e.response.headers.get('Retry-After', 60))
            print(f"Rate limited. Retry after {retry_after}s")
        elif e.response.status_code >= 500:
            print("Server error. Retry later")
        else:
            print(f"Client error: {e.response.json()}")
        return None
```

### JavaScript Example

```javascript
async function fetchPredictions(page = 1) {
  const url = `http://localhost:8000/api/v2/predictions/?page=${page}`;

  try {
    const response = await fetch(url);

    if (response.status === 429) {
      const retryAfter = response.headers.get("Retry-After");
      console.log(`Rate limited. Retry after ${retryAfter}s`);
      return null;
    }

    if (!response.ok) {
      const error = await response.json();
      console.error("API Error:", error);
      return null;
    }

    return await response.json();
  } catch (error) {
    console.error("Network error:", error);
    return null;
  }
}
```

---

## Python Client Example

```python
import requests
from typing import Optional, Dict, Any

class SmartHR360Client:
    def __init__(self, base_url: str = "http://localhost:8000", api_version: str = "v2"):
        self.base_url = f"{base_url}/api/{api_version}"
        self.session = requests.Session()

    def authenticate(self, username: str, password: str):
        """Authenticate with username and password."""
        self.session.auth = (username, password)

    def get_predictions(self, page: int = 1, page_size: int = 10, **filters) -> Optional[Dict[str, Any]]:
        """Get predictions with optional filters."""
        params = {'page': page, 'page_size': page_size, **filters}
        response = self.session.get(f"{self.base_url}/predictions/", params=params)
        response.raise_for_status()
        return response.json()

    def get_employee(self, employee_id: int) -> Optional[Dict[str, Any]]:
        """Get employee details."""
        response = self.session.get(f"{self.base_url}/employees/{employee_id}/")
        response.raise_for_status()
        return response.json()

    def predict_skill(self, job_role: int, skill: int, horizon: int = 3, **kwargs) -> Dict[str, Any]:
        """Make a single skill prediction."""
        data = {'job_role': job_role, 'skill': skill, 'horizon': horizon, **kwargs}
        response = self.session.post(f"{self.base_url}/ml/predict/", json=data)
        response.raise_for_status()
        return response.json()

    def health_check(self) -> Dict[str, Any]:
        """Check API health."""
        response = self.session.get(f"{self.base_url.replace('/api/v2', '')}/api/health/")
        response.raise_for_status()
        return response.json()

# Usage
client = SmartHR360Client()
client.authenticate("admin", "password")

# Get predictions
predictions = client.get_predictions(page=1, job_role=5)
print(f"Found {predictions['count']} predictions")

# Make prediction
result = client.predict_skill(job_role=5, skill=10, horizon=3)
print(f"Prediction score: {result['score']}")

# Check health
health = client.health_check()
print(f"API Status: {health['status']}")
```

---

## Testing Commands

### Run all tests

```bash
pytest
```

### Test specific endpoint

```bash
pytest tests/test_api.py::test_predictions_list
```

### Test with coverage

```bash
pytest --cov=future_skills --cov-report=html
```

### Load testing (with Apache Bench)

```bash
# 1000 requests, 10 concurrent
ab -n 1000 -c 10 http://localhost:8000/api/v2/predictions/
```

---

## Environment Variables

```bash
# API Configuration
export DJANGO_SETTINGS_MODULE=config.settings.production
export DEBUG=False
export SECRET_KEY=your-secret-key

# Database
export DATABASE_URL=postgresql://user:pass@localhost/dbname

# Cache (Redis)
export CACHE_URL=redis://localhost:6379/1

# Rate Limiting
export THROTTLE_ANON_RATE=100/hour
export THROTTLE_USER_RATE=1000/hour
export THROTTLE_PREMIUM_RATE=5000/hour

# Monitoring
export LOG_LEVEL=INFO
export SENTRY_DSN=your-sentry-dsn
```

---

## Docker Commands

### Start services

```bash
docker-compose up -d
```

### View logs

```bash
docker-compose logs -f api
```

### Run migrations

```bash
docker-compose exec api python manage.py migrate
```

### Create superuser

```bash
docker-compose exec api python manage.py createsuperuser
```

### Access shell

```bash
docker-compose exec api python manage.py shell
```

---

## Useful Management Commands

### Clear cache

```bash
python manage.py shell
>>> from django.core.cache import cache
>>> cache.clear()
```

### Generate sample data

```bash
python manage.py generate_sample_data
```

### Export dataset

```bash
python manage.py export_future_skills_dataset
```

### Train model

```bash
python manage.py train_ml_model
```

---

## Links

- **Full Documentation**: [API_ARCHITECTURE.md](API_ARCHITECTURE.md)
- **Database Guide**: [DATABASE_OPTIMIZATION.md](DATABASE_OPTIMIZATION.md)
- **Admin Guide**: [ADMIN_GUIDE.md](ADMIN_GUIDE.md)
- **API Swagger**: http://localhost:8000/api/schema/swagger/
- **API ReDoc**: http://localhost:8000/api/schema/redoc/

---

**Last Updated**: 2025-11-28  
**API Version**: v2  
**Status**: Production Ready
