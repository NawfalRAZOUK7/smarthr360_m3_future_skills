# Celery Monitoring & Retry Strategies Documentation

Complete guide for Celery monitoring, advanced retry strategies, and production deployment.

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Architecture](#architecture)
4. [Monitoring](#monitoring)
5. [Retry Strategies](#retry-strategies)
6. [Dead Letter Queue](#dead-letter-queue)
7. [Performance Tuning](#performance-tuning)
8. [Troubleshooting](#troubleshooting)
9. [Best Practices](#best-practices)

---

## Overview

SmartHR360 uses Celery for asynchronous task processing with comprehensive monitoring and resilience features:

- **Flower UI**: Real-time web-based monitoring
- **Prometheus Metrics**: Production-grade observability
- **Grafana Dashboards**: Visual performance analytics
- **Advanced Retry Strategies**: Exponential backoff, circuit breakers
- **Dead Letter Queue**: Failed task management and reprocessing
- **Task Execution Tracking**: Complete audit trail
- **Resource Monitoring**: Memory and CPU tracking

---

## Quick Start

### 1. Install Dependencies

```bash
# Install Celery monitoring dependencies
pip install -r requirements_celery.txt

# Core dependencies installed:
# - flower (web monitoring)
# - celery-exporter (Prometheus metrics)
# - django-celery-results (database backend)
# - django-celery-beat (scheduled tasks)
# - tenacity (retry strategies)
# - pybreaker (circuit breaker)
```

### 2. Run Database Migrations

```bash
# Create tables for monitoring
python manage.py migrate

# This creates:
# - django_celery_results_* (task results)
# - django_celery_beat_* (scheduled tasks)
# - celery_task_execution (execution tracking)
# - celery_dead_letter_queue (failed tasks)
```

### 3. Start Celery Worker

```bash
# Basic worker
celery -A config worker --loglevel=info

# Worker with specific queues
celery -A config worker --loglevel=info \
    --queues=training,maintenance,default \
    --concurrency=4

# Worker with autoscaling
celery -A config worker --loglevel=info \
    --autoscale=10,3  # Max 10, min 3 workers
```

### 4. Start Flower Monitoring

```bash
# Basic Flower
celery -A config flower --port=5555

# Flower with authentication
celery -A config flower --port=5555 \
    --basic_auth=admin:secretpassword

# Flower with persistent storage
celery -A config flower --port=5555 \
    --db=flower.db --persistent=True

# Access: http://localhost:5555
```

### 5. Start Celery Beat (Scheduled Tasks)

```bash
# Start beat scheduler
celery -A config beat --loglevel=info \
    --scheduler django_celery_beat.schedulers:DatabaseScheduler

# Scheduled tasks:
# - cleanup-old-models-daily (2 AM)
# - cleanup-task-executions-weekly (Sunday 3 AM)
# - cleanup-dead-letter-monthly (1st of month 4 AM)
```

---

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Django Application                      │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ API Views   │→ │ Celery Tasks │→ │ Task Decorators  │   │
│  └─────────────┘  └──────────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              ↓
                    ┌──────────────────┐
                    │  Redis (Broker)  │
                    └──────────────────┘
                              ↓
        ┌─────────────────────┴─────────────────────┐
        ↓                                            ↓
┌──────────────────┐                      ┌──────────────────┐
│ Celery Workers   │                      │ Celery Beat      │
│ (Task Execution) │                      │ (Scheduler)      │
└──────────────────┘                      └──────────────────┘
        ↓                                            ↓
┌─────────────────────────────────────────────────────────────┐
│                      Monitoring Layer                        │
│  ┌────────┐  ┌──────────┐  ┌─────────┐  ┌────────────────┐│
│  │ Flower │  │ Grafana  │  │  Django │  │ Dead Letter    ││
│  │   UI   │  │Dashboard │  │   DB    │  │     Queue      ││
│  └────────┘  └──────────┘  └─────────┘  └────────────────┘│
└─────────────────────────────────────────────────────────────┘
                              ↓
                    ┌──────────────────┐
                    │   Prometheus     │
                    │   (Metrics)      │
                    └──────────────────┘
```

### Task Flow with Retry Strategies

```
┌─────────────────┐
│  Task Dispatch  │
└────────┬────────┘
         ↓
┌─────────────────┐
│ Idempotency     │  ← Prevents duplicate execution
│ Check           │
└────────┬────────┘
         ↓
┌─────────────────┐
│ Rate Limit      │  ← API rate limiting
│ Check           │
└────────┬────────┘
         ↓
┌─────────────────┐
│ Circuit Breaker │  ← Fail-fast if service down
│ Check           │
└────────┬────────┘
         ↓
┌─────────────────┐
│ Task Execution  │
└────────┬────────┘
         │
    [Success?]
         │
    Yes  │  No
         ↓  ↓
         │  ┌─────────────────┐
         │  │ Exponential     │  ← Retry with backoff
         │  │ Backoff Retry   │
         │  └────────┬────────┘
         │           │
         │      [Max retries?]
         │           │
         │      Yes  │  No (retry)
         │           ↓
         │  ┌─────────────────┐
         │  │ Dead Letter     │  ← Manual inspection
         │  │ Queue           │
         │  └─────────────────┘
         ↓
┌─────────────────┐
│ Success Metrics │  ← Prometheus, monitoring
└─────────────────┘
```

---

## Monitoring

### Flower Web UI

**Access**: http://localhost:5555

**Features**:

- Real-time task monitoring
- Worker status and statistics
- Task history and search
- Task execution graphs
- Rate limiting controls
- Task revocation
- Broker monitoring

**Configuration** (`config/flowerconfig.py`):

```python
# Basic auth
basic_auth = 'admin:password'

# Persistent storage
persistent = True
db = 'flower.db'

# Max tasks to keep
max_tasks = 10000
```

### Prometheus Metrics

**Metrics Exposed**:

| Metric                         | Type      | Description                  |
| ------------------------------ | --------- | ---------------------------- |
| `celery_task_started_total`    | Counter   | Total tasks started          |
| `celery_task_completed_total`  | Counter   | Tasks completed successfully |
| `celery_task_failed_total`     | Counter   | Tasks that failed            |
| `celery_task_retry_total`      | Counter   | Task retries                 |
| `celery_task_duration_seconds` | Histogram | Task execution duration      |
| `celery_queue_length`          | Gauge     | Tasks in queue               |
| `celery_active_tasks`          | Gauge     | Currently executing tasks    |
| `celery_worker_online`         | Gauge     | Worker status (1=online)     |
| `celery_task_memory_mb`        | Gauge     | Task memory usage            |

**Query Examples**:

```promql
# Success rate
(celery_task_completed_total / (celery_task_completed_total + celery_task_failed_total)) * 100

# P95 latency
histogram_quantile(0.95, rate(celery_task_duration_seconds_bucket[5m]))

# Tasks per second
rate(celery_task_started_total[5m])

# Average queue length
avg(celery_queue_length)
```

### Grafana Dashboard

**Import**: `config/grafana_celery_dashboard.json`

**Panels**:

1. **Task Success Rate** - Gauge showing % successful tasks
2. **Task Execution Rate** - Time series of tasks/second
3. **Task Duration Percentiles** - P50, P95, P99 latencies
4. **Queue Length** - Tasks waiting in each queue
5. **Active Tasks per Worker** - Real-time worker activity
6. **Worker Status** - Online/offline workers table
7. **Task Retries** - Retry frequency by task
8. **Task Memory Usage** - Memory consumption tracking

### Database Tracking

**TaskExecution Model** (`celery_monitoring.monitoring.TaskExecution`):

Tracks every task execution with:

- Task ID, name, status
- Timing: received_at, started_at, completed_at
- Durations: queue_time, execution_time, total_time
- Worker and queue information
- Result or error details
- Retry count
- Resource usage (memory, CPU)

**Query Examples**:

```python
from celery_monitoring.monitoring import TaskExecution

# Get recent failures
failures = TaskExecution.objects.filter(
    status='FAILURE',
    started_at__gte=timezone.now() - timedelta(hours=24)
)

# Get slowest tasks
slowest = TaskExecution.objects.filter(
    execution_time__isnull=False
).order_by('-execution_time')[:10]

# Get task statistics
from celery_monitoring.monitoring import get_task_performance_stats
stats = get_task_performance_stats(
    task_name='future_skills.train_model',
    hours=24
)
```

---

## Retry Strategies

### Exponential Backoff

Automatically retries with increasing delays:

```python
from celery_monitoring import retry_with_exponential_backoff

@shared_task
@retry_with_exponential_backoff(
    max_retries=5,
    base_delay=60,        # Start with 60s
    max_delay=3600,       # Max 1 hour
    exponential_base=2,   # Double each time
    jitter=True          # Add randomness
)
def my_task():
    # Task implementation
    pass

# Retry delays: 60s, 120s, 240s, 480s, 960s (capped at max_delay)
```

**When to Use**:

- Transient network errors
- Temporary service outages
- Rate-limited APIs
- Database connection issues

### Circuit Breaker

Prevents cascading failures by blocking requests to failing services:

```python
from celery_monitoring import with_circuit_breaker

@shared_task
@with_circuit_breaker(
    name='external_api',
    fail_max=5,           # Open after 5 failures
    reset_timeout=300    # Try again after 5 minutes
)
def call_external_api():
    response = requests.get('https://api.example.com')
    return response.json()

# Circuit states:
# - CLOSED: Normal operation
# - OPEN: Blocking requests (fails immediately)
# - HALF_OPEN: Testing recovery (allows 1 request)
```

**When to Use**:

- External API calls
- Database connections
- Microservice communication
- Third-party integrations

### Dead Letter Queue

Captures permanently failed tasks for manual inspection:

```python
from celery_monitoring import with_dead_letter_queue

@shared_task
@with_dead_letter_queue(max_retries=3)
def critical_payment_task(payment_id):
    # Process payment
    pass

# After 3 failures, task sent to dead letter queue
# Can be inspected and manually reprocessed
```

**Management**:

```python
from celery_monitoring.dead_letter import (
    DeadLetterTask,
    reprocess_dead_letter_tasks
)

# List failed tasks
failed_tasks = DeadLetterTask.objects.filter(reprocessed=False)

# Reprocess specific task
task = DeadLetterTask.objects.get(task_id='abc123')
result = task.reprocess()

# Bulk reprocess
results = reprocess_dead_letter_tasks(
    task_name='future_skills.train_model',
    limit=10
)
```

### Rate Limiting

Prevent overwhelming external services:

```python
from celery_monitoring import rate_limit

@shared_task
@rate_limit(calls=100, period=60)  # 100 calls per minute
def call_rate_limited_api():
    # API call
    pass
```

### Timeout Handling

Prevent runaway tasks:

```python
from celery_monitoring import with_timeout

@shared_task
@with_timeout(
    soft_timeout=300,   # 5 minutes soft limit
    hard_timeout=600    # 10 minutes hard limit
)
def long_running_task():
    # Long computation
    pass

# Soft timeout: SoftTimeLimitExceeded (can catch and cleanup)
# Hard timeout: TimeLimitExceeded (kills task)
```

### Idempotency

Prevent duplicate task execution:

```python
from celery_monitoring import idempotent

@shared_task
@idempotent(timeout=300)  # 5-minute lock
def send_notification(user_id):
    # Won't send duplicate notifications within 5 minutes
    pass
```

### Composite Strategy

Combine multiple strategies:

```python
from celery_monitoring import with_advanced_retry

@shared_task
@with_advanced_retry(
    max_retries=5,
    use_circuit_breaker=True,
    circuit_breaker_name='payment_api',
    use_dead_letter_queue=True,
    rate_limit_calls=100,
    rate_limit_period=60
)
def process_payment(payment_id):
    # Fully protected task with all strategies
    pass
```

---

## Dead Letter Queue

### Overview

Failed tasks are sent to a dead letter queue instead of being lost:

1. Task fails after max retries
2. Task saved to `DeadLetterTask` model
3. Task can be inspected, debugged, fixed
4. Task can be manually reprocessed

### Inspection

```python
from celery_monitoring.dead_letter import DeadLetterTask

# List all failed tasks
failed = DeadLetterTask.objects.filter(reprocessed=False)

for task in failed:
    print(f"Task: {task.task_name}")
    print(f"Failed: {task.failed_at}")
    print(f"Error: {task.exception_message}")
    print(f"Args: {task.args}")
    print(f"Kwargs: {task.kwargs}")
    print(f"Retries: {task.retries}")
    print(f"Traceback: {task.exception_traceback}")
```

### Reprocessing

```python
# Reprocess single task
task = DeadLetterTask.objects.get(task_id='abc123')
result = task.reprocess()

if result['status'] == 'success':
    print(f"Task reprocessed successfully: {result['result']}")
else:
    print(f"Reprocessing failed: {result['error']}")

# Bulk reprocess
from celery_monitoring.dead_letter import reprocess_dead_letter_tasks

results = reprocess_dead_letter_tasks(
    task_name='future_skills.train_model',
    limit=10
)

print(f"Total: {results['total']}")
print(f"Success: {results['success']}")
print(f"Failed: {results['failed']}")
```

### Cleanup

```python
from celery_monitoring.dead_letter import cleanup_old_dead_letter_tasks

# Delete reprocessed tasks older than 30 days
deleted = cleanup_old_dead_letter_tasks(days=30)
print(f"Deleted {deleted} old tasks")
```

---

## Performance Tuning

### Worker Configuration

```bash
# Autoscaling: dynamically adjust workers
celery -A config worker --autoscale=10,3 --loglevel=info

# Concurrency: fixed number of workers
celery -A config worker --concurrency=8 --loglevel=info

# Pool: choose execution pool
celery -A config worker --pool=prefork  # Default
celery -A config worker --pool=gevent --concurrency=100  # Async I/O
celery -A config worker --pool=solo  # Single process (debugging)

# Queue routing
celery -A config worker --queues=training,default --loglevel=info
```

### Optimization Tips

**1. Prefetch Multiplier**:

```python
# settings.py
CELERY_WORKER_PREFETCH_MULTIPLIER = 1  # For long-running tasks
CELERY_WORKER_PREFETCH_MULTIPLIER = 4  # For short tasks
```

**2. Task Acknowledgment**:

```python
# Acknowledge after completion (safer for long tasks)
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
```

**3. Result Backend**:

```python
# Use database for persistence
CELERY_RESULT_BACKEND = 'django-db'

# Or Redis for speed
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'

# Set expiration
CELERY_RESULT_EXPIRES = 3600  # 1 hour
```

**4. Worker Memory Management**:

```python
# Restart workers after N tasks
CELERY_WORKER_MAX_TASKS_PER_CHILD = 50

# Restart workers if memory exceeds
CELERY_WORKER_MAX_MEMORY_PER_CHILD = 200000  # 200MB
```

**5. Queue Priorities**:

```python
# Define queue priorities
CELERY_TASK_ROUTES = {
    'critical.task': {'queue': 'high', 'priority': 10},
    'normal.task': {'queue': 'default', 'priority': 5},
    'background.task': {'queue': 'low', 'priority': 1},
}
```

### Monitoring Performance

```python
from celery_monitoring.monitoring import (
    get_task_performance_stats,
    get_slowest_tasks
)

# Get statistics
stats = get_task_performance_stats(
    task_name='future_skills.train_model',
    hours=24
)

print(f"Total tasks: {stats['total_tasks']}")
print(f"Success rate: {stats['success_rate']}%")
print(f"Avg execution: {stats['avg_execution_time_seconds']}s")
print(f"Max execution: {stats['max_execution_time_seconds']}s")

# Find bottlenecks
slowest = get_slowest_tasks(limit=10, hours=24)
for task in slowest:
    print(f"{task['task_name']}: {task['execution_time']}s")
```

---

## Troubleshooting

### Common Issues

#### 1. Worker Not Starting

**Problem**: `celery -A config worker` fails to start

**Solutions**:

```bash
# Check Redis connection
redis-cli ping  # Should return PONG

# Verify settings
python manage.py shell -c "from django.conf import settings; print(settings.CELERY_BROKER_URL)"

# Check for import errors
python -c "from config.celery import app; print(app)"

# Enable debug logging
celery -A config worker --loglevel=debug
```

#### 2. Tasks Not Executing

**Problem**: Tasks queued but not processing

**Solutions**:

```bash
# Check worker is consuming correct queue
celery -A config inspect active_queues

# Verify task routing
celery -A config inspect registered

# Check for task errors
celery -A config events  # Real-time monitoring

# Inspect task state
celery -A config inspect stats
```

#### 3. Task Stuck in PENDING

**Problem**: Task shows PENDING status indefinitely

**Solutions**:

```python
# Check if task exists
result = AsyncResult(task_id)
print(result.state)  # PENDING, SUCCESS, FAILURE, etc.

# Verify broker connection
from celery import current_app
print(current_app.connection().connected)

# Check worker logs
# Look for task execution in worker output

# Revoke stuck task
result.revoke(terminate=True)
```

#### 4. High Memory Usage

**Problem**: Workers consuming too much memory

**Solutions**:

```python
# Enable memory limits (settings.py)
CELERY_WORKER_MAX_MEMORY_PER_CHILD = 200000  # 200MB

# Reduce concurrency
celery -A config worker --concurrency=2

# Use memory profiling
@monitor_task(track_memory=True)
def my_task():
    pass

# Monitor memory usage
from celery_monitoring.monitoring import TaskExecution
executions = TaskExecution.objects.filter(
    task_name='my_task'
).order_by('-memory_usage_mb')
```

#### 5. Flower Not Showing Tasks

**Problem**: Flower UI empty or not updating

**Solutions**:

```python
# Enable task events (settings.py)
CELERY_SEND_EVENTS = True
CELERY_TASK_SEND_SENT_EVENT = True

# Restart workers with events
celery -A config worker --loglevel=info -E

# Check Flower connection
celery -A config flower --port=5555 --debug

# Clear Flower database
rm flower.db
```

### Debugging Tools

```bash
# Inspect workers
celery -A config inspect active      # Active tasks
celery -A config inspect scheduled   # Scheduled tasks
celery -A config inspect reserved    # Reserved tasks
celery -A config inspect stats       # Worker statistics
celery -A config inspect registered  # Registered tasks

# Control workers
celery -A config control shutdown    # Graceful shutdown
celery -A config control pool_restart  # Restart worker pool
celery -A config purge               # Clear all queues

# Monitor events
celery -A config events              # Real-time event monitor
```

---

## Best Practices

### Task Design

**1. Keep Tasks Small and Focused**:

```python
# Bad: Monolithic task
@shared_task
def process_everything(data):
    result1 = process_step1(data)
    result2 = process_step2(result1)
    result3 = process_step3(result2)
    return result3

# Good: Separate tasks
@shared_task
def process_step1(data):
    return result1

@shared_task
def process_step2(result1):
    return result2

# Chain tasks
from celery import chain
workflow = chain(
    process_step1.s(data),
    process_step2.s(),
    process_step3.s()
)
workflow.apply_async()
```

**2. Make Tasks Idempotent**:

```python
# Bad: Not idempotent
@shared_task
def increment_counter(user_id):
    user = User.objects.get(id=user_id)
    user.login_count += 1
    user.save()

# Good: Idempotent
@shared_task
@idempotent(timeout=300)
def record_login(user_id, timestamp):
    Login.objects.get_or_create(
        user_id=user_id,
        timestamp=timestamp
    )
```

**3. Handle Failures Gracefully**:

```python
@shared_task
@retry_with_exponential_backoff(max_retries=3)
def send_email(to, subject, body):
    try:
        # Send email
        send_mail(subject, body, 'from@example.com', [to])
        return {'status': 'sent', 'to': to}
    except SMTPException as e:
        logger.error(f"Failed to send email to {to}: {e}")
        # Will retry automatically
        raise
    except Exception as e:
        # Log and fail without retry
        logger.error(f"Unexpected error: {e}")
        raise Ignore()
```

**4. Use Appropriate Timeouts**:

```python
# ML training: long timeout
@shared_task
@with_timeout(soft_timeout=1500, hard_timeout=1800)
def train_model():
    pass

# API call: short timeout
@shared_task
@with_timeout(soft_timeout=10, hard_timeout=30)
def fetch_api_data():
    pass
```

### Monitoring

**1. Track Important Metrics**:

```python
@shared_task
@monitor_task(track_memory=True, track_cpu=True)
def resource_intensive_task():
    # Automatically tracks memory and CPU
    pass
```

**2. Set Up Alerts**:

```yaml
# Prometheus alerting rules
groups:
  - name: celery
    rules:
      - alert: HighTaskFailureRate
        expr: rate(celery_task_failed_total[5m]) > 0.1
        annotations:
          summary: "High task failure rate"

      - alert: LongQueueLength
        expr: celery_queue_length > 100
        annotations:
          summary: "Queue backlog growing"
```

**3. Regular Cleanup**:

```python
# Schedule cleanup tasks (settings.py)
CELERY_BEAT_SCHEDULE = {
    'cleanup-old-executions': {
        'task': 'celery_monitoring.cleanup_task_executions',
        'schedule': crontab(hour=3, minute=0),
        'kwargs': {'days': 7}
    },
}
```

### Production Deployment

**1. Use Supervisor or Systemd**:

```ini
# /etc/supervisor/conf.d/celery.conf
[program:celery-worker]
command=/path/to/venv/bin/celery -A config worker --loglevel=info
directory=/path/to/project
user=www-data
autostart=true
autorestart=true
stdout_logfile=/var/log/celery/worker.log
stderr_logfile=/var/log/celery/worker-error.log

[program:celery-beat]
command=/path/to/venv/bin/celery -A config beat --loglevel=info
directory=/path/to/project
user=www-data
autostart=true
autorestart=true
stdout_logfile=/var/log/celery/beat.log

[program:flower]
command=/path/to/venv/bin/celery -A config flower --port=5555
directory=/path/to/project
user=www-data
autostart=true
autorestart=true
```

**2. Use RabbitMQ for Production**:

```python
# More robust than Redis for task queuing
CELERY_BROKER_URL = 'amqp://user:pass@localhost:5672//'
```

**3. Configure Logging**:

```python
# settings.py
LOGGING = {
    'version': 1,
    'handlers': {
        'celery': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/celery/celery.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
        },
    },
    'loggers': {
        'celery': {
            'handlers': ['celery'],
            'level': 'INFO',
        },
    },
}
```

---

## Summary

**Implemented Features**:

- ✅ Flower web monitoring UI
- ✅ Prometheus metrics export
- ✅ Grafana dashboard
- ✅ Exponential backoff retry
- ✅ Circuit breaker pattern
- ✅ Dead letter queue
- ✅ Task execution tracking
- ✅ Resource monitoring
- ✅ Rate limiting
- ✅ Idempotency
- ✅ Timeout handling
- ✅ Periodic cleanup tasks

**Quick Commands**:

```bash
# Start worker
celery -A config worker --loglevel=info --concurrency=4

# Start Flower
celery -A config flower --port=5555

# Start Beat
celery -A config beat --loglevel=info

# Check worker status
celery -A config inspect stats

# Purge queue
celery -A config purge
```

**Key Files**:

- `requirements_celery.txt` - Dependencies
- `celery_monitoring/__init__.py` - Retry strategies
- `celery_monitoring/monitoring.py` - Metrics and tracking
- `celery_monitoring/dead_letter.py` - Failed task management
- `config/flowerconfig.py` - Flower configuration
- `config/grafana_celery_dashboard.json` - Grafana dashboard
- `future_skills/tasks.py` - Enhanced tasks

**Resources**:

- Flower UI: http://localhost:5555
- Prometheus metrics: http://localhost:9808/metrics
- Celery Docs: https://docs.celeryproject.org/
- Flower Docs: https://flower.readthedocs.io/

---

**Need Help?** Check the troubleshooting section or review task execution logs in Flower UI.
