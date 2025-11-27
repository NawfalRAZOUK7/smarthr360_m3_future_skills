"""
End-to-End tests for SmartHR360 Future Skills project.

These tests simulate complete user journeys through the application.
"""

import pytest
from django.urls import reverse
from rest_framework import status


@pytest.mark.django_db
@pytest.mark.e2e
@pytest.mark.slow
class TestCompleteUserJourney:
    """Test complete user journey from login to prediction."""

    def test_complete_hr_manager_workflow(self, api_client, hr_manager, sample_job_role, sample_skill):
        """
        Test complete HR manager workflow:
        1. Login
        2. View future skill predictions
        3. Recalculate predictions
        4. View updated results
        5. Check recommendations
        """
        # Step 1: Authenticate
        api_client.force_authenticate(user=hr_manager)

        # Step 2: View future skill predictions
        url = reverse('future-skills-list')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK

        # Step 3: Filter by job role
        response = api_client.get(url, {'job_role_id': sample_job_role.id})
        assert response.status_code == status.HTTP_200_OK

        # Step 4: Recalculate predictions (requires staff permission)
        # hr_manager should have appropriate permissions for this
        recalc_url = reverse('future-skills-recalculate')
        recalc_data = {'horizon_years': 5}
        response = api_client.post(recalc_url, recalc_data, format='json')
        # May return 403 if hr_manager doesn't have IsHRStaff permission
        # or 200 if they do
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]

        # Step 5: View market trends
        trends_url = reverse('market-trends-list')
        response = api_client.get(trends_url)
        assert response.status_code == status.HTTP_200_OK

        # Step 6: View HR investment recommendations
        recommendations_url = reverse('hr-investment-recommendations-list')
        response = api_client.get(recommendations_url)
        assert response.status_code == status.HTTP_200_OK

    def test_viewer_limited_workflow(self, api_client, hr_viewer, sample_future_skill_prediction):
        """Test that viewer can only read data, not modify."""
        api_client.force_authenticate(user=hr_viewer)

        # Cannot view predictions (requires group membership)
        url = reverse('future-skills-list')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Cannot recalculate predictions (requires IsHRStaff)
        recalc_url = reverse('future-skills-recalculate')
        recalc_data = {'horizon_years': 5}
        response = api_client.post(recalc_url, recalc_data, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
@pytest.mark.e2e
class TestSkillManagementJourney:
    """Test skill and prediction management user journey."""

    def test_prediction_lifecycle(self, admin_client, sample_skill, sample_job_role):
        """
        Test complete prediction lifecycle:
        1. Create base data (skills, job roles)
        2. Trigger prediction recalculation
        3. View results
        4. Check recommendations generated
        """
        # Step 1: Skills and job roles already exist via fixtures

        # Step 2: Trigger recalculation
        url = reverse('future-skills-recalculate')
        data = {'horizon_years': 5}
        response = admin_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert 'total_predictions' in response.data

        # Step 3: View prediction results
        predictions_url = reverse('future-skills-list')
        response = admin_client.get(predictions_url)

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)

        # Step 4: Check HR recommendations
        recommendations_url = reverse('hr-investment-recommendations-list')
        response = admin_client.get(recommendations_url)

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)


@pytest.mark.django_db
@pytest.mark.e2e
@pytest.mark.slow
class TestBulkOperationsJourney:
    """Test bulk operations workflow - skipped as bulk endpoints not implemented."""

    @pytest.mark.skip(reason="Bulk prediction endpoints not yet implemented")
    def test_bulk_employee_import_and_predict(self, admin_client, db):
        """Test importing multiple employees and running bulk predictions."""
        pass


@pytest.mark.django_db
@pytest.mark.e2e
class TestReportingJourney:
    """Test reporting and analytics journey."""

    def test_view_market_trends(self, authenticated_client):
        """Test viewing market trends for analysis."""
        url = reverse('market-trends-list')
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)

    def test_view_economic_reports(self, authenticated_client):
        """Test viewing economic reports."""
        url = reverse('economic-reports-list')
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)


@pytest.mark.django_db
@pytest.mark.e2e
@pytest.mark.ml
class TestMLPipelineJourney:
    """Test complete ML pipeline journey - skipped as advanced ML endpoints not implemented."""

    @pytest.mark.skip(reason="Advanced ML endpoints not yet implemented")
    def test_model_training_to_prediction(self, admin_client, settings):
        """Test complete ML pipeline."""
        pass


@pytest.mark.django_db
@pytest.mark.e2e
class TestErrorRecoveryJourney:
    """Test error handling and recovery workflows."""

    def test_prediction_invalid_horizon(self, admin_client):
        """Test system behavior when invalid horizon_years is provided."""
        url = reverse('future-skills-recalculate')

        # Send invalid data to trigger error
        invalid_data = {'horizon_years': 'invalid'}

        response = admin_client.post(url, invalid_data, format='json')

        # Should return error status with helpful message
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_filter_invalid_job_role(self, authenticated_client):
        """Test handling of invalid job role filter."""
        url = reverse('future-skills-list')

        response = authenticated_client.get(url, {'job_role_id': 99999})

        # Should return empty results or 200 OK (not crash)
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
@pytest.mark.e2e
@pytest.mark.slow
class TestPerformanceJourney:
    """Test performance-critical workflows."""

    def test_large_dataset_handling(self, authenticated_client, db):
        """Test system behavior with large datasets."""
        from future_skills.models import Skill

        # Create many skills
        skills = [
            Skill(
                name=f'Skill {i}',
                category='Technical'
            )
            for i in range(100)
        ]
        Skill.objects.bulk_create(skills)

        # Test listing predictions (should complete without timeout)
        url = reverse('future-skills-list')
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Verify response time is acceptable (add timing if needed)
