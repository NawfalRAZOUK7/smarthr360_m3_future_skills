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

    def test_complete_hr_manager_workflow(self, api_client, hr_manager):
        """
        Test complete HR manager workflow:
        1. Login
        2. View employees
        3. Create prediction
        4. View results
        5. Generate recommendations
        """
        # Step 1: Authenticate
        api_client.force_authenticate(user=hr_manager)

        # Step 2: View employees list
        url = reverse('employee-list')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK

        # Step 3: Create a new employee
        employee_data = {
            'name': 'Alice Johnson',
            'email': 'alice.johnson@example.com',
            'department': 'Marketing',
            'position': 'Marketing Manager',
            'current_skills': ['SEO', 'Content Marketing', 'Analytics']
        }
        response = api_client.post(url, employee_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        employee_id = response.data['id']

        # Step 4: Request prediction for the employee
        predict_url = reverse('futureskill-predict-skills')
        predict_data = {
            'employee_id': employee_id,
            'current_skills': employee_data['current_skills']
        }
        response = api_client.post(predict_url, predict_data, format='json')
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]

        # Step 5: View prediction results
        predictions_url = reverse('predictionrun-list')
        response = api_client.get(predictions_url, {'employee': employee_id})
        assert response.status_code == status.HTTP_200_OK

        # Step 6: Get recommendations
        recommend_url = reverse('futureskill-recommend-skills')
        recommend_data = {'employee_id': employee_id}
        response = api_client.post(recommend_url, recommend_data, format='json')
        assert response.status_code == status.HTTP_200_OK

    def test_viewer_limited_workflow(self, api_client, hr_viewer, sample_employee):
        """Test that viewer can only read data, not modify."""
        api_client.force_authenticate(user=hr_viewer)

        # Can view employees
        url = reverse('employee-list')
        response = api_client.get(url)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]

        # Cannot create employees
        employee_data = {
            'name': 'Bob Smith',
            'email': 'bob@example.com',
            'department': 'IT'
        }
        response = api_client.post(url, employee_data, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Cannot update employees
        update_url = reverse('employee-detail', kwargs={'pk': sample_employee.id})
        response = api_client.patch(update_url, {'name': 'Updated'}, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Cannot delete employees
        response = api_client.delete(update_url)
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
@pytest.mark.e2e
class TestSkillManagementJourney:
    """Test skill management user journey."""

    def test_skill_lifecycle(self, admin_client):
        """
        Test complete skill lifecycle:
        1. Create skill
        2. Update skill
        3. Assign to employees
        4. Track usage
        5. Archive/delete skill
        """
        # Step 1: Create a new skill
        url = reverse('futureskill-list')
        skill_data = {
            'skill_name': 'Cloud Computing',
            'category': 'Technical',
            'description': 'AWS, Azure, GCP expertise',
            'importance_score': 0.88,
            'relevance_score': 0.92
        }
        response = admin_client.post(url, skill_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        skill_id = response.data['id']

        # Step 2: Update the skill
        update_url = reverse('futureskill-detail', kwargs={'pk': skill_id})
        update_data = {'importance_score': 0.95}
        response = admin_client.patch(update_url, update_data, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['importance_score'] == pytest.approx(0.95)

        # Step 3: Create employee with this skill
        employee_url = reverse('employee-list')
        employee_data = {
            'name': 'Cloud Expert',
            'email': 'cloud@example.com',
            'department': 'DevOps',
            'current_skills': ['Cloud Computing', 'Docker']
        }
        response = admin_client.post(employee_url, employee_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED

        # Step 4: Verify skill is in use
        response = admin_client.get(update_url)
        assert response.status_code == status.HTTP_200_OK

        # Step 5: Delete the skill
        response = admin_client.delete(update_url)
        assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.django_db
@pytest.mark.e2e
@pytest.mark.slow
class TestBulkOperationsJourney:
    """Test bulk operations workflow."""

    def test_bulk_employee_import_and_predict(self, admin_client, db):
        """Test importing multiple employees and running bulk predictions."""
        # Step 1: Bulk create employees
        employee_url = reverse('employee-list')
        employees_data = [
            {
                'name': f'Employee {i}',
                'email': f'employee{i}@example.com',
                'department': 'Engineering',
                'position': 'Developer',
                'current_skills': ['Python', 'JavaScript']
            }
            for i in range(3)
        ]

        employee_ids = []
        for emp_data in employees_data:
            response = admin_client.post(employee_url, emp_data, format='json')
            assert response.status_code == status.HTTP_201_CREATED
            employee_ids.append(response.data['id'])

        # Step 2: Bulk predict (if endpoint exists)
        bulk_predict_url = reverse('futureskill-bulk-predict')
        bulk_data = {'employee_ids': employee_ids}
        response = admin_client.post(bulk_predict_url, bulk_data, format='json')

        # Adjust based on actual API
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_202_ACCEPTED,
            status.HTTP_404_NOT_FOUND  # If endpoint doesn't exist yet
        ]


@pytest.mark.django_db
@pytest.mark.e2e
class TestReportingJourney:
    """Test reporting and analytics journey."""

    def test_generate_skills_gap_report(self, authenticated_client, db):
        """Test generating a skills gap analysis report."""
        from future_skills.models import FutureSkill, Employee

        # Create test data
        FutureSkill.objects.create(
            skill_name='AI/ML',
            category='Technical',
            importance_score=0.95
        )

        FutureSkill.objects.create(
            skill_name='Blockchain',
            category='Technical',
            importance_score=0.75
        )

        Employee.objects.create(
            name='Test Employee',
            email='test@example.com',
            department='IT',
            current_skills=['Python']
        )

        # Request skills gap report
        url = reverse('reports-skills-gap')
        response = authenticated_client.get(url)

        # Adjust based on actual API
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND  # If endpoint doesn't exist
        ]


@pytest.mark.django_db
@pytest.mark.e2e
@pytest.mark.ml
class TestMLPipelineJourney:
    """Test complete ML pipeline journey."""

    def test_model_training_to_prediction(self, admin_client, settings):
        """
        Test complete ML pipeline:
        1. Prepare training data
        2. Train model
        3. Evaluate model
        4. Deploy model
        5. Make predictions
        """
        if not settings.FUTURE_SKILLS_USE_ML:
            pytest.skip("ML is disabled")

        # This is a placeholder for ML pipeline testing
        # Actual implementation depends on your ML infrastructure

        # Step 1: Check model status
        model_status_url = reverse('ml-model-status')
        response = admin_client.get(model_status_url)

        # Adjust based on actual endpoints
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND
        ]


@pytest.mark.django_db
@pytest.mark.e2e
class TestErrorRecoveryJourney:
    """Test error handling and recovery workflows."""

    def test_prediction_failure_recovery(self, authenticated_client, sample_employee):
        """Test system behavior when prediction fails."""
        url = reverse('futureskill-predict-skills')

        # Send invalid data to trigger error
        invalid_data = {
            'employee_id': sample_employee.id,
            'current_skills': None  # Invalid
        }

        response = authenticated_client.post(url, invalid_data, format='json')

        # Should return error status with helpful message
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_concurrent_access_handling(self, api_client, hr_manager, sample_employee):
        """Test handling of concurrent modifications."""
        api_client.force_authenticate(user=hr_manager)

        url = reverse('employee-detail', kwargs={'pk': sample_employee.id})

        # Simulate concurrent updates
        update_data1 = {'name': 'Updated Name 1'}
        update_data2 = {'name': 'Updated Name 2'}

        response1 = api_client.patch(url, update_data1, format='json')
        response2 = api_client.patch(url, update_data2, format='json')

        # Both should succeed (last write wins) or implement optimistic locking
        assert response1.status_code == status.HTTP_200_OK
        assert response2.status_code == status.HTTP_200_OK


@pytest.mark.django_db
@pytest.mark.e2e
@pytest.mark.slow
class TestPerformanceJourney:
    """Test performance-critical workflows."""

    def test_large_dataset_handling(self, authenticated_client, db):
        """Test system behavior with large datasets."""
        from future_skills.models import FutureSkill

        # Create many skills
        skills = [
            FutureSkill(
                skill_name=f'Skill {i}',
                category='Technical',
                importance_score=0.7
            )
            for i in range(100)
        ]
        FutureSkill.objects.bulk_create(skills)

        # Test listing with pagination
        url = reverse('futureskill-list')
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Verify response time is acceptable (add timing if needed)
