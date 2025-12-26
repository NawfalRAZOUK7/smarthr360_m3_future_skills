# ml/monitoring.py

"""
ML Model Monitoring System for SmartHR360.

Provides comprehensive monitoring capabilities including:
- Prediction logging and tracking
- Model performance monitoring
- Data drift detection
- Concept drift detection
- Feature importance tracking
- Real-time metrics and alerts

Usage:
    from ml.monitoring import ModelMonitor, PredictionLogger

    # Initialize monitor
    monitor = ModelMonitor(model_name="future-skills-model")

    # Log predictions
    logger = PredictionLogger()
    logger.log_prediction(
        model_version="1.0.0",
        features={"experience": 5, "skill_level": 7},
        prediction="HIGH",
        probability=0.95
    )

    # Check for drift
    has_drift = monitor.detect_data_drift(reference_data, current_data)
"""

import json
import logging
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

try:
    from evidently.metric_preset import DataDriftPreset
    from evidently.metrics import DataDriftTable, DatasetDriftMetric
    from evidently.report import Report

    EVIDENTLY_AVAILABLE = True
except ImportError:
    EVIDENTLY_AVAILABLE = False
    logging.warning("Evidently not installed. Data drift detection will be limited.")

from django.core.cache import cache
from prometheus_client import Counter, Gauge, Histogram

logger = logging.getLogger(__name__)


# Prometheus Metrics
PREDICTION_COUNTER = Counter(
    "ml_predictions_total",
    "Total number of predictions made",
    ["model_name", "model_version", "prediction_class"],
)

PREDICTION_LATENCY = Histogram(
    "ml_prediction_latency_seconds",
    "Prediction latency in seconds",
    ["model_name", "model_version"],
)

MODEL_ACCURACY_GAUGE = Gauge("ml_model_accuracy", "Current model accuracy", ["model_name", "model_version"])

DRIFT_DETECTED = Counter(
    "ml_drift_detections_total",
    "Number of data drift detections",
    ["model_name", "drift_type"],
)

ERROR_COUNTER = Counter(
    "ml_prediction_errors_total",
    "Total prediction errors",
    ["model_name", "error_type"],
)


@dataclass
class PredictionLog:
    """Single prediction log entry."""

    timestamp: datetime
    model_name: str
    model_version: str
    features: Dict[str, Any]
    prediction: Any
    probability: Optional[float] = None
    actual_value: Optional[Any] = None
    prediction_time_ms: Optional[float] = None
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data

    def is_correct(self) -> Optional[bool]:
        """Check if prediction is correct (if actual value is known)."""
        if self.actual_value is None:
            return None
        return self.prediction == self.actual_value


