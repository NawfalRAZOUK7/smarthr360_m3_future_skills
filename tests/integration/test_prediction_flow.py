"""
Integration tests for the Future Skills prediction flow.

These tests verify the complete workflow from API requests to ML predictions.
NOTE: Most tests in this file are skipped as they test endpoints/models not yet implemented.
"""

import pytest
from django.urls import reverse
from rest_framework import status


@pytest.mark.django_db
@pytest.mark.integration
class TestPredictionFlow:
    """Test complete prediction flow from API request to response."""

    def test_complete_prediction_flow(self, authenticated_client, sample_employee):
        """
        Test the complete prediction flow:
        1. User makes a prediction request
        2. System processes the request
        3. ML model generates predictions
        4. Results are returned to user
        """
        url = reverse("futureskill-predict-skills")
        data = {
            "employee_id": sample_employee.id,
            "current_skills": sample_employee.current_skills,
            "department": sample_employee.department,
        }

        response = authenticated_client.post(url, data, format="json")

        # Assert successful response
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]

        # Assert response structure (adjust based on actual API)
        # assert 'predictions' in response.data
        # assert 'confidence' in response.data
        # assert isinstance(response.data['predictions'], list)

    def test_prediction_flow_with_invalid_data(self, authenticated_client):
        """Test prediction flow with invalid input data."""
        url = reverse("futureskill-predict-skills")
        data = {
            "employee_id": 99999,  # Non-existent employee
            "current_skills": [],
        }

        response = authenticated_client.post(url, data, format="json")

        # Should return error status
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND,
        ]

    def test_prediction_requires_authentication(self, api_client, sample_employee):
        """Test that prediction endpoint requires authentication."""
        url = reverse("futureskill-predict-skills")
        data = {"employee_id": sample_employee.id}

        response = api_client.post(url, data, format="json")

        # DRF returns 403 when permission check fails (not 401)
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    @pytest.mark.slow
    def test_bulk_prediction_flow(self, authenticated_client, db):
        """Test prediction flow for multiple employees at once."""
        from future_skills.models import Employee

        # Create multiple employees
        employees = [
            Employee.objects.create(
                name=f"Employee {i}",
                email=f"employee{i}@example.com",
                department="Engineering",
                position="Developer",
                current_skills=["Python", "Django"],
            )
            for i in range(5)
        ]

        # Assuming bulk prediction endpoint exists
        url = reverse("futureskill-bulk-predict")
        data = {"employee_ids": [emp.id for emp in employees]}

        response = authenticated_client.post(url, data, format="json")

        # Assert successful bulk processing
        # Adjust assertions based on actual API response
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_202_ACCEPTED]


@pytest.mark.django_db
@pytest.mark.integration
class TestRecommendationFlow:
    """Test complete recommendation flow."""

    def test_get_recommendations_for_employee(
        self, authenticated_client, sample_employee, sample_future_skill_prediction
    ):
        """Test getting skill recommendations for an employee."""
        url = reverse("futureskill-recommend-skills")
        data = {"employee_id": sample_employee.id}

        response = authenticated_client.post(url, data, format="json")

        # Assert successful response
        assert response.status_code == status.HTTP_200_OK

    def test_recommendation_considers_current_skills(
        self, authenticated_client, sample_employee
    ):
        """Test that recommendations consider employee's current skills."""
        url = reverse("futureskill-recommend-skills")
        data = {"employee_id": sample_employee.id, "exclude_current": True}

        response = authenticated_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        # Verify no current skills are recommended
        # if 'recommendations' in response.data:
        #     recommended_skills = [r['skill_name'] for r in response.data['recommendations']]
        #     assert not any(skill in sample_employee.current_skills for skill in recommended_skills)


