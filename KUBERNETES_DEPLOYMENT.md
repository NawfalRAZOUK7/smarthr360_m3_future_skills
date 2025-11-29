# SmartHR360 - Complete Deployment Guide

## 🚀 Quick Start

Choose one of the following methods to prepare your deployment:

### Method 1: Interactive Setup (Recommended)

```bash
./scripts/quick_setup.sh
```

### Method 2: Automated Script with Defaults

```bash
# Set environment variables
export DOCKER_REGISTRY="docker.io"
export DOCKER_USERNAME="your-username"
export IMAGE_TAG="v1.0.0"
export DOMAIN="yourdomain.com"
export ADMIN_EMAIL="admin@yourdomain.com"

# Run preparation script
./scripts/prepare_deployment.sh
```

### Method 3: Manual Configuration

Follow the steps below to manually configure each component.

---

## 📋 Manual Setup Steps

### Step 1: Update Secrets

#### Option A: Use the script to generate secrets

```bash
./scripts/prepare_deployment.sh --skip-build --skip-push
```

#### Option B: Generate secrets manually

```bash
# Generate Django SECRET_KEY
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'

# Generate JWT Secret
python -c 'import secrets; print(secrets.token_urlsafe(50))'

# Generate database password
python -c 'import secrets; print(secrets.token_urlsafe(32))'

# Encode to base64
echo -n 'your-secret-value' | base64
```

Then update `k8s/02-secrets.yaml` with the base64-encoded values.

### Step 2: Build Docker Images

#### Prerequisites

- Docker installed and running
- Docker registry account (Docker Hub, GitHub Container Registry, etc.)

#### Build Commands

```bash
# Login to your registry
docker login docker.io  # or your registry

# Build API image (multi-stage)
docker build -t your-username/smarthr360:v1.0.0 -f Dockerfile .

# Build Celery worker image
docker build -t your-username/smarthr360-celery:v1.0.0 -f Dockerfile.celery .

# Build Nginx image
docker build -t your-username/smarthr360-nginx:v1.0.0 -f Dockerfile.nginx .

# Tag as latest
docker tag your-username/smarthr360:v1.0.0 your-username/smarthr360:latest
docker tag your-username/smarthr360-celery:v1.0.0 your-username/smarthr360-celery:latest
docker tag your-username/smarthr360-nginx:v1.0.0 your-username/smarthr360-nginx:latest
```

### Step 3: Push Images to Registry

```bash
docker push your-username/smarthr360:v1.0.0
docker push your-username/smarthr360:latest
docker push your-username/smarthr360-celery:v1.0.0
docker push your-username/smarthr360-celery:latest
docker push your-username/smarthr360-nginx:v1.0.0
docker push your-username/smarthr360-nginx:latest
```

### Step 4: Update Kubernetes Manifests

#### Update image references in:

- `k8s/20-api-deployment.yaml` (line 66)
- `k8s/21-celery-worker.yaml` (line 67)
- `k8s/22-celery-beat.yaml` (line 51)

Change from:

```yaml
image: your-registry/smarthr360:latest
```

To:

```yaml
image: your-username/smarthr360:v1.0.0
```

#### Update domain names in `k8s/30-ingress.yaml`:

- Line 49-52: TLS hosts
- Line 57: API subdomain host
- Line 69: Main domain host
- Line 92: WWW subdomain host
- Line 116: Admin email

### Step 5: Review Resource Limits

Check your Kubernetes cluster capacity:

```bash
kubectl top nodes
kubectl describe nodes
```

Current resource configuration:

| Component     | Requests     | Limits       | Replicas   |
| ------------- | ------------ | ------------ | ---------- |
| API           | 1Gi / 500m   | 2Gi / 1000m  | 3-10 (HPA) |
| Celery Worker | 1Gi / 500m   | 3Gi / 1500m  | 2-8 (HPA)  |
| Celery Beat   | 256Mi / 100m | 512Mi / 250m | 1          |
| PostgreSQL    | 512Mi / 250m | 2Gi / 1000m  | 1          |
| Redis         | 256Mi / 100m | 1Gi / 500m   | 1          |

**Total minimum:** ~2.5 CPU cores, ~4.5GB RAM  
**Total maximum (HPA at max):** ~20 CPU cores, ~35GB RAM

To adjust, edit the `resources` section in deployment files.

---

## 🎯 Deployment to Kubernetes

### Prerequisites

1. **Kubernetes Cluster** (v1.24+)

   - Cloud: AWS EKS, Google GKE, Azure AKS, DigitalOcean
   - Local: Minikube, Kind, k3s

2. **kubectl** configured and connected

   ```bash
   kubectl cluster-info
   kubectl get nodes
   ```

3. **Storage Class** available
   ```bash
   kubectl get storageclass
   ```