class PredictionLogger:
    """
    Logs and tracks model predictions.

    Stores predictions for monitoring, analysis, and retraining.
    """

    def __init__(self, storage_path: Optional[Path] = None, buffer_size: int = 1000):
        """
        Initialize prediction logger.

        Args:
            storage_path: Path to store prediction logs
            buffer_size: Number of predictions to buffer before writing
        """
        self.storage_path = storage_path or Path("ml/logs/predictions")
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.buffer_size = buffer_size
        self.buffer: deque = deque(maxlen=buffer_size)

        self._daily_file: Optional[Path] = None
        self._update_daily_file()

    def _update_daily_file(self) -> None:
        """Update daily log file path."""
        date_str = datetime.now().strftime("%Y%m%d")
        self._daily_file = self.storage_path / f"predictions_{date_str}.jsonl"

    def log_prediction(
        self,
        model_name: str,
        model_version: str,
        features: Dict[str, Any],
        prediction: Any,
        probability: Optional[float] = None,
        prediction_time_ms: Optional[float] = None,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log a prediction.

        Args:
            model_name: Name of the model
            model_version: Version of the model
            features: Input features used for prediction
            prediction: Model prediction
            probability: Prediction probability/confidence
            prediction_time_ms: Prediction latency in milliseconds
            request_id: Request identifier
            user_id: User identifier
            metadata: Additional metadata
        """
        log_entry = PredictionLog(
            timestamp=datetime.now(),
            model_name=model_name,
            model_version=model_version,
            features=features,
            prediction=prediction,
            probability=probability,
            prediction_time_ms=prediction_time_ms,
            request_id=request_id,
            user_id=user_id,
            metadata=metadata or {},
        )

        # Add to buffer
        self.buffer.append(log_entry)

        # Update Prometheus metrics
        PREDICTION_COUNTER.labels(
            model_name=model_name,
            model_version=model_version,
            prediction_class=str(prediction),
        ).inc()

        if prediction_time_ms:
            PREDICTION_LATENCY.labels(model_name=model_name, model_version=model_version).observe(
                prediction_time_ms / 1000.0
            )

        # Flush buffer if full
        if len(self.buffer) >= self.buffer_size:
            self.flush()

    def flush(self) -> None:
        """Write buffered predictions to disk."""
        if not self.buffer:
            return

        self._update_daily_file()

        try:
            with open(self._daily_file, "a") as f:
                for log_entry in self.buffer:
                    f.write(json.dumps(log_entry.to_dict()) + "\n")

            logger.debug(f"Flushed {len(self.buffer)} predictions to {self._daily_file}")
            self.buffer.clear()

        except Exception as e:
            logger.error(f"Failed to flush prediction logs: {e}")

    def get_recent_predictions(
        self,
        model_name: Optional[str] = None,
        model_version: Optional[str] = None,
        limit: int = 100,
    ) -> List[PredictionLog]:
        """
        Get recent predictions from buffer and recent log files.

        Args:
            model_name: Filter by model name
            model_version: Filter by model version
            limit: Maximum number of predictions to return

        Returns:
            List of PredictionLog objects
        """
        predictions = list(self.buffer)

        # Filter if needed
        if model_name:
            predictions = [p for p in predictions if p.model_name == model_name]
        if model_version:
            predictions = [p for p in predictions if p.model_version == model_version]

        return predictions[-limit:]

    def load_predictions_from_date(self, date: datetime, model_name: Optional[str] = None) -> List[PredictionLog]:
        """
        Load predictions from a specific date.

        Args:
            date: Date to load predictions from
            model_name: Optional model name filter

        Returns:
            List of PredictionLog objects
        """
        date_str = date.strftime("%Y%m%d")
        log_file = self.storage_path / f"predictions_{date_str}.jsonl"

        if not log_file.exists():
            return []

        predictions = []

        try:
            with open(log_file, "r") as f:
                for line in f:
                    data = json.loads(line)
                    data["timestamp"] = datetime.fromisoformat(data["timestamp"])

                    if model_name and data.get("model_name") != model_name:
                        continue

                    predictions.append(PredictionLog(**data))

        except Exception as e:
            logger.error(f"Failed to load predictions from {log_file}: {e}")

        return predictions

    def get_prediction_statistics(
        self, model_name: str, start_date: datetime, end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get prediction statistics for a date range.

        Args:
            model_name: Model name
            start_date: Start date
            end_date: End date (default: today)

        Returns:
            Dictionary of statistics
        """
        if end_date is None:
            end_date = datetime.now()

        all_predictions = []
        current_date = start_date

        while current_date <= end_date:
            predictions = self.load_predictions_from_date(current_date, model_name)
            all_predictions.extend(predictions)
            current_date += timedelta(days=1)

        if not all_predictions:
            return {
                "total_predictions": 0,
                "date_range": f"{start_date.date()} to {end_date.date()}",
            }

        # Calculate statistics
        prediction_times = [p.prediction_time_ms for p in all_predictions if p.prediction_time_ms is not None]

        probabilities = [p.probability for p in all_predictions if p.probability is not None]

        # Count predictions by class
        prediction_counts = defaultdict(int)
        for p in all_predictions:
            prediction_counts[str(p.prediction)] += 1

        stats = {
            "total_predictions": len(all_predictions),
            "date_range": f"{start_date.date()} to {end_date.date()}",
            "prediction_counts": dict(prediction_counts),
            "avg_prediction_time_ms": (np.mean(prediction_times) if prediction_times else None),
            "p50_prediction_time_ms": (np.percentile(prediction_times, 50) if prediction_times else None),
            "p95_prediction_time_ms": (np.percentile(prediction_times, 95) if prediction_times else None),
            "p99_prediction_time_ms": (np.percentile(prediction_times, 99) if prediction_times else None),
            "avg_probability": np.mean(probabilities) if probabilities else None,
            "min_probability": np.min(probabilities) if probabilities else None,
        }

        return stats


class ModelMonitor:
    """
    Comprehensive model monitoring.

    Tracks model performance, drift, and health metrics.
    """

    def __init__(self, model_name: str, model_version: Optional[str] = None, cache_ttl: int = 300):
        """
        Initialize model monitor.

        Args:
            model_name: Name of the model to monitor
            model_version: Optional specific version to monitor
            cache_ttl: Cache time-to-live in seconds
        """
        self.model_name = model_name
        self.model_version = model_version
        self.cache_ttl = cache_ttl

        self.prediction_logger = PredictionLogger()

        # Performance tracking
        self.performance_history: deque = deque(maxlen=1000)

        # Drift detection settings
        self.drift_threshold = 0.1  # 10% drift threshold
        self.reference_data: Optional[pd.DataFrame] = None

    def set_reference_data(self, data: pd.DataFrame) -> None:
        """
        Set reference data for drift detection.

        Args:
            data: Reference dataset (training data)
        """
        self.reference_data = data.copy()
        logger.info(f"Set reference data with {len(data)} samples")

    def detect_data_drift(
        self, current_data: pd.DataFrame, reference_data: Optional[pd.DataFrame] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Detect data drift between reference and current data.

        Args:
            current_data: Current dataset
            reference_data: Reference dataset (default: use set reference data)

        Returns:
            Tuple of (drift_detected, drift_report)
        """
        if not EVIDENTLY_AVAILABLE:
            logger.warning("Evidently not available, using basic drift detection")
            return self._basic_drift_detection(current_data, reference_data)

        if reference_data is None:
            reference_data = self.reference_data

        if reference_data is None:
            logger.error("No reference data set for drift detection")
            return False, {"error": "No reference data"}

        try:
            # Create Evidently report
            report = Report(
                metrics=[
                    DataDriftPreset(),
                    DatasetDriftMetric(),
                    DataDriftTable(),
                ]
            )

            report.run(reference_data=reference_data, current_data=current_data)

            # Extract drift results
            report_dict = report.as_dict()

            # Check if drift detected
            dataset_drift = report_dict.get("metrics", [{}])[0]
            drift_detected = dataset_drift.get("result", {}).get("dataset_drift", False)

            drift_report = {
                "drift_detected": drift_detected,
                "drift_score": dataset_drift.get("result", {}).get("drift_share", 0.0),
                "drifted_features": dataset_drift.get("result", {}).get("number_of_drifted_columns", 0),
                "timestamp": datetime.now().isoformat(),
            }

            if drift_detected:
                DRIFT_DETECTED.labels(model_name=self.model_name, drift_type="data_drift").inc()

                logger.warning(
                    f"Data drift detected for {self.model_name}: "
                    f"{drift_report['drifted_features']} features drifted"
                )

            return drift_detected, drift_report

        except Exception as e:
            logger.error(f"Failed to detect data drift: {e}")
            return False, {"error": str(e)}

    def _basic_drift_detection(
        self, current_data: pd.DataFrame, reference_data: Optional[pd.DataFrame] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Basic drift detection using statistical tests.

        Fallback when Evidently is not available.
        """
        if reference_data is None:
            reference_data = self.reference_data

        if reference_data is None:
            return False, {"error": "No reference data"}

        drift_detected = False
        drifted_features = []

        for column in reference_data.select_dtypes(include=[np.number]).columns:
            if column not in current_data.columns:
                continue

            # Use Kolmogorov-Smirnov test for numeric features
            from scipy import stats

            ref_values = reference_data[column].dropna()
            cur_values = current_data[column].dropna()

            _, pvalue = stats.ks_2samp(ref_values, cur_values)

            if pvalue < 0.05:  # Significant drift
                drift_detected = True
                drifted_features.append(column)

        drift_report = {
            "drift_detected": drift_detected,
            "drifted_features": drifted_features,
            "num_drifted_features": len(drifted_features),
            "timestamp": datetime.now().isoformat(),
        }

        return drift_detected, drift_report

    def track_model_performance(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        metrics: Optional[Dict[str, float]] = None,
    ) -> None:
        """
        Track model performance over time.

        Args:
            y_true: True labels
            y_pred: Predicted labels
            metrics: Optional pre-calculated metrics
        """
        if metrics is None:
            from sklearn.metrics import accuracy_score, precision_recall_fscore_support

            accuracy = accuracy_score(y_true, y_pred)
            precision, recall, f1, _ = precision_recall_fscore_support(
                y_true, y_pred, average="weighted", zero_division=0
            )

            metrics = {
                "accuracy": accuracy,
                "precision": precision,
                "recall": recall,
                "f1_score": f1,
            }

        # Add timestamp
        metrics["timestamp"] = datetime.now().isoformat()
        metrics["sample_count"] = len(y_true)

        # Add to history
        self.performance_history.append(metrics)

        # Update Prometheus gauge
        MODEL_ACCURACY_GAUGE.labels(model_name=self.model_name, model_version=self.model_version or "unknown").set(
            metrics["accuracy"]
        )

        # Cache recent metrics
        cache_key = f"model_metrics:{self.model_name}"
        cache.set(cache_key, metrics, self.cache_ttl)

    def get_performance_metrics(self, window_size: int = 100) -> Dict[str, Any]:
        """
        Get recent performance metrics.

        Args:
            window_size: Number of recent evaluations to include

        Returns:
            Dictionary of aggregated metrics
        """
        if not self.performance_history:
            return {}

        recent_metrics = list(self.performance_history)[-window_size:]

        # Aggregate metrics
        aggregated = {
            "window_size": len(recent_metrics),
            "latest": recent_metrics[-1] if recent_metrics else {},
            "average": {},
            "trend": {},
        }

        # Calculate averages
        for metric_name in ["accuracy", "precision", "recall", "f1_score"]:
            values = [m.get(metric_name) for m in recent_metrics if metric_name in m]
            if values:
                aggregated["average"][metric_name] = np.mean(values)

                # Simple trend (compare first half to second half)
                if len(values) >= 4:
                    mid = len(values) // 2
                    first_half = np.mean(values[:mid])
                    second_half = np.mean(values[mid:])
                    trend = "improving" if second_half > first_half else "declining"
                    aggregated["trend"][metric_name] = {
                        "direction": trend,
                        "change": second_half - first_half,
                    }

        return aggregated

    def check_model_health(self) -> Dict[str, Any]:
        """
        Perform health check on the model.

        Returns:
            Dictionary with health status and issues
        """
        health = {
            "status": "healthy",
            "issues": [],
            "timestamp": datetime.now().isoformat(),
        }

        # Check performance degradation
        metrics = self.get_performance_metrics(window_size=100)
        if metrics.get("latest"):
            latest_accuracy = metrics["latest"].get("accuracy", 1.0)

            if latest_accuracy < 0.7:
                health["status"] = "degraded"
                health["issues"].append(f"Low accuracy: {latest_accuracy:.3f} (threshold: 0.7)")

        # Check for declining trend
        if metrics.get("trend", {}).get("accuracy"):
            trend = metrics["trend"]["accuracy"]
            if trend["direction"] == "declining" and abs(trend["change"]) > 0.05:
                health["status"] = "warning"
                health["issues"].append(f"Declining accuracy trend: {trend['change']:.3f}")

        # Check prediction latency
        recent_predictions = self.prediction_logger.get_recent_predictions(model_name=self.model_name, limit=100)

        if recent_predictions:
            latencies = [p.prediction_time_ms for p in recent_predictions if p.prediction_time_ms is not None]

            if latencies:
                p95_latency = np.percentile(latencies, 95)
                if p95_latency > 1000:  # > 1 second
                    health["status"] = "warning"
                    health["issues"].append(f"High prediction latency: P95={p95_latency:.0f}ms")

        return health

    def generate_monitoring_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive monitoring report.

        Returns:
            Dictionary with monitoring data
        """
        report = {
            "model_name": self.model_name,
            "model_version": self.model_version,
            "generated_at": datetime.now().isoformat(),
            "health": self.check_model_health(),
            "performance": self.get_performance_metrics(),
        }

        # Add prediction statistics
        stats = self.prediction_logger.get_prediction_statistics(
            model_name=self.model_name, start_date=datetime.now() - timedelta(days=7)
        )
        report["prediction_stats"] = stats

        return report


def get_model_monitor(model_name: str, model_version: Optional[str] = None) -> ModelMonitor:
    """
    Get or create a model monitor instance.

    Args:
        model_name: Name of the model
        model_version: Optional model version

    Returns:
        ModelMonitor instance
    """
    cache_key = f"model_monitor:{model_name}"

    monitor = cache.get(cache_key)
    if monitor is None:
        monitor = ModelMonitor(model_name, model_version)
        cache.set(cache_key, monitor, timeout=3600)

    return monitor
