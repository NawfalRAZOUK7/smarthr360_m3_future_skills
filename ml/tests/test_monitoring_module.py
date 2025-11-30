"""
Comprehensive tests for ml/monitoring.py module.

Tests the core monitoring infrastructure including:
- PredictionLogger class
- ModelMonitor class
- Data drift detection
- Performance tracking
- Health checks
- Metrics generation

Run with:
    pytest ml/tests/test_monitoring_module.py -v
"""

import pytest
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import numpy as np
import pandas as pd

from ml.monitoring import (
    PredictionLog,
    PredictionLogger,
    ModelMonitor,
    get_model_monitor,
    PREDICTION_COUNTER,
    PREDICTION_LATENCY,
    MODEL_ACCURACY_GAUGE,
    DRIFT_DETECTED,
)


class TestPredictionLog:
    """Test PredictionLog dataclass."""

    def test_prediction_log_creation(self):
        """Test creating a PredictionLog instance."""
        log = PredictionLog(
            timestamp=datetime.now(),
            model_name="test-model",
            model_version="1.0.0",
            features={"feature1": 0.5, "feature2": 0.8},
            prediction="HIGH",
            probability=0.95,
        )

        assert log.model_name == "test-model"
        assert log.model_version == "1.0.0"
        assert log.prediction == "HIGH"
        assert log.probability == 0.95

    def test_prediction_log_to_dict(self):
        """Test converting PredictionLog to dictionary."""
        timestamp = datetime(2025, 1, 1, 12, 0, 0)
        log = PredictionLog(
            timestamp=timestamp,
            model_name="test-model",
            model_version="1.0.0",
            features={"feature1": 0.5},
            prediction="HIGH",
            probability=0.95,
        )

        result = log.to_dict()

        assert isinstance(result, dict)
        assert result["model_name"] == "test-model"
        assert result["timestamp"] == timestamp.isoformat()
        assert result["features"] == {"feature1": 0.5}

    def test_is_correct_with_actual_value(self):
        """Test checking if prediction is correct."""
        log = PredictionLog(
            timestamp=datetime.now(),
            model_name="test-model",
            model_version="1.0.0",
            features={},
            prediction="HIGH",
            actual_value="HIGH",
        )

        assert log.is_correct() is True

    def test_is_correct_incorrect_prediction(self):
        """Test checking incorrect prediction."""
        log = PredictionLog(
            timestamp=datetime.now(),
            model_name="test-model",
            model_version="1.0.0",
            features={},
            prediction="HIGH",
            actual_value="LOW",
        )

        assert log.is_correct() is False

    def test_is_correct_no_actual_value(self):
        """Test is_correct returns None when actual value is not set."""
        log = PredictionLog(
            timestamp=datetime.now(),
            model_name="test-model",
            model_version="1.0.0",
            features={},
            prediction="HIGH",
        )

        assert log.is_correct() is None

    def test_prediction_log_with_metadata(self):
        """Test PredictionLog with metadata."""
        metadata = {"source": "api", "environment": "production"}
        log = PredictionLog(
            timestamp=datetime.now(),
            model_name="test-model",
            model_version="1.0.0",
            features={},
            prediction="HIGH",
            metadata=metadata,
        )

        assert log.metadata == metadata

    def test_prediction_log_with_request_id(self):
        """Test PredictionLog with request_id."""
        log = PredictionLog(
            timestamp=datetime.now(),
            model_name="test-model",
            model_version="1.0.0",
            features={},
            prediction="HIGH",
            request_id="req-12345",
        )

        assert log.request_id == "req-12345"


