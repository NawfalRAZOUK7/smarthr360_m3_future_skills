# Security Quick Reference - SmartHR360

# ======================================

## JWT Authentication Quick Commands

### Login (Get Tokens)

```bash
curl -X POST http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your_password"}'
```

### Refresh Token

```bash
curl -X POST http://localhost:8000/api/auth/token/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh":"<refresh_token>"}'
```

### Logout

```bash
curl -X POST http://localhost:8000/api/auth/logout/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"refresh":"<refresh_token>"}'
```

### Verify Token

```bash
curl -X POST http://localhost:8000/api/auth/verify/ \
  -H "Authorization: Bearer <access_token>"
```

### Use Token in Request

```bash
curl -H "Authorization: Bearer <access_token>" \
  http://localhost:8000/api/skills/
```

---

## Security Scanning Commands

### Run Full Security Scan

```bash
./scripts/security_scan.sh
```

### Individual Scans

```bash
# Dependency vulnerabilities
safety check
pip-audit --desc

# Code security
bandit -r . -ll --exclude '.venv,*/tests/*,*/migrations/*'

# SAST
semgrep --config=auto

# Django deployment check
python manage.py check --deploy
```

---

## Security Monitoring Commands

### View Security Events

```bash
# Last 24 hours
python manage.py monitor_security --hours 24

# Last 1000 entries
python manage.py monitor_security --tail 1000

# JSON output
python manage.py monitor_security --json
```

### Check Failed Logins (django-axes)

```bash
# List locked accounts
python manage.py axes_list_attempts

# Reset specific user
python manage.py axes_reset_username <username>

# Reset IP
python manage.py axes_reset_ip <ip>

# Reset all
python manage.py axes_reset
```

### View Logs

```bash
# Security log
tail -f logs/security.log

# Filter for errors
tail -f logs/security.log | grep ERROR

# Filter for specific event
tail -f logs/security.log | grep "auth_failure"
```

---

## Dependency Management

### Check for Updates

```bash
pip list --outdated
```

### Update Specific Package

```bash
pip install --upgrade package_name
```

### Update All (Development Only)

```bash
pip install --upgrade -r requirements.txt
```

### Freeze Current Versions

```bash
pip freeze > requirements_locked.txt
```

---

## Secret Management

### Generate Django SECRET_KEY

```bash
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

### Environment Variables

```bash
# .env file
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DATABASE_URL=postgresql://user:pass@localhost/db
CORS_ALLOWED_ORIGINS=https://yourdomain.com
```

---

## Production Security Checklist

### Pre-Deployment

- [ ] DEBUG=False in production
- [ ] Strong SECRET_KEY (50+ characters)
- [ ] ALLOWED_HOSTS configured
- [ ] Database uses SSL/TLS
- [ ] All secrets in environment variables
- [ ] HTTPS enforced (SECURE_SSL_REDIRECT=True)
- [ ] HSTS enabled
- [ ] Security headers configured
- [ ] CORS properly restricted
- [ ] Rate limiting enabled
- [ ] Dependencies up to date
- [ ] Security scan passed
- [ ] Backup strategy in place

### Post-Deployment

- [ ] HTTPS certificate valid
- [ ] Security headers present (check with curl -I)
- [ ] JWT authentication working
- [ ] Rate limiting functional
- [ ] Logging operational
- [ ] Monitoring alerts configured
- [ ] Incident response plan ready
- [ ] Team trained on security procedures

---

## Common Security Issues & Fixes

### 1. Hardcoded Secrets

```python
# ❌ BAD
SECRET_KEY = "django-insecure-hardcoded"

# ✅ GOOD
from decouple import config
SECRET_KEY = config('SECRET_KEY')
```

### 2. SQL Injection

```python
# ❌ BAD
User.objects.raw(f"SELECT * FROM users WHERE id = {user_id}")

# ✅ GOOD
User.objects.get(id=user_id)
```

### 3. XSS

```python
# ❌ BAD
html = f"<div>{user_input}</div>"

# ✅ GOOD
from django.utils.html import escape
html = f"<div>{escape(user_input)}</div>"
```

### 4. CSRF

```python
# ✅ Ensure CSRF middleware enabled
MIDDLEWARE = [
    'django.middleware.csrf.CsrfViewMiddleware',  # Required
]
```

### 5. Weak Passwords

```python
# ✅ Strong password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 12}},
]

# ✅ Use Argon2 hasher
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
]
```

---

## Emergency Response

### Compromised Account

```bash
# Disable account
python manage.py shell
>>> from django.contrib.auth.models import User
>>> user = User.objects.get(username='compromised')
>>> user.is_active = False
>>> user.save()
```

### Invalidate All JWT Tokens

```python
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
OutstandingToken.objects.all().delete()
```

### Block IP Address

```bash
# Temporarily (nginx)
sudo nginx -s reload

# Firewall
sudo ufw deny from 1.2.3.4
```

### Rotate SECRET_KEY

```bash
# 1. Generate new key
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'

# 2. Update .env
# 3. Restart application
# 4. All sessions invalidated
```

---

## Testing Security

### Test JWT Flow

```bash
# 1. Get token
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}' | jq -r .access)

# 2. Use token
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/skills/

# 3. Verify token
curl -X POST http://localhost:8000/api/auth/verify/ \
  -H "Authorization: Bearer $TOKEN"
```

### Test Rate Limiting

```bash
# Send many requests quickly
for i in {1..100}; do
  curl http://localhost:8000/api/skills/
done
# Should see 429 (Too Many Requests) after limit
```

### Test Security Headers

```bash
curl -I https://yourdomain.com
# Look for:
# - Strict-Transport-Security
# - X-Content-Type-Options: nosniff
# - X-Frame-Options: DENY
# - Content-Security-Policy
# - Permissions-Policy
```

---

## Useful Links

- Security Guide: `docs/SECURITY_GUIDE.md`
- Celery Monitoring: `docs/CELERY_MONITORING_GUIDE.md`
- API Documentation: `http://localhost:8000/api/schema/swagger-ui/`
- Django Security: https://docs.djangoproject.com/en/stable/topics/security/
- OWASP Top 10: https://owasp.org/www-project-top-ten/

---

## Environment Variables Reference

```bash
# Core Django
SECRET_KEY=                    # 50+ character random string
DEBUG=False                    # Never True in production
ALLOWED_HOSTS=domain.com,www.domain.com

# Database
DATABASE_URL=postgresql://user:pass@host:port/dbname?sslmode=require

# Cache/Celery
CACHE_URL=redis://localhost:6379/1
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=django-db

# Security
CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Optional
SENTRY_DSN=                    # Error tracking
LOG_LEVEL=INFO                 # Logging level
```

---

## Quick Health Check

```bash
# Application health
curl http://localhost:8000/api/health/

# Database connectivity
python manage.py dbshell --command="SELECT 1;"

# Celery workers
celery -A config inspect active

# Redis
redis-cli ping
```

---

**For detailed information, see:** `docs/SECURITY_GUIDE.md`  
**Report security issues to:** security@smarthr360.com
