# Test Training API endpoints (Section 2.4)

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from future_skills.models import TrainingRun

User = get_user_model()


class TrainingAPITest(TestCase):
    """Test Training API endpoints."""

    def setUp(self):
        """Set up test user and client."""
        # Create test user (HR role)
        self.user = User.objects.create_user(
            username="test_hr",
            password="testpass123",
            email="hr@test.com",
            is_staff=True,
            role=User.Role.HR,
        )

        # Create API client
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_list_training_runs(self):
        """Test GET /api/training/runs/"""
        response = self.client.get("/api/training/runs/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("count", response.data)
        self.assertIn("results", response.data)
        print(f"✅ List endpoint: {response.status_code}, Count: {response.data['count']}")

    def test_filter_by_status(self):
        """Test filtering by status."""
        response = self.client.get("/api/training/runs/?status=COMPLETED")
        self.assertEqual(response.status_code, 200)
        print(f"✅ Filter endpoint: {response.status_code}")

    def test_training_run_detail(self):
        """Test GET /api/training/runs/<id>/"""
        # Get first training run
        training_run = TrainingRun.objects.first()

        if training_run:
            response = self.client.get(f"/api/training/runs/{training_run.id}/")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data["id"], training_run.id)
            print(f"✅ Detail endpoint: {response.status_code}, Model: {response.data['model_version']}")
        else:
            print("⚠️  No training runs to test detail endpoint")

    def test_validation(self):
        """Test request validation."""
        # Invalid n_estimators
        response = self.client.post(
            "/api/training/train/",
            {"hyperparameters": {"n_estimators": 5000}},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        print(f"✅ Validation works: {response.status_code}")

    def test_train_model_small(self):
        """Test training a small model."""
        request_data = {
            "dataset_path": str(settings.ML_DATASETS_DIR / "future_skills_dataset.csv"),
            "test_split": 0.2,
            "hyperparameters": {
                "n_estimators": 20,
                "max_depth": 5,
            },
            "model_version": "test_api_v1",
            "notes": "API test run",
        }

        response = self.client.post("/api/training/train/", request_data, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertIn("training_run_id", response.data)
        self.assertEqual(response.data["status"], "COMPLETED")

        # Verify in database
        training_run = TrainingRun.objects.get(id=response.data["training_run_id"])
        self.assertEqual(training_run.status, "COMPLETED")
        self.assertEqual(training_run.model_version, "test_api_v1")
        self.assertGreater(training_run.accuracy, 0)

        print(f"✅ Training endpoint: {response.status_code}")
        print(f"   Run ID: {response.data['training_run_id']}")
        print(f"   Accuracy: {response.data['metrics']['accuracy']:.2%}")
