"""
API Rate Limiting and Throttling

Implements multiple throttling strategies for different user types and endpoints.
Provides granular control over API usage with proper rate limit headers.
"""

import time

from django.conf import settings
from django.core.cache import cache
from rest_framework.throttling import AnonRateThrottle, ScopedRateThrottle, UserRateThrottle


class AnonThrottle(AnonRateThrottle):
    """
    Throttle for anonymous (unauthenticated) users.

    Rate: 100 requests per hour
    Scope: Global for all anonymous requests
    """

    rate = "100/hour"
    scope = "anon"


class UserThrottle(UserRateThrottle):
    """
    Throttle for authenticated users (default tier).

    Rate: 1000 requests per hour
    Scope: Global for authenticated users
    """

    rate = "1000/hour"
    scope = "user"


class BurstRateThrottle(UserRateThrottle):
    """
    Burst rate limiting for short-term traffic spikes.

    Rate: 60 requests per minute
    Use: Prevents rapid-fire requests while allowing sustained usage
    """

    rate = "60/min"
    scope = "burst"


class SustainedRateThrottle(UserRateThrottle):
    """
    Sustained rate limiting for long-term usage.

    Rate: 10000 requests per day
    Use: Prevents abuse over longer periods
    """

    rate = "10000/day"
    scope = "sustained"


class PremiumUserThrottle(UserRateThrottle):
    """
    Higher rate limits for premium/staff users.

    Rate: 5000 requests per hour
    Scope: Staff and premium users
    """

    rate = "5000/hour"
    scope = "premium"

    def allow_request(self, request, view):
        """Only apply to staff or users with premium flag"""
        if request.user and request.user.is_authenticated:
            # Check if user is staff or has premium attribute
            if request.user.is_staff or getattr(request.user, "is_premium", False):
                return super().allow_request(request, view)

        # Fall back to regular user throttle for non-premium users
        regular_throttle = UserThrottle()
        return regular_throttle.allow_request(request, view)


class MLOperationsThrottle(ScopedRateThrottle):
    """
    Specific throttling for ML operations (training, bulk predictions).

    Rate: 10 requests per hour
    Reason: ML operations are resource-intensive
    """

    scope = "ml_operations"

    def get_cache_key(self, request, view):
        """Custom cache key for ML operations"""
        if request.user and request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)

        return f"throttle_{self.scope}_{ident}"


class BulkOperationsThrottle(ScopedRateThrottle):
    """
    Throttling for bulk operations (bulk import, bulk predict).

    Rate: 30 requests per hour
    Reason: Bulk operations can be database-intensive
    """

    scope = "bulk_operations"


class HealthCheckThrottle(AnonRateThrottle):
    """
    Relaxed throttling for health check endpoints.

    Rate: 300 requests per minute
    Reason: Health checks need frequent access for monitoring
    """

    rate = "300/min"
    scope = "health_check"


class CustomThrottle(UserRateThrottle):
    """
    Base class for custom throttling with additional features.

    Features:
    - Custom rate limit headers
    - Throttle bypass for specific IPs
    - Dynamic rate adjustment
    """

    BYPASS_IPS = getattr(settings, "THROTTLE_BYPASS_IPS", [])

    def allow_request(self, request, view):
        """Check if request should bypass throttling"""
        # Bypass for whitelisted IPs
        client_ip = self.get_ident(request)
        if client_ip in self.BYPASS_IPS:
            return True

        # Bypass for superusers
        if request.user and request.user.is_authenticated and request.user.is_superuser:
            return True

        return super().allow_request(request, view)

    def throttle_success(self):
        """Called when request is allowed"""
        return super().throttle_success()

    def throttle_failure(self):
        """Called when request is throttled"""
        # Log throttling event
        from django.utils import timezone

        cache_key = self.get_cache_key(self.request, self.view)
        cache.set(f"{cache_key}_throttled_at", timezone.now().isoformat(), timeout=3600)
        return super().throttle_failure()


def get_throttle_rates():
    """
    Get all configured throttle rates.

    Returns:
        dict: Throttle scopes and their rates
    """
    return {
        "anon": "100/hour",
        "user": "1000/hour",
        "burst": "60/min",
        "sustained": "10000/day",
        "premium": "5000/hour",
        "ml_operations": "10/hour",
        "bulk_operations": "30/hour",
        "health_check": "300/min",
    }


def get_rate_limit_headers(throttle_instance, request, view):
    """
    Generate rate limit headers for response.

    Args:
        throttle_instance: Throttle instance that processed the request
        request: Django request object
        view: View that handled the request

    Returns:
        dict: Headers to add to response (X-RateLimit-*)
    """
    if not hasattr(throttle_instance, "history"):
        return {}

    # Calculate rate limit info
    now = time.time()
    history = throttle_instance.history
    duration = throttle_instance.duration
    num_requests = throttle_instance.num_requests

    # Remaining requests in current window
    remaining = num_requests - len([h for h in history if h > now - duration])

    # Reset time (when current window expires)
    if history:
        reset = int(history[0] + duration)
    else:
        reset = int(now + duration)

    return {
        "X-RateLimit-Limit": str(num_requests),
        "X-RateLimit-Remaining": str(max(0, remaining)),
        "X-RateLimit-Reset": str(reset),
    }


class RateLimitHeadersMixin:
    """
    Mixin to add rate limit headers to API responses.

    Usage:
        class MyView(RateLimitHeadersMixin, APIView):
            throttle_classes = [UserThrottle]
            ...
    """

    def finalize_response(self, request, response, *args, **kwargs):
        """Add rate limit headers to response"""
        response = super().finalize_response(request, response, *args, **kwargs)

        # Get throttle instances
        for throttle in self.get_throttles():
            if hasattr(throttle, "history"):
                headers = get_rate_limit_headers(throttle, request, self)
                for header, value in headers.items():
                    response[header] = value
                break  # Only use first throttle for headers

        return response


# Throttle configuration for different endpoint types
THROTTLE_CLASSES_BY_ENDPOINT = {
    "default": [BurstRateThrottle, SustainedRateThrottle],
    "ml_operations": [MLOperationsThrottle],
    "bulk_operations": [BulkOperationsThrottle],
    "health_check": [HealthCheckThrottle],
    "premium": [PremiumUserThrottle],
}


def get_throttle_classes_for_view(view_name):
    """
    Get appropriate throttle classes for a specific view.

    Args:
        view_name: Name or type of the view

    Returns:
        list: Throttle classes to apply
    """
    # Check for ML operations
    if any(keyword in view_name.lower() for keyword in ["train", "predict", "ml"]):
        return THROTTLE_CLASSES_BY_ENDPOINT["ml_operations"]

    # Check for bulk operations
    if "bulk" in view_name.lower():
        return THROTTLE_CLASSES_BY_ENDPOINT["bulk_operations"]

    # Check for health check
    if "health" in view_name.lower():
        return THROTTLE_CLASSES_BY_ENDPOINT["health_check"]

    # Default throttling
    return THROTTLE_CLASSES_BY_ENDPOINT["default"]
