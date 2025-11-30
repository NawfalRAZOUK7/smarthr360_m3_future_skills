"""
Comprehensive monitoring and metrics for Celery tasks.

Provides Prometheus metrics, task execution tracking, performance monitoring,
and real-time observability for Celery workers and tasks.
"""

import functools
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from celery import signals
from celery.states import FAILURE, RECEIVED, RETRY, STARTED, SUCCESS
from django.db import models
from django.utils import timezone
from prometheus_client import REGISTRY, Counter, Gauge, Histogram, Info, Summary, generate_latest

logger = logging.getLogger(__name__)


# ============================================================================
# PROMETHEUS METRICS
# ============================================================================

# Task execution metrics
TASK_STARTED_COUNTER = Counter(
    "celery_task_started_total", "Total number of tasks started", ["task_name", "queue"]
)

TASK_COMPLETED_COUNTER = Counter(
    "celery_task_completed_total",
    "Total number of tasks completed successfully",
    ["task_name", "queue"],
)

TASK_FAILED_COUNTER = Counter(
    "celery_task_failed_total",
    "Total number of tasks that failed",
    ["task_name", "queue", "exception"],
)

TASK_RETRY_COUNTER = Counter(
    "celery_task_retry_total", "Total number of task retries", ["task_name", "queue"]
)

TASK_DURATION_HISTOGRAM = Histogram(
    "celery_task_duration_seconds",
    "Task execution duration in seconds",
    ["task_name", "queue"],
    buckets=[1, 5, 10, 30, 60, 120, 300, 600, 1800, 3600],
)

TASK_DURATION_SUMMARY = Summary(
    "celery_task_duration_summary",
    "Summary of task execution durations",
    ["task_name", "queue"],
)

# Queue metrics
QUEUE_LENGTH_GAUGE = Gauge(
    "celery_queue_length", "Number of tasks waiting in queue", ["queue"]
)

ACTIVE_TASKS_GAUGE = Gauge(
    "celery_active_tasks", "Number of currently executing tasks", ["worker", "queue"]
)

# Worker metrics
WORKER_ONLINE_GAUGE = Gauge(
    "celery_worker_online", "Worker online status (1=online, 0=offline)", ["worker"]
)

WORKER_POOL_SIZE_GAUGE = Gauge(
    "celery_worker_pool_size",
    "Worker pool size (number of concurrent tasks)",
    ["worker"],
)

# Resource metrics
TASK_MEMORY_USAGE_GAUGE = Gauge(
    "celery_task_memory_mb", "Task memory usage in MB", ["task_name"]
)


# ============================================================================
# TASK EXECUTION TRACKING
# ============================================================================


class TaskExecution(models.Model):
    """
    Track detailed execution information for all Celery tasks.

    Provides comprehensive audit trail and performance analysis.
    """

    task_id = models.CharField(max_length=255, unique=True, db_index=True)
    task_name = models.CharField(max_length=255, db_index=True)

    # Execution timing
    received_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Duration metrics (in seconds)
    queue_time = models.FloatField(
        null=True, blank=True, help_text="Time spent in queue"
    )
    execution_time = models.FloatField(
        null=True, blank=True, help_text="Actual execution time"
    )
    total_time = models.FloatField(
        null=True, blank=True, help_text="Total time from receive to complete"
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ("RECEIVED", "Received"),
            ("STARTED", "Started"),
            ("SUCCESS", "Success"),
            ("FAILURE", "Failure"),
            ("RETRY", "Retry"),
            ("REVOKED", "Revoked"),
        ],
        default="RECEIVED",
        db_index=True,
    )

    # Result and error information
    result = models.JSONField(null=True, blank=True)
    exception_type = models.CharField(max_length=255, blank=True)
    exception_message = models.TextField(blank=True)
    traceback = models.TextField(blank=True)

    # Retry information
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(null=True, blank=True)

    # Worker information
    worker_name = models.CharField(max_length=255, blank=True, db_index=True)
    queue_name = models.CharField(max_length=255, blank=True, db_index=True)

    # Resource usage
    memory_usage_mb = models.FloatField(null=True, blank=True)
    cpu_percent = models.FloatField(null=True, blank=True)

    # Task arguments (for debugging)
    args = models.JSONField(default=list)
    kwargs = models.JSONField(default=dict)

    class Meta:
        db_table = "celery_task_execution"
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["task_name", "status", "started_at"]),
            models.Index(fields=["worker_name", "started_at"]),
            models.Index(fields=["queue_name", "started_at"]),
            models.Index(fields=["status", "started_at"]),
        ]

    def __str__(self):
        return f"{self.task_name} ({self.task_id}) - {self.status}"

    @property
    def duration_display(self) -> str:
        """Human-readable duration."""
        if not self.execution_time:
            return "N/A"

        if self.execution_time < 60:
            return f"{self.execution_time:.2f}s"
        elif self.execution_time < 3600:
            return f"{self.execution_time / 60:.2f}m"
        else:
            return f"{self.execution_time / 3600:.2f}h"

    def calculate_metrics(self):
        """Calculate timing metrics."""
        if self.received_at and self.started_at:
            self.queue_time = (self.started_at - self.received_at).total_seconds()

        if self.started_at and self.completed_at:
            self.execution_time = (self.completed_at - self.started_at).total_seconds()

        if self.received_at and self.completed_at:
            self.total_time = (self.completed_at - self.received_at).total_seconds()


