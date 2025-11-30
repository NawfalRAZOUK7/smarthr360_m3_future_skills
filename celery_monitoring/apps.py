"""Celery Monitoring application configuration."""

from django.apps import AppConfig


class CeleryMonitoringConfig(AppConfig):
    """Configuration for the Celery Monitoring application."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "celery_monitoring"
    verbose_name = "Celery Monitoring"
