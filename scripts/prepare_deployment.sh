#!/bin/bash
# ==============================================================================
# SmartHR360 Deployment Preparation Script
# ==============================================================================
# This script:
# 1. Generates secure secrets and updates 02-secrets.yaml
# 2. Builds Docker images with multi-stage builds
# 3. Tags and pushes images to container registry
# 4. Updates Kubernetes manifests with image references
# ==============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ==============================================================================
# Configuration Variables
# ==============================================================================

# Container Registry Configuration
REGISTRY="${DOCKER_REGISTRY:-docker.io}"  # Change to your registry
REGISTRY_USERNAME="${DOCKER_USERNAME:-your-username}"
IMAGE_PREFIX="${REGISTRY}/${REGISTRY_USERNAME}"

# Image Tags
IMAGE_TAG="${IMAGE_TAG:-v1.0.0}"
IMAGE_TAG_LATEST="latest"

# Domain Configuration
DOMAIN="${DOMAIN:-smarthr360.com}"
API_SUBDOMAIN="api.${DOMAIN}"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@${DOMAIN}}"

# Kubernetes Namespace
K8S_NAMESPACE="smarthr360"

# Database Configuration
DB_NAME="smarthr360"
DB_USER="smarthr360_user"

# ==============================================================================
# Helper Functions
# ==============================================================================

print_header() {
    echo -e "\n${BLUE}===============================================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}===============================================================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# ==============================================================================
# Step 1: Generate Secure Secrets
# ==============================================================================

generate_secrets() {
    print_header "Step 1: Generating Secure Secrets"

    # Generate Django SECRET_KEY
    print_info "Generating Django SECRET_KEY..."
    DJANGO_SECRET_KEY=$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
    DJANGO_SECRET_KEY_B64=$(echo -n "$DJANGO_SECRET_KEY" | base64)
    print_success "Django SECRET_KEY generated"

    # Generate JWT_SECRET_KEY
    print_info "Generating JWT_SECRET_KEY..."
    JWT_SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(50))')
    JWT_SECRET_KEY_B64=$(echo -n "$JWT_SECRET_KEY" | base64)
    print_success "JWT_SECRET_KEY generated"

    # Generate DB Password
    print_info "Generating database password..."
    DB_PASSWORD=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')
    DB_PASSWORD_B64=$(echo -n "$DB_PASSWORD" | base64)
    DB_USER_B64=$(echo -n "$DB_USER" | base64)
    print_success "Database password generated"

    # Generate Redis Password
    print_info "Generating Redis password..."
    REDIS_PASSWORD=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')
    REDIS_PASSWORD_B64=$(echo -n "$REDIS_PASSWORD" | base64)
    print_success "Redis password generated"

    # Generate Superuser credentials
    print_info "Generating Django superuser credentials..."
    SUPERUSER_USERNAME="admin"
    SUPERUSER_PASSWORD=$(python -c 'import secrets; print(secrets.token_urlsafe(24))')
    SUPERUSER_EMAIL="${ADMIN_EMAIL}"
    SUPERUSER_USERNAME_B64=$(echo -n "$SUPERUSER_USERNAME" | base64)
    SUPERUSER_PASSWORD_B64=$(echo -n "$SUPERUSER_PASSWORD" | base64)
    SUPERUSER_EMAIL_B64=$(echo -n "$SUPERUSER_EMAIL" | base64)
    print_success "Superuser credentials generated"

    # DB name for postgres secrets
    DB_NAME_B64=$(echo -n "$DB_NAME" | base64)

    # Save secrets to a secure file (NOT committed to git)
    SECRETS_FILE=".secrets.env"
    cat > "$SECRETS_FILE" << EOF
# SmartHR360 Generated Secrets
# Generated on: $(date)
# DO NOT COMMIT THIS FILE TO VERSION CONTROL!

# Django
DJANGO_SECRET_KEY=${DJANGO_SECRET_KEY}
JWT_SECRET_KEY=${JWT_SECRET_KEY}

# Database
DB_NAME=${DB_NAME}
DB_USER=${DB_USER}
DB_PASSWORD=${DB_PASSWORD}

# Redis
REDIS_PASSWORD=${REDIS_PASSWORD}

# Django Superuser
DJANGO_SUPERUSER_USERNAME=${SUPERUSER_USERNAME}
DJANGO_SUPERUSER_PASSWORD=${SUPERUSER_PASSWORD}
DJANGO_SUPERUSER_EMAIL=${SUPERUSER_EMAIL}

# Base64 Encoded (for Kubernetes secrets)
DJANGO_SECRET_KEY_B64=${DJANGO_SECRET_KEY_B64}
JWT_SECRET_KEY_B64=${JWT_SECRET_KEY_B64}
DB_USER_B64=${DB_USER_B64}
DB_PASSWORD_B64=${DB_PASSWORD_B64}
DB_NAME_B64=${DB_NAME_B64}
REDIS_PASSWORD_B64=${REDIS_PASSWORD_B64}
SUPERUSER_USERNAME_B64=${SUPERUSER_USERNAME_B64}
SUPERUSER_PASSWORD_B64=${SUPERUSER_PASSWORD_B64}
SUPERUSER_EMAIL_B64=${SUPERUSER_EMAIL_B64}
EOF

    chmod 600 "$SECRETS_FILE"
    print_success "Secrets saved to $SECRETS_FILE (secure file)"
    print_warning "IMPORTANT: Keep $SECRETS_FILE secure and DO NOT commit to git!"

    # Update .gitignore
    if ! grep -q ".secrets.env" .gitignore 2>/dev/null; then
        echo ".secrets.env" >> .gitignore
        print_success "Added .secrets.env to .gitignore"
    fi

    # Update k8s/02-secrets.yaml
    print_info "Updating k8s/02-secrets.yaml with generated secrets..."
    cat > k8s/02-secrets.yaml << EOF
# ==============================================================================
# Secrets Configuration (Base64 encoded)
# Generated on: $(date)
# ==============================================================================
apiVersion: v1
kind: Secret
metadata:
  name: smarthr360-secrets
  namespace: smarthr360
  labels:
    app: smarthr360
    component: secrets
type: Opaque
data:
  SECRET_KEY: ${DJANGO_SECRET_KEY_B64}
  JWT_SECRET_KEY: ${JWT_SECRET_KEY_B64}
  DB_PASSWORD: ${DB_PASSWORD_B64}
  DB_USER: ${DB_USER_B64}
  REDIS_PASSWORD: ${REDIS_PASSWORD_B64}
  ELASTIC_APM_SECRET_TOKEN: ""
  SENTRY_DSN: ""
  DJANGO_SUPERUSER_USERNAME: ${SUPERUSER_USERNAME_B64}
  DJANGO_SUPERUSER_PASSWORD: ${SUPERUSER_PASSWORD_B64}
  DJANGO_SUPERUSER_EMAIL: ${SUPERUSER_EMAIL_B64}

---
# ==============================================================================
# Database Secret (for PostgreSQL StatefulSet)
# ==============================================================================
apiVersion: v1
kind: Secret
metadata:
  name: postgres-secrets
  namespace: smarthr360
  labels:
    app: smarthr360
    component: postgres
type: Opaque
data:
  POSTGRES_USER: ${DB_USER_B64}
  POSTGRES_PASSWORD: ${DB_PASSWORD_B64}
  POSTGRES_DB: ${DB_NAME_B64}
EOF

    print_success "Updated k8s/02-secrets.yaml with real secrets"
    print_warning "Secrets are base64 encoded but NOT encrypted. Use external secret management in production!"
}

