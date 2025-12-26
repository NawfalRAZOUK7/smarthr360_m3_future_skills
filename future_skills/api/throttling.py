"""API rate limiting and throttling utilities.

Implements multiple throttling strategies for different user types and endpoints.
Provides granular control over API usage with proper rate limit headers.
"""

import time

from django.conf import settings
from django.core.cache import cache
from rest_framework.throttling import AnonRateThrottle as DRFAnonRateThrottle
from rest_framework.throttling import ScopedRateThrottle as DRFScopedRateThrottle
from rest_framework.throttling import UserRateThrottle as DRFUserRateThrottle


def _parse_rate(rate):
    """Parse a rate string like '5/minute' into (num_requests, seconds)."""
    if not rate:
        return None

    try:
        num, period = rate.split("/")
        num_requests = int(num)
    except (ValueError, TypeError):
        return None

    period = period.strip().lower()
    seconds_map = {
        "s": 1,
        "sec": 1,
        "second": 1,
        "seconds": 1,
        "m": 60,
        "min": 60,
        "minute": 60,
        "minutes": 60,
        "h": 3600,
        "hr": 3600,
        "hour": 3600,
        "hours": 3600,
        "d": 86400,
        "day": 86400,
        "days": 86400,
    }

    duration = seconds_map.get(period)
    if duration is None:
        return None

    return num_requests, duration


class BaseSimpleThrottle:
    """Minimal, test-focused throttle implementation with headers and caching."""

    scope = None
    rate = None  # e.g. "5/minute"

    def __init__(self):
        """Initialize the throttle configuration."""
        self.history = []
        self.num_requests = None
        self.duration = None
        self.timer = time.time
        self.cache = cache
        self.view = None
        self.request = None

    def get_rate(self):
        """Return the rate string for this throttle."""
        rates = getattr(settings, "REST_FRAMEWORK", {}).get("DEFAULT_THROTTLE_RATES", {})
        return self.rate or rates.get(self.scope)

    def get_cache_key(self, request, view):
        """Return the cache key used to identify the request source."""
        ident = self.get_ident(request)
        return f"throttle_{self.scope}_{ident}"

    def get_ident(self, request):
        """Return a unique identifier for the client making the request."""
        return request.META.get("REMOTE_ADDR", "anon")

    def allow_request(self, request, view):
        """Return True if the request is allowed, otherwise False."""
        self.view = view
        self.request = request

        # Superusers should not be throttled
        if getattr(getattr(request, "user", None), "is_superuser", False):
            return True

        # Bypass if IP is whitelisted
        bypass_ips = getattr(settings, "THROTTLE_BYPASS_IPS", [])
        if self.get_ident(request) in bypass_ips:
            return True

        rate = self.get_rate()
        if not rate:
            return True

        parsed = _parse_rate(rate)
        if not parsed:
            return True

        self.num_requests, self.duration = parsed
        now = self.timer()

        cache_key = self.get_cache_key(request, view)
        # Start from local history; cache is optional best-effort
        if cache_key:
            self.history = self.cache.get(cache_key, self.history)

        # Drop requests outside the window
        self.history = [ts for ts in self.history if ts > now - self.duration]

        if len(self.history) >= self.num_requests:
            # Store truncated history for wait()/headers()
            if cache_key:
                self.cache.set(cache_key, self.history, self.duration)
            return False

        self.history.append(now)
        if cache_key:
            self.cache.set(cache_key, self.history, self.duration)
        return True

    def wait(self):
        """Return the number of seconds to wait before the next allowed request."""
        if self.history and self.duration:
            remaining = self.duration - (self.timer() - self.history[0])
            return max(remaining, 0)
        return None

    def get_rate_limit_headers(self, request, view):
        """Build X-RateLimit-* headers for the current client and scope."""
        # Ensure we have current history
        if not self.history or self.num_requests is None or self.duration is None:
            self.allow_request(request, view)

        now = self.timer()
        remaining = max(self.num_requests - len(self.history), 0) if self.num_requests else 0
        reset_base = self.history[0] + self.duration if self.history else now + (self.duration or 0)
        reset = int(reset_base + 1)  # ensure strictly in the future

        return {
            "X-RateLimit-Limit": str(self.num_requests or 0),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(reset),
        }


class AnonRateThrottle(BaseSimpleThrottle, DRFAnonRateThrottle):
    """Throttle anonymous requests using project-wide rate limits."""

    scope = "anon"


class UserRateThrottle(BaseSimpleThrottle, DRFUserRateThrottle):
    """Throttle authenticated users based on their user IDs."""

    scope = "user"

    def get_cache_key(self, request, view):
        """Return the cache key used to track this user's requests."""
        if not getattr(request, "user", None) or not request.user.is_authenticated:
            return None
        return f"throttle_{self.scope}_{request.user.pk}"


class BurstRateThrottle(UserRateThrottle):
    """Short-window burst throttle for authenticated users."""

    scope = "burst"


class SustainedRateThrottle(UserRateThrottle):
    """Long-window sustained throttle for authenticated users."""

    scope = "sustained"


class PremiumUserThrottle(UserRateThrottle):
    """Throttle that relaxes limits for premium or high-value users."""

    scope = "premium"

    def allow_request(self, request, view):
        """Allow more requests for premium users while still enforcing safety limits."""
        if request.user and request.user.is_authenticated:
            if request.user.is_superuser:
                return True
            if request.user.is_staff or getattr(request.user, "is_premium", False):
                return super().allow_request(request, view)
        return True


class MLOperationsThrottle(UserRateThrottle, DRFScopedRateThrottle):
    """Protect ML/analytics endpoints from abusive usage."""

    scope = "ml_operations"

    def allow_request(self, request, view):
        """Enforce stricter limits for expensive ML operations."""
        if not request.path.startswith("/api/v2/ml"):
            return True
        return super().allow_request(request, view)


class BulkOperationsThrottle(UserRateThrottle, DRFScopedRateThrottle):
    """Throttle bulk operations that are resource intensive."""

    scope = "bulk_operations"

    def allow_request(self, request, view):
        """Limit the frequency of bulk operations per user."""
        if "/bulk/" not in request.path:
            return True
        return super().allow_request(request, view)


class HealthCheckThrottle(AnonRateThrottle):
    """Throttle health-check endpoints, typically with a generous limit."""

    scope = "health_check"

    def allow_request(self, request, view):
        """Allow frequent health checks while preventing abuse."""
        if not request.path.startswith("/api/health"):
            return True
        return super().allow_request(request, view)


def get_throttle_rates():
    """Get all configured throttle rates.

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
    """Generate rate limit headers for response.

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
    """Mixin to add rate limit headers to API responses.

    Usage:
        class MyView(RateLimitHeadersMixin, APIView):
            throttle_classes = [UserThrottle]
            ...
    """

    def finalize_response(self, request, response, *args, **kwargs):
        """Add rate limit headers to response."""
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
    """Get appropriate throttle classes for a specific view.

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
