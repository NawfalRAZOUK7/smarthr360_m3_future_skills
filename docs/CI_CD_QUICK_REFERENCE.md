# SmartHR360 CI/CD Quick Reference

Quick commands and procedures for common CI/CD operations.

## 📋 Table of Contents

- [Deployment Commands](#deployment-commands)
- [Rollback Procedures](#rollback-procedures)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)
- [Emergency Procedures](#emergency-procedures)

---

## 🚀 Deployment Commands

### Deploy to Development

```bash
# Push to develop branch (auto-deploys via ArgoCD)
git checkout develop
git pull origin develop
git merge feature/your-feature
git push origin develop

# Verify deployment
argocd app get smarthr360-dev
kubectl get pods -n smarthr360-dev
```

### Deploy to Staging

```bash
# Merge to staging branch (triggers CD pipeline)
git checkout staging
git pull origin staging
git merge develop
git push origin staging

# Monitor deployment
kubectl rollout status deployment/smarthr360-api -n smarthr360-staging -w
```

### Deploy to Production

#### Option 1: Rolling Update (Standard)

```bash
# Create and push tag
git checkout main
git pull origin main
git merge staging
git tag v1.2.3
git push origin main
git push origin v1.2.3

# Monitor in GitHub Actions
# https://github.com/your-org/smarthr360/actions
```

#### Option 2: Blue-Green Deployment

```bash
# Run script
./scripts/blue-green-deploy.sh v1.2.3

# The script will:
# 1. Create new deployment
# 2. Run smoke tests
# 3. Ask for confirmation
# 4. Switch traffic
```

#### Option 3: Canary Deployment

```bash
# Standard canary (5%, 10%, 25%, 50%, 100%)
./scripts/canary-deploy.sh v1.2.3

# Custom canary steps
CANARY_STEPS="10,20,50,100" \
STEP_DURATION="10m" \
./scripts/canary-deploy.sh v1.2.3
```

---

## ⏮️ Rollback Procedures

### Automated Rollback (Recommended)

```bash
# Rollback all components
./scripts/rollback.sh all

# Rollback specific component
./scripts/rollback.sh api
./scripts/rollback.sh celery-worker
```

### Manual Rollback

```bash
# Rollback to previous version
kubectl rollout undo deployment/smarthr360-api -n smarthr360

# Rollback to specific revision
kubectl rollout history deployment/smarthr360-api -n smarthr360
kubectl rollout undo deployment/smarthr360-api -n smarthr360 --to-revision=5
```

### ArgoCD Rollback

```bash
# Via CLI
argocd app rollback smarthr360-production

# Via UI
# Navigate to: Applications → smarthr360-production → History → Select revision → Rollback
```

### Blue-Green Rollback

```bash
# Switch back to previous color
kubectl patch service smarthr360-api -n smarthr360 \
  -p '{"spec":{"selector":{"color":"blue"}}}'
```

---

## 📊 Monitoring

### Check Deployment Status

```bash
# Get all pods
kubectl get pods -n smarthr360

# Watch rollout
kubectl rollout status deployment/smarthr360-api -n smarthr360 -w

# Check deployment history
kubectl rollout history deployment/smarthr360-api -n smarthr360
```

### View Logs

```bash
# API logs (live)
kubectl logs -f -n smarthr360 -l component=api

# Celery worker logs
kubectl logs -f -n smarthr360 -l component=celery-worker

# All logs from last hour
kubectl logs -n smarthr360 -l app=smarthr360 --since=1h

# Previous pod logs (if crashed)
kubectl logs -n smarthr360 <pod-name> --previous
```

### Resource Usage

```bash
# Pod resource usage
kubectl top pods -n smarthr360

# Node resource usage
kubectl top nodes

# HPA status
kubectl get hpa -n smarthr360
kubectl describe hpa smarthr360-api-hpa -n smarthr360
```

### Service Health

```bash
# Get services
kubectl get svc -n smarthr360

# Get ingress
kubectl get ingress -n smarthr360

# Test API health
kubectl port-forward -n smarthr360 svc/smarthr360-api 8000:8000
curl http://localhost:8000/api/health/

# Check endpoints
kubectl get endpoints -n smarthr360
```

### ArgoCD Monitoring

```bash
# List applications
argocd app list

# Get app details
argocd app get smarthr360-production

# Check sync status
argocd app diff smarthr360-production

# View app logs
argocd app logs smarthr360-production
```

---

## 🔧 Troubleshooting

### Pod Issues

#### ImagePullBackOff

```bash
# Describe pod
kubectl describe pod <pod-name> -n smarthr360

# Check image exists
docker pull ghcr.io/your-org/smarthr360-api:v1.2.3

# Verify registry secret
kubectl get secret ghcr-secret -n smarthr360
kubectl describe secret ghcr-secret -n smarthr360
```

#### CrashLoopBackOff

```bash
# Check logs
kubectl logs <pod-name> -n smarthr360
kubectl logs <pod-name> -n smarthr360 --previous

# Check events
kubectl get events -n smarthr360 --sort-by='.lastTimestamp' | grep <pod-name>

# Debug container
kubectl exec -it <pod-name> -n smarthr360 -- sh
```

#### Pending Pods

```bash
# Check why pending
kubectl describe pod <pod-name> -n smarthr360

# Common causes:
# 1. Insufficient resources
kubectl describe nodes | grep -A 5 "Allocated resources"

# 2. PVC issues
kubectl get pvc -n smarthr360
kubectl describe pvc <pvc-name> -n smarthr360

# 3. Node selector issues
kubectl get nodes --show-labels
```

### Deployment Issues

#### Deployment Stuck

```bash
# Check deployment status
kubectl get deployment smarthr360-api -n smarthr360
kubectl describe deployment smarthr360-api -n smarthr360

# Check replica set
kubectl get rs -n smarthr360
kubectl describe rs <rs-name> -n smarthr360

# Force delete stuck pods
kubectl delete pod <pod-name> -n smarthr360 --grace-period=0 --force
```

#### Rollout Paused

```bash
# Resume rollout
kubectl rollout resume deployment/smarthr360-api -n smarthr360

# Restart deployment
kubectl rollout restart deployment/smarthr360-api -n smarthr360
```

### Database Issues

#### Connection Failures

```bash
# Test database connectivity
kubectl exec -n smarthr360 <api-pod> -- nc -zv postgres 5432

# Check database pod
kubectl get pod -n smarthr360 -l app=postgres
kubectl logs -n smarthr360 -l app=postgres

# Verify credentials
kubectl get secret smarthr360-secrets -n smarthr360 -o yaml

# Access database
kubectl exec -it -n smarthr360 <postgres-pod> -- psql -U smarthr360_user smarthr360
```

#### Migration Issues

```bash
# Check migration status
kubectl exec -n smarthr360 <api-pod> -- python manage.py showmigrations

# Run migrations manually
kubectl exec -n smarthr360 <api-pod> -- python manage.py migrate

# Fake migration if needed
kubectl exec -n smarthr360 <api-pod> -- python manage.py migrate --fake app_name migration_name
```

### Ingress Issues

#### Certificate Not Issuing

```bash
# Check certificate
kubectl get certificate -n smarthr360
kubectl describe certificate smarthr360-tls -n smarthr360

# Check certificate request
kubectl get certificaterequest -n smarthr360
kubectl describe certificaterequest <request-name> -n smarthr360

# Check cert-manager logs
kubectl logs -n cert-manager deployment/cert-manager

# Delete and recreate certificate
kubectl delete certificate smarthr360-tls -n smarthr360
kubectl apply -f k8s/30-ingress.yaml
```

#### 502 Bad Gateway

```bash
# Check API pods
kubectl get pods -n smarthr360 -l component=api

# Check service endpoints
kubectl get endpoints smarthr360-api -n smarthr360

# Check ingress
kubectl describe ingress smarthr360-ingress -n smarthr360

# Check nginx logs
kubectl logs -n ingress-nginx -l app.kubernetes.io/component=controller
```

### ArgoCD Issues

#### Application OutOfSync

```bash
# Check differences
argocd app diff smarthr360-production

# Sync manually
argocd app sync smarthr360-production

# Force sync (ignore differences)
argocd app sync smarthr360-production --force

# Refresh cache
argocd app refresh smarthr360-production
```

#### Sync Failing

```bash
# Check sync status
argocd app get smarthr360-production

# View detailed logs
argocd app logs smarthr360-production --follow

# Check hooks
kubectl get jobs -n smarthr360
kubectl logs job/<hook-job> -n smarthr360

# Delete failed hooks
kubectl delete job <hook-job> -n smarthr360
argocd app sync smarthr360-production --retry
```

---

## 🚨 Emergency Procedures

### Complete Service Outage

```bash
# 1. Quick assessment
kubectl get pods -n smarthr360
kubectl get svc -n smarthr360
kubectl get ingress -n smarthr360

# 2. Check external access
curl https://api.smarthr360.com/api/health/

# 3. Immediate rollback
./scripts/rollback.sh all

# 4. If still down, scale up
kubectl scale deployment smarthr360-api -n smarthr360 --replicas=5

# 5. Check database
kubectl logs -n smarthr360 -l app=postgres --tail=100

# 6. Restart pods if needed
kubectl rollout restart deployment/smarthr360-api -n smarthr360
```

### Database Emergency

```bash
# 1. Check database status
kubectl get pod -n smarthr360 -l app=postgres

# 2. Create immediate backup
DB_POD=$(kubectl get pod -n smarthr360 -l app=postgres -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n smarthr360 $DB_POD -- pg_dump -U smarthr360_user smarthr360 > emergency-backup-$(date +%Y%m%d-%H%M%S).sql

# 3. Check database logs
kubectl logs -n smarthr360 $DB_POD --tail=200

# 4. If corrupted, restore from backup
kubectl exec -i -n smarthr360 $DB_POD -- psql -U smarthr360_user smarthr360 < latest-backup.sql
```

### High Error Rate

```bash
# 1. Check recent errors
kubectl logs -n smarthr360 -l component=api --since=5m | grep ERROR

# 2. Check resource usage
kubectl top pods -n smarthr360

# 3. Scale up if under load
kubectl scale deployment smarthr360-api -n smarthr360 --replicas=5
kubectl scale deployment smarthr360-celery-worker -n smarthr360 --replicas=4

# 4. Restart if memory leak suspected
kubectl rollout restart deployment/smarthr360-api -n smarthr360
```

### Certificate Expired

```bash
# 1. Check certificate
kubectl get certificate -n smarthr360

# 2. Delete and recreate
kubectl delete certificate smarthr360-tls -n smarthr360
kubectl delete secret smarthr360-tls -n smarthr360

# 3. Reapply ingress
kubectl apply -f k8s/overlays/production/ingress-patch.yaml

# 4. Monitor certificate issuance
kubectl get certificate -n smarthr360 -w
```

---

## 🔐 Security Operations

### Rotate Secrets

```bash
# 1. Generate new secrets
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'

# 2. Update in GitHub Secrets
# Settings → Secrets and variables → Actions → Update DJANGO_SECRET_KEY

# 3. Trigger redeployment
git tag v1.2.4-security
git push origin v1.2.4-security

# 4. Verify pods restarted
kubectl get pods -n smarthr360 -w
```

### Update Docker Registry Credentials

```bash
# Delete old secret
kubectl delete secret ghcr-secret -n smarthr360

# Create new secret
kubectl create secret docker-registry ghcr-secret \
  --docker-server=ghcr.io \
  --docker-username=$GITHUB_ACTOR \
  --docker-password=$NEW_TOKEN \
  --namespace=smarthr360

# Restart deployments to use new secret
kubectl rollout restart deployment/smarthr360-api -n smarthr360
```

---

## 📞 Contacts

- **DevOps Lead**: devops@smarthr360.com
- **On-Call**: +1-XXX-XXX-XXXX
- **Slack**: #devops-alerts
- **Incident Channel**: #incident-response

---

## 📚 Related Documentation

- [Full CI/CD Guide](./CI_CD_GUIDE.md)
- [Kubernetes Deployment Guide](../KUBERNETES_DEPLOYMENT.md)
- [Architecture Overview](./architecture/ARCHITECTURE.md)
- [Troubleshooting Guide](./TROUBLESHOOTING.md)

---

**Quick Links:**

- [GitHub Actions](https://github.com/your-org/smarthr360/actions)
- [ArgoCD Dashboard](https://argocd.smarthr360.com)
- [Grafana Dashboards](https://grafana.smarthr360.com)
- [Sentry](https://sentry.io/smarthr360)
