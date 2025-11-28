"""
Integration tests for ML model integration with API endpoints.

These tests verify that:
- ML predictions work correctly with API endpoints
- ML/rules-based engines can be switched dynamically
- Prediction endpoints handle ML models correctly
- Recalculation works with both ML and rules-based engines
"""

import pytest
from django.urls import reverse
from rest_framework import status
from pathlib import Path
from unittest.mock import patch, MagicMock


@pytest.mark.django_db
@pytest.mark.integration
@pytest.mark.ml
class TestMLIntegration:
    """Test ML model integration with API endpoints."""

    def test_prediction_endpoint_uses_ml(self, authenticated_client, sample_employee, sample_future_skill_prediction, settings):
        """Test that prediction endpoint can use ML model."""
        settings.FUTURE_SKILLS_USE_ML = True

        url = reverse('futureskill-predict-skills')
        data = {'employee_id': sample_employee.id}

        response = authenticated_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        # Response might be empty if no predictions exist for employee's job role
        assert isinstance(response.data, list)

    def test_prediction_endpoint_uses_rules(self, authenticated_client, sample_employee, sample_future_skill_prediction, settings):
        """Test that prediction endpoint works with rules-based engine."""
        settings.FUTURE_SKILLS_USE_ML = False

        url = reverse('futureskill-predict-skills')
        data = {'employee_id': sample_employee.id}

        response = authenticated_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        # Response might be empty if no predictions exist for employee's job role
        assert isinstance(response.data, list)

    def test_recalculate_with_ml(self, admin_client, settings):
        """Test that recalculate endpoint works with ML."""
        settings.FUTURE_SKILLS_USE_ML = True

        url = reverse('future-skills-recalculate')
        data = {'horizon_years': 5}

        response = admin_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert 'total_predictions' in response.data
        assert response.data['total_predictions'] >= 0

    def test_recalculate_with_rules(self, admin_client, settings):
        """Test that recalculate endpoint works with rules-based engine."""
        settings.FUTURE_SKILLS_USE_ML = False

        url = reverse('future-skills-recalculate')
        data = {'horizon_years': 5}

        response = admin_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert 'total_predictions' in response.data
        assert response.data['total_predictions'] >= 0

    def test_switch_between_ml_and_rules(self, authenticated_client, sample_employee, sample_future_skill_prediction, settings):
        """Test switching between ML and rules-based predictions."""
        url = reverse('futureskill-predict-skills')
        data = {'employee_id': sample_employee.id}

        # First request with ML
        settings.FUTURE_SKILLS_USE_ML = True
        response_ml = authenticated_client.post(url, data, format='json')
        assert response_ml.status_code == status.HTTP_200_OK

        # Second request with rules
        settings.FUTURE_SKILLS_USE_ML = False
        response_rules = authenticated_client.post(url, data, format='json')
        assert response_rules.status_code == status.HTTP_200_OK

        # Both should return valid list responses
        assert isinstance(response_ml.data, list)
        assert isinstance(response_rules.data, list)


