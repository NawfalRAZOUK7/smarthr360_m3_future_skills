# Logging & Monitoring Guide

**SmartHR360 Future Skills Platform**

## Table of Contents

1. [Overview](#overview)
2. [Centralized Logging](#centralized-logging)
3. [Application Performance Monitoring (APM)](#application-performance-monitoring-apm)
4. [Health Checks](#health-checks)
5. [Metrics & Prometheus](#metrics--prometheus)
6. [Log Analysis](#log-analysis)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

---

## Overview

The SmartHR360 platform implements comprehensive logging and monitoring through:

- **Structured Logging**: JSON-formatted logs with `structlog` for machine parsing
- **Centralized Logging**: Log aggregation with Logstash/Elasticsearch
- **APM Tools**: Elastic APM and Sentry for error tracking and performance monitoring
- **Metrics**: Prometheus metrics for system and application monitoring
- **Health Checks**: Automated health and readiness checks
- **Distributed Tracing**: Correlation IDs for request tracking across services

### Architecture

```
┌─────────────┐
│  Application │
└──────┬──────┘
       │
       ├─► Structured Logs (structlog)
       │   ├─► Console (development)
       │   ├─► Files (application.log, error.log, security.log, performance.log)
       │   └─► Logstash (production)
       │
       ├─► APM
       │   ├─► Elastic APM (transactions, spans, errors)
       │   └─► Sentry (error tracking, user context)
       │
       ├─► Metrics
       │   └─► Prometheus (counters, gauges, histograms)
       │
       └─► Health Checks
           ├─► /health/ (django-health-check)
           ├─► /api/health/ (custom)
           ├─► /api/ready/ (readiness)
           └─► /api/alive/ (liveness)
```

---

## Centralized Logging

### Configuration

The logging system is configured in `config/logging_config.py` and automatically initialized in WSGI/ASGI.

#### Log Levels

```python
DEBUG    # Detailed debugging information
INFO     # General informational messages
WARNING  # Warning messages
ERROR    # Error messages
CRITICAL # Critical errors
```

#### Log Files

| File                   | Purpose              | Rotation         |
| ---------------------- | -------------------- | ---------------- |
| `logs/application.log` | All application logs | 10MB, 10 backups |
| `logs/error.log`       | Errors only          | 10MB, 10 backups |
| `logs/security.log`    | Security events      | 10MB, 10 backups |
| `logs/performance.log` | Performance metrics  | 10MB, 10 backups |

### Using Structured Logging

#### Basic Usage

```python
from config.logging_config import get_logger

logger = get_logger(__name__)

# Simple logging
logger.info('user_login', user_id=123, username='john.doe')

# With context
logger.warning(
    'slow_query',
    query_time=2.5,
    table='skills',
    operation='SELECT'
)

# Error logging
try:
    risky_operation()
except Exception as e:
    logger.error(
        'operation_failed',
        operation='risky_operation',
        error=str(e),
        exc_info=True  # Include stack trace
    )
```

#### Log Context

Add context to all logs in a block:

```python
from config.logging_config import LogContext

with LogContext(user_id=123, request_id='abc-123'):
    logger.info('processing_request')  # Automatically includes user_id and request_id
    # ... do work ...
    logger.info('request_completed')   # Still includes the context
```

#### Performance Logging

Decorator to automatically log function performance:

```python
from config.logging_config import log_performance

@log_performance('performance')
def expensive_operation():
    # ... do work ...
    pass

# Logs: function=expensive_operation, duration_seconds=1.234, status=success
```

### Log Processors

The system includes custom processors:

1. **add_app_context**: Adds application name and environment
2. **add_log_level**: Standardizes log level field
3. **censor_sensitive_data**: Removes passwords, tokens, etc.
4. **add_correlation_id**: Adds request correlation ID

### JSON Log Format

Production logs use JSON format for easy parsing:

```json
{
  "timestamp": "2024-11-28T10:30:45.123Z",
  "level": "INFO",
  "logger": "future_skills.api.views",
  "event": "prediction_created",
  "app": "smarthr360",
  "environment": "production",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": 123,
  "skill": "Python",
  "job_role": "Data Scientist",
  "predicted_level": 4
}
```

### Logstash Integration

For centralized logging, configure Logstash:

```bash
# .env
LOGSTASH_HOST=logstash.example.com
LOGSTASH_PORT=5000
```

Logs are automatically shipped to Logstash when configured.

---

## Application Performance Monitoring (APM)

### Elastic APM

Elastic APM provides distributed tracing, performance monitoring, and error tracking.

#### Configuration

```bash
# .env
ELASTIC_APM_SERVER_URL=https://apm.example.com:8200
ELASTIC_APM_SECRET_TOKEN=your-secret-token
ELASTIC_APM_SERVICE_NAME=smarthr360-future-skills
ENVIRONMENT=production

# Optional
ELASTIC_APM_TRANSACTION_SAMPLE_RATE=1.0  # Sample 100% (0.0 to 1.0)
ELASTIC_APM_CAPTURE_BODY=errors           # off|errors|transactions|all
```

#### Features

1. **Transaction Tracing**: Automatic tracing of HTTP requests
2. **Span Tracking**: Database queries, external API calls, custom spans
3. **Error Tracking**: Automatic error capture with stack traces
4. **Performance Metrics**: Response times, throughput, error rates
5. **Distributed Tracing**: Track requests across microservices

#### Using APM

```python
from config.apm_config import capture_exception, set_user_context, set_custom_context

# Capture exception
try:
    operation()
except Exception as e:
    capture_exception(e, operation='data_processing', user_id=123)

# Set user context
set_user_context(
    user_id=request.user.id,
    username=request.user.username,
    email=request.user.email
)

# Set custom context
set_custom_context('processing', {
    'batch_size': 100,
    'model_version': 'v2.1.0'
})
```

#### Custom Spans

```python
import elasticapm

# Automatic span
@elasticapm.capture_span()
def process_data(data):
    # ... processing ...
    pass

# Manual span
with elasticapm.capture_span('custom_operation'):
    # ... do work ...
    pass
```

### Sentry

Sentry provides error tracking, release tracking, and user feedback.

#### Configuration

```bash
# .env
SENTRY_DSN=https://xxx@sentry.io/yyy
APP_VERSION=v1.2.3
ENVIRONMENT=production

# Optional
SENTRY_TRACES_SAMPLE_RATE=1.0    # Performance monitoring sample rate
SENTRY_PROFILES_SAMPLE_RATE=1.0  # Profiling sample rate
```

#### Features

1. **Error Tracking**: Automatic error capture with grouping
2. **Release Tracking**: Track errors by release version
3. **User Feedback**: Collect user feedback on errors
4. **Performance Monitoring**: Transaction tracking and profiling
5. **Alerts**: Email/Slack notifications for errors

#### Using Sentry

```python
import sentry_sdk

# Capture exception
try:
    operation()
except Exception as e:
    sentry_sdk.capture_exception(e)

# Capture message
sentry_sdk.capture_message('Something went wrong', level='warning')

# Add context
with sentry_sdk.push_scope() as scope:
    scope.set_context('processing', {
        'batch_size': 100,
        'model_version': 'v2.1.0'
    })
    scope.set_user({'id': 123, 'username': 'john.doe'})
    sentry_sdk.capture_exception(exception)

# Add breadcrumb
sentry_sdk.add_breadcrumb(
    category='auth',
    message='User logged in',
    level='info',
    data={'user_id': 123}
)
```

---

## Health Checks

### Endpoints

| Endpoint       | Purpose                    | Use Case                    |
| -------------- | -------------------------- | --------------------------- |
| `/health/`     | Comprehensive health check | Load balancer health checks |
| `/api/health/` | Custom health check        | Application monitoring      |
| `/api/ready/`  | Readiness check            | Kubernetes readiness probe  |
| `/api/alive/`  | Liveness check             | Kubernetes liveness probe   |

### Management Command

```bash
# Check all systems
python manage.py health_check

# Check specific component
python manage.py health_check --check database
python manage.py health_check --check cache
python manage.py health_check --check celery
python manage.py health_check --check disk
python manage.py health_check --check memory

# JSON output
python manage.py health_check --json
```

### Health Check Response

```json
{
  "database": {
    "healthy": true,
    "response_time": 0.012,
    "message": "Database connection successful"
  },
  "cache": {
    "healthy": true,
    "response_time": 0.005,
    "message": "Cache working correctly"
  },
  "celery": {
    "healthy": true,
    "worker_count": 3,
    "workers": ["worker1@host", "worker2@host", "worker3@host"],
    "message": "3 worker(s) active"
  },
  "disk": {
    "healthy": true,
    "total_gb": 500,
    "used_gb": 250,
    "free_gb": 250,
    "percent_used": 50,
    "message": "Disk 50% used"
  },
  "memory": {
    "healthy": true,
    "total_gb": 16,
    "used_gb": 8,
    "free_gb": 8,
    "percent_used": 50,
    "message": "Memory 50% used"
  },
  "overall": {
    "healthy": true,
    "timestamp": 1701172800.0
  }
}
```

### Kubernetes Probes

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: smarthr360-app
spec:
  containers:
    - name: app
      image: smarthr360:latest
      livenessProbe:
        httpGet:
          path: /api/alive/
          port: 8000
        initialDelaySeconds: 30
        periodSeconds: 10
      readinessProbe:
        httpGet:
          path: /api/ready/
          port: 8000
        initialDelaySeconds: 10
        periodSeconds: 5
```

---

## Metrics & Prometheus

### Prometheus Endpoints

- **Metrics**: `/metrics` - Prometheus-formatted metrics
- **Application Metrics**: `/api/metrics/` - Custom JSON metrics

### Available Metrics

#### HTTP Metrics

```
# Request counters
django_http_requests_total{method="GET",view="skill_list",status="200"}

# Request duration histogram
django_http_request_duration_seconds_bucket{method="GET",view="skill_list",le="0.1"}

# Response size histogram
django_http_response_size_bytes_bucket{view="skill_list",le="1000"}
```

#### Database Metrics

```
# Query counters
django_db_query_total{vendor="postgresql",alias="default"}

# Query duration histogram
django_db_query_duration_seconds_bucket{vendor="postgresql",alias="default",le="0.01"}

# Connection pool
django_db_connections_total{vendor="postgresql",alias="default"}
```

#### Cache Metrics

```
# Cache operations
django_cache_operations_total{operation="get",backend="redis",status="hit"}
django_cache_operations_total{operation="set",backend="redis",status="success"}
```

#### Custom Metrics

```
# Future skills predictions
future_skills_predictions_total{model_version="v2",level="4"}

# ML model performance
future_skills_model_inference_duration_seconds
```

### Querying Metrics

```bash
# Get all metrics
curl http://localhost:8000/metrics

# Query Prometheus
# Request rate
rate(django_http_requests_total[5m])

# Average response time
rate(django_http_request_duration_seconds_sum[5m]) /
rate(django_http_request_duration_seconds_count[5m])

# Error rate
rate(django_http_requests_total{status=~"5.."}[5m])
```

### Grafana Dashboards

Import pre-built dashboards:

1. **Django Overview**: Dashboard ID 14056
2. **Django Database**: Dashboard ID 14057
3. **Django Cache**: Dashboard ID 14058

---

## Log Analysis

### Management Command

```bash
# Analyze logs from last 24 hours
python manage.py analyze_logs

# Analyze specific log file
python manage.py analyze_logs --log-file logs/application.log

# Analyze last 7 days
python manage.py analyze_logs --hours 168

# Show only errors
python manage.py analyze_logs --errors-only

# Show performance analysis
python manage.py analyze_logs --performance

# JSON output
python manage.py analyze_logs --json

# Show top 20 items
python manage.py analyze_logs --top 20
```

### Analysis Output

```
================================================================================
Log Analysis
================================================================================
Log file: /app/logs/application.log
Time range: Last 24 hours

Summary:
--------------------------------------------------------------------------------
Total logs: 125,432
Time range: 2024-11-27 10:00:00 to 2024-11-28 10:00:00

Log Levels:
--------------------------------------------------------------------------------
  INFO: 120,000
  WARNING: 4,500
  ERROR: 800
  CRITICAL: 132

Errors:
--------------------------------------------------------------------------------
Total errors: 932

Top error types:
  database_connection_timeout: 450
  api_rate_limit_exceeded: 250
  model_prediction_failed: 150
  validation_error: 82

Recent errors:
  [2024-11-28 09:55:23] database_connection_timeout: Connection pool exhausted
  [2024-11-28 09:52:10] api_rate_limit_exceeded: User 123 exceeded rate limit
  [2024-11-28 09:48:55] model_prediction_failed: Model file not found

Performance:
--------------------------------------------------------------------------------
Total requests: 95,234
Avg duration: 0.085s
Min duration: 0.001s
Max duration: 5.234s

Slow requests (> 1s): 234
  POST /api/v2/predictions/batch/: 2.456s
  GET /api/v2/skills/: 1.892s
  POST /api/v2/predictions/: 1.234s

Requests:
--------------------------------------------------------------------------------
Total requests: 95,234

Top endpoints:
  GET /api/v2/skills/: 45,123
  GET /api/v2/job-roles/: 23,456
  POST /api/v2/predictions/: 12,345
  GET /api/v2/future-skills/: 8,901
  GET /api/health/: 5,409
```

---

## Best Practices

### Development

1. **Use Colored Console Logs**

   ```python
   # Automatically enabled in development
   ENVIRONMENT=development  # in .env
   ```

2. **Debug Logging**

   ```python
   # Enable debug logging
   LOG_LEVEL=DEBUG  # in .env
   ```

3. **SQL Query Logging** (development only)
   ```python
   # Enable in settings
   DEBUG = True
   # SQLQueryLoggingMiddleware will log queries
   ```

### Production

1. **Use JSON Logs**

   ```python
   ENVIRONMENT=production  # Auto-enables JSON format
   ```

2. **Set Appropriate Log Level**

   ```python
   LOG_LEVEL=INFO  # or WARNING for high-traffic apps
   ```

3. **Enable APM**

   ```bash
   ELASTIC_APM_SERVER_URL=https://apm.example.com
   SENTRY_DSN=https://xxx@sentry.io/yyy
   ```

4. **Configure Logstash**

   ```bash
   LOGSTASH_HOST=logstash.example.com
   LOGSTASH_PORT=5000
   ```

5. **Disable Debug Middleware**
   ```python
   # Remove SQLQueryLoggingMiddleware from MIDDLEWARE
   ```

### Logging Guidelines

1. **Be Specific**: Use descriptive event names

   ```python
   # Good
   logger.info('user_login_success', user_id=123, ip='192.168.1.1')

   # Bad
   logger.info('User logged in')
   ```

2. **Include Context**: Add relevant data

   ```python
   logger.error(
       'prediction_failed',
       skill_id=skill.id,
       job_role_id=job_role.id,
       model_version='v2.1.0',
       error=str(e)
   )
   ```

3. **Use Appropriate Levels**

   - DEBUG: Detailed debugging (e.g., variable values)
   - INFO: Normal operations (e.g., request completed)
   - WARNING: Unusual but handled (e.g., slow query)
   - ERROR: Errors that need attention (e.g., API call failed)
   - CRITICAL: System-level failures (e.g., database down)

4. **Never Log Sensitive Data**

   ```python
   # Good - automatically censored
   logger.info('token_generated', token='***REDACTED***')

   # Bad - don't do this
   logger.info('token_generated', token=actual_token)
   ```

5. **Use Structured Data**

   ```python
   # Good
   logger.info('batch_processing', count=100, duration=2.5)

   # Bad
   logger.info(f'Processed {count} items in {duration}s')
   ```

---

## Troubleshooting

### No Logs Appearing

1. **Check log directory exists**

   ```bash
   mkdir -p logs
   chmod 755 logs
   ```

2. **Check log level**

   ```bash
   # .env
   LOG_LEVEL=INFO  # Not ERROR or CRITICAL
   ```

3. **Check logging initialization**
   ```python
   # Should be called in wsgi.py/asgi.py
   from config.logging_config import setup_logging
   setup_logging()
   ```

### APM Not Working

1. **Check APM configuration**

   ```bash
   # Verify env vars are set
   echo $ELASTIC_APM_SERVER_URL
   echo $SENTRY_DSN
   ```

2. **Check APM initialization**

   ```python
   # Should be called in wsgi.py/asgi.py
   from config.apm_config import initialize_apm
   initialize_apm()
   ```

3. **Test connectivity**
   ```bash
   curl $ELASTIC_APM_SERVER_URL
   ```

### High Memory Usage

1. **Check log rotation**

   ```python
   # Ensure RotatingFileHandler is configured
   maxBytes=10485760  # 10MB
   backupCount=10
   ```

2. **Reduce sampling rate**

   ```bash
   ELASTIC_APM_TRANSACTION_SAMPLE_RATE=0.1  # Sample 10%
   SENTRY_TRACES_SAMPLE_RATE=0.1
   ```

3. **Clean old logs**
   ```bash
   find logs/ -name "*.log.*" -mtime +30 -delete
   ```

### Performance Issues

1. **Use async Logstash handler**

   ```python
   # Already configured in logging_config.py
   logstash_async.handler.AsynchronousLogstashHandler
   ```

2. **Reduce log verbosity**

   ```bash
   LOG_LEVEL=WARNING  # Only warnings and errors
   ```

3. **Disable SQL logging in production**
   ```python
   # Remove SQLQueryLoggingMiddleware
   ```

---

## Quick Reference

### Environment Variables

```bash
# Logging
LOG_LEVEL=INFO                    # DEBUG|INFO|WARNING|ERROR|CRITICAL
ENVIRONMENT=production            # development|staging|production

# Logstash
LOGSTASH_HOST=logstash.example.com
LOGSTASH_PORT=5000

# Elastic APM
ELASTIC_APM_SERVER_URL=https://apm.example.com:8200
ELASTIC_APM_SECRET_TOKEN=your-secret-token
ELASTIC_APM_SERVICE_NAME=smarthr360-future-skills
ELASTIC_APM_TRANSACTION_SAMPLE_RATE=1.0
ELASTIC_APM_CAPTURE_BODY=errors

# Sentry
SENTRY_DSN=https://xxx@sentry.io/yyy
SENTRY_TRACES_SAMPLE_RATE=1.0
SENTRY_PROFILES_SAMPLE_RATE=1.0
APP_VERSION=v1.2.3
```

### Commands

```bash
# Health check
python manage.py health_check
python manage.py health_check --json
python manage.py health_check --check database

# Log analysis
python manage.py analyze_logs
python manage.py analyze_logs --hours 24
python manage.py analyze_logs --errors-only
python manage.py analyze_logs --performance
python manage.py analyze_logs --json

# View metrics
curl http://localhost:8000/metrics
curl http://localhost:8000/api/metrics/
```

### Endpoints

```
GET  /metrics             # Prometheus metrics
GET  /health/             # Django health check
GET  /api/health/         # Custom health check
GET  /api/ready/          # Readiness probe
GET  /api/alive/          # Liveness probe
GET  /api/version/        # Version info
GET  /api/metrics/        # Custom metrics JSON
```
