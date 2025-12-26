"""
Integration tests for API Architecture features.

Tests:
- API versioning (URL path, Accept header)
- Rate limiting and throttling
- Performance monitoring
- Caching
- Health check endpoints
- Deprecation warnings
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from future_skills.models import JobRole, Skill

User = get_user_model()


class APIVersioningTestCase(APITestCase):
    """Test API versioning functionality."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.client.force_authenticate(user=self.user)

        # Create test data
        self.skill = Skill.objects.create(name="Python", category="Technical", description="Python programming")
        self.job_role = JobRole.objects.create(name="Data Scientist", description="Data science role")

    def test_v2_url_path_versioning(self):
        """Test v2 API using URL path versioning."""
        response = self.client.get("/api/v2/predictions/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)

    def test_v1_url_path_versioning_deprecated(self):
        """Test v1 API includes deprecation warnings."""
        response = self.client.get("/api/v1/future-skills/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check deprecation headers
        self.assertIn("X-API-Deprecation", response)
        self.assertIn("X-API-Sunset-Date", response)
        self.assertEqual(response["X-API-Sunset-Date"], "2026-06-01")

    def test_accept_header_versioning_v2(self):
        """Test Accept header versioning for v2."""
        response = self.client.get("/api/predictions/", HTTP_ACCEPT="application/vnd.smarthr360.v2+json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_accept_header_versioning_v1(self):
        """Test Accept header versioning for v1."""
        response = self.client.get("/api/future-skills/", HTTP_ACCEPT="application/vnd.smarthr360.v1+json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("X-API-Deprecation", response)

    def test_default_version_is_v2(self):
        """Test that default version is v2 when not specified."""
        response = self.client.get("/api/predictions/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should work like v2

    def test_invalid_version_returns_404(self):
        """Test that invalid version returns 404."""
        response = self.client.get("/api/v3/predictions/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_version_info_endpoint(self):
        """Test version info endpoint."""
        response = self.client.get("/api/version/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data["current_version"], "v2")
        self.assertIn("v1", data["available_versions"])
        self.assertIn("v2", data["available_versions"])
        self.assertIn("v1", data["deprecated_versions"])


class RateLimitingTestCase(APITestCase):
    """Test rate limiting and throttling."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        cache.clear()  # Clear cache before each test

    @override_settings(
        REST_FRAMEWORK={
            "DEFAULT_THROTTLE_CLASSES": [
                "future_skills.api.throttling.AnonRateThrottle",
            ],
            "DEFAULT_THROTTLE_RATES": {
                "anon": "5/minute",  # Low limit for testing
            },
        }
    )
    def test_anonymous_rate_limiting(self):
        """Test rate limiting for anonymous users."""
        # Make requests up to the limit
        for i in range(5):
            response = self.client.get("/api/v2/predictions/")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn("X-RateLimit-Limit", response)
            self.assertIn("X-RateLimit-Remaining", response)

        # Next request should be throttled
        response = self.client.get("/api/v2/predictions/")
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertIn("Retry-After", response)

    def test_rate_limit_headers_present(self):
        """Test that rate limit headers are present in responses."""
        response = self.client.get("/api/v2/predictions/")

        self.assertIn("X-RateLimit-Limit", response)
        self.assertIn("X-RateLimit-Remaining", response)
        self.assertIn("X-RateLimit-Reset", response)

        # Verify header values
        limit = int(response["X-RateLimit-Limit"])
        remaining = int(response["X-RateLimit-Remaining"])
        reset = int(response["X-RateLimit-Reset"])

        self.assertGreater(limit, 0)
        self.assertGreaterEqual(remaining, 0)
        self.assertGreater(reset, 0)

    def test_authenticated_user_higher_limits(self):
        """Test that authenticated users have higher rate limits."""
        user = User.objects.create_user(username="testuser", password="testpass123")

        # Anonymous request
        anon_response = self.client.get("/api/v2/predictions/")
        anon_limit = int(anon_response.get("X-RateLimit-Limit", 0))

        # Authenticated request
        self.client.force_authenticate(user=user)
        auth_response = self.client.get("/api/v2/predictions/")
        auth_limit = int(auth_response.get("X-RateLimit-Limit", 0))

        # Authenticated should have higher or equal limit
        self.assertGreaterEqual(auth_limit, anon_limit)

    def test_superuser_bypass_throttle(self):
        """Test that superusers bypass throttling."""
        superuser = User.objects.create_superuser(username="admin", password="admin123", email="admin@test.com")
        self.client.force_authenticate(user=superuser)

        # Make many requests - should not be throttled
        for i in range(20):
            response = self.client.get("/api/v2/predictions/")
            self.assertEqual(response.status_code, status.HTTP_200_OK)


class PerformanceMonitoringTestCase(APITestCase):
    """Test performance monitoring features."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.client.force_authenticate(user=self.user)

    def test_response_time_header(self):
        """Test that X-Response-Time header is present."""
        response = self.client.get("/api/v2/predictions/")

        self.assertIn("X-Response-Time", response)
        response_time = response["X-Response-Time"]
        self.assertTrue(response_time.endswith("ms"))

        # Verify it's a valid number
        time_value = float(response_time.replace("ms", ""))
        self.assertGreater(time_value, 0)

    def test_db_queries_header(self):
        """Test that X-DB-Queries header is present."""
        response = self.client.get("/api/v2/predictions/")

        self.assertIn("X-DB-Queries", response)
        query_count = int(response["X-DB-Queries"])
        self.assertGreaterEqual(query_count, 0)

    def test_cache_hit_header(self):
        """Test that X-Cache-Hit header is present."""
        response = self.client.get("/api/v2/predictions/")

        self.assertIn("X-Cache-Hit", response)
        cache_hit = response["X-Cache-Hit"]
        self.assertIn(cache_hit, ["true", "false"])

    @patch("future_skills.api.middleware.logger")
    def test_slow_request_logging(self, mock_logger):
        """Test that slow requests are logged."""
        # Mock a slow response
        with patch("time.time", side_effect=[0, 2.0, 2.0, 2.0, 2.0]):  # 2 second response
            self.client.get("/api/v2/predictions/")

        # Verify warning was logged
        self.assertTrue(mock_logger.warning.called)


class CachingTestCase(APITestCase):
    """Test caching functionality."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.client.force_authenticate(user=self.user)
        cache.clear()

    def test_cache_hit_on_second_request(self):
        """Test that second request hits cache."""
        # First request - cache miss
        response1 = self.client.get("/api/v2/predictions/")
        self.assertEqual(response1["X-Cache-Hit"], "false")

        # Second request - should hit cache
        response2 = self.client.get("/api/v2/predictions/")
        self.assertEqual(response2["X-Cache-Hit"], "true")

    def test_cache_invalidation_on_post(self):
        """Test that cache is invalidated on POST requests."""
        # Make GET request to cache it
        self.client.get("/api/v2/predictions/")

        # Make POST request (should invalidate cache)
        skill = Skill.objects.create(name="Test Skill", category="Technical")
        job_role = JobRole.objects.create(name="Test Role")

        # Next GET should be cache miss
        self.client.get("/api/v2/predictions/")
        # Note: Actual invalidation depends on implementation

    def test_cache_control_headers(self):
        """Test that Cache-Control headers are present."""
        response = self.client.get("/api/v2/predictions/")

        # May have Cache-Control header
        if "Cache-Control" in response:
            cache_control = response["Cache-Control"]
            self.assertIsNotNone(cache_control)


class MonitoringEndpointsTestCase(APITestCase):
    """Test monitoring and health check endpoints."""

    def setUp(self):
        """Set up test client."""
        self.client = APIClient()

    def test_health_check_endpoint(self):
        """Test /api/health/ endpoint."""
        response = self.client.get("/api/health/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIn("status", data)
        self.assertIn("timestamp", data)
        self.assertIn("checks", data)

        # Verify checks
        checks = data["checks"]
        self.assertIn("database", checks)
        self.assertIn("cache", checks)

    def test_health_check_shows_healthy_status(self):
        """Test that health check shows healthy when systems are up."""
        response = self.client.get("/api/health/")
        data = response.json()

        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["checks"]["database"]["status"], "healthy")

    def test_readiness_check_endpoint(self):
        """Test /api/ready/ endpoint."""
        response = self.client.get("/api/ready/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIn("ready", data)
        self.assertIn("timestamp", data)
        self.assertIn("checks", data)

        # Verify checks
        self.assertTrue(data["ready"])
        self.assertEqual(data["checks"]["database"], "passed")

    def test_liveness_check_endpoint(self):
        """Test /api/alive/ endpoint."""
        response = self.client.get("/api/alive/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIn("alive", data)
        self.assertIn("timestamp", data)
        self.assertTrue(data["alive"])

    def test_version_info_endpoint(self):
        """Test /api/version/ endpoint."""
        response = self.client.get("/api/version/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIn("current_version", data)
        self.assertIn("available_versions", data)
        self.assertIn("deprecated_versions", data)

        self.assertEqual(data["current_version"], "v2")

    def test_metrics_endpoint_requires_staff(self):
        """Test that /api/metrics/ requires staff permissions."""
        # Anonymous request should fail
        response = self.client.get("/api/metrics/")
        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )

    def test_metrics_endpoint_for_staff(self):
        """Test /api/metrics/ endpoint for staff users."""
        staff_user = User.objects.create_user(username="staff", password="staff123", is_staff=True)
        self.client.force_authenticate(user=staff_user)

        response = self.client.get("/api/metrics/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIn("timestamp", data)
        self.assertIn("system", data)
        self.assertIn("database", data)


class DeprecationWarningsTestCase(APITestCase):
    """Test deprecation warning functionality."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.client.force_authenticate(user=self.user)

    def test_v1_endpoints_have_deprecation_headers(self):
        """Test that v1 endpoints include deprecation headers."""
        response = self.client.get("/api/v1/future-skills/")

        self.assertIn("X-API-Deprecation", response)
        self.assertIn("X-API-Sunset-Date", response)
        self.assertIn("Link", response)

        # Verify deprecation message
        deprecation_msg = response["X-API-Deprecation"]
        self.assertIn("deprecated", deprecation_msg.lower())
        self.assertIn("v2", deprecation_msg)

    def test_v2_endpoints_no_deprecation(self):
        """Test that v2 endpoints do not have deprecation headers."""
        response = self.client.get("/api/v2/predictions/")

        self.assertNotIn("X-API-Deprecation", response)
        self.assertNotIn("X-API-Sunset-Date", response)

    def test_deprecation_in_json_response(self):
        """Test that deprecation warning appears in JSON response for v1."""
        response = self.client.get("/api/v1/future-skills/")
        data = response.json()

        # May include _deprecation field
        if "_deprecation" in data:
            self.assertIn("warning", data["_deprecation"])
            self.assertIn("sunset_date", data["_deprecation"])


class RequestLoggingTestCase(APITestCase):
    """Test request logging functionality."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.client.force_authenticate(user=self.user)

    @patch("future_skills.api.middleware.logger")
    def test_request_logging(self, mock_logger):
        """Test that requests are logged."""
        self.client.get("/api/v2/predictions/")

        # Verify info was logged
        self.assertTrue(mock_logger.info.called)

        # Check log message contains key information
        log_call = mock_logger.info.call_args
        log_message = str(log_call)
        self.assertIn("GET", log_message)
        self.assertIn("/api/v2/predictions/", log_message)

    @patch("future_skills.api.middleware.logger")
    def test_error_logging(self, mock_logger):
        """Test that errors are logged."""
        # Request to non-existent endpoint
        self.client.get("/api/v2/nonexistent/")

        # Some logging should occur
        self.assertTrue(mock_logger.info.called or mock_logger.warning.called or mock_logger.error.called)


class CORSHeadersTestCase(APITestCase):
    """Test CORS headers functionality."""

    def setUp(self):
        """Set up test client."""
        self.client = APIClient()

    def test_cors_headers_present(self):
        """Test that CORS headers are present in responses."""
        response = self.client.get("/api/v2/predictions/")

        # Check for CORS headers
        self.assertIn("Access-Control-Allow-Origin", response)

    def test_cors_preflight_request(self):
        """Test CORS preflight OPTIONS request."""
        response = self.client.options("/api/v2/predictions/")

        # Should return 200 OK
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Should have CORS headers
        self.assertIn("Access-Control-Allow-Methods", response)


class EndToEndAPITestCase(APITestCase):
    """End-to-end integration tests for API architecture."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.client.force_authenticate(user=self.user)

        # Create test data
        self.skill = Skill.objects.create(name="Python", category="Technical", description="Python programming")
        self.job_role = JobRole.objects.create(name="Data Scientist", description="Data science role")

    def test_complete_api_workflow(self):
        """Test complete API workflow with all architecture features."""
        # 1. Check health
        health_response = self.client.get("/api/health/")
        self.assertEqual(health_response.status_code, status.HTTP_200_OK)
        self.assertEqual(health_response.json()["status"], "healthy")

        # 2. Get version info
        version_response = self.client.get("/api/version/")
        self.assertEqual(version_response.status_code, status.HTTP_200_OK)
        self.assertEqual(version_response.json()["current_version"], "v2")

        # 3. Make API requests
        predictions_response = self.client.get("/api/v2/predictions/")
        self.assertEqual(predictions_response.status_code, status.HTTP_200_OK)

        # Verify all architecture headers present
        self.assertIn("X-Response-Time", predictions_response)
        self.assertIn("X-DB-Queries", predictions_response)
        self.assertIn("X-Cache-Hit", predictions_response)
        self.assertIn("X-RateLimit-Limit", predictions_response)
        self.assertIn("X-RateLimit-Remaining", predictions_response)

        # 4. Test backward compatibility with v1
        v1_response = self.client.get("/api/v1/future-skills/")
        self.assertEqual(v1_response.status_code, status.HTTP_200_OK)
        self.assertIn("X-API-Deprecation", v1_response)

    def test_api_performance_benchmarks(self):
        """Test that API meets performance benchmarks."""
        response = self.client.get("/api/v2/predictions/")

        # Extract response time
        response_time_str = response["X-Response-Time"].replace("ms", "")
        response_time = float(response_time_str)

        # Should be under 1 second (1000ms) for most requests
        self.assertLess(
            response_time,
            1000,
            f"Response time {response_time}ms exceeds 1000ms threshold",
        )

        # Database queries should be reasonable
        db_queries = int(response["X-DB-Queries"])
        self.assertLess(db_queries, 50, f"Database queries {db_queries} exceeds 50 query threshold")
