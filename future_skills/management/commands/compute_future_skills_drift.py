"""Compute drift report for Future Skills predictions."""

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from future_skills.services.drift_monitoring import (
    compute_drift_report,
    update_drift_metrics,
    write_drift_report,
)
from future_skills.tasks import trigger_async_training


class Command(BaseCommand):
    """Generate a drift report and optionally trigger retraining."""

    help = "Compute Future Skills drift report from monitoring logs."

    def add_arguments(self, parser):
        parser.add_argument("--baseline-days", type=int, default=None, help="Baseline window in days.")
        parser.add_argument("--recent-days", type=int, default=None, help="Recent window in days.")
        parser.add_argument(
            "--output",
            type=str,
            default=None,
            help="Output path for drift report JSON.",
        )
        parser.add_argument(
            "--trigger-retrain",
            action="store_true",
            help="Trigger retraining when drift alert is detected.",
        )

    def handle(self, *args, **options):
        baseline_days = options.get("baseline_days")
        recent_days = options.get("recent_days")
        output_path = options.get("output")
        trigger_retrain = bool(options.get("trigger_retrain"))

        report = compute_drift_report(
            baseline_days=baseline_days,
            recent_days=recent_days,
        )
        update_drift_metrics(report)

        output = Path(
            output_path
            or getattr(
                settings,
                "FUTURE_SKILLS_DRIFT_REPORT_PATH",
                settings.BASE_DIR / "logs" / "future_skills_drift_report.json",
            )
        )
        write_drift_report(report, output)

        self.stdout.write(self.style.SUCCESS(f"Drift report saved to {output}"))
        self.stdout.write(self.style.WARNING(f"Overall status: {report.get('overall_status')}"))

        if trigger_retrain and report.get("retrain_recommended"):
            dataset_path = str(getattr(settings, "FUTURE_SKILLS_DATASET_PATH", settings.ML_DATASETS_DIR))
            test_split = float(getattr(settings, "FUTURE_SKILLS_RETRAIN_TEST_SPLIT", 0.2))
            hyperparameters = getattr(settings, "FUTURE_SKILLS_RETRAIN_HYPERPARAMETERS", {"n_estimators": 200})
            notes = f"Manual drift-triggered retrain at {report.get('generated_at')}"
            training_run, task_id = trigger_async_training(
                dataset_path=dataset_path,
                test_split=test_split,
                hyperparameters=hyperparameters,
                notes=notes,
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Retraining triggered: run_id={training_run.id}, task_id={task_id}"
                )
            )
