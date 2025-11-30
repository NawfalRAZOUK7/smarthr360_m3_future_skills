"""
Test settings for SmartHR360 Future Skills project.

This configuration is optimized for running automated tests with pytest.
"""

from .base import *  # noqa: F403,S2208 - Standard Django settings pattern

# Debug mode for tests
DEBUG = True

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
    **REST_FRAMEWORK,  # inherit from base
    "PAGE_SIZE": 10,
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
}

# Security settings - relaxed for tests
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

print("🧪 Running in TEST mode")
