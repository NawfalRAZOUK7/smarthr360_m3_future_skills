# future_skills/tests/test_recommendations.py

from django.test import TestCase

from future_skills.models import FutureSkillPrediction, HRInvestmentRecommendation, JobRole, Skill
from future_skills.services.recommendation_engine import generate_recommendations_from_predictions


class RecommendationEngineTests(TestCase):
    def setUp(self):
        self.skill_python = Skill.objects.create(
            name="Python",
            category="Technique",
        )
        self.skill_gp = Skill.objects.create(
            name="Gestion de projet",
            category="Soft Skill",
        )

        self.job_de = JobRole.objects.create(
            name="Data Engineer",
            department="IT",
        )
        self.job_rh = JobRole.objects.create(
            name="Responsable RH",
            department="RH",
        )

        # HIGH prediction → doit générer une recommandation
        FutureSkillPrediction.objects.create(
            job_role=self.job_de,
            skill=self.skill_python,
            horizon_years=5,
            score=90.0,
            level=FutureSkillPrediction.LEVEL_HIGH,
            rationale="Test HIGH.",
        )

        # MEDIUM prediction → ne doit PAS générer
        FutureSkillPrediction.objects.create(
            job_role=self.job_rh,
            skill=self.skill_gp,
            horizon_years=5,
            score=60.0,
            level=FutureSkillPrediction.LEVEL_MEDIUM,
            rationale="Test MEDIUM.",
        )

    def test_generate_recommendations_only_for_high_predictions(self):
        self.assertEqual(HRInvestmentRecommendation.objects.count(), 0)

        total = generate_recommendations_from_predictions(horizon_years=5)

        # Une seule HIGH → une seule recommandation
        self.assertEqual(total, 1)
        self.assertEqual(HRInvestmentRecommendation.objects.count(), 1)

        rec = HRInvestmentRecommendation.objects.first()
        self.assertEqual(rec.skill, self.skill_python)
        self.assertEqual(rec.job_role, self.job_de)
        self.assertEqual(rec.horizon_years, 5)
        self.assertEqual(rec.priority_level, HRInvestmentRecommendation.PRIORITY_HIGH)
