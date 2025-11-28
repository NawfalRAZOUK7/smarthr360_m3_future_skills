# SmartHR360 Future Skills API Documentation

## Overview

The SmartHR360 Future Skills API provides comprehensive endpoints for predicting future skill requirements, managing ML models, and generating HR investment recommendations.

## Base URL

```
Development: http://localhost:8000/api/
Production: https://your-domain.com/api/
```

## Interactive Documentation

### Swagger UI (Recommended)

**URL**: `/api/docs/`

Interactive API documentation with:

- Complete endpoint listing and descriptions
- Request/response schemas
- Try-it-out functionality
- Authentication support
- Example requests and responses

### ReDoc

**URL**: `/api/redoc/`

Alternative documentation interface with:

- Clean, responsive design
- Comprehensive schema documentation
- Search functionality
- Print-friendly format

### OpenAPI Schema

**URL**: `/api/schema/`

Raw OpenAPI 3.0 schema in YAML format for:

- Code generation tools
- API testing frameworks
- Documentation generators
- Third-party integrations

## Authentication

All endpoints require authentication. The API supports:

### Session Authentication

Use Django's built-in session authentication (suitable for web applications):

```bash
# Login via admin or custom endpoint
curl -X POST http://localhost:8000/api/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your_password"}'
```

### Basic Authentication

Include credentials in the Authorization header:

```bash
curl -X GET http://localhost:8000/api/future-skills/ \
  -u username:password
```

### Session Authentication in Browser

The API documentation UI automatically uses session authentication when logged into Django admin.

## Authorization Roles

### HR Staff (DRH/Responsable RH)

**Full access** including:

- Recalculate predictions
- Train ML models
- Manage employees
- View all data
- Bulk operations

### Manager

**Read access** to:

- View predictions
- View market trends
- View team employee data
- View analytics

### Authenticated User

**Limited read access** to:

- View own employee data
- View public trends

## Core Endpoints

### 1. Predictions

#### List Predictions

```http
GET /api/future-skills/
```

**Description**: Retrieve paginated list of skill predictions

**Query Parameters**:

- `job_role_id` (integer): Filter by job role
- `horizon_years` (integer): Filter by prediction horizon (3, 5, 10)
- `page` (integer): Page number
- `page_size` (integer): Items per page (max 100)

**Example Request**:

```bash
curl -X GET "http://localhost:8000/api/future-skills/?job_role_id=1&horizon_years=5&page=1" \
  -u admin:password
```

**Example Response**:

```json
{
  "count": 357,
  "next": "http://localhost:8000/api/future-skills/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "job_role": {
        "id": 1,
        "name": "Data Engineer",
        "department": "Engineering"
      },
      "skill": {
        "id": 1,
        "name": "Python",
        "category": "Technical"
      },
      "horizon_years": 5,
      "score": 85.5,
      "level": "HIGH",
      "rationale": "ML prediction based on market trends and internal usage...",
      "created_at": "2024-11-28T10:00:00Z"
    }
  ]
}
```

#### Recalculate Predictions

```http
POST /api/future-skills/recalculate/
```

**Description**: Trigger complete recalculation of all predictions

**Permissions**: HR Staff only

**Request Body**:

```json
{
  "horizon_years": 5
}
```

**Example Request**:

```bash
curl -X POST http://localhost:8000/api/future-skills/recalculate/ \
  -H "Content-Type: application/json" \
  -u admin:password \
  -d '{"horizon_years": 5}'
```

**Example Response**:

```json
{
  "horizon_years": 5,
  "total_predictions": 357,
  "total_recommendations": 42
}
```

**Process**:

1. Recalculates predictions for all job role × skill combinations
2. Uses ML model if available, falls back to rules engine
3. Generates HR investment recommendations for HIGH predictions
4. Creates PredictionRun record for traceability

**Performance**: May take several seconds for large datasets (500+ combinations)

---

### 2. Model Training

#### Train New Model

```http
POST /api/training/train/
```

**Description**: Train a new ML model for predictions

**Permissions**: HR Staff only

**Request Body**:

```json
{
  "dataset_path": "ml/data/future_skills_dataset.csv",
  "test_split": 0.2,
  "hyperparameters": {
    "n_estimators": 150,
    "max_depth": 20,
    "min_samples_split": 5
  },
  "model_version": "v2.1_production",
  "notes": "Optimized model for Q4 2024",
  "async_training": false
}
```

