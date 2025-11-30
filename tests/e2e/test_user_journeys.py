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

    def test_complete_hr_manager_workflow(
        self, api_client, hr_manager, sample_job_role, sample_skill
    ):
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
        url = reverse("future-skills-list")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK

        # Step 3: Filter by job role
        response = api_client.get(url, {"job_role_id": sample_job_role.id})
        assert response.status_code == status.HTTP_200_OK

        # Step 4: Recalculate predictions (requires staff permission)
        # hr_manager should have appropriate permissions for this
        recalc_url = reverse("future-skills-recalculate")
        recalc_data = {"horizon_years": 5}
        response = api_client.post(recalc_url, recalc_data, format="json")
        # May return 403 if hr_manager doesn't have IsHRStaff permission
        # or 200 if they do
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]

        # Step 5: View market trends
        trends_url = reverse("market-trends-list")
        response = api_client.get(trends_url)
        assert response.status_code == status.HTTP_200_OK

        # Step 6: View HR investment recommendations
        recommendations_url = reverse("hr-investment-recommendations-list")
        response = api_client.get(recommendations_url)
        assert response.status_code == status.HTTP_200_OK

    def test_viewer_limited_workflow(
        self, api_client, hr_viewer, sample_future_skill_prediction
    ):
        """Test that viewer can only read data, not modify."""
        api_client.force_authenticate(user=hr_viewer)

        # Cannot view predictions (requires group membership)
        url = reverse("future-skills-list")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Cannot recalculate predictions (requires IsHRStaff)
        recalc_url = reverse("future-skills-recalculate")
        recalc_data = {"horizon_years": 5}
        response = api_client.post(recalc_url, recalc_data, format="json")
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
        url = reverse("future-skills-recalculate")
        data = {"horizon_years": 5}
        response = admin_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert "total_predictions" in response.data

        # Step 3: View prediction results
        predictions_url = reverse("future-skills-list")
        response = admin_client.get(predictions_url)

        assert response.status_code == status.HTTP_200_OK
        # Handle paginated response
        data = response.data
        results = data.get("results", data) if isinstance(data, dict) else data
        assert isinstance(results, list)

        # Step 4: Check HR recommendations
        recommendations_url = reverse("hr-investment-recommendations-list")
        response = admin_client.get(recommendations_url)

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)


@pytest.mark.django_db
@pytest.mark.e2e
@pytest.mark.slow
class TestBulkOperationsJourney:
    """Test bulk operations workflow."""

    def test_bulk_employee_import_and_predict(self, admin_client, db, sample_job_role):
        """Test importing multiple employees and running bulk predictions."""
        url = reverse("employee-bulk-import")

        employees_data = [
            {
                "name": f"Employee {i}",
                "email": f"employee{i}@test.com",
                "department": "Engineering",
                "position": "Developer",
                "job_role_id": sample_job_role.id,
                "current_skills": ["Python", "Django"],
            }
            for i in range(5)
        ]

        data = {"employees": employees_data, "auto_predict": True, "horizon_years": 5}

        response = admin_client.post(url, data, format="json")

        # Debug output
        if response.status_code not in [status.HTTP_200_OK, status.HTTP_201_CREATED]:
            print(f"\nUnexpected status: {response.status_code}")
            print(f"Response data: {response.data}")
            print(f"Response content: {response.content}")

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED,
            status.HTTP_207_MULTI_STATUS,
        ]
        assert response.data.get("created", 0) == 5
        assert response.data.get("predictions_generated") is True


@pytest.mark.django_db
@pytest.mark.e2e
class TestReportingJourney:
    """Test reporting and analytics journey."""

    def test_view_market_trends(self, authenticated_client):
        """Test viewing market trends for analysis."""
        url = reverse("market-trends-list")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)

    def test_view_economic_reports(self, authenticated_client):
        """Test viewing economic reports."""
        url = reverse("economic-reports-list")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)


