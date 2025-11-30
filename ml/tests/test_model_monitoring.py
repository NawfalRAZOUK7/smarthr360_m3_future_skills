"""
Tests for model performance monitoring and prediction logging.

This module tests the monitoring infrastructure that enables:
- Prediction logging for drift detection
- Model performance tracking
- Monitoring enablement/disablement

Run with:
    pytest ml/tests/test_model_monitoring.py -v
"""

import pytest
import json
from pathlib import Path
from django.conf import settings
from future_skills.services.prediction_engine import _log_prediction_for_monitoring


@pytest.mark.django_db
class TestModelMonitoring:
    """Test prediction logging and monitoring."""

    def test_prediction_logging(self, tmp_path, settings):
        """Test that predictions are logged correctly."""
        log_file = tmp_path / "test_predictions.jsonl"
        settings.FUTURE_SKILLS_MONITORING_LOG = log_file
        settings.FUTURE_SKILLS_ENABLE_MONITORING = True

        # Log a prediction
        _log_prediction_for_monitoring(
            job_role_id=1,
            skill_id=5,
            predicted_level="HIGH",
            score=85.0,
            engine="ml",
            model_version="v1.0",
            features={"feature1": 0.8, "feature2": 0.9},
        )

        # Verify log file exists
        assert log_file.exists()

        # Verify log content
        with open(log_file, "r") as f:
            log_entry = json.loads(f.readline())

        assert log_entry["job_role_id"] == 1
        assert log_entry["skill_id"] == 5
        assert log_entry["predicted_level"] == "HIGH"
        assert log_entry["score"] == 85.0
        assert log_entry["engine"] == "ml"
        assert log_entry["model_version"] == "v1.0"
        assert log_entry["features"] == {"feature1": 0.8, "feature2": 0.9}
        assert "timestamp" in log_entry

    def test_monitoring_disabled(self, tmp_path, settings):
        """Test that monitoring can be disabled."""
        settings.FUTURE_SKILLS_ENABLE_MONITORING = False
        log_file = tmp_path / "test_predictions.jsonl"
        settings.FUTURE_SKILLS_MONITORING_LOG = log_file

        _log_prediction_for_monitoring(
            job_role_id=1, skill_id=5, predicted_level="HIGH", score=85.0, engine="ml"
        )

        # Log file should not be created
        assert not log_file.exists()

    def test_multiple_predictions_logging(self, tmp_path, settings):
        """Test that multiple predictions are logged in sequence."""
        log_file = tmp_path / "test_predictions.jsonl"
        settings.FUTURE_SKILLS_MONITORING_LOG = log_file
        settings.FUTURE_SKILLS_ENABLE_MONITORING = True

        # Log multiple predictions
        predictions = [
            {
                "job_role_id": 1,
                "skill_id": 5,
                "predicted_level": "HIGH",
                "score": 85.0,
                "engine": "ml",
            },
            {
                "job_role_id": 2,
                "skill_id": 6,
                "predicted_level": "MEDIUM",
                "score": 55.0,
                "engine": "rules",
            },
            {
                "job_role_id": 3,
                "skill_id": 7,
                "predicted_level": "LOW",
                "score": 25.0,
                "engine": "ml",
            },
        ]

        for pred in predictions:
            _log_prediction_for_monitoring(**pred)

        # Verify all entries
        assert log_file.exists()

        with open(log_file, "r") as f:
            lines = f.readlines()

        assert len(lines) == 3

        # Verify each entry
        for i, line in enumerate(lines):
            log_entry = json.loads(line)
            assert log_entry["job_role_id"] == predictions[i]["job_role_id"]
            assert log_entry["skill_id"] == predictions[i]["skill_id"]
            assert log_entry["predicted_level"] == predictions[i]["predicted_level"]
            assert log_entry["score"] == predictions[i]["score"]
            assert log_entry["engine"] == predictions[i]["engine"]

    def test_log_entry_structure(self, tmp_path, settings):
        """Test that log entries have correct structure."""
        log_file = tmp_path / "test_predictions.jsonl"
        settings.FUTURE_SKILLS_MONITORING_LOG = log_file
        settings.FUTURE_SKILLS_ENABLE_MONITORING = True

        _log_prediction_for_monitoring(
            job_role_id=1,
            skill_id=5,
            predicted_level="HIGH",
            score=85.5,
            engine="ml",
            model_version="v2.0",
            features={"trend_score": 0.9, "internal_usage": 0.7},
        )

        with open(log_file, "r") as f:
            log_entry = json.loads(f.readline())

        # Required fields
        required_fields = [
            "timestamp",
            "job_role_id",
            "skill_id",
            "predicted_level",
            "score",
            "engine",
            "model_version",
            "features",
        ]
        for field in required_fields:
            assert field in log_entry

        # Type validation
        assert isinstance(log_entry["timestamp"], str)
        assert isinstance(log_entry["job_role_id"], int)
        assert isinstance(log_entry["skill_id"], int)
        assert isinstance(log_entry["predicted_level"], str)
        assert isinstance(log_entry["score"], (int, float))
        assert isinstance(log_entry["engine"], str)
        assert isinstance(log_entry["features"], dict)

    def test_score_rounding(self, tmp_path, settings):
        """Test that scores are rounded to 2 decimal places."""
        log_file = tmp_path / "test_predictions.jsonl"
        settings.FUTURE_SKILLS_MONITORING_LOG = log_file
        settings.FUTURE_SKILLS_ENABLE_MONITORING = True

        # Log with high precision score
        _log_prediction_for_monitoring(
            job_role_id=1,
            skill_id=5,
            predicted_level="HIGH",
            score=85.6789,
            engine="ml",
        )

        with open(log_file, "r") as f:
            log_entry = json.loads(f.readline())

        # Should be rounded to 2 decimals
        assert log_entry["score"] == 85.68

    def test_empty_features(self, tmp_path, settings):
        """Test logging without features."""
        log_file = tmp_path / "test_predictions.jsonl"
        settings.FUTURE_SKILLS_MONITORING_LOG = log_file
        settings.FUTURE_SKILLS_ENABLE_MONITORING = True

        _log_prediction_for_monitoring(
            job_role_id=1,
            skill_id=5,
            predicted_level="HIGH",
            score=85.0,
            engine="rules",
        )

        with open(log_file, "r") as f:
            log_entry = json.loads(f.readline())

        # Features should be empty dict
        assert log_entry["features"] == {}

    def test_none_model_version(self, tmp_path, settings):
        """Test logging with None model version."""
        log_file = tmp_path / "test_predictions.jsonl"
        settings.FUTURE_SKILLS_MONITORING_LOG = log_file
        settings.FUTURE_SKILLS_ENABLE_MONITORING = True

        _log_prediction_for_monitoring(
            job_role_id=1,
            skill_id=5,
            predicted_level="HIGH",
            score=85.0,
            engine="rules",
            model_version=None,
        )

        with open(log_file, "r") as f:
            log_entry = json.loads(f.readline())

        # model_version should be None
        assert log_entry["model_version"] is None

    def test_log_directory_creation(self, tmp_path, settings):
        """Test that log directory is created if it doesn't exist."""
        log_dir = tmp_path / "nested" / "logs" / "monitoring"
        log_file = log_dir / "predictions.jsonl"
        settings.FUTURE_SKILLS_MONITORING_LOG = log_file
        settings.FUTURE_SKILLS_ENABLE_MONITORING = True

        # Directory doesn't exist yet
        assert not log_dir.exists()

        _log_prediction_for_monitoring(
            job_role_id=1, skill_id=5, predicted_level="HIGH", score=85.0, engine="ml"
        )

        # Directory should be created
        assert log_dir.exists()
        assert log_file.exists()

    def test_rules_engine_logging(self, tmp_path, settings):
        """Test logging predictions from rules-based engine."""
        log_file = tmp_path / "test_predictions.jsonl"
        settings.FUTURE_SKILLS_MONITORING_LOG = log_file
        settings.FUTURE_SKILLS_ENABLE_MONITORING = True

        _log_prediction_for_monitoring(
            job_role_id=10,
            skill_id=20,
            predicted_level="MEDIUM",
            score=55.0,
            engine="rules_v1",
        )

        with open(log_file, "r") as f:
            log_entry = json.loads(f.readline())

        assert log_entry["engine"] == "rules_v1"
        assert log_entry["model_version"] is None
        assert log_entry["features"] == {}

    def test_ml_engine_logging_with_features(self, tmp_path, settings):
        """Test logging predictions from ML engine with features."""
        log_file = tmp_path / "test_predictions.jsonl"
        settings.FUTURE_SKILLS_MONITORING_LOG = log_file
        settings.FUTURE_SKILLS_ENABLE_MONITORING = True

        features = {
            "trend_score": 0.85,
            "internal_usage": 0.75,
            "training_requests": 0.65,
            "scarcity_index": 0.55,
        }

        _log_prediction_for_monitoring(
            job_role_id=15,
            skill_id=25,
            predicted_level="HIGH",
            score=88.0,
            engine="ml_v2",
            model_version="v2.1.0",
            features=features,
        )

        with open(log_file, "r") as f:
            log_entry = json.loads(f.readline())

        assert log_entry["engine"] == "ml_v2"
        assert log_entry["model_version"] == "v2.1.0"
        assert log_entry["features"] == features


