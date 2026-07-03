"""Stable demand-by-skill API (cross-service contract for career-sim)."""

from django.contrib.auth import get_user_model
from django.core.management import call_command
from rest_framework.test import APITestCase

from future_skills.models import FutureSkillPrediction, JobRole, Skill


class DemandAPITests(APITestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(
            email="hr@corp.com", username="hr", password="x", role="HR"
        )
        self.client.force_authenticate(user)

        self.python = Skill.objects.create(name="Python")
        self.k8s = Skill.objects.create(name="Kubernetes")
        dev = JobRole.objects.create(name="Developer")
        ops = JobRole.objects.create(name="SRE")

        FutureSkillPrediction.objects.create(
            job_role=dev, skill=self.python, horizon_years=3,
            score=70, level="MEDIUM",
        )
        FutureSkillPrediction.objects.create(
            job_role=ops, skill=self.python, horizon_years=3,
            score=92, level="HIGH",
        )
        FutureSkillPrediction.objects.create(
            job_role=ops, skill=self.k8s, horizon_years=5,
            score=88, level="HIGH",
        )

    def test_aggregates_strongest_prediction_per_skill(self):
        resp = self.client.get("/api/future-skills/demand/")
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertEqual(body["count"], 2)
        top = body["results"][0]
        self.assertEqual(top["skill_name"], "Python")
        self.assertEqual(top["score"], 92.0)          # max across roles
        self.assertEqual(top["demand_level"], "HIGH")
        self.assertEqual(top["job_roles_count"], 2)

    def test_horizon_filter_and_platform_codes(self):
        call_command("map_platform_codes", "--defaults")
        resp = self.client.get("/api/future-skills/demand/?horizon_years=5")
        body = resp.json()
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["results"][0]["skill_code"], "K8S")

    def test_bad_horizon_400_and_anonymous_401(self):
        self.assertEqual(
            self.client.get(
                "/api/future-skills/demand/?horizon_years=soon"
            ).status_code,
            400,
        )
        self.client.force_authenticate(None)
        # 401 with token auth in prod, 403 with the test-settings
        # session authenticator — rejected either way
        self.assertIn(
            self.client.get("/api/future-skills/demand/").status_code,
            (401, 403),
        )
