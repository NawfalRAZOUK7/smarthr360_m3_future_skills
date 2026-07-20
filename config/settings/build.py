"""Minimal deterministic settings used only while building the container image."""

import os

os.environ.setdefault("SECRET_KEY", "build-only-not-for-runtime")

from .base import *  # noqa: E402,F403,S2208 - standard Django settings pattern

DEBUG = False
ALLOWED_HOSTS = ["localhost"]
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "build.sqlite3",  # noqa: F405
    }
}
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
FUTURE_SKILLS_USE_ML = False
FUTURE_SKILLS_ENABLE_MONITORING = False
STATICFILES_DIRS = []
LOGGING["handlers"]["file"] = {"class": "logging.NullHandler"}  # noqa: F405
