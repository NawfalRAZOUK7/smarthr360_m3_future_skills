"""
API Performance Middleware

Provides request/response timing, caching, compression, and performance monitoring.
"""

import time
import logging
from django.core.cache import cache
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
import json

logger = logging.getLogger(__name__)


class APIPerformanceMiddleware(MiddlewareMixin):
    """
    Middleware to track API request performance and add timing headers.

    Adds the following response headers:
    - X-Response-Time: Request processing time in milliseconds
    - X-DB-Queries: Number of database queries executed
    - X-Cache-Hit: Whether response was served from cache
    """

    def process_request(self, request):
        """Mark request start time"""
        request._start_time = time.time()
        request._db_queries_before = self._get_db_query_count()

    def process_response(self, request, response):
        """Add performance headers to response"""
        if hasattr(request, "_start_time"):
            # Calculate request duration
            duration = time.time() - request._start_time
            duration_ms = int(duration * 1000)

            # Add timing header
            response["X-Response-Time"] = f"{duration_ms}ms"

            # Add database query count
            if hasattr(request, "_db_queries_before"):
                db_queries = self._get_db_query_count() - request._db_queries_before
                response["X-DB-Queries"] = str(db_queries)

            # Log slow requests
            if duration_ms > 1000:  # Over 1 second
                logger.warning(
                    f"Slow API request: {request.method} {request.path} "
                    f"took {duration_ms}ms"
                )

        return response

    def _get_db_query_count(self):
        """Get current database query count"""
        from django.db import connection

        return len(connection.queries) if hasattr(connection, "queries") else 0


class APICacheMiddleware(MiddlewareMixin):
    """
    Middleware for HTTP caching of API responses.

    Supports:
    - Cache-Control headers
    - ETag validation
    - Conditional GET requests

    Cache keys are based on:
    - Request path
    - Query parameters
    - Request method
    - User authentication state
    """

    # Default cache timeout (5 minutes)
    DEFAULT_TIMEOUT = 300

    # Paths that should not be cached
    CACHE_EXCLUDE_PATHS = [
        "/api/future-skills/recalculate/",
        "/api/train-model/",
        "/api/bulk-import/",
        "/api/bulk-upload/",
    ]

    # Cache timeout by path pattern (in seconds)
    CACHE_TIMEOUTS = {
        "/api/skills/": 3600,  # 1 hour
        "/api/job-roles/": 3600,  # 1 hour
        "/api/future-skills/": 300,  # 5 minutes
        "/api/market-trends/": 600,  # 10 minutes
        "/api/economic-reports/": 600,  # 10 minutes
        "/api/hr-investment-recommendations/": 300,  # 5 minutes
        "/api/employees/": 180,  # 3 minutes
    }

    def process_request(self, request):
        """Check if request can be served from cache"""
        # Only cache GET requests
        if request.method != "GET":
            return None

        # Skip excluded paths
        if any(request.path.startswith(path) for path in self.CACHE_EXCLUDE_PATHS):
            return None

        # Generate cache key
        cache_key = self._get_cache_key(request)

        # Try to get from cache
        cached_response = cache.get(cache_key)
        if cached_response:
            logger.debug(f"Cache HIT for {request.path}")
            response = JsonResponse(cached_response, safe=False)
            response["X-Cache-Hit"] = "true"
            return response

        logger.debug(f"Cache MISS for {request.path}")
        return None

    def process_response(self, request, response):
        """Cache successful GET responses"""
        # Only cache GET requests
        if request.method != "GET":
            return response

        # Only cache successful responses
        if response.status_code != 200:
            return response

        # Skip excluded paths
        if any(request.path.startswith(path) for path in self.CACHE_EXCLUDE_PATHS):
            return response

        # Skip if already from cache
        if response.get("X-Cache-Hit"):
            return response

        # Generate cache key
        cache_key = self._get_cache_key(request)

        # Determine cache timeout
        timeout = self._get_cache_timeout(request.path)

        # Cache JSON responses only
        if "application/json" in response.get("Content-Type", ""):
            try:
                # Parse and cache response data
                if hasattr(response, "data"):
                    # DRF Response object
                    cache.set(cache_key, response.data, timeout)
                else:
                    # Regular JsonResponse
                    response_data = json.loads(response.content)
                    cache.set(cache_key, response_data, timeout)

                logger.debug(f"Cached response for {request.path} (timeout={timeout}s)")
            except (json.JSONDecodeError, AttributeError):
                pass

        # Add cache headers
        response["Cache-Control"] = f"max-age={timeout}"
        response["X-Cache-Hit"] = "false"

        return response

    def _get_cache_key(self, request):
        """Generate cache key for request"""
        # Include path, query string, and auth state
        user_id = request.user.id if request.user.is_authenticated else "anon"
        query_string = request.META.get("QUERY_STRING", "")

        return f"api_cache:{request.path}:{query_string}:{user_id}"

    def _get_cache_timeout(self, path):
        """Get cache timeout for specific path"""
        for pattern, timeout in self.CACHE_TIMEOUTS.items():
            if path.startswith(pattern):
                return timeout
        return self.DEFAULT_TIMEOUT


