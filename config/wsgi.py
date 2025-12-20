"""
WSGI config for config project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

from config.apm_config import initialize_apm
from config.logging_config import setup_logging

# Use the settings module set by environment variable or default
settings_module = os.environ.get(
    "DJANGO_SETTINGS_MODULE", "config.settings.development"
)
with open("/app/debug_wsgi.log", "w") as f:
    f.write(f"WSGI: DJANGO_SETTINGS_MODULE is: {settings_module}\n")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module)

# Initialize Django application
application = get_wsgi_application()

# Initialize logging and monitoring

setup_logging()
initialize_apm()