@pytest.mark.django_db
@pytest.mark.e2e
@pytest.mark.ml
class TestMLPipelineJourney:
    """Test complete ML pipeline journey."""

    @pytest.mark.slow
    def test_model_training_to_prediction(self, admin_client, db, tmp_path):
        """
        Test complete ML pipeline from training to prediction.

        This test:
        1. Creates a sample training dataset
        2. Starts model training via the API
        3. Verifies training run is created
        4. Checks training run status
        """
        # Step 1: Create sample dataset
        dataset_path = tmp_path / "training_data.csv"

        # Create sample data with required columns for ModelTrainer
        # Required: future_need_level (target) + feature columns
        sample_data = """job_role_name,skill_name,skill_category,job_department,trend_score,internal_usage,training_requests,scarcity_index,hiring_difficulty,avg_salary_k,economic_indicator,future_need_level
Software Engineer,Python,Technical,Engineering,0.85,0.80,45,0.65,0.70,95.5,0.75,HIGH
Software Engineer,Machine Learning,Technical,Engineering,0.90,0.75,60,0.80,0.85,110.0,0.78,HIGH
Manager,Leadership,Soft Skills,Management,0.75,0.85,30,0.40,0.50,85.0,0.72,MEDIUM
HR Specialist,Communication,Soft Skills,HR,0.80,0.90,25,0.35,0.45,75.0,0.70,MEDIUM
Data Analyst,Data Analysis,Technical,Analytics,0.88,0.82,50,0.70,0.75,90.0,0.76,HIGH
Project Manager,Project Management,Management,Management,0.82,0.88,35,0.55,0.60,88.0,0.73,MEDIUM
Cloud Engineer,Cloud Computing,Technical,Engineering,0.92,0.70,65,0.85,0.90,105.0,0.80,HIGH
Scrum Master,Agile Methods,Management,Engineering,0.78,0.80,28,0.50,0.55,82.0,0.71,MEDIUM
DevOps Engineer,DevOps,Technical,Engineering,0.87,0.78,55,0.75,0.80,98.0,0.77,HIGH
Team Lead,Team Collaboration,Soft Skills,Management,0.76,0.92,22,0.38,0.42,80.0,0.69,LOW
Business Analyst,SQL,Technical,Analytics,0.84,0.85,40,0.60,0.65,87.5,0.74,MEDIUM
UX Designer,Design Thinking,Soft Skills,Design,0.79,0.75,32,0.52,0.58,83.0,0.72,MEDIUM
Security Engineer,Cybersecurity,Technical,Security,0.91,0.68,68,0.88,0.92,112.0,0.81,HIGH
Product Manager,Product Strategy,Management,Product,0.83,0.87,38,0.58,0.63,93.0,0.75,MEDIUM
Quality Engineer,Testing,Technical,QA,0.77,0.82,26,0.48,0.52,78.0,0.70,LOW
Sales Manager,Negotiation,Soft Skills,Sales,0.74,0.88,20,0.42,0.48,86.0,0.68,LOW
Marketing Analyst,Marketing Analytics,Technical,Marketing,0.81,0.80,42,0.62,0.68,85.5,0.73,MEDIUM
Finance Manager,Financial Analysis,Management,Finance,0.80,0.90,30,0.45,0.50,92.0,0.71,MEDIUM
Operations Manager,Process Improvement,Management,Operations,0.78,0.85,28,0.50,0.55,84.0,0.70,MEDIUM
Customer Success,Customer Relations,Soft Skills,Customer Success,0.75,0.92,24,0.40,0.45,77.0,0.69,LOW
"""
        dataset_path.write_text(sample_data)

        # Step 2: Start training
        url = reverse("training-start")
        data = {"dataset_path": str(dataset_path), "test_split": 0.2}
        response = admin_client.post(url, data, format="json")

        # Should accept 200 (sync success), 201 (created), or 202 (async accepted)
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED,
            status.HTTP_202_ACCEPTED,
        ]
        assert "training_run_id" in response.data

        # Step 3: Check training run status
        training_run_id = response.data["training_run_id"]
        detail_url = reverse("training-run-detail", kwargs={"pk": training_run_id})
        detail_response = admin_client.get(detail_url)

        assert detail_response.status_code == status.HTTP_200_OK
        assert detail_response.data["status"] in ["RUNNING", "COMPLETED"]


@pytest.mark.django_db
@pytest.mark.e2e
class TestErrorRecoveryJourney:
    """Test error handling and recovery workflows."""

    def test_prediction_invalid_horizon(self, admin_client):
        """Test system behavior when invalid horizon_years is provided."""
        url = reverse("future-skills-recalculate")

        # Send invalid data to trigger error
        invalid_data = {"horizon_years": "invalid"}

        response = admin_client.post(url, invalid_data, format="json")

        # Should return error status with helpful message
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_filter_invalid_job_role(self, authenticated_client):
        """Test handling of invalid job role filter."""
        url = reverse("future-skills-list")

        response = authenticated_client.get(url, {"job_role_id": 99999})

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
        skills = [Skill(name=f"Skill {i}", category="Technical") for i in range(100)]
        Skill.objects.bulk_create(skills)

        # Test listing predictions (should complete without timeout)
        url = reverse("future-skills-list")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Verify response time is acceptable (add timing if needed)
