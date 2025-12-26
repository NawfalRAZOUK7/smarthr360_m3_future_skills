"""
Test settings for SmartHR360 Future Skills project.

This configuration is optimized for running automated tests with pytest.
"""

import os

# Ensure required env defaults exist before importing base settings that expect them
os.environ["SECRET_KEY"] = os.environ.get("SECRET_KEY", "test-secret-key")
os.environ["DEBUG"] = "False"

from .base import *  # noqa: F403,S2208,E402 - Standard Django settings pattern

# Provide a deterministic secret key for tests so env vars aren't required
SECRET_KEY = config("SECRET_KEY", default="test-secret-key")  # noqa: F405
ALLOWED_HOSTS = ["*"]

# Debug mode for tests
DEBUG = True
TESTING = True

# Use lightweight, permissive auth for tests; explicit view permissions still apply
REST_FRAMEWORK = {
    **REST_FRAMEWORK,  # noqa: F405
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
    # Disable global throttling for most tests; specific tests override with @override_settings
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {},
}

# Locmem cache so caching/throttling tests have a working cache backend
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "future-skills-test-cache",
    }
}

# Test database (in-memory SQLite for speed)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Password hashers (use faster hasher for tests)
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]


# Disable migrations for tests (faster)
class DisableMigrations:
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None


# Uncomment to disable migrations in tests
# MIGRATION_MODULES = DisableMigrations()

# Email backend for tests
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Static files
STATIC_ROOT = BASE_DIR / "test_staticfiles"
MEDIA_ROOT = BASE_DIR / "test_media"

# Point ML datasets to a small, checked-in fixture so training API/tests can find it
ML_DATASETS_DIR = BASE_DIR / "tests/fixtures"
FUTURE_SKILLS_DATASET_PATH = ML_DATASETS_DIR / "future_skills_dataset.csv"

# Logging - minimal for tests
LOGGING["handlers"]["console"]["level"] = "ERROR"
LOGGING["loggers"]["future_skills"]["level"] = "ERROR"
LOGGING["loggers"]["django"]["level"] = "ERROR"

# Disable file logging in tests
LOGGING["handlers"]["file"] = {
    "class": "logging.NullHandler",
}

# ML settings for tests
FUTURE_SKILLS_USE_ML = False  # Disable ML predictions in tests by default
FUTURE_SKILLS_ENABLE_MONITORING = False  # Disable monitoring in tests

# CORS - allow all for tests
CORS_ALLOW_ALL_ORIGINS = True

# REST Framework settings for tests
REST_FRAMEWORK = {
    **REST_FRAMEWORK,  # inherit from base + overrides above
    "PAGE_SIZE": 10,
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
}

# Do not bypass throttling in tests; we want throttles to exercise
THROTTLE_BYPASS_IPS = []

# Security settings - relaxed for tests
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

print("🧪 Running in TEST mode")
