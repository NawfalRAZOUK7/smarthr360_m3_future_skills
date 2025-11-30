"""
Celery configuration for SmartHR360 M3 Future Skills project.

This module sets up Celery for asynchronous task processing.
Tasks are used for long-running operations like ML model training.

Usage:
    # Start Celery worker
    celery -A config worker --loglevel=info

    # Start Celery beat (for scheduled tasks)
    celery -A config beat --loglevel=info
"""

import os
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

# Create Celery app
app = Celery("smarthr360_future_skills")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix in Django settings.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django apps.
# This will automatically discover tasks.py files in all INSTALLED_APPS.
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task to verify Celery is working correctly."""
    print(f"Request: {self.request!r}")
