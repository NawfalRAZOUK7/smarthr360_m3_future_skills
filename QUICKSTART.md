# 🚀 Quick Start - CI/CD Pipeline Setup

## Prerequisites Check

```bash
# Verify you have these installed
kubectl version
git --version
```

## 5-Minute Setup

### 1️⃣ Install ArgoCD (2 minutes)

```bash
./scripts/install-argocd.sh
```

**What it does:**

- Installs ArgoCD in your Kubernetes cluster
- Sets up port-forwarding to access UI
- Provides admin credentials
- Optionally installs ArgoCD CLI

**Access ArgoCD UI:** https://localhost:8080  
**Username:** `admin`  
**Password:** (shown in script output)

---

### 2️⃣ Deploy Applications (1 minute)

```bash
./scripts/deploy-argocd-apps.sh
```

**What it does:**

- Deploys production AppProject with RBAC
- Creates 3 ArgoCD applications (dev/staging/production)
- Optionally performs initial sync

---

### 3️⃣ Configure GitHub Secrets (2 minutes)

Go to: https://github.com/NawfalRAZOUK7/smarthr360_m3_future_skills/settings/secrets/actions

**Click "New repository secret" and add:**

#### For Local Kubernetes (Docker Desktop/Minikube):

```bash
# Get your kubeconfig
cat ~/.kube/config | base64 | pbcopy
```

Then add:

- `CLOUD_PROVIDER` = `local`
- `KUBE_CONFIG` = (paste the base64 output)

#### Generate Application Secrets:

```bash
# Django secret key
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'

# JWT secret
python -c 'import secrets; print(secrets.token_urlsafe(50))'

# Passwords
python -c 'import secrets; print(secrets.token_urlsafe(32))'
```

Add these secrets:

- `DJANGO_SECRET_KEY` = (generated above)
- `JWT_SECRET_KEY` = (generated above)
- `STAGING_DB_PASSWORD` = (generated above)
- `PROD_DB_PASSWORD` = (generated above)

---

### 4️⃣ Verify Setup

```bash
./scripts/verify-pipeline.sh
```

**What it checks:**

- ArgoCD installation
- Application deployment
- Pod status
- Secrets configuration
- Workflow files

---

## Test the Pipeline

### Test CI (Automated Tests)

```bash
# Create test branch
git checkout -b feature/test-pipeline
echo "# Test" >> README.md
git add . && git commit -m "test: CI pipeline"
git push origin feature/test-pipeline

# Create PR to develop
# Watch: https://github.com/NawfalRAZOUK7/smarthr360_m3_future_skills/actions
```

### Test CD Staging (Automated Deployment)

```bash
# Merge to develop
git checkout develop
git merge feature/test-pipeline
git push origin develop

# Monitor deployment
kubectl get pods -n smarthr360-staging -w
```

### Test CD Production (Manual Approval)

```bash
# Create release tag
git checkout main
git merge develop
git tag v1.0.0
git push origin main --tags

# Approve in GitHub Actions:
# https://github.com/NawfalRAZOUK7/smarthr360_m3_future_skills/actions
```

---

## Essential Commands

### ArgoCD UI

```bash
# Start port-forward
kubectl port-forward svc/argocd-server -n argocd 8080:443

# Access: https://localhost:8080
```

### Monitor Applications

```bash
# List all applications
kubectl get applications -n argocd

# Get application details
kubectl describe application smarthr360-dev -n argocd

# Sync application manually
kubectl patch application smarthr360-dev -n argocd \
  --type merge -p '{"operation":{"sync":{}}}'
```

### Check Pods

```bash
# Dev
kubectl get pods -n smarthr360-dev

# Staging
kubectl get pods -n smarthr360-staging

# Production
kubectl get pods -n smarthr360
```

### View Logs

```bash
# API logs
kubectl logs -f -n smarthr360-staging -l component=api

# Worker logs
kubectl logs -f -n smarthr360-staging -l component=celery-worker
```

### Deployment Strategies

```bash
# Blue-Green (zero downtime)
./scripts/blue-green-deploy.sh v1.0.1

# Canary (gradual rollout)
./scripts/canary-deploy.sh v1.0.1

# Rollback
./scripts/rollback.sh all
```

---

## Troubleshooting

### ArgoCD Not Accessible

```bash
# Check pods
kubectl get pods -n argocd

# Restart port-forward
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

### Application OutOfSync

```bash
# Force sync
kubectl patch application smarthr360-dev -n argocd \
  --type merge -p '{"operation":{"sync":{"syncOptions":["Force=true"]}}}'
```

### Pods Not Starting

```bash
# Check pod status
kubectl describe pod -n smarthr360-staging <pod-name>

# Check logs
kubectl logs -n smarthr360-staging <pod-name>

# Common issues:
# - ImagePullBackOff: Check registry credentials
# - CrashLoopBackOff: Check application logs
# - Pending: Check resource availability
```

### Reset Everything

```bash
# Delete ArgoCD
kubectl delete namespace argocd

# Delete applications
kubectl delete namespace smarthr360-dev
kubectl delete namespace smarthr360-staging
kubectl delete namespace smarthr360

# Reinstall
./scripts/install-argocd.sh
./scripts/deploy-argocd-apps.sh
```

---

## What's Configured

✅ **CI Pipeline** - Automated testing, building, security scanning  
✅ **CD Staging** - Auto-deploy from develop branch  
✅ **CD Production** - Manual approval, tag-triggered  
✅ **GitOps** - ArgoCD manages Kubernetes deployments  
✅ **3 Environments** - Dev, Staging, Production  
✅ **3 Deployment Strategies** - Rolling, Blue-Green, Canary  
✅ **Security** - Trivy scanning, RBAC, secrets management  
✅ **Monitoring** - Health checks, logs, rollback automation

---

## File Structure

```
.github/workflows/
├── ci.yml                    # CI pipeline
├── cd-staging.yml           # Staging deployment
└── cd-production.yml        # Production deployment

k8s/overlays/
├── dev/                     # Dev configuration
├── staging/                 # Staging configuration
└── production/              # Production configuration

argocd/
├── project-production.yaml  # Production RBAC
├── application-dev.yaml     # Dev application
├── application-staging.yaml # Staging application
└── application-production.yaml # Production application

scripts/
├── install-argocd.sh        # Install ArgoCD
├── deploy-argocd-apps.sh    # Deploy applications
├── verify-pipeline.sh       # Verify setup
├── blue-green-deploy.sh     # Blue-green deployment
├── canary-deploy.sh         # Canary deployment
└── rollback.sh              # Rollback automation
```

---

## Resources

📖 **Detailed Guide:** [SETUP_GUIDE.md](./SETUP_GUIDE.md)  
📋 **Quick Reference:** [docs/CI_CD_QUICK_REFERENCE.md](./docs/CI_CD_QUICK_REFERENCE.md)  
📚 **Complete Documentation:** [docs/CI_CD_GUIDE.md](./docs/CI_CD_GUIDE.md)  
📊 **Implementation Summary:** [CI_CD_IMPLEMENTATION_SUMMARY.md](./CI_CD_IMPLEMENTATION_SUMMARY.md)

---

## Need Help?

1. Run verification script: `./scripts/verify-pipeline.sh`
2. Check detailed guide: `SETUP_GUIDE.md`
3. Review logs: `kubectl logs -n argocd -l app.kubernetes.io/name=argocd-server`
4. GitHub Actions: https://github.com/NawfalRAZOUK7/smarthr360_m3_future_skills/actions

**Your CI/CD pipeline is ready to use! 🎉**
