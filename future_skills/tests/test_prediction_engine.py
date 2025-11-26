# future_skills/tests/test_prediction_engine.py

from django.test import TestCase

from future_skills.models import (
    Skill,
    JobRole,
    MarketTrend,
    FutureSkillPrediction,
    PredictionRun,
)
from future_skills.services.prediction_engine import (
    calculate_level,
    recalculate_predictions,
)


class CalculateLevelTests(TestCase):
    def test_calculate_level_high_when_scores_are_high(self):
        level, score = calculate_level(
            trend_score=0.9,
            internal_usage=0.8,
            training_requests=8,
        )
        self.assertEqual(level, FutureSkillPrediction.LEVEL_HIGH)
        self.assertGreaterEqual(score, 70.0)

    def test_calculate_level_medium_when_scores_are_medium(self):
        level, score = calculate_level(
            trend_score=0.6,
            internal_usage=0.5,
            training_requests=4,
        )
        self.assertEqual(level, FutureSkillPrediction.LEVEL_MEDIUM)
        self.assertGreaterEqual(score, 40.0)
        self.assertLess(score, 70.0)

    def test_calculate_level_low_when_scores_are_low(self):
        level, score = calculate_level(
            trend_score=0.2,
            internal_usage=0.1,
            training_requests=0,
        )
        self.assertEqual(level, FutureSkillPrediction.LEVEL_LOW)
        self.assertLess(score, 40.0)


class RecalculatePredictionsTests(TestCase):
    def setUp(self):
        # Créer quelques Skills
        self.skill_python = Skill.objects.create(
            name="Python",
            category="Technique",
        )
        self.skill_gp = Skill.objects.create(
            name="Gestion de projet",
            category="Soft Skill",
        )

        # Créer quelques JobRoles
        self.job_de = JobRole.objects.create(
            name="Data Engineer",
            department="IT",
        )
        self.job_rh = JobRole.objects.create(
            name="Responsable RH",
            department="RH",
        )

        # Créer des tendances marché
        MarketTrend.objects.create(
            title="Explosion des besoins en IA & Data",
            source_name="Test Source",
            year=2025,
            sector="Tech",
            trend_score=0.9,
        )
        MarketTrend.objects.create(
            title="Digitalisation de la fonction RH",
            source_name="Test Source",
            year=2025,
            sector="RH",
            trend_score=0.8,
        )

    def test_recalculate_predictions_creates_predictions_and_run(self):
        # On part d'une base vide
        self.assertEqual(FutureSkillPrediction.objects.count(), 0)
        self.assertEqual(PredictionRun.objects.count(), 0)

        total = recalculate_predictions(horizon_years=5)

        # Nombre de couples (job_role, skill)
        expected_count = JobRole.objects.count() * Skill.objects.count()
        self.assertEqual(total, expected_count)

        # Vérifier que les prédictions ont été créées
        self.assertEqual(FutureSkillPrediction.objects.count(), expected_count)

        # Vérifier qu'un PredictionRun a été créé et qu'il stocke le bon total
        self.assertEqual(PredictionRun.objects.count(), 1)
        run = PredictionRun.objects.first()
        self.assertEqual(run.total_predictions, expected_count)

        # Nouveau : vérifier les paramètres par défaut
        self.assertIsNone(run.run_by)
        self.assertIn("horizon_years", run.parameters)
        self.assertEqual(run.parameters["horizon_years"], 5)
        self.assertEqual(run.parameters.get("engine"), "rules_v1")

