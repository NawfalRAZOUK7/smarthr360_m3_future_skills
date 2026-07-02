#!/usr/bin/env python3
"""Replay predictions across snapshot dates and compute a professional drift report."""

from __future__ import annotations

import argparse
import os
import sys
import warnings
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

from django.conf import settings
from django.utils import timezone as dj_timezone

import django

os.environ.setdefault(
    "PYTHONWARNINGS",
    "ignore::UserWarning:sklearn.utils.parallel",
)

# Silence noisy sklearn parallel warning during long replay runs.
warnings.filterwarnings(
    "ignore",
    message="`sklearn.utils.parallel.delayed` should be used",
    category=UserWarning,
)


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _as_timestamp(value: date) -> datetime:
    return datetime.combine(value, time(12, 0), tzinfo=timezone.utc)


def _reset_log(log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Replay Future Skills predictions over snapshot dates for professional drift monitoring.",
    )
    parser.add_argument("--start-date", type=_parse_date, default=None, help="Start date (YYYY-MM-DD).")
    parser.add_argument("--end-date", type=_parse_date, default=None, help="End date (YYYY-MM-DD).")
    parser.add_argument("--horizon", type=int, default=5, help="Prediction horizon in years.")
    parser.add_argument("--baseline-days", type=int, default=540, help="Baseline window in days (default: 540).")
    parser.add_argument("--recent-days", type=int, default=540, help="Recent window in days (default: 540).")
    parser.add_argument("--min-samples", type=int, default=100, help="Minimum samples required per window.")
    parser.add_argument(
        "--log-path",
        type=str,
        default=None,
        help="Monitoring log output path.",
    )
    parser.add_argument(
        "--report-path",
        type=str,
        default=None,
        help="Drift report output path.",
    )
    parser.add_argument(
        "--reset-log",
        action="store_true",
        help="Clear the log file before replaying predictions.",
    )
    parser.add_argument(
        "--max-dates",
        type=int,
        default=None,
        help="Limit number of snapshot dates (for quick runs).",
    )
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Shift timestamps so the latest snapshot aligns with today (features unchanged).",
    )
    parser.add_argument(
        "--timestamp-shift-minutes",
        type=int,
        default=0,
        help="Additional timestamp shift in minutes (useful for multi-run log enrichment).",
    )
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parents[1]
    if str(base_dir) not in sys.path:
        sys.path.insert(0, str(base_dir))

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
    django.setup()

    from future_skills.models import FutureSkillSnapshot, JobRole, Skill
    from future_skills.services.drift_monitoring import compute_drift_report, write_drift_report
    from future_skills.services.prediction_engine import PredictionEngine, _log_prediction_for_monitoring

    log_path = (
        Path(args.log_path) if args.log_path else settings.BASE_DIR / "logs" / "predictions_monitoring_professional.jsonl"
    )
    report_path = (
        Path(args.report_path)
        if args.report_path
        else settings.BASE_DIR / "logs" / "future_skills_drift_report_professional.json"
    )

    if args.reset_log:
        _reset_log(log_path)

    settings.FUTURE_SKILLS_MONITORING_LOG = log_path

    snapshots = FutureSkillSnapshot.objects.values_list("as_of_date", flat=True).distinct().order_by("as_of_date")
    if args.start_date:
        snapshots = snapshots.filter(as_of_date__gte=args.start_date)
    if args.end_date:
        snapshots = snapshots.filter(as_of_date__lte=args.end_date)

    snapshot_dates = list(snapshots)
    if args.max_dates:
        snapshot_dates = snapshot_dates[: args.max_dates]

    date_offset = timedelta(0)
    if args.simulate and snapshot_dates:
        latest_snapshot = max(snapshot_dates)
        date_offset = dj_timezone.now().date() - latest_snapshot
    time_shift = timedelta(minutes=args.timestamp_shift_minutes)

    engine = PredictionEngine()
    job_roles = list(JobRole.objects.all())
    skills = list(Skill.objects.all())

    for snap_date in snapshot_dates:
        timestamp = _as_timestamp(snap_date + date_offset) + time_shift
        for job_role in job_roles:
            for skill in skills:
                result = engine.predict_with_metadata(
                    job_role.id,
                    skill.id,
                    args.horizon,
                    as_of_date=snap_date,
                )
                audit_inputs = result.get("audit_payload", {}).get("inputs") or {}
                decision_policy = result.get("decision_policy", {}) or {}
                engine_for_logging = decision_policy.get("final_engine") or (
                    "ml_random_forest_v1" if engine.use_ml else "rules_v1"
                )
                _log_prediction_for_monitoring(
                    job_role_id=job_role.id,
                    skill_id=skill.id,
                    predicted_level=result["level"],
                    score=result["score"],
                    engine=engine_for_logging,
                    model_version=result.get("model_version"),
                    features=audit_inputs,
                    confidence=result.get("confidence"),
                    probabilities=result.get("probabilities"),
                    label_provenance=result.get("label_provenance_used"),
                    decision_policy=decision_policy,
                    timestamp_override=timestamp,
                )

    report = compute_drift_report(
        log_path=log_path,
        baseline_days=args.baseline_days,
        recent_days=args.recent_days,
        min_samples=args.min_samples,
    )
    write_drift_report(report, report_path)

    print(f"Drift report saved to {report_path}")
    print(f"Overall status: {report.get('overall_status')}")

    feature_metrics = report.get("feature_metrics", {}) or {}
    for feature, metrics in feature_metrics.items():
        print(
            f"{feature}: baseline={metrics.get('baseline_count')} "
            f"recent={metrics.get('recent_count')} "
            f"psi={metrics.get('psi')} "
            f"ks={metrics.get('ks')} "
            f"status={metrics.get('status')}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
