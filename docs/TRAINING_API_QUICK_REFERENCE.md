# 🚀 Training API Quick Reference

**Base URL:** `/api/training/`  
**Authentication:** Token required  
**Permissions:** IsHRStaff (train), IsHRStaffOrManager (view)

---

## 📍 Endpoints

| Method | Endpoint               | Permission         | Description        |
| ------ | ---------------------- | ------------------ | ------------------ |
| POST   | `/training/train/`     | IsHRStaff          | Train new model    |
| GET    | `/training/runs/`      | IsHRStaffOrManager | List training runs |
| GET    | `/training/runs/<id>/` | IsHRStaffOrManager | Get run details    |

---

## 🎯 Train Model

### **POST `/api/training/train/`**

**Request:**

```json
{
  "dataset_path": "ml/data/future_skills_dataset.csv",
  "test_split": 0.2,
  "hyperparameters": {
    "n_estimators": 100,
    "max_depth": 15,
    "min_samples_split": 5
  },
  "model_version": "v3.0",
  "notes": "Production model"
}
```

**All fields optional** - Defaults:

- `dataset_path`: `ml/data/future_skills_dataset.csv`
- `test_split`: `0.2`
- `hyperparameters`: `{}` (uses defaults)
- `model_version`: Auto-generated `api_v<timestamp>`
- `notes`: `""`

**Response (201 Created):**

```json
{
  "training_run_id": 10,
  "status": "COMPLETED",
  "message": "Training completed successfully in 0.25s",
  "model_version": "v3.0",
  "metrics": {
    "accuracy": 0.9861,
    "precision": 0.9867,
    "recall": 0.9861,
    "f1_score": 0.9862,
    "training_duration_seconds": 0.25
  }
}
```

**Errors:**

- `400`: Invalid request data (validation failed)
- `400`: Data loading error
- `500`: Training error
- `500`: Unexpected error

---

## 📋 List Training Runs

### **GET `/api/training/runs/`**

**Query Parameters:**

- `page`: Page number (default: 1)
- `page_size`: Items per page (default: 20, max: 100)
- `status`: Filter by RUNNING/COMPLETED/FAILED
- `trained_by`: Filter by username

**Examples:**

```bash
GET /api/training/runs/
GET /api/training/runs/?page=2&page_size=50
GET /api/training/runs/?status=COMPLETED
GET /api/training/runs/?trained_by=admin
```

**Response (200 OK):**

```json
{
  "count": 42,
  "next": "http://localhost:8000/api/training/runs/?page=2",
  "previous": null,
  "results": [
    {
      "id": 10,
      "run_date": "2025-11-27T16:30:00Z",
      "model_version": "v3.0",
      "status": "COMPLETED",
      "accuracy": 0.9861,
      "precision": 0.9867,
      "recall": 0.9861,
      "f1_score": 0.9862,
      "training_duration_seconds": 0.25,
      "trained_by_username": "admin"
    }
  ]
}
```

---

## 🔍 Get Training Run Details

### **GET `/api/training/runs/<id>/`**

**Example:**

```bash
GET /api/training/runs/10/
```

**Response (200 OK):**

```json
{
  "id": 10,
  "run_date": "2025-11-27T16:30:00Z",
  "model_version": "v3.0",
  "model_path": "ml/models/v3.0.pkl",
  "dataset_path": "ml/data/future_skills_dataset.csv",
  "status": "COMPLETED",
  "error_message": null,
  "accuracy": 0.9861,
  "precision": 0.9867,
  "recall": 0.9861,
  "f1_score": 0.9862,
  "total_samples": 357,
  "train_samples": 285,
  "test_samples": 72,
  "test_split": 0.2,
  "n_estimators": 100,
  "random_state": 42,
  "hyperparameters": {
    "n_estimators": 100,
    "max_depth": 15,
    "min_samples_split": 5
  },
  "training_duration_seconds": 0.25,
  "per_class_metrics": {
    "MEDIUM": {"accuracy": 0.979, "support": 48},
    "HIGH": {"accuracy": 1.0, "support": 24}
  },
  "features_used": ["job_role_name", "skill_name", ...],
  "trained_by_username": "admin",
  "notes": "Production model"
}
```

**Errors:**

- `404`: Training run not found

---

## 💻 Usage Examples

### **Python (requests)**

