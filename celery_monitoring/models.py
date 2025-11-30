"""
Django models for Celery monitoring.

Register these models in your app's models.py or create a separate app.
"""

from django.db import models

from celery_monitoring.dead_letter import DeadLetterTask
from celery_monitoring.monitoring import TaskExecution

# These models are automatically created when celery_monitoring is imported
# They will be registered with Django's ORM

__all__ = ["TaskExecution", "DeadLetterTask"]