class TestPredictionLogger:
    """Test PredictionLogger class."""

    def test_initialization(self, tmp_path):
        """Test PredictionLogger initialization."""
        storage_path = tmp_path / "logs"
        logger = PredictionLogger(storage_path=storage_path, buffer_size=100)

        assert logger.storage_path == storage_path
        assert logger.buffer_size == 100
        assert len(logger.buffer) == 0
        assert storage_path.exists()

    def test_initialization_default_path(self):
        """Test PredictionLogger with default storage path."""
        logger = PredictionLogger()

        assert logger.storage_path == Path("ml/logs/predictions")
        assert logger.buffer_size == 1000

    def test_log_prediction(self, tmp_path):
        """Test logging a single prediction."""
        logger = PredictionLogger(storage_path=tmp_path, buffer_size=10)

        logger.log_prediction(
            model_name="test-model",
            model_version="1.0.0",
            features={"feature1": 0.5},
            prediction="HIGH",
            probability=0.95,
        )

        assert len(logger.buffer) == 1
        log_entry = logger.buffer[0]
        assert log_entry.model_name == "test-model"
        assert log_entry.prediction == "HIGH"

    def test_log_prediction_with_all_parameters(self, tmp_path):
        """Test logging prediction with all optional parameters."""
        logger = PredictionLogger(storage_path=tmp_path)

        logger.log_prediction(
            model_name="test-model",
            model_version="1.0.0",
            features={"feature1": 0.5},
            prediction="HIGH",
            probability=0.95,
            prediction_time_ms=50.5,
            request_id="req-123",
            user_id="user-456",
            metadata={"source": "api"},
        )

        log_entry = logger.buffer[0]
        assert log_entry.prediction_time_ms == 50.5
        assert log_entry.request_id == "req-123"
        assert log_entry.user_id == "user-456"
        assert log_entry.metadata == {"source": "api"}

    def test_buffer_flush_on_size(self, tmp_path):
        """Test that buffer flushes when full."""
        logger = PredictionLogger(storage_path=tmp_path, buffer_size=5)

        # Log 5 predictions to fill buffer
        for i in range(5):
            logger.log_prediction(
                model_name="test-model",
                model_version="1.0.0",
                features={"feature1": i},
                prediction="HIGH",
            )

        # Buffer should be cleared after flush
        assert len(logger.buffer) == 0

        # Check that file was created
        log_files = list(tmp_path.glob("predictions_*.jsonl"))
        assert len(log_files) == 1

    def test_flush_writes_to_file(self, tmp_path):
        """Test manual flush writes to file."""
        logger = PredictionLogger(storage_path=tmp_path, buffer_size=100)

        logger.log_prediction(
            model_name="test-model",
            model_version="1.0.0",
            features={"feature1": 0.5},
            prediction="HIGH",
        )

        logger.flush()

        assert len(logger.buffer) == 0

        log_files = list(tmp_path.glob("predictions_*.jsonl"))
        assert len(log_files) == 1

        # Verify content
        with open(log_files[0], "r") as f:
            content = json.loads(f.readline())
            assert content["model_name"] == "test-model"

    def test_flush_empty_buffer(self, tmp_path):
        """Test flushing empty buffer doesn't create file."""
        logger = PredictionLogger(storage_path=tmp_path)

        logger.flush()

        log_files = list(tmp_path.glob("predictions_*.jsonl"))
        assert len(log_files) == 0

    def test_daily_file_naming(self, tmp_path):
        """Test that log files use daily naming convention."""
        logger = PredictionLogger(storage_path=tmp_path, buffer_size=5)

        for i in range(5):
            logger.log_prediction(
                model_name="test-model",
                model_version="1.0.0",
                features={},
                prediction="HIGH",
            )

        date_str = datetime.now().strftime("%Y%m%d")
        expected_file = tmp_path / f"predictions_{date_str}.jsonl"
        assert expected_file.exists()

    def test_get_recent_predictions(self, tmp_path):
        """Test retrieving recent predictions from buffer."""
        logger = PredictionLogger(storage_path=tmp_path, buffer_size=100)

        for i in range(10):
            logger.log_prediction(
                model_name="test-model",
                model_version="1.0.0",
                features={"index": i},
                prediction="HIGH",
            )

        recent = logger.get_recent_predictions(limit=5)

        assert len(recent) == 5
        # Should get most recent 5
        assert recent[-1].features["index"] == 9

    def test_get_recent_predictions_filter_by_model(self, tmp_path):
        """Test filtering recent predictions by model name."""
        logger = PredictionLogger(storage_path=tmp_path)

        logger.log_prediction(
            model_name="model-A", model_version="1.0.0", features={}, prediction="HIGH"
        )
        logger.log_prediction(
            model_name="model-B", model_version="1.0.0", features={}, prediction="LOW"
        )
        logger.log_prediction(
            model_name="model-A",
            model_version="1.0.0",
            features={},
            prediction="MEDIUM",
        )

        recent = logger.get_recent_predictions(model_name="model-A")

        assert len(recent) == 2
        assert all(p.model_name == "model-A" for p in recent)

    def test_get_recent_predictions_filter_by_version(self, tmp_path):
        """Test filtering recent predictions by model version."""
        logger = PredictionLogger(storage_path=tmp_path)

        logger.log_prediction(
            model_name="test-model",
            model_version="1.0.0",
            features={},
            prediction="HIGH",
        )
        logger.log_prediction(
            model_name="test-model",
            model_version="2.0.0",
            features={},
            prediction="LOW",
        )

        recent = logger.get_recent_predictions(model_version="1.0.0")

        assert len(recent) == 1
        assert recent[0].model_version == "1.0.0"

    def test_load_predictions_from_date(self, tmp_path):
        """Test loading predictions from specific date."""
        logger = PredictionLogger(storage_path=tmp_path, buffer_size=5)

        # Log and flush predictions
        for i in range(5):
            logger.log_prediction(
                model_name="test-model",
                model_version="1.0.0",
                features={"index": i},
                prediction="HIGH",
            )

        # Load from today
        predictions = logger.load_predictions_from_date(datetime.now())

        assert len(predictions) == 5

    def test_load_predictions_from_date_no_file(self, tmp_path):
        """Test loading from date with no log file."""
        logger = PredictionLogger(storage_path=tmp_path)

        # Load from date in the past
        past_date = datetime.now() - timedelta(days=30)
        predictions = logger.load_predictions_from_date(past_date)

        assert len(predictions) == 0

    def test_load_predictions_filter_by_model(self, tmp_path):
        """Test loading predictions filtered by model name."""
        logger = PredictionLogger(storage_path=tmp_path, buffer_size=10)

        for i in range(5):
            logger.log_prediction(
                model_name="model-A",
                model_version="1.0.0",
                features={},
                prediction="HIGH",
            )
        for i in range(5):
            logger.log_prediction(
                model_name="model-B",
                model_version="1.0.0",
                features={},
                prediction="LOW",
            )

        predictions = logger.load_predictions_from_date(
            datetime.now(), model_name="model-A"
        )

        assert len(predictions) == 5
        assert all(p.model_name == "model-A" for p in predictions)

    def test_get_prediction_statistics(self, tmp_path):
        """Test getting prediction statistics."""
        logger = PredictionLogger(storage_path=tmp_path, buffer_size=20)

        # Log predictions with varying attributes
        for i in range(10):
            logger.log_prediction(
                model_name="test-model",
                model_version="1.0.0",
                features={},
                prediction="HIGH" if i % 2 == 0 else "LOW",
                probability=0.8 + (i * 0.01),
                prediction_time_ms=10.0 + i,
            )

        stats = logger.get_prediction_statistics(
            model_name="test-model", start_date=datetime.now(), end_date=datetime.now()
        )

        assert stats["total_predictions"] == 10
        assert "prediction_counts" in stats
        assert stats["prediction_counts"]["HIGH"] == 5
        assert stats["prediction_counts"]["LOW"] == 5
        assert stats["avg_prediction_time_ms"] is not None
        assert stats["avg_probability"] is not None

    def test_get_prediction_statistics_no_data(self, tmp_path):
        """Test statistics with no predictions."""
        logger = PredictionLogger(storage_path=tmp_path)

        stats = logger.get_prediction_statistics(
            model_name="test-model", start_date=datetime.now(), end_date=datetime.now()
        )

        assert stats["total_predictions"] == 0

    def test_get_prediction_statistics_percentiles(self, tmp_path):
        """Test that statistics include percentile metrics."""
        logger = PredictionLogger(storage_path=tmp_path, buffer_size=100)

        for i in range(50):
            logger.log_prediction(
                model_name="test-model",
                model_version="1.0.0",
                features={},
                prediction="HIGH",
                prediction_time_ms=float(i),
            )

        stats = logger.get_prediction_statistics(
            model_name="test-model", start_date=datetime.now()
        )

        assert "p50_prediction_time_ms" in stats
        assert "p95_prediction_time_ms" in stats
        assert "p99_prediction_time_ms" in stats
        assert stats["p50_prediction_time_ms"] is not None


