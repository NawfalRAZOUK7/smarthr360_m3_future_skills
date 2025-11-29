"""
Logging and Monitoring Middleware
SmartHR360 Future Skills Platform

Provides middleware for request/response logging, performance tracking,
and correlation ID management.
"""

import time
import uuid
from typing import Callable

from django.http import HttpRequest, HttpResponse
from django.utils.deprecation import MiddlewareMixin

from config.logging_config import get_logger
from config.apm_config import set_user_context, set_custom_context


# ============================================================================
# REQUEST LOGGING MIDDLEWARE
# ============================================================================

class RequestLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log all HTTP requests and responses.
    Captures request details, response status, and timing information.
    """

    def __init__(self, get_response: Callable):
        """Initialize middleware."""
        self.get_response = get_response
        self.logger = get_logger('django.request')

    def process_request(self, request: HttpRequest) -> None:
        """Process incoming request."""
        # Store start time
        request._start_time = time.time()

        # Log request
        self.logger.info(
            'request_started',
            method=request.method,
            path=request.path,
            query_params=dict(request.GET),
            remote_addr=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            correlation_id=getattr(request, 'correlation_id', None),
        )

    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """Process outgoing response."""
        # Calculate duration
        duration = time.time() - getattr(request, '_start_time', time.time())

        # Log response
        self.logger.info(
            'request_completed',
            method=request.method,
            path=request.path,
            status_code=response.status_code,
            duration_seconds=round(duration, 3),
            correlation_id=getattr(request, 'correlation_id', None),
        )

        return response

    def process_exception(self, request: HttpRequest, exception: Exception) -> None:
        """Process exception during request handling."""
        duration = time.time() - getattr(request, '_start_time', time.time())

        self.logger.error(
            'request_exception',
            method=request.method,
            path=request.path,
            duration_seconds=round(duration, 3),
            exception=str(exception),
            correlation_id=getattr(request, 'correlation_id', None),
            exc_info=True,
        )

    @staticmethod
    def get_client_ip(request: HttpRequest) -> str:
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


# ============================================================================
# CORRELATION ID MIDDLEWARE
# ============================================================================

class CorrelationIdMiddleware:
    """
    Middleware to add correlation ID to requests for distributed tracing.
    Generates a unique ID for each request or uses existing from header.
    
    Uses modern Django middleware pattern with sync_capable/async_capable.
    """

    CORRELATION_ID_HEADER = 'X-Correlation-ID'
    sync_capable = True
    async_capable = False

    def __init__(self, get_response: Callable):
        """Initialize middleware."""
        self.get_response = get_response
        self.logger = get_logger(__name__)

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Process request and response."""
        # Get correlation ID from header or generate new one
        correlation_id = request.META.get(
            f'HTTP_{self.CORRELATION_ID_HEADER.upper().replace("-", "_")}',
            str(uuid.uuid4())
        )

        # Store on request
        request.correlation_id = correlation_id

        # Bind to structlog context
        import structlog
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)

        # Get response
        response = self.get_response(request)

        # Add correlation ID to response headers
        response[self.CORRELATION_ID_HEADER] = correlation_id

        # Clear structlog context
        structlog.contextvars.clear_contextvars()

        return response


# ============================================================================        return response


# ============================================================================
# PERFORMANCE MONITORING MIDDLEWARE
# ============================================================================

class PerformanceMonitoringMiddleware(MiddlewareMixin):
    """
    Middleware to monitor and log performance metrics.
    Tracks slow requests and database query counts.
    """

    SLOW_REQUEST_THRESHOLD = 1.0  # seconds

    def __init__(self, get_response: Callable):
        """Initialize middleware."""
        self.get_response = get_response
        self.logger = get_logger('performance')

    def process_request(self, request: HttpRequest) -> None:
        """Process incoming request."""
        from django.db import connection

        # Store start time and query count
        request._perf_start_time = time.time()
        request._perf_query_count = len(connection.queries)

    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """Process outgoing response."""
        from django.db import connection

        # Calculate metrics
        duration = time.time() - getattr(request, '_perf_start_time', time.time())
        query_count = len(connection.queries) - getattr(request, '_perf_query_count', 0)

        # Log if slow request
        if duration > self.SLOW_REQUEST_THRESHOLD:
            self.logger.warning(
                'slow_request',
                method=request.method,
                path=request.path,
                duration_seconds=round(duration, 3),
                query_count=query_count,
                status_code=response.status_code,
                correlation_id=getattr(request, 'correlation_id', None),
            )

        # Log performance metrics
        self.logger.info(
            'request_performance',
            method=request.method,
            path=request.path,
            duration_seconds=round(duration, 3),
            query_count=query_count,
            status_code=response.status_code,
            correlation_id=getattr(request, 'correlation_id', None),
        )

        # Add performance headers
        response['X-Response-Time'] = f'{duration:.3f}s'
        response['X-Query-Count'] = str(query_count)

        return response


