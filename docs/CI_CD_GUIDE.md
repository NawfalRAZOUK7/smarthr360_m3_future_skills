# SmartHR360 CI/CD Pipeline Documentation

## Overview

This document describes the complete CI/CD pipeline for SmartHR360, including automated testing, building, deployment strategies, and GitOps workflows using GitHub Actions and ArgoCD.

## Table of Contents

1. [Pipeline Architecture](#pipeline-architecture)
2. [GitHub Actions Workflows](#github-actions-workflows)
3. [GitOps with ArgoCD](#gitops-with-argocd)
4. [Deployment Strategies](#deployment-strategies)
5. [Environment Management](#environment-management)
6. [Security & Secrets](#security--secrets)
7. [Monitoring & Rollback](#monitoring--rollback)
8. [Troubleshooting](#troubleshooting)

---

## Pipeline Architecture

### Flow Diagram

```
┌─────────────┐
│   Code      │
│   Push      │
└──────┬──────┘
       │
       v
┌─────────────────────────────────────────────────┐
│  CI Pipeline (GitHub Actions)                   │
│  - Lint & Format Check                          │
│  - Security Scan                                │
│  - Unit Tests                                   │
│  - Integration Tests                            │
│  - Build Docker Images                          │
│  - Push to Registry                             │
└──────┬──────────────────────────────────────────┘
       │
       v
┌─────────────────────────────────────────────────┐
│  Environment Deployment                          │
│                                                  │
│  ┌─────────┐  ┌──────────┐  ┌──────────────┐  │
│  │   Dev   │  │ Staging  │  │ Production   │  │
│  │  Auto   │  │   Auto   │  │   Manual     │  │
│  └─────────┘  └──────────┘  └──────────────┘  │
└──────┬──────────────────────────────────────────┘
       │
       v
┌─────────────────────────────────────────────────┐
│  GitOps (ArgoCD)                                 │
│  - Monitors Git Repository                       │
│  - Syncs Kubernetes Manifests                    │
│  - Manages Deployments                           │
└──────┬──────────────────────────────────────────┘
       │
       v
┌─────────────────────────────────────────────────┐
│  Kubernetes Cluster                              │
│  - Rolling Updates                               │
│  - Blue-Green Deployments                        │
│  - Canary Releases                               │
└──────────────────────────────────────────────────┘
```

---

## GitHub Actions Workflows

### 1. CI Workflow (`.github/workflows/ci.yml`)

**Triggers:**

- Push to `main`, `develop`, `feature/**`
- Pull requests to `main`, `develop`
- Manual dispatch

**Jobs:**

#### lint-and-test

```yaml
- Checkout code
- Set up Python 3.11
- Install dependencies
- Run linting (flake8, black, isort)
- Run security checks (bandit, safety)
- Run tests with coverage
- Upload coverage to Codecov
```

#### build-docker

```yaml
- Build Docker images (API, Celery, Nginx)
- Tag with branch name and SHA
- Push to GitHub Container Registry
- Run Trivy security scan
- Upload scan results
```

#### integration-tests

```yaml
- Start services with docker-compose
- Run integration tests
- Verify API health
```

**Required Secrets:**

- `GITHUB_TOKEN` (automatically provided)
- `CODECOV_TOKEN` (optional)
- `SLACK_WEBHOOK_URL` (optional)

### 2. CD Staging Workflow (`.github/workflows/cd-staging.yml`)

**Triggers:**

- Push to `develop` branch
- Manual dispatch

**Steps:**

1. Configure cloud provider credentials (AWS/GCP/Azure)
2. Update kubeconfig
3. Create/update Kubernetes secrets
4. Update image tags in manifests using kustomize
5. Deploy to staging namespace
6. Run database migrations
7. Verify deployment
8. Run smoke tests
9. Rollback on failure

**Required Secrets:**

```yaml
# Cloud Provider (choose one)
CLOUD_PROVIDER: aws|gcp|azure

# AWS
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
AWS_REGION
EKS_CLUSTER_NAME

# GCP
GCP_CREDENTIALS
GCP_PROJECT
GCP_ZONE
GKE_CLUSTER_NAME

# Azure
AZURE_CREDENTIALS
AZURE_RESOURCE_GROUP
AKS_CLUSTER_NAME

# Application
DJANGO_SECRET_KEY
JWT_SECRET_KEY
STAGING_DB_PASSWORD
STAGING_DB_USER
STAGING_REDIS_PASSWORD
ELASTIC_APM_SECRET_TOKEN
SENTRY_DSN
```

### 3. CD Production Workflow (`.github/workflows/cd-production.yml`)

**Triggers:**

- Git tags matching `v*.*.*` (e.g., v1.0.0)
- Manual dispatch with version selection

**Deployment Strategies:**

- **Rolling Update** (default): Gradual replacement of pods
- **Blue-Green**: Deploy alongside current, then switch traffic
- **Canary**: Gradually increase traffic to new version

**Steps:**

1. Pre-deployment validation
   - Validate tag format
   - Check staging health
   - Run security scan
   - Check for breaking changes
2. Create backup (database + manifests)
3. Deploy using selected strategy
4. Run database migrations
5. Verify deployment
6. Run smoke tests
7. Monitor for 5 minutes
8. Rollback on failure
9. Send notifications

**Required Secrets:**

```yaml
# Same as staging, plus:
PROD_DB_PASSWORD
PROD_DB_USER
PROD_REDIS_PASSWORD
```

---

## GitOps with ArgoCD

### Architecture

ArgoCD continuously monitors the Git repository and automatically syncs changes to Kubernetes clusters. This ensures that the cluster state always matches the desired state in Git.

### ArgoCD Applications

#### 1. Development (`argocd/application-dev.yaml`)

```yaml
Source: develop branch
Path: k8s/overlays/dev
Target: smarthr360-dev namespace
Sync Policy: Automated (prune + self-heal)
```

#### 2. Staging (`argocd/application-staging.yaml`)

```yaml
Source: staging branch
Path: k8s/overlays/staging
Target: smarthr360-staging namespace
Sync Policy: Automated (prune + self-heal)
Notifications: Slack on sync success/failure
```

#### 3. Production (`argocd/application-production.yaml`)

```yaml
Source: main branch
Path: k8s/overlays/production
Target: smarthr360 namespace
Sync Policy: Manual (requires approval)
Project: production (with RBAC)
Notifications: Slack alerts
```

### ArgoCD Project for Production

The production AppProject (`argocd/project-production.yaml`) includes:

- **Source repositories**: Whitelisted Git repos
- **Destinations**: Allowed namespaces and clusters
- **Resource whitelists/blacklists**: Control what can be deployed
- **Sync windows**: Define maintenance windows
  - Allow: 2 AM - 4 AM (maintenance window)
  - Deny: 8 AM - 6 PM weekdays (business hours)
- **RBAC roles**:
  - **admin**: Full access
  - **deployer**: Can sync and view
  - **readonly**: View only

### Setting Up ArgoCD

#### Install ArgoCD

```bash
# Create namespace
kubectl create namespace argocd

# Install ArgoCD
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Access ArgoCD UI
kubectl port-forward svc/argocd-server -n argocd 8080:443

# Get admin password
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
```

#### Deploy Applications

```bash
# Create production project
kubectl apply -f argocd/project-production.yaml

# Deploy applications
kubectl apply -f argocd/application-dev.yaml
kubectl apply -f argocd/application-staging.yaml
kubectl apply -f argocd/application-production.yaml

# Verify
argocd app list
```

#### Configure Notifications

```bash
# Install ArgoCD Notifications
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj-labs/argocd-notifications/stable/manifests/install.yaml

# Configure Slack webhook
kubectl create secret generic argocd-notifications-secret \
  -n argocd \
  --from-literal=slack-token=$SLACK_WEBHOOK_URL
```

---

## Deployment Strategies

### 1. Rolling Update (Default)

**When to use:** Regular updates, low risk changes

**How it works:**

- Gradually replaces old pods with new ones
- Maintains availability during update
- Automatic rollback on failure

**Usage:**

```bash
# Automatic via GitHub Actions
git tag v1.2.0
git push origin v1.2.0

# Manual
kubectl set image deployment/smarthr360-api \
  api=ghcr.io/your-org/smarthr360-api:v1.2.0 \
  -n smarthr360
```

**Configuration:**

```yaml
spec:
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1 # Max pods above desired count
      maxUnavailable: 0 # Max pods that can be unavailable
```

### 2. Blue-Green Deployment

**When to use:** Zero-downtime deployments, need for quick rollback

**How it works:**

- Deploy new version alongside current (green beside blue)
- Test green deployment
- Switch traffic from blue to green
- Keep blue for rollback

**Usage:**

```bash
# Using script
./scripts/blue-green-deploy.sh v1.2.0

# The script will:
# 1. Create green deployment
# 2. Wait for readiness
# 3. Run smoke tests
# 4. Prompt for traffic switch
# 5. Switch service selector
# 6. Monitor new deployment
# 7. Option to cleanup old deployment
```

**Quick Rollback:**

```bash
# Switch back to blue
kubectl patch service smarthr360-api -n smarthr360 \
  -p '{"spec":{"selector":{"color":"blue"}}}'
```

### 3. Canary Deployment

**When to use:** High-risk changes, gradual rollout needed

**How it works:**

- Deploy new version with small percentage of traffic (5%)
- Monitor metrics (errors, latency, etc.)
- Gradually increase traffic (10% → 25% → 50% → 100%)
- Rollback if issues detected

**Usage:**

```bash
# Using script with defaults (5%, 10%, 25%, 50%, 100%)
./scripts/canary-deploy.sh v1.2.0

# Custom canary steps
CANARY_STEPS="10,20,50,100" \
STEP_DURATION="10m" \
./scripts/canary-deploy.sh v1.2.0

# The script will:
# 1. Create canary deployment
# 2. Gradually increase replicas
# 3. Monitor health at each step
# 4. Prompt for confirmation
# 5. Rollback on failure
```

**Manual Rollback:**

```bash
# During canary
kubectl scale deployment smarthr360-api-canary -n smarthr360 --replicas=0
kubectl scale deployment smarthr360-api -n smarthr360 --replicas=3
```

---

## Environment Management

### Kustomize Structure

```
k8s/
├── base/                      # Base Kubernetes manifests
│   ├── kustomization.yaml
│   └── (all base manifests)
└── overlays/
    ├── dev/                   # Development environment
    │   ├── kustomization.yaml
    │   └── ingress-patch.yaml
    ├── staging/               # Staging environment
    │   ├── kustomization.yaml
    │   └── ingress-patch.yaml
    └── production/            # Production environment
        ├── kustomization.yaml
        └── ingress-patch.yaml
```

### Environment Differences

| Feature               | Dev     | Staging | Production |
| --------------------- | ------- | ------- | ---------- |
| **Replicas (API)**    | 1       | 2       | 3          |
| **Replicas (Worker)** | 1       | 2       | 3          |
| **HPA Min**           | 1       | 2       | 3          |
| **HPA Max**           | 3       | 5       | 10         |
| **CPU Request**       | 250m    | 500m    | 500m       |
| **CPU Limit**         | 500m    | 1000m   | 1000m      |
| **Memory Request**    | 512Mi   | 1Gi     | 1Gi        |
| **Memory Limit**      | 1Gi     | 2Gi     | 2Gi        |
| **PostgreSQL PVC**    | 10Gi    | 50Gi    | 100Gi      |
| **Media PVC**         | 10Gi    | 25Gi    | 50Gi       |
| **ML Models PVC**     | 5Gi     | 20Gi    | 20Gi       |
| **Debug Mode**        | true    | false   | false      |
| **Log Level**         | DEBUG   | INFO    | WARNING    |
| **SSL Issuer**        | staging | prod    | prod       |

### Building Manifests

```bash
# Preview dev manifests
kubectl kustomize k8s/overlays/dev

# Preview staging manifests
kubectl kustomize k8s/overlays/staging

# Preview production manifests
kubectl kustomize k8s/overlays/production

# Apply directly
kubectl apply -k k8s/overlays/dev
kubectl apply -k k8s/overlays/staging
kubectl apply -k k8s/overlays/production
```

---

## Security & Secrets

### Secrets Management

#### GitHub Secrets

Store sensitive data in GitHub repository secrets:

```bash
# Navigate to: Settings → Secrets and variables → Actions

# Add secrets:
- DJANGO_SECRET_KEY
- JWT_SECRET_KEY
- STAGING_DB_PASSWORD
- PROD_DB_PASSWORD
- AWS_ACCESS_KEY_ID
- SLACK_WEBHOOK_URL
# ... etc
```

#### Kubernetes Secrets

Created automatically by CI/CD pipeline:

```yaml
# Example: API secrets
apiVersion: v1
kind: Secret
metadata:
  name: smarthr360-secrets
  namespace: smarthr360
type: Opaque
data:
  SECRET_KEY: <base64-encoded>
  JWT_SECRET_KEY: <base64-encoded>
  DB_PASSWORD: <base64-encoded>
  # ...
```

#### External Secrets (Recommended for Production)

Use external secret managers for production:

**AWS Secrets Manager:**

```bash
# Install External Secrets Operator
helm install external-secrets \
  external-secrets/external-secrets \
  -n external-secrets-system \
  --create-namespace

# Create SecretStore
kubectl apply -f - <<EOF
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: aws-secrets-manager
  namespace: smarthr360
spec:
  provider:
    aws:
      service: SecretsManager
      region: us-east-1
      auth:
        secretRef:
          accessKeyIDSecretRef:
            name: aws-credentials
            key: access-key-id
          secretAccessKeySecretRef:
            name: aws-credentials
            key: secret-access-key
EOF

# Create ExternalSecret
kubectl apply -f - <<EOF
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: smarthr360-secrets
  namespace: smarthr360
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: SecretStore
  target:
    name: smarthr360-secrets
    creationPolicy: Owner
  data:
    - secretKey: SECRET_KEY
      remoteRef:
        key: smarthr360/production
        property: secret_key
EOF
```

### Image Security

#### Trivy Scanning

Automated in CI pipeline:

```yaml
- name: Run Trivy security scan
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: ghcr.io/${{ github.repository }}-api:${{ github.sha }}
    format: "sarif"
    output: "trivy-results.sarif"
```

#### Registry Authentication

```bash
# Create Docker registry secret
kubectl create secret docker-registry ghcr-secret \
  --docker-server=ghcr.io \
  --docker-username=$GITHUB_ACTOR \
  --docker-password=$GITHUB_TOKEN \
  --namespace=smarthr360

# Add to ServiceAccount
kubectl patch serviceaccount smarthr360-sa -n smarthr360 \
  -p '{"imagePullSecrets": [{"name": "ghcr-secret"}]}'
```

---

## Monitoring & Rollback

### Health Checks

#### Kubernetes Probes

```yaml
livenessProbe:
  httpGet:
    path: /api/health/alive/
    port: 8000
  initialDelaySeconds: 60
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /api/health/ready/
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 5
```

#### Manual Health Check

```bash
# Port forward
kubectl port-forward -n smarthr360 svc/smarthr360-api 8000:8000

# Test endpoints
curl http://localhost:8000/api/health/
curl http://localhost:8000/api/skills/
```

### Monitoring Deployment

```bash
# Watch rollout
kubectl rollout status deployment/smarthr360-api -n smarthr360 -w

# Watch pods
kubectl get pods -n smarthr360 -w

# Check logs
kubectl logs -f -n smarthr360 -l component=api

# Check events
kubectl get events -n smarthr360 --sort-by='.lastTimestamp'

# Resource usage
kubectl top pods -n smarthr360
kubectl top nodes
```

### Automated Rollback

#### Using Script

```bash
# Rollback all components
./scripts/rollback.sh all

# Rollback specific component
./scripts/rollback.sh api
./scripts/rollback.sh celery-worker
./scripts/rollback.sh celery-beat
```

#### Manual Rollback

```bash
# Rollback to previous revision
kubectl rollout undo deployment/smarthr360-api -n smarthr360

# Rollback to specific revision
kubectl rollout undo deployment/smarthr360-api -n smarthr360 --to-revision=5

# Check rollout history
kubectl rollout history deployment/smarthr360-api -n smarthr360

# Check specific revision
kubectl rollout history deployment/smarthr360-api -n smarthr360 --revision=5
```

### ArgoCD Rollback

```bash
# Rollback via ArgoCD CLI
argocd app rollback smarthr360-production

# Rollback to specific revision
argocd app rollback smarthr360-production 5

# Rollback via UI
# Navigate to: Applications → smarthr360-production → History → Rollback
```

---

## Troubleshooting

### Common Issues

#### 1. CI Pipeline Failures

**Tests failing:**

```bash
# Run tests locally
pytest --cov=future_skills -v

# Check test database
docker-compose up -d postgres redis
export DB_HOST=localhost
pytest
```

**Docker build failing:**

```bash
# Build locally
docker build -t test:latest .

# Check build logs
docker build --progress=plain -t test:latest .

# Test container
docker run -it test:latest sh
```

#### 2. Deployment Failures

**ImagePullBackOff:**

```bash
# Check image exists
docker pull ghcr.io/your-org/smarthr360-api:v1.0.0

# Verify registry secret
kubectl get secret ghcr-secret -n smarthr360 -o yaml

# Check ServiceAccount
kubectl get serviceaccount smarthr360-sa -n smarthr360 -o yaml
```

**CrashLoopBackOff:**

```bash
# Check logs
kubectl logs -n smarthr360 <pod-name>

# Check previous logs
kubectl logs -n smarthr360 <pod-name> --previous

# Describe pod
kubectl describe pod -n smarthr360 <pod-name>

# Check environment variables
kubectl exec -n smarthr360 <pod-name> -- env
```

**Database Connection Issues:**

```bash
# Test database connectivity
kubectl exec -n smarthr360 <api-pod> -- nc -zv postgres 5432

# Check database pod
kubectl logs -n smarthr360 -l app=postgres

# Verify secrets
kubectl get secret smarthr360-secrets -n smarthr360 -o yaml | grep DB_PASSWORD | awk '{print $2}' | base64 -d
```

#### 3. ArgoCD Issues

**App OutOfSync:**

```bash
# Check differences
argocd app diff smarthr360-production

# Force sync
argocd app sync smarthr360-production --force

# Refresh app
argocd app refresh smarthr360-production
```

**Sync Hooks Failing:**

```bash
# Check hook logs
kubectl logs -n smarthr360 -l app.kubernetes.io/instance=smarthr360

# Delete failed hook
kubectl delete job <hook-job-name> -n smarthr360
```

### Emergency Procedures

#### Complete Service Outage

```bash
# 1. Check all pods
kubectl get pods -n smarthr360

# 2. Check ingress
kubectl get ingress -n smarthr360
kubectl describe ingress smarthr360-ingress -n smarthr360

# 3. Check external services
kubectl get svc -n smarthr360

# 4. Rollback immediately
./scripts/rollback.sh all

# 5. Scale up if needed
kubectl scale deployment smarthr360-api -n smarthr360 --replicas=5
```

#### Database Issues

```bash
# 1. Check database pod
kubectl get pod -n smarthr360 -l app=postgres

# 2. Access database
kubectl exec -it -n smarthr360 <postgres-pod> -- psql -U smarthr360_user smarthr360

# 3. Check connections
SELECT * FROM pg_stat_activity;

# 4. Restore from backup if needed
kubectl exec -n smarthr360 <postgres-pod> -- pg_restore -U smarthr360_user -d smarthr360 < backup.sql
```

---

## Best Practices

### 1. **Trunk-Based Development**

- Keep feature branches short-lived
- Merge to `develop` frequently
- Use feature flags for incomplete features

### 2. **Semantic Versioning**

- Format: `v{major}.{minor}.{patch}`
- Increment major for breaking changes
- Increment minor for new features
- Increment patch for bug fixes

### 3. **GitOps Principles**

- Git is the single source of truth
- Declarative configuration
- Automated synchronization
- Version control everything

### 4. **Testing Strategy**

- Unit tests: 80%+ coverage
- Integration tests: Critical paths
- End-to-end tests: User workflows
- Load testing: Before major releases

### 5. **Deployment Safety**

- Always test in staging first
- Use canary for high-risk changes
- Monitor metrics during rollout
- Have rollback plan ready

### 6. **Security**

- Scan images for vulnerabilities
- Rotate secrets regularly
- Use RBAC for access control
- Enable audit logging

---

## References

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [ArgoCD Documentation](https://argo-cd.readthedocs.io/)
- [Kustomize Documentation](https://kustomize.io/)
- [Kubernetes Best Practices](https://kubernetes.io/docs/concepts/configuration/overview/)
- [12-Factor App Methodology](https://12factor.net/)

---

## Support

For issues or questions:

- **CI/CD Issues**: Check GitHub Actions logs
- **Deployment Issues**: Check ArgoCD UI and Kubernetes events
- **Production Incidents**: Follow emergency procedures above
- **General Support**: Contact DevOps team

---

**Last Updated:** November 2025
**Maintained by:** DevOps Team