### Install Required Components

#### 1. Nginx Ingress Controller

```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.1/deploy/static/provider/cloud/deploy.yaml

# Wait for deployment
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=120s
```

#### 2. cert-manager (for TLS certificates)

```bash
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Wait for deployment
kubectl wait --namespace cert-manager \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/instance=cert-manager \
  --timeout=120s
```

### Deploy SmartHR360

#### 1. Apply Kubernetes Manifests (in order)

```bash
cd k8s/

# Infrastructure
kubectl apply -f 00-namespace.yaml
kubectl apply -f 01-configmap.yaml
kubectl apply -f 02-secrets.yaml
kubectl apply -f 03-persistent-volumes.yaml
kubectl apply -f 60-rbac-pdb.yaml

# Verify namespace
kubectl get namespace smarthr360

# Databases
kubectl apply -f 10-postgres.yaml
kubectl apply -f 11-redis.yaml

# Wait for databases to be ready
echo "Waiting for PostgreSQL..."
kubectl wait --for=condition=ready pod -l app=postgres -n smarthr360 --timeout=300s

echo "Waiting for Redis..."
kubectl wait --for=condition=ready pod -l app=redis -n smarthr360 --timeout=300s
```

#### 2. Deploy Application Components

```bash
# Application
kubectl apply -f 20-api-deployment.yaml
kubectl apply -f 21-celery-worker.yaml
kubectl apply -f 22-celery-beat.yaml

# Wait for API pods
kubectl wait --for=condition=ready pod -l component=api -n smarthr360 --timeout=300s
```

#### 3. Run Database Migrations

```bash
# Get API pod name
export API_POD=$(kubectl get pod -n smarthr360 -l component=api -o jsonpath='{.items[0].metadata.name}')

# Run migrations
kubectl exec -it $API_POD -n smarthr360 -- python manage.py migrate

# Collect static files
kubectl exec -it $API_POD -n smarthr360 -- python manage.py collectstatic --noinput

# Create superuser (optional, if not using AUTO_CREATE_SUPERUSER)
kubectl exec -it $API_POD -n smarthr360 -- python manage.py createsuperuser
```

#### 4. Apply Networking & Scaling

```bash
# Ingress with TLS
kubectl apply -f 30-ingress.yaml

# Horizontal Pod Autoscalers
kubectl apply -f 40-hpa.yaml

# Network Policies
kubectl apply -f 50-network-policies.yaml
```

### Configure DNS

1. Get the ingress external IP:

```bash
kubectl get svc -n ingress-nginx
# Look for EXTERNAL-IP of ingress-nginx-controller
```

2. Add DNS A records pointing to the external IP:

   - `yourdomain.com` → EXTERNAL-IP
   - `api.yourdomain.com` → EXTERNAL-IP
   - `www.yourdomain.com` → EXTERNAL-IP

3. Wait for DNS propagation (can take up to 48 hours):

```bash
# Test DNS resolution
nslookup api.yourdomain.com
```

### Verify Deployment

```bash
# Check all pods are running
kubectl get pods -n smarthr360

# Check services
kubectl get svc -n smarthr360

# Check ingress
kubectl get ingress -n smarthr360

# Check certificate (may take a few minutes)
kubectl get certificate -n smarthr360
kubectl describe certificate smarthr360-tls -n smarthr360

# View logs
kubectl logs -f deployment/smarthr360-api -n smarthr360

# Check HPA status
kubectl get hpa -n smarthr360
```

### Access Your Application

Once DNS is configured and certificate is issued:

- **API**: https://api.yourdomain.com/api/
- **Admin Panel**: https://api.yourdomain.com/admin/
- **Health Check**: https://api.yourdomain.com/api/health/

---

## 🔍 Testing & Verification

### Port-Forward for Local Testing (before DNS)

```bash
# Forward API service
kubectl port-forward svc/smarthr360-api 8000:8000 -n smarthr360

# Test in another terminal
curl http://localhost:8000/api/health/
curl http://localhost:8000/api/skills/
```

### Check Application Health

```bash
# API health
kubectl exec -it $API_POD -n smarthr360 -- curl http://localhost:8000/api/health/

# Database connection
kubectl exec -it postgres-0 -n smarthr360 -- psql -U smarthr360_user -d smarthr360 -c "\dt"

# Redis connection
kubectl exec -it deployment/smarthr360-api -n smarthr360 -- python -c "
import redis
r = redis.Redis(host='redis', port=6379)
print('Redis connection:', r.ping())
"

# Celery workers
kubectl exec -it deployment/smarthr360-celery-worker -n smarthr360 -- celery -A config inspect active
```

---

## 📊 Monitoring & Operations

### View Logs

