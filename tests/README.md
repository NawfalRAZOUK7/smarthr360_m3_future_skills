# Testing Guide

Comprehensive testing documentation for SmartHR360 Future Skills project.

## Table of Contents

- [Test Structure](#test-structure)
- [Running Tests](#running-tests)
- [Test Categories](#test-categories)
- [Writing Tests](#writing-tests)
- [Fixtures](#fixtures)
- [Best Practices](#best-practices)

## Test Structure

```
tests/
├── __init__.py
├── conftest.py                    # Shared fixtures and pytest configuration
├── integration/                   # Integration tests
│   ├── __init__.py
│   ├── test_prediction_flow.py
│   └── test_api_endpoints.py
├── e2e/                          # End-to-end tests
│   ├── __init__.py
│   └── test_user_journeys.py
└── fixtures/                      # Reusable test fixtures
    ├── __init__.py
    └── common.py

future_skills/tests/              # Unit tests (existing)
├── __init__.py
├── test_models.py
├── test_serializers.py
└── test_views.py
```

## Running Tests

### Run All Tests

```bash
pytest
```

### Run Specific Test Categories

**Unit Tests Only:**

```bash
pytest future_skills/tests/
```

**Integration Tests:**

```bash
pytest tests/integration/ -v
```

**End-to-End Tests:**

```bash
pytest tests/e2e/ -v
```

### Run Tests by Marker

**API Tests:**

```bash
pytest -m api
```

**Integration Tests:**

```bash
pytest -m integration
```

**E2E Tests:**

```bash
pytest -m e2e
```

**ML Tests (requires ML model):**

```bash
pytest -m ml
```

**Exclude Slow Tests:**

```bash
pytest -m "not slow"
```

### Run Specific Test Files

```bash
pytest tests/integration/test_prediction_flow.py
pytest tests/e2e/test_user_journeys.py -v
```

### Run Specific Test Classes

```bash
pytest tests/integration/test_prediction_flow.py::TestPredictionFlow
```

### Run Specific Test Methods

```bash
pytest tests/integration/test_prediction_flow.py::TestPredictionFlow::test_complete_prediction_flow
```

### Coverage Reports

**Terminal Coverage:**

```bash
pytest --cov=future_skills --cov-report=term-missing
```

**HTML Coverage:**

```bash
pytest --cov=future_skills --cov-report=html
open htmlcov/index.html
```

**Coverage for Specific Module:**

```bash
pytest --cov=future_skills.services --cov-report=term
```

## Test Categories

### Unit Tests (`future_skills/tests/`)

- Test individual components in isolation
- Mock external dependencies
- Fast execution
- High coverage

**Examples:**

- Model validation
- Serializer behavior
- View logic
- Utility functions

### Integration Tests (`tests/integration/`)

- Test multiple components working together
- Use real database (test database)
- May use mocked ML models
- Test API endpoints with real requests

**Examples:**

- Complete prediction flow
- API endpoint behavior
- Database queries
- Permission checking

### End-to-End Tests (`tests/e2e/`)

- Test complete user workflows
- Simulate real user interactions
- Test multiple APIs in sequence
- May be slower

**Examples:**

- Complete user journey (login → view → create → predict)
- Multi-step workflows
- Error recovery scenarios
- Performance testing

## Writing Tests

### Basic Test Structure

```python
import pytest
from django.urls import reverse
from rest_framework import status

@pytest.mark.django_db
class TestMyFeature:
    """Test suite for my feature."""

    def test_something(self, authenticated_client):
        """Test description."""
        # Arrange
        url = reverse('my-endpoint')
        data = {'key': 'value'}

        # Act
        response = authenticated_client.post(url, data, format='json')

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert 'expected_key' in response.data
```

### Using Fixtures

**Built-in Fixtures:**

```python
def test_with_fixtures(authenticated_client, sample_employee, sample_future_skill):
    """Use multiple fixtures in a test."""
    # Test code here
    assert sample_employee.id is not None
```

**Custom Fixtures:**

```python
@pytest.fixture
def my_custom_fixture(db):
    """Create custom test data."""
    return MyModel.objects.create(field='value')

def test_with_custom_fixture(my_custom_fixture):
    """Use custom fixture."""
    assert my_custom_fixture.field == 'value'
```

### Parametrized Tests

```python
@pytest.mark.parametrize('input,expected', [
    ('valid@email.com', True),
    ('invalid-email', False),
    ('', False),
])
def test_email_validation(input, expected):
    """Test email validation with multiple inputs."""
    result = validate_email(input)
    assert result == expected
```

### Testing Exceptions

```python
def test_raises_exception():
    """Test that function raises expected exception."""
    with pytest.raises(ValueError, match="Invalid input"):
        some_function(invalid_input)
```

### Async Tests

```python
@pytest.mark.asyncio
async def test_async_function():
    """Test async functionality."""
    result = await async_function()
    assert result is not None
```

## Fixtures

### Available Fixtures

**API Clients:**

- `api_client` - Unauthenticated API client
- `authenticated_client` - Authenticated with regular user
- `admin_client` - Authenticated with admin user

**Users:**

- `regular_user` - Regular user without special permissions
- `admin_user` - Superuser with full permissions
- `hr_manager` - Staff user with future_skills permissions
- `hr_viewer` - User with read-only permissions

**Models:**

- `sample_employee` - Single employee instance
- `sample_future_skill` - Single future skill instance
- `sample_prediction` - Single prediction run instance
- `multiple_employees` - List of employees
- `multiple_future_skills` - List of skills

**Test Data:**

- `employee_data` - Dict with employee data
- `future_skill_data` - Dict with skill data
- `valid_employee_payload` - Valid API payload
- `invalid_employee_payload` - Invalid API payload

**ML Testing:**

- `mock_ml_model` - Mocked ML model
- `mock_ml_predictions` - Mocked predictions
- `disable_ml` - Disables ML features
- `ml_enabled_settings` - Enables ML
- `ml_disabled_settings` - Disables ML

**Scenarios:**

- `skills_gap_scenario` - Complete skills gap test scenario
- `prediction_test_scenario` - Complete prediction test scenario

**Utilities:**

- `request_factory` - Django request factory
- `freeze_time` - Freeze time for testing
- `clear_cache` - Clear Django cache

## Best Practices

### 1. Test Organization

- Group related tests in classes
- Use descriptive test names
- Follow Arrange-Act-Assert pattern
- One assertion per test (when possible)

### 2. Test Independence

- Each test should be independent
- Don't rely on test execution order
- Clean up after tests (use fixtures)
- Use `@pytest.mark.django_db` when accessing database

### 3. Fixtures Usage

- Use fixtures for reusable test data
- Keep fixtures simple and focused
- Document fixture purpose
- Use appropriate scope (function, class, module, session)

### 4. Mocking

- Mock external services (email, APIs)
- Mock slow operations (ML model loading)
- Don't over-mock - test real code when possible
- Use `mocker` fixture for mocking

### 5. Assertions

- Use specific assertions
- Add assertion messages when helpful
- Test both positive and negative cases
- Test edge cases

### 6. Performance

- Keep unit tests fast (< 100ms)
- Mark slow tests with `@pytest.mark.slow`
- Use database fixtures efficiently
- Consider using `pytest-xdist` for parallel execution

### 7. Coverage

- Aim for 80%+ coverage
- Focus on critical paths
- Don't chase 100% coverage blindly
- Review coverage reports regularly

### 8. Test Data

- Use factories or fixtures for test data
- Keep test data minimal
- Use realistic but simplified data
- Don't use production data

## Common Patterns

### Testing API Endpoints

```python
@pytest.mark.django_db
def test_list_endpoint(authenticated_client, sample_employee):
    """Test list endpoint returns data."""
    url = reverse('employee-list')
    response = authenticated_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) > 0
```

### Testing Permissions

```python
@pytest.mark.django_db
def test_permission_denied(api_client, sample_employee):
    """Test unauthenticated access is denied."""
    url = reverse('employee-detail', kwargs={'pk': sample_employee.id})
    response = api_client.get(url)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
```

### Testing with ML

```python
@pytest.mark.django_db
@pytest.mark.ml
def test_prediction(authenticated_client, sample_employee, ml_enabled_settings):
    """Test prediction with ML enabled."""
    url = reverse('futureskill-predict-skills')
    data = {'employee_id': sample_employee.id}

    response = authenticated_client.post(url, data, format='json')

    assert response.status_code == status.HTTP_200_OK
```

## Continuous Integration

Tests run automatically on:

- Pull request creation
- Push to main branch
- Manual trigger

### CI Configuration

See `.github/workflows/tests.yml` for CI/CD configuration.

## Troubleshooting

### Tests Fail Locally But Pass in CI

- Check Python version compatibility
- Verify all dependencies installed
- Check environment variables
- Ensure database is clean

### Slow Test Execution

- Use `pytest-xdist` for parallel execution
- Mark slow tests and exclude them during development
- Check for N+1 queries
- Use `select_related()` and `prefetch_related()`

### Flaky Tests

- Tests that sometimes pass/fail
- Often caused by timing issues or shared state
- Use `freeze_time` for time-dependent tests
- Ensure test independence

### Import Errors

- Check PYTHONPATH
- Verify Django settings module
- Ensure all test files have `__init__.py`

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-django](https://pytest-django.readthedocs.io/)
- [DRF Testing](https://www.django-rest-framework.org/api-guide/testing/)
- [Django Testing](https://docs.djangoproject.com/en/stable/topics/testing/)