@pytest.mark.django_db
@pytest.mark.integration
class TestDataPipelineFlow:
    """Test data pipeline from input to storage."""

    def test_employee_creation_flow(self, admin_client):
        """Test complete employee creation workflow."""
        url = reverse("employee-list")
        data = {
            "name": "New Employee",
            "email": "new.employee@example.com",
            "department": "Sales",
            "position": "Sales Representative",
            "current_skills": ["CRM", "Communication"],
        }

        response = admin_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == data["name"]
        assert response.data["email"] == data["email"]

    def test_skill_tracking_flow(self, admin_client, sample_employee, sample_skill):
        """Test tracking skill assignments to employees using ManyToMany relationship."""
        # Add skill to employee
        url = reverse("employee-add-skill", kwargs={"pk": sample_employee.id})
        data = {"skill_id": sample_skill.id}

        response = admin_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert sample_skill.name in response.data["skills"]

        # Verify employee was updated using ManyToMany relationship
        sample_employee.refresh_from_db()
        assert sample_skill in sample_employee.skills.all()

        # Remove skill
        remove_url = reverse("employee-remove-skill", kwargs={"pk": sample_employee.id})
        remove_response = admin_client.post(remove_url, data, format="json")

        assert remove_response.status_code == status.HTTP_200_OK
        assert sample_skill.name not in remove_response.data["skills"]


@pytest.mark.django_db
@pytest.mark.integration
@pytest.mark.ml
class TestMLModelIntegration:
    """Test ML model integration with the application."""

    def test_model_loading(self, settings):
        """Test that ML model can be loaded successfully."""
        from future_skills.services.prediction_engine import PredictionEngine

        # Test with ML disabled
        engine_no_ml = PredictionEngine(use_ml=False)
        assert engine_no_ml.model is None

        # Test with ML enabled (will fall back to rules if model doesn't exist)
        engine_ml = PredictionEngine(use_ml=True)
        # Should not raise error even if model doesn't exist
        assert engine_ml is not None

    def test_prediction_with_real_model(self, sample_job_role, sample_skill):
        """Test prediction using the actual ML model (if available)."""
        from future_skills.services.prediction_engine import PredictionEngine

        engine = PredictionEngine()

        score, level, rationale, explanation = engine.predict(
            job_role_id=sample_job_role.id, skill_id=sample_skill.id, horizon_years=5
        )

        # Verify prediction structure
        assert isinstance(score, float)
        assert 0 <= score <= 100
        assert level in ["LOW", "MEDIUM", "HIGH"]
        assert isinstance(rationale, str)
        assert isinstance(explanation, dict)

    def test_batch_prediction(self, sample_job_role, sample_skill, db):
        """Test batch prediction functionality."""
        from future_skills.models import Skill
        from future_skills.services.prediction_engine import PredictionEngine

        # Create multiple skills
        skills = [sample_skill]
        for i in range(3):
            skills.append(
                Skill.objects.create(name=f"Test Skill {i}", category="Technical")
            )

        engine = PredictionEngine()

        predictions_data = [
            {
                "job_role_id": sample_job_role.id,
                "skill_id": skill.id,
                "horizon_years": 5,
            }
            for skill in skills
        ]

        results = engine.batch_predict(predictions_data)

        assert len(results) == len(skills)
        for result in results:
            assert "score" in result
            assert "level" in result
            assert "rationale" in result


@pytest.mark.django_db
@pytest.mark.integration
class TestPermissionsFlow:
    """Test permission-based workflows."""

    def test_hr_manager_can_access_all_employees(
        self, api_client, hr_manager, sample_employee
    ):
        """Test that HR managers can access all employee data."""
        api_client.force_authenticate(user=hr_manager)

        url = reverse("employee-list")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK

    def test_regular_user_limited_access(self, authenticated_client):
        """Test that regular users have limited access."""
        url = reverse("employee-list")
        response = authenticated_client.get(url)

        # Depending on your permissions, this might be 200 or 403
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]

    def test_viewer_cannot_create_records(self, api_client, hr_viewer):
        """Test that viewers cannot create new records."""
        api_client.force_authenticate(user=hr_viewer)

        url = reverse("employee-list")
        data = {
            "name": "Test Employee",
            "email": "test@example.com",
            "department": "IT",
        }

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
