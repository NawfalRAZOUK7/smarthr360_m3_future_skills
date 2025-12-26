"""
Test settings for SmartHR360 Future Skills project.

This configuration is optimized for running automated tests with pytest.
"""

from .base import *  # noqa: F403,S2208 - Standard Django settings pattern

# Debug mode for tests
DEBUG = True

# Use lightweight, permissive auth for tests to avoid 401s while still honoring view permissions
REST_FRAMEWORK = {
    **REST_FRAMEWORK,  # noqa: F405
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
    # Keep throttling enabled for throttle tests; use slightly lower rates for faster coverage
    "DEFAULT_THROTTLE_CLASSES": [
        "future_skills.api.throttling.AnonRateThrottle",
        "future_skills.api.throttling.UserRateThrottle",
        "future_skills.api.throttling.BurstRateThrottle",
        "future_skills.api.throttling.SustainedRateThrottle",
        "future_skills.api.throttling.PremiumUserThrottle",
        "future_skills.api.throttling.MLOperationsThrottle",
        "future_skills.api.throttling.BulkOperationsThrottle",
        "future_skills.api.throttling.HealthCheckThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "10/minute",
        "user": "20/minute",
        "burst": "5/minute",
        "sustained": "100/hour",
        "premium": "50/minute",
        "ml_operations": "5/minute",
        "bulk_operations": "3/minute",
        "health_check": "5/minute",
    },
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

# Bypass IP-based throttling for local test client
THROTTLE_BYPASS_IPS = ["127.0.0.1", "::1"]

# Security settings - relaxed for tests
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

print("🧪 Running in TEST mode")