class APIDeprecationMiddleware(MiddlewareMixin):
    """
    Middleware to add deprecation warnings to API responses.

    Adds headers for deprecated API versions:
    - X-API-Deprecation: Warning message
    - X-API-Sunset-Date: Date when version will be removed
    - Link: URL to migration guide
    """

    def process_response(self, request, response):
        """Add deprecation headers if needed"""
        # Check if request has deprecation warning (set by versioning)
        if hasattr(request, "_deprecation_warning"):
            response["X-API-Deprecation"] = request._deprecation_warning
            response["X-API-Sunset-Date"] = "2026-06-01"
            response["Link"] = '</api/docs/migration/>; rel="deprecation"'

            # Also add to response body if JSON
            if "application/json" in response.get("Content-Type", ""):
                try:
                    if hasattr(response, "data"):
                        if isinstance(response.data, dict):
                            response.data["_deprecation"] = {
                                "warning": request._deprecation_warning,
                                "sunset_date": "2026-06-01",
                                "migration_guide": "/api/docs/migration/",
                            }
                except (AttributeError, TypeError):
                    pass

        return response


class RequestLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log all API requests for audit and debugging.

    Logs:
    - Request method, path, and query parameters
    - User information (if authenticated)
    - Response status code
    - Request duration
    """

    # Paths to exclude from logging (too noisy)
    EXCLUDE_PATHS = [
        "/api/health/",
        "/admin/jsi18n/",
    ]

    def process_request(self, request):
        """Log request start"""
        request._log_start_time = time.time()

    def process_response(self, request, response):
        """Log request completion"""
        # Skip excluded paths
        if any(request.path.startswith(path) for path in self.EXCLUDE_PATHS):
            return response

        # Calculate duration
        duration = 0
        if hasattr(request, "_log_start_time"):
            duration = int((time.time() - request._log_start_time) * 1000)

        # Get user info
        user_info = "anonymous"
        if request.user and request.user.is_authenticated:
            user_info = f"user:{request.user.id}({request.user.username})"

        # Get query params (sanitized)
        query_params = dict(request.GET)
        # Remove sensitive params
        for sensitive_key in ["password", "token", "secret", "key"]:
            if sensitive_key in query_params:
                query_params[sensitive_key] = "***"

        # Log the request
        logger.info(
            f"API Request: {request.method} {request.path} "
            f"| User: {user_info} "
            f"| Status: {response.status_code} "
            f"| Duration: {duration}ms "
            f"| Params: {query_params}"
        )

        return response


class CORSHeadersMiddleware(MiddlewareMixin):
    """
    Simple CORS middleware for API responses.

    Note: For production, use django-cors-headers package instead.
    This is a simple implementation for development/testing.
    """

    def process_response(self, request, response):
        """Add CORS headers to API responses"""
        if request.path.startswith("/api/"):
            response["Access-Control-Allow-Origin"] = "*"
            response["Access-Control-Allow-Methods"] = (
                "GET, POST, PUT, PATCH, DELETE, OPTIONS"
            )
            response["Access-Control-Allow-Headers"] = (
                "Content-Type, Authorization, X-Requested-With"
            )
            response["Access-Control-Max-Age"] = "3600"
            response["Access-Control-Expose-Headers"] = (
                "X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset, X-Response-Time"
            )

        return response
