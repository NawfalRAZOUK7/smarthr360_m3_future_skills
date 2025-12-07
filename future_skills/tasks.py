"""
Celery tasks for Future Skills ML training.

This module contains asynchronous tasks for long-running ML operations.
Tasks are executed by Celery workers in the background, allowing API
endpoints to return immediately without blocking.

Section 2.5 - Production-Ready Celery Task Implementation
Enhanced with advanced retry strategies, monitoring, and error handling.
"""

import logging

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model

from celery_monitoring import (
    idempotent,
    monitor_task,
    retry_with_exponential_backoff,
    with_dead_letter_queue,
    with_timeout,
)
from future_skills.models import TrainingRun
from future_skills.services.training_service import (
    DataLoadError,
    ModelTrainer,
    TrainingError,
)

logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task(bind=True, name="future_skills.train_model")
@monitor_task(track_memory=True, track_cpu=True)
@with_timeout(soft_timeout=1500, hard_timeout=1800)  # 25/30 minute limits
@with_dead_letter_queue(max_retries=3)
@retry_with_exponential_backoff(max_retries=3, base_delay=120, max_delay=1800)
def train_model_task(self, training_run_id, dataset_path, test_split, hyperparameters):
    """
    Asynchronous task to train a machine learning model.

    This task runs in the background via Celery, allowing the API to return
    immediately. It handles the complete training lifecycle:
    1. Load and validate dataset
    2. Train RandomForest model
    3. Evaluate model performance
    4. Save trained model to disk
    5. Update TrainingRun record with results or errors

    Enhanced with:
    - Exponential backoff retry (3 retries, 2-30 min delays)
    - Dead letter queue for permanent failures
    - Comprehensive monitoring (memory, CPU, execution time)
    - Timeout protection (25 min soft, 30 min hard)

    Args:
        self: Celery task instance (bound task)
        training_run_id (int): Primary key of the TrainingRun record to update
        dataset_path (str): Path to the CSV dataset file
        test_split (float): Proportion of data to use for testing (0.0-1.0)
        hyperparameters (dict): Model hyperparameters (n_estimators, max_depth, etc.)

    Returns:
        dict: Training results with status, metrics, and model information

    Raises:
        DataLoadError: If dataset cannot be loaded or validated
        TrainingError: If model training fails
        Exception: For unexpected errors during training

    Example:
        # Dispatch task asynchronously
        result = train_model_task.delay(
            training_run_id=1,
            dataset_path=str(settings.ML_DATASETS_DIR / "dataset.csv"),
            test_split=0.2,
            hyperparameters={"n_estimators": 100, "max_depth": 10}
        )

        # Check task status later
        if result.ready():
            metrics = result.get()

    Task Properties:
        - bind=True: Task receives self reference for status updates
        - name: Explicit task name for easy identification in logs
        - max_retries: 3 with exponential backoff
        - time_limit: 30 minutes hard, 25 minutes soft
        - monitoring: Memory, CPU, Prometheus metrics
        - resilience: Dead letter queue, circuit breaker ready
    """
    logger.info(
        f"[CELERY] Starting async training task for TrainingRun ID={training_run_id}"
    )

    # Retrieve the TrainingRun object
    try:
        training_run = TrainingRun.objects.get(pk=training_run_id)
    except TrainingRun.DoesNotExist:
        error_msg = f"TrainingRun with ID={training_run_id} does not exist"
        logger.error(f"[CELERY] {error_msg}")
        raise ValueError(error_msg)

    # Update task state to show progress
    self.update_state(
        state="PROGRESS",
        meta={"stage": "initializing", "training_run_id": training_run_id},
    )

    try:
        # === STEP 1: Initialize ModelTrainer ===
        logger.info(
            f"[CELERY] Initializing ModelTrainer for {training_run.model_version}"
        )
        trainer = ModelTrainer(
            dataset_path=dataset_path, test_split=test_split, random_state=42
        )

        # === STEP 2: Load and validate data ===
        self.update_state(
            state="PROGRESS",
            meta={"stage": "loading_data", "training_run_id": training_run_id},
        )
        logger.info("[CELERY] Loading dataset...")
        trainer.load_data()
        logger.info(
            f"[CELERY] Data loaded: {len(trainer.X_train)} train samples, "
            f"{len(trainer.X_test)} test samples"
        )

        # === STEP 3: Train model ===
        self.update_state(
            state="PROGRESS",
            meta={"stage": "training", "training_run_id": training_run_id},
        )
        logger.info(f"[CELERY] Training model with hyperparameters: {hyperparameters}")
        metrics = trainer.train(**hyperparameters)
        logger.info(
            f"[CELERY] Training completed: accuracy={metrics['accuracy']:.4f}, "
            f"duration={metrics['training_duration_seconds']:.2f}s"
        )

        # === STEP 4: Evaluate model ===
        self.update_state(
            state="PROGRESS",
            meta={"stage": "evaluating", "training_run_id": training_run_id},
        )
        evaluation_metrics = trainer.evaluate()
        logger.info(
            f"[CELERY] Evaluation: accuracy={evaluation_metrics['accuracy']:.4f}, "
            f"f1={evaluation_metrics['f1_score']:.4f}"
        )

        # === STEP 5: Save model to disk ===
        self.update_state(
            state="PROGRESS",
            meta={"stage": "saving_model", "training_run_id": training_run_id},
        )
        model_path = settings.ML_MODELS_DIR / f"{training_run.model_version}.pkl"
        model_path_str = str(model_path)
        model_size = trainer.save_model(model_path_str)
        logger.info(f"[CELERY] Model saved: {model_path} ({model_size:,} bytes)")

        # === STEP 6: Update TrainingRun with success ===
        self.update_state(
            state="PROGRESS",
            meta={"stage": "updating_database", "training_run_id": training_run_id},
        )

        training_run.status = "COMPLETED"
        training_run.model_path = model_path_str
        training_run.accuracy = evaluation_metrics["accuracy"]
        training_run.precision = evaluation_metrics["precision"]
        training_run.recall = evaluation_metrics["recall"]
        training_run.f1_score = evaluation_metrics["f1_score"]
        training_run.training_duration_seconds = metrics["training_duration_seconds"]
        training_run.total_samples = evaluation_metrics["total_samples"]
        training_run.per_class_metrics = evaluation_metrics.get("per_class_metrics", {})
        training_run.features_used = evaluation_metrics.get("features_used", [])
        training_run.save()

        logger.info(
            f"[CELERY] ✅ Training successful for {training_run.model_version}: "
            f"accuracy={training_run.accuracy:.4f}"
        )

        # Return results
        result = {
            "status": "COMPLETED",
            "training_run_id": training_run_id,
            "model_version": training_run.model_version,
            "accuracy": training_run.accuracy,
            "f1_score": training_run.f1_score,
            "training_duration_seconds": training_run.training_duration_seconds,
            "model_path": model_path_str,
            "message": "Training completed successfully",
        }

        return result

    except DataLoadError as e:
        # Data loading or validation error
        error_message = f"Data loading failed: {str(e)}"
        logger.error(f"[CELERY] ❌ {error_message}")

        training_run.status = "FAILED"
        training_run.error_message = error_message
        training_run.save()

        # Update task state
        self.update_state(
            state="FAILURE",
            meta={"error": error_message, "training_run_id": training_run_id},
        )

        # Re-raise to mark task as failed in Celery
        raise

    except TrainingError as e:
        # Model training error
        error_message = f"Training failed: {str(e)}"
        logger.error(f"[CELERY] ❌ {error_message}")

        training_run.status = "FAILED"
        training_run.error_message = error_message
        training_run.save()

        self.update_state(
            state="FAILURE",
            meta={"error": error_message, "training_run_id": training_run_id},
        )

        raise

    except Exception as e:
        # Unexpected error
        error_message = f"Unexpected error during training: {str(e)}"
        logger.error(f"[CELERY] ❌ {error_message}", exc_info=True)

        training_run.status = "FAILED"
        training_run.error_message = error_message
        training_run.save()

        self.update_state(
            state="FAILURE",
            meta={"error": error_message, "training_run_id": training_run_id},
        )

        raise