# ============================================================================
# APM CONTEXT MIDDLEWARE
# ============================================================================

class APMContextMiddleware(MiddlewareMixin):
    """
    Middleware to add user and custom context to APM tools.
    Sets user information and request context for better monitoring.
    """

    def __init__(self, get_response: Callable):
        """Initialize middleware."""
        self.get_response = get_response

    def process_request(self, request: HttpRequest) -> None:
        """Process incoming request."""
        # Set user context if authenticated
        if hasattr(request, 'user') and request.user.is_authenticated:
            set_user_context(
                user_id=request.user.id,
                username=request.user.username,
                email=request.user.email,
                is_staff=request.user.is_staff,
                is_superuser=request.user.is_superuser,
            )

        # Set custom context
        set_custom_context('request', {
            'method': request.method,
            'path': request.path,
            'correlation_id': getattr(request, 'correlation_id', None),
        })


# ============================================================================
# ERROR TRACKING MIDDLEWARE
# ============================================================================

class ErrorTrackingMiddleware(MiddlewareMixin):
    """
    Middleware to capture and track errors.
    Sends errors to APM tools with full context.
    """

    def __init__(self, get_response: Callable):
        """Initialize middleware."""
        self.get_response = get_response
        self.logger = get_logger('django.request')

    def process_exception(self, request: HttpRequest, exception: Exception) -> None:
        """Process exception during request handling."""
        from config.apm_config import capture_exception

        # Build context
        context = {
            'request': {
                'method': request.method,
                'path': request.path,
                'query_params': dict(request.GET),
                'correlation_id': getattr(request, 'correlation_id', None),
            }
        }

        # Add user context if available
        if hasattr(request, 'user') and request.user.is_authenticated:
            context['user'] = {
                'id': request.user.id,
                'username': request.user.username,
                'email': request.user.email,
            }

        # Capture exception
        capture_exception(exception, **context)

        # Log error
        self.logger.error(
            'request_error',
            method=request.method,
            path=request.path,
            exception_type=type(exception).__name__,
            exception_message=str(exception),
            correlation_id=getattr(request, 'correlation_id', None),
            exc_info=True,
        )


# ============================================================================
# SQL QUERY LOGGING MIDDLEWARE (Development Only)
# ============================================================================

class SQLQueryLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log SQL queries (for development/debugging).
    WARNING: Only enable in development, not production!
    """

    def __init__(self, get_response: Callable):
        """Initialize middleware."""
        self.get_response = get_response
        self.logger = get_logger('django.db.backends')

    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """Process outgoing response."""
        from django.conf import settings
        from django.db import connection

        # Only log in debug mode
        if settings.DEBUG:
            queries = connection.queries

            if queries:
                self.logger.debug(
                    'sql_queries',
                    path=request.path,
                    query_count=len(queries),
                    total_time=sum(float(q['time']) for q in queries),
                    queries=[
                        {
                            'sql': q['sql'][:200],  # Truncate long queries
                            'time': q['time'],
                        }
                        for q in queries[-10:]  # Last 10 queries
                    ],
                )

        return response


# ============================================================================
# CUSTOM LOG CONTEXT MIDDLEWARE
# ============================================================================

class CustomLogContextMiddleware(MiddlewareMixin):
    """
    Middleware to add custom context to all log messages during request.
    Uses structlog's contextvars to bind context for the request lifecycle.
    """

    def __init__(self, get_response: Callable):
        """Initialize middleware."""
        self.get_response = get_response

    def process_request(self, request: HttpRequest) -> None:
        """Process incoming request."""
        import structlog

        # Bind request context
        structlog.contextvars.bind_contextvars(
            request_id=getattr(request, 'correlation_id', None),
            method=request.method,
            path=request.path,
            user_id=request.user.id if hasattr(request, 'user') and request.user.is_authenticated else None,
        )

    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """Process outgoing response."""
        import structlog

        # Clear context
        structlog.contextvars.clear_contextvars()

        return response
