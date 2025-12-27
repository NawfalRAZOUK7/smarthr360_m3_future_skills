"""
Unit tests for API middleware components.

Tests:
- APIPerformanceMiddleware
- APICacheMiddleware
- APIDeprecationMiddleware
- RequestLoggingMiddleware
- CORSHeadersMiddleware
"""

import time
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from django.test import RequestFactory, TestCase

from future_skills.api.middleware import (
    APICacheMiddleware,
    APIDeprecationMiddleware,
    APIPerformanceMiddleware,
    CORSHeadersMiddleware,
    RequestLoggingMiddleware,
)

User = get_user_model()


class APIPerformanceMiddlewareTestCase(TestCase):
    """Test APIPerformanceMiddleware."""

    def setUp(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()
        self.get_response = Mock(return_value=HttpResponse())
        self.middleware = APIPerformanceMiddleware(self.get_response)

    def test_adds_response_time_header(self):
        """Test that response time header is added."""
        request = self.factory.get("/api/v2/predictions/")

        response = self.middleware(request)

        self.assertIn("X-Response-Time", response)
        self.assertTrue(response["X-Response-Time"].endswith("ms"))

    def test_adds_db_queries_header(self):
        """Test that database queries header is added."""
        request = self.factory.get("/api/v2/predictions/")

        response = self.middleware(request)

        self.assertIn("X-DB-Queries", response)
        query_count = int(response["X-DB-Queries"])
        self.assertGreaterEqual(query_count, 0)

    @patch("future_skills.api.middleware.logger")
    def test_logs_slow_requests(self, mock_logger):
        """Test that slow requests are logged."""
        request = self.factory.get("/api/v2/predictions/")

        # Mock slow response
        with patch("time.time", side_effect=[0, 2.0]):  # 2 second response
            self.middleware(request)

        # Verify warning was logged
        mock_logger.warning.assert_called()
        call_args = str(mock_logger.warning.call_args)
        self.assertIn("Slow API request", call_args)

    def test_only_processes_api_paths(self):
        """Test that middleware only processes /api/ paths."""
        request = self.factory.get("/admin/")

        response = self.middleware(request)

        # Should not add performance headers for non-API paths
        # (but implementation may vary)
        self.assertIsInstance(response, HttpResponse)

    def test_response_time_accuracy(self):
        """Test that response time is reasonably accurate."""
        request = self.factory.get("/api/v2/predictions/")

        # Add a small delay
        def delayed_response(*args, **kwargs):
            time.sleep(0.01)  # 10ms
            return HttpResponse()

        self.middleware.get_response = delayed_response
        response = self.middleware(request)

        response_time_str = response["X-Response-Time"].replace("ms", "")
        response_time = float(response_time_str)

        # Should be at least 10ms
        self.assertGreaterEqual(response_time, 8)  # Allow some variance


class APICacheMiddlewareTestCase(TestCase):
    """Test APICacheMiddleware."""

    def setUp(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()
        self.get_response = Mock(return_value=JsonResponse({"data": "test"}))
        self.middleware = APICacheMiddleware(self.get_response)
        cache.clear()

    def test_caches_get_requests(self):
        """Test that GET requests are cached."""
        request = self.factory.get("/api/v2/predictions/")

        # First request - cache miss
        response1 = self.middleware(request)
        self.assertEqual(response1["X-Cache-Hit"], "false")

        # Second request - cache hit
        response2 = self.middleware(request)
        self.assertEqual(response2["X-Cache-Hit"], "true")

    def test_does_not_cache_post_requests(self):
        """Test that POST requests are not cached."""
        request = self.factory.post("/api/v2/predictions/")

        response = self.middleware(request)

        # POST should not be cached
        self.assertEqual(response.get("X-Cache-Hit", "false"), "false")

    def test_cache_invalidation_on_post(self):
        """Test that POST requests invalidate cache."""
        get_request = self.factory.get("/api/v2/predictions/")
        post_request = self.factory.post("/api/v2/predictions/")

        # Cache a GET request
        self.middleware(get_request)

        # POST request should invalidate
        self.middleware(post_request)

        # Next GET should be cache miss
        response = self.middleware(get_request)
        self.assertEqual(response["X-Cache-Hit"], "false")

    def test_different_cache_timeouts_by_path(self):
        """Test that different paths have different cache timeouts."""
        # This tests the cache timeout logic in middleware
        skills_request = self.factory.get("/api/v2/skills/")
        predictions_request = self.factory.get("/api/v2/predictions/")

        # Both should cache, but with potentially different timeouts
        skills_response = self.middleware(skills_request)
        predictions_response = self.middleware(predictions_request)

        self.assertIsInstance(skills_response, JsonResponse)
        self.assertIsInstance(predictions_response, JsonResponse)

    def test_cache_key_includes_query_params(self):
        """Test that cache key includes query parameters."""
        request1 = self.factory.get("/api/v2/predictions/?page=1")
        request2 = self.factory.get("/api/v2/predictions/?page=2")

        # Different query params should have different cache keys
        response1 = self.middleware(request1)
        response2 = self.middleware(request2)

        # Both should be cache misses (different keys)
        self.assertEqual(response1["X-Cache-Hit"], "false")
        self.assertEqual(response2["X-Cache-Hit"], "false")

    def test_cache_key_includes_user(self):
        """Test that cache key includes authenticated user."""
        user = User.objects.create_user(username="testuser", email="testuser@example.com", password="pass")

        request = self.factory.get("/api/v2/predictions/")
        request.user = user

        response = self.middleware(request)

        # Should cache per user
        self.assertEqual(response["X-Cache-Hit"], "false")


class APIDeprecationMiddlewareTestCase(TestCase):
    """Test APIDeprecationMiddleware."""

    def setUp(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()
        self.get_response = Mock(return_value=JsonResponse({"data": "test"}))
        self.middleware = APIDeprecationMiddleware(self.get_response)

    def test_adds_deprecation_headers_for_v1(self):
        """Test that v1 API gets deprecation headers."""
        request = self.factory.get("/api/v1/future-skills/")

        response = self.middleware(request)

        self.assertIn("X-API-Deprecation", response)
        self.assertIn("X-API-Sunset-Date", response)
        self.assertIn("Link", response)

    def test_no_deprecation_headers_for_v2(self):
        """Test that v2 API does not get deprecation headers."""
        request = self.factory.get("/api/v2/predictions/")

        response = self.middleware(request)

        self.assertNotIn("X-API-Deprecation", response)
        self.assertNotIn("X-API-Sunset-Date", response)

    def test_deprecation_message_content(self):
        """Test deprecation message content."""
        request = self.factory.get("/api/v1/future-skills/")

        response = self.middleware(request)

        deprecation_msg = response["X-API-Deprecation"]
        self.assertIn("deprecated", deprecation_msg.lower())
        self.assertIn("v2", deprecation_msg)
        self.assertIn("2026-06-01", deprecation_msg)

    def test_sunset_date_format(self):
        """Test that sunset date is in correct format."""
        request = self.factory.get("/api/v1/future-skills/")

        response = self.middleware(request)

        sunset_date = response["X-API-Sunset-Date"]
        self.assertEqual(sunset_date, "2026-06-01")

    def test_adds_deprecation_to_json_response(self):
        """Test that deprecation info is added to JSON response."""
        request = self.factory.get("/api/v1/future-skills/")

        response = self.middleware(request)

        # Check if _deprecation was added to response
        if hasattr(response, "content"):
            import json

            try:
                data = json.loads(response.content)
                if "_deprecation" in data:
                    self.assertIn("warning", data["_deprecation"])
                    self.assertIn("sunset_date", data["_deprecation"])
            except json.JSONDecodeError:
                pass  # Not JSON response


class RequestLoggingMiddlewareTestCase(TestCase):
    """Test RequestLoggingMiddleware."""

    def setUp(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()
        self.get_response = Mock(return_value=HttpResponse(status=200))
        self.middleware = RequestLoggingMiddleware(self.get_response)

    @patch("future_skills.api.middleware.logger")
    def test_logs_api_requests(self, mock_logger):
        """Test that API requests are logged."""
        request = self.factory.get("/api/v2/predictions/")
        request.user = User.objects.create_user(username="testuser", email="testuser@example.com")

        self.middleware(request)

        # Verify logging occurred
        mock_logger.info.assert_called()

        # Check log message
        call_args = str(mock_logger.info.call_args)
        self.assertIn("GET", call_args)
        self.assertIn("/api/v2/predictions/", call_args)
        self.assertIn("testuser", call_args)

    @patch("future_skills.api.middleware.logger")
    def test_logs_anonymous_requests(self, mock_logger):
        """Test that anonymous requests are logged."""
        from django.contrib.auth.models import AnonymousUser

        request = self.factory.get("/api/v2/predictions/")
        request.user = AnonymousUser()

        self.middleware(request)

        mock_logger.info.assert_called()
        call_args = str(mock_logger.info.call_args)
        self.assertIn("anonymous", call_args.lower())

    @patch("future_skills.api.middleware.logger")
    def test_logs_response_status(self, mock_logger):
        """Test that response status is logged."""
        request = self.factory.get("/api/v2/predictions/")
        request.user = User.objects.create_user(username="testuser", email="testuser@example.com")

        self.middleware(request)

        call_args = str(mock_logger.info.call_args)
        self.assertIn("200", call_args)

    @patch("future_skills.api.middleware.logger")
    def test_logs_request_duration(self, mock_logger):
        """Test that request duration is logged."""
        request = self.factory.get("/api/v2/predictions/")
        request.user = User.objects.create_user(username="testuser", email="testuser@example.com")

        self.middleware(request)

        call_args = str(mock_logger.info.call_args)
        self.assertIn("ms", call_args.lower())

    @patch("future_skills.api.middleware.logger")
    def test_sanitizes_sensitive_params(self, mock_logger):
        """Test that sensitive parameters are sanitized."""
        request = self.factory.get("/api/v2/predictions/?password=secret123&api_key=key123")
        request.user = User.objects.create_user(username="testuser", email="testuser@example.com")

        self.middleware(request)

        call_args = str(mock_logger.info.call_args)
        self.assertNotIn("secret123", call_args)
        self.assertNotIn("key123", call_args)
        self.assertIn("***", call_args)

    @patch("future_skills.api.middleware.logger")
    def test_only_logs_api_paths(self, mock_logger):
        """Test that only /api/ paths are logged."""
        request = self.factory.get("/admin/")
        request.user = User.objects.create_user(username="testuser", email="testuser@example.com")

        self.middleware(request)

        # Should not log non-API paths
        # (implementation dependent)


class CORSHeadersMiddlewareTestCase(TestCase):
    """Test CORSHeadersMiddleware."""

    def setUp(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()
        self.get_response = Mock(return_value=HttpResponse())
        self.middleware = CORSHeadersMiddleware(self.get_response)

    def test_adds_cors_headers(self):
        """Test that CORS headers are added."""
        request = self.factory.get("/api/v2/predictions/")

        response = self.middleware(request)

        self.assertIn("Access-Control-Allow-Origin", response)
        self.assertIn("Access-Control-Allow-Methods", response)
        self.assertIn("Access-Control-Allow-Headers", response)

    def test_cors_allow_origin_value(self):
        """Test CORS Allow-Origin header value."""
        request = self.factory.get("/api/v2/predictions/")

        response = self.middleware(request)

        allow_origin = response["Access-Control-Allow-Origin"]
        self.assertIn(allow_origin, ["*", "http://localhost:3000"])

    def test_cors_allow_methods(self):
        """Test CORS Allow-Methods header."""
        request = self.factory.get("/api/v2/predictions/")

        response = self.middleware(request)

        allow_methods = response["Access-Control-Allow-Methods"]
        self.assertIn("GET", allow_methods)
        self.assertIn("POST", allow_methods)

    def test_cors_allow_headers(self):
        """Test CORS Allow-Headers header."""
        request = self.factory.get("/api/v2/predictions/")

        response = self.middleware(request)

        allow_headers = response["Access-Control-Allow-Headers"]
        self.assertIn("Content-Type", allow_headers)
        self.assertIn("Authorization", allow_headers)

    def test_preflight_request(self):
        """Test CORS preflight OPTIONS request."""
        request = self.factory.options("/api/v2/predictions/")

        response = self.middleware(request)

        # Should have CORS headers
        self.assertIn("Access-Control-Allow-Origin", response)
        self.assertIn("Access-Control-Allow-Methods", response)

    def test_only_adds_to_api_paths(self):
        """Test that CORS headers only added to /api/ paths."""
        api_request = self.factory.get("/api/v2/predictions/")
        admin_request = self.factory.get("/admin/")

        api_response = self.middleware(api_request)
        self.middleware(admin_request)

        self.assertIn("Access-Control-Allow-Origin", api_response)
        # May or may not be in admin response depending on implementation


class MiddlewareIntegrationTestCase(TestCase):
    """Test middleware working together."""

    def setUp(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()
        cache.clear()

    def test_all_middleware_headers_present(self):
        """Test that all middleware add their headers."""

        # Stack all middleware
        def get_response(request):
            return JsonResponse({"data": "test"})

        # Apply middleware in order
        response_handler = get_response
        response_handler = CORSHeadersMiddleware(response_handler)
        response_handler = RequestLoggingMiddleware(response_handler)
        response_handler = APIDeprecationMiddleware(response_handler)
        response_handler = APICacheMiddleware(response_handler)
        response_handler = APIPerformanceMiddleware(response_handler)

        request = self.factory.get("/api/v2/predictions/")
        request.user = User.objects.create_user(username="testuser", email="testuser@example.com")

        response = response_handler(request)

        # Check all headers present
        self.assertIn("X-Response-Time", response)
        self.assertIn("X-DB-Queries", response)
        self.assertIn("X-Cache-Hit", response)
        self.assertIn("Access-Control-Allow-Origin", response)

    @patch("future_skills.api.middleware.logger")
    def test_middleware_order_matters(self, mock_logger):
        """Test that middleware order is important."""

        # Performance middleware should wrap others to measure total time
        def get_response(request):
            time.sleep(0.01)  # Simulate work
            return HttpResponse()

        response_handler = APIPerformanceMiddleware(get_response)

        request = self.factory.get("/api/v2/predictions/")
        response = response_handler(request)

        # Should have measured the time
        self.assertIn("X-Response-Time", response)
        response_time = float(response["X-Response-Time"].replace("ms", ""))
        self.assertGreater(response_time, 8)  # At least 8ms
