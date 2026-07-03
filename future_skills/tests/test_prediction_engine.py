# future_skills/tests/test_prediction_engine.py

from django.test import TestCase

from future_skills.models import FutureSkillPrediction, JobRole, MarketTrend, PredictionRun, Skill
from future_skills.services.prediction_engine import calculate_level, recalculate_predictions


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
        """
        Test basique du recalcul des prédictions avec moteur de règles.
        Force FUTURE_SKILLS_USE_ML = False pour tester exclusivement les règles.
        """
        from django.test import override_settings

        # On part d'une base vide
        self.assertEqual(FutureSkillPrediction.objects.count(), 0)
        self.assertEqual(PredictionRun.objects.count(), 0)

        # Forcer l'utilisation du moteur de règles
        with override_settings(FUTURE_SKILLS_USE_ML=False):
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


class MLFallbackTests(TestCase):
    """Tests pour vérifier le comportement du système ML avec fallback sur le moteur de règles."""

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

    def test_fallback_to_rules_when_ml_unavailable(self):
        """
        Vérifie que le système bascule sur le moteur de règles quand le ML est indisponible.

        Test : FUTURE_SKILLS_USE_ML = True mais modèle ML non disponible.
        Résultat attendu :
        - Aucune exception levée
        - Prédictions créées avec succès
        - PredictionRun.parameters["engine"] == "rules_v1" (fallback)
        """
        from unittest.mock import patch

        from django.test import override_settings

        with override_settings(FUTURE_SKILLS_USE_ML=True):
            # Mock du modèle pour simuler qu'il n'est pas disponible
            with patch("future_skills.services.prediction_engine.FutureSkillsModel.instance") as mock_ml:
                mock_ml.return_value.is_available.return_value = False

                # Appel du recalcul
                total = recalculate_predictions(horizon_years=5)

                # Vérifications
                expected_count = JobRole.objects.count() * Skill.objects.count()
                self.assertEqual(total, expected_count)
                self.assertEqual(FutureSkillPrediction.objects.count(), expected_count)

                # Vérifier le PredictionRun créé
                last_run = PredictionRun.objects.order_by("-run_date").first()
                self.assertIsNotNone(last_run)
                self.assertEqual(last_run.total_predictions, expected_count)

                # ✅ Point clé : le moteur utilisé doit être "rules_v1" (fallback)
                self.assertEqual(last_run.parameters.get("engine"), "rules_v1")

                # ✅ Le champ model_version ne doit PAS être présent en mode fallback
                self.assertNotIn("model_version", last_run.parameters)

    def test_uses_ml_when_available(self):
        """
        Vérifie que le système utilise bien le ML quand il est disponible.

        Test : FUTURE_SKILLS_USE_ML = True et modèle ML disponible.
        Résultat attendu :
        - Prédictions créées avec succès
        - PredictionRun.parameters["engine"] == "ml_random_forest_v1"
        - PredictionRun.parameters["model_version"] est défini
        """
        from unittest.mock import MagicMock, patch

        from django.test import override_settings

        with override_settings(FUTURE_SKILLS_USE_ML=True, FUTURE_SKILLS_MODEL_VERSION="ml_random_forest_v1"):
            # Mock du modèle pour simuler qu'il est disponible et fonctionnel
            with patch("future_skills.services.prediction_engine.FutureSkillsModel.instance") as mock_ml:
                mock_instance = MagicMock()
                mock_instance.is_available.return_value = True
                mock_instance.predict_level.return_value = ("HIGH", 85.0)
                mock_ml.return_value = mock_instance

                # Appel du recalcul
                total = recalculate_predictions(horizon_years=5)

                # Vérifications
                expected_count = JobRole.objects.count() * Skill.objects.count()
                self.assertEqual(total, expected_count)

                # Vérifier le PredictionRun créé
                last_run = PredictionRun.objects.order_by("-run_date").first()
                self.assertIsNotNone(last_run)

                # ✅ Point clé : le moteur utilisé doit être "ml_random_forest_v1"
                self.assertEqual(last_run.parameters.get("engine"), "ml_random_forest_v1")

                # ✅ Le champ model_version doit être présent
                self.assertEqual(last_run.parameters.get("model_version"), "ml_random_forest_v1")

                # Vérifier que predict_level a bien été appelé
                self.assertTrue(mock_instance.predict_level.called)
