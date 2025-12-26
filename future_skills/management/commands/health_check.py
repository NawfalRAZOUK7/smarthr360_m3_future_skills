"""
System Health Check Management Command
Checks system health, dependencies, and application status.
"""

import sys
import time
from typing import Any, Dict

from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.db import connection

from config.logging_config import get_logger


class Command(BaseCommand):
    """Check system health and dependencies."""

    help = "Check system health, dependencies, and application status"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--json",
            action="store_true",
            help="Output in JSON format",
        )
        parser.add_argument(
            "--check",
            type=str,
            choices=["all", "database", "cache", "celery", "disk", "memory"],
            default="all",
            help="Specific check to run",
        )

    def __init__(self, *args, **kwargs):
        """Initialize command."""
        super().__init__(*args, **kwargs)
        self.logger = get_logger(__name__)

    def handle(self, *args, **options):
        """Execute command."""
        json_output = options["json"]
        check_type = options["check"]

        if not json_output:
            self.stdout.write(self.style.HTTP_INFO("=" * 80))
            self.stdout.write(self.style.HTTP_INFO("System Health Check"))
            self.stdout.write(self.style.HTTP_INFO("=" * 80))

        # Run checks
        results = {}

        if check_type in ["all", "database"]:
            results["database"] = self._check_database()

        if check_type in ["all", "cache"]:
            results["cache"] = self._check_cache()

        if check_type in ["all", "celery"]:
            results["celery"] = self._check_celery()

        if check_type in ["all", "disk"]:
            results["disk"] = self._check_disk()

        if check_type in ["all", "memory"]:
            results["memory"] = self._check_memory()

        # Calculate overall health
        results["overall"] = {
            "healthy": all(r.get("healthy", False) for r in results.values() if isinstance(r, dict)),
            "timestamp": time.time(),
        }

        # Output results
        if json_output:
            import json

            self.stdout.write(json.dumps(results, indent=2))
        else:
            self._print_results(results)

        # Exit with error if unhealthy
        if not results["overall"]["healthy"]:
            sys.exit(1)

    def _check_database(self) -> Dict[str, Any]:
        """Check database connectivity."""
        try:
            start_time = time.time()
            connection.ensure_connection()
            duration = time.time() - start_time

            result = {
                "healthy": True,
                "response_time": round(duration, 3),
                "message": "Database connection successful",
            }

            self.stdout.write(self.style.SUCCESS("✓ Database: OK"))

            return result

        except Exception as e:
            self.logger.error("database_health_check_failed", error=str(e), exc_info=True)

            self.stdout.write(self.style.ERROR(f"✗ Database: FAILED - {str(e)}"))

            return {
                "healthy": False,
                "error": str(e),
                "message": "Database connection failed",
            }

    def _check_cache(self) -> Dict[str, Any]:
        """Check cache connectivity."""
        try:
            start_time = time.time()

            # Test write
            cache.set("health_check", "test", 10)

            # Test read
            value = cache.get("health_check")

            duration = time.time() - start_time

            if value == "test":
                result = {
                    "healthy": True,
                    "response_time": round(duration, 3),
                    "message": "Cache working correctly",
                }

                self.stdout.write(self.style.SUCCESS("✓ Cache: OK"))

                return result
            else:
                raise Exception("Cache read/write mismatch")

        except Exception as e:
            self.logger.error("cache_health_check_failed", error=str(e), exc_info=True)

            self.stdout.write(self.style.ERROR(f"✗ Cache: FAILED - {str(e)}"))

            return {
                "healthy": False,
                "error": str(e),
                "message": "Cache check failed",
            }

    def _check_celery(self) -> Dict[str, Any]:
        """Check Celery worker status."""
        try:
            from celery import current_app

            # Inspect workers
            inspect = current_app.control.inspect()
            active = inspect.active()

            if active:
                worker_count = len(active)

                result = {
                    "healthy": True,
                    "worker_count": worker_count,
                    "workers": list(active.keys()),
                    "message": f"{worker_count} worker(s) active",
                }

                self.stdout.write(self.style.SUCCESS(f"✓ Celery: {worker_count} worker(s) active"))

                return result
            else:
                self.stdout.write(self.style.WARNING("⚠ Celery: No workers found"))

                return {
                    "healthy": False,
                    "worker_count": 0,
                    "message": "No Celery workers found",
                }

        except Exception as e:
            self.logger.error("celery_health_check_failed", error=str(e), exc_info=True)

            self.stdout.write(self.style.ERROR(f"✗ Celery: FAILED - {str(e)}"))

            return {
                "healthy": False,
                "error": str(e),
                "message": "Celery check failed",
            }

    def _check_disk(self) -> Dict[str, Any]:
        """Check disk usage."""
        try:
            import psutil

            disk = psutil.disk_usage("/")

            percent_used = disk.percent
            healthy = percent_used < 90  # Alert if > 90% used

            result = {
                "healthy": healthy,
                "total_gb": round(disk.total / (1024**3), 2),
                "used_gb": round(disk.used / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "percent_used": percent_used,
                "message": f"Disk {percent_used}% used",
            }

            if healthy:
                self.stdout.write(self.style.SUCCESS(f"✓ Disk: {percent_used}% used"))
            else:
                self.stdout.write(self.style.WARNING(f"⚠ Disk: {percent_used}% used (HIGH)"))

            return result

        except Exception as e:
            self.logger.error("disk_health_check_failed", error=str(e), exc_info=True)

            self.stdout.write(self.style.ERROR(f"✗ Disk: FAILED - {str(e)}"))

            return {
                "healthy": False,
                "error": str(e),
                "message": "Disk check failed",
            }

    def _check_memory(self) -> Dict[str, Any]:
        """Check memory usage."""
        try:
            import psutil

            memory = psutil.virtual_memory()

            percent_used = memory.percent
            healthy = percent_used < 90  # Alert if > 90% used

            result = {
                "healthy": healthy,
                "total_gb": round(memory.total / (1024**3), 2),
                "used_gb": round(memory.used / (1024**3), 2),
                "free_gb": round(memory.available / (1024**3), 2),
                "percent_used": percent_used,
                "message": f"Memory {percent_used}% used",
            }

            if healthy:
                self.stdout.write(self.style.SUCCESS(f"✓ Memory: {percent_used}% used"))
            else:
                self.stdout.write(self.style.WARNING(f"⚠ Memory: {percent_used}% used (HIGH)"))

            return result

        except Exception as e:
            self.logger.error("memory_health_check_failed", error=str(e), exc_info=True)

            self.stdout.write(self.style.ERROR(f"✗ Memory: FAILED - {str(e)}"))

            return {
                "healthy": False,
                "error": str(e),
                "message": "Memory check failed",
            }

    def _print_results(self, results: Dict[str, Any]):
        """Print results in human-readable format."""
        self.stdout.write("")
        self.stdout.write(self.style.HTTP_INFO("Summary:"))
        self.stdout.write(self.style.HTTP_INFO("-" * 80))

        if results["overall"]["healthy"]:
            self.stdout.write(self.style.SUCCESS("Overall Status: HEALTHY ✓"))
        else:
            self.stdout.write(self.style.ERROR("Overall Status: UNHEALTHY ✗"))

        self.stdout.write("")
