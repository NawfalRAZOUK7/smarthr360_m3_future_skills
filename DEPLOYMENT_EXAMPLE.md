# Example: Deployment Preparation Walkthrough

This document provides a complete example of preparing SmartHR360 for deployment.

## Scenario

You want to deploy SmartHR360 to:

- **Container Registry**: Docker Hub
- **Username**: `mycompany`
- **Domain**: `hr-platform.example.com`
- **Kubernetes Cluster**: AWS EKS (3 nodes, t3.xlarge)

## Step-by-Step Walkthrough

### Option 1: Using Interactive Script (Easiest)

```bash
# Run the interactive setup
./scripts/quick_setup.sh

# You'll be prompted for:
# Container Registry: docker.io
# Registry Username: mycompany
# Image Tag: v1.0.0
# Domain Name: hr-platform.example.com
# Admin Email: admin@example.com
# Choose: 3 (Full deployment preparation)
```

**What happens:**

1. Generates strong random secrets
2. Saves secrets to `.secrets.env` (keep secure!)
3. Updates `k8s/02-secrets.yaml` with base64-encoded values
4. Builds 3 Docker images:
   - `mycompany/smarthr360:v1.0.0`
   - `mycompany/smarthr360-celery:v1.0.0`
   - `mycompany/smarthr360-nginx:v1.0.0`
