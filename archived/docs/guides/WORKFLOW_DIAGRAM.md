# CI/CD Pipeline Visual Guide

## 🏗️ Complete Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Developer                                │
│                     (You - NawfalRAZOUK7)                        │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           │ git push
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                      GitHub Repository                           │
│          NawfalRAZOUK7/smarthr360_m3_future_skills              │
│                                                                  │
│  Branches:                                                       │
│  ├─ feature/*  ────→ [CI Tests]                                │
│  ├─ develop    ────→ [CI Tests] ──→ [CD Staging]               │
│  └─ main       ────→ [CI Tests] ──→ [CD Production]            │
└──────────────────────────┬──────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        │ Push to PR       │ Push to develop  │ Tag v*.*.*
        │                  │                  │
┌───────▼─────┐   ┌────────▼────────┐   ┌────▼──────────┐
│  CI Tests   │   │  CD Staging     │   │ CD Production │
│             │   │                 │   │               │
│ • Lint      │   │ • Build Images  │   │ • Validation  │
│ • Security  │   │ • Push to GHCR  │   │ • Backup      │
│ • Unit Test │   │ • Update K8s    │   │ • Deploy      │
│ • Build     │   │ • Deploy        │   │ • Monitor     │
│ • Scan      │   │ • Migrate       │   │ • Verify      │
└─────────────┘   └────────┬────────┘   └────┬──────────┘
                           │                  │
                           │ Auto-deploy      │ Manual approval
                           │                  │
┌──────────────────────────▼──────────────────▼──────────────────┐
│                          ArgoCD                                  │
│                    (GitOps Controller)                           │
│                                                                  │
│  Applications:                                                   │
│  ├─ smarthr360-dev        (Auto-sync from develop)             │
│  ├─ smarthr360-staging    (Auto-sync from develop)             │
│  └─ smarthr360-production (Manual sync from main)              │
│                                                                  │
│  UI: https://localhost:8080                                     │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           │ Sync manifests
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                    Kubernetes Cluster                            │
│                                                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   Dev Env       │  │  Staging Env    │  │  Production Env │ │
│  │ (smarthr360-dev)│  │(smarthr360-     │  │   (smarthr360)  │ │
│  │                 │  │   staging)      │  │                 │ │
│  │ • 1 replica     │  │ • 2 replicas    │  │ • 3 replicas    │ │
│  │ • 512Mi RAM     │  │ • 1Gi RAM       │  │ • 2Gi RAM       │ │
│  │ • Debug ON      │  │ • Debug OFF     │  │ • Debug OFF     │ │
│  │ • Auto-sync     │  │ • Auto-sync     │  │ • Manual sync   │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│                                                                  │
│  Each environment contains:                                      │
│  ├─ API Deployment          (Django REST API)                   │
│  ├─ Celery Worker           (Background tasks)                  │
│  ├─ Celery Beat             (Scheduled tasks)                   │
│  ├─ PostgreSQL              (Database)                          │
│  ├─ Redis                   (Cache & message broker)            │
│  ├─ Nginx                   (Reverse proxy)                     │
│  └─ Ingress                 (External access)                   │
└──────────────────────────────────────────────────────────────────┘
```

## 🔄 Deployment Flow

### Development Flow

```
Developer
   │
   ├─ Create feature branch: git checkout -b feature/new-feature
   │
   ├─ Make changes, commit
   │
   ├─ Push: git push origin feature/new-feature
   │
   └─ Create PR to develop
      │
      ├─ GitHub Actions runs CI
      │  ├─ Linting (flake8, black, isort)
      │  ├─ Security (bandit, safety, Trivy)
      │  ├─ Tests (pytest with coverage)
      │  └─ Build Docker images
      │
      ├─ Review & approve PR
      │
      └─ Merge to develop
         │
         ├─ GitHub Actions runs CD Staging
         │  ├─ Build & tag images
         │  ├─ Push to ghcr.io/nawfalrazouk7/*
         │  ├─ Update Kustomize manifests
         │  ├─ Deploy to staging
         │  ├─ Run migrations
         │  └─ Smoke tests
         │
         └─ ArgoCD auto-syncs to staging namespace
            │
            └─ Application live in staging! ✅
```

### Production Flow

```
Release Manager
   │
   ├─ Test in staging ✅
   │
   ├─ Merge develop to main
   │
   ├─ Create release tag: git tag v1.0.0
   │
   └─ Push tag: git push origin v1.0.0
      │
      ├─ GitHub Actions runs CD Production
      │  ├─ Pre-deployment validation
      │  │  ├─ Check tag format
      │  │  ├─ Verify staging health
      │  │  └─ Security scan
      │  │
      │  ├─ Create backups
      │  │  ├─ Database dump
      │  │  └─ Current manifests
      │  │
      │  ├─ Wait for manual approval ⏸️
      │  │  (Requires approval in GitHub UI)
      │  │
      │  ├─ Deploy with selected strategy
      │  │  ├─ Rolling (default)
      │  │  ├─ Blue-Green (zero downtime)
      │  │  └─ Canary (gradual rollout)
      │  │
      │  ├─ Run migrations
      │  │
      │  ├─ Verify deployment
      │  │
      │  └─ Monitor for 5 minutes
      │     └─ Auto-rollback on errors
      │
      └─ ArgoCD shows production app
         │
         ├─ Requires manual sync in UI
         │
         └─ After sync, application live! 🚀
```

## 🛠️ Setup Flow

```
Step 1: Generate Secrets
├─ Run: ./scripts/generate-secrets.sh
├─ Generates: Django SECRET_KEY, JWT_SECRET_KEY, passwords
└─ Saves to file (optional)

Step 2: Add to GitHub
├─ Go to: Settings → Secrets and variables → Actions
├─ Add each secret:
│  ├─ CLOUD_PROVIDER
│  ├─ DJANGO_SECRET_KEY
│  ├─ JWT_SECRET_KEY
│  ├─ Database passwords
│  └─ Cloud credentials (if needed)
└─ Saved ✅

Step 3: Install ArgoCD
├─ Run: ./scripts/install-argocd.sh
├─ Creates ArgoCD namespace
├─ Installs ArgoCD components
├─ Waits for pods to be ready
├─ Shows admin password
└─ Starts port-forward to UI ✅

Step 4: Access ArgoCD UI
├─ Open: https://localhost:8080
├─ Login: admin / <generated-password>
├─ Change password (recommended)
└─ Ready ✅

Step 5: Deploy Applications
├─ Run: ./scripts/deploy-argocd-apps.sh
├─ Creates production project (RBAC)
├─ Deploys 3 applications:
│  ├─ smarthr360-dev
│  ├─ smarthr360-staging
│  └─ smarthr360-production
└─ Applications created ✅

Step 6: Initial Sync
├─ Option A: Using script (auto-syncs dev & staging)
├─ Option B: Using ArgoCD UI (click SYNC on each app)
└─ Option C: Using ArgoCD CLI
   ├─ argocd app sync smarthr360-dev
   ├─ argocd app sync smarthr360-staging
   └─ argocd app sync smarthr360-production
      └─ Applications synced ✅

Step 7: Verify
├─ Run: ./scripts/verify-pipeline.sh
├─ Checks:
│  ├─ ArgoCD installation ✅
│  ├─ Applications deployed ✅
│  ├─ Pods running ✅
│  ├─ Secrets configured ✅
│  └─ Workflows present ✅
└─ All good! ✅

Step 8: Test Pipeline
├─ Create test branch
├─ Push changes
├─ Watch GitHub Actions
├─ See deployment in ArgoCD
└─ Pipeline working! 🎉
```

## 🎯 Deployment Strategies Visual

### Rolling Update (Default)

```
Before:     [v1.0] [v1.0] [v1.0]

Step 1:     [v1.1] [v1.0] [v1.0]  ← One pod updated
Step 2:     [v1.1] [v1.1] [v1.0]  ← Two pods updated
Step 3:     [v1.1] [v1.1] [v1.1]  ← All pods updated ✅

Downtime: None (overlapping deployment)
Rollback: Fast (kubectl rollout undo)
```

### Blue-Green Deployment

```
Before:     Blue Env [v1.0] [v1.0] [v1.0]  ← Active
            Green Env: None

Step 1:     Blue [v1.0] [v1.0] [v1.0]  ← Still active
            Green [v1.1] [v1.1] [v1.1]  ← Deploy & test

Step 2:     Blue [v1.0] [v1.0] [v1.0]  ← Still serving traffic
            Green [v1.1] [v1.1] [v1.1]  ← Ready & tested ✅

Step 3:     Switch traffic to Green
            Blue [v1.0] [v1.0] [v1.0]  ← No traffic
            Green [v1.1] [v1.1] [v1.1]  ← Now active ✅

After:      Optional: Delete Blue
            Green [v1.1] [v1.1] [v1.1]  ← Active

Downtime: Zero
Rollback: Instant (switch back to Blue)
Usage: ./scripts/blue-green-deploy.sh v1.1.0
```

### Canary Deployment

```
Before:     Stable [v1.0] [v1.0] [v1.0] [v1.0] [v1.0]

Step 1:     Canary [v1.1]                           ← 5% traffic
            Stable [v1.0] [v1.0] [v1.0] [v1.0]

Step 2:     Canary [v1.1] [v1.1]                    ← 10% traffic
            Stable [v1.0] [v1.0] [v1.0]
            Monitor... ✅

Step 3:     Canary [v1.1] [v1.1]                    ← 25% traffic
            Stable [v1.0] [v1.0] [v1.0]
            Monitor... ✅

Step 4:     Canary [v1.1] [v1.1] [v1.1]            ← 50% traffic
            Stable [v1.0] [v1.0]
            Monitor... ✅

Step 5:     All [v1.1] [v1.1] [v1.1] [v1.1] [v1.1] ← 100% ✅

Downtime: None
Rollback: Automatic if health checks fail
Usage: ./scripts/canary-deploy.sh v1.1.0
Custom: CANARY_STEPS="10,50,100" ./scripts/canary-deploy.sh v1.1.0
```

## 📊 Environment Comparison

```
┌─────────────────┬──────────────┬──────────────┬──────────────┐
│    Resource     │     Dev      │   Staging    │  Production  │
├─────────────────┼──────────────┼──────────────┼──────────────┤
│ API Replicas    │      1       │      2       │      3       │
│ Worker Replicas │      1       │      2       │      3       │
│ HPA Min/Max     │    1-3       │    2-5       │    3-10      │
│ CPU Request     │   250m       │   500m       │   500m       │
│ Memory Request  │   512Mi      │   1Gi        │   1Gi        │
│ CPU Limit       │   500m       │   1000m      │   1000m      │
│ Memory Limit    │   1Gi        │   2Gi        │   2Gi        │
│ PostgreSQL PVC  │   10Gi       │   50Gi       │   100Gi      │
│ Media PVC       │   10Gi       │   25Gi       │   50Gi       │
│ ML Models PVC   │   5Gi        │   20Gi       │   20Gi       │
│ Debug Mode      │   true       │   false      │   false      │
│ Log Level       │   DEBUG      │   INFO       │   WARNING    │
│ SSL Issuer      │   staging    │   prod       │   prod       │
│ Auto-sync       │   Yes        │   Yes        │   No         │
│ Approval        │   No         │   No         │   Yes        │
└─────────────────┴──────────────┴──────────────┴──────────────┘
```

## 🔐 Security Flow

```
GitHub Secrets (Encrypted)
   │
   ├─ DJANGO_SECRET_KEY ──────┐
   ├─ JWT_SECRET_KEY ─────────┤
   ├─ Database passwords ─────┤
   └─ Cloud credentials ──────┤
                              │
                              ▼
                    GitHub Actions Workflow
                              │
                              ├─ Uses secrets securely
                              ├─ Never logged or exposed
                              └─ Passed to kubectl
                                    │
                                    ▼
                         Kubernetes Secrets
                         (Base64 encoded)
                                    │
                                    ├─ smarthr360-secrets-dev
                                    ├─ smarthr360-secrets-staging
                                    └─ smarthr360-secrets
                                          │
                                          ▼
                                  Application Pods
                                  (Environment variables)
                                          │
                                          └─ Used by application ✅
```

## 🎬 Quick Commands Reference

### Setup

```bash
# 1. Generate secrets
./scripts/generate-secrets.sh

# 2. Install ArgoCD
./scripts/install-argocd.sh

# 3. Deploy applications
./scripts/deploy-argocd-apps.sh

# 4. Verify setup
./scripts/verify-pipeline.sh
```

### Deploy

```bash
# Dev/Staging (automatic)
git push origin develop

# Production (manual approval)
git tag v1.0.0
git push origin v1.0.0
# Then approve in GitHub Actions UI

# Blue-Green
./scripts/blue-green-deploy.sh v1.0.1

# Canary
./scripts/canary-deploy.sh v1.0.1

# Rollback
./scripts/rollback.sh all
```

### Monitor

```bash
# ArgoCD UI
kubectl port-forward svc/argocd-server -n argocd 8080:443
# Open: https://localhost:8080

# Application status
kubectl get applications -n argocd

# Pod status
kubectl get pods -n smarthr360-staging

# Logs
kubectl logs -f -n smarthr360-staging -l component=api
```

## 📚 Documentation Map

```
Repository Root
│
├─ QUICKSTART.md              ← Start here! (5-minute setup)
├─ SETUP_GUIDE.md             ← Detailed step-by-step guide
├─ CHANGES.md                 ← What was updated
├─ WORKFLOW_DIAGRAM.md        ← This file (visual guide)
│
├─ CI_CD_IMPLEMENTATION_SUMMARY.md  ← Complete overview
│
├─ docs/
│  ├─ CI_CD_GUIDE.md          ← Complete CI/CD documentation
│  └─ CI_CD_QUICK_REFERENCE.md ← Command reference
│
└─ scripts/
   ├─ generate-secrets.sh     ← Generate secure secrets
   ├─ install-argocd.sh       ← Install ArgoCD
   ├─ deploy-argocd-apps.sh   ← Deploy applications
   ├─ verify-pipeline.sh      ← Verify setup
   ├─ blue-green-deploy.sh    ← Blue-green deployment
   ├─ canary-deploy.sh        ← Canary deployment
   └─ rollback.sh             ← Rollback automation
```

---

**Ready to start?** → [QUICKSTART.md](./QUICKSTART.md)

**Need help?** → [SETUP_GUIDE.md](./SETUP_GUIDE.md)

**Your complete CI/CD pipeline awaits! 🚀**
