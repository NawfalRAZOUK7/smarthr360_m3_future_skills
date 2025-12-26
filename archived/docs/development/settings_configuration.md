# Settings Configuration Guide

This document explains the environment-based settings structure for the SmartHR360 Future Skills project.

## Overview

The settings are split into multiple files to support different environments:

- **base.py**: Common settings shared across all environments
- **development.py**: Local development settings with debugging enabled
- **production.py**: Production settings with security and performance optimizations
- **test.py**: Testing settings optimized for automated tests

## Directory Structure

```
config/
├── settings/
│   ├── __init__.py
│   ├── base.py           # Base settings (common)
│   ├── development.py    # Development environment
│   ├── production.py     # Production environment
│   └── test.py          # Test environment
├── urls.py
├── wsgi.py              # Uses production settings
└── asgi.py              # Uses production settings
```

## Usage

### Running with Different Settings

**Development (default for manage.py):**

```bash
python manage.py runserver
# or explicitly:
python manage.py runserver --settings=config.settings.development
```

**Production:**

```bash
gunicorn config.wsgi:application --bind 0.0.0.0:8000
# or with manage.py:
python manage.py migrate --settings=config.settings.production
```

**Testing:**

```bash
pytest
# Tests automatically use config.settings.test via pytest.ini
```

### Environment Variables

Set the `DJANGO_SETTINGS_MODULE` environment variable to override defaults:

```bash
# For development
export DJANGO_SETTINGS_MODULE=config.settings.development

# For production
export DJANGO_SETTINGS_MODULE=config.settings.production

# For testing
export DJANGO_SETTINGS_MODULE=config.settings.test
```

## Settings Details

### Base Settings (base.py)

Contains common configuration shared across all environments:

- Installed apps
- Middleware
- Templates
- Password validators
- Internationalization
- REST Framework configuration
- ML model configuration
- Logging configuration

**Environment Variables Used:**

- `SECRET_KEY`: Django secret key (required in production)
- `DEBUG`: Debug mode (default: False)
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts
- `DATABASE_URL`: Database connection string (optional, overrides default)

### Development Settings (development.py)

Optimized for local development:

- `DEBUG = True`
- SQLite database (default)
- Console email backend
- Django Debug Toolbar (optional)
- Django Extensions
- CORS allows all origins
- Verbose logging

**Additional Apps:**

- `django_extensions`: Management command enhancements
- `debug_toolbar`: SQL query profiler and debugging panel (if installed)

### Production Settings (production.py)

Optimized for production deployment:

- `DEBUG = False`
- PostgreSQL database (via DATABASE_URL)
- SMTP email backend
- SSL/HTTPS enforcement
- HSTS headers
- Secure cookies
- Restricted CORS
- Error logging to file

**Security Features:**

- `SECURE_SSL_REDIRECT = True`
- `SESSION_COOKIE_SECURE = True`
- `CSRF_COOKIE_SECURE = True`
- `SECURE_HSTS_SECONDS = 31536000`
- `X_FRAME_OPTIONS = 'DENY'`

**Required Environment Variables:**

- `DATABASE_URL`: PostgreSQL connection string (required)
- `SECRET_KEY`: Secure random key (required)
- `ALLOWED_HOSTS`: Comma-separated domain list (required)
- `CORS_ALLOWED_ORIGINS`: Comma-separated origin list (optional)

**Email Configuration (optional):**

- `EMAIL_HOST`: SMTP server (default: smtp.gmail.com)
- `EMAIL_PORT`: SMTP port (default: 587)
- `EMAIL_HOST_USER`: Email username
- `EMAIL_HOST_PASSWORD`: Email password

### Test Settings (test.py)

Optimized for automated testing:

- In-memory SQLite database (`:memory:`)
- Fast password hasher (MD5)
- Email backend: in-memory
- Minimal logging
- ML features disabled by default
- Relaxed security settings

## Docker Integration

### Development (docker-compose.yml)

```yaml
environment:
  - DJANGO_SETTINGS_MODULE=config.settings.development
  - DATABASE_URL=postgresql://postgres:postgres@db:5432/smarthr360
```

### Production (docker-compose.prod.yml)

```yaml
environment:
  - DJANGO_SETTINGS_MODULE=config.settings.production
  - SECRET_KEY=${SECRET_KEY}
  - DATABASE_URL=postgresql://...
  - ALLOWED_HOSTS=${ALLOWED_HOSTS}
```

## Example .env Files

### Development (.env)

```env
DJANGO_SETTINGS_MODULE=config.settings.development
SECRET_KEY=dev-secret-key-not-for-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=sqlite:///db.sqlite3
```

### Production (.env.prod)

```env
DJANGO_SETTINGS_MODULE=config.settings.production
SECRET_KEY=your-super-secure-secret-key-here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DATABASE_URL=postgresql://user:password@host:5432/dbname
CORS_ALLOWED_ORIGINS=https://yourdomain.com

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Security
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
```

## Migration Guide

### From Single settings.py

If you were using the old single `config/settings.py`:

1. ✅ Settings have been split automatically
2. ✅ `manage.py` now uses `config.settings.development`
3. ✅ `wsgi.py` and `asgi.py` use `config.settings.production`
4. ✅ `pytest.ini` uses `config.settings.test`
5. ✅ Docker configs updated with appropriate settings

### Testing the Migration

```bash
# Test development settings
python manage.py check --settings=config.settings.development

# Test production settings (requires DATABASE_URL)
DATABASE_URL=sqlite:///db.sqlite3 python manage.py check --settings=config.settings.production

# Test test settings
python manage.py check --settings=config.settings.test

# Run all tests
pytest
```

## Best Practices

1. **Never commit sensitive data**: Use `.env` files (add to `.gitignore`)
2. **Use environment variables**: For all environment-specific values
3. **Test production settings**: Before deploying
4. **Keep base.py DRY**: Don't duplicate settings across environments
5. **Document custom settings**: Add comments for team understanding
6. **Use strong SECRET_KEY**: Generate with `python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'`

## Troubleshooting

### Issue: "DJANGO_SETTINGS_MODULE is not set"

**Solution:** Set the environment variable or use `--settings` flag

### Issue: "DATABASE_URL is required in production"

**Solution:** Set `DATABASE_URL` environment variable

### Issue: "ALLOWED_HOSTS validation failed"

**Solution:** Add your domain to `ALLOWED_HOSTS` environment variable

### Issue: Tests not using test settings

**Solution:** Check `pytest.ini` has `DJANGO_SETTINGS_MODULE = config.settings.test`

## References

- [Django Settings Documentation](https://docs.djangoproject.com/en/stable/topics/settings/)
- [Deployment Checklist](https://docs.djangoproject.com/en/stable/howto/deployment/checklist/)
- [12-Factor App Config](https://12factor.net/config)