5. Pushes images to Docker Hub (you'll be prompted to login)
6. Updates Kubernetes manifests with your image names
7. Updates ingress with your domain names
8. Generates `DEPLOYMENT_CHECKLIST.md` with next steps

### Option 2: Using Environment Variables (Automation-Friendly)

```bash
# Set your configuration
export DOCKER_REGISTRY="docker.io"
export DOCKER_USERNAME="mycompany"
export IMAGE_TAG="v1.0.0"
export DOMAIN="hr-platform.example.com"
export ADMIN_EMAIL="admin@example.com"

# Run the full preparation
./scripts/prepare_deployment.sh

# Or run specific steps:
# ./scripts/prepare_deployment.sh --skip-build --skip-push  # Just secrets
# ./scripts/prepare_deployment.sh --skip-secrets            # Build and push only
```

### Option 3: Manual Step-by-Step

#### 1. Generate Secrets Manually

```bash
# Generate Django SECRET_KEY
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
# Output: django-insecure-example-key-abc123xyz789

# Generate JWT secret
python -c 'import secrets; print(secrets.token_urlsafe(50))'
# Output: aBcDeFgHiJkLmNoPqRsTuVwXyZ0123456789_-aBcDeFg

# Generate database password
python -c 'import secrets; print(secrets.token_urlsafe(32))'
# Output: xYz789AbC123_-DeF456GhI

# Encode to base64
echo -n 'django-insecure-example-key-abc123xyz789' | base64
# Output: ZGphbmdvLWluc2VjdXJlLWV4YW1wbGUta2V5LWFiYzEyM3h5ejc4OQ==
```

#### 2. Update k8s/02-secrets.yaml

Replace the placeholder values with your base64-encoded secrets:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: smarthr360-secrets
  namespace: smarthr360
data:
  SECRET_KEY: ZGphbmdvLWluc2VjdXJlLWV4YW1wbGUta2V5LWFiYzEyM3h5ejc4OQ==
  JWT_SECRET_KEY: YUJjRGVGZ0hpSmtMbU5vUHFSc1R1VndYeVowMTIzNDU2Nzg5Xy1hQmNEZUZn
  DB_PASSWORD: eFl6Nzg5QWJDMTI3Xy1EZUY0NTZHaEk=
  # ... etc
```

#### 3. Build Docker Images

```bash
# Login to Docker Hub
docker login docker.io
# Username: mycompany
# Password: [your password]

# Build API image
docker build \
  --target runtime \
  -t mycompany/smarthr360:v1.0.0 \
  -t mycompany/smarthr360:latest \
  -f Dockerfile .

# Build Celery image
docker build \
  -t mycompany/smarthr360-celery:v1.0.0 \
  -t mycompany/smarthr360-celery:latest \
  -f Dockerfile.celery .

# Build Nginx image
docker build \
  -t mycompany/smarthr360-nginx:v1.0.0 \
  -t mycompany/smarthr360-nginx:latest \
  -f Dockerfile.nginx .
```

#### 4. Push Images

```bash
docker push mycompany/smarthr360:v1.0.0
docker push mycompany/smarthr360:latest
docker push mycompany/smarthr360-celery:v1.0.0
docker push mycompany/smarthr360-celery:latest
docker push mycompany/smarthr360-nginx:v1.0.0
docker push mycompany/smarthr360-nginx:latest
```

#### 5. Update Kubernetes Manifests

Edit these files:

**k8s/20-api-deployment.yaml** (line 66):

```yaml
# Change from:
image: your-registry/smarthr360:latest

# To:
image: mycompany/smarthr360:v1.0.0
```

**k8s/21-celery-worker.yaml** (line 67):

```yaml
image: mycompany/smarthr360-celery:v1.0.0
```

**k8s/22-celery-beat.yaml** (line 51):

```yaml
image: mycompany/smarthr360-celery:v1.0.0
```

**k8s/30-ingress.yaml** (lines 49-52, 57, 69, 92, 116):

```yaml
# Change all instances of smarthr360.com to your domain
# api.smarthr360.com → api.hr-platform.example.com
# smarthr360.com → hr-platform.example.com
# admin@smarthr360.com → admin@example.com
```

## Verification

After running any option above:

### 1. Check Generated Files

```bash
# Secrets file (DO NOT COMMIT!)
cat .secrets.env

# Updated Kubernetes secrets
cat k8s/02-secrets.yaml

# Deployment checklist
cat DEPLOYMENT_CHECKLIST.md
```

### 2. Verify Docker Images

```bash
# List local images
docker images | grep mycompany

# Verify images are on registry
docker pull mycompany/smarthr360:v1.0.0
docker pull mycompany/smarthr360-celery:v1.0.0
docker pull mycompany/smarthr360-nginx:v1.0.0
```

### 3. Check Manifest Updates

```bash
# Check image references
grep "image:" k8s/20-api-deployment.yaml
grep "image:" k8s/21-celery-worker.yaml
grep "image:" k8s/22-celery-beat.yaml

# Check domain configuration
grep "hr-platform.example.com" k8s/30-ingress.yaml
```

## Deploy to Kubernetes

Once preparation is complete, follow these steps:

### 1. Connect to Your Cluster

```bash
# AWS EKS example
aws eks update-kubeconfig --region us-east-1 --name my-cluster

# Verify connection
kubectl cluster-info
kubectl get nodes
```

### 2. Install Prerequisites

```bash
# Nginx Ingress Controller
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.1/deploy/static/provider/cloud/deploy.yaml

# cert-manager for TLS
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Wait for controllers to be ready
kubectl wait --for=condition=ready pod -n ingress-nginx -l app.kubernetes.io/component=controller --timeout=300s
kubectl wait --for=condition=ready pod -n cert-manager -l app=cert-manager --timeout=300s
```

### 3. Apply SmartHR360 Manifests

```bash
cd k8s/

# Infrastructure
kubectl apply -f 00-namespace.yaml
kubectl apply -f 01-configmap.yaml
kubectl apply -f 02-secrets.yaml
kubectl apply -f 03-persistent-volumes.yaml
kubectl apply -f 60-rbac-pdb.yaml

# Databases
kubectl apply -f 10-postgres.yaml
kubectl apply -f 11-redis.yaml

# Wait for databases
kubectl wait --for=condition=ready pod -l app=postgres -n smarthr360 --timeout=300s
kubectl wait --for=condition=ready pod -l app=redis -n smarthr360 --timeout=300s

# Application
kubectl apply -f 20-api-deployment.yaml
kubectl apply -f 21-celery-worker.yaml
kubectl apply -f 22-celery-beat.yaml

# Networking
kubectl apply -f 30-ingress.yaml
kubectl apply -f 40-hpa.yaml
kubectl apply -f 50-network-policies.yaml
```

### 4. Run Migrations

```bash
# Get API pod
export API_POD=$(kubectl get pod -n smarthr360 -l component=api -o jsonpath='{.items[0].metadata.name}')

# Run migrations
kubectl exec -it $API_POD -n smarthr360 -- python manage.py migrate

# Collect static files
kubectl exec -it $API_POD -n smarthr360 -- python manage.py collectstatic --noinput
```

### 5. Configure DNS

```bash
# Get ingress external IP
kubectl get svc -n ingress-nginx

# Add DNS A records pointing to this IP:
# hr-platform.example.com → EXTERNAL_IP
# api.hr-platform.example.com → EXTERNAL_IP
# www.hr-platform.example.com → EXTERNAL_IP
```

### 6. Verify Deployment

```bash
# Check all pods are running
kubectl get pods -n smarthr360

# Check ingress
kubectl get ingress -n smarthr360

# Check certificate (may take a few minutes)
kubectl get certificate -n smarthr360

# Test API (once DNS is configured)
curl https://api.hr-platform.example.com/api/health/
```

## Troubleshooting

### Images Won't Pull

```bash
# Check image name
kubectl describe pod <pod-name> -n smarthr360 | grep Image

# Create Docker registry secret if using private registry
kubectl create secret docker-registry regcred \
  --docker-server=docker.io \
  --docker-username=mycompany \
  --docker-password=<your-password> \
  --docker-email=admin@example.com \
  -n smarthr360

# Add to deployment
kubectl patch serviceaccount smarthr360-sa -n smarthr360 \
  -p '{"imagePullSecrets": [{"name": "regcred"}]}'
```

### Certificate Not Issuing

```bash
# Check cert-manager logs
kubectl logs -n cert-manager deployment/cert-manager

# Check certificate request
kubectl describe certificate smarthr360-tls -n smarthr360

# Common issue: DNS not configured yet
# Solution: Configure DNS A records and wait
```

### Pods Crashing

```bash
# Check pod logs
kubectl logs <pod-name> -n smarthr360

# Check events
kubectl get events -n smarthr360 --sort-by='.lastTimestamp'

# Common issues:
# - Wrong secrets: Check k8s/02-secrets.yaml
# - Database not ready: Wait longer or check PostgreSQL logs
# - Out of memory: Increase resource limits
```

## Success! 🎉

Once deployed, access your application at:

- **API**: https://api.hr-platform.example.com/api/
- **Admin**: https://api.hr-platform.example.com/admin/
- **Health**: https://api.hr-platform.example.com/api/health/

Login credentials are in `.secrets.env`:

- Username: admin
- Password: [check DJANGO_SUPERUSER_PASSWORD in .secrets.env]

## Next Steps

1. Set up monitoring (Prometheus, Grafana)
2. Configure backups
3. Set up CI/CD pipeline
4. Load test the application
5. Set up alerting
6. Document runbooks for operations

---

**Remember:** Keep `.secrets.env` secure and never commit it to version control!
