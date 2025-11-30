"""
Security Middleware
===================

Custom middleware for security headers, monitoring, and protection.
"""

import logging
import time

import user_agents
from django.conf import settings
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from ipware import get_client_ip

logger = logging.getLogger("security")


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Add comprehensive security headers to all responses.

    Headers added:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - X-XSS-Protection: 1; mode=block
    - Referrer-Policy: strict-origin-when-cross-origin
    - Permissions-Policy: restrictive permissions
    """

    def process_response(self, request, response):
        # Prevent MIME type sniffing
        response["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        if not response.get("X-Frame-Options"):
            response["X-Frame-Options"] = "DENY"

        # XSS Protection (legacy but still useful)
        response["X-XSS-Protection"] = "1; mode=block"

        # Referrer Policy
        response["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions Policy (formerly Feature Policy)
        response["Permissions-Policy"] = (
            "accelerometer=(), "
            "camera=(), "
            "geolocation=(), "
            "gyroscope=(), "
            "magnetometer=(), "
            "microphone=(), "
            "payment=(), "
            "usb=()"
        )

        # HSTS (Strict-Transport-Security) - only in production
        if not settings.DEBUG:
            response["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        return response


class SecurityEventLoggingMiddleware(MiddlewareMixin):
    """
    Log security-relevant events and suspicious activities.
    """

    # Suspicious patterns
    SUSPICIOUS_PATTERNS = [
        "../",
        "..\\",  # Path traversal
        "<script",
        "javascript:",  # XSS attempts
        "union select",
        "drop table",  # SQL injection
        "${",
        "#{",  # Template injection
        "eval(",
        "exec(",  # Code execution
    ]

    def process_request(self, request):
        # Store request start time
        request._security_start_time = time.time()

        # Get client info
        client_ip, is_routable = get_client_ip(request)
        user_agent_string = request.META.get("HTTP_USER_AGENT", "")
        user_agent = user_agents.parse(user_agent_string)

        # Store in request for later use
        request._client_ip = client_ip
        request._user_agent = user_agent

        # Check for suspicious patterns in request
        suspicious = self._check_suspicious_request(request)
        if suspicious:
            logger.warning(
                f"Suspicious request detected from {client_ip}",
                extra={
                    "event": "suspicious_request",
                    "ip_address": client_ip,
                    "path": request.path,
                    "method": request.method,
                    "user_agent": user_agent_string,
                    "suspicious_patterns": suspicious,
                    "user": (
                        str(request.user) if hasattr(request, "user") else "anonymous"
                    ),
                },
            )

        return None

    def process_response(self, request, response):
        # Calculate request duration
        if hasattr(request, "_security_start_time"):
            duration = time.time() - request._security_start_time

            # Log slow requests (potential DoS)
            if duration > 5.0:  # 5 seconds
                logger.warning(
                    f"Slow request detected: {duration:.2f}s",
                    extra={
                        "event": "slow_request",
                        "duration": duration,
                        "path": request.path,
                        "method": request.method,
                        "ip_address": getattr(request, "_client_ip", "unknown"),
                    },
                )

        # Log failed authentication attempts
        if response.status_code in [401, 403]:
            logger.warning(
                f"Authentication/Authorization failure: {response.status_code}",
                extra={
                    "event": "auth_failure",
                    "status_code": response.status_code,
                    "path": request.path,
                    "method": request.method,
                    "ip_address": getattr(request, "_client_ip", "unknown"),
                    "user": (
                        str(request.user) if hasattr(request, "user") else "anonymous"
                    ),
                },
            )

        return response

    def _check_suspicious_request(self, request):
        """Check for suspicious patterns in the request."""
        suspicious = []

        # Check URL path
        path_lower = request.path.lower()
        for pattern in self.SUSPICIOUS_PATTERNS:
            if pattern.lower() in path_lower:
                suspicious.append(f"path:{pattern}")

        # Check query parameters
        query_string = request.META.get("QUERY_STRING", "").lower()
        for pattern in self.SUSPICIOUS_PATTERNS:
            if pattern.lower() in query_string:
                suspicious.append(f"query:{pattern}")

        # Check for unusual methods
        if request.method not in [
            "GET",
            "POST",
            "PUT",
            "PATCH",
            "DELETE",
            "HEAD",
            "OPTIONS",
        ]:
            suspicious.append(f"method:{request.method}")

        # Check for missing or suspicious User-Agent
        user_agent = request.META.get("HTTP_USER_AGENT", "")
        if not user_agent:
            suspicious.append("no_user_agent")
        elif len(user_agent) < 10 or "bot" in user_agent.lower():
            suspicious.append(f"suspicious_ua:{user_agent[:50]}")

        return suspicious


class RateLimitMiddleware(MiddlewareMixin):
    """
    Simple rate limiting middleware using Django cache.

    For more advanced rate limiting, use django-ratelimit decorators
    or django-axes for login protection.
    """

    def __init__(self, get_response):
        super().__init__(get_response)
        try:
            from django.core.cache import cache

            self.cache = cache
        except Exception:
            self.cache = None

    def process_request(self, request):
        if not self.cache:
            return None

        # Skip rate limiting for certain paths
        skip_paths = ["/admin/", "/static/", "/media/"]
        if any(request.path.startswith(path) for path in skip_paths):
            return None

        # Get client identifier
        client_ip = getattr(request, "_client_ip", None)
        if not client_ip:
            client_ip, _ = get_client_ip(request)

        # Create cache key
        cache_key = f"rate_limit:{client_ip}:{request.path}"

        # Get request count
        request_count = self.cache.get(cache_key, 0)

        # Check limit (100 requests per minute per IP per endpoint)
        limit = 100
        window = 60  # seconds

        if request_count >= limit:
            logger.warning(
                f"Rate limit exceeded for {client_ip}",
                extra={
                    "event": "rate_limit_exceeded",
                    "ip_address": client_ip,
                    "path": request.path,
                    "count": request_count,
                    "limit": limit,
                },
            )
            return JsonResponse(
                {
                    "error": "Rate limit exceeded",
                    "detail": f"Maximum {limit} requests per minute",
                    "retry_after": window,
                },
                status=429,
            )

        # Increment counter
        self.cache.set(cache_key, request_count + 1, window)

        return None


class IPWhitelistMiddleware(MiddlewareMixin):
    """
    Optional: Restrict access to specific IP addresses.

    Configure ALLOWED_IPS in settings to enable.
    """

    def process_request(self, request):
        # Only enforce in production and if configured
        if settings.DEBUG:
            return None

        allowed_ips = getattr(settings, "ALLOWED_IPS", None)
        if not allowed_ips:
            return None

        client_ip, _ = get_client_ip(request)

        # Skip for certain paths (e.g., health checks)
        skip_paths = getattr(
            settings, "IP_WHITELIST_SKIP_PATHS", ["/health/", "/api/health/"]
        )
        if any(request.path.startswith(path) for path in skip_paths):
            return None

        if client_ip not in allowed_ips:
            logger.warning(
                f"Access denied for IP: {client_ip}",
                extra={
                    "event": "ip_blocked",
                    "ip_address": client_ip,
                    "path": request.path,
                },
            )
            return JsonResponse({"error": "Access denied"}, status=403)

        return None


class SecurityAuditMiddleware(MiddlewareMixin):
    """
    Audit all requests for security compliance and monitoring.

    Logs detailed information about authenticated requests.
    """

    def process_request(self, request):
        # Only audit authenticated requests
        if not hasattr(request, "user") or not request.user.is_authenticated:
            return None

        # Skip for static files and common paths
        if request.path.startswith(("/static/", "/media/", "/favicon.ico")):
            return None

        # Log the request
        logger.info(
            f"Authenticated request: {request.method} {request.path}",
            extra={
                "event": "authenticated_request",
                "user_id": request.user.id,
                "username": request.user.username,
                "method": request.method,
                "path": request.path,
                "ip_address": getattr(request, "_client_ip", "unknown"),
                "user_agent": request.META.get("HTTP_USER_AGENT", "")[:200],
            },
        )

        return None


# Example usage in settings.py:
# MIDDLEWARE = [
#     'django.middleware.security.SecurityMiddleware',
#     'config.security_middleware.SecurityHeadersMiddleware',  # Add early
#     'django.contrib.sessions.middleware.SessionMiddleware',
#     'django.middleware.common.CommonMiddleware',
#     'django.middleware.csrf.CsrfViewMiddleware',
#     'django.contrib.auth.middleware.AuthenticationMiddleware',
#     'config.security_middleware.SecurityEventLoggingMiddleware',  # After auth
#     'config.security_middleware.RateLimitMiddleware',  # After auth
#     'config.security_middleware.SecurityAuditMiddleware',  # After auth
#     'django.contrib.messages.middleware.MessageMiddleware',
#     'django.middleware.clickjacking.XFrameOptionsMiddleware',
# ]
