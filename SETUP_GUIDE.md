# CI/CD Pipeline Setup Guide

This guide walks you through setting up the complete CI/CD pipeline for SmartHR360.

## Prerequisites

- GitHub account with admin access to the repository
- Kubernetes cluster (local or cloud)
- `kubectl` installed and configured
- `git` installed

---

## Step 1: Configure GitHub Secrets

### 1.1 Navigate to GitHub Secrets

1. Go to your repository: https://github.com/NawfalRAZOUK7/smarthr360_m3_future_skills
2. Click **Settings** (top menu)
3. In the left sidebar, click **Secrets and variables** → **Actions**
4. Click **New repository secret**

### 1.2 Add Required Secrets

Add each of these secrets one by one:

#### Cloud Provider Credentials (Choose based on your setup)

**Option A: Local Kubernetes (Docker Desktop, Minikube, Kind)**

```
CLOUD_PROVIDER: local
KUBE_CONFIG: <base64 encoded kubeconfig file>
```

To get your kubeconfig:

```bash
# Encode your kubeconfig
cat ~/.kube/config | base64 | pbcopy
# Paste the output as KUBE_CONFIG secret
```

**Option B: AWS EKS**

```
CLOUD_PROVIDER: aws
AWS_ACCESS_KEY_ID: <your-aws-access-key>
AWS_SECRET_ACCESS_KEY: <your-aws-secret-key>
AWS_REGION: us-east-1
EKS_CLUSTER_NAME: smarthr360-cluster
```

**Option C: GCP GKE**

```
CLOUD_PROVIDER: gcp
GCP_CREDENTIALS: <service-account-json>
GCP_PROJECT: your-project-id
GCP_ZONE: us-central1-a
GKE_CLUSTER_NAME: smarthr360-cluster
```

**Option D: Azure AKS**

```
CLOUD_PROVIDER: azure
AZURE_CREDENTIALS: <service-principal-json>
AZURE_RESOURCE_GROUP: smarthr360-rg
AKS_CLUSTER_NAME: smarthr360-cluster
```

#### Application Secrets

Generate secure secrets:

```bash
# Django SECRET_KEY
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'

# JWT SECRET_KEY
python -c 'import secrets; print(secrets.token_urlsafe(50))'

# Database passwords
python -c 'import secrets; print(secrets.token_urlsafe(32))'
```

Add these secrets:

```
DJANGO_SECRET_KEY: <generated-secret-key>
JWT_SECRET_KEY: <generated-jwt-secret>
STAGING_DB_PASSWORD: <generated-password>
STAGING_DB_USER: smarthr360_staging
STAGING_REDIS_PASSWORD: <generated-password>
PROD_DB_PASSWORD: <generated-password>
PROD_DB_USER: smarthr360_prod
PROD_REDIS_PASSWORD: <generated-password>
```

#### Optional Monitoring Secrets

```
ELASTIC_APM_SECRET_TOKEN: <your-elastic-token>
SENTRY_DSN: <your-sentry-dsn>
SLACK_WEBHOOK_URL: <your-slack-webhook>
CODECOV_TOKEN: <your-codecov-token>
```

### 1.3 Verify Secrets

After adding all secrets, you should see them listed (values will be hidden).

---

## Step 2: Install ArgoCD in Kubernetes

### 2.1 Install ArgoCD

```bash
# Create ArgoCD namespace
kubectl create namespace argocd

# Install ArgoCD
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Wait for ArgoCD to be ready (takes 2-3 minutes)
kubectl wait --for=condition=ready pod -n argocd -l app.kubernetes.io/name=argocd-server --timeout=300s
```

### 2.2 Access ArgoCD UI

#### Option A: Port Forward (Recommended for local/testing)

```bash
# Forward ArgoCD server to localhost
kubectl port-forward svc/argocd-server -n argocd 8080:443

# Access UI at: https://localhost:8080
# (Accept the self-signed certificate warning)
```

#### Option B: Load Balancer (For production)

```bash
# Patch service to LoadBalancer
kubectl patch svc argocd-server -n argocd -p '{"spec": {"type": "LoadBalancer"}}'

# Get external IP
kubectl get svc argocd-server -n argocd
```

### 2.3 Get Initial Admin Password

```bash
# Get the initial password
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d && echo
```

**Login credentials:**

- Username: `admin`
- Password: <output from above command>

### 2.4 Install ArgoCD CLI (Optional but recommended)

**macOS:**

```bash
brew install argocd
```

**Linux:**

```bash
curl -sSL -o argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
chmod +x argocd
sudo mv argocd /usr/local/bin/
```

**Login with CLI:**

```bash
# If using port-forward
argocd login localhost:8080 --username admin --password <your-password> --insecure

# Change password
argocd account update-password
```

### 2.5 Install ArgoCD Notifications (Optional)

```bash
# Install notifications controller
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj-labs/argocd-notifications/stable/manifests/install.yaml

# Configure Slack notifications (if you have webhook)
kubectl create secret generic argocd-notifications-secret -n argocd \
  --from-literal=slack-token=<your-slack-webhook-url>
```

---

## Step 3: Update Repository Configuration

