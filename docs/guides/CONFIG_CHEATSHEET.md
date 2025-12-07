# Configuration Management - Command Cheat Sheet

## 🚀 Quick Setup (New Project)

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Generate secret key
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# 3. Edit .env and paste secret key
nano .env  # or vim .env, code .env

# 4. Validate configuration
python manage.py validate_config

# 5. You're ready!
python manage.py runserver
```

---

## 🔍 Validation Commands

```bash
# Show current configuration
python manage.py validate_config --info

# Validate current environment (auto-detect)
python manage.py validate_config

# Validate specific environment
python manage.py validate_config --env development
python manage.py validate_config --env production
python manage.py validate_config --env test

# Exit with error if validation fails (CI/CD)
python manage.py validate_config --env production --exit-on-error
```

---

## ⚙️ Common Environment Variables

```env
# Required
SECRET_KEY=<50+ character secure key>
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_URL=sqlite:///db.sqlite3
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Celery (Task Queue)
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# ML
FUTURE_SKILLS_USE_ML=True

# Debug
DEBUG=True  # False in production!
```

---

## 🔧 Troubleshooting

```bash
# Check Django configuration
python manage.py check

# Check for deployment issues
python manage.py check --deploy

# Show environment info
python manage.py validate_config --info

# Test database connection
python manage.py dbshell

# Check Redis connection
redis-cli ping  # Should return: PONG
```

---

## 🔒 Production Checklist

```bash
# Before deployment, verify:
□ SECRET_KEY is unique and secure (50+ chars)
□ DEBUG=False
□ ALLOWED_HOSTS explicitly set
□ DATABASE_URL uses PostgreSQL
□ SECURE_SSL_REDIRECT=True
□ SESSION_COOKIE_SECURE=True
□ CSRF_COOKIE_SECURE=True

# Run validation
python manage.py validate_config --env production --exit-on-error

# Run deployment check
python manage.py check --deploy
```

---

## 📚 Documentation Links

- **Full Guide:** [docs/CONFIGURATION.md](docs/CONFIGURATION.md)
- **Quick Reference:** [docs/CONFIGURATION_QUICK_REFERENCE.md](docs/CONFIGURATION_QUICK_REFERENCE.md)
- **Implementation Summary:** [CONFIGURATION_IMPLEMENTATION_SUMMARY.md](CONFIGURATION_IMPLEMENTATION_SUMMARY.md)
- **Environment Template:** [.env.example](.env.example)

---

## 💡 Pro Tips

```bash
# Validate configuration before git commit
git add . && python manage.py validate_config && git commit -m "feat: ..."

# CI/CD pre-deployment check
python manage.py validate_config --env production --exit-on-error && \
python manage.py check --deploy && \
python manage.py collectstatic --noinput

# Quick environment check
python manage.py validate_config --info | grep -E "(Debug|Secret|Database|ML)"
```

---

**Need help?** Run `python manage.py validate_config --info` to see your current configuration.
