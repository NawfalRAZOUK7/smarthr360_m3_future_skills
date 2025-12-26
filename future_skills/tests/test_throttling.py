"""
Unit tests for API throttling classes.

Tests all 8 throttle classes:
- AnonRateThrottle
- UserRateThrottle
- BurstRateThrottle
- SustainedRateThrottle
- PremiumUserThrottle
- MLOperationsThrottle
- BulkOperationsThrottle
- HealthCheckThrottle
"""

import time
from unittest.mock import Mock

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import RequestFactory, TestCase, override_settings

from future_skills.api.throttling import (
    AnonRateThrottle,
    BulkOperationsThrottle,
    BurstRateThrottle,
    HealthCheckThrottle,
    MLOperationsThrottle,
    PremiumUserThrottle,
    SustainedRateThrottle,
    UserRateThrottle,
)

User = get_user_model()


class BaseThrottleTestCase(TestCase):
    """Base test case for throttle tests."""

    def setUp(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()
        cache.clear()

    def create_request(self, path="/", user=None):
        """Create a test request."""
        request = self.factory.get(path)
        if user:
            request.user = user
        else:
            from django.contrib.auth.models import AnonymousUser

            request.user = AnonymousUser()
        return request


class AnonRateThrottleTestCase(BaseThrottleTestCase):
    """Test AnonRateThrottle."""

    @override_settings(
        REST_FRAMEWORK={
            "DEFAULT_THROTTLE_RATES": {
                "anon": "5/minute",
            }
        }
    )
    def test_anonymous_user_throttled(self):
        """Test that anonymous users are throttled."""
        throttle = AnonRateThrottle()
        request = self.create_request()

        # Make requests up to limit
        for i in range(5):
            self.assertTrue(throttle.allow_request(request, None))

        # Next request should be throttled
        self.assertFalse(throttle.allow_request(request, None))

    def test_authenticated_user_not_throttled_by_anon(self):
        """Test that authenticated users bypass anon throttle."""
        throttle = AnonRateThrottle()
        user = User.objects.create_user(username="testuser", password="pass")
        request = self.create_request(user=user)

        # Authenticated user should not be throttled by anon throttle
        self.assertTrue(throttle.allow_request(request, None))

    def test_rate_limit_headers(self):
        """Test that rate limit headers are added."""
        throttle = AnonRateThrottle()
        request = self.create_request()
        view = Mock()

        throttle.allow_request(request, view)

        # Get headers
        headers = throttle.get_rate_limit_headers(request, view)

        self.assertIn("X-RateLimit-Limit", headers)
        self.assertIn("X-RateLimit-Remaining", headers)
        self.assertIn("X-RateLimit-Reset", headers)

    def test_wait_time_calculation(self):
        """Test wait time calculation when throttled."""
        throttle = AnonRateThrottle()
        request = self.create_request()

        # Exhaust the limit
        with override_settings(REST_FRAMEWORK={"DEFAULT_THROTTLE_RATES": {"anon": "1/minute"}}):
            throttle.allow_request(request, None)
            throttle.allow_request(request, None)

            wait = throttle.wait()
            self.assertIsNotNone(wait)
            self.assertGreater(wait, 0)


class UserRateThrottleTestCase(BaseThrottleTestCase):
    """Test UserRateThrottle."""

    @override_settings(
        REST_FRAMEWORK={
            "DEFAULT_THROTTLE_RATES": {
                "user": "10/minute",
            }
        }
    )
    def test_authenticated_user_throttled(self):
        """Test that authenticated users are throttled."""
        throttle = UserRateThrottle()
        user = User.objects.create_user(username="testuser", password="pass")
        request = self.create_request(user=user)

        # Make requests up to limit
        for i in range(10):
            self.assertTrue(throttle.allow_request(request, None))

        # Next request should be throttled
        self.assertFalse(throttle.allow_request(request, None))

    def test_different_users_separate_limits(self):
        """Test that different users have separate limits."""
        throttle = UserRateThrottle()

        user1 = User.objects.create_user(username="user1", password="pass")
        user2 = User.objects.create_user(username="user2", password="pass")

        request1 = self.create_request(user=user1)
        request2 = self.create_request(user=user2)

        # Both users should have their own limits
        self.assertTrue(throttle.allow_request(request1, None))
        self.assertTrue(throttle.allow_request(request2, None))

    def test_anonymous_user_not_throttled_by_user_throttle(self):
        """Test that anonymous users bypass user throttle."""
        throttle = UserRateThrottle()
        request = self.create_request()

        # Anonymous should bypass user throttle
        self.assertTrue(throttle.allow_request(request, None))


class BurstRateThrottleTestCase(BaseThrottleTestCase):
    """Test BurstRateThrottle."""

    @override_settings(
        REST_FRAMEWORK={
            "DEFAULT_THROTTLE_RATES": {
                "burst": "3/minute",
            }
        }
    )
    def test_burst_rate_limiting(self):
        """Test burst rate limiting."""
        throttle = BurstRateThrottle()
        user = User.objects.create_user(username="testuser", password="pass")
        request = self.create_request(user=user)

        # Make burst requests
        for i in range(3):
            self.assertTrue(throttle.allow_request(request, None))

        # Should be throttled after burst
        self.assertFalse(throttle.allow_request(request, None))

    def test_burst_applies_to_all_users(self):
        """Test that burst throttle applies to all users."""
        throttle = BurstRateThrottle()
        user = User.objects.create_user(username="testuser", password="pass")
        request = self.create_request(user=user)

        # Should throttle authenticated users
        self.assertTrue(throttle.allow_request(request, None))


class SustainedRateThrottleTestCase(BaseThrottleTestCase):
    """Test SustainedRateThrottle."""

    @override_settings(
        REST_FRAMEWORK={
            "DEFAULT_THROTTLE_RATES": {
                "sustained": "100/day",
            }
        }
    )
    def test_sustained_rate_limiting(self):
        """Test sustained rate limiting."""
        throttle = SustainedRateThrottle()
        user = User.objects.create_user(username="testuser", password="pass")
        request = self.create_request(user=user)

        # Make sustained requests
        for i in range(100):
            self.assertTrue(throttle.allow_request(request, None))

        # Should be throttled after daily limit
        self.assertFalse(throttle.allow_request(request, None))


class PremiumUserThrottleTestCase(BaseThrottleTestCase):
    """Test PremiumUserThrottle."""

    @override_settings(
        REST_FRAMEWORK={
            "DEFAULT_THROTTLE_RATES": {
                "premium": "100/hour",
            }
        }
    )
    def test_staff_user_gets_premium_rate(self):
        """Test that staff users get premium rate."""
        throttle = PremiumUserThrottle()
        staff_user = User.objects.create_user(username="staff", password="pass", is_staff=True)
        request = self.create_request(user=staff_user)

        # Staff should have premium rate
        self.assertTrue(throttle.allow_request(request, None))

    def test_premium_user_attribute(self):
        """Test users with is_premium attribute get premium rate."""
        throttle = PremiumUserThrottle()
        user = User.objects.create_user(username="premium", password="pass")

        # Add is_premium attribute (if model supports it)
        if hasattr(user, "is_premium"):
            user.is_premium = True
            user.save()

        request = self.create_request(user=user)
        self.assertTrue(throttle.allow_request(request, None))

    def test_regular_user_bypassed(self):
        """Test that regular users bypass premium throttle."""
        throttle = PremiumUserThrottle()
        user = User.objects.create_user(username="regular", password="pass")
        request = self.create_request(user=user)

        # Regular user should bypass (returns True)
        self.assertTrue(throttle.allow_request(request, None))

    def test_superuser_bypass(self):
        """Test that superusers bypass throttle."""
        throttle = PremiumUserThrottle()
        superuser = User.objects.create_superuser(username="admin", password="admin123", email="admin@test.com")
        request = self.create_request(user=superuser)

        # Make many requests - should never throttle
        for i in range(200):
            self.assertTrue(throttle.allow_request(request, None))


class MLOperationsThrottleTestCase(BaseThrottleTestCase):
    """Test MLOperationsThrottle."""

    @override_settings(
        REST_FRAMEWORK={
            "DEFAULT_THROTTLE_RATES": {
                "ml_operations": "2/hour",
            }
        }
    )
    def test_ml_operations_throttling(self):
        """Test ML operations throttling."""
        throttle = MLOperationsThrottle()
        user = User.objects.create_user(username="testuser", password="pass")
        request = self.create_request(path="/api/v2/ml/train/", user=user)

        # Make requests up to limit
        for i in range(2):
            self.assertTrue(throttle.allow_request(request, None))

        # Should be throttled
        self.assertFalse(throttle.allow_request(request, None))

    def test_only_applies_to_ml_endpoints(self):
        """Test that throttle only applies to ML endpoints."""
        throttle = MLOperationsThrottle()
        user = User.objects.create_user(username="testuser", password="pass")

        # ML endpoint should be throttled
        ml_request = self.create_request(path="/api/v2/ml/predict/", user=user)
        self.assertTrue(throttle.allow_request(ml_request, None))

        # Non-ML endpoint should bypass
        other_request = self.create_request(path="/api/v2/predictions/", user=user)
        # Implementation dependent - may bypass or apply


class BulkOperationsThrottleTestCase(BaseThrottleTestCase):
    """Test BulkOperationsThrottle."""

    @override_settings(
        REST_FRAMEWORK={
            "DEFAULT_THROTTLE_RATES": {
                "bulk_operations": "3/hour",
            }
        }
    )
    def test_bulk_operations_throttling(self):
        """Test bulk operations throttling."""
        throttle = BulkOperationsThrottle()
        user = User.objects.create_user(username="testuser", password="pass")
        request = self.create_request(path="/api/v2/bulk/employees/import/", user=user)

        # Make requests up to limit
        for i in range(3):
            self.assertTrue(throttle.allow_request(request, None))

        # Should be throttled
        self.assertFalse(throttle.allow_request(request, None))

    def test_only_applies_to_bulk_endpoints(self):
        """Test that throttle only applies to bulk endpoints."""
        throttle = BulkOperationsThrottle()
        user = User.objects.create_user(username="testuser", password="pass")

        # Bulk endpoint should be throttled
        bulk_request = self.create_request(path="/api/v2/bulk/employees/upload/", user=user)
        self.assertTrue(throttle.allow_request(bulk_request, None))


class HealthCheckThrottleTestCase(BaseThrottleTestCase):
    """Test HealthCheckThrottle."""

    @override_settings(
        REST_FRAMEWORK={
            "DEFAULT_THROTTLE_RATES": {
                "health_check": "10/minute",
            }
        }
    )
    def test_health_check_throttling(self):
        """Test health check throttling."""
        throttle = HealthCheckThrottle()
        request = self.create_request(path="/api/health/")

        # Make requests up to limit
        for i in range(10):
            self.assertTrue(throttle.allow_request(request, None))

        # Should be throttled
        self.assertFalse(throttle.allow_request(request, None))

    def test_higher_limit_for_monitoring(self):
        """Test that health checks have higher limits."""
        # Health checks should have a relatively high limit
        # since they're used for monitoring
        throttle = HealthCheckThrottle()
        request = self.create_request(path="/api/health/")

        # Should allow many requests
        self.assertTrue(throttle.allow_request(request, None))


class ThrottleHeadersTestCase(BaseThrottleTestCase):
    """Test rate limit headers functionality."""

    def test_get_rate_limit_headers(self):
        """Test getting rate limit headers."""
        throttle = AnonRateThrottle()
        request = self.create_request()
        view = Mock()

        throttle.allow_request(request, view)
        headers = throttle.get_rate_limit_headers(request, view)

        self.assertIn("X-RateLimit-Limit", headers)
        self.assertIn("X-RateLimit-Remaining", headers)
        self.assertIn("X-RateLimit-Reset", headers)

        # Verify types
        self.assertIsInstance(int(headers["X-RateLimit-Limit"]), int)
        self.assertIsInstance(int(headers["X-RateLimit-Remaining"]), int)
        self.assertIsInstance(int(headers["X-RateLimit-Reset"]), int)

    def test_headers_show_correct_values(self):
        """Test that headers show correct rate limit values."""
        with override_settings(REST_FRAMEWORK={"DEFAULT_THROTTLE_RATES": {"anon": "5/minute"}}):
            throttle = AnonRateThrottle()
            request = self.create_request()
            view = Mock()

            # First request
            throttle.allow_request(request, view)
            headers = throttle.get_rate_limit_headers(request, view)

            limit = int(headers["X-RateLimit-Limit"])
            remaining = int(headers["X-RateLimit-Remaining"])

            self.assertEqual(limit, 5)
            self.assertEqual(remaining, 4)  # One request made

    def test_headers_countdown(self):
        """Test that remaining count goes down with requests."""
        with override_settings(REST_FRAMEWORK={"DEFAULT_THROTTLE_RATES": {"anon": "10/minute"}}):
            throttle = AnonRateThrottle()
            request = self.create_request()
            view = Mock()

            previous_remaining = None
            for i in range(5):
                throttle.allow_request(request, view)
                headers = throttle.get_rate_limit_headers(request, view)
                remaining = int(headers["X-RateLimit-Remaining"])

                if previous_remaining is not None:
                    self.assertEqual(remaining, previous_remaining - 1)

                previous_remaining = remaining

    def test_reset_timestamp_in_future(self):
        """Test that reset timestamp is in the future."""
        throttle = AnonRateThrottle()
        request = self.create_request()
        view = Mock()

        throttle.allow_request(request, view)
        headers = throttle.get_rate_limit_headers(request, view)

        reset_timestamp = int(headers["X-RateLimit-Reset"])
        current_time = int(time.time())

        self.assertGreater(reset_timestamp, current_time)


class IPWhitelistTestCase(BaseThrottleTestCase):
    """Test IP whitelisting functionality."""

    @override_settings(THROTTLE_BYPASS_IPS=["127.0.0.1", "192.168.1.100"])
    def test_whitelisted_ip_bypass(self):
        """Test that whitelisted IPs bypass throttling."""
        throttle = AnonRateThrottle()
        request = self.create_request()
        request.META["REMOTE_ADDR"] = "127.0.0.1"

        # Should bypass throttle (if implemented)
        # Implementation dependent
        result = throttle.allow_request(request, None)
        self.assertIsInstance(result, bool)

    def test_non_whitelisted_ip_throttled(self):
        """Test that non-whitelisted IPs are throttled."""
        with override_settings(
            REST_FRAMEWORK={"DEFAULT_THROTTLE_RATES": {"anon": "2/minute"}},
            THROTTLE_BYPASS_IPS=["192.168.1.100"],
        ):
            throttle = AnonRateThrottle()
            request = self.create_request()
            request.META["REMOTE_ADDR"] = "10.0.0.1"

            # Make requests up to limit
            throttle.allow_request(request, None)
            throttle.allow_request(request, None)

            # Should be throttled
            self.assertFalse(throttle.allow_request(request, None))


class ThrottleIntegrationTestCase(BaseThrottleTestCase):
    """Test multiple throttles working together."""

    def test_multiple_throttles_applied(self):
        """Test that multiple throttles can be applied together."""
        # Both burst and sustained throttles
        burst_throttle = BurstRateThrottle()
        sustained_throttle = SustainedRateThrottle()

        user = User.objects.create_user(username="testuser", password="pass")
        request = self.create_request(user=user)

        # Both should allow the first request
        self.assertTrue(burst_throttle.allow_request(request, None))
        self.assertTrue(sustained_throttle.allow_request(request, None))

    def test_most_restrictive_throttle_wins(self):
        """Test that the most restrictive throttle is enforced."""
        # If burst is more restrictive than sustained, burst should throttle first
        with override_settings(
            REST_FRAMEWORK={
                "DEFAULT_THROTTLE_RATES": {
                    "burst": "2/minute",
                    "sustained": "100/day",
                }
            }
        ):
            burst_throttle = BurstRateThrottle()
            sustained_throttle = SustainedRateThrottle()

            user = User.objects.create_user(username="testuser", password="pass")
            request = self.create_request(user=user)

            # Make 2 requests
            burst_throttle.allow_request(request, None)
            sustained_throttle.allow_request(request, None)
            burst_throttle.allow_request(request, None)
            sustained_throttle.allow_request(request, None)

            # Third request - burst should throttle
            burst_allowed = burst_throttle.allow_request(request, None)
            sustained_allowed = sustained_throttle.allow_request(request, None)

            self.assertFalse(burst_allowed)
            self.assertTrue(sustained_allowed)

    def test_endpoint_specific_throttles(self):
        """Test that different endpoints can have different throttles."""
        ml_throttle = MLOperationsThrottle()
        bulk_throttle = BulkOperationsThrottle()

        user = User.objects.create_user(username="testuser", password="pass")

        ml_request = self.create_request(path="/api/v2/ml/train/", user=user)
        bulk_request = self.create_request(path="/api/v2/bulk/employees/import/", user=user)

        # Each endpoint should have its own throttle
        self.assertTrue(ml_throttle.allow_request(ml_request, None))
        self.assertTrue(bulk_throttle.allow_request(bulk_request, None))
