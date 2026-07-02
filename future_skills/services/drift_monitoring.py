"""Drift monitoring utilities for Future Skills predictions."""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List

import numpy as np
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

DEFAULT_FEATURES = [
    "trend_score",
    "internal_usage",
    "training_requests",
    "scarcity_index",
    "economic_indicator",
]

try:  # pragma: no cover - optional metrics dependency
    from prometheus_client import Gauge  # type: ignore

    DRIFT_STATUS_GAUGE = Gauge(
        "future_skills_drift_status",
        "Drift status for Future Skills model (0=ok,1=warn,2=alert)",
    )
    DRIFT_PSI_GAUGE = Gauge(
        "future_skills_drift_psi",
        "Population Stability Index for Future Skills features",
        ["feature"],
    )
    DRIFT_KS_GAUGE = Gauge(
        "future_skills_drift_ks",
        "KS statistic for Future Skills features",
        ["feature"],
    )
except Exception:  # pragma: no cover - metrics optional
    DRIFT_STATUS_GAUGE = None
    DRIFT_PSI_GAUGE = None
    DRIFT_KS_GAUGE = None


def _parse_timestamp(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    if timezone.is_naive(parsed):
        return timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def _compute_psi(expected: list[float], actual: list[float], buckets: int = 10) -> float | None:
    if len(expected) < 2 or len(actual) < 2:
        return None

    expected_arr = np.asarray(expected, dtype=float)
    actual_arr = np.asarray(actual, dtype=float)
    quantiles = np.linspace(0, 100, buckets + 1)
    breakpoints = np.unique(np.percentile(expected_arr, quantiles))
    if len(breakpoints) < 3:
        return 0.0

    expected_hist, _ = np.histogram(expected_arr, bins=breakpoints)
    actual_hist, _ = np.histogram(actual_arr, bins=breakpoints)

    expected_pct = expected_hist / max(len(expected_arr), 1)
    actual_pct = actual_hist / max(len(actual_arr), 1)

    epsilon = 1e-6
    psi = np.sum((actual_pct - expected_pct) * np.log((actual_pct + epsilon) / (expected_pct + epsilon)))
    return float(psi)


def _compute_ks(sample_a: list[float], sample_b: list[float]) -> float | None:
    if len(sample_a) < 2 or len(sample_b) < 2:
        return None

    a = np.sort(np.asarray(sample_a, dtype=float))
    b = np.sort(np.asarray(sample_b, dtype=float))
    data_all = np.sort(np.concatenate([a, b]))

    cdf_a = np.searchsorted(a, data_all, side="right") / max(len(a), 1)
    cdf_b = np.searchsorted(b, data_all, side="right") / max(len(b), 1)
    return float(np.max(np.abs(cdf_a - cdf_b)))


def _collect_feature_values(
    log_path: Path,
    *,
    baseline_start: datetime,
    baseline_end: datetime,
    recent_start: datetime,
    recent_end: datetime,
    features: Iterable[str],
) -> tuple[Dict[str, list[float]], Dict[str, list[float]]]:
    baseline_values: Dict[str, list[float]] = defaultdict(list)
    recent_values: Dict[str, list[float]] = defaultdict(list)

    if not log_path.exists():
        logger.warning("Monitoring log not found: %s", log_path)
        return baseline_values, recent_values

    with open(log_path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            timestamp = _parse_timestamp(entry.get("timestamp"))
            if not timestamp:
                continue

            target = None
            if baseline_start <= timestamp < baseline_end:
                target = baseline_values
            elif recent_start <= timestamp <= recent_end:
                target = recent_values
            if target is None:
                continue

            feature_payload = entry.get("features", {}) or {}
            for feature in features:
                value = feature_payload.get(feature)
                if value is None:
                    continue
                try:
                    target[feature].append(float(value))
                except (TypeError, ValueError):
                    continue

    return baseline_values, recent_values


def compute_drift_report(
    *,
    log_path: Path | None = None,
    baseline_days: int | None = None,
    recent_days: int | None = None,
    min_samples: int | None = None,
    features: Iterable[str] | None = None,
) -> Dict[str, Any]:
    """Compute a drift report from prediction monitoring logs."""
    now = timezone.now()
    baseline_days = baseline_days or int(getattr(settings, "FUTURE_SKILLS_DRIFT_BASELINE_DAYS", 90))
    recent_days = recent_days or int(getattr(settings, "FUTURE_SKILLS_DRIFT_RECENT_DAYS", 30))
    min_samples = min_samples or int(getattr(settings, "FUTURE_SKILLS_DRIFT_MIN_WINDOW_COUNT", 50))

    recent_end = now
    recent_start = now - timedelta(days=recent_days)
    baseline_end = recent_start
    baseline_start = baseline_end - timedelta(days=baseline_days)

    log_path = Path(
        log_path
        or getattr(
            settings,
            "FUTURE_SKILLS_MONITORING_LOG",
            settings.BASE_DIR / "logs" / "predictions_monitoring.jsonl",
        )
    )
    features = list(features or getattr(settings, "FUTURE_SKILLS_DRIFT_FEATURES", DEFAULT_FEATURES))

    baseline_values, recent_values = _collect_feature_values(
        log_path,
        baseline_start=baseline_start,
        baseline_end=baseline_end,
        recent_start=recent_start,
        recent_end=recent_end,
        features=features,
    )

    psi_warn = float(getattr(settings, "FUTURE_SKILLS_DRIFT_PSI_THRESHOLD", 0.2))
    psi_alert = float(getattr(settings, "FUTURE_SKILLS_DRIFT_PSI_HIGH", 0.3))
    ks_threshold = float(getattr(settings, "FUTURE_SKILLS_DRIFT_KS_THRESHOLD", 0.2))

    feature_metrics = {}
    overall_status = "insufficient_data"

    for feature in features:
        baseline_sample = baseline_values.get(feature, [])
        recent_sample = recent_values.get(feature, [])
        if len(baseline_sample) < min_samples or len(recent_sample) < min_samples:
            feature_metrics[feature] = {
                "psi": None,
                "ks": None,
                "baseline_count": len(baseline_sample),
                "recent_count": len(recent_sample),
                "status": "insufficient_data",
            }
            continue

        if overall_status == "insufficient_data":
            overall_status = "ok"

        psi = _compute_psi(baseline_sample, recent_sample)
        ks = _compute_ks(baseline_sample, recent_sample)

        status = "ok"
        if psi is not None and psi >= psi_alert:
            status = "alert"
        elif psi is not None and psi >= psi_warn:
            status = "warn"
        if ks is not None and ks >= ks_threshold:
            status = "alert" if status != "alert" else status

        if status == "alert":
            overall_status = "alert"
        elif status == "warn" and overall_status != "alert":
            overall_status = "warn"

        feature_metrics[feature] = {
            "psi": psi,
            "ks": ks,
            "baseline_count": len(baseline_sample),
            "recent_count": len(recent_sample),
            "status": status,
        }

    retrain_recommended = overall_status == "alert"

    return {
        "generated_at": now.isoformat(),
        "window": {
            "baseline_start": baseline_start.isoformat(),
            "baseline_end": baseline_end.isoformat(),
            "recent_start": recent_start.isoformat(),
            "recent_end": recent_end.isoformat(),
        },
        "overall_status": overall_status,
        "retrain_recommended": retrain_recommended,
        "feature_metrics": feature_metrics,
        "thresholds": {
            "psi_warn": psi_warn,
            "psi_alert": psi_alert,
            "ks_threshold": ks_threshold,
            "min_samples": min_samples,
        },
    }


def update_drift_metrics(report: Dict[str, Any]) -> None:
    """Update Prometheus gauges with drift report values."""
    if DRIFT_STATUS_GAUGE is None:
        return

    status_map = {"ok": 0, "warn": 1, "alert": 2, "insufficient_data": 0}
    status_value = status_map.get(report.get("overall_status", "ok"), 0)
    DRIFT_STATUS_GAUGE.set(status_value)

    feature_metrics = report.get("feature_metrics", {}) or {}
    if DRIFT_PSI_GAUGE and DRIFT_KS_GAUGE:
        for feature, metrics in feature_metrics.items():
            psi_value = metrics.get("psi")
            ks_value = metrics.get("ks")
            if psi_value is not None:
                DRIFT_PSI_GAUGE.labels(feature=feature).set(float(psi_value))
            if ks_value is not None:
                DRIFT_KS_GAUGE.labels(feature=feature).set(float(ks_value))


def write_drift_report(report: Dict[str, Any], output_path: Path) -> None:
    """Persist the drift report to disk as JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)
