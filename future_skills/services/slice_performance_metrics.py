"""Prometheus metrics for Future Skills slice-level performance."""

from __future__ import annotations

from typing import Any, Dict

from django.conf import settings

try:  # pragma: no cover - optional metrics dependency
    from prometheus_client import Gauge  # type: ignore

    SLICE_PERFORMANCE = Gauge(
        "future_skills_slice_performance",
        "Slice-level performance metrics for future skills models",
        ["slice_type", "slice_value", "metric"],
    )
    SLICE_SUPPORT = Gauge(
        "future_skills_slice_support",
        "Slice-level sample counts used for evaluation",
        ["slice_type", "slice_value"],
    )
except Exception:  # pragma: no cover - metrics optional
    SLICE_PERFORMANCE = None
    SLICE_SUPPORT = None


def update_slice_performance_metrics(*, slice_metrics: Dict[str, Any]) -> None:
    """Update Prometheus gauges for slice performance metrics."""
    if not getattr(settings, "FUTURE_SKILLS_ENABLE_MONITORING", True):
        return
    if SLICE_PERFORMANCE is None or not slice_metrics:
        return

    try:
        SLICE_PERFORMANCE.clear()
        if SLICE_SUPPORT is not None:
            SLICE_SUPPORT.clear()
    except Exception:  # pragma: no cover - gauge clear optional
        pass

    max_groups = int(getattr(settings, "FUTURE_SKILLS_SLICE_METRICS_MAX_GROUPS", 20))
    metrics_to_export = (
        "macro_f1",
        "balanced_accuracy",
        "accuracy",
        "macro_precision",
        "macro_recall",
    )

    for bucket, group_metrics in slice_metrics.items():
        if bucket == "min_slice_size":
            continue
        if not isinstance(group_metrics, dict):
            continue

        group_items = list(group_metrics.items())
        group_items.sort(key=lambda item: (item[1] or {}).get("support", 0), reverse=True)
        if max_groups > 0:
            group_items = group_items[:max_groups]

        for group_value, metrics in group_items:
            if not isinstance(metrics, dict):
                continue
            slice_value = str(group_value)

            for metric_name in metrics_to_export:
                value = metrics.get(metric_name)
                if value is None:
                    continue
                try:
                    SLICE_PERFORMANCE.labels(
                        slice_type=bucket,
                        slice_value=slice_value,
                        metric=metric_name,
                    ).set(float(value))
                except (TypeError, ValueError):
                    continue

            if SLICE_SUPPORT is not None:
                support = metrics.get("support")
                if support is None:
                    continue
                try:
                    SLICE_SUPPORT.labels(
                        slice_type=bucket,
                        slice_value=slice_value,
                    ).set(float(support))
                except (TypeError, ValueError):
                    continue