# ==============================================================================
# Step 2: Build Docker Images
# ==============================================================================

build_images() {
    print_header "Step 2: Building Docker Images"

    print_info "Building smarthr360 API image (multi-stage)..."
    docker build \
        --target runtime \
        -t ${IMAGE_PREFIX}/smarthr360:${IMAGE_TAG} \
        -t ${IMAGE_PREFIX}/smarthr360:${IMAGE_TAG_LATEST} \
        -f Dockerfile \
        .
    print_success "Built smarthr360:${IMAGE_TAG}"

    print_info "Building smarthr360-celery image..."
    docker build \
        -t ${IMAGE_PREFIX}/smarthr360-celery:${IMAGE_TAG} \
        -t ${IMAGE_PREFIX}/smarthr360-celery:${IMAGE_TAG_LATEST} \
        -f Dockerfile.celery \
        .
    print_success "Built smarthr360-celery:${IMAGE_TAG}"

    print_info "Building smarthr360-nginx image..."
    docker build \
        -t ${IMAGE_PREFIX}/smarthr360-nginx:${IMAGE_TAG} \
        -t ${IMAGE_PREFIX}/smarthr360-nginx:${IMAGE_TAG_LATEST} \
        -f Dockerfile.nginx \
        .
    print_success "Built smarthr360-nginx:${IMAGE_TAG}"

    print_success "All images built successfully"
}

