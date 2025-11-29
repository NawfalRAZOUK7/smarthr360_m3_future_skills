# Environment Configuration Guide

## Overview

SmartHR360 Future Skills uses environment variables for configuration management, following the [12-factor app](https://12factor.net/config) methodology. This ensures secure, flexible, and environment-specific configuration without hardcoding sensitive values.

## Quick Start

### 1. Create Environment File

```bash
# Copy the example file
cp .env.example .env

# Edit with your values
nano .env
```

### 2. Generate Secret Key

```bash
# Generate a secure Django secret key
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 3. Validate Configuration

```bash
# Validate current configuration
python manage.py validate_config

# Validate for specific environment
python manage.py validate_config --env production

# Show current configuration
python manage.py validate_config --info
```

## Environment Variables Reference

### Core Django Settings

#### SECRET_KEY (REQUIRED)

**Type:** String  
**Required:** Yes (all environments)  
**Min Length:** 50 characters (recommended)

Django's secret key for cryptographic signing. Must be kept secret and unique per installation.

```env
SECRET_KEY=django-insecure-your-secret-key-here-at-least-50-chars
```

**Security Notes:**

- Never commit to version control
- Use different keys for each environment
- Rotate periodically in production
- Generate using Django's utility (see Quick Start)

#### DEBUG

**Type:** Boolean  
**Default:** False  
**Required:** No

Enables Django debug mode. **MUST be False in production.**

```env
DEBUG=True   # Development only
DEBUG=False  # Production (default)
```

**Warning:** Debug mode exposes sensitive information. Never enable in production!

#### ALLOWED_HOSTS

**Type:** Comma-separated list  
**Default:** localhost,127.0.0.1  
**Required:** Yes (production)

Domains/IPs that this Django site can serve.

```env
# Development
ALLOWED_HOSTS=localhost,127.0.0.1

# Production
ALLOWED_HOSTS=example.com,www.example.com,api.example.com
```

### Database Configuration

#### DATABASE_URL

**Type:** Database URL  
**Required:** Yes (production, recommended for all)  
**Format:** `<engine>://<user>:<password>@<host>:<port>/<database>`

Database connection string. Supports PostgreSQL, MySQL, SQLite.

```env
# SQLite (development)
DATABASE_URL=sqlite:///db.sqlite3

# PostgreSQL (production recommended)
DATABASE_URL=postgresql://user:password@localhost:5432/smarthr360

# PostgreSQL with SSL
DATABASE_URL=postgresql://user:password@host:5432/smarthr360?sslmode=require

# Docker PostgreSQL
DATABASE_URL=postgresql://postgres:postgres@db:5432/smarthr360
```

**Production Recommendations:**

- Use PostgreSQL for better performance and features
- Enable SSL/TLS connections
- Use managed database services (AWS RDS, Azure Database, etc.)
- Configure connection pooling

### Celery Configuration

#### CELERY_BROKER_URL

**Type:** URL  
**Default:** redis://localhost:6379/0  
**Required:** Recommended

Message broker for Celery task queue. Supports Redis, RabbitMQ.

```env
# Redis (recommended)
CELERY_BROKER_URL=redis://localhost:6379/0

# Redis with password
CELERY_BROKER_URL=redis://:password@localhost:6379/0

# RabbitMQ
CELERY_BROKER_URL=amqp://user:password@localhost:5672//

# Redis Sentinel (high availability)
CELERY_BROKER_URL=sentinel://localhost:26379;sentinel://localhost:26380
```

#### CELERY_RESULT_BACKEND

**Type:** URL  
**Default:** redis://localhost:6379/0  
**Required:** Recommended

Backend for storing task results.

```env
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### Machine Learning Configuration

#### FUTURE_SKILLS_USE_ML

**Type:** Boolean  
**Default:** True  
**Required:** No

Enable or disable ML predictions. Falls back to rules-based predictions when False.

```env
FUTURE_SKILLS_USE_ML=True   # Use ML models
FUTURE_SKILLS_USE_ML=False  # Use rules-based fallback
```

**Use Cases:**

- Set to False during development if ML models aren't trained yet
- Set to False as fallback if ML service is unavailable
- Set to True in production for optimal predictions

### CORS Configuration

#### CORS_ALLOWED_ORIGINS

**Type:** Comma-separated list  
**Required:** Recommended (if using separate frontend)  
**Default:** Empty

Allowed origins for Cross-Origin Resource Sharing.

```env
# Development
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080

# Production
CORS_ALLOWED_ORIGINS=https://app.example.com,https://www.example.com
```

### Email Configuration

#### EMAIL_BACKEND

**Type:** String  
**Default:** console (dev), smtp (production)

Email backend to use.

```env
# Console (development)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# SMTP (production)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend

# File (testing)
EMAIL_BACKEND=django.core.mail.backends.filebased.EmailBackend
```

#### SMTP Settings

```env
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@example.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@smarthr360.com
```

**Provider Examples:**

**Gmail:**

```env
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

Note: Create App Password at https://myaccount.google.com/apppasswords

**SendGrid:**

```env
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=your-sendgrid-api-key
```

**AWS SES:**

```env
EMAIL_HOST=email-smtp.us-east-1.amazonaws.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-smtp-username
EMAIL_HOST_PASSWORD=your-smtp-password
```

### Security Settings (Production)

#### SECURE_SSL_REDIRECT

**Type:** Boolean  
**Default:** True (production)

Redirect all HTTP requests to HTTPS.

```env
SECURE_SSL_REDIRECT=True
```

#### SESSION_COOKIE_SECURE

**Type:** Boolean  
**Default:** True (production)

Only send session cookies over HTTPS.

```env
SESSION_COOKIE_SECURE=True
```

#### CSRF_COOKIE_SECURE

**Type:** Boolean  
**Default:** True (production)

Only send CSRF cookies over HTTPS.

```env
CSRF_COOKIE_SECURE=True
```

#### SECURE_HSTS_SECONDS

**Type:** Integer  
**Default:** 31536000 (1 year)

HTTP Strict Transport Security duration.

```env
SECURE_HSTS_SECONDS=31536000  # 1 year
```

### Cache Configuration

#### CACHE_BACKEND

**Type:** String  
**Default:** django.core.cache.backends.locmem.LocMemCache

Cache backend for Django caching framework.

```env
# Local memory (development)
CACHE_BACKEND=django.core.cache.backends.locmem.LocMemCache

# Redis (production)
CACHE_BACKEND=django.core.cache.backends.redis.RedisCache

# Memcached (production)
CACHE_BACKEND=django.core.cache.backends.memcached.PyMemcacheCache
```

#### CACHE_LOCATION

**Type:** String  
**Required:** If using Redis/Memcached

```env
# Redis
CACHE_LOCATION=redis://localhost:6379/1

# Memcached
CACHE_LOCATION=127.0.0.1:11211
```

## Environment-Specific Configuration

### Development Environment

**File:** `.env` (local)

```env
SECRET_KEY=django-insecure-dev-key-only
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=sqlite:///db.sqlite3
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
FUTURE_SKILLS_USE_ML=False
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

**Run with:**

```bash
export DJANGO_SETTINGS_MODULE=config.settings.development
python manage.py runserver
```

### Production Environment

**File:** Environment variables (server/container)

```env
SECRET_KEY=<your-secure-production-key>
DEBUG=False
ALLOWED_HOSTS=example.com,www.example.com
DATABASE_URL=postgresql://user:pass@prod-db:5432/smarthr360?sslmode=require
CELERY_BROKER_URL=redis://redis-prod:6379/0
CELERY_RESULT_BACKEND=redis://redis-prod:6379/0
FUTURE_SKILLS_USE_ML=True
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.sendgrid.net
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=<your-api-key>
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
CORS_ALLOWED_ORIGINS=https://app.example.com
```

**Run with:**

```bash
export DJANGO_SETTINGS_MODULE=config.settings.production
gunicorn config.wsgi:application
```

### Test Environment

**File:** `.env.test` or environment variables

```env
SECRET_KEY=test-secret-key
DEBUG=False
DATABASE_URL=sqlite:///test_db.sqlite3
CELERY_BROKER_URL=memory://
CELERY_RESULT_BACKEND=cache+memory://
FUTURE_SKILLS_USE_ML=False
EMAIL_BACKEND=django.core.mail.backends.locmem.EmailBackend
```

**Run with:**

```bash
export DJANGO_SETTINGS_MODULE=config.settings.test
pytest
```

## Validation

### Automatic Validation

Add to your deployment pipeline:

```bash
# Validate before deployment
python manage.py validate_config --env production --exit-on-error

# If validation fails, deployment stops
```

### Manual Validation

```bash
# Validate current environment
python manage.py validate_config

# Validate specific environment
python manage.py validate_config --env production

# Show configuration info
python manage.py validate_config --info
```

### Python Script Validation

```python
from config.settings.validators import validate_environment

# Validate and print results
is_valid = validate_environment('production', exit_on_error=True)
```

## Security Best Practices

### 1. Secret Key Management

✅ **DO:**

- Generate unique keys per environment
- Use at least 50 characters
- Store in environment variables or secret managers
- Rotate keys periodically

❌ **DON'T:**

- Commit keys to version control
- Share keys between environments
- Use default/example keys
- Expose keys in logs

### 2. Environment Files

✅ **DO:**

- Keep `.env` in `.gitignore`
- Provide `.env.example` with safe defaults
- Document all variables
- Use secret management services (AWS Secrets Manager, Azure Key Vault)

❌ **DON'T:**

- Commit `.env` files
- Include real credentials in examples
- Use production credentials locally

### 3. Production Security

✅ **DO:**

- Enable all security settings (SSL, HSTS, secure cookies)
- Use HTTPS everywhere
- Validate configuration before deployment
- Monitor for security issues
- Use environment-specific settings

❌ **DON'T:**

- Run DEBUG=True in production
- Disable security features
- Use weak credentials
- Expose sensitive endpoints

## Troubleshooting

### Common Issues

#### 1. SECRET_KEY Not Set

**Error:**

```
django.core.exceptions.ImproperlyConfigured: The SECRET_KEY setting must not be empty.
```

**Solution:**

```bash
# Generate a new key
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# Add to .env
echo "SECRET_KEY=<generated-key>" >> .env
```

#### 2. Database Connection Failed

**Error:**

```
django.db.utils.OperationalError: could not connect to server
```

**Solution:**

```bash
# Check DATABASE_URL format
python manage.py validate_config --info

# Test connection
python manage.py dbshell
```

#### 3. ALLOWED_HOSTS Not Set

**Error:**

```
CommandError: You must set settings.ALLOWED_HOSTS if DEBUG is False.
```

**Solution:**

```env
# Add to .env
ALLOWED_HOSTS=your-domain.com,www.your-domain.com
```

#### 4. Celery Connection Failed

**Error:**

```
kombu.exceptions.OperationalError: [Errno 111] Connection refused
```

**Solution:**

```bash
# Check if Redis is running
redis-cli ping

# Start Redis
redis-server

# Or update CELERY_BROKER_URL in .env
```

## Additional Resources

- [Django Settings Documentation](https://docs.djangoproject.com/en/stable/ref/settings/)
- [12-Factor App Config](https://12factor.net/config)
- [Python Decouple](https://github.com/henriquebastos/python-decouple)
- [Django Security Checklist](https://docs.djangoproject.com/en/stable/howto/deployment/checklist/)

## Support

For configuration issues:

1. Run validation: `python manage.py validate_config`
2. Check documentation: `docs/CONFIGURATION.md`
3. Review logs: `logs/future_skills.log`
4. Contact team lead or DevOps