```bash
# Stream API logs
kubectl logs -f deployment/smarthr360-api -n smarthr360

# Stream worker logs
kubectl logs -f deployment/smarthr360-celery-worker -n smarthr360

# View recent events
kubectl get events -n smarthr360 --sort-by='.lastTimestamp' | tail -20

# Logs from all API pods
kubectl logs -l component=api -n smarthr360 --tail=100
```

### Scaling

```bash
# Manual scaling
kubectl scale deployment smarthr360-api --replicas=5 -n smarthr360

# Check HPA status
kubectl get hpa -n smarthr360
kubectl describe hpa smarthr360-api-hpa -n smarthr360

# Force HPA evaluation
kubectl autoscale deployment smarthr360-api --cpu-percent=50 --min=3 --max=10 -n smarthr360
```

### Rolling Updates

```bash
# Update to new image version
kubectl set image deployment/smarthr360-api api=your-username/smarthr360:v1.0.1 -n smarthr360

# Check rollout status
kubectl rollout status deployment/smarthr360-api -n smarthr360

# Rollback if needed
kubectl rollout undo deployment/smarthr360-api -n smarthr360

# View rollout history
kubectl rollout history deployment/smarthr360-api -n smarthr360
```

### Backup & Recovery

```bash
# Backup database
kubectl exec -it postgres-0 -n smarthr360 -- pg_dump -U smarthr360_user smarthr360 > backup.sql

# Backup persistent volumes
kubectl get pvc -n smarthr360

# Backup all manifests
kubectl get all,configmaps,secrets,pvc -n smarthr360 -o yaml > smarthr360-backup.yaml
```

---

## 🐛 Troubleshooting

### Pods Not Starting

```bash
# Check pod status
kubectl get pods -n smarthr360

# Describe problematic pod
kubectl describe pod <pod-name> -n smarthr360

# Check events
kubectl get events -n smarthr360 --field-selector involvedObject.name=<pod-name>

# Common issues:
# - ImagePullBackOff: Wrong image name or private registry auth issue
# - CrashLoopBackOff: Application error, check logs
# - Pending: Insufficient resources or PVC issue
```

### Database Connection Issues

```bash
# Check PostgreSQL pod
kubectl get pods -l app=postgres -n smarthr360

# Check service endpoints
kubectl get endpoints postgres -n smarthr360

# Test connection from API pod
kubectl exec -it $API_POD -n smarthr360 -- nc -zv postgres 5432

# Check PostgreSQL logs
kubectl logs postgres-0 -n smarthr360
```

### Certificate Issues

```bash
# Check certificate status
kubectl get certificate -n smarthr360
kubectl describe certificate smarthr360-tls -n smarthr360

# Check cert-manager logs
kubectl logs -n cert-manager deployment/cert-manager

# Check certificate request
kubectl get certificaterequest -n smarthr360

# Force certificate renewal
kubectl delete certificate smarthr360-tls -n smarthr360
kubectl apply -f k8s/30-ingress.yaml
```

### Performance Issues

```bash
# Check resource usage
kubectl top pods -n smarthr360
kubectl top nodes

# Check HPA metrics
kubectl get hpa -n smarthr360
kubectl describe hpa smarthr360-api-hpa -n smarthr360

# Check for throttling
kubectl describe pod <pod-name> -n smarthr360 | grep -A 5 "Resource Limits"
```

---

## 🔐 Security Best Practices

1. **Secrets Management**

   - Use external secret managers (AWS Secrets Manager, Vault, etc.)
   - Never commit `.secrets.env` to git
   - Rotate secrets regularly

2. **Network Security**

   - Network policies are applied by default
   - Only necessary traffic is allowed between pods
   - External access only through ingress

3. **Image Security**

   - Use specific image tags, not `latest`
   - Scan images for vulnerabilities
   - Use minimal base images

4. **RBAC**

   - Service accounts with minimal permissions
   - Pod security standards applied
   - Regular audits of permissions

5. **TLS/SSL**
   - All external traffic encrypted
   - Automatic certificate renewal with cert-manager
   - HSTS headers enabled

---

## 📞 Support

For issues or questions:

- Check logs: `kubectl logs -f deployment/smarthr360-api -n smarthr360`
- Review events: `kubectl get events -n smarthr360`
- Consult [Kubernetes documentation](https://kubernetes.io/docs/)
- Review application docs in `docs/` directory

---

## 📚 Additional Resources

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Nginx Ingress Controller](https://kubernetes.github.io/ingress-nginx/)
- [cert-manager Documentation](https://cert-manager.io/docs/)
- [Docker Documentation](https://docs.docker.com/)
- Main Project Documentation: `docs/DEPLOYMENT_GUIDE.md`

---

**Generated**: November 28, 2025  
**Version**: 1.0.0  
**SmartHR360 Future Skills Platform**
