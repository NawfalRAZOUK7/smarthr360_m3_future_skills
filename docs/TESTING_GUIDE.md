# Testing Strategy Guide

**Last Updated**: 2025-11-28  
**Status**: Production Ready

---

## Table of Contents

1. [Overview](#overview)
2. [Test Structure](#test-structure)
3. [Running Tests](#running-tests)
4. [Test Coverage](#test-coverage)
5. [Writing Tests](#writing-tests)
6. [Testing API Architecture](#testing-api-architecture)
7. [Best Practices](#best-practices)
8. [CI/CD Integration](#cicd-integration)
9. [Troubleshooting](#troubleshooting)

---

## 1. Overview

SmartHR360 uses a comprehensive testing strategy covering:

- **Unit Tests**: Individual components and functions
- **Integration Tests**: Component interactions
- **API Tests**: REST API endpoints and architecture
- **ML Tests**: Machine learning models and predictions
- **End-to-End Tests**: Complete user workflows

### Testing Framework

- **Test Runner**: pytest
- **Django Testing**: pytest-django
- **Coverage**: pytest-cov
- **Assertions**: pytest assertions + Django test utilities
- **Mocking**: unittest.mock

### Test Organization

```
future_skills/tests/
├── __init__.py
├── test_api.py                    # API endpoint tests
├── test_api_architecture.py       # API versioning, throttling, monitoring
├── test_middleware.py             # Middleware unit tests
├── test_throttling.py             # Throttle class tests
├── test_prediction_engine.py      # ML prediction tests
├── test_recommendations.py        # Recommendation engine tests
├── test_training_api.py           # Model training API tests
└── test_celery_training.py        # Celery task tests
```

---

## 2. Test Structure

### Test Categories

#### Unit Tests

Test individual functions/methods in isolation:

```python
# future_skills/tests/test_middleware.py
def test_adds_response_time_header(self):
    """Test that response time header is added."""
    request = self.factory.get('/api/v2/predictions/')
    response = self.middleware(request)
    self.assertIn('X-Response-Time', response)
```

#### Integration Tests

Test component interactions:

```python
# future_skills/tests/test_api_architecture.py
def test_complete_api_workflow(self):
    """Test complete API workflow with all architecture features."""
    # 1. Check health
    health_response = self.client.get('/api/health/')

    # 2. Get version info
    version_response = self.client.get('/api/version/')

    # 3. Make API requests
    predictions_response = self.client.get('/api/v2/predictions/')
```

#### API Tests

Test REST API endpoints:

```python
# future_skills/tests/test_api.py
def test_predictions_list_authenticated(self):
    """Test predictions list for authenticated users."""
    self.client.force_authenticate(user=self.user)
    response = self.client.get('/api/v2/predictions/')
    self.assertEqual(response.status_code, 200)
```

### Test Fixtures

#### Setup Methods

```python
class MyTestCase(TestCase):
    def setUp(self):
        """Run before each test method."""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.skill = Skill.objects.create(
            name='Python',
            category='Technical'
        )

    def tearDown(self):
        """Run after each test method."""
        cache.clear()
```

#### Fixtures with pytest

```python
@pytest.fixture
def api_client():
    """Provide authenticated API client."""
    from rest_framework.test import APIClient
    client = APIClient()
    user = User.objects.create_user(username='test', password='pass')
    client.force_authenticate(user=user)
    return client

def test_with_fixture(api_client):
    response = api_client.get('/api/v2/predictions/')
    assert response.status_code == 200
```

### Test Markers

Mark tests for selective execution:

```python
import pytest

@pytest.mark.slow
def test_bulk_import():
    """Slow test - skipped in quick runs."""
    pass

@pytest.mark.integration
def test_api_workflow():
    """Integration test."""
    pass

@pytest.mark.api
@pytest.mark.versioning
def test_api_versioning():
    """API versioning test."""
    pass
```

---

## 3. Running Tests

### Basic Commands

**Run all tests**:

```bash
pytest
```

**Run specific test file**:

```bash
pytest future_skills/tests/test_api_architecture.py
```

**Run specific test class**:

```bash
pytest future_skills/tests/test_api_architecture.py::APIVersioningTestCase
```

**Run specific test method**:

```bash
pytest future_skills/tests/test_api_architecture.py::APIVersioningTestCase::test_v2_url_path_versioning
```

### Test Selection by Markers

**Run only API tests**:

```bash
pytest -m api
```

**Run only integration tests**:

```bash
pytest -m integration
```

**Exclude slow tests**:

```bash
pytest -m "not slow"
```

**Run multiple markers**:

```bash
pytest -m "api and not slow"
```

**Run middleware tests**:

```bash
pytest -m middleware
```

**Run throttling tests**:

```bash
pytest -m throttling
```

### Parallel Execution

**Run tests in parallel** (requires pytest-xdist):

```bash
# Install
pip install pytest-xdist

# Run with 4 workers
pytest -n 4

# Run with auto-detect CPUs
pytest -n auto
```

### Verbose Output

**Detailed output**:

```bash
pytest -v
```

**Very verbose**:

```bash
pytest -vv
```

**Show print statements**:

```bash
pytest -s
```

**Show full diff**:

```bash
pytest --tb=long
```

### Quick Smoke Tests

**Run only smoke tests**:

```bash
pytest -m smoke
```

**Fast validation** (skip slow tests):

```bash
pytest -m "not slow" --maxfail=3
```

---

## 4. Test Coverage

### Running Coverage

**Generate coverage report**:

```bash
pytest --cov=future_skills --cov-report=html
```

**View coverage in terminal**:

```bash
pytest --cov=future_skills --cov-report=term-missing
```

**Generate XML report** (for CI):

```bash
pytest --cov=future_skills --cov-report=xml
```

**Branch coverage**:

```bash
pytest --cov=future_skills --cov-branch --cov-report=html
```

### Coverage Reports

**HTML Report**:

```bash
pytest --cov=future_skills --cov-report=html
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

**Terminal Report**:

```
---------- coverage: platform darwin, python 3.12.0 -----------
Name                                          Stmts   Miss Branch BrPart  Cover
--------------------------------------------------------------------------------
future_skills/__init__.py                         2      0      0      0   100%
future_skills/api/__init__.py                     0      0      0      0   100%
future_skills/api/middleware.py                 125     15     28      4    88%
future_skills/api/monitoring.py                  85      8     16      2    90%
future_skills/api/throttling.py                 110     12     22      3    89%
future_skills/api/versioning.py                  78      6     14      1    92%
future_skills/models.py                         245     18     42      5    92%
future_skills/services/prediction_engine.py     180     20     38      6    88%
--------------------------------------------------------------------------------
TOTAL                                          1850    125    198     28    91%
```

### Coverage Targets

| Component  | Target | Current |
| ---------- | ------ | ------- |
| Overall    | 80%    | 91%     |
| API Layer  | 85%    | 92%     |
| Services   | 80%    | 88%     |
| Middleware | 85%    | 88%     |
| Models     | 75%    | 92%     |

### Coverage Configuration

**pytest.ini settings**:

```ini
[coverage:run]
source = future_skills,config
omit =
    */migrations/*
    */tests/*
    */test_*.py
branch = True

[coverage:report]
precision = 2
show_missing = True
skip_covered = False
fail_under = 70
```

### Improving Coverage

**Find uncovered code**:

```bash
pytest --cov=future_skills --cov-report=term-missing
```

**Focus on specific module**:

```bash
pytest --cov=future_skills.api.middleware --cov-report=html
```

**Check branch coverage**:

```bash
pytest --cov=future_skills --cov-branch --cov-report=term-missing
```

---

## 5. Writing Tests

### Test Structure

**Good test structure**:

```python
def test_descriptive_name(self):
    """
    Test description explaining what is being tested and why.

    Arrange: Set up test data and preconditions
    Act: Execute the code under test
    Assert: Verify the expected outcome
    """
    # Arrange
    user = User.objects.create_user(username='test', password='pass')
    self.client.force_authenticate(user=user)

    # Act
    response = self.client.get('/api/v2/predictions/')

    # Assert
    self.assertEqual(response.status_code, 200)
    self.assertIn('results', response.data)
```

### Testing API Endpoints

**GET request**:

```python
def test_list_predictions(self):
    """Test listing predictions."""
    response = self.client.get('/api/v2/predictions/')

    self.assertEqual(response.status_code, status.HTTP_200_OK)
    self.assertIn('results', response.data)
    self.assertIn('count', response.data)
```

**POST request**:

```python
def test_create_employee(self):
    """Test creating an employee."""
    data = {
        'employee_id': 'EMP001',
        'name': 'John Doe',
        'job_role': self.job_role.id,
        'years_of_experience': 5,
        'current_skill_level': 7
    }
    response = self.client.post('/api/v2/employees/', data)

    self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    self.assertEqual(response.data['name'], 'John Doe')
```

**Authentication**:

```python
def test_requires_authentication(self):
    """Test that endpoint requires authentication."""
    self.client.force_authenticate(user=None)
    response = self.client.get('/api/v2/predictions/')

    self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
```

### Testing with Mocks

**Mock external dependencies**:

```python
from unittest.mock import patch, Mock

@patch('future_skills.services.prediction_engine.make_prediction')
def test_prediction_with_mock(self, mock_predict):
    """Test prediction with mocked ML model."""
    # Configure mock
    mock_predict.return_value = {'score': 0.85, 'level': 'HIGH'}

    # Test
    response = self.client.post('/api/v2/ml/predict/', {...})

    # Verify
    self.assertEqual(response.data['score'], 0.85)
    mock_predict.assert_called_once()
```

**Mock Django cache**:

```python
@patch('django.core.cache.cache.get')
@patch('django.core.cache.cache.set')
def test_caching(self, mock_set, mock_get):
    """Test caching behavior."""
    mock_get.return_value = None  # Cache miss

    response = self.client.get('/api/v2/predictions/')

    mock_get.assert_called_once()
    mock_set.assert_called_once()
```

### Testing Middleware

**Test middleware in isolation**:

```python
def test_middleware_adds_header(self):
    """Test that middleware adds custom header."""
    request = self.factory.get('/api/v2/predictions/')
    response = self.middleware(request)

    self.assertIn('X-Custom-Header', response)
```

**Test middleware integration**:

```python
def test_middleware_stack(self):
    """Test middleware working together."""
    response = self.client.get('/api/v2/predictions/')

    # Check all middleware headers
    self.assertIn('X-Response-Time', response)
    self.assertIn('X-Cache-Hit', response)
    self.assertIn('Access-Control-Allow-Origin', response)
```

### Testing Throttling

**Test rate limiting**:

```python
@override_settings(
    REST_FRAMEWORK={
        'DEFAULT_THROTTLE_RATES': {
            'anon': '5/minute',
        }
    }
)
def test_rate_limiting(self):
    """Test that rate limiting works."""
    # Make requests up to limit
    for i in range(5):
        response = self.client.get('/api/v2/predictions/')
        self.assertEqual(response.status_code, 200)

    # Next request should be throttled
    response = self.client.get('/api/v2/predictions/')
    self.assertEqual(response.status_code, 429)
```

### Testing Async Code

**Test Celery tasks**:

```python
@patch('future_skills.tasks.train_model.delay')
def test_async_training(self, mock_task):
    """Test async model training trigger."""
    response = self.client.post('/api/v2/ml/train/', {...})

    self.assertEqual(response.status_code, 202)
    mock_task.assert_called_once()
```

---

## 6. Testing API Architecture

### Versioning Tests

**Test URL path versioning**:

```python
def test_v2_api(self):
    """Test v2 API endpoint."""
    response = self.client.get('/api/v2/predictions/')
    self.assertEqual(response.status_code, 200)

def test_v1_deprecated(self):
    """Test v1 API shows deprecation."""
    response = self.client.get('/api/v1/future-skills/')
    self.assertIn('X-API-Deprecation', response)
```

**Test Accept header versioning**:

```python
def test_accept_header_versioning(self):
    """Test Accept header versioning."""
    response = self.client.get(
        '/api/predictions/',
        HTTP_ACCEPT='application/vnd.smarthr360.v2+json'
    )
    self.assertEqual(response.status_code, 200)
```

### Throttling Tests

See `future_skills/tests/test_throttling.py` for comprehensive examples.

**Basic throttling test**:

```python
def test_anonymous_throttling(self):
    """Test anonymous user throttling."""
    for i in range(100):  # Up to limit
        response = self.client.get('/api/v2/predictions/')
        if response.status_code == 429:
            break

    self.assertEqual(response.status_code, 429)
    self.assertIn('Retry-After', response)
```

### Monitoring Tests

**Test health check**:

```python
def test_health_check(self):
    """Test health check endpoint."""
    response = self.client.get('/api/health/')

    self.assertEqual(response.status_code, 200)
    data = response.json()
    self.assertEqual(data['status'], 'healthy')
    self.assertIn('database', data['checks'])
```

**Test metrics endpoint**:

```python
def test_metrics_requires_staff(self):
    """Test metrics endpoint requires staff."""
    # Anonymous
    response = self.client.get('/api/metrics/')
    self.assertEqual(response.status_code, 401)

    # Staff
    staff_user = User.objects.create_user(
        username='staff',
        password='pass',
        is_staff=True
    )
    self.client.force_authenticate(user=staff_user)
    response = self.client.get('/api/metrics/')
    self.assertEqual(response.status_code, 200)
```

### Performance Tests

**Test response time**:

```python
import time

def test_response_time(self):
    """Test API response time."""
    start = time.time()
    response = self.client.get('/api/v2/predictions/')
    duration = (time.time() - start) * 1000  # ms

    self.assertLess(duration, 1000)  # < 1 second
```

**Test database queries**:

```python
from django.test import override_settings
from django.db import connection
from django.test.utils import override_settings

def test_query_count(self):
    """Test number of database queries."""
    with self.assertNumQueries(5):  # Expect 5 queries
        response = self.client.get('/api/v2/predictions/')
```

---

## 7. Best Practices

### General Guidelines

1. **One assertion per test** (when possible)
2. **Test both success and failure cases**
3. **Use descriptive test names**
4. **Keep tests independent**
5. **Mock external dependencies**
6. **Clean up after tests** (use tearDown)
7. **Use fixtures for common setup**
8. **Test edge cases and boundary conditions**

### Test Naming

**Good names**:

```python
def test_user_can_create_prediction_with_valid_data(self):
    """Test that authenticated user can create prediction."""
    pass

def test_anonymous_user_gets_401_on_prediction_create(self):
    """Test that anonymous users cannot create predictions."""
    pass

def test_rate_limit_header_decrements_with_each_request(self):
    """Test rate limit remaining counter decreases."""
    pass
```

**Bad names**:

```python
def test_1(self):  # Non-descriptive
    pass

def test_prediction(self):  # Too vague
    pass

def test_everything(self):  # Too broad
    pass
```

### Test Organization

**Group related tests**:

```python
class PredictionAPITestCase(APITestCase):
    """Tests for prediction API endpoints."""

    def test_list_predictions(self):
        pass

    def test_create_prediction(self):
        pass

    def test_update_prediction(self):
        pass
```

**Use descriptive docstrings**:

```python
def test_cache_invalidation_on_post(self):
    """
    Test that POST requests invalidate the cache.

    This ensures that after creating a new prediction,
    subsequent GET requests return fresh data.
    """
    pass
```

### Testing Edge Cases

```python
def test_empty_queryset(self):
    """Test API with no data."""
    FutureSkillPrediction.objects.all().delete()
    response = self.client.get('/api/v2/predictions/')
    self.assertEqual(response.data['count'], 0)

def test_pagination_last_page(self):
    """Test last page of paginated results."""
    response = self.client.get('/api/v2/predictions/?page=999')
    # Should handle gracefully

def test_invalid_version(self):
    """Test with invalid API version."""
    response = self.client.get('/api/v99/predictions/')
    self.assertEqual(response.status_code, 404)
```

### Testing Errors

```python
def test_validation_error(self):
    """Test validation error response."""
    data = {'invalid': 'data'}
    response = self.client.post('/api/v2/employees/', data)

    self.assertEqual(response.status_code, 400)
    self.assertIn('error', response.data)

def test_not_found(self):
    """Test 404 error."""
    response = self.client.get('/api/v2/employees/99999/')
    self.assertEqual(response.status_code, 404)

def test_permission_denied(self):
    """Test permission denied."""
    regular_user = User.objects.create_user(...)
    self.client.force_authenticate(user=regular_user)

    response = self.client.delete('/api/v2/employees/1/')
    self.assertEqual(response.status_code, 403)
```

---

## 8. CI/CD Integration

### GitHub Actions

**Example workflow** (`.github/workflows/test.yml`):

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: |
          pip install -r requirements-dev.txt

      - name: Run tests
        run: |
          pytest --cov=future_skills --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

### Pre-commit Hooks

**Install pre-commit**:

```bash
pip install pre-commit
```

**`.pre-commit-config.yaml`**:

```yaml
repos:
  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: pytest
        language: system
        pass_filenames: false
        always_run: true
        args: ["-m", "not slow"]
```

### Makefile Targets

**Run tests**:

```makefile
.PHONY: test
test:
	pytest

.PHONY: test-fast
test-fast:
	pytest -m "not slow"

.PHONY: test-coverage
test-coverage:
	pytest --cov=future_skills --cov-report=html

.PHONY: test-watch
test-watch:
	pytest-watch
```

---

## 9. Troubleshooting

### Common Issues

**Issue**: Tests fail with database errors

```
Solution: Use --create-db instead of --reuse-db
pytest --create-db
```

**Issue**: Tests hang or timeout

```
Solution: Run with timeout plugin
pip install pytest-timeout
pytest --timeout=30
```

**Issue**: Flaky tests (sometimes pass/fail)

```
Solution:
1. Check for timing issues
2. Use freezegun for time-dependent tests
3. Clear cache between tests
4. Check for test interdependencies
```

**Issue**: Import errors

```
Solution: Check PYTHONPATH and DJANGO_SETTINGS_MODULE
export DJANGO_SETTINGS_MODULE=config.settings.test
export PYTHONPATH=/path/to/project
```

### Debugging Tests

**Run single test with verbose output**:

```bash
pytest -vv -s future_skills/tests/test_api.py::test_method_name
```

**Drop into debugger on failure**:

```bash
pytest --pdb
```

**Show local variables on failure**:

```bash
pytest --tb=long --showlocals
```

**Run last failed tests**:

```bash
pytest --lf
```

**Run failed tests first**:

```bash
pytest --ff
```

### Performance Debugging

**Profile test execution**:

```bash
pytest --durations=10  # Show 10 slowest tests
```

**Identify slow tests**:

```bash
pytest --durations=0  # Show all test durations
```

---

## Summary

### Quick Reference

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=future_skills --cov-report=html

# Run specific tests
pytest -m api
pytest -m "not slow"
pytest future_skills/tests/test_api_architecture.py

# Run in parallel
pytest -n auto

# Debug
pytest -vv -s --pdb

# Coverage report
open htmlcov/index.html
```

### Test Statistics

| Category         | Tests | Coverage |
| ---------------- | ----- | -------- |
| API Architecture | 45+   | 92%      |
| Middleware       | 25+   | 88%      |
| Throttling       | 30+   | 89%      |
| Integration      | 15+   | 90%      |
| Overall          | 250+  | 91%      |

### Next Steps

1. Review [test files](../future_skills/tests/) for examples
2. Run smoke tests: `pytest -m smoke`
3. Check coverage: `pytest --cov=future_skills --cov-report=html`
4. Add tests for new features before implementation
5. Keep coverage above 80%

---

**Last Updated**: 2025-11-28  
**Author**: SmartHR360 Development Team  
**Status**: Production Ready