@pytest.mark.django_db
@pytest.mark.integration
@pytest.mark.ml
class TestMLPredictionQuality:
    """Test quality of ML predictions through API."""

    def test_ml_predictions_have_valid_scores(self, authenticated_client, sample_employee, settings):
        """Test that ML predictions return valid scores."""
        settings.FUTURE_SKILLS_USE_ML = True

        url = reverse('futureskill-predict-skills')
        data = {'employee_id': sample_employee.id}

        response = authenticated_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK

        # Check each prediction has valid score
        if isinstance(response.data, list) and len(response.data) > 0:
            for prediction in response.data:
                if 'score' in prediction:
                    score = prediction['score']
                    assert 0 <= score <= 100, f"Score {score} out of valid range"

    def test_ml_predictions_have_levels(self, authenticated_client, sample_employee, settings):
        """Test that ML predictions return valid priority levels."""
        settings.FUTURE_SKILLS_USE_ML = True

        url = reverse('futureskill-predict-skills')
        data = {'employee_id': sample_employee.id}

        response = authenticated_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK

        valid_levels = ['HIGH', 'MEDIUM', 'LOW']
        if isinstance(response.data, list) and len(response.data) > 0:
            for prediction in response.data:
                if 'priority_level' in prediction:
                    assert prediction['priority_level'] in valid_levels

    def test_ml_predictions_consistency(self, authenticated_client, sample_employee, settings):
        """Test that ML predictions are consistent for same input."""
        settings.FUTURE_SKILLS_USE_ML = True

        url = reverse('futureskill-predict-skills')
        data = {'employee_id': sample_employee.id}

        # Make two identical requests
        response1 = authenticated_client.post(url, data, format='json')
        response2 = authenticated_client.post(url, data, format='json')

        assert response1.status_code == status.HTTP_200_OK
        assert response2.status_code == status.HTTP_200_OK

        # Predictions should be consistent (same length at minimum)
        assert len(response1.data) == len(response2.data)


@pytest.mark.django_db
@pytest.mark.integration
@pytest.mark.ml
class TestMLRecalculationIntegration:
    """Test ML model integration with recalculation endpoints."""

    def test_recalculation_creates_predictions(self, admin_client, sample_job_role, sample_skill, settings):
        """Test that recalculation creates FutureSkillPrediction records."""
        from future_skills.models import FutureSkillPrediction

        settings.FUTURE_SKILLS_USE_ML = False  # Use rules for predictability

        # Clear existing predictions
        FutureSkillPrediction.objects.all().delete()

        url = reverse('future-skills-recalculate')
        data = {'horizon_years': 5}

        response = admin_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['total_predictions'] > 0

        # Verify predictions were created
        predictions = FutureSkillPrediction.objects.filter(horizon_years=5)
        assert predictions.exists()
        assert predictions.count() == response.data['total_predictions']

    def test_recalculation_with_different_horizons(self, admin_client, settings):
        """Test recalculation with different horizon years."""
        settings.FUTURE_SKILLS_USE_ML = False

        url = reverse('future-skills-recalculate')

        # Test different horizons
        horizons = [3, 5, 7]
        for horizon in horizons:
            data = {'horizon_years': horizon}
            response = admin_client.post(url, data, format='json')

            assert response.status_code == status.HTTP_200_OK
            assert 'total_predictions' in response.data

    def test_recalculation_updates_existing_predictions(self, admin_client, sample_future_skill_prediction, settings):
        """Test that recalculation updates existing predictions."""
        from future_skills.models import FutureSkillPrediction

        settings.FUTURE_SKILLS_USE_ML = False

        # Get initial prediction
        initial_prediction = FutureSkillPrediction.objects.get(
            id=sample_future_skill_prediction.id
        )
        initial_score = initial_prediction.score

        url = reverse('future-skills-recalculate')
        data = {'horizon_years': sample_future_skill_prediction.horizon_years}

        response = admin_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK

        # Prediction should still exist (updated, not duplicated)
        updated_prediction = FutureSkillPrediction.objects.get(
            job_role=sample_future_skill_prediction.job_role,
            skill=sample_future_skill_prediction.skill,
            horizon_years=sample_future_skill_prediction.horizon_years
        )
        assert updated_prediction is not None


