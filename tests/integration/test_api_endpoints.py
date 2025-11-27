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
class TestFutureSkillAPI:
    """Test FutureSkill API endpoints."""

    def test_list_future_skills(self, authenticated_client, sample_future_skill):
        """Test listing all future skills."""
        url = reverse('futureskill-list')
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, (list, dict))

    def test_retrieve_future_skill(self, authenticated_client, sample_future_skill):
        """Test retrieving a specific future skill."""
        url = reverse('futureskill-detail', kwargs={'pk': sample_future_skill.id})
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['skill_name'] == sample_future_skill.skill_name

    def test_create_future_skill(self, admin_client, future_skill_data):
        """Test creating a new future skill."""
        url = reverse('futureskill-list')
        response = admin_client.post(url, future_skill_data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['skill_name'] == future_skill_data['skill_name']

    def test_update_future_skill(self, admin_client, sample_future_skill):
        """Test updating an existing future skill."""
        url = reverse('futureskill-detail', kwargs={'pk': sample_future_skill.id})
        data = {'importance_score': 0.95}

        response = admin_client.patch(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['importance_score'] == pytest.approx(0.95)

    def test_delete_future_skill(self, admin_client, sample_future_skill):
        """Test deleting a future skill."""
        url = reverse('futureskill-detail', kwargs={'pk': sample_future_skill.id})
        response = admin_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify deletion
        response = admin_client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_search_future_skills(self, authenticated_client, sample_future_skill):
        """Test searching for future skills."""
        url = reverse('futureskill-list')
        response = authenticated_client.get(url, {'search': 'Python'})

        assert response.status_code == status.HTTP_200_OK

    def test_filter_by_category(self, authenticated_client, sample_future_skill):
        """Test filtering skills by category."""
        url = reverse('futureskill-list')
        response = authenticated_client.get(url, {'category': 'Technical'})

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
@pytest.mark.integration
@pytest.mark.api
class TestEmployeeAPI:
    """Test Employee API endpoints."""

    def test_list_employees(self, authenticated_client, sample_employee):
        """Test listing all employees."""
        url = reverse('employee-list')
        response = authenticated_client.get(url)

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]

    def test_retrieve_employee(self, authenticated_client, sample_employee):
        """Test retrieving a specific employee."""
        url = reverse('employee-detail', kwargs={'pk': sample_employee.id})
        response = authenticated_client.get(url)

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]

    def test_create_employee(self, admin_client, employee_data):
        """Test creating a new employee."""
        url = reverse('employee-list')
        response = admin_client.post(url, employee_data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == employee_data['name']


@pytest.mark.django_db
@pytest.mark.integration
@pytest.mark.api
class TestPredictionAPI:
    """Test Prediction API endpoints."""

    def test_list_predictions(self, authenticated_client, sample_prediction):
        """Test listing prediction runs."""
        url = reverse('predictionrun-list')
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK

    def test_retrieve_prediction(self, authenticated_client, sample_prediction):
        """Test retrieving a specific prediction."""
        url = reverse('predictionrun-detail', kwargs={'pk': sample_prediction.id})
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == sample_prediction.status

    def test_filter_predictions_by_status(self, authenticated_client, sample_prediction):
        """Test filtering predictions by status."""
        url = reverse('predictionrun-list')
        response = authenticated_client.get(url, {'status': 'completed'})

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
@pytest.mark.integration
@pytest.mark.api
class TestAPIAuthentication:
    """Test API authentication and authorization."""

    def test_unauthenticated_access_denied(self, api_client):
        """Test that unauthenticated requests are denied."""
        url = reverse('futureskill-list')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_authenticated_access_allowed(self, authenticated_client):
        """Test that authenticated requests are allowed."""
        url = reverse('futureskill-list')
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK

    def test_admin_access_allowed(self, admin_client):
        """Test that admin users have full access."""
        url = reverse('futureskill-list')
        response = admin_client.get(url)

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
@pytest.mark.integration
@pytest.mark.api
class TestAPIPagination:
    """Test API pagination."""

    def test_pagination_applied(self, authenticated_client, db):
        """Test that pagination is applied to list endpoints."""
        from future_skills.models import FutureSkill

        # Create multiple skills
        for i in range(15):
            FutureSkill.objects.create(
                skill_name=f'Skill {i}',
                category='Technical',
                importance_score=0.7
            )

        url = reverse('futureskill-list')
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Check if pagination info exists (adjust based on your pagination style)
        # assert 'count' in response.data or 'next' in response.data

    def test_page_size_parameter(self, authenticated_client, db):
        """Test custom page size parameter."""
        from future_skills.models import FutureSkill

        for i in range(10):
            FutureSkill.objects.create(
                skill_name=f'Skill {i}',
                category='Technical'
            )

        url = reverse('futureskill-list')
        response = authenticated_client.get(url, {'page_size': 5})

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
@pytest.mark.integration
@pytest.mark.api
class TestAPIErrorHandling:
    """Test API error handling."""

    def test_invalid_data_returns_400(self, admin_client):
        """Test that invalid data returns 400 Bad Request."""
        url = reverse('futureskill-list')
        data = {'skill_name': ''}  # Invalid: empty skill name

        response = admin_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_not_found_returns_404(self, authenticated_client):
        """Test that non-existent resources return 404."""
        url = reverse('futureskill-detail', kwargs={'pk': 99999})
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_method_not_allowed_returns_405(self, authenticated_client, sample_future_skill):
        """Test that unsupported methods return 405."""
        # Assuming PUT is not allowed, only PATCH
        # Test depends on your API configuration
        # url = reverse('futureskill-detail', kwargs={'pk': sample_future_skill.id})
        # data = {'skill_name': 'Updated'}
        # response = authenticated_client.put(url, data, format='json')
        # assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        pass  # Placeholder test - implement when API configuration is finalized
