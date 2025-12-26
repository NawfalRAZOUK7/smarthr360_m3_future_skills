"""WSGI config for config project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os
from pathlib import Path

from django.core.wsgi import get_wsgi_application

from config.apm_config import initialize_apm
from config.logging_config import setup_logging

# Use the settings module set by environment variable or default
settings_module = os.environ.get("DJANGO_SETTINGS_MODULE", "config.settings.development")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module)

# Write a small debug hint without failing if the path is missing
try:
    debug_log_path = Path(__file__).resolve().parent.parent / "var" / "log" / "debug_wsgi.log"
    debug_log_path.parent.mkdir(parents=True, exist_ok=True)
    debug_log_path.write_text(f"WSGI: DJANGO_SETTINGS_MODULE is: {settings_module}\n")
except OSError:
    # Best effort only; continue startup
    pass

# Initialize Django application
application = get_wsgi_application()

# Initialize logging and monitoring
setup_logging()
initialize_apm()
