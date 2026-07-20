"""Lifecycle helpers for non-blocking prediction recalculation."""

import logging
import threading
from django.conf import settings
from django.db import close_old_connections
from django.utils import timezone
from future_skills.models import PredictionRun

logger = logging.getLogger(__name__)


def _execute_prediction_run(run_id: int, horizon_years: int) -> None:
    close_old_connections()
    try:
        run = PredictionRun.objects.get(pk=run_id)
        run.status = "RUNNING"
        run.started_at = timezone.now()
        run.save(update_fields=["status", "started_at"])
        from .prediction_engine import recalculate_predictions
        recalculate_predictions(horizon_years=horizon_years, run_by=run.run_by, parameters=run.parameters, prediction_run=run)
    except Exception as exc:
        logger.exception("Prediction run %s failed", run_id)
        PredictionRun.objects.filter(pk=run_id).update(status="FAILED", error_message=str(exc), completed_at=timezone.now())
    finally:
        close_old_connections()


def queue_prediction_run(*, horizon_years: int, run_by=None, trigger: str) -> PredictionRun:
    run = PredictionRun.objects.create(status="QUEUED", total_predictions=0, run_by=run_by, parameters={"trigger": trigger, "horizon_years": horizon_years}, description=f"Queued prediction recalculation ({trigger}).")
    if getattr(settings, "FUTURE_SKILLS_ASYNC_PREDICTIONS", True):
        threading.Thread(target=_execute_prediction_run, args=(run.id, horizon_years), name=f"future-skills-prediction-{run.id}", daemon=True).start()
    else:
        _execute_prediction_run(run.id, horizon_years)
    return run
