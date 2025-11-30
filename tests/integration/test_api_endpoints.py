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

    def test_list_future_skills(
        self, authenticated_client, sample_future_skill_prediction
    ):
        """Test listing all future skill predictions."""
        url = reverse("future-skills-list")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Response should be paginated
        assert "results" in response.data
        assert "count" in response.data
        assert isinstance(response.data["results"], list)

    def test_filter_by_job_role(
        self, authenticated_client, sample_future_skill_prediction
    ):
        """Test filtering predictions by job role."""
        url = reverse("future-skills-list")
        response = authenticated_client.get(
            url, {"job_role_id": sample_future_skill_prediction.job_role.id}
        )

        assert response.status_code == status.HTTP_200_OK

    def test_filter_by_horizon_years(
        self, authenticated_client, sample_future_skill_prediction
    ):
        """Test filtering predictions by horizon years."""
        url = reverse("future-skills-list")
        response = authenticated_client.get(url, {"horizon_years": 5})

        assert response.status_code == status.HTTP_200_OK

    def test_recalculate_predictions(self, admin_client):
        """Test recalculating future skill predictions."""
        url = reverse("future-skills-recalculate")
        response = admin_client.post(url, {"horizon_years": 5}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert "total_predictions" in response.data

    def test_invalid_horizon_years(self, admin_client):
        """Test that invalid horizon years returns empty results."""
        url = reverse("future-skills-list")
        response = admin_client.get(url, {"horizon_years": "invalid"})

        # Invalid horizon_years now returns an empty paginated response instead of 400
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 0
        assert len(response.data["results"]) == 0


@pytest.mark.django_db
@pytest.mark.integration
@pytest.mark.api
class TestMarketTrendAPI:
    """Test MarketTrend API endpoints."""

    def test_list_market_trends(self, authenticated_client):
        """Test listing market trends."""
        url = reverse("market-trends-list")
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
        url = reverse("future-skills-list")
        response = api_client.get(url)

        # DRF returns 403 when permission classes check fails on unauthenticated user
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    def test_authenticated_access_allowed(self, authenticated_client):
        """Test that authenticated requests with proper group membership are allowed."""
        url = reverse("future-skills-list")
        response = authenticated_client.get(url)

        # authenticated_client uses regular_user who has MANAGER group
        assert response.status_code == status.HTTP_200_OK

    def test_admin_access_allowed(self, admin_client):
        """Test that admin users have full access."""
        url = reverse("future-skills-recalculate")
        response = admin_client.post(url, {"horizon_years": 5}, format="json")

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
@pytest.mark.integration
@pytest.mark.api
class TestAPIPagination:
    """Test API pagination."""

    def test_pagination_applied(
        self, authenticated_client, db, sample_job_role, sample_skill
    ):
        """Test that pagination is applied to list endpoints."""
        from future_skills.models import FutureSkillPrediction, Skill, JobRole

        # Create additional skills to ensure we have enough unique combinations
        skills = [sample_skill]
        for i in range(1, 9):
            skill = Skill.objects.create(
                name=f"Test Skill {i}",
                category="Technical",
                description=f"Test skill for pagination {i}",
            )
            skills.append(skill)

        # Create additional job roles
        job_roles = [sample_job_role]
        for i in range(1, 7):
            job_role = JobRole.objects.create(
                name=f"Test Role {i}",
                department=f"Department {i}",
                description=f"Test role for pagination {i}",
            )
            job_roles.append(job_role)

        # Create 25 predictions with guaranteed unique combinations
        # Use a counter to track combinations and ensure uniqueness
        predictions = []
        counter = 0
        for skill in skills[:5]:  # Use first 5 skills
            for job_role in job_roles:  # Use all 4 job roles
                if counter >= 25:
                    break
                # Alternate horizon_years to create variety
                horizon = 3 + (counter % 3)

                prediction = FutureSkillPrediction.objects.create(
                    job_role=job_role,
                    skill=skill,
                    horizon_years=horizon,
                    score=float(counter * 3),
                    level="MEDIUM",
                    rationale=f"Prediction {counter}",
                )
                predictions.append(prediction)
                counter += 1
            if counter >= 25:
                break

        # Test future-skills-list pagination
        url = reverse("future-skills-list")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK

        # Check pagination structure
        assert "results" in response.data
        assert "count" in response.data
        assert "next" in response.data
        assert "previous" in response.data

        # Check page size
        assert len(response.data["results"]) == 10
        assert response.data["count"] == 25
        assert response.data["next"] is not None
        assert response.data["previous"] is None

        # Test page 2
        page2_response = authenticated_client.get(url, {"page": 2})
        assert page2_response.status_code == status.HTTP_200_OK
        assert len(page2_response.data["results"]) == 10
        assert page2_response.data["next"] is not None
        assert page2_response.data["previous"] is not None

        # Test page 3 (last page)
        page3_response = authenticated_client.get(url, {"page": 3})
        assert page3_response.status_code == status.HTTP_200_OK
        assert len(page3_response.data["results"]) == 5
        assert page3_response.data["next"] is None
        assert page3_response.data["previous"] is not None

    def test_employee_list_pagination(self, authenticated_client, db, sample_job_role):
        """Test that pagination is applied to employee list endpoint."""
        from future_skills.models import Employee

        # Create 15 employees
        for i in range(15):
            Employee.objects.create(
                name=f"Employee {i}",
                email=f"emp{i}@test.com",
                department="Engineering",
                position="Developer",
                job_role=sample_job_role,
                current_skills=["Python"],
            )

        url = reverse("employee-list")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 10
        assert response.data["count"] == 15

    def test_custom_page_size(self, authenticated_client, db, sample_job_role):
        """Test that custom page_size parameter works correctly."""
        from future_skills.models import Employee

        # Create 15 employees
        for i in range(15):
            Employee.objects.create(
                name=f"Employee {i}",
                email=f"emp{i}@test.com",
                department="Engineering",
                position="Developer",
                job_role=sample_job_role,
                current_skills=["Python"],
            )

        url = reverse("employee-list")
        response = authenticated_client.get(url, {"page_size": 5})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) <= 5


@pytest.mark.django_db
@pytest.mark.integration
@pytest.mark.api
class TestAPIErrorHandling:
    """Test API error handling."""

    def test_invalid_horizon_years_returns_400(self, admin_client):
        """Test that invalid horizon years returns 400 Bad Request."""
        url = reverse("future-skills-recalculate")
        data = {"horizon_years": "invalid"}

        response = admin_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_url_returns_404(self, authenticated_client):
        """Test that non-existent endpoints return 404."""
        response = authenticated_client.get("/api/non-existent-endpoint/")

        assert response.status_code == status.HTTP_404_NOT_FOUND