# ==============================================================================
# Step 3: Push Images to Registry
# ==============================================================================

push_images() {
    print_header "Step 3: Pushing Images to Registry"

    print_info "Container Registry: ${REGISTRY}"
    print_info "Username: ${REGISTRY_USERNAME}"
    print_info "Image Tag: ${IMAGE_TAG}"

    # Login to registry (if needed)
    if [ "${REGISTRY}" != "docker.io" ] || [ ! -f ~/.docker/config.json ]; then
        print_info "Logging in to ${REGISTRY}..."
        docker login ${REGISTRY}
    fi

    print_info "Pushing smarthr360:${IMAGE_TAG}..."
    docker push ${IMAGE_PREFIX}/smarthr360:${IMAGE_TAG}
    docker push ${IMAGE_PREFIX}/smarthr360:${IMAGE_TAG_LATEST}
    print_success "Pushed smarthr360:${IMAGE_TAG}"

    print_info "Pushing smarthr360-celery:${IMAGE_TAG}..."
    docker push ${IMAGE_PREFIX}/smarthr360-celery:${IMAGE_TAG}
    docker push ${IMAGE_PREFIX}/smarthr360-celery:${IMAGE_TAG_LATEST}
    print_success "Pushed smarthr360-celery:${IMAGE_TAG}"

    print_info "Pushing smarthr360-nginx:${IMAGE_TAG}..."
    docker push ${IMAGE_PREFIX}/smarthr360-nginx:${IMAGE_TAG}
    docker push ${IMAGE_PREFIX}/smarthr360-nginx:${IMAGE_TAG_LATEST}
    print_success "Pushed smarthr360-nginx:${IMAGE_TAG}"

    print_success "All images pushed successfully"
}

# ==============================================================================
# Step 4: Update Kubernetes Manifests
# ==============================================================================