```python
import requests

BASE_URL = "http://localhost:8000"
TOKEN = "your_token_here"
headers = {"Authorization": f"Token {TOKEN}"}

# Train model
response = requests.post(
    f"{BASE_URL}/api/training/train/",
    headers=headers,
    json={
        "hyperparameters": {"n_estimators": 100},
        "model_version": "v1.0",
        "notes": "First production model"
    }
)
data = response.json()
run_id = data['training_run_id']
print(f"Training Run ID: {run_id}")
print(f"Accuracy: {data['metrics']['accuracy']:.2%}")

# List all runs
response = requests.get(
    f"{BASE_URL}/api/training/runs/",
    headers=headers,
    params={"status": "COMPLETED", "page_size": 10}
)
runs = response.json()['results']
for run in runs:
    print(f"{run['model_version']}: {run['accuracy']:.2%}")

# Get run details
response = requests.get(
    f"{BASE_URL}/api/training/runs/{run_id}/",
    headers=headers
)
details = response.json()
print(f"Hyperparameters: {details['hyperparameters']}")
```

### **cURL**

```bash
# Train model
curl -X POST http://localhost:8000/api/training/train/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "hyperparameters": {"n_estimators": 100},
    "model_version": "v1.0"
  }'

# List runs
curl http://localhost:8000/api/training/runs/ \
  -H "Authorization: Token YOUR_TOKEN"

# Filter by status
curl http://localhost:8000/api/training/runs/?status=COMPLETED \
  -H "Authorization: Token YOUR_TOKEN"

# Get details
curl http://localhost:8000/api/training/runs/10/ \
  -H "Authorization: Token YOUR_TOKEN"
```

### **JavaScript (fetch)**

```javascript
const BASE_URL = "http://localhost:8000";
const TOKEN = "your_token_here";

// Train model
const trainModel = async () => {
  const response = await fetch(`${BASE_URL}/api/training/train/`, {
    method: "POST",
    headers: {
      Authorization: `Token ${TOKEN}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      hyperparameters: { n_estimators: 100 },
      model_version: "v1.0",
      notes: "First model",
    }),
  });

  const data = await response.json();
  console.log(`Run ID: ${data.training_run_id}`);
  console.log(`Accuracy: ${(data.metrics.accuracy * 100).toFixed(2)}%`);
};

// List runs
const listRuns = async () => {
  const response = await fetch(`${BASE_URL}/api/training/runs/?status=COMPLETED`, {
    headers: { Authorization: `Token ${TOKEN}` },
  });

  const data = await response.json();
  data.results.forEach((run) => {
    console.log(`${run.model_version}: ${(run.accuracy * 100).toFixed(2)}%`);
  });
};

// Get details
const getRunDetails = async (runId) => {
  const response = await fetch(`${BASE_URL}/api/training/runs/${runId}/`, {
    headers: { Authorization: `Token ${TOKEN}` },
  });

  const details = await response.json();
  console.log("Hyperparameters:", details.hyperparameters);
  console.log("Per-class metrics:", details.per_class_metrics);
};
```

---

## 🔐 Authentication

### **Get Token**

```bash
curl -X POST http://localhost:8000/api-token-auth/ \
  -H "Content-Type: application/json" \
  -d '{"username": "your_username", "password": "your_password"}'
```

**Response:**

```json
{
  "token": "abc123def456..."
}
```

### **Use Token**

Add to every request:

```
Authorization: Token abc123def456...
```

---

## 🎯 Validation Rules

### **test_split**

- Type: Float
- Range: 0.1 - 0.5
- Default: 0.2

### **hyperparameters.n_estimators**

- Type: Integer
- Range: 1 - 1000
- Default: 100

### **hyperparameters.max_depth**

- Type: Integer or null
- Range: 1 - 100
- Default: null (unlimited)

### **hyperparameters.min_samples_split**

- Type: Integer
- Range: 2+
- Default: 2

---

## 📊 Status Codes

| Code | Meaning               | When                                |
| ---- | --------------------- | ----------------------------------- |
| 200  | OK                    | GET requests successful             |
| 201  | Created               | Training completed successfully     |
| 400  | Bad Request           | Validation error or data load error |
| 401  | Unauthorized          | No/invalid token                    |
| 403  | Forbidden             | User not in required group          |
| 404  | Not Found             | Training run ID doesn't exist       |
| 500  | Internal Server Error | Training error or unexpected error  |

---

## 🔗 Related Documentation

- **Section 2.3:** ModelTrainer service (`docs/SECTION_2.3_COMPLETION_SUMMARY.md`)
- **Section 2.4 Full Docs:** `docs/SECTION_2.4_COMPLETION_SUMMARY.md`
- **ModelTrainer Quick Ref:** `docs/MODELTRAINER_QUICK_REFERENCE.md`
- **API Tests:** `future_skills/tests/test_training_api.py`

---

**Last Updated:** 2025-11-27  
**Status:** ✅ Production Ready
