"""
Django base settings for config project.

This module contains common settings shared across all environments.
Environment-specific settings are in development.py, production.py, and test.py
"""

from pathlib import Path

import dj_database_url
from decouple import Csv, config

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent


# SECURITY WARNING: keep the secret key used in production secret!
# SECRET_KEY must be set in environment variables or .env file
SECRET_KEY = config('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
# This should be overridden in environment-specific settings
DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party apps
    'rest_framework',
    'rest_framework_simplejwt',  # JWT authentication
    'rest_framework_simplejwt.token_blacklist',  # Token blacklist
    'corsheaders',  # CORS headers
    'axes',  # Login attempt tracking
    'drf_spectacular',  # OpenAPI documentation

    # Monitoring & APM
    'django_prometheus',  # Prometheus metrics
    'health_check',  # Health check endpoints
    'health_check.db',
    'health_check.cache',
    'health_check.storage',

    # Project apps
    'future_skills',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django_prometheus.middleware.PrometheusBeforeMiddleware',  # Prometheus - start
    'config.security_middleware.SecurityHeadersMiddleware',  # Security headers
    'corsheaders.middleware.CorsMiddleware',  # CORS - must be before CommonMiddleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'log_request_id.middleware.RequestIDMiddleware',  # Request ID tracking
    'config.logging_middleware.CorrelationIdMiddleware',  # Correlation ID
    'config.logging_middleware.RequestLoggingMiddleware',  # Request logging
    'config.logging_middleware.PerformanceMonitoringMiddleware',  # Performance monitoring
    'config.logging_middleware.APMContextMiddleware',  # APM context
    'config.security_middleware.SecurityEventLoggingMiddleware',  # Security logging
    'config.security_middleware.RateLimitMiddleware',  # Rate limiting
    'axes.middleware.AxesMiddleware',  # Login protection - must be after AuthenticationMiddleware
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # API Performance & Monitoring Middleware
    'future_skills.api.middleware.APIPerformanceMiddleware',
    'future_skills.api.middleware.RequestLoggingMiddleware',
    'future_skills.api.middleware.APIDeprecationMiddleware',
    'config.security_middleware.SecurityAuditMiddleware',  # Security audit
    'config.logging_middleware.ErrorTrackingMiddleware',  # Error tracking
    'django_prometheus.middleware.PrometheusAfterMiddleware',  # Prometheus - end
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases
# Database configuration should be overridden in environment-specific settings

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Support for DATABASE_URL environment variable (used in Docker/production)
DATABASE_URL = config('DATABASE_URL', default=None)
if DATABASE_URL:
    DATABASES['default'] = dj_database_url.parse(DATABASE_URL)


# Cache Configuration
# https://docs.djangoproject.com/en/5.2/topics/cache/
# Default: local memory cache (development)
# Production: Redis (configured via CACHE_URL environment variable)

CACHE_URL = config('CACHE_URL', default=None)

if CACHE_URL:
    # Use Redis or Memcached from CACHE_URL
    import django_redis
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': CACHE_URL,
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                'SOCKET_CONNECT_TIMEOUT': 5,
                'SOCKET_TIMEOUT': 5,
                'CONNECTION_POOL_KWARGS': {'max_connections': 50},
                'IGNORE_EXCEPTIONS': True,  # Fallback to database if cache fails
            },
            'KEY_PREFIX': 'smarthr360',
            'TIMEOUT': 300,  # Default 5 minutes
        }
    }
else:
    # Local memory cache for development
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'smarthr360-cache',
            'TIMEOUT': 300,
            'OPTIONS': {
                'MAX_ENTRIES': 1000,
            },
        }
    }


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 12,  # Stronger minimum length
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Use Argon2 password hasher (more secure than PBKDF2)
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = []

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",  # JWT first
        "rest_framework.authentication.SessionAuthentication",
        # BasicAuthentication removed for security (use JWT or Session)
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # API Versioning
    "DEFAULT_VERSIONING_CLASS": "future_skills.api.versioning.URLPathVersioning",
    "DEFAULT_VERSION": "v2",
    "ALLOWED_VERSIONS": ["v1", "v2"],
    # Rate Limiting / Throttling
    "DEFAULT_THROTTLE_CLASSES": [
        "future_skills.api.throttling.BurstRateThrottle",
        "future_skills.api.throttling.SustainedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/hour",
        "user": "1000/hour",
        "burst": "60/min",
        "sustained": "10000/day",
        "premium": "5000/hour",
        "ml_operations": "10/hour",
        "bulk_operations": "30/hour",
        "health_check": "300/min",
    },
}