**Parameters**:

- `dataset_path` (string, required): Path to training CSV
- `test_split` (float, default: 0.2): Train/test split ratio
- `hyperparameters` (object): Random Forest hyperparameters
  - `n_estimators` (int, default: 100): Number of trees
  - `max_depth` (int, default: 15): Maximum tree depth
  - `min_samples_split` (int, default: 5): Min samples to split
  - `random_state` (int, default: 42): Random seed
- `model_version` (string): Version identifier (auto-generated if omitted)
- `notes` (string): Training notes/description
- `async_training` (boolean, default: false): Use Celery for background training

**Execution Modes**:

**Synchronous (async_training=false)**:

- Training executes immediately
- Returns complete metrics when finished
- Suitable for small datasets
- May timeout on large datasets

**Asynchronous (async_training=true)**:

- Training executes in background via Celery
- Returns immediately with task ID
- Check status via `/api/training/runs/{id}/`
- Recommended for production

**Example Request (Sync)**:

```bash
curl -X POST http://localhost:8000/api/training/train/ \
  -H "Content-Type: application/json" \
  -u admin:password \
  -d '{
    "dataset_path": "ml/data/future_skills_dataset.csv",
    "test_split": 0.2,
    "hyperparameters": {"n_estimators": 150, "max_depth": 20},
    "model_version": "v2.1_prod",
    "async_training": false
  }'
```

**Example Response (Sync)**:

```json
{
  "training_run_id": 10,
  "status": "COMPLETED",
  "message": "Training completed successfully in 12.45s",
  "model_version": "v2.1_prod",
  "metrics": {
    "accuracy": 0.9861,
    "precision": 0.9855,
    "recall": 0.9861,
    "f1_score": 0.986,
    "training_duration_seconds": 12.45
  }
}
```

**Example Response (Async)**:

```json
{
  "training_run_id": 10,
  "status": "RUNNING",
  "message": "Training started in background",
  "model_version": "v2.2_background",
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

#### List Training Runs

```http
GET /api/training/runs/
```

**Description**: List all training runs with metrics

**Query Parameters**:

- `status` (string): Filter by status (RUNNING, COMPLETED, FAILED)
- `trained_by` (string): Filter by username
- `page` (integer): Page number
- `page_size` (integer): Items per page (max 100)

**Example Request**:

```bash
curl -X GET "http://localhost:8000/api/training/runs/?status=COMPLETED" \
  -u admin:password
```

**Example Response**:

```json
{
  "count": 15,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 10,
      "model_version": "v2.1_prod",
      "status": "COMPLETED",
      "accuracy": 0.9861,
      "f1_score": 0.986,
      "training_duration_seconds": 12.45,
      "total_samples": 800,
      "trained_by": "admin",
      "created_at": "2024-11-28T10:00:00Z"
    }
  ]
}
```

#### Get Training Run Details

```http
GET /api/training/runs/{id}/
```

**Description**: Get detailed information about a specific training run

**Example Request**:

```bash
curl -X GET http://localhost:8000/api/training/runs/10/ \
  -u admin:password