# ============================================================================
# SIGNAL HANDLERS FOR AUTOMATIC TRACKING
# ============================================================================


@signals.task_received.connect
def task_received_handler(sender=None, request=None, **kwargs):
    """Track when task is received by worker."""
    TaskExecution.objects.update_or_create(
        task_id=request.id,
        defaults={
            "task_name": request.task,
            "received_at": timezone.now(),
            "status": "RECEIVED",
            "worker_name": request.hostname,
            "queue_name": (
                request.delivery_info.get("routing_key", "")
                if request.delivery_info
                else ""
            ),
            "args": list(request.args or []),
            "kwargs": dict(request.kwargs or {}),
        },
    )


@signals.task_prerun.connect
def task_prerun_handler(
    sender=None, task_id=None, task=None, args=None, kwargs=None, **extra
):
    """Track when task execution starts."""
    execution, created = TaskExecution.objects.update_or_create(
        task_id=task_id,
        defaults={
            "task_name": task.name,
            "started_at": timezone.now(),
            "status": "STARTED",
        },
    )

    # Update Prometheus metrics
    queue = execution.queue_name or "default"
    TASK_STARTED_COUNTER.labels(task_name=task.name, queue=queue).inc()
    ACTIVE_TASKS_GAUGE.labels(worker=execution.worker_name, queue=queue).inc()


@signals.task_postrun.connect
def task_postrun_handler(
    sender=None,
    task_id=None,
    task=None,
    args=None,
    kwargs=None,
    retval=None,
    state=None,
    **extra,
):
    """Track task completion."""
    try:
        execution = TaskExecution.objects.get(task_id=task_id)
        execution.completed_at = timezone.now()
        execution.status = state

        # Store result (truncate if too large)
        if retval is not None:
            result_str = str(retval)
            if len(result_str) > 10000:
                result_str = result_str[:10000] + "... (truncated)"
            execution.result = {"value": result_str}

        # Calculate metrics
        execution.calculate_metrics()
        execution.save()

        # Update Prometheus metrics
        queue = execution.queue_name or "default"
        ACTIVE_TASKS_GAUGE.labels(worker=execution.worker_name, queue=queue).dec()

        if state == SUCCESS:
            TASK_COMPLETED_COUNTER.labels(task_name=task.name, queue=queue).inc()
            if execution.execution_time:
                TASK_DURATION_HISTOGRAM.labels(
                    task_name=task.name, queue=queue
                ).observe(execution.execution_time)
                TASK_DURATION_SUMMARY.labels(task_name=task.name, queue=queue).observe(
                    execution.execution_time
                )

    except TaskExecution.DoesNotExist:
        logger.warning(f"TaskExecution not found for task_id: {task_id}")


@signals.task_failure.connect
def task_failure_handler(
    sender=None,
    task_id=None,
    exception=None,
    args=None,
    kwargs=None,
    traceback=None,
    einfo=None,
    **extra,
):
    """Track task failures."""
    import traceback as tb

    try:
        execution = TaskExecution.objects.get(task_id=task_id)
        execution.completed_at = timezone.now()
        execution.status = "FAILURE"
        execution.exception_type = type(exception).__name__
        execution.exception_message = str(exception)
        execution.traceback = str(einfo) if einfo else tb.format_exc()
        execution.calculate_metrics()
        execution.save()

        # Update Prometheus metrics
        queue = execution.queue_name or "default"
        TASK_FAILED_COUNTER.labels(
            task_name=sender.name, queue=queue, exception=type(exception).__name__
        ).inc()
        ACTIVE_TASKS_GAUGE.labels(worker=execution.worker_name, queue=queue).dec()

    except TaskExecution.DoesNotExist:
        logger.warning(f"TaskExecution not found for task_id: {task_id}")


@signals.task_retry.connect
def task_retry_handler(sender=None, task_id=None, reason=None, einfo=None, **kwargs):
    """Track task retries."""
    try:
        execution = TaskExecution.objects.get(task_id=task_id)
        execution.retry_count += 1
        execution.status = "RETRY"
        execution.exception_message = str(reason)
        execution.save()

        # Update Prometheus metrics
        queue = execution.queue_name or "default"
        TASK_RETRY_COUNTER.labels(task_name=sender.name, queue=queue).inc()

    except TaskExecution.DoesNotExist:
        logger.warning(f"TaskExecution not found for task_id: {task_id}")


