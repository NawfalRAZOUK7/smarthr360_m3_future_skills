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


class DemandContractExtrasTests(APITestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(
            email="hr2@corp.com", username="hr2", password="x", role="HR"
        )
        self.client.force_authenticate(user)
        self.skill = Skill.objects.create(name="Python", platform_code="PY")
        self.dev = JobRole.objects.create(name="Developer")

    def test_confidence_version_and_explanation_in_contract(self):
        FutureSkillPrediction.objects.create(
            job_role=self.dev, skill=self.skill, horizon_years=3,
            score=91, level="HIGH", model_version="v2.3.0",
            rationale="Strong market growth across sectors.",
            probabilities={"p_low": 0.05, "p_medium": 0.15, "p_high": 0.80},
            explanation={"text": "SHAP: trend_score dominates.",
                         "confidence": 0.87},
        )
        row = self.client.get("/api/future-skills/demand/").json()["results"][0]
        self.assertEqual(row["confidence"], 0.87)
        self.assertEqual(row["model_version"], "v2.3.0")
        self.assertIn("SHAP", row["explanation"])

    def test_confidence_falls_back_to_class_probability(self):
        FutureSkillPrediction.objects.create(
            job_role=self.dev, skill=self.skill, horizon_years=3,
            score=88, level="HIGH",
            probabilities={"p_low": 0.1, "p_medium": 0.2, "p_high": 0.7},
        )
        row = self.client.get("/api/future-skills/demand/").json()["results"][0]
        self.assertEqual(row["confidence"], 0.7)

    def test_job_role_filter(self):
        ops = JobRole.objects.create(name="SRE")
        FutureSkillPrediction.objects.create(
            job_role=self.dev, skill=self.skill, horizon_years=3,
            score=60, level="MEDIUM",
        )
        FutureSkillPrediction.objects.create(
            job_role=ops, skill=self.skill, horizon_years=3,
            score=95, level="HIGH",
        )
        body = self.client.get(
            "/api/future-skills/demand/?job_role=developer"
        ).json()
        self.assertEqual(body["results"][0]["score"], 60.0)

    def test_department_filter(self):
        eng = JobRole.objects.create(name="Backend Engineer", department="ENG")
        sales = JobRole.objects.create(name="Account Exec", department="SALES")
        FutureSkillPrediction.objects.create(
            job_role=eng, skill=self.skill, horizon_years=3,
            score=88, level="HIGH",
        )
        FutureSkillPrediction.objects.create(
            job_role=sales, skill=self.skill, horizon_years=3,
            score=42, level="MEDIUM",
        )
        # case-insensitive; only the ENG prediction is aggregated
        body = self.client.get(
            "/api/future-skills/demand/?department=eng"
        ).json()
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["results"][0]["score"], 88.0)
        # an unknown department yields an empty (but valid) contract
        empty = self.client.get(
            "/api/future-skills/demand/?department=NOPE"
        ).json()
        self.assertEqual(empty["count"], 0)
        self.assertEqual(empty["results"], [])

    def test_history_series_and_trend(self):
        from future_skills.models import FutureSkillSnapshot

        for date, trend in (("2026-01-01", 0.40), ("2026-04-01", 0.55),
                            ("2026-07-01", 0.70)):
            FutureSkillSnapshot.objects.create(
                job_role=self.dev, skill=self.skill, as_of_date=date,
                trend_score=trend, internal_usage=0.3,
                training_requests=5, scarcity_index=0.6,
                hiring_difficulty=0.5, avg_salary_k=60,
                economic_indicator=0.5,
            )
        body = self.client.get(
            "/api/future-skills/demand/history/?skill_code=PY"
        ).json()
        self.assertEqual(body["points"], 3)
        self.assertEqual(body["trend"], "rising")
        self.assertEqual(body["series"][0]["trend_score"], 0.4)

        self.assertEqual(
            self.client.get(
                "/api/future-skills/demand/history/"
            ).status_code,
            400,
        )
        self.assertEqual(
            self.client.get(
                "/api/future-skills/demand/history/?skill_code=NOPE"
            ).status_code,
            404,
        )
