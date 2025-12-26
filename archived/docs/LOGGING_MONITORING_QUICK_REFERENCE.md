# Logging & Monitoring Quick Reference

**SmartHR360 Future Skills Platform**

## Quick Setup (5 Minutes)

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Setup Logs Directory

```bash
make -f Makefile.logging logs-setup
```

### 3. Configure Environment

```bash
# .env
ENVIRONMENT=development
LOG_LEVEL=INFO
```

### 4. Test Logging

```bash
make -f Makefile.logging logs-test
```

## Essential Commands

### View Logs

```bash
# Tail application logs
make -f Makefile.logging logs-tail

# View errors only
make -f Makefile.logging logs-tail-errors

# View last 100 lines
make -f Makefile.logging logs-view
```

### Analyze Logs

```bash
# Analyze last 24 hours
make -f Makefile.logging logs-analyze

# Show errors only
make -f Makefile.logging logs-errors

# Performance analysis
make -f Makefile.logging logs-performance
```

### Health Checks

```bash
# Full health check
make -f Makefile.logging health-check

# Specific checks
make -f Makefile.logging health-check-database
make -f Makefile.logging health-check-cache
```

### Monitoring Dashboard

```bash
# Show dashboard
make -f Makefile.logging monitor-dashboard

# Watch dashboard (refresh every 5s)
make -f Makefile.logging monitor-watch
```

## Code Examples

### Basic Logging

```python
from config.logging_config import get_logger

logger = get_logger(__name__)

# Simple log
logger.info('user_login', user_id=123)

# With context
logger.warning('slow_query', duration=2.5, table='skills')

# Error with stack trace
try:
    operation()
except Exception as e:
    logger.error('operation_failed', error=str(e), exc_info=True)
```

### Performance Logging

```python
from config.logging_config import log_performance

@log_performance('performance')
def expensive_operation():
    # ... do work ...
    pass
```

### APM Integration

```python
from config.apm_config import capture_exception, set_user_context

# Capture exception
try:
    operation()
except Exception as e:
    capture_exception(e, user_id=123, operation='process_data')

# Set user context
set_user_context(
    user_id=request.user.id,
    username=request.user.username
)
```

## Environment Variables

### Required

```bash
ENVIRONMENT=production          # development|staging|production
LOG_LEVEL=INFO                 # DEBUG|INFO|WARNING|ERROR|CRITICAL
```

### Optional - Elastic APM

```bash
ELASTIC_APM_SERVER_URL=https://apm.example.com:8200
ELASTIC_APM_SECRET_TOKEN=your-token
ELASTIC_APM_SERVICE_NAME=smarthr360-future-skills
ELASTIC_APM_TRANSACTION_SAMPLE_RATE=1.0
```

### Optional - Sentry

```bash
SENTRY_DSN=https://xxx@sentry.io/yyy
SENTRY_TRACES_SAMPLE_RATE=1.0
APP_VERSION=v1.0.0
```

### Optional - Logstash

```bash
LOGSTASH_HOST=logstash.example.com
LOGSTASH_PORT=5000
```

## API Endpoints

| Endpoint        | Purpose               |
| --------------- | --------------------- |
| `/metrics`      | Prometheus metrics    |
| `/health/`      | Django health check   |
| `/api/health/`  | Custom health check   |
| `/api/ready/`   | Readiness probe       |
| `/api/alive/`   | Liveness probe        |
| `/api/metrics/` | Custom metrics (JSON) |

## Log Files

| File                   | Content              |
| ---------------------- | -------------------- |
| `logs/application.log` | All application logs |
| `logs/error.log`       | Errors only          |
| `logs/security.log`    | Security events      |
| `logs/performance.log` | Performance metrics  |

## Common Tasks

### Find Errors in Last Hour

```bash
python manage.py analyze_logs --hours 1 --errors-only
```

### Check System Health

```bash
python manage.py health_check
```

### View Metrics

```bash
curl http://localhost:8000/metrics
curl http://localhost:8000/api/metrics/ | jq
```

### Rotate Logs

```bash
make -f Makefile.logging logs-rotate
```

### Archive Old Logs

```bash
make -f Makefile.logging logs-archive
```

## Troubleshooting

### No Logs Appearing

1. Check logs directory exists: `make -f Makefile.logging logs-setup`
2. Check LOG_LEVEL in .env
3. Verify logging initialized in wsgi.py

### APM Not Working

1. Check environment variables are set
2. Test connection: `make -f Makefile.logging apm-test-elastic`
3. Send test error: `make -f Makefile.logging apm-test-error`

### High Disk Usage

1. Check log sizes: `make -f Makefile.logging logs-size`
2. Archive old logs: `make -f Makefile.logging logs-archive`
3. Clean archives: `make -f Makefile.logging logs-cleanup`

## Production Checklist

- [ ] Set `ENVIRONMENT=production`
- [ ] Set `LOG_LEVEL=INFO` or `WARNING`
- [ ] Configure Elastic APM or Sentry
- [ ] Setup Logstash for centralized logging
- [ ] Configure log rotation
- [ ] Set up monitoring alerts
- [ ] Test health check endpoints
- [ ] Verify Prometheus metrics
- [ ] Setup Grafana dashboards

## Next Steps

1. **Read Full Guide**: [docs/LOGGING_MONITORING_GUIDE.md](./LOGGING_MONITORING_GUIDE.md)
2. **Configure APM**: Set up Elastic APM or Sentry
3. **Setup Alerts**: Configure monitoring alerts
4. **Create Dashboards**: Import Grafana dashboards
5. **Test Everything**: Run through test commands

## Support

For questions or issues:

1. Check full documentation: `docs/LOGGING_MONITORING_GUIDE.md`
2. Run help command: `make -f Makefile.logging help`
3. View logs: `make -f Makefile.logging logs-view`

---

**Documentation Version**: 1.0.0  
**Last Updated**: November 2024
