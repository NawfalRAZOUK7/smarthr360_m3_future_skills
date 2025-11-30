# future_skills/tests/test_api.py

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from future_skills.models import JobRole, MarketTrend, PredictionRun, Skill
from future_skills.services.prediction_engine import recalculate_predictions
from future_skills.services.recommendation_engine import (
    generate_recommendations_from_predictions,
)

User = get_user_model()


class BaseAPITestCase(APITestCase):
    def setUp(self):
        # Create groups for roles
        self.group_drh = Group.objects.create(name="DRH")
        self.group_resp_rh = Group.objects.create(name="RESPONSABLE_RH")
        self.group_manager = Group.objects.create(name="MANAGER")

        # Create test users
        self.user_no_role = User.objects.create_user(
            username="user_no_role", password="pass1234"
        )

        self.user_manager = User.objects.create_user(
            username="manager_user", password="pass1234"
        )
        self.user_manager.groups.add(self.group_manager)

        self.user_drh = User.objects.create_user(
            username="drh_user", password="pass1234"
        )
        self.user_drh.groups.add(self.group_drh)

        # Create test data for predictions
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

        # Pré-calculer quelques prédictions pour les tests GET
        recalculate_predictions(horizon_years=5)

        # Pré-générer des recommandations pour les tests
        generate_recommendations_from_predictions(horizon_years=5)


class FutureSkillsListAPITests(BaseAPITestCase):
    def test_get_future_skills_without_auth_should_be_forbidden(self):
        url = reverse("future-skills-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_future_skills_with_manager_role_should_succeed(self):
        url = reverse("future-skills-list")
        # Authentifier en tant que MANAGER
        self.client.force_authenticate(user=self.user_manager)

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        # Handle paginated response
        results = data.get("results", data) if isinstance(data, dict) else data
        # On doit avoir au moins une prédiction
        self.assertTrue(len(results) > 0)
        # Verif champs principaux
        first = results[0]
        self.assertIn("job_role", first)
        self.assertIn("skill", first)
        self.assertIn("horizon_years", first)
        self.assertIn("score", first)
        self.assertIn("level", first)


class RecalculateFutureSkillsAPITests(BaseAPITestCase):
    def test_recalculate_future_skills_with_no_role_should_be_forbidden(self):
        url = reverse("future-skills-recalculate")
        self.client.force_authenticate(user=self.user_no_role)

        response = self.client.post(url, {"horizon_years": 5}, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_recalculate_future_skills_with_drh_role_should_succeed(self):
        """
        Test du endpoint recalculate avec utilisateur DRH.
        Force FUTURE_SKILLS_USE_ML = False pour tester exclusivement les règles.
        """
        from django.test import override_settings

        url = reverse("future-skills-recalculate")
        self.client.force_authenticate(user=self.user_drh)

        # Forcer l'utilisation du moteur de règles
        with override_settings(FUTURE_SKILLS_USE_ML=False):
            response = self.client.post(url, {"horizon_years": 5}, format="json")

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.json()

            self.assertIn("total_predictions", data)
            self.assertIn("horizon_years", data)

            # Vérifie que total_predictions correspond bien au nombre d'objets en base
            expected = JobRole.objects.count() * Skill.objects.count()
            self.assertEqual(data["total_predictions"], expected)

            # Vérifier le dernier PredictionRun
            last_run = PredictionRun.objects.order_by("-run_date").first()
            self.assertIsNotNone(last_run)
            self.assertEqual(last_run.run_by, self.user_drh)
            self.assertIsInstance(last_run.parameters, dict)
            self.assertEqual(last_run.parameters.get("trigger"), "api")
            self.assertEqual(last_run.parameters.get("horizon_years"), 5)
            self.assertEqual(last_run.parameters.get("engine"), "rules_v1")


class RecalculateFutureSkillsMLFallbackTests(BaseAPITestCase):
    """Tests pour vérifier le fallback ML dans l'API."""

    def test_recalculate_with_ml_unavailable_fallback_to_rules(self):
        """
        Test du endpoint POST /api/future-skills/recalculate/ avec ML indisponible.

        Test : FUTURE_SKILLS_USE_ML = True mais modèle ML non disponible.
        Résultat attendu :
        - Réponse 200 OK
        - total_predictions > 0
        - PredictionRun.parameters["engine"] == "rules_v1" (fallback)
        - PredictionRun.parameters["trigger"] == "api"
        - PredictionRun.run_by == utilisateur DRH
        """
        from unittest.mock import patch

        from django.test import override_settings

        url = reverse("future-skills-recalculate")
        self.client.force_authenticate(user=self.user_drh)

        with override_settings(FUTURE_SKILLS_USE_ML=True):
            # Mock du modèle pour simuler qu'il n'est pas disponible
            with patch(
                "future_skills.services.prediction_engine.FutureSkillsModel.instance"
            ) as mock_ml:
                mock_ml.return_value.is_available.return_value = False

                # Appel de l'API
                response = self.client.post(url, {"horizon_years": 5}, format="json")

                # Vérifications de la réponse HTTP
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                data = response.json()

                self.assertIn("total_predictions", data)
                self.assertIn("horizon_years", data)

                expected = JobRole.objects.count() * Skill.objects.count()
                self.assertEqual(data["total_predictions"], expected)
                self.assertEqual(data["horizon_years"], 5)

                # Vérifier le dernier PredictionRun créé
                last_run = PredictionRun.objects.order_by("-run_date").first()
                self.assertIsNotNone(last_run)

                # ✅ Vérifier que le bon utilisateur est tracé
                self.assertEqual(last_run.run_by, self.user_drh)

                # ✅ Vérifier que les paramètres reflètent le fallback
                self.assertIsInstance(last_run.parameters, dict)
                self.assertEqual(last_run.parameters.get("trigger"), "api")
                self.assertEqual(last_run.parameters.get("horizon_years"), 5)
                self.assertEqual(last_run.parameters.get("engine"), "rules_v1")

                # ✅ Le champ model_version ne doit PAS être présent en mode fallback
                self.assertNotIn("model_version", last_run.parameters)


class MarketTrendsAPITests(BaseAPITestCase):
    def test_get_market_trends_with_manager_role_should_succeed(self):
        url = reverse("market-trends-list")
        self.client.force_authenticate(user=self.user_manager)

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertTrue(len(data) >= 2)  # on a créé 2 MarketTrend en setUp


class HRInvestmentRecommendationsAPITests(BaseAPITestCase):
    def test_get_hr_investment_recommendations_without_auth_should_be_forbidden(self):
        from django.urls import reverse

        url = reverse("hr-investment-recommendations-list")

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_hr_investment_recommendations_with_manager_role_should_succeed(self):
        from django.urls import reverse

        url = reverse("hr-investment-recommendations-list")

        self.client.force_authenticate(user=self.user_manager)

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        # On s'attend à au moins une recommandation, vu qu'on en génère en setUp
        self.assertTrue(len(data) > 0)
        first = data[0]
        self.assertIn("skill", first)
        self.assertIn("horizon_years", first)
        self.assertIn("priority_level", first)
        self.assertIn("recommended_action", first)