@shared_task(name="future_skills.cleanup_old_models")
@monitor_task(track_memory=False, track_cpu=False)
@idempotent(timeout=3600)  # Prevent duplicate runs within 1 hour
@retry_with_exponential_backoff(max_retries=2, base_delay=300)
def cleanup_old_models_task(days_to_keep=30):
    """
    Periodic task to clean up old model files and training runs.

    This task can be scheduled with Celery Beat to run periodically
    (e.g., daily or weekly) to prevent disk space issues.

    Enhanced with:
    - Idempotency (prevents duplicate runs within 1 hour)
    - Retry with exponential backoff (2 retries, 5 min delays)
    - Basic monitoring (no resource tracking for lightweight task)

    Args:
        days_to_keep (int): Keep models from the last N days (default: 30)

    Returns:
        dict: Cleanup statistics

    Example Celery Beat schedule (in settings.py):
        CELERY_BEAT_SCHEDULE = {
            'cleanup-old-models': {
                'task': 'future_skills.cleanup_old_models',
                'schedule': crontab(hour=2, minute=0),  # Run at 2 AM daily
                'kwargs': {'days_to_keep': 30}
            }
        }
    """
    import os
    from datetime import timedelta

    from django.utils import timezone

    logger.info(f"[CELERY] Starting cleanup task (keeping last {days_to_keep} days)")

    cutoff_date = timezone.now() - timedelta(days=days_to_keep)

    # Find old training runs
    old_runs = TrainingRun.objects.filter(
        run_date__lt=cutoff_date, status__in=["COMPLETED", "FAILED"]
    )

    deleted_files = 0
    total_size_freed = 0

    for run in old_runs:
        if run.model_path and os.path.exists(run.model_path):
            try:
                file_size = os.path.getsize(run.model_path)
                os.remove(run.model_path)
                deleted_files += 1
                total_size_freed += file_size
                logger.info(f"[CELERY] Deleted model: {run.model_path}")
            except Exception as e:
                logger.error(f"[CELERY] Failed to delete {run.model_path}: {e}")

    # Optionally delete the TrainingRun records too
    deleted_count = old_runs.count()
    # old_runs.delete()  # Uncomment to delete records

    logger.info(
        f"[CELERY] Cleanup complete: {deleted_files} files deleted, "
        f"{total_size_freed / 1024 / 1024:.2f} MB freed"
    )

    return {
        "deleted_files": deleted_files,
        "total_size_freed_mb": total_size_freed / 1024 / 1024,
        "old_runs_count": deleted_count,
        "cutoff_date": cutoff_date.isoformat(),
    }
