# SmartHR360 Future Skills Platform - Architecture Documentation

## Table of Contents

1. [System Overview](#system-overview)
2. [High-Level Architecture](#high-level-architecture)
3. [Component Architecture](#component-architecture)
4. [Data Architecture](#data-architecture)
5. [API Architecture](#api-architecture)
6. [ML Pipeline Architecture](#ml-pipeline-architecture)
7. [Security Architecture](#security-architecture)
8. [Deployment Architecture](#deployment-architecture)
9. [Monitoring & Observability](#monitoring--observability)
10. [Scalability & Performance](#scalability--performance)

---

## System Overview

SmartHR360 Future Skills Platform is an enterprise-grade machine learning system that predicts future skill requirements for job roles. The platform combines Django REST Framework for the API layer, Celery for asynchronous task processing, and scikit-learn for machine learning capabilities.

### Key Features

- **ML-Powered Predictions**: Skills gap analysis and future requirements
- **API-First Design**: RESTful API with versioning (v1, v2)
- **Asynchronous Processing**: Background tasks for model training
- **Comprehensive Security**: JWT authentication, rate limiting, security headers
- **Production-Ready**: Logging, monitoring, health checks, metrics

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Client Layer                                │
├─────────────────────────────────────────────────────────────────────┤
│  Web Apps  │  Mobile Apps  │  Third-Party  │  Internal Services    │
└──────────────────────┬──────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       Load Balancer / CDN                            │
│                     (Nginx / AWS ALB)                                │
└──────────────────────┬──────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        API Gateway Layer                             │
├─────────────────────────────────────────────────────────────────────┤
│  - Rate Limiting                                                     │
│  - Authentication (JWT)                                              │
│  - Request Logging                                                   │
│  - CORS Headers                                                      │
│  - Security Middleware                                               │
└──────────────────────┬──────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Application Layer (Django)                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────┐  │
│  │   API Views      │  │   Business       │  │   ML Services   │  │
│  │   (v1, v2)       │  │   Logic          │  │                 │  │
│  │                  │  │                  │  │   - Prediction  │  │
│  │  - Skills        │  │  - Validation    │  │   - Training    │  │
│  │  - Job Roles     │  │  - Permissions   │  │   - Explanation │  │
│  │  - Predictions   │  │  - Caching       │  │   - Recommend.  │  │
│  │  - Training      │  │                  │  │                 │  │
│  └──────────────────┘  └──────────────────┘  └─────────────────┘  │
│                                                                       │
└──────────────┬──────────────────────┬─────────────────────────────┘
               │                      │
               ▼                      ▼
┌──────────────────────┐  ┌─────────────────────────────────────────┐
│   Database Layer     │  │     Task Queue (Celery)                 │
│   (PostgreSQL)       │  │                                         │
│                      │  │  ┌─────────────────┐                   │
│  - Skills            │  │  │ Celery Workers  │                   │
│  - Job Roles         │  │  │                 │                   │
│  - Predictions       │  │  │ - Model Train   │                   │
│  - Training History  │  │  │ - Bulk Predict  │                   │
│  - Users/Auth        │  │  │ - Data Export   │                   │
│                      │  │  └─────────────────┘                   │
└──────────────────────┘  │                                         │
                           │  Broker: Redis                         │
                           │  Backend: Django ORM                   │
                           └─────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     External Services Layer                          │
├─────────────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │  Cache   │  │   APM    │  │  Logging │  │   File Storage   │  │
│  │  (Redis) │  │  Sentry  │  │ Logstash │  │   (S3/Local)     │  │
│  │          │  │  Elastic │  │          │  │                  │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Component Architecture

### 1. API Layer

```
┌─────────────────────────────────────────────────────────────────┐
│                         API Layer                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    URL Routing                            │  │
│  │                                                            │  │
│  │  /api/v1/  ──────► V1 Views (Legacy)                     │  │
│  │  /api/v2/  ──────► V2 Views (Current)                    │  │
│  │  /api/auth/ ─────► JWT Authentication                    │  │
│  │  /api/health/ ───► Health Checks                         │  │
│  │  /metrics ───────► Prometheus Metrics                    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                   Middleware Stack                        │  │
│  │                                                            │  │
│  │  1. SecurityMiddleware                                    │  │
│  │  2. PrometheusBeforeMiddleware                           │  │
│  │  3. SecurityHeadersMiddleware                            │  │
│  │  4. CorsMiddleware                                       │  │
│  │  5. SessionMiddleware                                    │  │
│  │  6. CsrfViewMiddleware                                   │  │
│  │  7. AuthenticationMiddleware                             │  │
│  │  8. RequestIDMiddleware                                  │  │
│  │  9. CorrelationIdMiddleware                              │  │
│  │  10. RequestLoggingMiddleware                            │  │
│  │  11. PerformanceMonitoringMiddleware                     │  │
│  │  12. APMContextMiddleware                                │  │
│  │  13. SecurityEventLoggingMiddleware                      │  │
│  │  14. RateLimitMiddleware                                 │  │
│  │  15. AxesMiddleware                                      │  │
│  │  16. APIPerformanceMiddleware                            │  │
│  │  17. SecurityAuditMiddleware                             │  │
│  │  18. ErrorTrackingMiddleware                             │  │
│  │  19. PrometheusAfterMiddleware                           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                   API Views                               │  │
│  │                                                            │  │
│  │  Skills ViewSet:                                          │  │
│  │    - List, Create, Retrieve, Update, Delete              │  │
│  │    - Bulk import/export                                  │  │
│  │    - Search and filtering                                │  │
│  │                                                            │  │
│  │  Job Roles ViewSet:                                      │  │
│  │    - CRUD operations                                     │  │
│  │    - Bulk operations                                     │  │
│  │    - Related skills                                      │  │
│  │                                                            │  │
│  │  Predictions ViewSet:                                    │  │
│  │    - Create predictions                                  │  │
│  │    - Batch predictions                                   │  │
│  │    - Recalculate predictions                             │  │
│  │    - Get explanations                                    │  │
│  │    - Get recommendations                                 │  │
│  │                                                            │  │
│  │  Training API:                                           │  │
│  │    - Train model (async)                                 │  │
│  │    - Check training status                               │  │
│  │    - Get training history                                │  │
│  │    - Model metrics                                       │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 2. Service Layer

```
┌─────────────────────────────────────────────────────────────────┐
│                      Service Layer                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │          Prediction Engine Service                        │  │
│  │                                                            │  │
│  │  - predict_skill_level()                                  │  │
│  │  - batch_predict()                                        │  │
│  │  - recalculate_predictions()                              │  │
│  │  - get_model_info()                                       │  │
│  │                                                            │  │
│  │  ML Backend:                                              │  │
│  │    ├─ Scikit-learn Model (if ML enabled)                │  │
│  │    └─ Rules-based Fallback                              │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │          Explanation Engine Service                       │  │
│  │                                                            │  │
│  │  - explain_prediction()                                   │  │
│  │  - get_shap_values()                                      │  │
│  │  - get_lime_explanation()                                 │  │
│  │  - feature_importance()                                   │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │        Recommendation Engine Service                      │  │
│  │                                                            │  │
│  │  - recommend_skills()                                     │  │
│  │  - identify_gaps()                                        │  │
│  │  - suggest_learning_path()                                │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │          Training Service                                 │  │
│  │                                                            │  │
│  │  - train_model_async()                                    │  │
│  │  - prepare_training_data()                                │  │
│  │  - evaluate_model()                                       │  │
│  │  - save_model()                                           │  │
│  │  - track_training_history()                               │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │          File Parser Service                              │  │
│  │                                                            │  │
│  │  - parse_csv()                                            │  │
│  │  - parse_json()                                           │  │
│  │  - parse_excel()                                          │  │
│  │  - validate_data()                                        │  │
│  │  - bulk_import()                                          │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 3. Data Layer

```
┌─────────────────────────────────────────────────────────────────┐
│                       Data Layer                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                   Django Models                           │  │
│  │                                                            │  │
│  │  Skill:                                                   │  │
│  │    - name, category, description                          │  │
│  │    - difficulty_level, is_active                          │  │
│  │    - created_at, updated_at                               │  │
│  │                                                            │  │
│  │  JobRole:                                                 │  │
│  │    - title, department, description                       │  │
│  │    - seniority_level, is_active                           │  │
│  │    - created_at, updated_at                               │  │
│  │                                                            │  │
│  │  FutureSkillPrediction:                                   │  │
│  │    - skill, job_role                                      │  │
│  │    - predicted_level, confidence_score                    │  │
│  │    - model_version, prediction_date                       │  │
│  │    - features_used                                        │  │
│  │                                                            │  │
│  │  ModelTraining:                                           │  │
│  │    - model_version, training_date                         │  │
│  │    - metrics, parameters                                  │  │
│  │    - status, error_message                                │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  Database (PostgreSQL)                    │  │
│  │                                                            │  │
│  │  Tables:                                                  │  │
│  │    - future_skills_skill                                  │  │
│  │    - future_skills_jobrole                                │  │
│  │    - future_skills_futureskillprediction                  │  │
│  │    - future_skills_modeltraining                          │  │
│  │    - auth_user                                            │  │
│  │    - authtoken_token                                      │  │
│  │    - axes_accessattempt                                   │  │
│  │    - token_blacklist_*                                    │  │
│  │                                                            │  │
│  │  Indexes:                                                 │  │
│  │    - skill_name_idx                                       │  │
│  │    - jobrole_title_idx                                    │  │
│  │    - prediction_skill_job_idx                             │  │
│  │    - prediction_date_idx                                  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    Cache Layer (Redis)                    │  │
│  │                                                            │  │
│  │  - API Response Caching                                   │  │
│  │  - Session Storage                                        │  │
│  │  - Rate Limiting Counters                                 │  │
│  │  - Celery Task Results                                    │  │
│  │  - ML Model Cache                                         │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Architecture

### Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    Entity Relationship Diagram                   │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────────┐
│       Skill          │
├──────────────────────┤
│ id (PK)              │
│ name                 │
│ category             │
│ description          │
│ difficulty_level     │
│ is_active            │
│ created_at           │
│ updated_at           │
└──────────┬───────────┘
           │
           │ 1:N
           │
           ▼
┌──────────────────────────────────┐
│  FutureSkillPrediction           │
├──────────────────────────────────┤
│ id (PK)                          │
│ skill_id (FK) ───────────────────┘
│ job_role_id (FK) ────────┐
│ predicted_level          │
│ confidence_score         │
│ explanation              │
│ model_version            │
│ prediction_date          │
│ features_used (JSON)     │
│ created_at               │
│ updated_at               │
└──────────────────────────┘
           ▲
           │ N:1
           │
┌──────────┴───────────┐
│      JobRole         │
├──────────────────────┤
│ id (PK)              │
│ title                │
│ department           │
│ description          │
│ seniority_level      │
│ is_active            │
│ created_at           │
│ updated_at           │
└──────────────────────┘

┌──────────────────────────────────┐
│      ModelTraining               │
├──────────────────────────────────┤
│ id (PK)                          │
│ model_version                    │
│ training_date                    │
│ status                           │
│ dataset_size                     │
│ metrics (JSON)                   │
│ parameters (JSON)                │
│ model_path                       │
│ error_message                    │
│ created_at                       │
│ updated_at                       │
└──────────────────────────────────┘

┌──────────────────────────────────┐
│      User (Django Auth)          │
├──────────────────────────────────┤
│ id (PK)                          │
│ username                         │
│ email                            │
│ password                         │
│ is_staff                         │
│ is_active                        │
│ date_joined                      │
└──────────────────────────────────┘
```

### Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     Data Flow Diagram                            │
└─────────────────────────────────────────────────────────────────┘

1. Prediction Flow:

   Client Request
        │
        ▼
   API View (POST /api/v2/predictions/)
        │
        ├─► Validate Input
        ├─► Check Cache
        │
        ▼
   Prediction Engine
        │
        ├─► Load ML Model (if enabled)
        ├─► Extract Features
        ├─► Make Prediction
        ├─► Calculate Confidence
        │
        ▼
   Save to Database
        │
        ├─► Create FutureSkillPrediction
        ├─► Update Cache
        │
        ▼
   Return Response
        │
        └─► JSON Response


2. Training Flow:

   Client Request
        │
        ▼
   API View (POST /api/v2/training/train/)
        │
        ├─► Validate Request
        ├─► Check Permissions
        │
        ▼
   Celery Task (Async)
        │
        ├─► Create Training Record
        ├─► Fetch Training Data
        ├─► Prepare Features
        │
        ▼
   ML Training
        │
        ├─► Train Model
        ├─► Evaluate Performance
        ├─► Save Model File
        │
        ▼
   Update Database
        │
        ├─► Update Training Record
        ├─► Store Metrics
        │
        ▼
   Complete Task
        │
        └─► Return Task Result


3. Bulk Import Flow:

   Client Upload (CSV/JSON/Excel)
        │
        ▼
   API View (POST /api/v2/skills/bulk-import/)
        │
        ├─► Validate File
        ├─► Parse File
        │
        ▼
   File Parser Service
        │
        ├─► Read File
        ├─► Validate Each Row
        ├─► Transform Data
        │
        ▼
   Database Operations
        │
        ├─► Bulk Create/Update
        ├─► Transaction Management
        │
        ▼
   Return Results
        │
        └─► Summary Response
```

---

## API Architecture

### API Versioning Strategy

```
┌─────────────────────────────────────────────────────────────────┐
│                    API Versioning                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Version 1 (v1) - Legacy:                                        │
│    /api/v1/skills/                                               │
│    /api/v1/job-roles/                                            │
│    /api/v1/future-skills/                                        │
│                                                                   │
│  Version 2 (v2) - Current:                                       │
│    /api/v2/skills/                                               │
│    /api/v2/job-roles/                                            │
│    /api/v2/predictions/                                          │
│    /api/v2/training/                                             │
│                                                                   │
│  URL Path Versioning:                                            │
│    - Version in URL path                                         │
│    - Explicit and visible                                        │
│    - Easy to cache                                               │
│    - Backward compatible                                         │
│                                                                   │
│  Deprecation Policy:                                             │
│    - v1 marked as deprecated                                     │
│    - Warning headers in responses                                │
│    - Sunset date communicated                                    │
│    - v2 is current stable version                                │
└─────────────────────────────────────────────────────────────────┘
```

### API Request/Response Flow

```
┌─────────────────────────────────────────────────────────────────┐
│              API Request/Response Flow                           │
└─────────────────────────────────────────────────────────────────┘

1. Client Request:
   ┌──────────────────────────────────────────────────────────┐
   │ POST /api/v2/predictions/                                │
   │ Authorization: Bearer eyJ0eXAiOiJKV1QiLCJh...           │
   │ Content-Type: application/json                           │
   │                                                           │
   │ {                                                         │
   │   "skill_id": 1,                                         │
   │   "job_role_id": 5                                       │
   │ }                                                         │
   └──────────────────────────────────────────────────────────┘
                            │
                            ▼
2. Middleware Processing:
   ┌──────────────────────────────────────────────────────────┐
   │ Security Headers → CORS → Authentication → Rate Limit    │
   │ Request Logging → Performance Tracking → APM Context     │
   └──────────────────────────────────────────────────────────┘
                            │
                            ▼
3. View Processing:
   ┌──────────────────────────────────────────────────────────┐
   │ - Parse Request                                           │
   │ - Validate Data                                           │
   │ - Check Permissions                                       │
   │ - Call Service Layer                                      │
   └──────────────────────────────────────────────────────────┘
                            │
                            ▼
4. Service Layer:
   ┌──────────────────────────────────────────────────────────┐
   │ - Business Logic                                          │
   │ - ML Prediction                                           │
   │ - Data Transformation                                     │
   └──────────────────────────────────────────────────────────┘
                            │
                            ▼
5. Response:
   ┌──────────────────────────────────────────────────────────┐
   │ HTTP/1.1 201 Created                                      │
   │ Content-Type: application/json                            │
   │ X-Correlation-ID: 550e8400-e29b-41d4-a716-446655440000   │
   │ X-Response-Time: 0.234s                                   │
   │                                                           │
   │ {                                                         │
   │   "id": 123,                                             │
   │   "skill_id": 1,                                         │
   │   "job_role_id": 5,                                      │
   │   "predicted_level": 4,                                  │
   │   "confidence_score": 0.87,                              │
   │   "model_version": "v2.1.0",                             │
   │   "prediction_date": "2024-11-28T10:30:00Z"              │
   │ }                                                         │
   └──────────────────────────────────────────────────────────┘
```

---

## ML Pipeline Architecture

### Training Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                   ML Training Pipeline                           │
└─────────────────────────────────────────────────────────────────┘

1. Data Collection
   ┌────────────────────────────────────────┐
   │ - Query Database                       │
   │ - Filter Active Skills/Roles           │
   │ - Join Prediction History              │
   │ - Export to DataFrame                  │
   └────────────────┬───────────────────────┘
                    │
                    ▼
2. Data Preparation
   ┌────────────────────────────────────────┐
   │ - Handle Missing Values                │
   │ - Encode Categorical Features          │
   │ - Scale Numerical Features             │
   │ - Split Train/Test (80/20)             │
   └────────────────┬───────────────────────┘
                    │
                    ▼
3. Feature Engineering
   ┌────────────────────────────────────────┐
   │ - Create Interaction Features          │
   │ - Generate Polynomial Features         │
   │ - Apply Feature Selection              │
   │ - Store Feature Metadata               │
   └────────────────┬───────────────────────┘
                    │
                    ▼
4. Model Training
   ┌────────────────────────────────────────┐
   │ Algorithm: Random Forest Classifier    │
   │ - n_estimators: 100                    │
   │ - max_depth: 10                        │
   │ - Cross-validation: 5-fold             │
   │ - Hyperparameter tuning (optional)     │
   └────────────────┬───────────────────────┘
                    │
                    ▼
5. Model Evaluation
   ┌────────────────────────────────────────┐
   │ Metrics:                               │
   │ - Accuracy                             │
   │ - Precision/Recall/F1                  │
   │ - Confusion Matrix                     │
   │ - Feature Importance                   │
   │ - ROC-AUC Score                        │
   └────────────────┬───────────────────────┘
                    │
                    ▼
6. Model Persistence
   ┌────────────────────────────────────────┐
   │ - Serialize with joblib                │
   │ - Save to artifacts/models/            │
   │ - Version: v{major}.{minor}.{patch}    │
   │ - Update database record               │
   └────────────────┬───────────────────────┘
                    │
                    ▼
7. Model Registry
   ┌────────────────────────────────────────┐
   │ - Track in ModelTraining table         │
   │ - Store metrics and parameters         │
   │ - Set as active model                  │
   │ - Notify monitoring systems            │
   └────────────────────────────────────────┘
```

### Prediction Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                  ML Prediction Pipeline                          │
└─────────────────────────────────────────────────────────────────┘

1. Request Receipt
   ┌────────────────────────────────────────┐
   │ - Validate Input                       │
   │ - Extract skill_id, job_role_id        │
   │ - Check Cache                          │
   └────────────────┬───────────────────────┘
                    │
                    ▼
2. Model Loading
   ┌────────────────────────────────────────┐
   │ - Check if ML enabled                  │
   │ - Load active model from disk          │
   │ - Cache model in memory                │
   │ - Fallback to rules if unavailable     │
   └────────────────┬───────────────────────┘
                    │
                    ▼
3. Feature Extraction
   ┌────────────────────────────────────────┐
   │ - Fetch skill/role attributes          │
   │ - Apply same transformations           │
   │ - Encode categorical variables         │
   │ - Scale numerical features             │
   └────────────────┬───────────────────────┘
                    │
                    ▼
4. Prediction
   ┌────────────────────────────────────────┐
   │ - Call model.predict()                 │
   │ - Get probability scores               │
   │ - Calculate confidence                 │
   │ - Generate prediction level (1-5)      │
   └────────────────┬───────────────────────┘
                    │
                    ▼
5. Explanation (Optional)
   ┌────────────────────────────────────────┐
   │ - SHAP values                          │
   │ - LIME explanation                     │
   │ - Feature importance                   │
   │ - Generate human-readable text         │
   └────────────────┬───────────────────────┘
                    │
                    ▼
6. Persistence
   ┌────────────────────────────────────────┐
   │ - Save to FutureSkillPrediction        │
   │ - Store features_used (JSON)           │
   │ - Update cache                         │
   │ - Log prediction event                 │
   └────────────────┬───────────────────────┘
                    │
                    ▼
7. Response
   ┌────────────────────────────────────────┐
   │ - Format response                      │
   │ - Include metadata                     │
   │ - Add correlation ID                   │
   │ - Return to client                     │
   └────────────────────────────────────────┘
```

---

## Security Architecture

### Authentication & Authorization Flow

```
┌─────────────────────────────────────────────────────────────────┐
│             Authentication & Authorization                       │
└─────────────────────────────────────────────────────────────────┘

1. Login Request:
   ┌──────────────────────────────────────┐
   │ POST /api/auth/token/                │
   │ {                                    │
   │   "username": "user",                │
   │   "password": "pass"                 │
   │ }                                    │
   └────────────┬─────────────────────────┘
                │
                ▼
   ┌──────────────────────────────────────┐
   │ - Validate credentials               │
   │ - Check account active               │
   │ - Check login attempts (Axes)        │
   │ - Log security event                 │
   └────────────┬─────────────────────────┘
                │
                ▼
   ┌──────────────────────────────────────┐
   │ Generate JWT Tokens:                 │
   │ - Access Token (30 min)              │
   │ - Refresh Token (7 days)             │
   │ - Add custom claims                  │
   │ - Sign with HS256                    │
   └────────────┬─────────────────────────┘
                │
                ▼
   ┌──────────────────────────────────────┐
   │ Response:                            │
   │ {                                    │
   │   "access": "eyJ0eX...",             │
   │   "refresh": "eyJ0eX...",            │
   │   "user": {...}                      │
   │ }                                    │
   └──────────────────────────────────────┘


2. Authenticated Request:
   ┌──────────────────────────────────────┐
   │ GET /api/v2/predictions/             │
   │ Authorization: Bearer eyJ0eX...      │
   └────────────┬─────────────────────────┘
                │
                ▼
   ┌──────────────────────────────────────┐
   │ JWT Authentication:                  │
   │ - Extract token                      │
   │ - Verify signature                   │
   │ - Check expiration                   │
   │ - Check blacklist                    │
   └────────────┬─────────────────────────┘
                │
                ▼
   ┌──────────────────────────────────────┐
   │ Permission Check:                    │
   │ - IsAuthenticated                    │
   │ - Custom permissions                 │
   │ - Object-level permissions           │
   └────────────┬─────────────────────────┘
                │
                ▼
   ┌──────────────────────────────────────┐
   │ Process Request                      │
   └──────────────────────────────────────┘


3. Token Refresh:
   ┌──────────────────────────────────────┐
   │ POST /api/auth/token/refresh/        │
   │ {                                    │
   │   "refresh": "eyJ0eX..."             │
   │ }                                    │
   └────────────┬─────────────────────────┘
                │
                ▼
   ┌──────────────────────────────────────┐
   │ - Validate refresh token             │
   │ - Check blacklist                    │
   │ - Generate new access token          │
   │ - Rotate refresh token (optional)    │
   └────────────┬─────────────────────────┘
                │
                ▼
   ┌──────────────────────────────────────┐
   │ Response:                            │
   │ {                                    │
   │   "access": "eyJ0eX...",             │
   │   "refresh": "eyJ0eX..." (optional)  │
   │ }                                    │
   └──────────────────────────────────────┘
```

### Security Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                     Security Layers                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│ Layer 1: Network Security                                        │
│   - HTTPS/TLS encryption                                         │
│   - Firewall rules                                               │
│   - DDoS protection                                              │
│   - IP whitelisting (optional)                                   │
│                                                                   │
│ Layer 2: Application Gateway                                     │
│   - Rate limiting (100 req/min per IP)                           │
│   - Request size limits                                          │
│   - CORS configuration                                           │
│   - Security headers (CSP, HSTS, X-Frame-Options)                │
│                                                                   │
│ Layer 3: Authentication                                          │
│   - JWT tokens (HS256)                                           │
│   - Token blacklisting                                           │
│   - Session management                                           │
│   - Login attempt protection (5 attempts, 30min lockout)         │
│                                                                   │
│ Layer 4: Authorization                                           │
│   - Permission checks                                            │
│   - Role-based access control                                    │
│   - Object-level permissions                                     │
│   - API versioning access control                                │
│                                                                   │
│ Layer 5: Data Security                                           │
│   - Argon2 password hashing                                      │
│   - Sensitive data masking in logs                               │
│   - Database encryption (at rest)                                │
│   - Secure file upload handling                                  │
│                                                                   │
│ Layer 6: Monitoring & Auditing                                   │
│   - Security event logging                                       │
│   - Failed login tracking                                        │
│   - Suspicious activity detection                                │
│   - APM error tracking                                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Deployment Architecture

### Development Environment

```
┌─────────────────────────────────────────────────────────────────┐
│                  Development Environment                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                   Developer Machine                         │ │
│  │                                                              │ │
│  │  Django Dev Server (manage.py runserver)                    │ │
│  │    ├─ SQLite database                                       │ │
│  │    ├─ Local memory cache                                    │ │
│  │    ├─ Console logging (colored)                             │ │
│  │    └─ Debug mode enabled                                    │ │
│  │                                                              │ │
│  │  Celery Worker (optional)                                   │ │
│  │    └─ Redis broker (localhost)                              │ │
│  │                                                              │ │
│  │  Environment:                                               │ │
│  │    - ENVIRONMENT=development                                │ │
│  │    - DEBUG=True                                             │ │
│  │    - LOG_LEVEL=DEBUG                                        │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Docker Compose Setup

```
┌─────────────────────────────────────────────────────────────────┐
│                  Docker Compose Architecture                     │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                         Docker Host                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────┐  ┌──────────────────┐                    │
│  │   Web Container  │  │  Worker Container│                     │
│  │   (Django+Gunic) │  │  (Celery Worker) │                    │
│  │                  │  │                  │                     │
│  │  Port: 8000      │  │  Queues:         │                     │
│  │  Replicas: 2     │  │   - default      │                     │
│  └────────┬─────────┘  │   - ml_tasks     │                     │
│           │            │   - exports      │                     │
│           │            └────────┬─────────┘                     │
│           │                     │                                │
│           │  ┌──────────────────┴─────┐                         │
│           │  │                        │                          │
│           ▼  ▼                        ▼                          │
│  ┌────────────────┐         ┌────────────────┐                 │
│  │   PostgreSQL   │         │     Redis      │                 │
│  │   Container    │         │   Container    │                 │
│  │                │         │                │                 │
│  │  Port: 5432    │         │  Port: 6379    │                 │
│  │  Volume: data  │         │  Volume: cache │                 │
│  └────────────────┘         └────────────────┘                 │
│                                                                   │
│  ┌──────────────────────────────────────────┐                  │
│  │           Nginx Container                 │                  │
│  │           (Reverse Proxy)                 │                  │
│  │                                           │                  │
│  │  Port: 80, 443                            │                  │
│  │  SSL Termination                          │                  │
│  │  Static file serving                      │                  │
│  └──────────────────────────────────────────┘                  │
│                                                                   │
│  Docker Network: smarthr360_network                             │
│  Volumes: db_data, redis_data, static, media                    │
└─────────────────────────────────────────────────────────────────┘
```

### Production Deployment (Kubernetes)

```
┌─────────────────────────────────────────────────────────────────┐
│              Kubernetes Production Architecture                  │
└─────────────────────────────────────────────────────────────────┘

                    ┌─────────────────────┐
                    │   Load Balancer     │
                    │   (AWS ALB/ELB)     │
                    └──────────┬──────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Kubernetes Cluster                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                     Ingress Controller                    │  │
│  │                    (nginx-ingress)                        │  │
│  └────────────────────────┬─────────────────────────────────┘  │
│                            │                                     │
│           ┌────────────────┼────────────────┐                   │
│           │                │                │                   │
│           ▼                ▼                ▼                   │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐  │
│  │  API Service   │  │  API Service   │  │  API Service   │  │
│  │   (Pod 1)      │  │   (Pod 2)      │  │   (Pod 3)      │  │
│  │                │  │                │  │                │  │
│  │  Django+Gunic  │  │  Django+Gunic  │  │  Django+Gunic  │  │
│  │  Replicas: 3   │  │  Replicas: 3   │  │  Replicas: 3   │  │
│  │                │  │                │  │                │  │
│  │  Resources:    │  │  Resources:    │  │  Resources:    │  │
│  │  CPU: 1        │  │  CPU: 1        │  │  CPU: 1        │  │
│  │  Memory: 2Gi   │  │  Memory: 2Gi   │  │  Memory: 2Gi   │  │
│  └────────────────┘  └────────────────┘  └────────────────┘  │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Celery Worker Deployment                     │  │
│  │                                                            │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐               │  │
│  │  │ Worker 1 │  │ Worker 2 │  │ Worker 3 │               │  │
│  │  │          │  │          │  │          │               │  │
│  │  │ Replicas:│  │          │  │          │               │  │
│  │  │    3     │  │          │  │          │               │  │
│  │  └──────────┘  └──────────┘  └──────────┘               │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌──────────────────┐         ┌──────────────────┐             │
│  │   PostgreSQL     │         │      Redis       │             │
│  │  StatefulSet     │         │   StatefulSet    │             │
│  │                  │         │                  │             │
│  │  Replicas: 1     │         │  Replicas: 1     │             │
│  │  PVC: 100Gi      │         │  PVC: 10Gi       │             │
│  └──────────────────┘         └──────────────────┘             │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                   ConfigMaps & Secrets                    │  │
│  │                                                            │  │
│  │  - Environment variables                                  │  │
│  │  - Database credentials                                   │  │
│  │  - JWT secrets                                            │  │
│  │  - APM tokens                                             │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                   Persistent Volumes                      │  │
│  │                                                            │  │
│  │  - Database data (EBS/Persistent Disk)                    │  │
│  │  - Redis data                                             │  │
│  │  - Media files (S3/Cloud Storage)                         │  │
│  │  - ML models                                              │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘

External Services:
  - RDS PostgreSQL (managed)
  - ElastiCache Redis (managed)
  - S3 for media/static files
  - CloudWatch for logging
  - Elastic APM / Sentry for monitoring
```

---

## Monitoring & Observability

### Monitoring Stack

```
┌─────────────────────────────────────────────────────────────────┐
│                   Monitoring Architecture                        │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                        Application                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Logging:                                                        │
│    ├─ Structured logs (structlog)                               │
│    ├─ JSON format (production)                                  │
│    ├─ File handlers (rotation)                                  │
│    └─ Logstash shipping                                         │
│                                                                   │
│  Metrics:                                                        │
│    ├─ Prometheus exporters                                      │
│    ├─ Django middleware                                         │
│    ├─ Custom application metrics                                │
│    └─ /metrics endpoint                                         │
│                                                                   │
│  Tracing:                                                        │
│    ├─ Correlation IDs                                           │
│    ├─ Request/response logging                                  │
│    ├─ Elastic APM spans                                         │
│    └─ Distributed tracing                                       │
│                                                                   │
│  Error Tracking:                                                 │
│    ├─ Sentry integration                                        │
│    ├─ Elastic APM errors                                        │
│    ├─ Automatic capture                                         │
│    └─ User context                                              │
└───────────┬─────────────────────────────────────────────────────┘
            │
            │ (Logs)        (Metrics)      (Traces)    (Errors)
            │
            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Aggregation Layer                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  Logstash    │  │ Prometheus   │  │ Elastic APM  │         │
│  │              │  │              │  │              │         │
│  │ - Parse logs │  │ - Scrape     │  │ - Collect    │         │
│  │ - Transform  │  │   metrics    │  │   traces     │         │
│  │ - Ship to ES │  │ - Store TSDB │  │ - Index ES   │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                   │
│  ┌──────────────┐                                               │
│  │   Sentry     │                                               │
│  │              │                                               │
│  │ - Aggregate  │                                               │
│  │   errors     │                                               │
│  │ - Group      │                                               │
│  │ - Alert      │                                               │
│  └──────────────┘                                               │
└───────────┬─────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Visualization Layer                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────────┐  ┌──────────────────────┐            │
│  │   Kibana             │  │   Grafana            │            │
│  │                      │  │                      │            │
│  │ - Log search         │  │ - Metrics dashboard  │            │
│  │ - Log visualization  │  │ - Time series graphs │            │
│  │ - APM UI             │  │ - Alerts             │            │
│  │ - Dashboards         │  │ - Annotations        │            │
│  └──────────────────────┘  └──────────────────────┘            │
│                                                                   │
│  ┌──────────────────────┐                                       │
│  │   Sentry Dashboard   │                                       │
│  │                      │                                       │
│  │ - Error tracking     │                                       │
│  │ - Release tracking   │                                       │
│  │ - Performance        │                                       │
│  └──────────────────────┘                                       │
└───────────┬─────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Alerting Layer                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Alert Manager:                                                  │
│    ├─ High error rate                                           │
│    ├─ Slow response times                                       │
│    ├─ High resource usage                                       │
│    ├─ Service downtime                                          │
│    └─ Failed health checks                                      │
│                                                                   │
│  Notification Channels:                                          │
│    ├─ Email                                                      │
│    ├─ Slack                                                      │
│    ├─ PagerDuty                                                  │
│    └─ SMS                                                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## Scalability & Performance

### Horizontal Scaling Strategy

```
┌─────────────────────────────────────────────────────────────────┐
│                   Horizontal Scaling                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  API Layer (Stateless):                                          │
│    ├─ Multiple Django instances                                 │
│    ├─ Load balanced (round-robin)                               │
│    ├─ Auto-scaling based on CPU/Memory                          │
│    └─ Can scale to 10+ instances                                │
│                                                                   │
│  Worker Layer:                                                   │
│    ├─ Multiple Celery workers                                   │
│    ├─ Queue-based load distribution                             │
│    ├─ Dedicated workers for ML tasks                            │
│    └─ Scale based on queue length                               │
│                                                                   │
│  Database Layer:                                                 │
│    ├─ Read replicas for scaling reads                           │
│    ├─ Connection pooling (PgBouncer)                            │
│    ├─ Query optimization                                        │
│    └─ Sharding (if needed)                                      │
│                                                                   │
│  Cache Layer:                                                    │
│    ├─ Redis cluster                                             │
│    ├─ Multiple cache instances                                  │
│    ├─ Distributed caching                                       │
│    └─ Cache warming strategies                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Performance Optimizations

```
┌─────────────────────────────────────────────────────────────────┐
│                 Performance Optimizations                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Database:                                                       │
│    ✓ Indexing on frequently queried fields                      │
│    ✓ Query optimization (select_related, prefetch_related)      │
│    ✓ Database connection pooling                                │
│    ✓ Query result caching                                       │
│    ✓ Pagination for large datasets                              │
│                                                                   │
│  API:                                                            │
│    ✓ Response caching (Redis)                                   │
│    ✓ ETags for conditional requests                             │
│    ✓ Compression (gzip)                                         │
│    ✓ API versioning for backward compatibility                  │
│    ✓ Throttling to prevent abuse                                │
│                                                                   │
│  Application:                                                    │
│    ✓ Lazy loading of ML models                                  │
│    ✓ Model caching in memory                                    │
│    ✓ Async processing for heavy tasks                           │
│    ✓ Bulk operations for multiple records                       │
│    ✓ Code profiling and optimization                            │
│                                                                   │
│  Frontend:                                                       │
│    ✓ Static file compression                                    │
│    ✓ CDN for static assets                                      │
│    ✓ Browser caching headers                                    │
│    ✓ Minification of JS/CSS                                     │
│                                                                   │
│  Infrastructure:                                                 │
│    ✓ Load balancing                                             │
│    ✓ Auto-scaling groups                                        │
│    ✓ Content delivery network                                   │
│    ✓ Database read replicas                                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## Technology Stack Summary

### Core Technologies

- **Framework**: Django 5.2+, Django REST Framework 3.16+
- **Language**: Python 3.10+
- **Database**: PostgreSQL 14+ (production), SQLite (development)
- **Cache**: Redis 7.0+
- **Task Queue**: Celery 5.5+ with Redis broker
- **ML**: scikit-learn 1.3+, pandas, numpy, joblib

### API & Documentation

- **API**: RESTful with versioning (v1, v2)
- **Documentation**: drf-spectacular (OpenAPI 3.0)
- **Authentication**: JWT (djangorestframework-simplejwt)

### Security

- **Authentication**: JWT tokens with rotation and blacklisting
- **Password Hashing**: Argon2
- **Security Headers**: CSP, HSTS, X-Frame-Options, etc.
- **Rate Limiting**: django-ratelimit, custom middleware
- **Login Protection**: django-axes

### Monitoring & Logging

- **Logging**: structlog with JSON formatting
- **APM**: Elastic APM, Sentry
- **Metrics**: Prometheus with django-prometheus
- **Health Checks**: django-health-check
- **Log Aggregation**: Logstash (optional)

### Deployment

- **Web Server**: Gunicorn (production), Django dev server (development)
- **Reverse Proxy**: Nginx
- **Containerization**: Docker, Docker Compose
- **Orchestration**: Kubernetes (production)

### Development Tools

- **Profiling**: django-silk, py-spy
- **Testing**: pytest, coverage
- **Code Quality**: bandit, safety, pip-audit
- **Version Control**: Git, GitHub

---

## Documentation References

- **API Documentation**: `/api/docs/` (Swagger UI)
- **Architecture Guide**: This document
- **Security Guide**: `docs/SECURITY_GUIDE.md`
- **Logging & Monitoring**: `docs/LOGGING_MONITORING_GUIDE.md`
- **Deployment Guide**: `docs/deployment/README.md`
- **Development Guide**: `docs/development/README.md`

---

**Version**: 1.0.0  
**Last Updated**: November 2024  
**Maintained by**: SmartHR360 Engineering Team
