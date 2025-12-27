"""API health check and monitoring endpoints.

Provides endpoints for system health checks, version info, and metrics.
"""

import platform
import sys

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from ..permissions import IsSecurityAdmin

class HealthCheckView(APIView):
    """Health check endpoint for monitoring and load balancers.

    GET /api/health/

    Returns:
        200 OK: System is healthy
        503 Service Unavailable: System has issues

    Response includes:
    - Overall status
    - Database connectivity
    - Cache availability
    - System info
    """

    permission_classes = [AllowAny]
    throttle_classes = []  # No throttling for health checks

    def get(self, request):
        """Check system health."""
        health_data = {
            "status": "healthy",
            "timestamp": timezone.now().isoformat(),
            "checks": {},
        }

        # Check database
        db_healthy = self._check_database()
        health_data["checks"]["database"] = {
            "status": "healthy" if db_healthy else "unhealthy",
            "type": settings.DATABASES["default"]["ENGINE"],
        }

        # Check cache
        cache_healthy = self._check_cache()
        health_data["checks"]["cache"] = {
            "status": "healthy" if cache_healthy else "unhealthy",
        }

        # Overall status
        all_healthy = db_healthy and cache_healthy
        health_data["status"] = "healthy" if all_healthy else "degraded"

        # Return appropriate status code
        response_status = status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

        return Response(health_data, status=response_status)

    def _check_database(self):
        """Check database connectivity."""
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            return True
        except Exception:
            return False

    def _check_cache(self):
        """Check cache availability."""
        try:
            cache.set("health_check", "ok", 10)
            value = cache.get("health_check")
            return value == "ok"
        except Exception:
            return False


class VersionInfoView(APIView):
    """API version information endpoint.

    GET /api/version/

    Returns:
    - Current API version
    - Supported versions
    - Deprecated versions
    - Changelog
    """

    permission_classes = [AllowAny]

    def get(self, request):
        """Get version information."""
        from .versioning import get_version_info

        version_data = get_version_info()
        # Provide explicit keys expected by tests
        version_data["current_version"] = version_data.get("current", "v2")
        version_data.setdefault("available_versions", version_data.get("supported", []))
        version_data.setdefault("deprecated_versions", version_data.get("deprecated", []))
        version_data.update(
            {
                "server_time": timezone.now().isoformat(),
                "python_version": sys.version,
                "django_version": self._get_django_version(),
            }
        )

        return Response(version_data)

    def _get_django_version(self):
        """Get Django version."""
        import django

        return django.get_version()


class MetricsView(APIView):
    """API metrics endpoint for monitoring.

    GET /api/metrics/

    Requires authentication.
    Only accessible to security admins.

    Returns:
    - Request counts
    - Error rates
    - Response times
    - Database stats
    """

    permission_classes = [IsSecurityAdmin]

    def get(self, request):
        """Get API metrics."""
        metrics = {
            "timestamp": timezone.now().isoformat(),
            "system": self._get_system_metrics(),
            "database": self._get_database_metrics(),
            "cache": self._get_cache_metrics(),
            "api": self._get_api_metrics(),
        }

        return Response(metrics)

    def _get_system_metrics(self):
        """Get system-level metrics."""
        return {
            "platform": platform.platform(),
            "python_version": sys.version,
            "cpu_count": platform.machine(),
        }

    def _get_database_metrics(self):
        """Get database metrics."""
        try:
            with connection.cursor() as cursor:
                # Get table count
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM sqlite_master
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                """
                )
                table_count = cursor.fetchone()[0]

            return {
                "status": "connected",
                "engine": settings.DATABASES["default"]["ENGINE"],
                "table_count": table_count,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    def _get_cache_metrics(self):
        """Get cache metrics."""
        try:
            # Test cache
            test_key = "metrics_test"
            cache.set(test_key, "test", 10)
            cache.get(test_key)
            cache.delete(test_key)

            return {
                "status": "available",
                "backend": settings.CACHES["default"]["BACKEND"],
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    def _get_api_metrics(self):
        """Get API-specific metrics."""
        from future_skills.models import Employee, FutureSkillPrediction, JobRole, Skill

        return {
            "models": {
                "skills": Skill.objects.count(),
                "job_roles": JobRole.objects.count(),
                "predictions": FutureSkillPrediction.objects.count(),
                "employees": Employee.objects.count(),
            },
            "rate_limits": self._get_rate_limit_info(),
        }

    def _get_rate_limit_info(self):
        """Get rate limit configuration."""
        from .throttling import get_throttle_rates

        return get_throttle_rates()


class ReadyCheckView(APIView):
    """Readiness check endpoint for Kubernetes/container orchestration.

    GET /api/ready/

    Similar to health check but includes more thorough checks.
    Used to determine if the service is ready to accept traffic.
    """

    permission_classes = [AllowAny]
    throttle_classes = []

    def get(self, request):
        """Check if service is ready."""
        checks = {
            "database": self._check_database(),
            "cache": self._check_cache(),
        }

        # Only check migrations in production
        from django.conf import settings

        if settings.DEBUG or getattr(settings, "ENVIRONMENT", "development") != "production":
            checks["migrations"] = True  # Skip migration check in development
        else:
            checks["migrations"] = self._check_migrations()

        all_ready = all(checks.values())

        ready_data = {
            "ready": all_ready,
            "timestamp": timezone.now().isoformat(),
            "checks": {key: "passed" if value else "failed" for key, value in checks.items()},
        }

        response_status = status.HTTP_200_OK if all_ready else status.HTTP_503_SERVICE_UNAVAILABLE
        return Response(ready_data, status=response_status)

    def _check_database(self):
        """Check database connectivity."""
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            return True
        except Exception:
            return False

    def _check_migrations(self):
        """Check if all migrations are applied."""
        from django.db.migrations.executor import MigrationExecutor

        try:
            executor = MigrationExecutor(connection)
            plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
            return len(plan) == 0
        except Exception:
            return False

    def _check_cache(self):
        """Check cache availability."""
        try:
            cache.set("ready_check", "ok", 10)
            value = cache.get("ready_check")
            cache.delete("ready_check")
            return value == "ok"
        except Exception:
            return False


class LivenessCheckView(APIView):
    """Liveness check endpoint for Kubernetes/container orchestration.

    GET /api/alive/

    Simple endpoint to check if the service is running.
    Does not perform deep checks, just returns 200 OK.
    """

    permission_classes = [AllowAny]
    throttle_classes = []

    def get(self, request):
        """Check if service is alive."""
        return Response(
            {
                "alive": True,
                "timestamp": timezone.now().isoformat(),
            }
        )
