"""
Production settings for SmartHR360 Future Skills project.

This configuration is optimized for production deployment with security enabled.
"""

import os
from .base import *  # noqa: F403,S2208 - Standard Django settings pattern

# Debug mode MUST be False in production
DEBUG = False

# Allowed hosts must be explicitly set
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='', cast=Csv())
if not ALLOWED_HOSTS:
    raise ValueError("ALLOWED_HOSTS environment variable must be set in production")

# Security settings for production
SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=True, cast=bool)
SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default=True, cast=bool)
CSRF_COOKIE_SECURE = config('CSRF_COOKIE_SECURE', default=True, cast=bool)
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# HSTS settings (HTTP Strict Transport Security)
SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', default=31536000, cast=int)  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Production database (PostgreSQL recommended)
# DATABASE_URL should be set in environment variables
if not config('DATABASE_URL', default=None):
    raise ValueError("DATABASE_URL environment variable is required in production")

# Production email backend
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default=EMAIL_HOST_USER)

# CORS settings for production (restrict to specific origins)
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='', cast=Csv())
CORS_ALLOW_CREDENTIALS = True

# Static files (using WhiteNoise or cloud storage)
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'

# Media files (should use cloud storage in production)
# Consider using django-storages with S3/Azure/GCS
# DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

# Logging - less verbose in production, log to file
LOGGING['handlers']['file']['level'] = 'WARNING'
LOGGING['loggers']['future_skills']['level'] = 'INFO'
LOGGING['loggers']['django']['level'] = 'WARNING'

# Production-specific logging to track errors
LOGGING['handlers']['error_file'] = {
    'class': 'logging.FileHandler',
    'filename': BASE_DIR / 'logs' / 'errors.log',
    'formatter': 'verbose',
    'level': 'ERROR',
}
LOGGING['loggers']['django.request'] = {
    'handlers': ['error_file', 'console'],
    'level': 'ERROR',
    'propagate': False,
}

# ML settings for production
FUTURE_SKILLS_USE_ML = True
FUTURE_SKILLS_ENABLE_MONITORING = True

# Cache configuration (using Redis in production)
CACHES = {
    'default': {
        'BACKEND': config('CACHE_BACKEND', default='django.core.cache.backends.locmem.LocMemCache'),
        'LOCATION': config('CACHE_LOCATION', default='unique-snowflake'),
    }
}

# Session configuration
SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Strict'

# CSRF configuration
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Strict'

print("⚡ Running in PRODUCTION mode")
