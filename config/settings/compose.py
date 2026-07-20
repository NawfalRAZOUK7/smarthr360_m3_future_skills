"""Local Compose settings: production-like runtime over plain localhost HTTP."""

from .base import *  # noqa: F403,S2208 - standard Django settings pattern

DEBUG = False
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
FUTURE_SKILLS_USE_ML = config("FUTURE_SKILLS_USE_ML", default=False, cast=bool)  # noqa: F405
FUTURE_SKILLS_ENABLE_MONITORING = True
