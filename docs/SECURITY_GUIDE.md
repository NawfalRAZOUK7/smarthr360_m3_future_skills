# Security Hardening Guide - SmartHR360

# =====================================

**Version:** 1.0  
**Last Updated:** November 2025  
**Status:** Production Ready

## Table of Contents

1. [Overview](#overview)
2. [JWT Authentication](#jwt-authentication)
3. [Security Headers](#security-headers)
4. [Vulnerability Scanning](#vulnerability-scanning)
5. [Security Monitoring](#security-monitoring)
6. [Best Practices](#best-practices)
7. [Incident Response](#incident-response)
8. [Compliance](#compliance)

---

## Overview

This guide covers the comprehensive security hardening implemented in SmartHR360, including JWT authentication, security headers, vulnerability scanning, and monitoring.

### Security Features Implemented

- **JWT Authentication**: Token-based authentication with rotation and blacklisting
- **Security Headers**: CSP, HSTS, X-Frame-Options, CORS
- **Password Security**: Argon2 hashing, strong validation
- **Rate Limiting**: Request throttling and login protection
- **Vulnerability Scanning**: Automated dependency and code scanning
- **Security Monitoring**: Event logging and suspicious activity detection
- **HTTPS Enforcement**: Production SSL/TLS requirements

---

## JWT Authentication

### Overview

JWT (JSON Web Tokens) provides stateless, secure authentication for the API.

### Configuration

```python
# Token Lifetimes
ACCESS_TOKEN_LIFETIME = 30 minutes
REFRESH_TOKEN_LIFETIME = 7 days

# Security Features
- Token rotation on refresh
- Automatic blacklisting of old tokens
- User information in token payload
- Issuer validation (smarthr360)
```

### Endpoints

#### 1. Obtain Token (Login)

```bash
POST /api/auth/token/
Content-Type: application/json

{
  "username": "your_username",
  "password": "your_password"
}

Response:
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": 1,
    "username": "your_username",
    "email": "user@example.com",
    "is_staff": false,
    "groups": ["Managers"]
  }
}
```

#### 2. Refresh Token

```bash
POST /api/auth/token/refresh/
Content-Type: application/json

{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}

Response:
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."  # New refresh token (rotation)
}
```

#### 3. Logout

```bash
POST /api/auth/logout/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}

Response:
{
  "message": "Successfully logged out"
}
```

#### 4. Verify Token

```bash
POST /api/auth/verify/
Authorization: Bearer <access_token>

Response:
{
  "valid": true,
  "user": {
    "id": 1,
    "username": "your_username",
    "email": "user@example.com"
  }
}
```

### Using JWT in Requests

```bash
# Include Bearer token in Authorization header
curl -H "Authorization: Bearer <access_token>" \
     https://api.smarthr360.com/api/skills/
```

```python
# Python example
import requests

headers = {
    'Authorization': f'Bearer {access_token}'
}
response = requests.get('https://api.smarthr360.com/api/skills/', headers=headers)
```

```javascript
// JavaScript example
fetch("https://api.smarthr360.com/api/skills/", {
  headers: {
    Authorization: `Bearer ${accessToken}`,
  },
});
```

### Token Claims

Access tokens include:

- `user_id`: User ID
- `username`: Username
- `email`: User email
- `is_staff`: Staff status
- `groups`: User groups/roles
- `exp`: Expiration timestamp
- `iat`: Issued at timestamp
- `jti`: JWT ID for tracking

### Security Best Practices

1. **Store Securely**

   - Never store tokens in localStorage (XSS vulnerable)
   - Use httpOnly cookies or secure memory storage
   - Clear tokens on logout

2. **Refresh Tokens**

   - Refresh access tokens before expiry
   - Implement automatic refresh in clients
   - Handle refresh failures gracefully

3. **Transmission**

   - Always use HTTPS in production
   - Never log or expose tokens
   - Use secure channels only

4. **Rotation**
   - Tokens rotate on refresh
   - Old refresh tokens are blacklisted
   - Supports logout across devices

---

## Security Headers

### Implemented Headers

#### 1. Content Security Policy (CSP)

```python
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'")
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")
CSP_IMG_SRC = ("'self'", "data:", "https:")
CSP_FRAME_ANCESTORS = ("'none'",)
```

**Purpose**: Prevents XSS attacks by controlling resource loading

#### 2. HTTP Strict Transport Security (HSTS)

```python
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
```

**Purpose**: Forces HTTPS connections

#### 3. X-Frame-Options

```python
X_FRAME_OPTIONS = 'DENY'
```

**Purpose**: Prevents clickjacking attacks

#### 4. X-Content-Type-Options

```python
SECURE_CONTENT_TYPE_NOSNIFF = True
```

**Purpose**: Prevents MIME type sniffing

#### 5. Referrer-Policy

```python
Referrer-Policy: strict-origin-when-cross-origin
```

**Purpose**: Controls referrer information

#### 6. Permissions-Policy

```python
Permissions-Policy: accelerometer=(), camera=(), geolocation=(), ...
```

**Purpose**: Restricts browser features

### CORS Configuration

```python
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'https://yourdomain.com',
]

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_HEADERS = [
    'authorization',
    'content-type',
    'x-csrftoken',
]
```

### Cookie Security

```python
# Session Cookies
SESSION_COOKIE_SECURE = True      # HTTPS only
SESSION_COOKIE_HTTPONLY = True    # No JavaScript access
SESSION_COOKIE_SAMESITE = 'Lax'   # CSRF protection

# CSRF Cookies
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'
```

---

## Vulnerability Scanning

### Automated Scanning Suite

Run comprehensive security scans:

```bash
./scripts/security_scan.sh
```

This executes:

1. **Safety** - Dependency vulnerability scanning
2. **pip-audit** - OSV database vulnerability checks
3. **Bandit** - Python code security analysis
4. **Semgrep** - SAST (Static Application Security Testing)
5. **Django Check** - Django deployment security
6. **Git Secrets** - Secret detection in repository

### Individual Scans

#### 1. Dependency Vulnerabilities

```bash
# Safety
safety check

# pip-audit
pip-audit --desc

# Both
pip install -r requirements.txt && safety check
```

#### 2. Code Security Analysis

```bash
# Bandit (Python security linter)
bandit -r . -ll --exclude '.venv,venv,*/tests/*,*/migrations/*'

# Detailed report
bandit -r . -f json -o security_reports/bandit_report.json
```

#### 3. SAST with Semgrep

```bash
# Auto configuration (recommended)
semgrep --config=auto

# Specific rulesets
semgrep --config=p/django
semgrep --config=p/python
semgrep --config=p/security-audit

# CI/CD integration
semgrep --config=auto --json --output=semgrep.json
```

#### 4. Django Security Check

```bash
# Production deployment check
python manage.py check --deploy

# Specific checks
python manage.py check --tag security
```

### Interpreting Results

#### Severity Levels

- **CRITICAL**: Immediate action required, production at risk
- **HIGH**: Fix within 24-48 hours
- **MEDIUM**: Fix within 1 week, assess risk
- **LOW**: Fix when convenient, minimal risk
- **INFO**: Informational, best practice suggestions

#### Common Issues

1. **Outdated Dependencies**

   ```bash
   # Update specific package
   pip install --upgrade package_name

   # Update all (careful in production)
   pip list --outdated
   pip install --upgrade -r requirements.txt
   ```

2. **Hardcoded Secrets**

   ```python
   # BAD
   SECRET_KEY = "hard-coded-secret-123"

   # GOOD
   from decouple import config
   SECRET_KEY = config('SECRET_KEY')
   ```

3. **SQL Injection Risks**

   ```python
   # BAD
   query = f"SELECT * FROM users WHERE id = {user_id}"

   # GOOD (Django ORM)
   User.objects.get(id=user_id)
   ```

4. **XSS Vulnerabilities**

   ```python
   # BAD
   html = f"<div>{user_input}</div>"

   # GOOD (Django template escaping)
   from django.utils.html import escape
   html = f"<div>{escape(user_input)}</div>"
   ```

### CI/CD Integration

```yaml
# .github/workflows/security.yml
name: Security Scan

on: [push, pull_request]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          pip install safety bandit pip-audit semgrep

      - name: Run Security Scan
        run: ./scripts/security_scan.sh

      - name: Upload Reports
        uses: actions/upload-artifact@v3
        with:
          name: security-reports
          path: security_reports/
```

---

## Security Monitoring

### Security Event Logging

All security events are logged to `logs/security.log` in JSON format.

#### Event Types

- `jwt_token_issued` - JWT token created
- `jwt_login_attempt` - Login attempt
- `jwt_login_success` - Successful login
- `jwt_login_failed` - Failed login
- `jwt_logout` - User logout
- `auth_failure` - 401/403 responses
- `suspicious_request` - Suspicious patterns detected
- `rate_limit_exceeded` - Rate limit hit
- `ip_blocked` - IP blocked
- `slow_request` - Request took >5s

### Monitoring Security Events

```bash
# View recent security events
python manage.py monitor_security --hours 24

# Last 1000 log entries
python manage.py monitor_security --tail 1000

# JSON output
python manage.py monitor_security --json > security_analysis.json
```

### Example Output

```
=== Security Event Analysis (Last 24 hours) ===

Total Events: 1,234

Event Types:
  authenticated_request: 980
  jwt_login_success: 45
  auth_failure: 12
  suspicious_request: 3

Security Metrics:
  Failed Authentication Attempts: 12
  Suspicious Activities: 3
  Rate Limited Requests: 0
  Blocked IPs: 0

Top IP Addresses:
  192.168.1.100: 456 requests
  192.168.1.101: 234 requests
```

### Login Protection (django-axes)

```python
# Configuration
AXES_FAILURE_LIMIT = 5           # Lock after 5 failures
AXES_COOLOFF_TIME = 30 minutes   # Lock duration
AXES_LOCK_OUT_BY_COMBINATION_USER_AND_IP = True
```

Check locked accounts:

```bash
# List locked accounts
python manage.py axes_list_attempts

# Reset specific user/IP
python manage.py axes_reset_username <username>
python manage.py axes_reset_ip <ip_address>

# Reset all
python manage.py axes_reset
```

### Real-time Monitoring

Set up monitoring alerts:

```python
# In settings.py - Add email handler for critical events
LOGGING = {
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
        },
    },
    'loggers': {
        'security': {
            'handlers': ['console', 'security_file', 'mail_admins'],
            'level': 'WARNING',
        },
    },
}
```

---

## Best Practices

### Development

1. **Environment Variables**

   ```bash
   # Use .env for secrets
   SECRET_KEY=your-secret-key-here
   DATABASE_URL=postgresql://user:pass@localhost/db

   # Never commit .env
   echo ".env" >> .gitignore
   ```

2. **Debug Mode**

   ```python
   # Never use DEBUG=True in production
   DEBUG = config('DEBUG', default=False, cast=bool)
   ```

3. **Dependencies**

   ```bash
   # Pin versions in production
   Django==5.2.0
   djangorestframework==3.16.0

   # Regular updates
   pip list --outdated
   pip install --upgrade <package>
   ```

### Production Deployment

1. **HTTPS Only**

   ```python
   SECURE_SSL_REDIRECT = True
   SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
   ```

2. **Strong SECRET_KEY**

   ```python
   # Generate with:
   python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
   ```

3. **Database Security**

   ```python
   # Use SSL for database connections
   DATABASES = {
       'default': {
           'OPTIONS': {
               'sslmode': 'require',
           },
       }
   }
   ```

4. **Static Files**
   ```python
   # Serve with WhiteNoise + security headers
   STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
   ```

### Code Review Checklist

- [ ] No hardcoded secrets or credentials
- [ ] Input validation on all user inputs
- [ ] Proper error handling (no sensitive info in errors)
- [ ] Authentication/authorization checks
- [ ] SQL injection prevention (use ORM)
- [ ] XSS prevention (escape user content)
- [ ] CSRF protection enabled
- [ ] Rate limiting on sensitive endpoints
- [ ] Logging of security events
- [ ] Dependencies up to date

### Regular Maintenance

```bash
# Weekly
- Run security scans
- Review security logs
- Check for dependency updates

# Monthly
- Full vulnerability assessment
- Review access logs
- Update documentation
- Test incident response

# Quarterly
- Penetration testing
- Security audit
- Update security policies
- Training refresher
```

---

## Incident Response

### Security Incident Procedure

#### 1. Detection & Analysis

```bash
# Check recent security events
python manage.py monitor_security --hours 24

# Review specific logs
tail -f logs/security.log | grep ERROR

# Check failed logins
python manage.py axes_list_attempts
```

#### 2. Containment

```python
# Block IP address
# Add to settings.py
ALLOWED_IPS = ['192.168.1.0/24']  # Whitelist only

# Or use nginx/firewall
sudo ufw deny from 1.2.3.4
```

```bash
# Disable compromised account
python manage.py shell
>>> from django.contrib.auth.models import User
>>> user = User.objects.get(username='compromised_user')
>>> user.is_active = False
>>> user.save()
```

#### 3. Eradication

```bash
# Rotate secrets
# 1. Generate new SECRET_KEY
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'

# 2. Update .env file
# 3. Restart application

# Invalidate all JWT tokens
python manage.py shell
>>> from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
>>> OutstandingToken.objects.all().delete()

# Force password reset for affected users
>>> User.objects.filter(email__in=affected_emails).update(password='!')
```

#### 4. Recovery

```bash
# Restore from backup if needed
pg_restore -d smarthr360 backup.dump

# Verify system integrity
python manage.py check --deploy
./scripts/security_scan.sh
```

#### 5. Post-Incident

```bash
# Document incident
- What happened
- When detected
- Actions taken
- Root cause
- Prevention measures

# Update procedures
- Fix vulnerabilities
- Improve monitoring
- Update documentation
- Team training
```

### Emergency Contacts

```
Security Team Lead: security@smarthr360.com
Infrastructure: ops@smarthr360.com
Management: cto@smarthr360.com
External: security-vendor@example.com
```

---

## Compliance

### GDPR Compliance

1. **Data Protection**

   - Encryption at rest and in transit
   - Access controls and authentication
   - Audit trails of data access

2. **User Rights**

   - Data export functionality
   - Data deletion on request
   - Consent management

3. **Data Breach**
   - Incident response procedure
   - 72-hour notification requirement
   - Documentation and reporting

### Security Standards

#### OWASP Top 10 (2021)

- [x] A01: Broken Access Control
- [x] A02: Cryptographic Failures
- [x] A03: Injection
- [x] A04: Insecure Design
- [x] A05: Security Misconfiguration
- [x] A06: Vulnerable Components
- [x] A07: Identification and Authentication Failures
- [x] A08: Software and Data Integrity Failures
- [x] A09: Security Logging and Monitoring Failures
- [x] A10: Server-Side Request Forgery (SSRF)

### Audit Trail

```python
# Security events are logged with:
- Timestamp
- User ID and username
- IP address
- Action performed
- Result (success/failure)
- User agent
- Additional context
```

---

## Additional Resources

- [Django Security Documentation](https://docs.djangoproject.com/en/stable/topics/security/)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)
- [Content Security Policy](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP)
- [Common Vulnerabilities Database](https://cve.mitre.org/)

---

## Support

For security concerns or questions:

- Email: security@smarthr360.com
- Slack: #security-team
- Documentation: docs/SECURITY_GUIDE.md

**Report Security Vulnerabilities**: security@smarthr360.com (PGP key available)
