# SmartHR360 Developer Guide

## Table of Contents

1. [Getting Started](#getting-started)
2. [Project Structure](#project-structure)
3. [Development Workflow](#development-workflow)
4. [Coding Standards](#coding-standards)
5. [Testing Guide](#testing-guide)
6. [API Development](#api-development)
7. [ML Model Development](#ml-model-development)
8. [Database Management](#database-management)
9. [Contributing](#contributing)
10. [Best Practices](#best-practices)

---

## Getting Started

### Prerequisites

- Python 3.10+
- Git
- PostgreSQL 14+ (or SQLite for dev)
- Redis 7.0+ (optional for dev)
- IDE (VS Code, PyCharm recommended)

### Initial Setup

```bash
# Clone repository
git clone https://github.com/yourusername/smarthr360_m3_future_skills.git
cd smarthr360_m3_future_skills

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Copy environment template
cp .env.example .env

# Update .env with your settings
nano .env  # or use your editor

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Load sample data
python manage.py loaddata future_skills/fixtures/initial_data.json

# Run development server
python manage.py runserver
```

### IDE Setup

#### VS Code

Install recommended extensions:

```json
{
  "recommendations": ["ms-python.python", "ms-python.vscode-pylance", "ms-python.black-formatter", "charliermarsh.ruff", "batisteo.vscode-django", "njpwerner.autodocstring", "visualstudioexptteam.vscodeintellicode"]
}
```

Settings (`.vscode/settings.json`):

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": false,
  "python.linting.flake8Enabled": true,
  "python.testing.pytestEnabled": true,
  "python.testing.unittestEnabled": false,
  "editor.formatOnSave": true,
  "editor.rulers": [88, 120],
  "files.exclude": {
    "**/__pycache__": true,
    "**/*.pyc": true
  }
}
```

#### PyCharm

1. Open project in PyCharm
2. Configure Python interpreter: Settings → Project → Python Interpreter → Add → Existing environment → Select `.venv/bin/python`
3. Enable Django support: Settings → Languages & Frameworks → Django → Enable Django Support
4. Configure test runner: Settings → Tools → Python Integrated Tools → Testing → Select pytest

---

## Project Structure

```
smarthr360_m3_future_skills/
├── config/                      # Django settings and configuration
│   ├── __init__.py
│   ├── asgi.py
│   ├── wsgi.py
│   ├── celery.py               # Celery configuration
│   ├── urls.py                 # Root URL configuration
│   ├── logging_config.py       # Logging configuration
│   ├── apm_config.py           # APM configuration
│   ├── logging_middleware.py   # Custom middleware
│   └── settings/               # Split settings
│       ├── __init__.py
│       ├── base.py             # Base settings
│       ├── development.py      # Development settings
│       ├── production.py       # Production settings
│       └── testing.py          # Testing settings
│
├── future_skills/              # Main Django app
│   ├── __init__.py
│   ├── admin.py                # Django admin configuration
│   ├── apps.py                 # App configuration
│   ├── models.py               # Database models
│   ├── permissions.py          # Custom permissions
│   ├── tasks.py                # Celery tasks
│   ├── ml_model.py             # ML model interface
│   │
│   ├── api/                    # API layer
│   │   ├── v1/                 # API version 1
│   │   │   ├── views.py
│   │   │   ├── serializers.py
│   │   │   └── urls.py
│   │   └── v2/                 # API version 2
│   │       ├── views.py
│   │       ├── serializers.py
│   │       └── urls.py
│   │
│   ├── services/               # Business logic layer
│   │   ├── __init__.py
│   │   ├── prediction_engine.py
│   │   ├── explanation_engine.py
│   │   ├── recommendation_engine.py
│   │   ├── training_service.py
│   │   └── file_parser.py
│   │
│   ├── management/             # Management commands
│   │   └── commands/
│   │       ├── health_check.py
│   │       ├── analyze_logs.py
│   │       └── export_future_skills_dataset.py
│   │
│   ├── migrations/             # Database migrations
│   ├── fixtures/               # Test data
│   └── tests/                  # Test suite
│       ├── test_models.py
│       ├── test_api.py
│       ├── test_services.py
│       └── test_ml.py
│
├── ml/                         # Machine learning components
│   ├── __init__.py
│   ├── models/                 # Trained ML models
│   ├── notebooks/              # Jupyter notebooks
│   └── scripts/                # Training scripts
│
├── docs/                       # Documentation
│   ├── ARCHITECTURE.md
│   ├── DEPLOYMENT_GUIDE.md
│   ├── DEVELOPER_GUIDE.md
│   ├── API_DOCUMENTATION.md
│   ├── LOGGING_MONITORING_GUIDE.md
│   └── SECURITY_GUIDE.md
│
├── nginx/                      # Nginx configuration
├── scripts/                    # Utility scripts
├── logs/                       # Application logs
├── media/                      # User-uploaded files
├── staticfiles/                # Collected static files
│
├── .env.example                # Environment template
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── Makefile                    # Development commands
├── manage.py                   # Django management script
├── pytest.ini                  # Pytest configuration
├── requirements.txt            # Python dependencies
├── requirements-dev.txt        # Development dependencies
└── README.md
```

---

## Development Workflow

### Feature Development Workflow

1. **Create Feature Branch**

```bash
git checkout -b feature/your-feature-name
```

2. **Make Changes**

- Write code following coding standards
- Add tests for new functionality
- Update documentation

3. **Test Changes**

```bash
# Run tests
make test

# Check code quality
make lint

# Run security checks
make security-scan
```

4. **Commit Changes**

```bash
git add .
git commit -m "feat: add new feature description"
```

5. **Push and Create PR**

```bash
git push origin feature/your-feature-name
# Create Pull Request on GitHub
```

### Commit Message Convention

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:**

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**

```bash
feat(api): add batch prediction endpoint
fix(models): correct skill level validation
docs(api): update prediction endpoint docs
test(services): add tests for recommendation engine
```

### Branch Strategy

- `main`: Production-ready code
- `develop`: Integration branch
- `feature/*`: New features
- `fix/*`: Bug fixes
- `hotfix/*`: Production hotfixes
- `release/*`: Release preparation

---

## Coding Standards

### Python Style Guide

Follow [PEP 8](https://pep8.org/) with these specifics:

```python
# Line length: 88 characters (Black default)
# Use double quotes for strings
# Use f-strings for formatting

# Good
name = f"Hello, {user.name}!"

# Bad
name = "Hello, %s!" % user.name

# Imports order: standard library, third-party, local
import os
import sys

from django.db import models
from rest_framework import serializers

from future_skills.models import Skill
from future_skills.services import PredictionEngine
```

### Code Formatting

Use Black and isort:

```bash
# Format code
black .

# Sort imports
isort .

# Or use Makefile
make format
```

### Type Hints

Use type hints for better code clarity:

```python
from typing import List, Dict, Optional, Union
from django.http import HttpRequest, HttpResponse

def predict_skill_level(
    skill_id: int,
    job_role_id: int,
    use_ml: bool = True
) -> Dict[str, Union[int, float]]:
    """
    Predict skill level for a given skill and job role.

    Args:
        skill_id: ID of the skill
        job_role_id: ID of the job role
        use_ml: Whether to use ML model

    Returns:
        Dictionary containing prediction results
    """
    # Implementation
    pass
```

### Docstrings

Use Google-style docstrings:

```python
def create_prediction(skill: Skill, job_role: JobRole) -> FutureSkillPrediction:
    """
    Create a future skill prediction.

    Creates a prediction for the given skill and job role combination using
    the ML model if available, otherwise falls back to rules-based logic.

    Args:
        skill: The skill to predict for
        job_role: The job role to predict for

    Returns:
        FutureSkillPrediction: The created prediction object

    Raises:
        ValueError: If skill or job_role is inactive
        ModelNotFoundError: If ML model is required but not available

    Examples:
        >>> skill = Skill.objects.get(name="Python")
        >>> role = JobRole.objects.get(title="Data Scientist")
        >>> prediction = create_prediction(skill, role)
        >>> print(prediction.predicted_level)
        4
    """
    # Implementation
    pass
```

### Error Handling

```python
from rest_framework.exceptions import ValidationError, NotFound
import logging

logger = logging.getLogger(__name__)

def process_data(data: dict) -> dict:
    """Process incoming data with proper error handling."""
    try:
        # Validate input
        if not data.get("skill_id"):
            raise ValidationError("skill_id is required")

        # Process data
        result = perform_operation(data)

        return result

    except KeyError as e:
        logger.error(f"Missing key in data: {e}")
        raise ValidationError(f"Missing required field: {e}")

    except Exception as e:
        logger.exception("Unexpected error processing data")
        raise
```

---

## Testing Guide

### Test Structure

```python
# future_skills/tests/test_services.py
import pytest
from django.test import TestCase
from future_skills.models import Skill, JobRole
from future_skills.services import PredictionEngine

class TestPredictionEngine(TestCase):
    """Test cases for PredictionEngine service."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data once for all tests."""
        cls.skill = Skill.objects.create(
            name="Python",
            category="Programming",
            difficulty_level=3
        )
        cls.job_role = JobRole.objects.create(
            title="Data Scientist",
            department="Engineering",
            seniority_level="Mid"
        )

    def setUp(self):
        """Set up before each test."""
        self.engine = PredictionEngine()

    def test_predict_skill_level_success(self):
        """Test successful skill level prediction."""
        result = self.engine.predict_skill_level(
            skill_id=self.skill.id,
            job_role_id=self.job_role.id
        )

        self.assertIn("predicted_level", result)
        self.assertIn("confidence_score", result)
        self.assertGreaterEqual(result["predicted_level"], 1)
        self.assertLessEqual(result["predicted_level"], 5)

    def test_predict_skill_level_invalid_skill(self):
        """Test prediction with invalid skill ID."""
        with self.assertRaises(ValueError):
            self.engine.predict_skill_level(
                skill_id=99999,
                job_role_id=self.job_role.id
            )
```

### Pytest Fixtures

```python
# conftest.py
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from future_skills.models import Skill, JobRole

User = get_user_model()

@pytest.fixture
def api_client():
    """Return DRF API client."""
    return APIClient()

@pytest.fixture
def authenticated_client(api_client):
    """Return authenticated API client."""
    user = User.objects.create_user(
        username="testuser",
        password="testpass123"
    )
    api_client.force_authenticate(user=user)
    return api_client

@pytest.fixture
def sample_skill():
    """Create and return a sample skill."""
    return Skill.objects.create(
        name="Python",
        category="Programming",
        difficulty_level=3
    )

@pytest.fixture
def sample_job_role():
    """Create and return a sample job role."""
    return JobRole.objects.create(
        title="Data Scientist",
        department="Engineering",
        seniority_level="Mid"
    )
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=future_skills --cov-report=html

# Run specific test file
pytest future_skills/tests/test_api.py

# Run specific test
pytest future_skills/tests/test_api.py::TestSkillAPI::test_list_skills

# Run tests matching pattern
pytest -k "test_prediction"

# Run with verbose output
pytest -v

# Stop on first failure
pytest -x

# Run parallel tests
pytest -n auto
```

### Test Coverage Goals

- Overall coverage: > 80%
- Critical paths: > 95%
- ML components: > 85%
- API endpoints: 100%

```bash
# Generate coverage report
make coverage

# View HTML report
open htmlcov/index.html
```

---

## API Development

### Creating a New API Endpoint

1. **Define Serializer**

```python
# future_skills/api/v2/serializers.py
from rest_framework import serializers
from future_skills.models import Skill

class SkillCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating skills."""

    class Meta:
        model = Skill
        fields = ["name", "category", "description", "difficulty_level"]

    def validate_name(self, value):
        """Validate skill name is unique."""
        if Skill.objects.filter(name__iexact=value).exists():
            raise serializers.ValidationError(
                "Skill with this name already exists"
            )
        return value

    def validate_difficulty_level(self, value):
        """Validate difficulty level is in valid range."""
        if not 1 <= value <= 5:
            raise serializers.ValidationError(
                "Difficulty level must be between 1 and 5"
            )
        return value
```

2. **Create View**

```python
# future_skills/api/v2/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter

from future_skills.models import Skill
from .serializers import SkillCreateSerializer, SkillListSerializer

class SkillViewSet(viewsets.ModelViewSet):
    """ViewSet for managing skills."""

    queryset = Skill.objects.filter(is_active=True)
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == "create":
            return SkillCreateSerializer
        return SkillListSerializer

    @extend_schema(
        summary="List all skills",
        description="Retrieve a paginated list of all active skills",
        responses={200: SkillListSerializer(many=True)}
    )
    def list(self, request):
        """List all skills."""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Create new skill",
        request=SkillCreateSerializer,
        responses={201: SkillListSerializer}
    )
    def create(self, request):
        """Create a new skill."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        skill = serializer.save()

        # Log creation
        logger.info(
            f"Skill created: {skill.name}",
            extra={"skill_id": skill.id, "user": request.user.id}
        )

        return Response(
            SkillListSerializer(skill).data,
            status=status.HTTP_201_CREATED
        )

    @extend_schema(
        summary="Search skills by category",
        parameters=[
            OpenApiParameter(
                name="category",
                type=str,
                required=True,
                description="Category to filter by"
            )
        ]
    )
    @action(detail=False, methods=["get"])
    def by_category(self, request):
        """Filter skills by category."""
        category = request.query_params.get("category")

        if not category:
            return Response(
                {"error": "category parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        skills = self.get_queryset().filter(category=category)
        serializer = self.get_serializer(skills, many=True)

        return Response(serializer.data)
```

3. **Add URL Route**

```python
# future_skills/api/v2/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SkillViewSet

router = DefaultRouter()
router.register(r"skills", SkillViewSet, basename="skill")

urlpatterns = [
    path("", include(router.urls)),
]
```

4. **Write Tests**

```python
# future_skills/tests/test_api_v2.py
import pytest
from rest_framework import status
from django.urls import reverse

@pytest.mark.django_db
class TestSkillAPI:
    """Test cases for Skill API v2."""

    def test_list_skills(self, authenticated_client, sample_skill):
        """Test listing skills."""
        url = reverse("api-v2:skill-list")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) > 0

    def test_create_skill(self, authenticated_client):
        """Test creating a new skill."""
        url = reverse("api-v2:skill-list")
        data = {
            "name": "JavaScript",
            "category": "Programming",
            "description": "Programming language",
            "difficulty_level": 2
        }
        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "JavaScript"

    def test_create_skill_duplicate_name(self, authenticated_client, sample_skill):
        """Test creating skill with duplicate name fails."""
        url = reverse("api-v2:skill-list")
        data = {
            "name": sample_skill.name,
            "category": "Programming",
            "difficulty_level": 2
        }
        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
```

---

## ML Model Development

### Training a New Model

```python
# ml/scripts/train_model.py
import os
import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

def prepare_data():
    """Prepare training data."""
    from future_skills.models import FutureSkillPrediction

    # Fetch data
    predictions = FutureSkillPrediction.objects.select_related(
        "skill", "job_role"
    ).all()

    # Convert to DataFrame
    data = []
    for p in predictions:
        data.append({
            "skill_category": p.skill.category,
            "skill_difficulty": p.skill.difficulty_level,
            "job_department": p.job_role.department,
            "job_seniority": p.job_role.seniority_level,
            "predicted_level": p.predicted_level
        })

    return pd.DataFrame(data)

def train_model():
    """Train and save ML model."""
    # Prepare data
    df = prepare_data()

    # Feature engineering
    X = pd.get_dummies(df.drop("predicted_level", axis=1))
    y = df["predicted_level"]

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # Train model
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        random_state=42
    )
    model.fit(X_train, y_train)

    # Evaluate
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)

    print(f"Model Accuracy: {accuracy:.4f}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))

    # Save model under artifacts/models to align with shared storage
    model_path = "artifacts/models/skill_prediction_model_v1.pkl"
    joblib.dump(model, model_path)
    print(f"\nModel saved to: {model_path}")

    return model, accuracy

if __name__ == "__main__":
    train_model()
```

> Configure `settings.ML_MODEL_PATH` (and the corresponding env var) to point at `BASE_DIR / "artifacts/models"` so the runtime loader resolves the same location used during training.

### Using the Model

```python
# future_skills/services/prediction_engine.py
import joblib
import pandas as pd
from django.conf import settings

class PredictionEngine:
    """Engine for making skill predictions."""

    def __init__(self):
        self.model = None
        if settings.FUTURE_SKILLS_USE_ML:
            self._load_model()

    def _load_model(self):
        """Load ML model from disk."""
        try:
            model_path = settings.ML_MODEL_PATH / "skill_prediction_model_v1.pkl"
            self.model = joblib.load(model_path)
        except FileNotFoundError:
            logger.warning("ML model not found, using fallback")
            self.model = None

    def predict(self, skill, job_role):
        """Make prediction for skill and job role."""
        if self.model is not None:
            return self._predict_ml(skill, job_role)
        return self._predict_fallback(skill, job_role)

    def _predict_ml(self, skill, job_role):
        """Make ML-based prediction."""
        # Prepare features
        features = pd.DataFrame([{
            f"skill_category_{skill.category}": 1,
            "skill_difficulty": skill.difficulty_level,
            f"job_department_{job_role.department}": 1,
            f"job_seniority_{job_role.seniority_level}": 1,
        }])

        # Predict
        prediction = self.model.predict(features)[0]
        confidence = self.model.predict_proba(features).max()

        return {
            "predicted_level": int(prediction),
            "confidence_score": float(confidence),
            "model_version": "v1.0.0"
        }
```

---

## Database Management

### Creating Migrations

```bash
# Create migration for model changes
python manage.py makemigrations future_skills

# Create empty migration for data migration
python manage.py makemigrations --empty future_skills

# Apply migrations
python manage.py migrate

# Show migration status
python manage.py showmigrations

# Rollback migration
python manage.py migrate future_skills 0001
```

### Data Migrations

```python
# future_skills/migrations/0002_populate_initial_skills.py
from django.db import migrations

def populate_skills(apps, schema_editor):
    """Populate initial skills."""
    Skill = apps.get_model("future_skills", "Skill")

    skills = [
        {"name": "Python", "category": "Programming", "difficulty_level": 3},
        {"name": "JavaScript", "category": "Programming", "difficulty_level": 2},
        {"name": "SQL", "category": "Database", "difficulty_level": 2},
    ]

    for skill_data in skills:
        Skill.objects.get_or_create(**skill_data)

def reverse_populate(apps, schema_editor):
    """Reverse the migration."""
    Skill = apps.get_model("future_skills", "Skill")
    Skill.objects.filter(
        name__in=["Python", "JavaScript", "SQL"]
    ).delete()

class Migration(migrations.Migration):
    dependencies = [
        ("future_skills", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(populate_skills, reverse_populate),
    ]
```

### Database Queries Optimization

```python
# Bad: N+1 query problem
predictions = FutureSkillPrediction.objects.all()
for prediction in predictions:
    print(prediction.skill.name)  # Causes extra query
    print(prediction.job_role.title)  # Causes extra query

# Good: Use select_related
predictions = FutureSkillPrediction.objects.select_related(
    "skill", "job_role"
).all()
for prediction in predictions:
    print(prediction.skill.name)  # No extra query
    print(prediction.job_role.title)  # No extra query

# Good: Use prefetch_related for reverse relations
job_roles = JobRole.objects.prefetch_related("futureskillprediction_set").all()
for role in job_roles:
    predictions = role.futureskillprediction_set.all()  # No extra query
```

---

## Best Practices

### Security

```python
# Always validate input
def process_user_input(data):
    serializer = InputSerializer(data=data)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data

# Use parameterized queries (Django ORM does this automatically)
Skill.objects.filter(name=user_input)  # Safe

# Never use raw SQL with user input
# Bad:
cursor.execute(f"SELECT * FROM skills WHERE name='{user_input}'")

# Good:
cursor.execute("SELECT * FROM skills WHERE name=%s", [user_input])

# Sanitize file uploads
def handle_file_upload(file):
    # Check file extension
    allowed_extensions = [".csv", ".json", ".xlsx"]
    ext = os.path.splitext(file.name)[1]
    if ext not in allowed_extensions:
        raise ValidationError("Invalid file type")

    # Check file size
    max_size = 10 * 1024 * 1024  # 10MB
    if file.size > max_size:
        raise ValidationError("File too large")
```

### Performance

```python
# Use bulk operations
skills = [
    Skill(name=f"Skill {i}", category="Test")
    for i in range(1000)
]
Skill.objects.bulk_create(skills)  # Single query

# Use update for bulk updates
Skill.objects.filter(category="Test").update(is_active=False)

# Use iterator() for large querysets
for skill in Skill.objects.iterator(chunk_size=1000):
    process_skill(skill)  # Reduces memory usage

# Cache expensive operations
from django.core.cache import cache

def get_popular_skills():
    cache_key = "popular_skills"
    skills = cache.get(cache_key)

    if skills is None:
        skills = Skill.objects.annotate(
            prediction_count=Count("futureskillprediction")
        ).order_by("-prediction_count")[:10]
        cache.set(cache_key, skills, timeout=3600)  # Cache for 1 hour

    return skills
```

### Logging

```python
import logging

logger = logging.getLogger(__name__)

def process_prediction(skill_id, job_role_id):
    """Process prediction with proper logging."""
    logger.info(
        "Starting prediction",
        extra={
            "skill_id": skill_id,
            "job_role_id": job_role_id
        }
    )

    try:
        result = make_prediction(skill_id, job_role_id)

        logger.info(
            "Prediction completed",
            extra={
                "skill_id": skill_id,
                "predicted_level": result["level"]
            }
        )

        return result

    except Exception as e:
        logger.error(
            "Prediction failed",
            exc_info=True,
            extra={
                "skill_id": skill_id,
                "job_role_id": job_role_id
            }
        )
        raise
```

---

## Contributing

### Code Review Checklist

- [ ] Code follows style guide (PEP 8, Black formatted)
- [ ] All tests pass
- [ ] New functionality has tests (>80% coverage)
- [ ] Documentation is updated
- [ ] API changes are documented in OpenAPI schema
- [ ] Security considerations addressed
- [ ] Performance impact considered
- [ ] Database migrations are reversible
- [ ] Error handling is appropriate
- [ ] Logging is adequate
- [ ] No sensitive data in logs/code
- [ ] Commit messages follow convention

### Pull Request Template

```markdown
## Description

Brief description of changes

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing

Describe testing performed

## Checklist

- [ ] Code follows style guide
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
```

---

## Useful Commands

```bash
# Development
make run              # Run development server
make test             # Run tests
make coverage         # Run tests with coverage
make lint             # Check code quality
make format           # Format code
make security-scan    # Run security checks

# Database
make migrate          # Run migrations
make migrations       # Create migrations
make shell            # Django shell
make dbshell          # Database shell

# Logs
make logs             # View logs
make logs-tail        # Tail logs
make logs-analyze     # Analyze logs

# Monitoring
make health-check     # Check system health
make metrics          # View metrics
```

---

## Resources

- [Django Documentation](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Celery Documentation](https://docs.celeryproject.org/)
- [pytest Documentation](https://docs.pytest.org/)
- [Black Code Style](https://black.readthedocs.io/)

**Version**: 1.0.0  
**Last Updated**: November 2024
