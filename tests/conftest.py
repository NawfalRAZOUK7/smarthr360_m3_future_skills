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

SKILL_MACHINE_LEARNING = "Machine Learning"


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
    Creates a manager user for authenticated API access.

    Usage:
        def test_user_creation(regular_user):
            assert regular_user.username == 'testuser'
            assert not regular_user.is_staff
    """
    user = User.objects.create_user(
        username="testuser",
        email="testuser@example.com",
        password="testpass123",
        is_staff=False,
        is_superuser=False,
        role=User.Role.MANAGER,
    )

    return user


@pytest.fixture
def admin_user(db):
    """
    Creates an admin user with superuser privileges.

    Usage:
        def test_admin_access(admin_user):
            assert admin_user.is_superuser
            assert admin_user.is_staff
    """
    return User.objects.create_superuser(username="admin", email="admin@example.com", password="adminpass123")


@pytest.fixture
def hr_manager(db):
    """
    Creates an HR user with staff privileges and legacy RESPONSABLE_RH group.

    Usage:
        def test_hr_manager_permissions(hr_manager):
            assert hr_manager.is_staff
            assert hr_manager.groups.filter(name='RESPONSABLE_RH').exists()
    """
    user = User.objects.create_user(
        username="hr_manager",
        email="hr_manager@example.com",
        password="hrpass123",
        is_staff=True,
        role=User.Role.HR,
    )

    # Add to RESPONSABLE_RH group for HR staff permissions
    from django.contrib.auth.models import Group

    hr_group, _ = Group.objects.get_or_create(name="RESPONSABLE_RH")
    user.groups.add(hr_group)

    # Add future_skills permissions
    permissions = Permission.objects.filter(content_type__app_label="future_skills")
    user.user_permissions.set(permissions)

    return user


@pytest.fixture
def hr_viewer(db):
    """
    Creates an HR viewer user with read-only permissions.
    NOT part of HR staff groups, so will get 403 on protected endpoints.

    Usage:
        def test_hr_viewer_access(hr_viewer):
            # This user should get 403 on HR staff-only endpoints
            assert not hr_viewer.groups.filter(name__in=['DRH', 'RESPONSABLE_RH']).exists()
    """
    user = User.objects.create_user(
        username="hr_viewer",
        email="hr_viewer@example.com",
        password="viewerpass123",
        is_staff=False,
        role=User.Role.EMPLOYEE,
    )

    # Add view-only permissions (but no group membership)
    view_permissions = Permission.objects.filter(content_type__app_label="future_skills", codename__startswith="view_")
    user.user_permissions.set(view_permissions)

    return user


# ============================================================================
# Database Fixtures
# ============================================================================


@pytest.fixture
def sample_skill(db):
    """
    Creates a sample Skill instance for testing.

    Usage:
        def test_skill_display(sample_skill):
            assert 'Python' in sample_skill.name
    """
    from future_skills.models import Skill

    return Skill.objects.create(
        name="Python Programming",
        category="Technical",
        description="Advanced Python programming skills",
    )


@pytest.fixture
def sample_job_role(db):
    """
    Creates a sample JobRole instance for testing.

    Usage:
        def test_job_role_display(sample_job_role):
            assert 'Engineer' in sample_job_role.name
    """
    from future_skills.models import JobRole

    return JobRole.objects.create(
        name="Software Engineer",
        department="Engineering",
        description="Develops and maintains software applications",
    )


@pytest.fixture
def sample_future_skill_prediction(db, sample_job_role, sample_skill):
    """
    Creates a sample FutureSkillPrediction instance for testing.

    Usage:
        def test_prediction_display(sample_future_skill_prediction):
            assert sample_future_skill_prediction.level == 'HIGH'
    """
    from future_skills.models import FutureSkillPrediction

    return FutureSkillPrediction.objects.create(
        job_role=sample_job_role,
        skill=sample_skill,
        horizon_years=5,
        score=85.0,
        level="HIGH",
        rationale="High demand for Python skills in software engineering",
    )


@pytest.fixture
def sample_prediction_run(db):
    """
    Creates a sample PredictionRun instance for testing.

    Usage:
        def test_prediction_run_results(sample_prediction_run):
            assert sample_prediction_run.total_predictions > 0
    """
    from future_skills.models import PredictionRun

    return PredictionRun.objects.create(
        description="Test prediction run",
        total_predictions=10,
        parameters={"horizon_years": 5, "engine": "rules"},
    )


@pytest.fixture
def sample_employee(db, sample_job_role):
    """
    Creates a sample Employee instance for testing.

    Usage:
        def test_employee_info(sample_employee):
            assert sample_employee.name == 'John Doe'
            assert 'Python' in sample_employee.current_skills
    """
    from future_skills.models import Employee

    return Employee.objects.create(
        name="John Doe",
        email="john.doe@example.com",
        department="Engineering",
        position="Developer",
        job_role=sample_job_role,
        current_skills=["Python", "Django"],
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
    mock_model = mocker.patch("future_skills.services.prediction_engine.load_model")
    mock_model.return_value.predict.return_value = ["AI", SKILL_MACHINE_LEARNING]
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
def skill_data():
    """
    Provides sample skill data for testing.

    Usage:
        def test_skill_creation(skill_data):
            skill = Skill.objects.create(**skill_data)
            assert skill.category == 'Technical'
    """
    return {
        "name": SKILL_MACHINE_LEARNING,
        "category": "Technical",
        "description": "ML algorithms and frameworks",
    }


@pytest.fixture
def job_role_data():
    """
    Provides sample job role data for testing.

    Usage:
        def test_job_role_creation(job_role_data):
            role = JobRole.objects.create(**job_role_data)
            assert role.department == 'Data Science'
    """
    return {
        "name": "Data Analyst",
        "department": "Data Science",
        "description": "Analyzes data and provides insights",
    }


@pytest.fixture
def future_skill_prediction_data(sample_job_role, sample_skill):
    """
    Provides sample future skill prediction data for testing.

    Usage:
        def test_prediction_creation(future_skill_prediction_data):
            prediction = FutureSkillPrediction.objects.create(**future_skill_prediction_data)
            assert prediction.level == 'HIGH'
    """
    return {
        "job_role": sample_job_role,
        "skill": sample_skill,
        "horizon_years": 5,
        "score": 90.0,
        "level": "HIGH",
        "rationale": "Strong market demand",
    }


# ============================================================================
# Pytest Configuration
# ============================================================================


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "e2e: marks tests as end-to-end tests")
    config.addinivalue_line("markers", "ml: marks tests that require ML model")
    config.addinivalue_line("markers", "api: marks tests for API endpoints")
