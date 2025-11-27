"""
Test fixtures for SmartHR360 Future Skills project.

This module contains reusable test data fixtures.
"""

import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


# ============================================================================
# Complex Model Fixtures
# ============================================================================

@pytest.fixture
def complete_employee_with_predictions(db, sample_employee):
    """
    Creates an employee with complete prediction history.
    
    Usage:
        def test_employee_history(complete_employee_with_predictions):
            employee = complete_employee_with_predictions
            assert employee.prediction_runs.count() > 0
    """
    from future_skills.models import PredictionRun
    
    # Create multiple prediction runs
    for i in range(3):
        PredictionRun.objects.create(
            employee=sample_employee,
            status='completed',
            confidence_score=0.70 + (i * 0.05),
            predicted_skills=[f'Skill {j}' for j in range(3)],
            model_version=f'v1.{i}'
        )
    
    return sample_employee


@pytest.fixture
def multiple_employees(db):
    """
    Creates multiple employees for testing list operations.
    
    Usage:
        def test_employee_listing(multiple_employees):
            assert len(multiple_employees) == 5
    """
    from future_skills.models import Employee
    
    employees = []
    for i in range(5):
        emp = Employee.objects.create(
            name=f'Employee {i}',
            email=f'employee{i}@example.com',
            department='Engineering' if i % 2 == 0 else 'Marketing',
            position=f'Position {i}',
            current_skills=[f'Skill {j}' for j in range(3)]
        )
        employees.append(emp)
    
    return employees


@pytest.fixture
def multiple_future_skills(db):
    """
    Creates multiple future skills for testing.
    
    Usage:
        def test_skill_categories(multiple_future_skills):
            assert len(multiple_future_skills) == 10
    """
    from future_skills.models import FutureSkill
    
    categories = ['Technical', 'Soft Skills', 'Leadership', 'Domain']
    skills = []
    
    for i in range(10):
        skill = FutureSkill.objects.create(
            skill_name=f'Skill {i}',
            category=categories[i % len(categories)],
            description=f'Description for skill {i}',
            importance_score=0.5 + (i * 0.05),
            relevance_score=0.6 + (i * 0.04)
        )
        skills.append(skill)
    
    return skills


# ============================================================================
# Scenario Fixtures
# ============================================================================

@pytest.fixture
def skills_gap_scenario(db):
    """
    Creates a scenario for testing skills gap analysis.
    
    Returns: dict with employees, current_skills, and future_skills
    """
    from future_skills.models import Employee, FutureSkill
    
    # Create future skills that are in demand
    future_skills = [
        FutureSkill.objects.create(
            skill_name='AI/ML',
            category='Technical',
            importance_score=0.95,
            relevance_score=0.90
        ),
        FutureSkill.objects.create(
            skill_name='Cloud Architecture',
            category='Technical',
            importance_score=0.88,
            relevance_score=0.85
        ),
        FutureSkill.objects.create(
            skill_name='Leadership',
            category='Soft Skills',
            importance_score=0.82,
            relevance_score=0.80
        )
    ]
    
    # Create employees with gaps in their skills
    employees = [
        Employee.objects.create(
            name='Developer A',
            email='deva@example.com',
            department='Engineering',
            current_skills=['Python', 'Django']  # Missing AI/ML, Cloud
        ),
        Employee.objects.create(
            name='Developer B',
            email='devb@example.com',
            department='Engineering',
            current_skills=['JavaScript', 'React']  # Missing AI/ML, Cloud
        )
    ]
    
    return {
        'employees': employees,
        'future_skills': future_skills,
        'expected_gaps': {
            'Developer A': ['AI/ML', 'Cloud Architecture', 'Leadership'],
            'Developer B': ['AI/ML', 'Cloud Architecture', 'Leadership']
        }
    }