class TestModelMonitor:
    """Test ModelMonitor class."""

    def test_initialization(self):
        """Test ModelMonitor initialization."""
        monitor = ModelMonitor(
            model_name="test-model", model_version="1.0.0", cache_ttl=600
        )

        assert monitor.model_name == "test-model"
        assert monitor.model_version == "1.0.0"
        assert monitor.cache_ttl == 600
        assert monitor.drift_threshold == 0.1

    def test_set_reference_data(self):
        """Test setting reference data for drift detection."""
        monitor = ModelMonitor(model_name="test-model")

        reference_data = pd.DataFrame(
            {"feature1": [1, 2, 3, 4, 5], "feature2": [5, 4, 3, 2, 1]}
        )

        monitor.set_reference_data(reference_data)

        assert monitor.reference_data is not None
        assert len(monitor.reference_data) == 5

    def test_basic_drift_detection_no_drift(self):
        """Test basic drift detection with no drift."""
        monitor = ModelMonitor(model_name="test-model")

        reference_data = pd.DataFrame(
            {
                "feature1": np.random.normal(0, 1, 100),
                "feature2": np.random.normal(5, 2, 100),
            }
        )

        current_data = pd.DataFrame(
            {
                "feature1": np.random.normal(0, 1, 100),
                "feature2": np.random.normal(5, 2, 100),
            }
        )

        monitor.set_reference_data(reference_data)
        drift_detected, report = monitor._basic_drift_detection(current_data)

        assert isinstance(drift_detected, bool)
        assert "drifted_features" in report

    def test_basic_drift_detection_with_drift(self):
        """Test basic drift detection with significant drift."""
        monitor = ModelMonitor(model_name="test-model")

        reference_data = pd.DataFrame({"feature1": np.random.normal(0, 1, 100)})

        # Create data with different distribution
        current_data = pd.DataFrame(
            {"feature1": np.random.normal(10, 1, 100)}  # Shifted mean
        )

        monitor.set_reference_data(reference_data)
        drift_detected, report = monitor._basic_drift_detection(current_data)

        assert drift_detected is True
        assert "feature1" in report["drifted_features"]

    def test_basic_drift_detection_no_reference_data(self):
        """Test drift detection without reference data."""
        monitor = ModelMonitor(model_name="test-model")

        current_data = pd.DataFrame({"feature1": [1, 2, 3]})

        drift_detected, report = monitor._basic_drift_detection(current_data)

        assert drift_detected is False
        assert "error" in report

    def test_track_model_performance(self):
        """Test tracking model performance."""
        monitor = ModelMonitor(model_name="test-model", model_version="1.0.0")

        y_true = np.array([0, 1, 1, 0, 1, 0])
        y_pred = np.array([0, 1, 1, 0, 0, 0])

        monitor.track_model_performance(y_true, y_pred)

        assert len(monitor.performance_history) == 1
        metrics = monitor.performance_history[0]
        assert "accuracy" in metrics
        assert "precision" in metrics
        assert "recall" in metrics
        assert "f1_score" in metrics

    def test_track_model_performance_with_custom_metrics(self):
        """Test tracking with pre-calculated metrics."""
        monitor = ModelMonitor(model_name="test-model")

        custom_metrics = {
            "accuracy": 0.85,
            "precision": 0.80,
            "recall": 0.90,
            "f1_score": 0.85,
        }

        y_true = np.array([1, 0, 1])
        y_pred = np.array([1, 0, 1])

        monitor.track_model_performance(y_true, y_pred, metrics=custom_metrics)

        metrics = monitor.performance_history[0]
        assert metrics["accuracy"] == 0.85

    def test_get_performance_metrics_empty(self):
        """Test getting performance metrics with no history."""
        monitor = ModelMonitor(model_name="test-model")

        metrics = monitor.get_performance_metrics()

        assert metrics == {}

    def test_get_performance_metrics(self):
        """Test getting aggregated performance metrics."""
        monitor = ModelMonitor(model_name="test-model")

        # Add multiple performance records
        for i in range(10):
            y_true = np.array([1, 0, 1, 0])
            y_pred = np.array([1, 0, 1, 0])
            monitor.track_model_performance(y_true, y_pred)

        metrics = monitor.get_performance_metrics(window_size=5)

        assert metrics["window_size"] == 5
        assert "latest" in metrics
        assert "average" in metrics
        assert "accuracy" in metrics["average"]

    def test_get_performance_metrics_trend(self):
        """Test performance trend calculation."""
        monitor = ModelMonitor(model_name="test-model")

        # Add declining performance
        for i in range(10):
            accuracy = 0.9 - (i * 0.05)  # Declining accuracy
            custom_metrics = {
                "accuracy": accuracy,
                "precision": accuracy,
                "recall": accuracy,
                "f1_score": accuracy,
            }
            y_true = np.array([1])
            y_pred = np.array([1])
            monitor.track_model_performance(y_true, y_pred, metrics=custom_metrics)

        metrics = monitor.get_performance_metrics(window_size=10)

        assert "trend" in metrics
        if "accuracy" in metrics["trend"]:
            assert metrics["trend"]["accuracy"]["direction"] == "declining"

    def test_check_model_health_healthy(self):
        """Test health check with healthy model."""
        monitor = ModelMonitor(model_name="test-model")

        # Add good performance
        y_true = np.array([1, 0, 1, 0, 1, 0])
        y_pred = np.array([1, 0, 1, 0, 1, 0])
        monitor.track_model_performance(y_true, y_pred)

        health = monitor.check_model_health()

        assert health["status"] == "healthy"
        assert len(health["issues"]) == 0

    def test_check_model_health_degraded(self):
        """Test health check with degraded model."""
        monitor = ModelMonitor(model_name="test-model")

        # Add poor performance
        custom_metrics = {
            "accuracy": 0.5,
            "precision": 0.5,
            "recall": 0.5,
            "f1_score": 0.5,
        }
        y_true = np.array([1])
        y_pred = np.array([1])
        monitor.track_model_performance(y_true, y_pred, metrics=custom_metrics)

        health = monitor.check_model_health()

        assert health["status"] == "degraded"
        assert len(health["issues"]) > 0

    def test_check_model_health_declining_trend(self):
        """Test health check detects declining trend."""
        monitor = ModelMonitor(model_name="test-model")

        # Add declining performance
        for i in range(10):
            accuracy = 0.85 - (i * 0.02)
            custom_metrics = {
                "accuracy": accuracy,
                "precision": accuracy,
                "recall": accuracy,
                "f1_score": accuracy,
            }
            y_true = np.array([1])
            y_pred = np.array([1])
            monitor.track_model_performance(y_true, y_pred, metrics=custom_metrics)

        health = monitor.check_model_health()

        # Should detect declining trend
        assert "warning" in health["status"] or "degraded" in health["status"]

    def test_generate_monitoring_report(self, tmp_path):
        """Test generating comprehensive monitoring report."""
        monitor = ModelMonitor(model_name="test-model", model_version="1.0.0")
        monitor.prediction_logger = PredictionLogger(
            storage_path=tmp_path, buffer_size=10
        )

        # Add some performance data
        y_true = np.array([1, 0, 1, 0])
        y_pred = np.array([1, 0, 1, 0])
        monitor.track_model_performance(y_true, y_pred)

        # Add some predictions
        for i in range(5):
            monitor.prediction_logger.log_prediction(
                model_name="test-model",
                model_version="1.0.0",
                features={},
                prediction="HIGH",
            )

        report = monitor.generate_monitoring_report()

        assert report["model_name"] == "test-model"
        assert report["model_version"] == "1.0.0"
        assert "health" in report
        assert "performance" in report
        assert "prediction_stats" in report

    @patch("ml.monitoring.cache")
    def test_get_model_monitor_cached(self, mock_cache):
        """Test getting model monitor from cache."""
        mock_monitor = Mock()
        mock_cache.get.return_value = mock_monitor

        monitor = get_model_monitor("test-model")

        assert monitor == mock_monitor
        mock_cache.get.assert_called_once()

    @patch("ml.monitoring.cache")
    def test_get_model_monitor_create_new(self, mock_cache):
        """Test creating new model monitor when not cached."""
        mock_cache.get.return_value = None

        monitor = get_model_monitor("test-model", "1.0.0")

        assert isinstance(monitor, ModelMonitor)
        assert monitor.model_name == "test-model"
        mock_cache.set.assert_called_once()

    def test_check_model_health_high_latency(self, tmp_path):
        """Test health check detects high prediction latency."""
        monitor = ModelMonitor(model_name="test-model")
        monitor.prediction_logger = PredictionLogger(storage_path=tmp_path)

        # Add predictions with high latency
        for i in range(100):
            monitor.prediction_logger.log_prediction(
                model_name="test-model",
                model_version="1.0.0",
                features={},
                prediction="HIGH",
                prediction_time_ms=1500.0,  # > 1000ms threshold
            )

        health = monitor.check_model_health()

        assert health["status"] in ["warning", "degraded"]
        assert any("latency" in issue.lower() for issue in health["issues"])


class TestPrometheusMetrics:
    """Test Prometheus metrics integration."""

    def test_prediction_counter_incremented(self, tmp_path):
        """Test that prediction counter is incremented."""
        logger = PredictionLogger(storage_path=tmp_path)

        initial_value = PREDICTION_COUNTER.labels(
            model_name="test-model", model_version="1.0.0", prediction_class="HIGH"
        )._value._value

        logger.log_prediction(
            model_name="test-model",
            model_version="1.0.0",
            features={},
            prediction="HIGH",
        )

        new_value = PREDICTION_COUNTER.labels(
            model_name="test-model", model_version="1.0.0", prediction_class="HIGH"
        )._value._value

        assert new_value > initial_value

    def test_prediction_latency_recorded(self, tmp_path):
        """Test that prediction latency is recorded."""
        logger = PredictionLogger(storage_path=tmp_path)

        logger.log_prediction(
            model_name="test-model",
            model_version="1.0.0",
            features={},
            prediction="HIGH",
            prediction_time_ms=50.0,
        )

        # Verify histogram was updated (count > 0)
        histogram = PREDICTION_LATENCY.labels(
            model_name="test-model", model_version="1.0.0"
        )

        assert histogram._metrics
