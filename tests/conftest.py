"""
Pytest configuration and shared fixtures for SmartHR360 Future Skills project.

This module provides common fixtures and configuration for all tests.
"""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from rest_framework.test import APIClient

User = get_user_model()


# ============================================================================
# Test Constants
# ============================================================================

SKILL_MACHINE_LEARNING = 'Machine Learning'


# ============================================================================
# API Client Fixtures
# ============================================================================

@pytest.fixture
def api_client():
    """
    Provides an unauthenticated DRF API client.

    Usage:
        def test_public_endpoint(api_client):
            response = api_client.get('/api/endpoint/')
            assert response.status_code == 200
    """
    return APIClient()


@pytest.fixture
def authenticated_client(api_client, regular_user):
    """
    Provides an authenticated API client with a regular user.

    Usage:
        def test_authenticated_endpoint(authenticated_client):
            response = authenticated_client.get('/api/protected/')
            assert response.status_code == 200
    """
    api_client.force_authenticate(user=regular_user)
    return api_client


@pytest.fixture
def admin_client(api_client, admin_user):
    """
    Provides an authenticated API client with an admin user.

    Usage:
        def test_admin_endpoint(admin_client):
            response = admin_client.get('/api/admin-only/')
            assert response.status_code == 200
    """
    api_client.force_authenticate(user=admin_user)
    return api_client


# ============================================================================
# User Fixtures
# ============================================================================

@pytest.fixture
def regular_user(db):
    """
    Creates a regular user without special permissions.

    Usage:
        def test_user_creation(regular_user):
            assert regular_user.username == 'testuser'
            assert not regular_user.is_staff
    """
    return User.objects.create_user(
        username='testuser',
        email='testuser@example.com',
        password='testpass123',
        is_staff=False,
        is_superuser=False
    )


@pytest.fixture
def admin_user(db):
    """
    Creates an admin user with superuser privileges.

    Usage:
        def test_admin_access(admin_user):
            assert admin_user.is_superuser
            assert admin_user.is_staff
    """
    return User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='adminpass123'
    )


@pytest.fixture
def hr_manager(db):
    """
    Creates an HR manager user with staff privileges.

    Usage:
        def test_hr_manager_permissions(hr_manager):
            assert hr_manager.is_staff
            assert hr_manager.has_perm('future_skills.view_futureskill')
    """
    user = User.objects.create_user(
        username='hr_manager',
        email='hr_manager@example.com',
        password='hrpass123',
        is_staff=True
    )

    # Add future_skills permissions
    permissions = Permission.objects.filter(
        content_type__app_label='future_skills'
    )
    user.user_permissions.set(permissions)

    return user


@pytest.fixture
def hr_viewer(db):
    """
    Creates an HR viewer user with read-only permissions.

    Usage:
        def test_hr_viewer_access(hr_viewer):
            assert hr_viewer.has_perm('future_skills.view_futureskill')
            assert not hr_viewer.has_perm('future_skills.add_futureskill')
    """
    user = User.objects.create_user(
        username='hr_viewer',
        email='hr_viewer@example.com',
        password='viewerpass123',
        is_staff=False
    )

    # Add view-only permissions
    view_permissions = Permission.objects.filter(
        content_type__app_label='future_skills',
        codename__startswith='view_'
    )
    user.user_permissions.set(view_permissions)

    return user


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture
def sample_future_skill(db):
    """
    Creates a sample FutureSkill instance for testing.

    Usage:
        def test_future_skill_display(sample_future_skill):
            assert 'Python' in sample_future_skill.skill_name
    """
    from future_skills.models import FutureSkill

    return FutureSkill.objects.create(
        skill_name='Python Programming',
        category='Technical',
        description='Advanced Python programming skills',
        importance_score=0.85,
        relevance_score=0.90
    )


@pytest.fixture
def sample_employee(db):
    """
    Creates a sample Employee instance for testing.

    Usage:
        def test_employee_creation(sample_employee):
            assert sample_employee.name == 'John Doe'
    """
    from future_skills.models import Employee

    return Employee.objects.create(
        name='John Doe',
        email='john.doe@example.com',
        department='Engineering',
        position='Software Engineer',
        current_skills=['Python', 'Django', 'REST APIs']
    )


@pytest.fixture
def sample_prediction(db, sample_employee):
    """
    Creates a sample PredictionRun instance for testing.

    Usage:
        def test_prediction_results(sample_prediction):
            assert sample_prediction.status == 'completed'
    """
    from future_skills.models import PredictionRun

    return PredictionRun.objects.create(
        employee=sample_employee,
        status='completed',
        confidence_score=0.75,
        predicted_skills=[SKILL_MACHINE_LEARNING, 'AI', 'Data Science'],
        model_version='v1.0'
    )


# ============================================================================
# ML Testing Fixtures
# ============================================================================

@pytest.fixture
def mock_ml_model(mocker):
    """
    Provides a mocked ML model for testing without actual model loading.

    Usage:
        def test_prediction_service(mock_ml_model):
            result = predict_future_skills(employee_data)
            assert result is not None
    """
    mock_model = mocker.patch('future_skills.services.prediction_engine.load_model')
    mock_model.return_value.predict.return_value = ['AI', SKILL_MACHINE_LEARNING]
    mock_model.return_value.predict_proba.return_value = [[0.1, 0.9]]
    return mock_model


@pytest.fixture
def disable_ml(settings):
    """
    Disables ML features for tests that don't require them.

    Usage:
        def test_without_ml(disable_ml):
            # Test runs without ML predictions
            pass
    """
    settings.FUTURE_SKILLS_USE_ML = False
    return settings


# ============================================================================
# Request Factory Fixtures
# ============================================================================

@pytest.fixture
def request_factory():
    """
    Provides Django's RequestFactory for testing views directly.

    Usage:
        def test_view_directly(request_factory):
            request = request_factory.get('/api/endpoint/')
            response = my_view(request)
            assert response.status_code == 200
    """
    from django.test import RequestFactory
    return RequestFactory()


# ============================================================================
# Test Data Fixtures
# ============================================================================

@pytest.fixture
def employee_data():
    """
    Provides sample employee data for testing.

    Usage:
        def test_employee_creation(employee_data):
            employee = Employee.objects.create(**employee_data)
            assert employee.name == employee_data['name']
    """
    return {
        'name': 'Jane Smith',
        'email': 'jane.smith@example.com',
        'department': 'Data Science',
        'position': 'Data Analyst',
        'current_skills': ['SQL', 'Excel', 'Tableau'],
        'experience_years': 3
    }


@pytest.fixture
def future_skill_data():
    """
    Provides sample future skill data for testing.

    Usage:
        def test_skill_creation(future_skill_data):
            skill = FutureSkill.objects.create(**future_skill_data)
            assert skill.category == 'Technical'
    """
    return {
        'skill_name': SKILL_MACHINE_LEARNING,
        'category': 'Technical',
        'description': 'ML algorithms and frameworks',
        'importance_score': 0.90,
        'relevance_score': 0.85,
        'growth_rate': 0.25
    }


# ============================================================================
# Pytest Configuration
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "e2e: marks tests as end-to-end tests"
    )
    config.addinivalue_line(
        "markers", "ml: marks tests that require ML model"
    )
    config.addinivalue_line(
        "markers", "api: marks tests for API endpoints"
    )
