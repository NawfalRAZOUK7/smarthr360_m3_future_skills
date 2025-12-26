# SmartHR360 Deployment Guide

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Environment Configuration](#environment-configuration)
4. [Local Development Setup](#local-development-setup)
5. [Docker Deployment](#docker-deployment)
6. [Production Deployment](#production-deployment)
7. [Database Setup](#database-setup)
8. [Monitoring Setup](#monitoring-setup)
9. [Backup & Recovery](#backup--recovery)
10. [Troubleshooting](#troubleshooting)

---

## Overview

This guide covers deploying SmartHR360 Future Skills Platform across different environments:

- **Local Development**: SQLite, Django dev server
- **Docker**: Docker Compose with PostgreSQL, Redis, Nginx
- **Production**: Kubernetes/Cloud deployment with managed services

---

## Prerequisites

### System Requirements

**Development:**

- Python 3.10 or higher
- pip and virtualenv
- Git
- 4GB RAM minimum
- 10GB disk space

**Docker Deployment:**

- Docker 20.10+
- Docker Compose 2.0+
- 8GB RAM minimum
- 50GB disk space

**Production Deployment:**

- Kubernetes 1.24+ OR Cloud provider (AWS/Azure/GCP)
- PostgreSQL 14+
- Redis 7.0+
- 16GB RAM minimum per node
- 100GB+ disk space

### Required Services

- PostgreSQL database
- Redis cache/broker
- (Optional) Elasticsearch for logging
- (Optional) Prometheus for metrics
- (Optional) Grafana for visualization

---

## Environment Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Django Settings
SECRET_KEY=your-secret-key-here-change-in-production
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,yourdomain.com
ENVIRONMENT=production  # development, staging, production

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/smarthr360
DB_NAME=smarthr360
DB_USER=smarthr360_user
DB_PASSWORD=secure_password
DB_HOST=localhost
DB_PORT=5432

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=django-db

# Security
CORS_ALLOWED_ORIGINS=http://localhost:3000,https://yourdomain.com
CSRF_TRUSTED_ORIGINS=http://localhost:3000,https://yourdomain.com

# JWT Settings
JWT_SECRET_KEY=your-jwt-secret-key
JWT_ACCESS_TOKEN_LIFETIME=30  # minutes
JWT_REFRESH_TOKEN_LIFETIME=7  # days

# Rate Limiting
RATELIMIT_ENABLE=True
RATELIMIT_USE_CACHE=default

# ML Settings
FUTURE_SKILLS_USE_ML=True
ML_MODEL_PATH=artifacts/models/
ML_MODEL_VERSION=v1.0.0

# File Storage
MEDIA_ROOT=/var/www/smarthr360/media
STATIC_ROOT=/var/www/smarthr360/static

# Logging & Monitoring
LOG_LEVEL=INFO
LOGSTASH_HOST=localhost
LOGSTASH_PORT=5000

# Elastic APM
ELASTIC_APM_SERVER_URL=https://your-apm-server:8200
ELASTIC_APM_SECRET_TOKEN=your-token
ELASTIC_APM_SERVICE_NAME=smarthr360
ELASTIC_APM_ENVIRONMENT=production

# Sentry
SENTRY_DSN=https://your-sentry-dsn
SENTRY_TRACES_SAMPLE_RATE=0.1

# Email Configuration (for alerts)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@example.com
EMAIL_HOST_PASSWORD=your-email-password
DEFAULT_FROM_EMAIL=noreply@smarthr360.com

# Admin
ADMIN_URL=admin/  # Change in production for security
```

### Generate Secret Keys

```bash
# Generate Django SECRET_KEY
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'

# Generate JWT SECRET_KEY
python -c 'import secrets; print(secrets.token_urlsafe(50))'
```

---

## Local Development Setup

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/smarthr360_m3_future_skills.git
cd smarthr360_m3_future_skills
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate
```

### 3. Install Dependencies

```bash
# Install all dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt

# Install ML dependencies (optional)
pip install -r requirements_ml.txt
```

### 4. Setup Database

```bash
# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Load initial data (optional)
python manage.py loaddata future_skills/fixtures/initial_data.json
```

### 5. Setup Logging

```bash
# Create log directories
make -f Makefile.logging logs-setup

# Test logging
make -f Makefile.logging logs-test
```

### 6. Run Development Server

```bash
# Start Django development server
python manage.py runserver

# In another terminal, start Celery worker (optional)
celery -A config worker -l info

# In another terminal, start Celery beat (optional)
celery -A config beat -l info
```

### 7. Access Application

- **API**: http://localhost:8000/api/
- **Admin**: http://localhost:8000/admin/
- **API Docs**: http://localhost:8000/api/docs/
- **Health Check**: http://localhost:8000/api/health/
- **Metrics**: http://localhost:8000/metrics

---

## Docker Deployment

### 1. Build Docker Images

```bash
# Build production image
docker build -t smarthr360:latest .

# Or use docker-compose
docker-compose -f docker-compose.prod.yml build
```

### 2. Configure Docker Environment

Create `docker-compose.prod.yml`:

```yaml
version: "3.8"

services:
  db:
    image: postgres:14
    environment:
      POSTGRES_DB: smarthr360
      POSTGRES_USER: smarthr360_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U smarthr360_user"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

  web:
    image: smarthr360:latest
    command: gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4 --timeout 120
    volumes:
      - static_volume:/app/staticfiles
      - media_volume:/app/media
      - ./logs:/app/logs
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health/"]
      interval: 30s
      timeout: 10s
      retries: 3

  worker:
    image: smarthr360:latest
    command: celery -A config worker -l info --concurrency=4
    volumes:
      - ./logs:/app/logs
      - media_volume:/app/media
    env_file:
      - .env
    depends_on:
      - db
      - redis

  beat:
    image: smarthr360:latest
    command: celery -A config beat -l info
    volumes:
      - ./logs:/app/logs
    env_file:
      - .env
    depends_on:
      - db
      - redis

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - static_volume:/app/staticfiles:ro
      - media_volume:/app/media:ro
    depends_on:
      - web

volumes:
  postgres_data:
  redis_data:
  static_volume:
  media_volume:
```

### 3. Start Services

```bash
# Start all services
docker-compose -f docker-compose.prod.yml up -d

# Check service status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Run migrations
docker-compose -f docker-compose.prod.yml exec web python manage.py migrate

# Create superuser
docker-compose -f docker-compose.prod.yml exec web python manage.py createsuperuser

# Collect static files
docker-compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput
```

### 4. Verify Deployment

```bash
# Check health
curl http://localhost/api/health/

# Test API
curl http://localhost/api/v2/skills/

# Check metrics
curl http://localhost/metrics
```

---

## Production Deployment

### Kubernetes Deployment

#### 1. Create Namespace

```bash
kubectl create namespace smarthr360
```

#### 2. Create ConfigMap

```yaml
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: smarthr360-config
  namespace: smarthr360
data:
  ENVIRONMENT: "production"
  DEBUG: "False"
  LOG_LEVEL: "INFO"
  ALLOWED_HOSTS: "*.smarthr360.com"
  FUTURE_SKILLS_USE_ML: "True"
```

```bash
kubectl apply -f k8s/configmap.yaml
```

#### 3. Create Secrets

```bash
# Create secrets
kubectl create secret generic smarthr360-secrets \
  --from-literal=SECRET_KEY='your-secret-key' \
  --from-literal=DB_PASSWORD='your-db-password' \
  --from-literal=JWT_SECRET_KEY='your-jwt-secret' \
  --from-literal=ELASTIC_APM_SECRET_TOKEN='your-apm-token' \
  --from-literal=SENTRY_DSN='your-sentry-dsn' \
  --namespace=smarthr360
```

#### 4. Deploy PostgreSQL

```yaml
# k8s/postgres.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: smarthr360
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
        - name: postgres
          image: postgres:14
          ports:
            - containerPort: 5432
          env:
            - name: POSTGRES_DB
              value: smarthr360
            - name: POSTGRES_USER
              value: smarthr360_user
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: smarthr360-secrets
                  key: DB_PASSWORD
          volumeMounts:
            - name: postgres-storage
              mountPath: /var/lib/postgresql/data
  volumeClaimTemplates:
    - metadata:
        name: postgres-storage
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 100Gi
---
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: smarthr360
spec:
  selector:
    app: postgres
  ports:
    - port: 5432
      targetPort: 5432
  clusterIP: None
```

#### 5. Deploy Redis

```yaml
# k8s/redis.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: smarthr360
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
        - name: redis
          image: redis:7-alpine
          ports:
            - containerPort: 6379
          volumeMounts:
            - name: redis-storage
              mountPath: /data
      volumes:
        - name: redis-storage
          persistentVolumeClaim:
            claimName: redis-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: redis
  namespace: smarthr360
spec:
  selector:
    app: redis
  ports:
    - port: 6379
      targetPort: 6379
```

#### 6. Deploy Application

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: smarthr360-api
  namespace: smarthr360
spec:
  replicas: 3
  selector:
    matchLabels:
      app: smarthr360-api
  template:
    metadata:
      labels:
        app: smarthr360-api
    spec:
      containers:
        - name: api
          image: your-registry/smarthr360:latest
          ports:
            - containerPort: 8000
          env:
            - name: SECRET_KEY
              valueFrom:
                secretKeyRef:
                  name: smarthr360-secrets
                  key: SECRET_KEY
            - name: DB_HOST
              value: postgres
            - name: DB_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: smarthr360-secrets
                  key: DB_PASSWORD
            - name: REDIS_URL
              value: redis://redis:6379/0
          envFrom:
            - configMapRef:
                name: smarthr360-config
          resources:
            requests:
              memory: "1Gi"
              cpu: "500m"
            limits:
              memory: "2Gi"
              cpu: "1000m"
          livenessProbe:
            httpGet:
              path: /api/health/alive/
              port: 8000
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /api/health/ready/
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: smarthr360-api
  namespace: smarthr360
spec:
  selector:
    app: smarthr360-api
  ports:
    - port: 8000
      targetPort: 8000
  type: ClusterIP
```

#### 7. Deploy Celery Workers

```yaml
# k8s/celery-worker.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: celery-worker
  namespace: smarthr360
spec:
  replicas: 3
  selector:
    matchLabels:
      app: celery-worker
  template:
    metadata:
      labels:
        app: celery-worker
    spec:
      containers:
        - name: worker
          image: your-registry/smarthr360:latest
          command: ["celery", "-A", "config", "worker", "-l", "info", "--concurrency=4"]
          env:
            - name: REDIS_URL
              value: redis://redis:6379/0
            - name: DB_HOST
              value: postgres
            - name: DB_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: smarthr360-secrets
                  key: DB_PASSWORD
          envFrom:
            - configMapRef:
                name: smarthr360-config
          resources:
            requests:
              memory: "1Gi"
              cpu: "500m"
            limits:
              memory: "2Gi"
              cpu: "1000m"
```

#### 8. Create Ingress

```yaml
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: smarthr360-ingress
  namespace: smarthr360
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
    - hosts:
        - api.smarthr360.com
      secretName: smarthr360-tls
  rules:
    - host: api.smarthr360.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: smarthr360-api
                port:
                  number: 8000
```

#### 9. Deploy Everything

```bash
# Apply all configurations
kubectl apply -f k8s/

# Check deployment status
kubectl get pods -n smarthr360
kubectl get services -n smarthr360
kubectl get ingress -n smarthr360

# Run migrations
kubectl exec -it deployment/smarthr360-api -n smarthr360 -- python manage.py migrate

# Create superuser
kubectl exec -it deployment/smarthr360-api -n smarthr360 -- python manage.py createsuperuser

# Collect static files
kubectl exec -it deployment/smarthr360-api -n smarthr360 -- python manage.py collectstatic --noinput
```

### AWS Deployment (Alternative)

#### Using AWS Elastic Beanstalk

1. **Install EB CLI**:

```bash
pip install awsebcli
```

2. **Initialize EB Application**:

```bash
eb init -p python-3.10 smarthr360 --region us-east-1
```

3. **Create Environment**:

```bash
eb create smarthr360-prod --database.engine postgres --database.size 100
```

4. **Configure Environment Variables**:

```bash
eb setenv SECRET_KEY=your-secret \
  ALLOWED_HOSTS=.elasticbeanstalk.com \
  ENVIRONMENT=production
```

5. **Deploy**:

```bash
eb deploy
```

---

## Database Setup

### PostgreSQL Configuration

#### 1. Install PostgreSQL

```bash
# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib

# macOS
brew install postgresql
```

#### 2. Create Database and User

```bash
# Connect to PostgreSQL
sudo -u postgres psql

# Create database and user
CREATE DATABASE smarthr360;
CREATE USER smarthr360_user WITH PASSWORD 'secure_password';
ALTER ROLE smarthr360_user SET client_encoding TO 'utf8';
ALTER ROLE smarthr360_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE smarthr360_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE smarthr360 TO smarthr360_user;
\q
```

#### 3. Run Migrations

```bash
python manage.py migrate
```

#### 4. Create Initial Data

```bash
# Create superuser
python manage.py createsuperuser

# Load fixtures (if available)
python manage.py loaddata initial_data
```

### Database Backup

```bash
# Backup database
pg_dump -U smarthr360_user -h localhost smarthr360 > backup_$(date +%Y%m%d).sql

# Restore database
psql -U smarthr360_user -h localhost smarthr360 < backup_20240101.sql
```

---

## Monitoring Setup

### 1. Setup Prometheus

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: "smarthr360"
    static_configs:
      - targets: ["localhost:8000"]
    metrics_path: "/metrics"
```

### 2. Setup Grafana

```bash
# Add datasource
curl -X POST http://admin:admin@localhost:3000/api/datasources \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Prometheus",
    "type": "prometheus",
    "url": "http://localhost:9090",
    "access": "proxy"
  }'

# Import dashboard (ID: 14056 for Django)
```

### 3. Setup Elastic APM

```bash
# Configure in .env
ELASTIC_APM_SERVER_URL=https://your-apm-server:8200
ELASTIC_APM_SECRET_TOKEN=your-token
ELASTIC_APM_SERVICE_NAME=smarthr360
```

### 4. Setup Sentry

```bash
# Configure in .env
SENTRY_DSN=https://your-sentry-dsn
SENTRY_TRACES_SAMPLE_RATE=0.1
```

---

## Backup & Recovery

### Automated Backup Script

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/var/backups/smarthr360"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup database
pg_dump -U smarthr360_user smarthr360 | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Backup media files
tar -czf $BACKUP_DIR/media_$DATE.tar.gz media/

# Backup ML models
tar -czf $BACKUP_DIR/models_$DATE.tar.gz artifacts/models/

# Remove backups older than 30 days
find $BACKUP_DIR -name "*.gz" -mtime +30 -delete

echo "Backup completed: $DATE"
```

### Setup Cron Job

```bash
# Add to crontab
crontab -e

# Daily backup at 2 AM
0 2 * * * /path/to/backup.sh >> /var/log/backup.log 2>&1
```

### Recovery Process

```bash
# Restore database
gunzip -c /var/backups/smarthr360/db_20240101_020000.sql.gz | psql -U smarthr360_user smarthr360

# Restore media files
tar -xzf /var/backups/smarthr360/media_20240101_020000.tar.gz -C /var/www/smarthr360/

# Restore ML models
tar -xzf /var/backups/smarthr360/models_20240101_020000.tar.gz -C /var/www/smarthr360/

# Run migrations if needed
python manage.py migrate

# Restart services
sudo systemctl restart gunicorn celery
```

---

## Troubleshooting

### Common Issues

#### 1. Database Connection Errors

```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Test connection
psql -U smarthr360_user -h localhost -d smarthr360

# Check credentials in .env
cat .env | grep DB_
```

#### 2. Redis Connection Errors

```bash
# Check Redis is running
redis-cli ping

# Test connection
redis-cli -h localhost -p 6379

# Check Redis URL
echo $REDIS_URL
```

#### 3. Static Files Not Loading

```bash
# Collect static files
python manage.py collectstatic --noinput

# Check STATIC_ROOT and STATIC_URL in settings
python manage.py diffsettings | grep STATIC

# Verify Nginx configuration
nginx -t
```

#### 4. Celery Workers Not Running

```bash
# Check Celery status
celery -A config inspect active

# Check Redis broker
celery -A config inspect ping

# View worker logs
celery -A config worker -l debug
```

#### 5. High Memory Usage

```bash
# Check process memory
ps aux | grep python | sort -k4 -rn

# Monitor in real-time
htop

# Check Django queries
python manage.py shell
>>> from django.db import connection
>>> print(len(connection.queries))
```

### Performance Tuning

```bash
# Check slow queries (PostgreSQL)
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;

# Enable query logging
# In postgresql.conf:
log_min_duration_statement = 1000  # Log queries > 1s

# Check Gunicorn workers
ps aux | grep gunicorn | wc -l

# Monitor request rate
tail -f logs/application.log | grep "request_completed"
```

### Health Check Commands

```bash
# Application health
curl http://localhost:8000/api/health/

# Database health
python manage.py health_check --check database

# Cache health
python manage.py health_check --check cache

# Celery health
python manage.py health_check --check celery

# Full health check
python manage.py health_check --json
```

---

## Security Checklist

Before going to production:

- [ ] Change `SECRET_KEY` and `JWT_SECRET_KEY`
- [ ] Set `DEBUG=False`
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Use strong database passwords
- [ ] Enable HTTPS/TLS
- [ ] Configure CORS properly
- [ ] Enable rate limiting
- [ ] Setup security headers
- [ ] Configure CSP
- [ ] Enable login attempt protection
- [ ] Setup monitoring and alerts
- [ ] Configure backups
- [ ] Review and test disaster recovery
- [ ] Perform security audit (`make security-scan`)
- [ ] Update dependencies (`pip-audit`)
- [ ] Change default admin URL
- [ ] Setup SSL certificates
- [ ] Configure firewall rules
- [ ] Enable database encryption
- [ ] Setup VPN for admin access
- [ ] Document access procedures

---

## Useful Commands

### Development

```bash
# Run development server
make run

# Run tests
make test

# Check code quality
make lint

# Run security scan
make security-scan
```

### Docker

```bash
# Build and start
docker-compose up --build -d

# View logs
docker-compose logs -f

# Execute commands
docker-compose exec web python manage.py migrate

# Stop services
docker-compose down

# Clean up
docker-compose down -v
```

### Kubernetes

```bash
# Deploy
kubectl apply -f k8s/

# Check status
kubectl get all -n smarthr360

# View logs
kubectl logs -f deployment/smarthr360-api -n smarthr360

# Execute command
kubectl exec -it deployment/smarthr360-api -n smarthr360 -- bash

# Scale deployment
kubectl scale deployment smarthr360-api --replicas=5 -n smarthr360
```

---

## Support

For deployment issues:

- Check logs: `tail -f logs/application.log`
- Review documentation: `docs/`
- Contact DevOps team
- Open GitHub issue

**Version**: 1.0.0  
**Last Updated**: November 2024
