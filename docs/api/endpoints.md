# API Endpoints Documentation

## Overview

The Future Skills API provides endpoints for managing and querying future skill predictions, market trends, economic reports, and HR investment recommendations.

**Base URL**: `/api/`

## Authentication

All endpoints require authentication. Users must belong to one of the following groups:

- `DRH` (HR Director) - Full access
- `RESPONSABLE_RH` (HR Manager) - Full access
- `MANAGER` - Read-only access

## Endpoints

### Future Skill Predictions

#### List Predictions

```
GET /api/future-skills/
```

**Query Parameters:**

- `job_role_id` (integer, optional) - Filter by job role
- `horizon_years` (integer, optional) - Filter by time horizon

**Permissions:** `IsHRStaffOrManager`

**Response:** Array of prediction objects

---

#### Recalculate Predictions

```
POST /api/future-skills/recalculate/
```

**Body:**

```json
{
  "horizon_years": 5
}
```

**Permissions:** `IsHRStaff` (DRH or RESPONSABLE_RH only)

**Response:**

```json
{
  "horizon_years": 5,
  "total_predictions": 150,
  "total_recommendations": 25
}
```

---

### Market Trends

#### List Market Trends

```
GET /api/market-trends/
```

**Query Parameters:**

- `year` (integer, optional) - Filter by year
- `sector` (string, optional) - Filter by sector

**Permissions:** `IsHRStaffOrManager`

**Response:** Array of market trend objects

---

### Economic Reports

#### List Economic Reports

```
GET /api/economic-reports/
```

**Query Parameters:**

- `year` (integer, optional) - Filter by year
- `sector` (string, optional) - Filter by sector
- `indicator` (string, optional) - Filter by indicator (contains)

**Permissions:** `IsHRStaffOrManager`

**Response:** Array of economic report objects

---

### HR Investment Recommendations

#### List Recommendations

```
GET /api/hr-investment-recommendations/
```

**Query Parameters:**

- `horizon_years` (integer, optional) - Filter by time horizon
- `skill_id` (integer, optional) - Filter by skill
- `job_role_id` (integer, optional) - Filter by job role
- `priority_level` (string, optional) - Filter by priority level

**Permissions:** `IsHRStaffOrManager`

**Response:** Array of recommendation objects

---

## Response Formats

### Prediction Object

```json
{
  "id": 1,
  "job_role": {
    "id": 1,
    "name": "Data Scientist",
    "department": "IT",
    "description": "..."
  },
  "skill": {
    "id": 1,
    "name": "Python",
    "category": "Technique",
    "description": "..."
  },
  "horizon_years": 5,
  "score": 0.85,
  "level": "HIGH",
  "rationale": "...",
  "created_at": "2025-11-27T10:00:00Z"
}
```

### Market Trend Object

```json
{
  "id": 1,
  "title": "AI Adoption in Healthcare",
  "source_name": "Gartner",
  "year": 2025,
  "sector": "Tech",
  "trend_score": 8.5,
  "description": "...",
  "created_at": "2025-11-27T10:00:00Z"
}
```

### Economic Report Object

```json
{
  "id": 1,
  "title": "Tech Sector Growth",
  "source_name": "IMF",
  "year": 2025,
  "indicator": "GDP Growth",
  "value": 5.2,
  "sector": "Tech",
  "created_at": "2025-11-27T10:00:00Z"
}
```

### Recommendation Object

```json
{
  "id": 1,
  "skill": {
    "id": 1,
    "name": "Python",
    "category": "Technique",
    "description": "..."
  },
  "job_role": {
    "id": 1,
    "name": "Data Scientist",
    "department": "IT",
    "description": "..."
  },
  "horizon_years": 5,
  "priority_level": "HIGH",
  "recommended_action": "Invest in training programs",
  "budget_hint": "$50,000 - $100,000",
  "rationale": "...",
  "created_at": "2025-11-27T10:00:00Z"
}
```

## Error Responses

### 400 Bad Request

```json
{
  "detail": "horizon_years must be an integer."
}
```

### 401 Unauthorized

```json
{
  "detail": "Authentication credentials were not provided."
}
```

### 403 Forbidden

```json
{
  "detail": "You do not have permission to perform this action."
}
```

## Testing

Example using curl:

```bash
# Login and get session cookie
curl -X POST http://localhost:8000/api-auth/login/ \
  -d "username=your_username&password=your_password"

# List predictions
curl -X GET http://localhost:8000/api/future-skills/ \
  -b cookies.txt

# Recalculate predictions
curl -X POST http://localhost:8000/api/future-skills/recalculate/ \
  -H "Content-Type: application/json" \
  -d '{"horizon_years": 5}' \
  -b cookies.txt
```

## API Structure

The API is organized in a clean layered architecture:

```
future_skills/
├── api/                      # API Layer
│   ├── __init__.py
│   ├── serializers.py       # Data serialization
│   ├── views.py             # API endpoints
│   └── urls.py              # URL routing
├── models.py                # Data models
├── services/                # Business logic
│   ├── prediction_engine.py
│   ├── recommendation_engine.py
│   └── explanation_engine.py
└── permissions.py           # Access control
```

This separation ensures:

- **API layer** handles HTTP requests/responses
- **Services layer** contains business logic
- **Models layer** defines data structure
- **Permissions** control access
