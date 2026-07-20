import tempfile
import time
from pathlib import Path
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APITransactionTestCase
from future_skills.models import DriftSnapshot, PredictionRun


class FutureSkillsIssue49Tests(APITransactionTestCase):
    def setUp(self):
        group, _ = Group.objects.get_or_create(name="DRH")
        self.user = get_user_model().objects.create_user(
            username="issue49-hr",
            email="issue49-hr@example.com",
            password="test",
        )
        self.user.groups.add(group)
        self.client.force_authenticate(self.user)

    @override_settings(FUTURE_SKILLS_ASYNC_PREDICTIONS=True, FUTURE_SKILLS_USE_ML=False)
    def test_bulk_import_returns_quickly_and_prediction_run_finishes(self):
        started = time.monotonic()
        response = self.client.post("/api/bulk-import/employees/", {"employees": [{"name": "Async Person", "email": "async@example.com", "department": "IT", "position": "Engineer", "current_skills": []}], "auto_predict": True, "horizon_years": 5}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertLess(time.monotonic() - started, 2.0)
        run_id = response.data["prediction_run_id"]
        deadline = time.monotonic() + 10
        run = PredictionRun.objects.get(pk=run_id)
        while run.status in {"QUEUED", "RUNNING"} and time.monotonic() < deadline:
            time.sleep(0.05)
            run.refresh_from_db()
        self.assertEqual(run.status, "DONE", run.error_message)
        self.assertEqual(self.client.get(f"/api/future-skills/prediction-runs/{run_id}/").data["status"], "DONE")

    def test_drift_endpoint_returns_latest_snapshot(self):
        run = PredictionRun.objects.create(total_predictions=1, status="DONE", parameters={"horizon_years": 5})
        DriftSnapshot.objects.create(prediction_run=run, mean_score=72, previous_mean_score=68, delta=4, status="STABLE", sample_size=1)
        response = self.client.get("/api/future-skills/drift/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "STABLE")
        self.assertEqual(response.data["last_run_id"], run.id)

    def test_dataset_upload_validation_and_replacement(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "future_skills_dataset.csv"
            with override_settings(FUTURE_SKILLS_DATASET_PATH=target):
                bad = SimpleUploadedFile("bad.csv", b"skill_name,future_need_level\nPython,HIGH\n", "text/csv")
                response = self.client.post("/api/training/dataset/", {"file": bad}, format="multipart")
                self.assertEqual(response.status_code, 400)
                self.assertIn("job_role_name", response.data["missing_columns"])
                header = "job_role_name,skill_name,skill_category,job_department,trend_score,internal_usage,training_requests,scarcity_index,hiring_difficulty,avg_salary_k,economic_indicator,future_need_level\n"
                row = "Engineer,Python,Technical,IT,0.9,0.5,4,0.7,0.8,70,0.2,HIGH\n"
                good = SimpleUploadedFile("training.csv", (header + row).encode(), "text/csv")
                response = self.client.post("/api/training/dataset/", {"file": good}, format="multipart")
                self.assertEqual(response.status_code, 201)
                self.assertEqual(response.data["rows"], 1)
                self.assertEqual(target.read_text(), header + row)