```

**Example Response**:

```json
{
  "id": 10,
  "model_version": "v2.1_prod",
  "model_path": "ml/models/v2.1_prod.pkl",
  "dataset_path": "ml/data/future_skills_dataset.csv",
  "status": "COMPLETED",
  "accuracy": 0.9861,
  "precision": 0.9855,
  "recall": 0.9861,
  "f1_score": 0.986,
  "per_class_metrics": {
    "HIGH": { "precision": 0.99, "recall": 0.98, "f1": 0.99 },
    "MEDIUM": { "precision": 0.98, "recall": 0.99, "f1": 0.98 },
    "LOW": { "precision": 0.99, "recall": 0.99, "f1": 0.99 }
  },
  "total_samples": 800,
  "train_samples": 640,
  "test_samples": 160,
  "training_duration_seconds": 12.45,
  "hyperparameters": {
    "n_estimators": 150,
    "max_depth": 20,
    "min_samples_split": 5,
    "random_state": 42
  },
  "features_used": ["trend_score", "internal_usage", "training_requests", "scarcity_index", "hiring_difficulty", "avg_salary_k"],
  "trained_by": "admin",
  "notes": "Optimized model for Q4 2024",
  "created_at": "2024-11-28T10:00:00Z",
  "error_message": null
}
```

---

### 3. Employee Management

#### List Employees

```http
GET /api/employees/
```

#### Create Employee

```http
POST /api/employees/
```

#### Update Employee

```http
PUT /api/employees/{id}/
```

#### Delete Employee

```http
DELETE /api/employees/{id}/
```

**See Swagger UI for detailed documentation**: `/api/docs/`

---

### 4. Analytics & Reporting

#### Market Trends

```http
GET /api/market-trends/
```

#### Economic Reports

```http
GET /api/economic-reports/
```

#### HR Investment Recommendations

```http
GET /api/hr-investment-recommendations/
```

**See Swagger UI for detailed documentation**: `/api/docs/`

---

## Common Response Codes

### Success Codes

- `200 OK`: Request successful
- `201 Created`: Resource created successfully
- `204 No Content`: Deletion successful

### Client Error Codes

- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `422 Unprocessable Entity`: Validation failed

### Server Error Codes

- `500 Internal Server Error`: Server error
- `503 Service Unavailable`: Service temporarily unavailable

## Error Response Format

```json
{
  "detail": "Error message description",
  "errors": {
    "field_name": ["Error for this field"]
  }
}
```

## Pagination

All list endpoints return paginated results:

```json
{
  "count": 100,
  "next": "http://localhost:8000/api/endpoint/?page=2",
  "previous": null,
  "results": [...]
}
```

**Query Parameters**:

- `page`: Page number (default: 1)
- `page_size`: Items per page (default: 10, max: 100)

## Rate Limiting

Currently no rate limiting is applied. Consider implementing for production:

- Django Rate Limit
- DRF Throttling
- API Gateway rate limiting

## Best Practices

### 1. Use Async Training for Production

```json
{
  "async_training": true
}
```

### 2. Filter Predictions by Horizon

```
GET /api/future-skills/?horizon_years=5
```

### 3. Monitor Training Status

```
GET /api/training/runs/?status=RUNNING
```

### 4. Use Pagination for Large Datasets

```
GET /api/future-skills/?page_size=50&page=1
```

### 5. Check Errors in Bulk Operations

```json
{
  "status": "partial_success",
  "errors": [...]
}
```

## Code Examples

### Python (requests)

```python
import requests

# Authentication
auth = ('admin', 'password')
base_url = 'http://localhost:8000/api'

# List predictions
response = requests.get(
    f'{base_url}/future-skills/',
    params={'horizon_years': 5, 'page_size': 20},
    auth=auth
)
predictions = response.json()

# Recalculate predictions
response = requests.post(
    f'{base_url}/future-skills/recalculate/',
    json={'horizon_years': 5},
    auth=auth
)
result = response.json()
print(f"Created {result['total_predictions']} predictions")
```

### JavaScript (fetch)

```javascript
const baseUrl = "http://localhost:8000/api";
const auth = btoa("admin:password");

// List predictions
const response = await fetch(`${baseUrl}/future-skills/?horizon_years=5`, {
  headers: {
    Authorization: `Basic ${auth}`,
  },
});
const data = await response.json();
console.log(`Found ${data.count} predictions`);
```

### cURL

```bash
# List predictions
curl -X GET "http://localhost:8000/api/future-skills/?horizon_years=5" \
  -u admin:password

# Train model
curl -X POST http://localhost:8000/api/training/train/ \
  -H "Content-Type: application/json" \
  -u admin:password \
  -d '{
    "dataset_path": "ml/data/future_skills_dataset.csv",
    "test_split": 0.2,
    "async_training": true
  }'
```

## Troubleshooting

### 401 Unauthorized

- Verify credentials are correct
- Check user has required role
- Ensure session is active

### 403 Forbidden

- Verify user has required permissions (HR Staff, Manager)
- Check endpoint access requirements

### 500 Internal Server Error

- Check server logs: `logs/future_skills.log`
- Verify ML model exists: `ml/models/`
- Check database connectivity

### Training Timeouts

- Use async training for large datasets
- Reduce hyperparameters (n_estimators)
- Check dataset format and size

## Support

For issues or questions:

1. Check interactive documentation: `/api/docs/`
2. Review API logs: `logs/future_skills.log`
3. Check model status: `/api/training/runs/`
4. Verify permissions and authentication

## Version

API Version: 1.0.0
Last Updated: November 2024