@pytest.mark.django_db
class TestMonitoringIntegration:
    """Test monitoring integration with prediction engine."""

    def test_monitoring_with_default_settings(self, tmp_path, settings):
        """Test that monitoring uses default settings correctly."""
        # Set custom BASE_DIR for test
        settings.BASE_DIR = tmp_path
        default_log_path = tmp_path / "logs" / "predictions_monitoring.jsonl"

        # Don't set FUTURE_SKILLS_MONITORING_LOG - should use default
        if hasattr(settings, "FUTURE_SKILLS_MONITORING_LOG"):
            delattr(settings, "FUTURE_SKILLS_MONITORING_LOG")

        settings.FUTURE_SKILLS_ENABLE_MONITORING = True

        _log_prediction_for_monitoring(
            job_role_id=1, skill_id=5, predicted_level="HIGH", score=85.0, engine="ml"
        )

        # Should use default path
        assert default_log_path.exists()

    def test_jsonl_format(self, tmp_path, settings):
        """Test that log uses JSONL format (one JSON per line)."""
        log_file = tmp_path / "test_predictions.jsonl"
        settings.FUTURE_SKILLS_MONITORING_LOG = log_file
        settings.FUTURE_SKILLS_ENABLE_MONITORING = True

        # Log multiple predictions
        for i in range(5):
            _log_prediction_for_monitoring(
                job_role_id=i,
                skill_id=i + 10,
                predicted_level="HIGH",
                score=80.0 + i,
                engine="ml",
            )

        # Each line should be valid JSON
        with open(log_file, "r") as f:
            lines = f.readlines()

        assert len(lines) == 5

        for i, line in enumerate(lines):
            # Each line should be valid JSON
            log_entry = json.loads(line.strip())
            assert log_entry["job_role_id"] == i
            assert log_entry["skill_id"] == i + 10
