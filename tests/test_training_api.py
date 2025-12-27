#!/usr/bin/env python
"""
Test script for Training API endpoints (Section 2.4)
"""

import os
import sys

import pytest

# Setup paths first
sys.path.insert(0, "/Users/nawfalrazouk/smarthr360_m3_future_skills")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")

# Setup Django
import django  # noqa: E402

django.setup()  # noqa: E402

pytestmark = pytest.mark.django_db

# Now import Django models
from django.conf import settings  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402
from django.contrib.auth.models import Group  # noqa: E402
from rest_framework.test import APIClient  # noqa: E402

from future_skills.models import TrainingRun  # noqa: E402

User = get_user_model()


def create_test_user():
    """Create a test user with HR staff permissions."""
    print("\n1️⃣  Creating test user...")

    # Get or create DRH group
    drh_group, _ = Group.objects.get_or_create(name="DRH")

    # Create or get user
    user, created = User.objects.get_or_create(
        username="test_hr_staff",
        defaults={
            "email": "hr@test.com",
            "is_staff": True,
            "is_active": True,
        },
    )

    if created:
        user.set_password("testpass123")
        user.save()
        user.groups.add(drh_group)
        print(f"   ✅ Created user: {user.username}")
    else:
        user.groups.add(drh_group)
        print(f"   ✅ Using existing user: {user.username}")

    return user


def test_training_run_list(client):
    """Test GET /api/training/runs/"""
    print("\n2️⃣  Testing TrainingRunListAPIView...")

    response = client.get("/api/training/runs/")

    print(f"   Status: {response.status_code}")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    data = response.json()
    print(f"   Total runs: {data['count']}")
    print(f"   Results in page: {len(data['results'])}")

    if data["results"]:
        first_run = data["results"][0]
        print(f"   First run: {first_run['model_version']} (status: {first_run['status']})")

    print("   ✅ List endpoint works!")


def test_training_run_detail(client):
    """Test GET /api/training/runs/<id>/"""
    print("\n3️⃣  Testing TrainingRunDetailAPIView...")

    # Get the first training run
    training_run = TrainingRun.objects.first()

    if not training_run:
        print("   ⚠️  No training runs in database, skipping detail test")
        return

    response = client.get(f"/api/training/runs/{training_run.id}/")

    print(f"   Status: {response.status_code}")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    data = response.json()
    print(f"   Run ID: {data['id']}")
    print(f"   Model Version: {data['model_version']}")
    print(f"   Status: {data['status']}")
    print(f"   Accuracy: {data['accuracy']:.2%}")
    print(f"   Hyperparameters: {data['hyperparameters']}")

    print("   ✅ Detail endpoint works!")


def test_train_model(client):
    """Test POST /api/training/train/"""
    print("\n4️⃣  Testing TrainModelAPIView...")

    # Prepare request data
    request_data = {
        "dataset_path": str(settings.ML_DATASETS_DIR / "future_skills_dataset.csv"),
        "test_split": 0.2,
        "hyperparameters": {
            "n_estimators": 30,  # Small for fast testing
            "max_depth": 10,
        },
        "model_version": "api_test_v1",
        "notes": "Test training via API",
    }

    print(f"   Request: {request_data}")

    response = client.post("/api/training/train/", data=request_data, format="json")

    print(f"   Status: {response.status_code}")

    if response.status_code == 201:
        data = response.json()
        print("   ✅ Training completed!")
        print(f"   Training Run ID: {data['training_run_id']}")
        print(f"   Status: {data['status']}")
        print(f"   Model Version: {data['model_version']}")
        print(f"   Message: {data['message']}")

        if "metrics" in data:
            metrics = data["metrics"]
            print(f"   Accuracy: {metrics['accuracy']:.2%}")
            print(f"   F1-Score: {metrics['f1_score']:.2%}")
            print(f"   Training Duration: {metrics['training_duration_seconds']:.3f}s")

        # Verify in database
        training_run = TrainingRun.objects.get(id=data["training_run_id"])
        assert training_run.status == "COMPLETED", f"Expected COMPLETED, got {training_run.status}"
        print("   ✅ TrainingRun record verified in database")

    else:
        print("   ❌ Training failed!")
        print(f"   Response: {response.json()}")
        raise AssertionError(f"Training endpoint failed with status {response.status_code}")


def test_train_model_with_invalid_data(client):
    """Test POST /api/training/train/ with invalid data"""
    print("\n5️⃣  Testing TrainModelAPIView with invalid data...")

    # Test with invalid hyperparameters
    request_data = {
        "hyperparameters": {
            "n_estimators": 5000,  # Too high
        }
    }

    response = client.post("/api/training/train/", data=request_data, format="json")

    print(f"   Status: {response.status_code}")
    assert response.status_code == 400, f"Expected 400, got {response.status_code}"

    data = response.json()
    print(f"   Error: {data}")
    print("   ✅ Validation works correctly!")


def test_filtering(client):
    """Test filtering in TrainingRunListAPIView"""
    print("\n6️⃣  Testing filtering in TrainingRunListAPIView...")

    # Filter by status
    response = client.get("/api/training/runs/?status=COMPLETED")
    print(f"   Status: {response.status_code}")
    assert response.status_code == 200

    data = response.json()
    print(f"   Completed runs: {data['count']}")

    # Verify all results have COMPLETED status
    if data["results"]:
        statuses = [r["status"] for r in data["results"]]
        assert all(s == "COMPLETED" for s in statuses), "Not all results have COMPLETED status"
        print("   ✅ Status filter works!")
    else:
        print("   ⚠️  No completed runs to verify filter")


def main():
    """Run all tests."""
    print("=" * 70)
    print("Testing Training API Endpoints (Section 2.4)")
    print("=" * 70)

    # Create test user
    user = create_test_user()

    # Create API client and authenticate
    client = APIClient()
    # Use both session login and DRF force_authenticate to ensure auth is applied
    client.login(username=user.email, password="testpass123")
    client.force_authenticate(user=user)

    try:
        # Run tests
        test_training_run_list(client)
        test_training_run_detail(client)
        test_filtering(client)
        test_train_model_with_invalid_data(client)
        test_train_model(client)

        print("\n" + "=" * 70)
        print("✅ ALL TESTS PASSED!")
        print("=" * 70)

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