# drf-spectacular settings for OpenAPI documentation
SPECTACULAR_SETTINGS = {
    'TITLE': 'SmartHR360 Future Skills API',
    'DESCRIPTION': '''Comprehensive API for SmartHR360 Future Skills prediction system.

## Features

### Prediction System
- **ML-Powered Predictions**: Machine learning models for future skill requirements
- **Rules-Based Fallback**: Reliable fallback when ML is unavailable
- **Batch Processing**: Efficient bulk predictions for large datasets
- **Real-time Recalculation**: On-demand prediction updates

### Training & MLOps
- **Model Training**: Async training with Celery integration
- **Version Control**: Track model versions and performance
- **Monitoring**: Comprehensive logging and drift detection
- **Explainability**: SHAP-based explanations for predictions

### HR Management
- **Employee Management**: Full CRUD operations with skill tracking
- **Bulk Import**: CSV/Excel file import with validation
- **Skill Recommendations**: Personalized training recommendations
- **Investment Planning**: HR investment recommendations based on predictions

### Analytics & Reporting
- **Market Trends**: Industry skill trend analysis
- **Economic Reports**: Economic indicators and impact
- **Performance Metrics**: Model accuracy and coverage metrics

## Authentication

All endpoints require authentication. Use Session or Basic Authentication.

### Permissions
- **HR Staff** (DRH/Responsable RH): Full access including recalculation and training
- **Manager**: Read access to predictions and team data
- **Authenticated**: Limited read access

## Rate Limiting

No rate limiting currently applied. Consider implementing for production.
    ''',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayOperationId': True,
        'filter': True,
    },
    'COMPONENT_SPLIT_REQUEST': True,
    'SORT_OPERATIONS': False,
    'SERVE_PERMISSIONS': ['rest_framework.permissions.IsAuthenticated'],
    'TAGS': [
        {'name': 'Predictions', 'description': 'Future skill predictions and recalculation'},
        {'name': 'Training', 'description': 'ML model training and management'},
        {'name': 'Employees', 'description': 'Employee management and skill tracking'},
        {'name': 'Analytics', 'description': 'Market trends and economic reports'},
        {'name': 'Recommendations', 'description': 'HR investment and skill recommendations'},
        {'name': 'Bulk Operations', 'description': 'Batch processing and file imports'},
    ],
}

# --- Module 3 : Future Skills / Machine Learning ---

# Active ou non l'utilisation du modèle ML pour les prédictions
FUTURE_SKILLS_USE_ML = True  # mets True quand tu es prêt à tester le ML

# Chemin vers le modèle entraîné (pipeline scikit-learn)
FUTURE_SKILLS_MODEL_PATH = BASE_DIR / "ml" / "models" / "future_skills_model.pkl"

# Chemin vers le dataset d'entraînement
FUTURE_SKILLS_DATASET_PATH = BASE_DIR / "ml" / "data" / "future_skills_dataset.csv"

# Version logique du modèle (utile pour la traçabilité dans PredictionRun.parameters)
FUTURE_SKILLS_MODEL_VERSION = "ml_random_forest_v1"

# MLOps: Monitoring et drift detection
FUTURE_SKILLS_ENABLE_MONITORING = True  # Active le logging des prédictions pour drift detection
FUTURE_SKILLS_MONITORING_LOG = BASE_DIR / "logs" / "predictions_monitoring.jsonl"

# --- Celery Configuration (Section 2.5 - Enhanced with Monitoring) ---

# Celery broker and backend (Redis)
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')

# Celery task settings
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes max per task
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60  # 25 minutes soft limit
CELERY_WORKER_PREFETCH_MULTIPLIER = 1  # Disable prefetch for long tasks
CELERY_WORKER_MAX_TASKS_PER_CHILD = 50  # Restart worker after 50 tasks

# Celery result expiration
CELERY_RESULT_EXPIRES = 3600  # Results expire after 1 hour

# Store task results in Django database (django-celery-results)
CELERY_RESULT_BACKEND = 'django-db'
CELERY_CACHE_BACKEND = 'django-cache'

# Task events for monitoring
CELERY_SEND_TASK_SENT_EVENT = True
CELERY_SEND_EVENTS = True
CELERY_TASK_SEND_SENT_EVENT = True

# Task routing (optional - route specific tasks to specific queues)
CELERY_TASK_ROUTES = {
    'future_skills.train_model': {'queue': 'training'},
    'future_skills.cleanup_old_models': {'queue': 'maintenance'},
}