# ============================================================================
# MONITORING DECORATOR
# ============================================================================


def monitor_task(track_memory: bool = False, track_cpu: bool = False):
    """
    Decorator to add comprehensive monitoring to Celery tasks.

    Args:
        track_memory: Track memory usage during execution
        track_cpu: Track CPU usage during execution

    Example:
        @shared_task
        @monitor_task(track_memory=True, track_cpu=True)
        def my_task():
            # Task will be automatically monitored
            pass
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()

            # Track resource usage if requested
            memory_before = None
            cpu_before = None

            if track_memory or track_cpu:
                import psutil

                process = psutil.Process()

                if track_memory:
                    memory_before = process.memory_info().rss / 1024 / 1024  # MB

                if track_cpu:
                    cpu_before = process.cpu_percent(interval=0.1)

            try:
                # Execute task
                result = func(*args, **kwargs)

                # Calculate execution time
                execution_time = time.time() - start_time

                # Track resource usage
                if track_memory and memory_before is not None:
                    memory_after = process.memory_info().rss / 1024 / 1024
                    memory_used = memory_after - memory_before
                    TASK_MEMORY_USAGE_GAUGE.labels(task_name=func.__name__).set(
                        memory_used
                    )

                logger.info(f"Task {func.__name__} completed in {execution_time:.2f}s")

                return result

            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(
                    f"Task {func.__name__} failed after {execution_time:.2f}s: {e}"
                )
                raise

        return wrapper

    return decorator


# ============================================================================
# PERFORMANCE ANALYSIS
# ============================================================================


def get_task_performance_stats(
    task_name: Optional[str] = None, hours: int = 24
) -> Dict[str, Any]:
    """
    Get performance statistics for tasks.

    Args:
        task_name: Optional filter by task name
        hours: Look back this many hours

    Returns:
        dict: Performance statistics
    """
    from django.db.models import Avg, Count, Max, Min

    cutoff_time = timezone.now() - timedelta(hours=hours)

    query = TaskExecution.objects.filter(started_at__gte=cutoff_time)
    if task_name:
        query = query.filter(task_name=task_name)

    stats = query.aggregate(
        total_tasks=Count("id"),
        avg_execution_time=Avg("execution_time"),
        min_execution_time=Min("execution_time"),
        max_execution_time=Max("execution_time"),
        avg_queue_time=Avg("queue_time"),
    )

    # Count by status
    status_counts = {}
    for status in ["SUCCESS", "FAILURE", "RETRY"]:
        count = query.filter(status=status).count()
        status_counts[status.lower()] = count

    # Calculate success rate
    total = stats["total_tasks"] or 0
    success = status_counts.get("success", 0)
    success_rate = (success / total * 100) if total > 0 else 0

    return {
        "period_hours": hours,
        "task_name": task_name or "all",
        "total_tasks": total,
        "success_rate": round(success_rate, 2),
        "status_counts": status_counts,
        "avg_execution_time_seconds": round(stats["avg_execution_time"] or 0, 2),
        "min_execution_time_seconds": round(stats["min_execution_time"] or 0, 2),
        "max_execution_time_seconds": round(stats["max_execution_time"] or 0, 2),
        "avg_queue_time_seconds": round(stats["avg_queue_time"] or 0, 2),
    }


def get_slowest_tasks(limit: int = 10, hours: int = 24) -> List[Dict[str, Any]]:
    """
    Get slowest task executions.

    Args:
        limit: Number of tasks to return
        hours: Look back this many hours

    Returns:
        list: Slowest tasks with details
    """
    cutoff_time = timezone.now() - timedelta(hours=hours)

    tasks = TaskExecution.objects.filter(
        started_at__gte=cutoff_time, execution_time__isnull=False
    ).order_by("-execution_time")[:limit]

    return [
        {
            "task_id": task.task_id,
            "task_name": task.task_name,
            "execution_time": round(task.execution_time, 2),
            "started_at": task.started_at.isoformat(),
            "status": task.status,
            "worker": task.worker_name,
        }
        for task in tasks
    ]


def cleanup_old_task_executions(days: int = 7) -> int:
    """
    Clean up old task execution records.

    Args:
        days: Delete records older than this many days

    Returns:
        int: Number of records deleted
    """
    cutoff_date = timezone.now() - timedelta(days=days)

    deleted_count, _ = TaskExecution.objects.filter(started_at__lt=cutoff_date).delete()

    logger.info(f"Cleaned up {deleted_count} old task execution records")

    return deleted_count
