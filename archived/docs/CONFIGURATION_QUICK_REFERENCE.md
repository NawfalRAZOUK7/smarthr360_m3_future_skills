# Configuration Management - Quick Reference

## Quick Commands

### Validate Configuration

```bash
# Auto-detect environment and validate
python manage.py validate_config

# Validate specific environment
python manage.py validate_config --env production

# Show current configuration
python manage.py validate_config --info

# Exit with error code if validation fails (for CI/CD)
python manage.py validate_config --env production --exit-on-error
```

### Generate Secret Key

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### Setup Environment

```bash
# 1. Copy template
cp .env.example .env

# 2. Generate secret key (run above command)

# 3. Edit .env file
nano .env

# 4. Validate
python manage.py validate_config
```

## Environment Files

### Development (.env)

```env
SECRET_KEY=<your-generated-secret-key>
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=sqlite:///db.sqlite3
FUTURE_SKILLS_USE_ML=True
```

### Production (Environment Variables)

```env
SECRET_KEY=<secure-production-key>
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DATABASE_URL=postgresql://user:pass@host:5432/dbname
CELERY_BROKER_URL=redis://redis:6379/0
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

## Common Environment Variables

| Variable               | Required | Default                  | Description                      |
| ---------------------- | -------- | ------------------------ | -------------------------------- |
| `SECRET_KEY`           | ✅ Yes   | -                        | Django secret key (50+ chars)    |
| `DEBUG`                | No       | False                    | Debug mode (False in production) |
| `ALLOWED_HOSTS`        | ✅ Prod  | localhost,127.0.0.1      | Allowed hostnames                |
| `DATABASE_URL`         | ✅ Prod  | sqlite:///db.sqlite3     | Database connection              |
| `CELERY_BROKER_URL`    | No       | redis://localhost:6379/0 | Celery broker                    |
| `FUTURE_SKILLS_USE_ML` | No       | True                     | Enable ML predictions            |
| `CORS_ALLOWED_ORIGINS` | No       | -                        | CORS allowed origins             |

## Configuration Validation Checks

### All Environments

- ✅ SECRET_KEY exists and is valid
- ✅ SECRET_KEY length >= 50 characters
- ✅ ALLOWED_HOSTS configured
- ✅ DATABASE_URL format valid
- ✅ Celery URLs format valid
- ⚠️ ML model exists if USE_ML=True

### Production Only

- ❌ DEBUG must be False
- ❌ ALLOWED_HOSTS must be explicitly set
- ❌ DATABASE_URL is required
- ⚠️ PostgreSQL recommended
- ⚠️ Security settings enabled (SSL, HTTPS, secure cookies)
- ⚠️ CORS origins explicitly set

## Troubleshooting

### SECRET_KEY Not Set

```bash
# Error: The SECRET_KEY setting must not be empty
# Solution:
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
# Copy output to .env: SECRET_KEY=<generated-key>
```

### Database Connection Failed

```bash
# Check configuration
python manage.py validate_config --info

# Test connection
python manage.py dbshell
```

### Celery Not Connecting

```bash
# Check if Redis is running
redis-cli ping
# Should return: PONG

# Start Redis if needed
redis-server
```

### Production Validation Errors

```bash
# Run validation
python manage.py validate_config --env production

# Fix errors in environment variables
# Re-validate
python manage.py validate_config --env production --exit-on-error
```

## CI/CD Integration

### Pre-Deployment Check

```bash
# In your deployment pipeline
python manage.py validate_config --env production --exit-on-error || exit 1
python manage.py check --deploy
```

### Docker Example

```dockerfile
# Validate configuration before starting
RUN python manage.py validate_config --env production --exit-on-error
CMD ["gunicorn", "config.wsgi:application"]
```

## Security Checklist

### Development

- [x] SECRET_KEY set in .env
- [x] .env in .gitignore
- [x] Debug mode enabled locally only

### Production

- [x] SECRET_KEY unique and secure (50+ chars)
- [x] DEBUG=False
- [x] ALLOWED_HOSTS explicitly set
- [x] DATABASE_URL uses PostgreSQL with SSL
- [x] SECURE_SSL_REDIRECT=True
- [x] SESSION_COOKIE_SECURE=True
- [x] CSRF_COOKIE_SECURE=True
- [x] CORS_ALLOWED_ORIGINS explicitly set
- [x] Email backend configured
- [x] Configuration validated before deployment

## Documentation

- **Full Guide:** [docs/CONFIGURATION.md](CONFIGURATION.md)
- **Environment Variables:** [.env.example](../.env.example)
- **Settings Files:** [config/settings/](../config/settings/)
- **Validators:** [config/settings/validators.py](../config/settings/validators.py)