The repository URLs and container registry paths need to be updated to match your actual repository.

**Current placeholders:**

- `your-org` → `nawfalrazouk7` (your GitHub username in lowercase)
- Repository: `smarthr360_m3_future_skills`
- Domains: Will use staging/production URLs you set up

### 3.1 Update All Configuration Files

I'll update all the placeholder values automatically in the next step.

---

## Step 4: Deploy ArgoCD Applications

### 4.1 Apply ArgoCD Project (Production controls)

```bash
# Apply production project with RBAC
kubectl apply -f argocd/project-production.yaml

# Verify
kubectl get appproject -n argocd
```

### 4.2 Deploy Applications

```bash
# Deploy dev environment (auto-syncs from develop branch)
kubectl apply -f argocd/application-dev.yaml

# Deploy staging environment (auto-syncs from develop)
kubectl apply -f argocd/application-staging.yaml

# Deploy production environment (manual sync only)
kubectl apply -f argocd/application-production.yaml

# Verify all applications
kubectl get applications -n argocd
```

### 4.3 Check Application Status

**Using kubectl:**

```bash
kubectl get applications -n argocd
kubectl describe application smarthr360-dev -n argocd
```

**Using ArgoCD CLI:**

```bash
argocd app list
argocd app get smarthr360-dev
```

**Using UI:**

- Navigate to https://localhost:8080
- You should see 3 applications: smarthr360-dev, smarthr360-staging, smarthr360-production

### 4.4 Initial Sync (First Time)

Since this is the first deployment, you need to sync manually:

```bash
# Sync dev environment
argocd app sync smarthr360-dev

# Sync staging environment
argocd app sync smarthr360-staging

# Production requires manual approval - sync when ready
# argocd app sync smarthr360-production
```

Or use the UI:

1. Click on an application
2. Click **SYNC** button
3. Click **SYNCHRONIZE**

---

## Step 5: Test the CI/CD Pipeline

### 5.1 Test CI Pipeline (Automated Tests)

```bash
# Create a test branch
git checkout -b feature/test-ci-pipeline

# Make a small change
echo "# CI/CD Test" >> README.md
git add README.md
git commit -m "test: Verify CI pipeline"
git push origin feature/test-ci-pipeline

# Create a Pull Request to develop branch
# GitHub Actions will automatically run:
# - Linting (flake8, black, isort)
# - Security scanning (bandit, safety)
# - Unit tests with coverage
# - Integration tests
# - Docker image builds
# - Container security scanning (Trivy)
```

**Check progress:**

- Go to: https://github.com/NawfalRAZOUK7/smarthr360_m3_future_skills/actions
- You should see the "CI - Test and Build" workflow running

### 5.2 Test CD Staging Pipeline

```bash
# Merge PR to develop branch (or push directly)
git checkout develop
git merge feature/test-ci-pipeline
git push origin develop

# This will trigger:
# 1. CI pipeline (tests + build)
# 2. CD Staging deployment workflow
# 3. ArgoCD will auto-sync the changes
```

**Monitor deployment:**

```bash
# Watch staging pods
kubectl get pods -n smarthr360-staging -w

# Check deployment status
kubectl rollout status deployment/smarthr360-api-staging -n smarthr360-staging

# Check ArgoCD sync status
argocd app get smarthr360-staging

# View logs
kubectl logs -f -n smarthr360-staging -l component=api
```

### 5.3 Test CD Production Pipeline

```bash
# Create a release tag (triggers production deployment)
git checkout main
git merge develop
git tag v1.0.0
git push origin main --tags

# This will trigger:
# 1. Pre-deployment validation
# 2. Backup creation
# 3. Production deployment (requires manual approval in GitHub)
# 4. Post-deployment monitoring
```

**Approve and monitor:**

1. Go to GitHub Actions: https://github.com/NawfalRAZOUK7/smarthr360_m3_future_skills/actions
2. Click on the "CD - Deploy to Production" workflow
3. Click **Review deployments** button
4. Check "production" and click **Approve and deploy**

```bash
# Monitor production deployment
kubectl get pods -n smarthr360 -w

# For production, ArgoCD requires manual sync
argocd app sync smarthr360-production

# Verify deployment
kubectl get all -n smarthr360
```

### 5.4 Test Deployment Strategies

#### Test Blue-Green Deployment

```bash
# SSH to a machine with kubectl access to your cluster
# Or run locally if kubectl is configured

# Run blue-green deployment
./scripts/blue-green-deploy.sh v1.0.1

# The script will:
# 1. Create new deployment (green)
# 2. Run smoke tests
# 3. Prompt for traffic switch
# 4. Switch service selector
# 5. Monitor for 2 minutes
# 6. Option to cleanup old deployment
```

#### Test Canary Deployment

```bash
# Standard canary (5% → 10% → 25% → 50% → 100%)
./scripts/canary-deploy.sh v1.0.2

# Custom canary steps
CANARY_STEPS="10,50,100" STEP_DURATION="10m" \
  ./scripts/canary-deploy.sh v1.0.2

# The script will:
# 1. Create canary deployment
# 2. Gradually increase traffic
# 3. Monitor health at each step
# 4. Prompt for continuation
# 5. Automatic rollback if health fails
```

