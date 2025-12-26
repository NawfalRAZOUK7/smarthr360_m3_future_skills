# SmartHR360 Future Skills - CI/CD Implementation Guide

## Table of Contents

1. [Project Overview](#project-overview)
2. [Current Architecture Analysis](#current-architecture-analysis)
3. [CI/CD Strategy](#cicd-strategy)
4. [Prerequisites](#prerequisites)
5. [GitHub Actions Workflow Setup](#github-actions-workflow-setup)
6. [Docker Registry Setup](#docker-registry-setup)
7. [Environment Configuration](#environment-configuration)
8. [Security Implementation](#security-implementation)
9. [Deployment Pipeline](#deployment-pipeline)
10. [Monitoring & Alerting](#monitoring--alerting)
11. [Rollback Strategy](#rollback-strategy)
12. [Testing Strategy](#testing-strategy)
13. [Performance Optimization](#performance-optimization)
14. [Troubleshooting](#troubleshooting)

---

## Project Overview

SmartHR360 Future Skills is a Django-based ML platform that provides:

- **REST API** for skill predictions and recommendations
- **Machine Learning** models for workforce analytics
- **Real-time processing** with Celery and Redis
- **Production-ready deployment** with Docker and PostgreSQL
- **Comprehensive testing** suite (unit, integration, e2e, ML tests)
- **Security features** (JWT auth, rate limiting, monitoring)

### Key Components

- **Backend**: Django REST Framework with PostgreSQL
- **ML Pipeline**: Scikit-learn models with MLflow tracking
- **Async Processing**: Celery workers with Redis broker
- **Web Server**: Gunicorn with Nginx reverse proxy
- **Monitoring**: Prometheus metrics, health checks
- **Security**: JWT authentication, rate limiting, security scanning

---

## Current Architecture Analysis

### Technology Stack

```
Frontend: N/A (API-only)
Backend: Django 5.2+ + DRF
Database: PostgreSQL 15
Cache/Broker: Redis 7
Async Tasks: Celery 5.5+
ML: Scikit-learn + MLflow
Web Server: Gunicorn + Nginx
Container: Docker + Docker Compose
Testing: pytest + coverage
Code Quality: black, flake8, isort, mypy, bandit
Security: safety, pip-audit
```

### Service Architecture

```
┌─────────────────┐    ┌─────────────────┐
│   Nginx (SSL)   │    │   MLflow UI     │
│     443/80      │    │     5500        │
└─────────┬───────┘    └─────────────────┘
          │
┌─────────┴─────────┐
│   Django App      │
│   Gunicorn:8000   │◄──┐
└─────────┬─────────┘   │
          │             │
┌─────────┼─────────┐   │
│ PostgreSQL:5432   │   │
│   Redis:6379      │   │
└─────────┼─────────┘   │
          │             │
┌─────────┴─────────┐   │
│  Celery Workers   │   │
│   Async Tasks     │   │
└───────────────────┘   │
                        │
┌───────────────────────┘
│   ML Pipeline Service
│   Training & Prediction
└─────────────────────────
```

### Current Deployment Environments

1. **Local Development**: SQLite + Django dev server
2. **Docker Development**: Full stack with docker-compose.yml
3. **Docker Production**: Optimized stack with docker-compose.prod.yml

---

## CI/CD Strategy

### Pipeline Overview

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Code Push  │───▶│    CI       │───▶│    Test     │───▶│   Security  │
│             │    │  Checks     │    │  Coverage   │    │   Scan      │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                                                            │
┌─────────────┐    ┌─────────────┐    ┌─────────────┐       │
│  Build      │◄───│   Docker    │◄───│   Deploy    │◄──────┘
│  Images     │    │   Test      │    │   Staging   │
└─────────────┘    └─────────────┘    └─────────────┘
                                                            │
┌─────────────┐    ┌─────────────┐    ┌─────────────┐       │
│ Production  │◄───│   E2E       │◄───│   Manual    │◄──────┘
│ Deployment  │    │   Tests     │    │   Approval  │
└─────────────┘    └─────────────┘    └─────────────┘
```

### Branch Strategy

```
main (production) ◄── staging ◄── feature/*
                    │
                    └── hotfix/*
```

### Environment Strategy

1. **Development**: Feature branches, automated testing
2. **Staging**: main branch merges, full integration testing
3. **Production**: Tag-based releases, manual approval required

---

## Prerequisites

### Required Tools & Services

```bash
# Local Development
- Python 3.10+
- Docker 24.0+
- Docker Compose 2.20+
- Git 2.30+
- Make 4.3+

# Cloud Services (choose one)
- GitHub Actions (free for public repos)
- GitLab CI/CD
- AWS CodePipeline
- Azure DevOps

# Container Registry
- Docker Hub (free)
- GitHub Container Registry
- AWS ECR
- Google Artifact Registry

# Deployment Target
- Docker Host
- Kubernetes Cluster
- Cloud Run (GCP)
- ECS Fargate (AWS)
- Azure Container Apps
```

### Repository Setup

```bash
# Clone repository
git clone https://github.com/NawfalRAZOUK7/smarthr360_m3_future_skills.git
cd smarthr360_m3_future_skills

# Create required branches
git checkout -b staging
git checkout main
git push origin staging main
```

---

## GitHub Actions Workflow Setup

### 1. Create Workflow Directory Structure

```bash
mkdir -p .github/workflows
touch .github/workflows/{ci.yml,build.yml,deploy-staging.yml,deploy-production.yml}
```

### 2. CI Pipeline (ci.yml)

```yaml
name: CI Pipeline

on:
  push:
    branches: [main, staging, feature/**]
  pull_request:
    branches: [main, staging]

env:
  PYTHON_VERSION: "3.12"
  NODE_VERSION: "18"
  DOCKER_BUILDKIT: 1

jobs:
  # Code Quality Checks
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Cache pip dependencies
        uses: actions/cache@v3
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements*.txt') }}
          restore-keys: |
            ${{ runner.os }}-pip-

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements-dev.txt

      - name: Run code quality checks
        run: |
          make lint
          make format-check
          make type-check

      - name: Security scan
        run: |
          make security-scan
          safety check
          bandit -r future_skills/ -f json -o security-report.json

      - name: Upload security report
        uses: actions/upload-artifact@v3
        with:
          name: security-report
          path: security-report.json

  # Unit Tests
  test-unit:
    runs-on: ubuntu-latest
    needs: quality
    services:
      postgres:
        image: postgres:15-alpine
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Cache pip dependencies
        uses: actions/cache@v3
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements*.txt') }}
          restore-keys: |
            ${{ runner.os }}-pip-

      - name: Install dependencies
        run: pip install -r requirements-dev.txt

      - name: Run database migrations
        run: |
          python manage.py migrate
        env:
          DJANGO_SETTINGS_MODULE: config.settings.test
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db
          REDIS_URL: redis://localhost:6379/0

      - name: Run unit tests
        run: |
          pytest future_skills/tests/ -v --cov=future_skills --cov-report=xml --cov-report=term-missing --cov-fail-under=80
        env:
          DJANGO_SETTINGS_MODULE: config.settings.test
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db
          REDIS_URL: redis://localhost:6379/0

      - name: Upload coverage reports
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          flags: unit-tests
          name: unit-tests-coverage

  # ML Tests
  test-ml:
    runs-on: ubuntu-latest
    needs: quality
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Cache pip dependencies
        uses: actions/cache@v3
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements*.txt') }}
          restore-keys: |
            ${{ runner.os }}-pip-

      - name: Install dependencies
        run: |
          pip install -r requirements-dev.txt
          pip install -r ml/requirements.txt

      - name: Run ML tests
        run: |
          pytest ml/tests/ -v --cov=ml --cov-report=xml --cov-report=term-missing --cov-fail-under=60 -m "not slow"
        env:
          DJANGO_SETTINGS_MODULE: config.settings.test

      - name: Upload ML coverage reports
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          flags: ml-tests
          name: ml-tests-coverage

  # Integration Tests
  test-integration:
    runs-on: ubuntu-latest
    needs: [test-unit, test-ml]
    services:
      postgres:
        image: postgres:15-alpine
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Cache pip dependencies
        uses: actions/cache@v3
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements*.txt') }}
          restore-keys: |
            ${{ runner.os }}-pip-

      - name: Install dependencies
        run: pip install -r requirements-dev.txt

      - name: Run integration tests
        run: |
          pytest tests/integration/ -v --cov=future_skills --cov-report=xml --cov-report=term-missing --cov-fail-under=70
        env:
          DJANGO_SETTINGS_MODULE: config.settings.test
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db
          REDIS_URL: redis://localhost:6379/0

      - name: Upload integration coverage reports
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          flags: integration-tests
          name: integration-tests-coverage

  # Docker Build Test
  docker-test:
    runs-on: ubuntu-latest
    needs: [test-unit, test-ml, test-integration]
    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Build test images
        run: |
          docker build -f Dockerfile.base -t smarthr360/base:test .
          docker build -f Dockerfile.web -t smarthr360/web:test .
          docker build -f Dockerfile.celery -t smarthr360/celery:test .
          docker build -f Dockerfile.nginx -t smarthr360/nginx:test .

      - name: Test Docker images
        run: |
          # Test web container
          docker run --rm smarthr360/web:test python manage.py check --deploy
          # Test celery container
          docker run --rm smarthr360/celery:test celery -A config worker --help | head -5

  # Performance Tests
  performance:
    runs-on: ubuntu-latest
    needs: docker-test
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4

      - name: Run performance tests
        run: |
          make test-performance
        env:
          DJANGO_SETTINGS_MODULE: config.settings.test

  # Final status check
  ci-success:
    runs-on: ubuntu-latest
    needs: [quality, test-unit, test-ml, test-integration, docker-test]
    if: success()
    steps:
      - name: CI Pipeline Success
        run: echo "✅ All CI checks passed successfully!"
```

### 3. Build Pipeline (build.yml)

```yaml
name: Build & Push Docker Images

on:
  push:
    branches: [main, staging]
  workflow_run:
    workflows: ["CI Pipeline"]
    types: [completed]
    branches: [main, staging]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  build:
    runs-on: ubuntu-latest
    if: ${{ github.event.workflow_run.conclusion == 'success' || github.event_name == 'push' }}

    permissions:
      contents: read
      packages: write

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Log in to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=ref,event=pr
            type=sha,prefix={{branch}}-
            type=raw,value=latest,enable={{is_default_branch}}

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Build and push base image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: ./Dockerfile.base
          push: true
          tags: ${{ steps.meta.outputs.tags }}-base
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Build and push web image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: ./Dockerfile.web
          push: true
          tags: ${{ steps.meta.outputs.tags }}-web
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Build and push celery image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: ./Dockerfile.celery
          push: true
          tags: ${{ steps.meta.outputs.tags }}-celery
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Build and push nginx image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: ./Dockerfile.nginx
          push: true
          tags: ${{ steps.meta.outputs.tags }}-nginx
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Build and push ml-pipeline image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: ./Dockerfile.ml
          push: true
          tags: ${{ steps.meta.outputs.tags }}-ml
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Generate artifact attestation
        uses: actions/attest-build-provenance@v1
        with:
          subject-name: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME}}
          subject-digest: ${{ steps.push.outputs.digest }}
          push-to-registry: true
```

### 4. Staging Deployment (deploy-staging.yml)

```yaml
name: Deploy to Staging

on:
  push:
    branches: [staging]
  workflow_run:
    workflows: ["Build & Push Docker Images"]
    types: [completed]
    branches: [staging]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  deploy-staging:
    runs-on: ubuntu-latest
    if: ${{ github.event.workflow_run.conclusion == 'success' || github.event_name == 'push' }}

    environment:
      name: staging
      url: https://staging.smarthr360.com

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Configure SSH
        run: |
          mkdir -p ~/.ssh
          echo "$SSH_PRIVATE_KEY" > ~/.ssh/id_rsa
          chmod 600 ~/.ssh/id_rsa
          ssh-keyscan -H "$STAGING_HOST" >> ~/.ssh/known_hosts
        env:
          SSH_PRIVATE_KEY: ${{ secrets.STAGING_SSH_PRIVATE_KEY }}
          STAGING_HOST: ${{ secrets.STAGING_HOST }}

      - name: Deploy to staging
        run: |
          ssh -o StrictHostKeyChecking=no $STAGING_USER@$STAGING_HOST << 'EOF'
            cd /opt/smarthr360
            git pull origin staging
            
            # Update environment variables
            cp .env.staging .env
            
            # Pull latest images
            docker-compose -f docker-compose.staging.yml pull
            
            # Deploy with zero downtime
            docker-compose -f docker-compose.staging.yml up -d --scale web=2
            
            # Wait for health checks
            sleep 30
            
            # Run database migrations
            docker-compose -f docker-compose.staging.yml exec -T web python manage.py migrate
            
            # Scale back to normal
            docker-compose -f docker-compose.staging.yml up -d --scale web=1
            
            # Clean up old images
            docker image prune -f
          EOF
        env:
          STAGING_USER: ${{ secrets.STAGING_USER }}
          STAGING_HOST: ${{ secrets.STAGING_HOST }}

      - name: Run staging tests
        run: |
          # Wait for deployment to be ready
          sleep 60

          # Run smoke tests against staging
          curl -f https://staging.smarthr360.com/api/health/

          # Run API tests against staging
          pytest tests/e2e/ -v --tb=short \
            --api-url=https://staging.smarthr360.com \
            --api-key=${{ secrets.STAGING_API_KEY }}

      - name: Notify deployment success
        if: success()
        run: |
          curl -X POST -H 'Content-type: application/json' \
            --data '{"text":"✅ Staging deployment successful!"}' \
            ${{ secrets.SLACK_WEBHOOK_URL }}

      - name: Notify deployment failure
        if: failure()
        run: |
          curl -X POST -H 'Content-type: application/json' \
            --data '{"text":"❌ Staging deployment failed!"}' \
            ${{ secrets.SLACK_WEBHOOK_URL }}
```

### 5. Production Deployment (deploy-production.yml)

```yaml
name: Deploy to Production

on:
  release:
    types: [published]
  workflow_dispatch:
    inputs:
      environment:
        description: "Target environment"
        required: true
        default: "production"
        type: choice
        options:
          - production
          - blue
          - green

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  deploy-production:
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://api.smarthr360.com

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Configure SSH
        run: |
          mkdir -p ~/.ssh
          echo "$SSH_PRIVATE_KEY" > ~/.ssh/id_rsa
          chmod 600 ~/.ssh/id_rsa
          ssh-keyscan -H "$PRODUCTION_HOST" >> ~/.ssh/known_hosts
        env:
          SSH_PRIVATE_KEY: ${{ secrets.PRODUCTION_SSH_PRIVATE_KEY }}
          PRODUCTION_HOST: ${{ secrets.PRODUCTION_HOST }}

      - name: Deploy to production
        run: |
          ssh -o StrictHostKeyChecking=no $PRODUCTION_USER@$PRODUCTION_HOST << 'EOF'
            cd /opt/smarthr360
            
            # Create backup
            ./scripts/backup.sh
            
            # Pull latest images
            docker-compose -f docker-compose.prod.yml pull
            
            # Blue-green deployment
            if [ "${{ github.event.inputs.environment }}" = "blue" ]; then
              export COMPOSE_PROJECT_NAME=smarthr360-blue
              docker-compose -f docker-compose.prod.yml up -d
              
              # Health check
              for i in {1..30}; do
                if curl -f http://localhost:8000/api/health/; then
                  break
                fi
                sleep 10
              done
              
              # Switch traffic (nginx config update)
              sudo cp nginx/sites-available/smarthr360-blue /etc/nginx/sites-enabled/
              sudo nginx -t && sudo nginx -s reload
              
              # Stop green environment
              export COMPOSE_PROJECT_NAME=smarthr360-green
              docker-compose -f docker-compose.prod.yml down
              
            elif [ "${{ github.event.inputs.environment }}" = "green" ]; then
              export COMPOSE_PROJECT_NAME=smarthr360-green
              docker-compose -f docker-compose.prod.yml up -d
              
              # Health check
              for i in {1..30}; do
                if curl -f http://localhost:8001/api/health/; then
                  break
                fi
                sleep 10
              done
              
              # Switch traffic
              sudo cp nginx/sites-available/smarthr360-green /etc/nginx/sites-enabled/
              sudo nginx -t && sudo nginx -s reload
              
              # Stop blue environment
              export COMPOSE_PROJECT_NAME=smarthr360-blue
              docker-compose -f docker-compose.prod.yml down
              
            else
              # Standard deployment
              docker-compose -f docker-compose.prod.yml up -d
              
              # Run migrations
              docker-compose -f docker-compose.prod.yml exec -T web python manage.py migrate
              
              # Health check
              curl -f http://localhost:8000/api/health/
            fi
            
            # Clean up
            docker image prune -f
            docker volume prune -f
          EOF
        env:
          PRODUCTION_USER: ${{ secrets.PRODUCTION_USER }}
          PRODUCTION_HOST: ${{ secrets.PRODUCTION_HOST }}

      - name: Run production smoke tests
        run: |
          sleep 60
          curl -f https://api.smarthr360.com/api/health/

      - name: Create deployment tag
        if: success()
        run: |
          git tag -a "deploy-$(date +%Y%m%d-%H%M%S)" -m "Production deployment"
          git push origin --tags

      - name: Notify deployment success
        if: success()
        run: |
          curl -X POST -H 'Content-type: application/json' \
            --data '{"text":"🚀 Production deployment successful!"}' \
            ${{ secrets.SLACK_WEBHOOK_URL }}

      - name: Notify deployment failure
        if: failure()
        run: |
          curl -X POST -H 'Content-type: application/json' \
            --data '{"text":"💥 Production deployment failed!"}' \
            ${{ secrets.SLACK_WEBHOOK_URL }}
```

---

## Docker Registry Setup

### GitHub Container Registry (Recommended)

```bash
# Login to GHCR
echo $GITHUB_TOKEN | docker login ghcr.io -u $GITHUB_USERNAME --password-stdin

# Tag and push images
docker tag smarthr360/web:latest ghcr.io/nawfalrazouk7/smarthr360_m3_future_skills/web:latest
docker push ghcr.io/nawfalrazouk7/smarthr360_m3_future_skills/web:latest
```

### Docker Hub Setup

```bash
# Login to Docker Hub
docker login -u $DOCKER_USERNAME -p $DOCKER_PASSWORD

# Tag and push images
docker tag smarthr360/web:latest nawfalrazouk/smarthr360:web-latest
docker push nawfalrazouk/smarthr360:web-latest
```

---

## Environment Configuration

### 1. GitHub Secrets Setup

```bash
# Repository Settings > Secrets and variables > Actions

# Docker Registry
GITHUB_TOKEN: (automatically provided)
DOCKER_USERNAME: your-docker-username
DOCKER_PASSWORD: your-docker-password

# SSH Access
STAGING_SSH_PRIVATE_KEY: (SSH private key for staging server)
PRODUCTION_SSH_PRIVATE_KEY: (SSH private key for production server)
STAGING_HOST: staging.smarthr360.com
PRODUCTION_HOST: api.smarthr360.com
STAGING_USER: deploy
PRODUCTION_USER: deploy

# API Keys
STAGING_API_KEY: your-staging-api-key
PRODUCTION_API_KEY: your-production-api-key

# Notifications
SLACK_WEBHOOK_URL: https://hooks.slack.com/services/...

# Database (if using managed)
DATABASE_URL: postgresql://user:pass@host:5432/db

# Redis (if using managed)
REDIS_URL: redis://host:6379

# MLflow (if using managed)
MLFLOW_TRACKING_URI: https://mlflow.smarthr360.com
```

### 2. Environment Files

```bash
# .env.staging
DJANGO_SETTINGS_MODULE=config.settings.production
DEBUG=False
SECRET_KEY=your-staging-secret-key
DATABASE_URL=postgresql://user:pass@staging-db:5432/smarthr360
REDIS_URL=redis://staging-redis:6379
ALLOWED_HOSTS=staging.smarthr360.com
CORS_ALLOWED_ORIGINS=https://staging-frontend.smarthr360.com

# .env.production
DJANGO_SETTINGS_MODULE=config.settings.production
DEBUG=False
SECRET_KEY=your-production-secret-key
DATABASE_URL=postgresql://user:pass@prod-db:5432/smarthr360
REDIS_URL=redis://prod-redis:6379
ALLOWED_HOSTS=api.smarthr360.com,app.smarthr360.com
CORS_ALLOWED_ORIGINS=https://app.smarthr360.com
```

---

## Security Implementation

### 1. Code Security Scanning

```yaml
# Add to ci.yml
- name: Security scan
  run: |
    # Dependency vulnerability scan
    safety check --output text
    pip-audit --format text

    # Code security scan
    bandit -r future_skills/ -f json -o bandit-report.json

    # Secrets detection
    detect-secrets scan --all-files > secrets-report.json
```

### 2. Container Security

```yaml
# Add to build.yml
- name: Scan container images
  uses: aquasecurity/trivy-action@master
  with:
    scan-type: "image"
    scan-ref: "${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:latest"
    format: "sarif"
    output: "trivy-results.sarif"

- name: Upload Trivy scan results
  uses: github/codeql-action/upload-sarif@v2
  if: always()
  with:
    sarif_file: "trivy-results.sarif"
```

### 3. Infrastructure Security

```yaml
# Add to deploy jobs
- name: Infrastructure security scan
  run: |
    # Check for exposed secrets
    trufflehog --regex --entropy=False .

    # Infrastructure as Code security
    checkov -f docker-compose*.yml --framework dockerfile
```

---

## Deployment Pipeline

### 1. Staging Environment Setup

```bash
# On staging server
sudo apt update
sudo apt install -y docker.io docker-compose git nginx

# Create deploy user
sudo useradd -m -s /bin/bash deploy
sudo usermod -aG docker deploy

# Setup SSH keys
sudo -u deploy mkdir /home/deploy/.ssh
sudo -u deploy chmod 700 /home/deploy/.ssh
# Add GitHub Actions public key to authorized_keys

# Clone repository
sudo -u deploy git clone https://github.com/NawfalRAZOUK7/smarthr360_m3_future_skills.git /opt/smarthr360
cd /opt/smarthr360

# Setup environment
sudo -u deploy cp .env.example .env.staging
# Edit .env.staging with staging values

# Initial deployment
sudo -u deploy make docker-prod
```

### 2. Production Environment Setup

```bash
# On production server
sudo apt update
sudo apt install -y docker.io docker-compose git nginx certbot

# Setup SSL certificates
sudo certbot certonly --standalone -d api.smarthr360.com

# Create deploy user and setup SSH
sudo useradd -m -s /bin/bash deploy
sudo usermod -aG docker deploy

# Clone and setup
sudo -u deploy git clone https://github.com/NawfalRAZOUK7/smarthr360_m3_future_skills.git /opt/smarthr360
cd /opt/smarthr360

# Setup production environment
sudo -u deploy cp .env.example .env.production
# Edit .env.production with production values

# Setup nginx for SSL termination
sudo cp nginx/nginx.conf /etc/nginx/sites-available/smarthr360
sudo ln -s /etc/nginx/sites-available/smarthr360 /etc/nginx/sites-enabled/
sudo nginx -t && sudo nginx -s reload

# Initial deployment
sudo -u deploy make docker-prod
```

### 3. Blue-Green Deployment Setup

```bash
# Create blue and green environments
mkdir -p /opt/smarthr360-blue /opt/smarthr360-green

# Setup blue environment
cd /opt/smarthr360-blue
git clone https://github.com/NawfalRAZOUK7/smarthr360_m3_future_skills.git .
cp .env.production .env
sed -i 's/8000/8001/g' docker-compose.prod.yml

# Setup green environment
cd /opt/smarthr360-green
git clone https://github.com/NawfalRAZOUK7/smarthr360_m3_future_skills.git .
cp .env.production .env
sed -i 's/8000/8002/g' docker-compose.prod.yml

# Setup nginx upstreams
# /etc/nginx/sites-available/smarthr360-blue
upstream django_blue {
    server 127.0.0.1:8001;
}

# /etc/nginx/sites-available/smarthr360-green
upstream django_green {
    server 127.0.0.1:8002;
}
```

---

## Monitoring & Alerting

### 1. Application Monitoring

```yaml
# Add to docker-compose.prod.yml
services:
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:latest
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
    ports:
      - "3000:3000"
```

### 2. Health Checks

```python
# config/settings/production.py
HEALTH_CHECK = {
    'DISK_USAGE_MAX': 90,  # percent
    'MEMORY_MIN': 100,    # in MB
    'CHECK_EXTERNAL_SERVICES': True,
}
```

### 3. Alerting Setup

```yaml
# alerting_rules.yml
groups:
  - name: smarthr360
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"

      - alert: DatabaseDown
        expr: up{job="postgres"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Database is down"
```

---

## Rollback Strategy

### 1. Automated Rollback

```yaml
# Add to deploy-production.yml
- name: Rollback on failure
  if: failure()
  run: |
    ssh -o StrictHostKeyChecking=no $PRODUCTION_USER@$PRODUCTION_HOST << 'EOF'
      cd /opt/smarthr360
      
      # Get previous working commit
      PREVIOUS_COMMIT=$(git log --oneline -n 2 | tail -1 | cut -d' ' -f1)
      git checkout $PREVIOUS_COMMIT
      
      # Rebuild and redeploy
      docker-compose -f docker-compose.prod.yml build
      docker-compose -f docker-compose.prod.yml up -d
      
      # Verify rollback
      curl -f http://localhost:8000/api/health/
    EOF
```

### 2. Manual Rollback

```bash
# On production server
cd /opt/smarthr360

# List recent deployments
git log --oneline -10

# Rollback to specific commit
git checkout <commit-hash>

# Rebuild and redeploy
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d

# Verify
curl http://localhost:8000/api/health/
```

### 3. Database Rollback

```bash
# Create database backup before deployment
docker-compose -f docker-compose.prod.yml exec db pg_dump -U postgres smarthr360 > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore on rollback
docker-compose -f docker-compose.prod.yml exec -T db psql -U postgres smarthr360 < backup_file.sql
```

---

## Testing Strategy

### 1. Test Categories

```python
# pytest.ini markers
markers =
    unit: Unit tests (fast, isolated)
    integration: Integration tests (database, external services)
    e2e: End-to-end tests (full application flow)
    ml: Machine learning tests
    api: API endpoint tests
    performance: Performance tests
    smoke: Quick smoke tests for deployment validation
```

### 2. Test Execution Strategy

```yaml
# CI test matrix
test-matrix:
  - name: "Unit Tests"
    command: "pytest future_skills/tests/ -m 'unit' --cov-fail-under=80"
    timeout: 10

  - name: "Integration Tests"
    command: "pytest tests/integration/ -m 'integration' --cov-fail-under=70"
    timeout: 20

  - name: "ML Tests"
    command: "pytest ml/tests/ -m 'ml and not slow' --cov-fail-under=60"
    timeout: 30

  - name: "E2E Tests"
    command: "pytest tests/e2e/ -m 'e2e'"
    timeout: 15

  - name: "Performance Tests"
    command: "pytest -m 'performance' --durations=10"
    timeout: 60
```

### 3. Load Testing

```yaml
# k6 load testing
- name: Load testing
  run: |
    k6 run --vus 10 --duration 30s tests/load/api_load_test.js

    # Check response times
    k6 run --vus 50 --duration 2m tests/load/stress_test.js
```

---

## Performance Optimization

### 1. Docker Optimization

```dockerfile
# Use multi-stage builds
FROM python:3.12-slim as base
# ... build dependencies

FROM base as production
COPY --from=base /app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Use .dockerignore
node_modules
__pycache__
*.pyc
.git
tests/
docs/
```

### 2. CI/CD Optimization

```yaml
# Cache strategy
- name: Cache pip dependencies
  uses: actions/cache@v3
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements*.txt') }}

- name: Cache Docker layers
  uses: docker/build-push-action@v5
  with:
    cache-from: type=gha
    cache-to: type=gha,mode=max
```

### 3. Deployment Optimization

```yaml
# Parallel deployments
jobs:
  deploy-web:
    runs-on: ubuntu-latest
  deploy-worker:
    runs-on: ubuntu-latest
  deploy-ml:
    runs-on: ubuntu-latest
```

---

## Troubleshooting

### Common Issues

#### 1. CI Pipeline Failures

```bash
# Check GitHub Actions logs
# Look for:
# - Python version compatibility
# - Missing dependencies
# - Database connection issues
# - Test timeouts

# Local reproduction
make test-unit
make test-integration
```

#### 2. Docker Build Failures

```bash
# Check build logs
docker build --no-cache -f Dockerfile.web .

# Common issues:
# - Missing .dockerignore
# - Large context size
# - Build argument issues
```

#### 3. Deployment Failures

```bash
# Check container logs
docker-compose -f docker-compose.prod.yml logs web

# Check health endpoints
curl http://localhost:8000/api/health/

# Common issues:
# - Environment variable misconfiguration
# - Database migration failures
# - Port conflicts
```

#### 4. Performance Issues

```bash
# Check resource usage
docker stats

# Profile application
python -m cProfile manage.py runserver

# Database query optimization
python manage.py shell_plus --print-sql
```

### Debug Commands

```bash
# Full pipeline debug
make test-all
make docker-build
make docker-test

# Environment validation
python manage.py check --deploy
python manage.py showmigrations

# Network debugging
docker network ls
docker network inspect smarthr360_default

# Log aggregation
docker-compose -f docker-compose.prod.yml logs -f --tail=100
```

---

## Implementation Checklist

### Phase 1: Foundation (Week 1)

- [ ] Create GitHub Actions workflows directory
- [ ] Set up CI pipeline (ci.yml)
- [ ] Configure code quality checks
- [ ] Set up test automation
- [ ] Create GitHub repository secrets

### Phase 2: Build & Deploy (Week 2)

- [ ] Create build pipeline (build.yml)
- [ ] Set up container registry
- [ ] Configure staging deployment
- [ ] Test staging deployment
- [ ] Set up production deployment

### Phase 3: Security & Monitoring (Week 3)

- [ ] Implement security scanning
- [ ] Set up monitoring and alerting
- [ ] Configure health checks
- [ ] Implement rollback strategy
- [ ] Set up log aggregation

### Phase 4: Optimization (Week 4)

- [ ] Performance testing
- [ ] CI/CD pipeline optimization
- [ ] Documentation updates
- [ ] Team training
- [ ] Go-live preparation

---

## Next Steps

1. **Immediate Actions:**

   - Create `.github/workflows/` directory
   - Copy the CI pipeline configuration
   - Set up required GitHub secrets
   - Test CI pipeline on a feature branch

2. **Short-term Goals:**

   - Implement automated testing
   - Set up staging environment
   - Configure monitoring

3. **Long-term Vision:**
   - Blue-green deployments
   - Multi-region deployment
   - Advanced monitoring and alerting
   - Automated scaling

---

_This CI/CD implementation guide provides a comprehensive, production-ready pipeline for the SmartHR360 Future Skills platform. The modular approach allows for incremental implementation and easy maintenance._</content>
<parameter name="filePath">/Users/nawfalrazouk/smarthr360_m3_future_skills/CI_CD_IMPLEMENTATION_GUIDE.md
