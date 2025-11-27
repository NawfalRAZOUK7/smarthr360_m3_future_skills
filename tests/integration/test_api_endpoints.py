"""
Integration tests for API endpoints.

These tests verify that API endpoints work correctly with proper data flow.
"""

import pytest
from django.urls import reverse
from rest_framework import status


@pytest.mark.django_db
@pytest.mark.integration
@pytest.mark.api
class TestFutureSkillPredictionAPI:
    """Test FutureSkillPrediction API endpoints."""

    def test_list_future_skills(self, authenticated_client, sample_future_skill_prediction):
        """Test listing all future skill predictions."""
        url = reverse('future-skills-list')
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)

    def test_filter_by_job_role(self, authenticated_client, sample_future_skill_prediction):
        """Test filtering predictions by job role."""
        url = reverse('future-skills-list')
        response = authenticated_client.get(url, {'job_role_id': sample_future_skill_prediction.job_role.id})

        assert response.status_code == status.HTTP_200_OK

    def test_filter_by_horizon_years(self, authenticated_client, sample_future_skill_prediction):
        """Test filtering predictions by horizon years."""
        url = reverse('future-skills-list')
        response = authenticated_client.get(url, {'horizon_years': 5})

        assert response.status_code == status.HTTP_200_OK

    def test_recalculate_predictions(self, admin_client):
        """Test recalculating future skill predictions."""
        url = reverse('future-skills-recalculate')
        response = admin_client.post(url, {'horizon_years': 5}, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert 'total_predictions' in response.data

    def test_invalid_horizon_years(self, admin_client):
        """Test that invalid horizon years returns error."""
        url = reverse('future-skills-list')
        response = admin_client.get(url, {'horizon_years': 'invalid'})

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
@pytest.mark.integration
@pytest.mark.api
class TestMarketTrendAPI:
    """Test MarketTrend API endpoints."""

    def test_list_market_trends(self, authenticated_client):
        """Test listing market trends."""
        url = reverse('market-trends-list')
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)


@pytest.mark.django_db
@pytest.mark.integration
@pytest.mark.api
class TestAPIAuthentication:
    """Test API authentication and authorization."""

    def test_unauthenticated_access_denied(self, api_client):
        """Test that unauthenticated requests are denied."""
        url = reverse('future-skills-list')
        response = api_client.get(url)

        # DRF returns 403 when permission classes check fails on unauthenticated user
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_authenticated_access_allowed(self, authenticated_client):
        """Test that authenticated requests with proper group membership are allowed."""
        url = reverse('future-skills-list')
        response = authenticated_client.get(url)

        # authenticated_client uses regular_user who has MANAGER group
        assert response.status_code == status.HTTP_200_OK

    def test_admin_access_allowed(self, admin_client):
        """Test that admin users have full access."""
        url = reverse('future-skills-recalculate')
        response = admin_client.post(url, {'horizon_years': 5}, format='json')

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
@pytest.mark.integration
@pytest.mark.api
class TestAPIPagination:
    """Test API pagination - skipped as current API doesn't implement pagination."""

    @pytest.mark.skip(reason="Current API uses simple list views without pagination")
    def test_pagination_applied(self, authenticated_client, db):
        """Test that pagination is applied to list endpoints."""
        pass


@pytest.mark.django_db
@pytest.mark.integration
@pytest.mark.api
class TestAPIErrorHandling:
    """Test API error handling."""

    def test_invalid_horizon_years_returns_400(self, admin_client):
        """Test that invalid horizon years returns 400 Bad Request."""
        url = reverse('future-skills-recalculate')
        data = {'horizon_years': 'invalid'}

        response = admin_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_url_returns_404(self, authenticated_client):
        """Test that non-existent endpoints return 404."""
        response = authenticated_client.get('/api/non-existent-endpoint/')

        assert response.status_code == status.HTTP_404_NOT_FOUND
