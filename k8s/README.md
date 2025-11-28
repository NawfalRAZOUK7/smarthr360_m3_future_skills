# Kubernetes Deployment Guide for SmartHR360

This directory contains Kubernetes manifests for deploying the SmartHR360 Future Skills application to a Kubernetes cluster.

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [Architecture](#architecture)
- [File Overview](#file-overview)
- [Configuration](#configuration)
- [Deployment Steps](#deployment-steps)
- [Verification](#verification)
- [Scaling](#scaling)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)
- [Useful Commands](#useful-commands)

## 🔧 Prerequisites

Before deploying, ensure you have:

1. **Kubernetes Cluster** (v1.24+)

   - Managed: EKS, GKE, AKS, or DigitalOcean Kubernetes
   - Self-hosted: kubeadm, k3s, or similar

2. **kubectl** CLI tool installed and configured

   ```bash
   kubectl version --client
   ```

3. **Ingress Controller** (Nginx)

   ```bash
   kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.1/deploy/static/provider/cloud/deploy.yaml
   ```

4. **cert-manager** for TLS certificates

   ```bash
   kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml
   ```

5. **Container Registry** (Docker Hub, ECR, GCR, ACR)

   - Build and push Docker images
   - Update image references in manifests

6. **Storage Class** configured in your cluster
   ```bash
   kubectl get storageclass
   ```

## 🏗️ Architecture

The deployment consists of:

- **Namespace**: `smarthr360` - Isolated namespace for all resources
- **PostgreSQL**: StatefulSet with persistent storage (100Gi)
- **Redis**: Deployment with persistent storage (10Gi)
- **Django API**: Deployment with 3-10 replicas (HPA enabled)
- **Celery Workers**: Deployment with 2-8 replicas (HPA enabled)
- **Celery Beat**: Deployment with 1 replica (singleton)
- **Ingress**: HTTPS with Let's Encrypt certificates
- **Network Policies**: Restrict pod-to-pod communication
- **RBAC**: Service accounts and role bindings
- **PDB**: Pod Disruption Budgets for high availability

## 📁 File Overview

Apply manifests in the following order:

| Order | File                         | Description                              |
| ----- | ---------------------------- | ---------------------------------------- |
| 1     | `00-namespace.yaml`          | Namespace definition                     |
| 2     | `01-configmap.yaml`          | Application configuration                |
| 3     | `02-secrets.yaml`            | Sensitive data (update before applying!) |
| 4     | `03-persistent-volumes.yaml` | Storage claims (210Gi total)             |
| 5     | `10-postgres.yaml`           | PostgreSQL database                      |
| 6     | `11-redis.yaml`              | Redis cache/broker                       |
| 7     | `20-api-deployment.yaml`     | Django API application                   |
| 8     | `21-celery-worker.yaml`      | Celery workers                           |
| 9     | `22-celery-beat.yaml`        | Celery beat scheduler                    |
| 10    | `30-ingress.yaml`            | Ingress + TLS certificates               |
| 11    | `40-hpa.yaml`                | Horizontal Pod Autoscalers               |
| 12    | `50-network-policies.yaml`   | Network security policies                |
| 13    | `60-rbac-pdb.yaml`           | RBAC + Pod Disruption Budgets            |

## ⚙️ Configuration

### 1. Update Secrets (CRITICAL!)

Edit `02-secrets.yaml` and replace all base64-encoded placeholder values:

```bash
# Generate a secure SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(50))" | base64

# Generate JWT_SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(50))" | base64

# Set database password
echo -n 'your-secure-password' | base64

# Update all other secrets
```

**Recommended**: Use external secret management instead:

- AWS Secrets Manager
- Azure Key Vault
- HashiCorp Vault
- Kubernetes External Secrets Operator

### 2. Update Container Images

Edit deployment files and replace `your-registry/smarthr360:latest`:

```yaml
# 20-api-deployment.yaml
image: your-registry.azurecr.io/smarthr360:v1.0.0

# 21-celery-worker.yaml
image: your-registry.azurecr.io/smarthr360-celery:v1.0.0
```

### 3. Update Domain Names

Edit `30-ingress.yaml` and replace `smarthr360.com` with your domain:

```yaml
spec:
  tls:
    - hosts:
        - api.yourdomain.com
        - yourdomain.com
```

### 4. Update Email Address

In `30-ingress.yaml`, update cert-manager email:

```yaml
spec:
  acme:
    email: admin@yourdomain.com # Replace with your email
```

### 5. Adjust Storage Classes

Edit `03-persistent-volumes.yaml` if your cluster uses a different storage class:

```yaml
storageClassName: gp3  # For AWS EKS
storageClassName: standard-rwo  # For GKE
storageClassName: managed-premium  # For AKS
```

### 6. Adjust Resource Limits

Based on your cluster capacity, adjust CPU/memory in deployment files:

```yaml
resources:
  requests:
    memory: "1Gi"
    cpu: "500m"
  limits:
    memory: "2Gi"
    cpu: "1000m"
```

## 🚀 Deployment Steps

### Step 1: Build and Push Docker Images

```bash
# Build images
docker build -t your-registry/smarthr360:v1.0.0 -f Dockerfile .
docker build -t your-registry/smarthr360-celery:v1.0.0 -f Dockerfile.celery .

# Push to registry
docker push your-registry/smarthr360:v1.0.0
docker push your-registry/smarthr360-celery:v1.0.0
```

### Step 2: Configure kubectl

```bash
# Verify cluster connection
kubectl cluster-info

# Set context (if multiple clusters)
kubectl config use-context your-cluster-name
```

### Step 3: Apply Kubernetes Manifests

```bash
# Navigate to k8s directory
cd k8s/

# Apply in order
kubectl apply -f 00-namespace.yaml
kubectl apply -f 01-configmap.yaml
kubectl apply -f 02-secrets.yaml
kubectl apply -f 03-persistent-volumes.yaml
kubectl apply -f 60-rbac-pdb.yaml
kubectl apply -f 10-postgres.yaml
kubectl apply -f 11-redis.yaml

# Wait for databases to be ready
kubectl wait --for=condition=ready pod -l app=postgres -n smarthr360 --timeout=300s
kubectl wait --for=condition=ready pod -l app=redis -n smarthr360 --timeout=300s

# Apply application components
kubectl apply -f 20-api-deployment.yaml
kubectl apply -f 21-celery-worker.yaml
kubectl apply -f 22-celery-beat.yaml

# Apply networking and autoscaling
kubectl apply -f 30-ingress.yaml
kubectl apply -f 40-hpa.yaml
kubectl apply -f 50-network-policies.yaml
```

### Step 4: Run Database Migrations

```bash
# Get API pod name
export API_POD=$(kubectl get pod -n smarthr360 -l component=api -o jsonpath='{.items[0].metadata.name}')

# Run migrations
kubectl exec -it $API_POD -n smarthr360 -- python manage.py migrate

# Create superuser (interactive)
kubectl exec -it $API_POD -n smarthr360 -- python manage.py createsuperuser

# Collect static files
kubectl exec -it $API_POD -n smarthr360 -- python manage.py collectstatic --noinput
```

### Step 5: Verify Deployment

```bash
# Check all pods are running
kubectl get pods -n smarthr360

# Check services
kubectl get svc -n smarthr360

# Check ingress
kubectl get ingress -n smarthr360

# Check PVCs
kubectl get pvc -n smarthr360

# View logs
kubectl logs -f deployment/smarthr360-api -n smarthr360
```

## ✅ Verification

### Health Checks

```bash
# Check API health
kubectl exec -it $API_POD -n smarthr360 -- curl http://localhost:8000/api/health/

# Port-forward to test locally
kubectl port-forward svc/smarthr360-api 8000:8000 -n smarthr360

# Test endpoint
curl http://localhost:8000/api/v1/skills/
```

### Database Connection

```bash
# Connect to PostgreSQL
kubectl exec -it postgres-0 -n smarthr360 -- psql -U smarthr360 -d smarthr360

# List tables
\dt

# Check migrations
SELECT * FROM django_migrations;
```

### Celery Workers

```bash
# Check worker status
kubectl exec -it deployment/smarthr360-celery-worker -n smarthr360 -- celery -A config inspect active

# Check scheduled tasks
kubectl exec -it deployment/smarthr360-celery-beat -n smarthr360 -- celery -A config inspect scheduled
```

## 📊 Scaling

### Manual Scaling

```bash
# Scale API
kubectl scale deployment smarthr360-api --replicas=5 -n smarthr360

# Scale Celery workers
kubectl scale deployment smarthr360-celery-worker --replicas=4 -n smarthr360
```

### Auto-scaling (HPA)

HPA is already configured in `40-hpa.yaml`:

```bash
# Check HPA status
kubectl get hpa -n smarthr360

# View HPA details
kubectl describe hpa smarthr360-api-hpa -n smarthr360
```

## 📈 Monitoring

### Kubernetes Dashboard

```bash
# Install dashboard (if not already installed)
kubectl apply -f https://raw.githubusercontent.com/kubernetes/dashboard/v2.7.0/aio/deploy/recommended.yaml

# Create admin user
kubectl create serviceaccount dashboard-admin -n kubernetes-dashboard
kubectl create clusterrolebinding dashboard-admin --clusterrole=cluster-admin --serviceaccount=kubernetes-dashboard:dashboard-admin

# Get token
kubectl create token dashboard-admin -n kubernetes-dashboard

# Port-forward
kubectl port-forward -n kubernetes-dashboard service/kubernetes-dashboard 8443:443
```

### Prometheus & Grafana

```bash
# Install Prometheus Operator
kubectl apply -f https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/main/bundle.yaml

# Install Grafana
kubectl apply -f https://raw.githubusercontent.com/grafana/grafana-operator/master/deploy/manifests/version.yaml
```

### View Logs

```bash
# Stream API logs
kubectl logs -f deployment/smarthr360-api -n smarthr360 --all-containers=true

# Stream worker logs
kubectl logs -f deployment/smarthr360-celery-worker -n smarthr360

# View events
kubectl get events -n smarthr360 --sort-by='.lastTimestamp'
```

## 🔧 Troubleshooting

### Pods Not Starting

```bash
# Describe pod to see events
kubectl describe pod <pod-name> -n smarthr360

# Check logs
kubectl logs <pod-name> -n smarthr360

# Common issues:
# - Image pull errors: Check image name and registry credentials
# - CrashLoopBackOff: Check application logs
# - Pending: Check PVC status and node resources
```

### Database Connection Issues

```bash
# Check PostgreSQL is running
kubectl get pods -l app=postgres -n smarthr360

# Check service endpoints
kubectl get endpoints postgres -n smarthr360

# Test connection from API pod
kubectl exec -it $API_POD -n smarthr360 -- nc -zv postgres 5432
```

### Ingress Not Working

```bash
# Check ingress controller
kubectl get pods -n ingress-nginx

# Check ingress resource
kubectl describe ingress smarthr360-ingress -n smarthr360

# Check certificate
kubectl get certificate -n smarthr360
kubectl describe certificate smarthr360-tls -n smarthr360

# Check cert-manager logs
kubectl logs -n cert-manager deployment/cert-manager
```

### High Memory Usage

```bash
# Check resource usage
kubectl top pods -n smarthr360

# Adjust limits in deployment files
# Restart deployment
kubectl rollout restart deployment/smarthr360-api -n smarthr360
```

## 📚 Useful Commands

```bash
# Switch to smarthr360 namespace
kubectl config set-context --current --namespace=smarthr360

# Get all resources
kubectl get all -n smarthr360

# Delete all resources (careful!)
kubectl delete namespace smarthr360

# Restart deployment
kubectl rollout restart deployment/smarthr360-api -n smarthr360

# View rollout status
kubectl rollout status deployment/smarthr360-api -n smarthr360

# Rollback deployment
kubectl rollout undo deployment/smarthr360-api -n smarthr360

# Execute commands in pod
kubectl exec -it <pod-name> -n smarthr360 -- /bin/bash

# Copy files to/from pod
kubectl cp <pod-name>:/app/logs/app.log ./app.log -n smarthr360

# Watch pods
kubectl get pods -n smarthr360 -w

# Get pod YAML
kubectl get pod <pod-name> -n smarthr360 -o yaml

# Port forward to service
kubectl port-forward svc/smarthr360-api 8000:8000 -n smarthr360

# Create backup of namespace
kubectl get all,configmaps,secrets,pvc -n smarthr360 -o yaml > backup.yaml
```

## 🔐 Security Best Practices

1. **Never commit secrets** to version control
2. **Use external secret management** (Vault, AWS Secrets Manager, etc.)
3. **Enable network policies** to restrict pod-to-pod communication
4. **Run as non-root user** (already configured)
5. **Keep images updated** with security patches
6. **Use RBAC** to limit permissions
7. **Enable TLS** for all external communication
8. **Regular backups** of persistent data
9. **Monitor logs** for suspicious activity
10. **Use Pod Security Standards** (PSS)

## 📞 Support

For issues or questions:

- Check application logs: `kubectl logs -f deployment/smarthr360-api -n smarthr360`
- Review Kubernetes events: `kubectl get events -n smarthr360`
- Contact DevOps team
- Refer to main documentation: `../docs/`

## 📄 License

Copyright © 2024 SmartHR360. All rights reserved.