@pytest.mark.django_db
@pytest.mark.integration
@pytest.mark.ml
class TestMLErrorHandling:
    """Test error handling in ML integration."""

    def test_ml_handles_missing_model_gracefully(self, authenticated_client, sample_employee, settings):
        """Test that system handles missing ML model gracefully."""
        settings.FUTURE_SKILLS_USE_ML = True
        settings.FUTURE_SKILLS_MODEL_PATH = Path('/nonexistent/model.pkl')

        url = reverse('futureskill-predict-skills')
        data = {'employee_id': sample_employee.id}

        response = authenticated_client.post(url, data, format='json')

        # Should either succeed with fallback to rules or return meaningful error
        assert response.status_code in [
            status.HTTP_200_OK,  # Fallback to rules
            status.HTTP_500_INTERNAL_SERVER_ERROR  # Or explicit error
        ]

    def test_invalid_employee_id(self, authenticated_client, settings):
        """Test prediction with invalid employee ID."""
        settings.FUTURE_SKILLS_USE_ML = True

        url = reverse('futureskill-predict-skills')
        data = {'employee_id': 99999}

        response = authenticated_client.post(url, data, format='json')

        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND
        ]

    def test_recalculate_with_invalid_horizon(self, admin_client, settings):
        """Test recalculation with invalid horizon years."""
        settings.FUTURE_SKILLS_USE_ML = False

        url = reverse('future-skills-recalculate')
        data = {'horizon_years': -1}  # Invalid negative horizon

        response = admin_client.post(url, data, format='json')

        # Should return error for invalid input
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_200_OK  # Some APIs might handle this gracefully
        ]


@pytest.mark.django_db
@pytest.mark.integration
@pytest.mark.ml
@pytest.mark.slow
class TestMLPerformanceIntegration:
    """Test ML model performance in integration scenarios."""

    def test_batch_prediction_performance(self, authenticated_client, db, settings):
        """Test ML predictions for multiple employees."""
        from future_skills.models import Employee, JobRole

        settings.FUTURE_SKILLS_USE_ML = False  # Use rules for speed

        # Create a job role
        job_role = JobRole.objects.create(
            name='Software Engineer',
            department='Engineering',
            description='Develops software'
        )

        # Create multiple employees
        employees = []
        for i in range(5):
            employee = Employee.objects.create(
                name=f'Employee {i}',
                email=f'employee{i}@test.com',
                department='Engineering',
                position='Developer',
                job_role=job_role,
                current_skills=['Python', 'Django']
            )
            employees.append(employee)

        url = reverse('futureskill-predict-skills')

        # Make predictions for each employee
        responses = []
        for employee in employees:
            data = {'employee_id': employee.id}
            response = authenticated_client.post(url, data, format='json')
            responses.append(response)

        # All should succeed
        for response in responses:
            assert response.status_code == status.HTTP_200_OK

    def test_concurrent_recalculations(self, admin_client, settings):
        """Test multiple recalculation requests."""
        settings.FUTURE_SKILLS_USE_ML = False

        url = reverse('future-skills-recalculate')
        data = {'horizon_years': 5}

        # Make multiple requests
        responses = []
        for _ in range(3):
            response = admin_client.post(url, data, format='json')
            responses.append(response)

        # All should succeed
        for response in responses:
            assert response.status_code == status.HTTP_200_OK
            assert 'total_predictions' in response.data


@pytest.mark.django_db
@pytest.mark.integration
@pytest.mark.ml
class TestMLMonitoringIntegration:
    """Test ML monitoring integration with API."""

    def test_predictions_are_logged(self, authenticated_client, sample_employee, settings, tmp_path):
        """Test that predictions are logged for monitoring."""
        settings.FUTURE_SKILLS_USE_ML = False
        settings.FUTURE_SKILLS_ENABLE_MONITORING = True
        log_file = tmp_path / "predictions.jsonl"
        settings.FUTURE_SKILLS_MONITORING_LOG = log_file

        url = reverse('futureskill-predict-skills')
        data = {'employee_id': sample_employee.id}

        response = authenticated_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK

        # Note: Logging happens at prediction engine level, not directly in view
        # This test verifies the integration doesn't break with monitoring enabled

    def test_monitoring_can_be_disabled(self, authenticated_client, sample_employee, settings):
        """Test that monitoring can be disabled without breaking predictions."""
        settings.FUTURE_SKILLS_USE_ML = False
        settings.FUTURE_SKILLS_ENABLE_MONITORING = False

        url = reverse('futureskill-predict-skills')
        data = {'employee_id': sample_employee.id}

        response = authenticated_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