# Default queue
CELERY_TASK_DEFAULT_QUEUE = 'default'
CELERY_TASK_DEFAULT_EXCHANGE = 'default'
CELERY_TASK_DEFAULT_ROUTING_KEY = 'default'

# Worker settings
CELERY_WORKER_SEND_TASK_EVENTS = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_WORKER_MAX_TASKS_PER_CHILD = 50
CELERY_WORKER_MAX_MEMORY_PER_CHILD = 200000  # 200MB

# Retry settings (default for all tasks)
CELERY_TASK_ACKS_LATE = True  # Acknowledge task after execution
CELERY_TASK_REJECT_ON_WORKER_LOST = True  # Reject task if worker dies

# Beat scheduler (for periodic tasks)
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# Celery Beat schedule (periodic tasks)
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    # Cleanup old models daily at 2 AM
    'cleanup-old-models-daily': {
        'task': 'future_skills.cleanup_old_models',
        'schedule': crontab(hour=2, minute=0),
        'kwargs': {'days_to_keep': 30}
    },
    # Cleanup old task executions weekly
    'cleanup-task-executions-weekly': {
        'task': 'celery_monitoring.cleanup_task_executions',
        'schedule': crontab(hour=3, minute=0, day_of_week=0),  # Sunday 3 AM
        'kwargs': {'days': 7}
    },
    # Cleanup old dead letter tasks monthly
    'cleanup-dead-letter-monthly': {
        'task': 'celery_monitoring.cleanup_dead_letter',
        'schedule': crontab(hour=4, minute=0, day_of_month=1),  # 1st of month 4 AM
        'kwargs': {'days': 30}
    },
}

# --- JWT Configuration (Simple JWT) ---

from datetime import timedelta

SIMPLE_JWT = {
    # Token Lifetimes
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),

    # Rotation & Blacklist
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,

    # Security
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': 'smarthr360',

    # Token Claims
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',

    # Token Behavior
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',

    # Additional Claims
    'JTI_CLAIM': 'jti',  # JWT ID for token tracking
}

# --- CORS Configuration ---

CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:3000,http://localhost:8000',
    cast=Csv()
)

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# --- Security Settings ---

# Session Security
SESSION_COOKIE_SECURE = not DEBUG  # HTTPS only in production
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 3600  # 1 hour

# CSRF Security
CSRF_COOKIE_SECURE = not DEBUG  # HTTPS only in production
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_TRUSTED_ORIGINS = config(
    'CSRF_TRUSTED_ORIGINS',
    default='http://localhost:3000,http://localhost:8000',
    cast=Csv()
)

# Security Headers
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# HTTPS Settings (production only)
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# Content Security Policy
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'")  # Adjust as needed
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")
CSP_IMG_SRC = ("'self'", "data:", "https:")
CSP_FONT_SRC = ("'self'", "data:")
CSP_CONNECT_SRC = ("'self'",)
CSP_FRAME_ANCESTORS = ("'none'",)

# Django Axes Configuration (Login Protection)
AXES_ENABLED = True
AXES_FAILURE_LIMIT = 5  # Lock after 5 failed attempts
AXES_COOLOFF_TIME = timedelta(minutes=30)  # Lock duration
AXES_LOCK_OUT_BY_COMBINATION_USER_AND_IP = True
AXES_RESET_ON_SUCCESS = True

# ============================================================================
# LOGGING & MONITORING CONFIGURATION
# ============================================================================

# Import logging configuration
from config.logging_config import get_structlog_config, setup_logging
import os

# Setup structured logging
# This will be initialized in wsgi.py and asgi.py
LOGGING = get_structlog_config(use_json=os.getenv('ENVIRONMENT', 'development').lower() == 'production')

# ============================================================================
# ELASTIC APM CONFIGURATION
# ============================================================================

from config.apm_config import get_elastic_apm_config

ELASTIC_APM = get_elastic_apm_config()

# ============================================================================
# SENTRY CONFIGURATION
# ============================================================================

# Sentry is initialized in wsgi.py and asgi.py via config.apm_config.initialize_apm()

# ============================================================================
# PROMETHEUS METRICS
# ============================================================================

# Prometheus metrics are automatically exported at /metrics endpoint
# Configure what to export
PROMETHEUS_EXPORT_MIGRATIONS = False
PROMETHEUS_LATENCY_BUCKETS = (0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0)

# ============================================================================
# HEALTH CHECK CONFIGURATION
# ============================================================================

# Health check endpoints at /health/
HEALTH_CHECK = {
    'DISK_USAGE_MAX': 90,  # Percent
    'MEMORY_MIN': 100,  # MB
}
            'level': 'INFO',
            'propagate': False,
        },
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
}
