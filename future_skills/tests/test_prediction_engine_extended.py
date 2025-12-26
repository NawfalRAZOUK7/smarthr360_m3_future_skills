"""Extended tests for prediction_engine module to improve coverage.

This test module focuses on:
- PredictionEngine.predict() method with both ML and rules paths
- PredictionEngine.batch_predict() functionality
- Helper functions (_normalize_training_requests, _find_relevant_trend, etc.)
- _log_prediction_for_monitoring() functionality
- Edge cases, error handling, and boundary conditions
- Explanation engine integration
- Settings variations

Target: Improve coverage from current level to 90%+
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from future_skills.models import FutureSkillPrediction, JobRole, MarketTrend, PredictionRun, Skill
from future_skills.services.prediction_engine import (
    PredictionEngine,
    _estimate_internal_usage,
    _estimate_scarcity_index,
    _estimate_training_requests,
    _find_relevant_trend,
    _log_prediction_for_monitoring,
    _normalize_training_requests,
    calculate_level,
    recalculate_predictions,
)

User = get_user_model()


# ============================================================================
# Test Helper Functions
# ============================================================================


class TestNormalizeTrainingRequests(TestCase):
    """Test _normalize_training_requests helper function."""

    def test_normalize_at_zero(self):
        """Test normalization with zero requests."""
        result = _normalize_training_requests(0.0, max_requests=100.0)
        self.assertEqual(result, 0.0)

    def test_normalize_at_max(self):
        """Test normalization at max requests."""
        result = _normalize_training_requests(100.0, max_requests=100.0)
        self.assertEqual(result, 1.0)

    def test_normalize_at_half(self):
        """Test normalization at half of max."""
        result = _normalize_training_requests(50.0, max_requests=100.0)
        self.assertEqual(result, 0.5)

    def test_normalize_exceeds_max(self):
        """Test that values exceeding max are clamped to 1.0."""
        result = _normalize_training_requests(150.0, max_requests=100.0)
        self.assertEqual(result, 1.0)

    def test_normalize_negative_value(self):
        """Test that negative values are clamped to 0.0."""
        result = _normalize_training_requests(-10.0, max_requests=100.0)
        self.assertEqual(result, 0.0)

    def test_normalize_with_zero_max(self):
        """Test normalization when max_requests is zero."""
        result = _normalize_training_requests(50.0, max_requests=0.0)
        self.assertEqual(result, 0.0)

    def test_normalize_with_negative_max(self):
        """Test normalization when max_requests is negative."""
        result = _normalize_training_requests(50.0, max_requests=-10.0)
        self.assertEqual(result, 0.0)

    def test_normalize_with_custom_max(self):
        """Test normalization with custom max value."""
        result = _normalize_training_requests(25.0, max_requests=50.0)
        self.assertEqual(result, 0.5)


class TestFindRelevantTrend(TestCase):
    """Test _find_relevant_trend helper function."""

    def setUp(self):
        self.job_role = JobRole.objects.create(name="Data Scientist", department="IT")
        self.skill = Skill.objects.create(name="Machine Learning", category="Technique")

    def test_find_trend_with_tech_sector(self):
        """Test finding trend in Tech sector."""
        trend = MarketTrend.objects.create(
            title="AI Boom",
            source_name="Test Source",
            year=2025,
            sector="Tech",
            trend_score=0.85,
        )

        result = _find_relevant_trend(self.job_role, self.skill)
        self.assertAlmostEqual(result, 0.85, places=2)

    def test_find_trend_no_tech_sector(self):
        """Test finding trend when no Tech sector exists."""
        trend = MarketTrend.objects.create(
            title="HR Trends",
            source_name="Test Source",
            year=2025,
            sector="HR",
            trend_score=0.60,
        )

        result = _find_relevant_trend(self.job_role, self.skill)
        self.assertAlmostEqual(result, 0.60, places=2)

    def test_find_trend_no_trends_exist(self):
        """Test default value when no trends exist."""
        result = _find_relevant_trend(self.job_role, self.skill)
        self.assertEqual(result, 0.5)

    def test_find_trend_multiple_tech_trends(self):
        """Test that most recent Tech trend is selected."""
        MarketTrend.objects.create(
            title="Old AI Trend",
            source_name="Test Source",
            year=2023,
            sector="Tech",
            trend_score=0.70,
        )
        MarketTrend.objects.create(
            title="New AI Trend",
            source_name="Test Source",
            year=2025,
            sector="Tech",
            trend_score=0.90,
        )

        result = _find_relevant_trend(self.job_role, self.skill)
        self.assertAlmostEqual(result, 0.90, places=2)

    def test_find_trend_value_clamped_to_one(self):
        """Test that trend score > 1.0 is clamped."""
        MarketTrend.objects.create(
            title="Overhyped Trend",
            source_name="Test Source",
            year=2025,
            sector="Tech",
            trend_score=1.5,
        )

        result = _find_relevant_trend(self.job_role, self.skill)
        self.assertEqual(result, 1.0)

    def test_find_trend_negative_value_clamped(self):
        """Test that negative trend score is clamped to 0."""
        MarketTrend.objects.create(
            title="Declining Trend",
            source_name="Test Source",
            year=2025,
            sector="Tech",
            trend_score=-0.2,
        )

        result = _find_relevant_trend(self.job_role, self.skill)
        self.assertEqual(result, 0.0)


class TestEstimateInternalUsage(TestCase):
    """Test _estimate_internal_usage helper function."""

    def test_manager_role_gets_higher_usage(self):
        """Test that manager roles get higher usage score."""
        manager = JobRole.objects.create(name="Project Manager", department="IT")
        skill = Skill.objects.create(name="Communication", category="Soft Skill")

        result = _estimate_internal_usage(manager, skill)
        self.assertEqual(result, 0.6)

    def test_non_manager_role_gets_lower_usage(self):
        """Test that non-manager roles get lower usage score."""
        engineer = JobRole.objects.create(name="Software Engineer", department="IT")
        skill = Skill.objects.create(name="Python", category="Technique")

        result = _estimate_internal_usage(engineer, skill)
        self.assertEqual(result, 0.4)

    def test_manager_case_insensitive(self):
        """Test that 'Manager' (capitalized) is detected."""
        manager = JobRole.objects.create(name="Senior MANAGER", department="IT")
        skill = Skill.objects.create(name="Leadership", category="Soft Skill")

        result = _estimate_internal_usage(manager, skill)
        self.assertEqual(result, 0.6)


class TestEstimateTrainingRequests(TestCase):
    """Test _estimate_training_requests helper function."""

    def test_data_skill_gets_high_requests(self):
        """Test that data-related skills get higher training requests."""
        job_role = JobRole.objects.create(name="Analyst", department="IT")
        skill = Skill.objects.create(name="Data Science", category="Technique")

        result = _estimate_training_requests(job_role, skill)
        self.assertEqual(result, 40.0)

    def test_ia_skill_gets_high_requests(self):
        """Test that IA/AI skills get higher training requests."""
        job_role = JobRole.objects.create(name="Engineer", department="IT")
        skill = Skill.objects.create(name="Intelligence Artificielle", category="Technique")

        result = _estimate_training_requests(job_role, skill)
        self.assertEqual(result, 40.0)

    def test_regular_skill_gets_low_requests(self):
        """Test that regular skills get lower training requests."""
        job_role = JobRole.objects.create(name="Manager", department="HR")
        skill = Skill.objects.create(name="Excel", category="Technique")

        result = _estimate_training_requests(job_role, skill)
        self.assertEqual(result, 10.0)

    def test_case_insensitive_data_detection(self):
        """Test case-insensitive detection of 'data' in skill name."""
        job_role = JobRole.objects.create(name="Analyst", department="IT")
        skill = Skill.objects.create(name="BIG DATA Analysis", category="Technique")

        result = _estimate_training_requests(job_role, skill)
        self.assertEqual(result, 40.0)


class TestEstimateScarcityIndex(TestCase):
    """Test _estimate_scarcity_index helper function."""

    def test_low_usage_means_high_scarcity(self):
        """Test that low internal usage results in high scarcity."""
        job_role = JobRole.objects.create(name="Developer", department="IT")
        skill = Skill.objects.create(name="Rust", category="Technique")

        internal_usage = 0.2
        result = _estimate_scarcity_index(job_role, skill, internal_usage)
        self.assertEqual(result, 0.8)

    def test_high_usage_means_low_scarcity(self):
        """Test that high internal usage results in low scarcity."""
        job_role = JobRole.objects.create(name="Manager", department="IT")
        skill = Skill.objects.create(name="Excel", category="Technique")

        internal_usage = 0.9
        result = _estimate_scarcity_index(job_role, skill, internal_usage)
        self.assertEqual(result, 0.1)

    def test_zero_usage_gives_max_scarcity(self):
        """Test that zero usage gives maximum scarcity."""
        job_role = JobRole.objects.create(name="Developer", department="IT")
        skill = Skill.objects.create(name="COBOL", category="Technique")

        result = _estimate_scarcity_index(job_role, skill, 0.0)
        self.assertEqual(result, 1.0)

    def test_full_usage_gives_zero_scarcity(self):
        """Test that full usage gives zero scarcity."""
        job_role = JobRole.objects.create(name="Developer", department="IT")
        skill = Skill.objects.create(name="JavaScript", category="Technique")

        result = _estimate_scarcity_index(job_role, skill, 1.0)
        self.assertEqual(result, 0.0)


# ============================================================================
# Test PredictionEngine Class
# ============================================================================


class TestPredictionEnginePredict(TestCase):
    """Test PredictionEngine.predict() method."""

    def setUp(self):
        self.job_role = JobRole.objects.create(name="Data Scientist", department="IT")
        self.skill = Skill.objects.create(name="Python", category="Technique")
        MarketTrend.objects.create(
            title="Python Growth",
            source_name="Test Source",
            year=2025,
            sector="Tech",
            trend_score=0.9,
        )

    @override_settings(FUTURE_SKILLS_USE_ML=False)
    def test_predict_uses_rules_engine(self):
        """Test that predict uses rules engine when ML is disabled."""
        engine = PredictionEngine()

        score, level, rationale, explanation = engine.predict(self.job_role.id, self.skill.id, horizon_years=5)

        self.assertIsInstance(score, float)
        self.assertIn(level, ["LOW", "MEDIUM", "HIGH"])
        self.assertIn("Prédiction basée sur", rationale)
        self.assertIn("rules_v1", rationale)
        self.assertEqual(explanation, {})

    @override_settings(FUTURE_SKILLS_USE_ML=True)
    @patch("future_skills.services.prediction_engine.FutureSkillsModel")
    def test_predict_uses_ml_engine(self, mock_model_class):
        """Test that predict uses ML engine when available."""
        # Mock ML model
        mock_model = MagicMock()
        mock_model.is_available.return_value = True
        mock_model.predict_level.return_value = ("HIGH", 85.0)
        mock_model_class.instance.return_value = mock_model

        engine = PredictionEngine()

        score, level, rationale, explanation = engine.predict(self.job_role.id, self.skill.id, horizon_years=5)

        self.assertEqual(score, 85.0)
        self.assertEqual(level, "HIGH")
        self.assertIn("ML prediction", rationale)
        self.assertIsInstance(explanation, dict)

    @override_settings(FUTURE_SKILLS_USE_ML=True)
    @patch("future_skills.services.prediction_engine.FutureSkillsModel")
    @patch("future_skills.services.prediction_engine.EXPLANATION_ENGINE_AVAILABLE", True)
    @patch("future_skills.services.prediction_engine.ExplanationEngine")
    def test_predict_with_explanation_engine(self, mock_explanation_class, mock_model_class):
        """Test prediction with explanation engine integration."""
        # Mock ML model
        mock_model = MagicMock()
        mock_model.is_available.return_value = True
        mock_model.predict_level.return_value = ("HIGH", 85.0)
        mock_model_class.instance.return_value = mock_model

        # Mock explanation engine
        mock_explanation = MagicMock()
        mock_explanation.generate_explanation.return_value = {
            "shap_values": [0.1, 0.2, 0.3],
            "feature_importance": {"trend_score": 0.5},
        }
        mock_explanation_class.return_value = mock_explanation

        engine = PredictionEngine()

        score, level, rationale, explanation = engine.predict(self.job_role.id, self.skill.id, horizon_years=5)

        self.assertIn("shap_values", explanation)
        self.assertIn("feature_importance", explanation)

    @override_settings(FUTURE_SKILLS_USE_ML=True)
    @patch("future_skills.services.prediction_engine.FutureSkillsModel")
    @patch("future_skills.services.prediction_engine.EXPLANATION_ENGINE_AVAILABLE", True)
    @patch("future_skills.services.prediction_engine.ExplanationEngine")
    def test_predict_handles_explanation_error(self, mock_explanation_class, mock_model_class):
        """Test that prediction continues even if explanation fails."""
        # Mock ML model
        mock_model = MagicMock()
        mock_model.is_available.return_value = True
        mock_model.predict_level.return_value = ("HIGH", 85.0)
        mock_model_class.instance.return_value = mock_model

        # Mock explanation engine that raises error
        mock_explanation = MagicMock()
        mock_explanation.generate_explanation.side_effect = Exception("SHAP error")
        mock_explanation_class.return_value = mock_explanation

        engine = PredictionEngine()

        # Should not raise exception
        score, level, rationale, explanation = engine.predict(self.job_role.id, self.skill.id, horizon_years=5)

        self.assertEqual(score, 85.0)
        self.assertEqual(level, "HIGH")
        # Explanation should be empty dict due to error
        self.assertEqual(explanation, {})


class TestPredictionEngineBatchPredict(TestCase):
    """Test PredictionEngine.batch_predict() method."""

    def setUp(self):
        self.job_role1 = JobRole.objects.create(name="Data Scientist", department="IT")
        self.job_role2 = JobRole.objects.create(name="Software Engineer", department="IT")
        self.skill1 = Skill.objects.create(name="Python", category="Technique")
        self.skill2 = Skill.objects.create(name="Java", category="Technique")
        MarketTrend.objects.create(
            title="Tech Trends",
            source_name="Test Source",
            year=2025,
            sector="Tech",
            trend_score=0.8,
        )

    @override_settings(FUTURE_SKILLS_USE_ML=False)
    def test_batch_predict_multiple_predictions(self):
        """Test batch prediction with multiple inputs."""
        engine = PredictionEngine()

        predictions_data = [
            {
                "job_role_id": self.job_role1.id,
                "skill_id": self.skill1.id,
                "horizon_years": 5,
            },
            {
                "job_role_id": self.job_role2.id,
                "skill_id": self.skill2.id,
                "horizon_years": 3,
            },
        ]

        results = engine.batch_predict(predictions_data)

        self.assertEqual(len(results), 2)

        # Check first result
        self.assertEqual(results[0]["job_role_id"], self.job_role1.id)
        self.assertEqual(results[0]["skill_id"], self.skill1.id)
        self.assertEqual(results[0]["horizon_years"], 5)
        self.assertIn("score", results[0])
        self.assertIn("level", results[0])
        self.assertIn("rationale", results[0])

        # Check second result
        self.assertEqual(results[1]["job_role_id"], self.job_role2.id)
        self.assertEqual(results[1]["skill_id"], self.skill2.id)
        self.assertEqual(results[1]["horizon_years"], 3)

    @override_settings(FUTURE_SKILLS_USE_ML=False)
    def test_batch_predict_empty_list(self):
        """Test batch prediction with empty input list."""
        engine = PredictionEngine()

        results = engine.batch_predict([])

        self.assertEqual(results, [])

    @override_settings(FUTURE_SKILLS_USE_ML=False)
    def test_batch_predict_single_item(self):
        """Test batch prediction with single item."""
        engine = PredictionEngine()

        predictions_data = [
            {
                "job_role_id": self.job_role1.id,
                "skill_id": self.skill1.id,
                "horizon_years": 5,
            }
        ]

        results = engine.batch_predict(predictions_data)

        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0]["score"], float)


# ============================================================================
# Test Prediction Logging
# ============================================================================


class TestLogPredictionForMonitoring(TestCase):
    """Test _log_prediction_for_monitoring function."""

    def setUp(self):
        self.job_role = JobRole.objects.create(name="Data Scientist", department="IT")
        self.skill = Skill.objects.create(name="Python", category="Technique")

    @override_settings(FUTURE_SKILLS_ENABLE_MONITORING=True)
    def test_log_prediction_creates_log_file(self):
        """Test that logging creates a log file with correct format."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "predictions_monitoring.jsonl"

            with override_settings(FUTURE_SKILLS_MONITORING_LOG=log_path):
                _log_prediction_for_monitoring(
                    job_role_id=self.job_role.id,
                    skill_id=self.skill.id,
                    predicted_level="HIGH",
                    score=85.5,
                    engine="ml_random_forest_v1",
                    model_version="v1.0.0",
                    features={"trend_score": 0.9, "internal_usage": 0.7},
                )

                # Verify file was created
                self.assertTrue(log_path.exists())

                # Verify content
                with open(log_path, "r") as f:
                    line = f.readline()
                    log_entry = json.loads(line)

                    self.assertEqual(log_entry["job_role_id"], self.job_role.id)
                    self.assertEqual(log_entry["skill_id"], self.skill.id)
                    self.assertEqual(log_entry["predicted_level"], "HIGH")
                    self.assertEqual(log_entry["score"], 85.5)
                    self.assertEqual(log_entry["engine"], "ml_random_forest_v1")
                    self.assertEqual(log_entry["model_version"], "v1.0.0")
                    self.assertIn("timestamp", log_entry)
                    self.assertIn("features", log_entry)

    @override_settings(FUTURE_SKILLS_ENABLE_MONITORING=False)
    def test_log_prediction_disabled_does_nothing(self):
        """Test that logging does nothing when disabled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "predictions_monitoring.jsonl"

            with override_settings(FUTURE_SKILLS_MONITORING_LOG=log_path):
                _log_prediction_for_monitoring(
                    job_role_id=self.job_role.id,
                    skill_id=self.skill.id,
                    predicted_level="HIGH",
                    score=85.5,
                    engine="rules_v1",
                )

                # Verify file was NOT created
                self.assertFalse(log_path.exists())

    @override_settings(FUTURE_SKILLS_ENABLE_MONITORING=True)
    def test_log_prediction_appends_to_existing_file(self):
        """Test that logging appends to existing log file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "predictions_monitoring.jsonl"

            with override_settings(FUTURE_SKILLS_MONITORING_LOG=log_path):
                # First log
                _log_prediction_for_monitoring(
                    job_role_id=self.job_role.id,
                    skill_id=self.skill.id,
                    predicted_level="HIGH",
                    score=85.5,
                    engine="ml_random_forest_v1",
                )

                # Second log
                _log_prediction_for_monitoring(
                    job_role_id=self.job_role.id,
                    skill_id=self.skill.id,
                    predicted_level="MEDIUM",
                    score=55.0,
                    engine="rules_v1",
                )

                # Verify both entries exist
                with open(log_path, "r") as f:
                    lines = f.readlines()
                    self.assertEqual(len(lines), 2)

                    entry1 = json.loads(lines[0])
                    entry2 = json.loads(lines[1])

                    self.assertEqual(entry1["predicted_level"], "HIGH")
                    self.assertEqual(entry2["predicted_level"], "MEDIUM")

    @override_settings(FUTURE_SKILLS_ENABLE_MONITORING=True)
    def test_log_prediction_with_no_features(self):
        """Test logging without features parameter."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "predictions_monitoring.jsonl"

            with override_settings(FUTURE_SKILLS_MONITORING_LOG=log_path):
                _log_prediction_for_monitoring(
                    job_role_id=self.job_role.id,
                    skill_id=self.skill.id,
                    predicted_level="LOW",
                    score=25.0,
                    engine="rules_v1",
                )

                with open(log_path, "r") as f:
                    log_entry = json.loads(f.readline())
                    self.assertEqual(log_entry["features"], {})

    @override_settings(FUTURE_SKILLS_ENABLE_MONITORING=True)
    @patch(
        "future_skills.services.prediction_engine.open",
        side_effect=IOError("Disk full"),
    )
    def test_log_prediction_handles_write_error(self, mock_open):
        """Test that logging handles write errors gracefully."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "predictions_monitoring.jsonl"

            with override_settings(FUTURE_SKILLS_MONITORING_LOG=log_path):
                # Should not raise exception
                _log_prediction_for_monitoring(
                    job_role_id=self.job_role.id,
                    skill_id=self.skill.id,
                    predicted_level="HIGH",
                    score=85.5,
                    engine="rules_v1",
                )


