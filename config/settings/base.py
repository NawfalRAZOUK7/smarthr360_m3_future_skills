"""
Django base settings for config project.

This module contains common settings shared across all environments.
Environment-specific settings are in development.py, production.py, and test.py
"""

import os
from pathlib import Path
from decouple import config, Csv

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

    'rest_framework',  # << ajoute ça
    'drf_spectacular',  # OpenAPI documentation

    # Apps projet
    'future_skills',   # ⬅️ ajoute cette ligne
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
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
import dj_database_url
DATABASE_URL = config('DATABASE_URL', default=None)
if DATABASE_URL:
    DATABASES['default'] = dj_database_url.parse(DATABASE_URL)


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
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
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
        # plus tard, tu pourras ajouter JWT si tu veux
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
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

# --- Celery Configuration (Section 2.5) ---

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

# --- Django Logging Configuration ---

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {name} {module}.{funcName}: {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'simple': {
            'format': '[{levelname}] {name}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
            'level': 'DEBUG',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'future_skills.log',
            'formatter': 'verbose',
            'level': 'INFO',
        },
    },
    'loggers': {
        'future_skills': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'future_skills.services.prediction_engine': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'future_skills.services.recommendation_engine': {
            'handlers': ['console', 'file'],
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