update_manifests() {
    print_header "Step 4: Updating Kubernetes Manifests"

    # Update image references in deployment files
    print_info "Updating image references..."

    # 20-api-deployment.yaml
    sed -i.bak "s|image: your-registry/smarthr360:latest.*|image: ${IMAGE_PREFIX}/smarthr360:${IMAGE_TAG}|g" k8s/20-api-deployment.yaml
    print_success "Updated k8s/20-api-deployment.yaml"

    # 21-celery-worker.yaml
    sed -i.bak "s|image: your-registry/smarthr360-celery:latest.*|image: ${IMAGE_PREFIX}/smarthr360-celery:${IMAGE_TAG}|g" k8s/21-celery-worker.yaml
    print_success "Updated k8s/21-celery-worker.yaml"

    # 22-celery-beat.yaml
    sed -i.bak "s|image: your-registry/smarthr360-celery:latest.*|image: ${IMAGE_PREFIX}/smarthr360-celery:${IMAGE_TAG}|g" k8s/22-celery-beat.yaml
    print_success "Updated k8s/22-celery-beat.yaml"

    # Update domain names in ingress
    print_info "Updating domain names in ingress..."
    sed -i.bak "s|smarthr360\.com|${DOMAIN}|g" k8s/30-ingress.yaml
    sed -i.bak "s|api\.smarthr360\.com|${API_SUBDOMAIN}|g" k8s/30-ingress.yaml
    sed -i.bak "s|admin@smarthr360\.com|${ADMIN_EMAIL}|g" k8s/30-ingress.yaml
    print_success "Updated k8s/30-ingress.yaml with domain: ${DOMAIN}"

    # Clean up backup files
    rm -f k8s/*.bak

    print_success "All manifests updated successfully"
}

# ==============================================================================
# Step 5: Review Resource Limits
# ==============================================================================

review_resources() {
    print_header "Step 5: Resource Limits Review"

    print_info "Current resource configuration:"
    echo ""
    echo "API Pods (20-api-deployment.yaml):"
    echo "  Requests: 1Gi memory, 500m CPU"
    echo "  Limits:   2Gi memory, 1000m CPU"
    echo "  Replicas: 3-10 (HPA)"
    echo ""
    echo "Celery Workers (21-celery-worker.yaml):"
    echo "  Requests: 1Gi memory, 500m CPU"
    echo "  Limits:   3Gi memory, 1500m CPU"
    echo "  Replicas: 2-8 (HPA)"
    echo ""
    echo "Celery Beat (22-celery-beat.yaml):"
    echo "  Requests: 256Mi memory, 100m CPU"
    echo "  Limits:   512Mi memory, 250m CPU"
    echo "  Replicas: 1"
    echo ""
    echo "PostgreSQL (10-postgres.yaml):"
    echo "  Requests: 512Mi memory, 250m CPU"
    echo "  Limits:   2Gi memory, 1000m CPU"
    echo ""
    echo "Redis (11-redis.yaml):"
    echo "  Requests: 256Mi memory, 100m CPU"
    echo "  Limits:   1Gi memory, 500m CPU"
    echo ""

    print_info "Total minimum resources required:"
    echo "  CPU: ~2.5 cores"
    echo "  Memory: ~4.5 GB"
    echo ""

    print_info "Total maximum resources (with HPA at max):"
    echo "  CPU: ~20 cores"
    echo "  Memory: ~35 GB"
    echo ""

    print_warning "Review these limits based on your cluster capacity!"
    print_info "To adjust, edit the 'resources' section in deployment files"
}

# ==============================================================================
# Step 6: Generate Deployment Summary
# ==============================================================================

generate_summary() {
    print_header "Deployment Summary"

    cat > DEPLOYMENT_CHECKLIST.md << EOF
# SmartHR360 Deployment Checklist
Generated on: $(date)

## ✅ Completed Steps

1. **Secrets Generated**
   - Django SECRET_KEY: ✅
   - JWT Secret: ✅
   - Database passwords: ✅
   - Redis password: ✅
   - Superuser credentials: ✅
   - File: \`.secrets.env\` (DO NOT COMMIT!)

2. **Docker Images Built**
   - ${IMAGE_PREFIX}/smarthr360:${IMAGE_TAG}
   - ${IMAGE_PREFIX}/smarthr360-celery:${IMAGE_TAG}
   - ${IMAGE_PREFIX}/smarthr360-nginx:${IMAGE_TAG}

3. **Kubernetes Manifests Updated**
   - Image references: ✅
   - Domain names: ${DOMAIN}
   - API subdomain: ${API_SUBDOMAIN}

## 📋 Next Steps

### 1. Verify Cluster Access
\`\`\`bash
kubectl cluster-info
kubectl get nodes
\`\`\`

### 2. Install Prerequisites
\`\`\`bash
# Nginx Ingress Controller
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.1/deploy/static/provider/cloud/deploy.yaml

# cert-manager (for TLS)
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml
\`\`\`

### 3. Apply Kubernetes Manifests
\`\`\`bash
cd k8s/
kubectl apply -f 00-namespace.yaml
kubectl apply -f 01-configmap.yaml
kubectl apply -f 02-secrets.yaml
kubectl apply -f 03-persistent-volumes.yaml
kubectl apply -f 60-rbac-pdb.yaml
kubectl apply -f 10-postgres.yaml
kubectl apply -f 11-redis.yaml

# Wait for databases
kubectl wait --for=condition=ready pod -l app=postgres -n smarthr360 --timeout=300s
kubectl wait --for=condition=ready pod -l app=redis -n smarthr360 --timeout=300s

# Deploy application
kubectl apply -f 20-api-deployment.yaml
kubectl apply -f 21-celery-worker.yaml
kubectl apply -f 22-celery-beat.yaml
kubectl apply -f 30-ingress.yaml
kubectl apply -f 40-hpa.yaml
kubectl apply -f 50-network-policies.yaml
\`\`\`

### 4. Run Database Migrations
\`\`\`bash
export API_POD=\$(kubectl get pod -n smarthr360 -l component=api -o jsonpath='{.items[0].metadata.name}')
kubectl exec -it \$API_POD -n smarthr360 -- python manage.py migrate
kubectl exec -it \$API_POD -n smarthr360 -- python manage.py collectstatic --noinput
\`\`\`

### 5. Verify Deployment
\`\`\`bash
kubectl get pods -n smarthr360
kubectl get svc -n smarthr360
kubectl get ingress -n smarthr360
\`\`\`

### 6. Configure DNS
Point your domain to the ingress controller's external IP:
\`\`\`bash
kubectl get svc -n ingress-nginx
\`\`\`

Add DNS A records:
- ${DOMAIN} → [INGRESS_IP]
- ${API_SUBDOMAIN} → [INGRESS_IP]
- www.${DOMAIN} → [INGRESS_IP]

### 7. Monitor Certificate Issuance
\`\`\`bash
kubectl get certificate -n smarthr360
kubectl describe certificate smarthr360-tls -n smarthr360
\`\`\`

## 🔐 Security Notes

- Secrets file: \`.secrets.env\` (Keep secure, DO NOT commit!)
- Kubernetes secrets are base64 encoded but NOT encrypted
- Consider using external secret management:
  - AWS Secrets Manager
  - Azure Key Vault
  - HashiCorp Vault
  - Sealed Secrets

## 📊 Resource Summary

**Minimum Required:**
- CPU: ~2.5 cores
- Memory: ~4.5 GB
- Storage: ~210 GB (PVCs)

**Maximum (HPA at max):**
- CPU: ~20 cores
- Memory: ~35 GB

## 📞 Access Information

- API Endpoint: https://${API_SUBDOMAIN}
- Admin Panel: https://${API_SUBDOMAIN}/admin
- Superuser: ${SUPERUSER_USERNAME} (password in .secrets.env)

## 🔧 Useful Commands

\`\`\`bash
# Watch deployment
kubectl get pods -n smarthr360 -w

# View logs
kubectl logs -f deployment/smarthr360-api -n smarthr360

# Scale manually
kubectl scale deployment smarthr360-api --replicas=5 -n smarthr360

# Restart deployment
kubectl rollout restart deployment/smarthr360-api -n smarthr360

# Port forward for testing
kubectl port-forward svc/smarthr360-api 8000:8000 -n smarthr360
\`\`\`
EOF

    print_success "Generated DEPLOYMENT_CHECKLIST.md"

    echo ""
    print_success "All preparation steps completed!"
    echo ""
    print_info "Next: Review DEPLOYMENT_CHECKLIST.md and deploy to Kubernetes"
    echo ""
}

# ==============================================================================
# Main Execution
# ==============================================================================

main() {
    echo -e "${GREEN}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║       SmartHR360 Deployment Preparation Script              ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"

    # Check if running from project root
    if [ ! -f "manage.py" ]; then
        print_error "Must run from project root directory"
        exit 1
    fi

    # Parse command line arguments
    SKIP_SECRETS=false
    SKIP_BUILD=false
    SKIP_PUSH=false
    DRY_RUN=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-secrets)
                SKIP_SECRETS=true
                shift
                ;;
            --skip-build)
                SKIP_BUILD=true
                shift
                ;;
            --skip-push)
                SKIP_PUSH=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --registry)
                REGISTRY="$2"
                shift 2
                ;;
            --username)
                REGISTRY_USERNAME="$2"
                shift 2
                ;;
            --tag)
                IMAGE_TAG="$2"
                shift 2
                ;;
            --domain)
                DOMAIN="$2"
                API_SUBDOMAIN="api.$2"
                shift 2
                ;;
            --help)
                echo "Usage: $0 [options]"
                echo ""
                echo "Options:"
                echo "  --skip-secrets      Skip secret generation"
                echo "  --skip-build        Skip Docker image building"
                echo "  --skip-push         Skip pushing images to registry"
                echo "  --dry-run           Show what would be done without doing it"
                echo "  --registry URL      Container registry URL (default: docker.io)"
                echo "  --username USER     Registry username"
                echo "  --tag TAG           Image tag (default: v1.0.0)"
                echo "  --domain DOMAIN     Your domain name (default: smarthr360.com)"
                echo "  --help              Show this help message"
                echo ""
                echo "Environment Variables:"
                echo "  DOCKER_REGISTRY     Container registry URL"
                echo "  DOCKER_USERNAME     Registry username"
                echo "  IMAGE_TAG           Docker image tag"
                echo "  DOMAIN              Your domain name"
                echo "  ADMIN_EMAIL         Admin email address"
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done

    if [ "$DRY_RUN" = true ]; then
        print_warning "DRY RUN MODE - No changes will be made"
        echo ""
    fi

    # Execute steps
    if [ "$SKIP_SECRETS" = false ]; then
        [ "$DRY_RUN" = false ] && generate_secrets || print_info "Would generate secrets"
    fi

    if [ "$SKIP_BUILD" = false ]; then
        [ "$DRY_RUN" = false ] && build_images || print_info "Would build images"
    fi

    if [ "$SKIP_PUSH" = false ]; then
        [ "$DRY_RUN" = false ] && push_images || print_info "Would push images"
    fi

    [ "$DRY_RUN" = false ] && update_manifests || print_info "Would update manifests"
    review_resources
    [ "$DRY_RUN" = false ] && generate_summary || print_info "Would generate summary"

    echo ""
    print_success "Setup complete! 🚀"
    echo ""
}

# Run main function
main "$@"
