"""
Development settings for SmartHR360 Future Skills project.

This configuration is optimized for local development with debugging tools enabled.
"""

from .base import *  # noqa: F403,S2208 - Standard Django settings pattern

# Debug mode
DEBUG = True

# Allowed hosts for development
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "::1", "0.0.0.0"]  # nosec B104

# Development apps (optional - install if needed)
DEVELOPMENT_APPS = []

# Django Extensions (optional - install with: pip install django-extensions)
try:
    pass

    DEVELOPMENT_APPS.append("django_extensions")
except ImportError:
    pass

INSTALLED_APPS += DEVELOPMENT_APPS

# Development middleware
MIDDLEWARE += []

# Debug toolbar configuration (optional - install with: pip install django-debug-toolbar)
try:
    pass

    INSTALLED_APPS += ["debug_toolbar"]
    MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")
    INTERNAL_IPS = ["127.0.0.1", "::1"]
    DEBUG_TOOLBAR_CONFIG = {
        "SHOW_TOOLBAR_CALLBACK": lambda request: DEBUG,
    }
except ImportError:
    pass

# Relax login protection in dev (avoid Axes lockouts during automated tests)
MIDDLEWARE = [mw for mw in MIDDLEWARE if mw != "axes.middleware.AxesMiddleware"]
AXES_ENABLED = False

# Development database (SQLite for simplicity)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Console email backend for development
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# CORS settings for development (allow all origins in dev)
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# Security settings (relaxed for development)
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Static files
STATICFILES_DIRS = []

# Logging - more verbose in development
LOGGING["handlers"]["console"]["level"] = "DEBUG"
LOGGING["loggers"]["future_skills"]["level"] = "DEBUG"

# ML settings for development (default to rules-only unless explicitly enabled)
FUTURE_SKILLS_USE_ML = config("FUTURE_SKILLS_USE_ML", default=False, cast=bool)
FUTURE_SKILLS_ENABLE_MONITORING = True

print("🚀 Running in DEVELOPMENT mode")

# Validate configuration (only show warnings, don't exit)
try:
    from .validators import EnvironmentValidator

    validator = EnvironmentValidator("development")
    validator.validate_all()
    if validator.warnings:
        print("\n⚠️  Configuration Warnings:")
        for warning in validator.warnings[:3]:  # Show first 3
            print(f"  {warning}")
        if len(validator.warnings) > 3:
            print(f"  ... and {len(validator.warnings) - 3} more")
        print("  Run 'python manage.py validate_config' for full details\n")
except ImportError:
    pass  # Validators not available yet
