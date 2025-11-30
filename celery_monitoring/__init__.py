"""
Celery retry strategies and decorators for robust task execution.

This module provides advanced retry patterns, circuit breakers, and
resilience strategies for Celery tasks to handle failures gracefully.

Features:
- Exponential backoff with jitter
- Circuit breaker pattern
- Dead letter queue for failed tasks
- Custom retry policies
- Task timeout handling
- Rate limiting

Usage:
    from celery_monitoring import (
        retry_with_exponential_backoff,
        with_circuit_breaker,
        with_dead_letter_queue,
        monitor_task
    )

    @shared_task
    @retry_with_exponential_backoff(max_retries=5)
    def my_task():
        # Task implementation
        pass
"""

__all__ = [
    "retry_with_exponential_backoff",
    "with_circuit_breaker",
    "with_dead_letter_queue",
    "rate_limit",
    "with_timeout",
    "idempotent",
    "with_advanced_retry",
    "monitor_task",
]


def __getattr__(name):
    """Lazy import to avoid registering Prometheus metrics at import time."""
    if name == "monitor_task":
        from celery_monitoring.monitoring import monitor_task

        return monitor_task
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


import functools
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Optional, Tuple, Type

from celery import Task
from celery.exceptions import (
    Ignore,
    Reject,
    Retry,
    SoftTimeLimitExceeded,
    TimeLimitExceeded,
)
from django.core.cache import cache
from django.utils import timezone
from pybreaker import CircuitBreaker, CircuitBreakerError
from tenacity import (
    after_log,
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


# ============================================================================
# RETRY POLICIES
# ============================================================================


class RetryPolicy:
    """Base retry policy configuration."""

    # Default retry settings
    MAX_RETRIES = 3
    RETRY_BACKOFF = True
    RETRY_BACKOFF_MAX = 600  # 10 minutes
    RETRY_JITTER = True

    # Exceptions that should trigger retry
    RETRIABLE_EXCEPTIONS = (
        ConnectionError,
        TimeoutError,
        IOError,
        OSError,
    )

    # Exceptions that should NOT trigger retry
    NON_RETRIABLE_EXCEPTIONS = (
        ValueError,
        TypeError,
        KeyError,
        AttributeError,
    )


class AggressiveRetryPolicy(RetryPolicy):
    """Aggressive retry for critical tasks."""

    MAX_RETRIES = 10
    RETRY_BACKOFF_MAX = 1800  # 30 minutes


class ConservativeRetryPolicy(RetryPolicy):
    """Conservative retry for non-critical tasks."""

    MAX_RETRIES = 2
    RETRY_BACKOFF_MAX = 300  # 5 minutes


# ============================================================================
# EXPONENTIAL BACKOFF DECORATOR
# ============================================================================


def retry_with_exponential_backoff(
    max_retries: int = 3,
    base_delay: int = 60,
    max_delay: int = 3600,
    exponential_base: int = 2,
    jitter: bool = True,
    retriable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
):
    """
    Decorator that adds exponential backoff retry logic to Celery tasks.

    The delay between retries grows exponentially:
    - Retry 1: base_delay * (exponential_base ^ 0) = 60s
    - Retry 2: base_delay * (exponential_base ^ 1) = 120s
    - Retry 3: base_delay * (exponential_base ^ 2) = 240s

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds (caps exponential growth)
        exponential_base: Base for exponential calculation
        jitter: Add random jitter to prevent thundering herd
        retriable_exceptions: Tuple of exceptions that trigger retry

    Example:
        @shared_task
        @retry_with_exponential_backoff(max_retries=5, base_delay=30)
        def fetch_external_api():
            response = requests.get('https://api.example.com')
            return response.json()
    """
    if retriable_exceptions is None:
        retriable_exceptions = RetryPolicy.RETRIABLE_EXCEPTIONS

    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except retriable_exceptions as exc:
                # Calculate retry number
                retry_count = self.request.retries

                if retry_count >= max_retries:
                    logger.error(
                        f"Task {self.name} failed after {max_retries} retries: {exc}"
                    )
                    raise

                # Calculate exponential backoff delay
                delay = min(base_delay * (exponential_base**retry_count), max_delay)

                # Add jitter (random variation ±20%)
                if jitter:
                    import random

                    jitter_range = delay * 0.2
                    delay = delay + random.uniform(-jitter_range, jitter_range)

                logger.warning(
                    f"Task {self.name} failed (attempt {retry_count + 1}/{max_retries}), "
                    f"retrying in {delay:.2f}s: {exc}"
                )

                # Retry with calculated delay
                raise self.retry(exc=exc, countdown=delay, max_retries=max_retries)

        return wrapper

    return decorator


# ============================================================================
# CIRCUIT BREAKER PATTERN
# ============================================================================

# Global circuit breakers for different services
CIRCUIT_BREAKERS = {}


def get_circuit_breaker(
    name: str, fail_max: int = 5, reset_timeout: int = 60
) -> CircuitBreaker:
    """
    Get or create a circuit breaker for a specific service.

    Circuit breaker states:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests blocked immediately
    - HALF_OPEN: Testing if service recovered, allows one request

    Args:
        name: Unique name for the circuit breaker
        fail_max: Number of failures before opening circuit
        reset_timeout: Seconds to wait before attempting to close circuit

    Returns:
        CircuitBreaker instance
    """
    if name not in CIRCUIT_BREAKERS:
        CIRCUIT_BREAKERS[name] = CircuitBreaker(
            fail_max=fail_max,
            reset_timeout=reset_timeout,
            name=name,
            listeners=[_circuit_breaker_listener],
        )
    return CIRCUIT_BREAKERS[name]


def _circuit_breaker_listener(cb, old_state, new_state):
    """Log circuit breaker state changes."""
    logger.warning(
        f"Circuit breaker '{cb.name}' changed state: {old_state} -> {new_state}"
    )


def with_circuit_breaker(name: str, fail_max: int = 5, reset_timeout: int = 60):
    """
    Decorator that adds circuit breaker pattern to Celery tasks.

    Prevents cascading failures by temporarily blocking requests
    to a failing service, giving it time to recover.

    Args:
        name: Unique name for the circuit breaker
        fail_max: Number of failures before opening circuit
        reset_timeout: Seconds to wait before attempting to close circuit

    Example:
        @shared_task
        @with_circuit_breaker('external_api', fail_max=3, reset_timeout=300)
        def call_external_api():
            response = requests.get('https://api.example.com')
            return response.json()
    """

    def decorator(func):
        breaker = get_circuit_breaker(name, fail_max, reset_timeout)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                # Call function through circuit breaker
                return breaker.call(func, *args, **kwargs)
            except CircuitBreakerError as e:
                logger.error(
                    f"Circuit breaker '{name}' is OPEN, blocking call to {func.__name__}"
                )
                # Don't retry, just fail fast
                raise Reject(str(e), requeue=False)

        return wrapper

    return decorator


# ============================================================================
# DEAD LETTER QUEUE
# ============================================================================


def with_dead_letter_queue(
    max_retries: int = 3, dead_letter_queue: str = "dead_letter_queue"
):
    """
    Decorator that sends permanently failed tasks to a dead letter queue.

    After max_retries, instead of losing the task, it's sent to a separate
    queue for manual inspection and reprocessing.

    Args:
        max_retries: Maximum retry attempts before sending to DLQ
        dead_letter_queue: Name of the dead letter queue

    Example:
        @shared_task
        @with_dead_letter_queue(max_retries=5)
        def process_payment(payment_id):
            # Critical operation that shouldn't be lost
            pass
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception as exc:
                retry_count = self.request.retries

                if retry_count >= max_retries:
                    # Send to dead letter queue
                    from celery_monitoring.dead_letter import send_to_dead_letter_queue

                    logger.error(
                        f"Task {self.name} failed permanently after {max_retries} retries, "
                        f"sending to DLQ: {exc}"
                    )

                    send_to_dead_letter_queue(
                        task_name=self.name,
                        task_id=self.request.id,
                        args=args,
                        kwargs=kwargs,
                        exception=exc,
                        retries=retry_count,
                    )

                    # Don't requeue, task is in DLQ
                    raise Ignore()

                # Retry with exponential backoff
                countdown = min(60 * (2**retry_count), 3600)
                raise self.retry(exc=exc, countdown=countdown, max_retries=max_retries)

        return wrapper

    return decorator


# ============================================================================
# RATE LIMITING
# ============================================================================


def rate_limit(calls: int = 10, period: int = 60):
    """
    Decorator that rate limits task execution.

    Useful for tasks that call external APIs with rate limits.

    Args:
        calls: Maximum number of calls allowed
        period: Time period in seconds

    Example:
        @shared_task
        @rate_limit(calls=100, period=60)  # 100 calls per minute
        def call_rate_limited_api():
            pass
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = f"rate_limit:{func.__name__}"

            # Get current call count
            call_count = cache.get(cache_key, 0)

            if call_count >= calls:
                # Rate limit exceeded
                wait_time = cache.ttl(cache_key)
                logger.warning(
                    f"Rate limit exceeded for {func.__name__}, "
                    f"retry in {wait_time}s"
                )
                raise Retry(countdown=wait_time)

            # Increment call count
            if call_count == 0:
                cache.set(cache_key, 1, period)
            else:
                cache.incr(cache_key)

            return func(*args, **kwargs)

        return wrapper

    return decorator


# ============================================================================
# TIMEOUT HANDLING
# ============================================================================


def with_timeout(soft_timeout: int = 300, hard_timeout: int = 600):
    """
    Decorator that adds timeout handling to tasks.

    Args:
        soft_timeout: Soft time limit in seconds (raises SoftTimeLimitExceeded)
        hard_timeout: Hard time limit in seconds (kills task)

    Example:
        @shared_task
        @with_timeout(soft_timeout=600, hard_timeout=900)
        def long_running_task():
            # Task with 10-minute soft limit, 15-minute hard limit
            pass
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            # Set timeouts on task
            self.time_limit = hard_timeout
            self.soft_time_limit = soft_timeout

            try:
                return func(self, *args, **kwargs)
            except SoftTimeLimitExceeded:
                logger.warning(
                    f"Task {self.name} exceeded soft time limit ({soft_timeout}s), "
                    f"attempting graceful shutdown"
                )
                # Attempt to save partial results or cleanup
                raise
            except TimeLimitExceeded:
                logger.error(
                    f"Task {self.name} exceeded hard time limit ({hard_timeout}s), "
                    f"forcefully terminated"
                )
                raise

        return wrapper

    return decorator


# ============================================================================
# IDEMPOTENCY KEY
# ============================================================================


def idempotent(timeout: int = 3600):
    """
    Decorator that makes tasks idempotent using cache-based locking.

    Prevents duplicate execution of the same task within the timeout period.

    Args:
        timeout: Lock timeout in seconds

    Example:
        @shared_task
        @idempotent(timeout=300)  # 5-minute lock
        def send_notification(user_id):
            # Won't send duplicate notifications within 5 minutes
            pass
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate idempotency key from function name and arguments
            import hashlib
            import json

            key_data = {"func": func.__name__, "args": args, "kwargs": kwargs}
            key_hash = hashlib.md5(
                json.dumps(key_data, sort_keys=True).encode()
            ).hexdigest()
            cache_key = f"idempotent:{key_hash}"

            # Check if task already executed
            if cache.get(cache_key):
                logger.info(
                    f"Task {func.__name__} already executed (idempotency key: {key_hash}), "
                    f"skipping"
                )
                return None

            # Execute task
            result = func(*args, **kwargs)

            # Mark as executed
            cache.set(cache_key, True, timeout)

            return result

        return wrapper

    return decorator


# ============================================================================
# COMPOSITE RETRY STRATEGY
# ============================================================================


def with_advanced_retry(
    max_retries: int = 5,
    use_circuit_breaker: bool = True,
    use_dead_letter_queue: bool = True,
    circuit_breaker_name: Optional[str] = None,
    rate_limit_calls: Optional[int] = None,
    rate_limit_period: int = 60,
):
    """
    Composite decorator combining multiple retry strategies.

    Combines exponential backoff, circuit breaker, dead letter queue,
    and optional rate limiting.

    Example:
        @shared_task
        @with_advanced_retry(
            max_retries=5,
            use_circuit_breaker=True,
            circuit_breaker_name='payment_api',
            rate_limit_calls=100
        )
        def process_payment(payment_id):
            # Fully protected task with all retry strategies
            pass
    """

    def decorator(func):
        # Start with base function
        decorated_func = func

        # Add rate limiting if specified
        if rate_limit_calls:
            decorated_func = rate_limit(
                calls=rate_limit_calls, period=rate_limit_period
            )(decorated_func)

        # Add circuit breaker if specified
        if use_circuit_breaker:
            cb_name = circuit_breaker_name or func.__name__
            decorated_func = with_circuit_breaker(cb_name)(decorated_func)

        # Add dead letter queue if specified
        if use_dead_letter_queue:
            decorated_func = with_dead_letter_queue(max_retries=max_retries)(
                decorated_func
            )

        # Add exponential backoff
        decorated_func = retry_with_exponential_backoff(max_retries=max_retries)(
            decorated_func
        )

        return decorated_func

    return decorator
