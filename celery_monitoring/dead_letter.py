"""
Dead Letter Queue implementation for Celery tasks.

Stores failed tasks for manual inspection and reprocessing.
Tasks that exceed max retries are sent here instead of being lost.
"""

import logging
import json
from datetime import datetime
from typing import Any, Dict, Optional
from django.db import models
from django.utils import timezone

logger = logging.getLogger(__name__)


class DeadLetterTask(models.Model):
    """
    Model to store permanently failed tasks in the dead letter queue.

    These tasks can be inspected, debugged, and manually reprocessed.
    """

    task_id = models.CharField(max_length=255, unique=True, db_index=True)
    task_name = models.CharField(max_length=255, db_index=True)

    # Task arguments
    args = models.JSONField(default=list, help_text="Positional arguments")
    kwargs = models.JSONField(default=dict, help_text="Keyword arguments")

    # Failure information
    exception_type = models.CharField(max_length=255)
    exception_message = models.TextField()
    exception_traceback = models.TextField(blank=True)

    # Metadata
    retries = models.IntegerField(default=0)
    failed_at = models.DateTimeField(default=timezone.now, db_index=True)

    # Reprocessing
    reprocessed = models.BooleanField(default=False, db_index=True)
    reprocessed_at = models.DateTimeField(null=True, blank=True)
    reprocessing_result = models.TextField(blank=True)

    # Additional context
    worker_name = models.CharField(max_length=255, blank=True)
    queue_name = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "celery_dead_letter_queue"
        ordering = ["-failed_at"]
        indexes = [
            models.Index(fields=["task_name", "failed_at"]),
            models.Index(fields=["reprocessed", "failed_at"]),
        ]

    def __str__(self):
        return f"{self.task_name} ({self.task_id}) - {self.failed_at}"

    def reprocess(self) -> Dict[str, Any]:
        """
        Attempt to reprocess this failed task.

        Returns:
            dict: Reprocessing result with status and details
        """
        from celery import current_app

        try:
            # Get task function
            task = current_app.tasks.get(self.task_name)
            if not task:
                raise ValueError(f"Task {self.task_name} not found")

            # Execute task synchronously
            logger.info(f"Reprocessing dead letter task: {self.task_id}")
            result = task.apply(args=self.args, kwargs=self.kwargs)

            # Mark as reprocessed
            self.reprocessed = True
            self.reprocessed_at = timezone.now()
            self.reprocessing_result = json.dumps(
                {
                    "status": "success",
                    "result": str(result.result) if hasattr(result, "result") else None,
                }
            )
            self.save()

            logger.info(f"Successfully reprocessed task: {self.task_id}")

            return {
                "status": "success",
                "task_id": self.task_id,
                "result": result.result if hasattr(result, "result") else None,
            }

        except Exception as e:
            logger.error(f"Failed to reprocess task {self.task_id}: {e}")

            self.reprocessing_result = json.dumps({"status": "failed", "error": str(e)})
            self.save()

            return {"status": "failed", "task_id": self.task_id, "error": str(e)}


def send_to_dead_letter_queue(
    task_name: str,
    task_id: str,
    args: tuple,
    kwargs: dict,
    exception: Exception,
    retries: int,
    worker_name: str = "",
    queue_name: str = "",
) -> DeadLetterTask:
    """
    Send a failed task to the dead letter queue.

    Args:
        task_name: Name of the failed task
        task_id: Unique task ID
        args: Task positional arguments
        kwargs: Task keyword arguments
        exception: Exception that caused the failure
        retries: Number of retry attempts made
        worker_name: Name of the worker that executed the task
        queue_name: Name of the queue the task was on

    Returns:
        DeadLetterTask: Created dead letter task record
    """
    import traceback

    # Get exception details
    exception_type = type(exception).__name__
    exception_message = str(exception)
    exception_traceback = traceback.format_exc()

    # Create dead letter task
    dead_letter_task = DeadLetterTask.objects.create(
        task_id=task_id,
        task_name=task_name,
        args=list(args),
        kwargs=kwargs,
        exception_type=exception_type,
        exception_message=exception_message,
        exception_traceback=exception_traceback,
        retries=retries,
        worker_name=worker_name,
        queue_name=queue_name,
    )

    logger.info(
        f"Sent task to dead letter queue: {task_name} ({task_id}), "
        f"exception: {exception_type}"
    )

    return dead_letter_task


def reprocess_dead_letter_tasks(
    task_name: Optional[str] = None, limit: int = 10
) -> Dict[str, Any]:
    """
    Bulk reprocess dead letter tasks.

    Args:
        task_name: Optional filter by task name
        limit: Maximum number of tasks to reprocess

    Returns:
        dict: Reprocessing statistics
    """
    query = DeadLetterTask.objects.filter(reprocessed=False)

    if task_name:
        query = query.filter(task_name=task_name)

    tasks = query[:limit]

    results = {"total": len(tasks), "success": 0, "failed": 0, "errors": []}

    for task in tasks:
        result = task.reprocess()
        if result["status"] == "success":
            results["success"] += 1
        else:
            results["failed"] += 1
            results["errors"].append(
                {"task_id": task.task_id, "error": result.get("error")}
            )

    return results


def cleanup_old_dead_letter_tasks(days: int = 30) -> int:
    """
    Clean up old reprocessed dead letter tasks.

    Args:
        days: Delete tasks older than this many days

    Returns:
        int: Number of tasks deleted
    """
    from datetime import timedelta

    cutoff_date = timezone.now() - timedelta(days=days)

    deleted_count, _ = DeadLetterTask.objects.filter(
        reprocessed=True, reprocessed_at__lt=cutoff_date
    ).delete()

    logger.info(f"Cleaned up {deleted_count} old dead letter tasks")

    return deleted_count
