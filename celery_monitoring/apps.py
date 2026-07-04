"""Django app configuration for Celery monitoring models."""

from django.apps import AppConfig


class CeleryMonitoringConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "celery_monitoring"
    verbose_name = "Celery monitoring"
