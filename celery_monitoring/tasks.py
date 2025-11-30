"""
Additional Celery tasks for monitoring and maintenance.

These tasks handle cleanup and maintenance of monitoring data.
"""

import logging
from celery import shared_task
from celery_monitoring.monitoring import cleanup_old_task_executions
from celery_monitoring.dead_letter import cleanup_old_dead_letter_tasks

logger = logging.getLogger(__name__)


@shared_task(name="celery_monitoring.cleanup_task_executions")
def cleanup_task_executions_task(days: int = 7):
    """
    Periodic task to cleanup old task execution records.

    Args:
        days: Delete records older than this many days

    Returns:
        dict: Cleanup statistics
    """
    logger.info(f"Starting cleanup of task executions older than {days} days")

    deleted_count = cleanup_old_task_executions(days=days)

    result = {"deleted_count": deleted_count, "days": days, "status": "completed"}

    logger.info(f"Cleanup completed: {deleted_count} task executions deleted")

    return result


@shared_task(name="celery_monitoring.cleanup_dead_letter")
def cleanup_dead_letter_task(days: int = 30):
    """
    Periodic task to cleanup old dead letter queue tasks.

    Args:
        days: Delete reprocessed tasks older than this many days

    Returns:
        dict: Cleanup statistics
    """
    logger.info(f"Starting cleanup of dead letter tasks older than {days} days")

    deleted_count = cleanup_old_dead_letter_tasks(days=days)

    result = {"deleted_count": deleted_count, "days": days, "status": "completed"}

    logger.info(f"Cleanup completed: {deleted_count} dead letter tasks deleted")

    return result