# ============================================================================
# Test recalculate_predictions Integration
# ============================================================================


class TestRecalculatePredictionsExtended(TestCase):
    """Extended tests for recalculate_predictions function."""

    def setUp(self):
        self.skill_python = Skill.objects.create(name="Python", category="Technique")
        self.skill_java = Skill.objects.create(name="Java", category="Technique")
        self.job_de = JobRole.objects.create(name="Data Engineer", department="IT")
        self.job_dev = JobRole.objects.create(name="Developer", department="IT")
        MarketTrend.objects.create(
            title="Tech Boom",
            source_name="Test Source",
            year=2025,
            sector="Tech",
            trend_score=0.9,
        )
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")

    @override_settings(FUTURE_SKILLS_USE_ML=False)
    def test_recalculate_with_run_by_user(self):
        """Test recalculate_predictions with run_by parameter."""
        total = recalculate_predictions(horizon_years=3, run_by=self.user)

        expected_count = JobRole.objects.count() * Skill.objects.count()
        self.assertEqual(total, expected_count)

        run = PredictionRun.objects.first()
        self.assertEqual(run.run_by, self.user)

    @override_settings(FUTURE_SKILLS_USE_ML=False)
    def test_recalculate_with_custom_parameters(self):
        """Test recalculate_predictions with custom parameters dict."""
        custom_params = {
            "trigger": "api",
            "source": "admin_panel",
            "custom_setting": "value",
        }

        total = recalculate_predictions(horizon_years=5, parameters=custom_params)

        run = PredictionRun.objects.first()
        self.assertEqual(run.parameters["trigger"], "api")
        self.assertEqual(run.parameters["source"], "admin_panel")
        self.assertEqual(run.parameters["custom_setting"], "value")
        self.assertEqual(run.parameters["engine"], "rules_v1")
        self.assertEqual(run.parameters["horizon_years"], 5)

    @override_settings(FUTURE_SKILLS_USE_ML=False)
    def test_recalculate_with_generate_explanations_flag(self):
        """Test recalculate_predictions with generate_explanations flag."""
        # This flag is currently not used in implementation but should not cause errors
        total = recalculate_predictions(horizon_years=5, generate_explanations=True)

        expected_count = JobRole.objects.count() * Skill.objects.count()
        self.assertEqual(total, expected_count)

    @override_settings(FUTURE_SKILLS_USE_ML=False)
    def test_recalculate_updates_existing_predictions(self):
        """Test that recalculate updates existing predictions instead of creating duplicates."""
        # First run
        total1 = recalculate_predictions(horizon_years=5)
        count_after_first = FutureSkillPrediction.objects.count()

        # Second run with same horizon
        total2 = recalculate_predictions(horizon_years=5)
        count_after_second = FutureSkillPrediction.objects.count()

        # Count should be the same (update_or_create)
        self.assertEqual(count_after_first, count_after_second)
        self.assertEqual(total1, total2)

    @override_settings(FUTURE_SKILLS_USE_ML=False)
    def test_recalculate_with_different_horizons(self):
        """Test recalculate with different horizon values."""
        # Create predictions for horizon=5
        total_5 = recalculate_predictions(horizon_years=5)

        # Create predictions for horizon=10
        total_10 = recalculate_predictions(horizon_years=10)

        # Should create separate sets of predictions
        predictions_5 = FutureSkillPrediction.objects.filter(horizon_years=5)
        predictions_10 = FutureSkillPrediction.objects.filter(horizon_years=10)

        self.assertEqual(predictions_5.count(), total_5)
        self.assertEqual(predictions_10.count(), total_10)

    @override_settings(FUTURE_SKILLS_USE_ML=True, FUTURE_SKILLS_MODEL_VERSION="ml_random_forest_v2")
    @patch("future_skills.services.prediction_engine.FutureSkillsModel")
    def test_recalculate_with_ml_includes_model_version(self, mock_model_class):
        """Test that ML mode includes model_version in parameters."""
        mock_model = MagicMock()
        mock_model.is_available.return_value = True
        mock_model.predict_level.return_value = ("HIGH", 85.0)
        mock_model_class.instance.return_value = mock_model

        total = recalculate_predictions(horizon_years=5)

        run = PredictionRun.objects.first()
        self.assertEqual(run.parameters["engine"], "ml_random_forest_v1")
        self.assertEqual(run.parameters["model_version"], "ml_random_forest_v2")

    @override_settings(FUTURE_SKILLS_USE_ML=False)
    def test_recalculate_with_none_parameters(self):
        """Test recalculate_predictions with parameters=None."""
        total = recalculate_predictions(horizon_years=5, parameters=None)

        run = PredictionRun.objects.first()
        self.assertIn("engine", run.parameters)
        self.assertIn("horizon_years", run.parameters)

    @override_settings(FUTURE_SKILLS_USE_ML=False, FUTURE_SKILLS_ENABLE_MONITORING=True)
    def test_recalculate_logs_predictions_for_monitoring(self):
        """Test that recalculate logs predictions when monitoring is enabled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "predictions_monitoring.jsonl"

            with override_settings(FUTURE_SKILLS_MONITORING_LOG=log_path):
                total = recalculate_predictions(horizon_years=5)

                # Verify monitoring logs were created
                self.assertTrue(log_path.exists())

                with open(log_path, "r") as f:
                    lines = f.readlines()
                    self.assertEqual(len(lines), total)


# ============================================================================
# Test calculate_level Edge Cases
# ============================================================================


class TestCalculateLevelEdgeCases(TestCase):
    """Test edge cases for calculate_level function."""

    def test_calculate_level_with_values_out_of_range_high(self):
        """Test that values > 1.0 are clamped correctly."""
        level, score = calculate_level(trend_score=1.5, internal_usage=1.2, training_requests=200.0)

        # Should clamp to valid range
        self.assertIn(level, ["LOW", "MEDIUM", "HIGH"])
        self.assertLessEqual(score, 100.0)

    def test_calculate_level_with_values_out_of_range_low(self):
        """Test that negative values are clamped to 0."""
        level, score = calculate_level(trend_score=-0.5, internal_usage=-0.2, training_requests=-10.0)

        self.assertEqual(level, "LOW")
        self.assertGreaterEqual(score, 0.0)

    def test_calculate_level_boundary_high_threshold(self):
        """Test boundary at HIGH threshold (0.7)."""
        level, score = calculate_level(trend_score=0.7, internal_usage=0.7, training_requests=70.0)

        self.assertEqual(level, "HIGH")
        self.assertGreaterEqual(score, 70.0)

    def test_calculate_level_boundary_medium_threshold(self):
        """Test boundary at MEDIUM threshold (0.4)."""
        level, score = calculate_level(trend_score=0.4, internal_usage=0.4, training_requests=40.0)

        self.assertEqual(level, "MEDIUM")
        self.assertGreaterEqual(score, 40.0)
        self.assertLess(score, 70.0)

    def test_calculate_level_all_zeros(self):
        """Test with all zero inputs."""
        level, score = calculate_level(trend_score=0.0, internal_usage=0.0, training_requests=0.0)

        self.assertEqual(level, "LOW")
        self.assertEqual(score, 0.0)

    def test_calculate_level_all_max(self):
        """Test with all maximum inputs."""
        level, score = calculate_level(trend_score=1.0, internal_usage=1.0, training_requests=100.0)

        self.assertEqual(level, "HIGH")
        self.assertEqual(score, 100.0)
