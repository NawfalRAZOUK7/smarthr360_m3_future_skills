"""Prometheus metrics for Future Skills predictions."""

from __future__ import annotations

from typing import Any, Dict

try:  # pragma: no cover - optional metrics dependency
    from prometheus_client import Counter, Histogram  # type: ignore

    PREDICTIONS_TOTAL = Counter(
        "future_skills_predictions_total",
        "Total number of future skills predictions",
        ["engine", "level"],
    )
    ABSTAIN_TOTAL = Counter(
        "future_skills_abstain_total",
        "Total number of fallback/abstain decisions",
        ["reason"],
    )
    CONFIDENCE_HIST = Histogram(
        "future_skills_prediction_confidence",
        "Distribution of prediction confidences",
        buckets=(0.0, 0.2, 0.4, 0.6, 0.8, 1.0),
    )
    DATA_QUALITY_TOTAL = Counter(
        "future_skills_data_quality_total",
        "Counts of data quality flags",
        ["flag"],
    )
except Exception:  # pragma: no cover - metrics optional
    PREDICTIONS_TOTAL = None
    ABSTAIN_TOTAL = None
    CONFIDENCE_HIST = None
    DATA_QUALITY_TOTAL = None


def update_prediction_metrics(
    *,
    level: str,
    confidence: float | None,
    decision_policy: Dict[str, Any] | None,
    features: Dict[str, Any] | None,
) -> None:
    """Update Prometheus metrics for a prediction."""
    if PREDICTIONS_TOTAL is None:
        return

    engine = "unknown"
    if decision_policy:
        engine = decision_policy.get("final_engine") or decision_policy.get("engine") or engine
    PREDICTIONS_TOTAL.labels(engine=engine, level=level).inc()

    if decision_policy and decision_policy.get("fallback_applied") and ABSTAIN_TOTAL is not None:
        reason = decision_policy.get("fallback_reason") or "fallback"
        ABSTAIN_TOTAL.labels(reason=reason).inc()

    if CONFIDENCE_HIST is not None and confidence is not None:
        CONFIDENCE_HIST.observe(float(confidence))

    if DATA_QUALITY_TOTAL is not None and features:
        for flag in ("data_quality_missing_flag", "data_quality_stale_flag", "data_quality_low_sample_flag"):
            try:
                if float(features.get(flag, 0.0)) >= 1.0:
                    DATA_QUALITY_TOTAL.labels(flag=flag).inc()
            except (TypeError, ValueError):
                continue