#### Test Rollback

```bash
# Simulate a bad deployment
git tag v1.0.3-bad
git push origin v1.0.3-bad

# Wait for deployment (or cancel it)

# Rollback using script
./scripts/rollback.sh all

# Or rollback specific component
./scripts/rollback.sh api

# Or manual rollback
kubectl rollout undo deployment/smarthr360-api -n smarthr360
```

---

## Step 6: Verify Everything Works

### 6.1 Check All Pods Running

```bash
# Dev environment
kubectl get pods -n smarthr360-dev

# Staging environment
kubectl get pods -n smarthr360-staging

# Production environment
kubectl get pods -n smarthr360
```

All pods should be in `Running` status.

### 6.2 Test API Endpoints

**Port-forward to test:**

```bash
# Forward API service
kubectl port-forward -n smarthr360-staging svc/smarthr360-api-staging 8000:8000

# Test health endpoint
curl http://localhost:8000/api/health/

# Test skills endpoint
curl http://localhost:8000/api/skills/
```

### 6.3 Check ArgoCD Sync Status

```bash
argocd app list

# All apps should show:
# - HEALTH: Healthy
# - SYNC: Synced
```

### 6.4 Review Logs

```bash
# API logs
kubectl logs -f -n smarthr360-staging -l component=api --tail=100

# Worker logs
kubectl logs -f -n smarthr360-staging -l component=celery-worker --tail=100

# Check for errors
kubectl logs -n smarthr360-staging -l component=api --tail=100 | grep -i error
```

---

## Common Issues and Solutions

### Issue 1: ImagePullBackOff

**Symptoms:** Pods stuck in `ImagePullBackOff` status

**Solution:**

```bash
# Check if images exist in registry
docker pull ghcr.io/nawfalrazouk7/smarthr360-api:develop

# Verify registry secret
kubectl get secret ghcr-secret -n smarthr360-staging

# Create/update registry secret
kubectl create secret docker-registry ghcr-secret \
  --docker-server=ghcr.io \
  --docker-username=<your-github-username> \
  --docker-password=<your-github-token> \
  --docker-email=<your-email> \
  -n smarthr360-staging --dry-run=client -o yaml | kubectl apply -f -
```

### Issue 2: ArgoCD OutOfSync

**Symptoms:** ArgoCD shows "OutOfSync" status

**Solution:**

```bash
# Check differences
argocd app diff smarthr360-dev

# Force sync
argocd app sync smarthr360-dev --force

# Or delete and recreate
argocd app delete smarthr360-dev
kubectl apply -f argocd/application-dev.yaml
```

### Issue 3: Database Connection Failed

**Symptoms:** API pods crash with database connection errors

**Solution:**

```bash
# Check database pod
kubectl get pods -n smarthr360-staging -l component=postgres

# Check database logs
kubectl logs -n smarthr360-staging -l component=postgres --tail=50

# Verify database secret
kubectl get secret smarthr360-secrets-staging -n smarthr360-staging -o yaml

# Run migrations manually
kubectl exec -it -n smarthr360-staging deployment/smarthr360-api-staging -- python manage.py migrate
```

### Issue 4: GitHub Actions Failing

**Symptoms:** CI/CD workflows fail

**Solution:**

```bash
# Check workflow file syntax
cat .github/workflows/ci.yml | python -m json.tool 2>&1 | head

# Verify secrets are set
# Go to: Settings → Secrets and variables → Actions

# Check workflow logs in GitHub UI
# Actions tab → Click on failed workflow → Click on failed job
```

---

## Next Steps After Setup

1. **Set up monitoring:**

   - Configure Prometheus & Grafana
   - Set up log aggregation (Loki/ELK)
   - Configure alerts

2. **Configure custom domains:**

   - Update ingress with your actual domains
   - Set up DNS records
   - Configure SSL certificates (Let's Encrypt)

3. **Set up backup automation:**

   - Schedule database backups
   - Configure backup retention
   - Test restore procedures

4. **Team onboarding:**

   - Share access credentials
   - Document deployment procedures
   - Set up on-call rotation

5. **Performance tuning:**
   - Adjust resource limits based on actual usage
   - Configure HPA thresholds
   - Optimize database queries

---

## Support

- **Documentation:** See `docs/CI_CD_GUIDE.md` for detailed information
- **Quick Reference:** See `docs/CI_CD_QUICK_REFERENCE.md` for common commands
- **Issues:** Open an issue in the GitHub repository
- **Emergency:** Follow procedures in `docs/CI_CD_QUICK_REFERENCE.md`

---

## Summary Checklist

- [ ] GitHub secrets configured
- [ ] ArgoCD installed and accessible
- [ ] Repository URLs updated
- [ ] ArgoCD applications deployed
- [ ] Dev environment synced
- [ ] Staging environment synced
- [ ] CI pipeline tested
- [ ] CD staging pipeline tested
- [ ] CD production pipeline tested
- [ ] All pods running
- [ ] API endpoints responding
- [ ] Deployment scripts tested

**Once all items are checked, your CI/CD pipeline is fully operational! 🎉**
