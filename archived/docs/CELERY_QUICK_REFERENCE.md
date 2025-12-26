# Celery Monitoring - Quick Reference Card

---

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run migrations
python manage.py migrate

# 3. Start services
celery -A config worker --loglevel=info --concurrency=4  # Terminal 1
celery -A config beat --loglevel=info                    # Terminal 2
celery -A config flower --port=5555                      # Terminal 3
```

---

## 📊 Monitoring Dashboards

| Service        | URL                           | Purpose                   |
| -------------- | ----------------------------- | ------------------------- |
| **Flower**     | http://localhost:5555         | Real-time task monitoring |
| **Prometheus** | http://localhost:9808/metrics | Metrics endpoint          |
| **Grafana**    | http://localhost:3000         | Visual dashboards         |

---

## 🔄 Retry Strategies

### Exponential Backoff

```python
@shared_task
@retry_with_exponential_backoff(max_retries=5, base_delay=60)
def my_task():
    pass
```

**Delays**: 60s → 120s → 240s → 480s → 960s

### Circuit Breaker

```python
@shared_task
@with_circuit_breaker(name='api', fail_max=5, reset_timeout=300)
def call_api():
    pass
```

**States**: CLOSED → OPEN (after 5 failures) → HALF_OPEN (after 5 min)

### Dead Letter Queue

```python
@shared_task
@with_dead_letter_queue(max_retries=3)
def critical_task():
    pass
```

**After 3 failures** → Sent to dead letter queue for manual inspection

### Composite (All Strategies)

```python
@shared_task
@with_advanced_retry(
    max_retries=5,
    use_circuit_breaker=True,
    use_dead_letter_queue=True,
    rate_limit_calls=100
)
def protected_task():
    pass
```

---

## 📈 Key Metrics

```promql
# Success Rate
(celery_task_completed_total / (celery_task_completed_total + celery_task_failed_total)) * 100

# P95 Latency
histogram_quantile(0.95, rate(celery_task_duration_seconds_bucket[5m]))

# Queue Length
celery_queue_length

# Active Tasks
celery_active_tasks
```

---

## 🔍 Inspection Commands

```bash
# Worker Status
celery -A config inspect stats

# Active Tasks
celery -A config inspect active

# Scheduled Tasks
celery -A config inspect scheduled

# Registered Tasks
celery -A config inspect registered

# Purge All Queues
celery -A config purge

# Real-time Events
celery -A config events
```

---

## 🗃️ Dead Letter Queue Management

### Python Shell

```python
from celery_monitoring.dead_letter import DeadLetterTask, reprocess_dead_letter_tasks

# List failed tasks
failed = DeadLetterTask.objects.filter(reprocessed=False)

# Reprocess single task
task = DeadLetterTask.objects.get(task_id='abc123')
result = task.reprocess()

# Bulk reprocess
results = reprocess_dead_letter_tasks(task_name='my_task', limit=10)
print(f"Success: {results['success']}, Failed: {results['failed']}")
```

---

## 📊 Performance Analysis

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

# Find bottlenecks
slowest = get_slowest_tasks(limit=10, hours=24)
```

---

## ⚙️ Configuration

### Worker Options

```bash
# Autoscaling
celery -A config worker --autoscale=10,3

# Fixed concurrency
celery -A config worker --concurrency=8

# Specific queues
celery -A config worker --queues=training,default

# Pool types
--pool=prefork  # Default (CPU-bound)
--pool=gevent   # Async I/O (IO-bound)
--pool=solo     # Single process (debugging)
```

### Settings.py

```python
# Task routing
CELERY_TASK_ROUTES = {
    'critical.*': {'queue': 'high', 'priority': 10},
    'normal.*': {'queue': 'default', 'priority': 5},
}

# Worker limits
CELERY_WORKER_MAX_TASKS_PER_CHILD = 50
CELERY_WORKER_MAX_MEMORY_PER_CHILD = 200000  # 200MB

# Result backend
CELERY_RESULT_BACKEND = 'django-db'
CELERY_RESULT_EXPIRES = 3600  # 1 hour

# Task events
CELERY_SEND_EVENTS = True
CELERY_TASK_TRACK_STARTED = True
```

---

## 🐛 Troubleshooting

### Worker Not Starting

```bash
# Check Redis
redis-cli ping  # Should return PONG

# Check broker URL
python manage.py shell -c "from django.conf import settings; print(settings.CELERY_BROKER_URL)"

# Debug mode
celery -A config worker --loglevel=debug
```

### Tasks Not Executing

```bash
# Verify worker consumes correct queue
celery -A config inspect active_queues

# Check task registration
celery -A config inspect registered

# Monitor real-time
celery -A config events
```

### High Memory Usage

```python
# Enable memory limits
CELERY_WORKER_MAX_MEMORY_PER_CHILD = 200000

# Monitor memory
@monitor_task(track_memory=True)
def my_task():
    pass
```

### Task Stuck in PENDING

```python
# Check task state
from celery.result import AsyncResult
result = AsyncResult(task_id)
print(result.state)

# Revoke stuck task
result.revoke(terminate=True)
```

---

## 📅 Scheduled Tasks (Beat)

```python
# settings.py
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'daily-cleanup': {
        'task': 'my_app.cleanup',
        'schedule': crontab(hour=2, minute=0),  # 2 AM daily
    },
    'every-5-minutes': {
        'task': 'my_app.health_check',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
    },
}
```

---

## 📦 Task Patterns

### Chain (Sequential)

```python
from celery import chain

workflow = chain(
    task1.s(arg),
    task2.s(),
    task3.s()
)
workflow.apply_async()
```

### Group (Parallel)

```python
from celery import group

job = group(
    task.s(1),
    task.s(2),
    task.s(3)
)
result = job.apply_async()
```

### Chord (Parallel + Callback)

```python
from celery import chord

callback = chord(
    (task.s(i) for i in range(10)),
    summarize.s()
)
result = callback.apply_async()
```

---

## 📝 Logging

```python
import logging
logger = logging.getLogger(__name__)

@shared_task
def my_task():
    logger.info("Task started")
    try:
        # Task logic
        logger.info("Task completed")
    except Exception as e:
        logger.error(f"Task failed: {e}", exc_info=True)
        raise
```

---

## 🔐 Security

### Flower Authentication

```bash
# Basic auth
celery -A config flower --port=5555 --basic_auth=user:password

# Multiple users
--basic_auth=user1:pass1,user2:pass2
```

### Task Serialization

```python
# Only accept JSON (secure)
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
```

---

## 📚 Resources

- **Full Guide**: `docs/CELERY_MONITORING_GUIDE.md`
- **Setup Script**: `./scripts/setup_celery_monitoring.sh`
- **Celery Docs**: https://docs.celeryproject.org/
- **Flower Docs**: https://flower.readthedocs.io/

---

## 🎯 Common Tasks

```bash
# Start everything
./scripts/setup_celery_monitoring.sh

# Stop all workers
pkill -f 'celery.*worker'

# Restart worker pool
celery -A config control pool_restart

# Graceful shutdown
celery -A config control shutdown
```

---

**Need Help?** Run `./scripts/setup_celery_monitoring.sh` for interactive setup