@pytest.fixture
def prediction_test_scenario(db):
    """
    Creates a complete scenario for testing prediction functionality.
    
    Returns: dict with employee, input_data, and expected_predictions
    """
    from future_skills.models import Employee, FutureSkill
    
    # Create employee
    employee = Employee.objects.create(
        name='Test Employee',
        email='test@example.com',
        department='Data Science',
        position='Data Analyst',
        current_skills=['Python', 'SQL', 'Excel']
    )
    
    # Create future skills that should be predicted
    predicted_skills = [
        FutureSkill.objects.create(
            skill_name='Machine Learning',
            category='Technical',
            importance_score=0.90
        ),
        FutureSkill.objects.create(
            skill_name='Data Visualization',
            category='Technical',
            importance_score=0.85
        )
    ]
    
    return {
        'employee': employee,
        'input_data': {
            'current_skills': employee.current_skills,
            'department': employee.department,
            'position': employee.position
        },
        'expected_skills': predicted_skills
    }


# ============================================================================
# API Request Fixtures
# ============================================================================

@pytest.fixture
def valid_employee_payload():
    """Provides valid employee creation payload."""
    return {
        'name': 'Valid Employee',
        'email': 'valid@example.com',
        'department': 'IT',
        'position': 'Software Engineer',
        'current_skills': ['Python', 'Django', 'PostgreSQL'],
        'experience_years': 5
    }


@pytest.fixture
def invalid_employee_payload():
    """Provides invalid employee creation payload for testing validation."""
    return {
        'name': '',  # Invalid: empty name
        'email': 'invalid-email',  # Invalid: not a proper email
        'department': 'IT',
        # Missing required fields
    }


@pytest.fixture
def valid_prediction_payload(sample_employee):
    """Provides valid prediction request payload."""
    return {
        'employee_id': sample_employee.id,
        'current_skills': sample_employee.current_skills,
        'department': sample_employee.department,
        'use_ml': True
    }


# ============================================================================
# File Upload Fixtures
# ============================================================================

@pytest.fixture
def sample_csv_data():
    """Provides sample CSV data for testing bulk imports."""
    import io
    
    csv_content = """name,email,department,position,current_skills
John Doe,john@example.com,Engineering,Developer,"Python,JavaScript"
Jane Smith,jane@example.com,Marketing,Manager,"SEO,Analytics"
Bob Wilson,bob@example.com,Sales,Representative,"CRM,Communication"
"""
    return io.StringIO(csv_content)


# ============================================================================
# Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_ml_predictions(mocker):
    """Mocks ML model predictions for testing without actual model."""
    mock_predict = mocker.patch('future_skills.services.prediction_engine.PredictionEngine.predict')
    mock_predict.return_value = {
        'predictions': ['AI/ML', 'Cloud Computing', 'DevOps'],
        'confidence_scores': [0.85, 0.78, 0.72],
        'model_version': 'v1.0'
    }
    return mock_predict


@pytest.fixture
def mock_recommendation_engine(mocker):
    """Mocks recommendation engine for testing."""
    mock_recommend = mocker.patch('future_skills.services.recommendation_engine.RecommendationEngine.recommend')
    mock_recommend.return_value = {
        'recommendations': [
            {'skill_name': 'Machine Learning', 'score': 0.90},
            {'skill_name': 'Data Science', 'score': 0.85},
            {'skill_name': 'Cloud Computing', 'score': 0.80}
        ]
    }
    return mock_recommend


# ============================================================================
# Time-based Fixtures
# ============================================================================

@pytest.fixture
def freeze_time():
    """Freezes time for testing time-dependent features."""
    import freezegun
    with freezegun.freeze_time('2025-01-01 12:00:00'):
        yield


# ============================================================================
# Cache Fixtures
# ============================================================================

@pytest.fixture
def clear_cache():
    """Clears Django cache before and after test."""
    from django.core.cache import cache
    cache.clear()
    yield
    cache.clear()


# ============================================================================
# Settings Fixtures
# ============================================================================

@pytest.fixture
def ml_enabled_settings(settings):
    """Enables ML features for testing."""
    settings.FUTURE_SKILLS_USE_ML = True
    settings.FUTURE_SKILLS_ENABLE_MONITORING = True
    return settings


@pytest.fixture
def ml_disabled_settings(settings):
    """Disables ML features for testing."""
    settings.FUTURE_SKILLS_USE_ML = False
    settings.FUTURE_SKILLS_ENABLE_MONITORING = False
    return settings
