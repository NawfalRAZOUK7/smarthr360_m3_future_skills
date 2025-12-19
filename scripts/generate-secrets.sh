#!/bin/bash
# Generate Secrets Script
# This script generates secure secrets for your application

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Banner
echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║          SmartHR360 - Secret Generator Script             ║"
echo "╔════════════════════════════════════════════════════════════╗"
echo -e "${NC}"

echo "This script generates secure secrets for your application."
echo "You'll need to add these to GitHub Secrets manually."
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo -e "${RED}Error: Python is required to generate secrets${NC}"
    exit 1
fi

# Use python3 if available, otherwise python
PYTHON_CMD=$(command -v python3 || command -v python)

echo -e "${YELLOW}Generating secrets...${NC}"
echo ""

# Generate Django SECRET_KEY (ensure it's at least 50 chars)
echo -e "${BLUE}1. Django SECRET_KEY${NC}"
DJANGO_SECRET=$(cat <<EOF | $PYTHON_CMD
from django.core.management.utils import get_random_secret_key
import secrets
import string

# Keep generating until we get a key without $ characters (to avoid shell interpretation)
while True:
    key = get_random_secret_key()
    if '$' not in key and len(key) >= 50:
        print(key)
        break
EOF
)
echo "   $DJANGO_SECRET"
echo "   Length: ${#DJANGO_SECRET}"

# --- Automatically update secrets.env with new Django SECRET_KEY ---
SECRETS_ENV_FILE="$(dirname "$0")/../secrets.env"
if [ -f "$SECRETS_ENV_FILE" ]; then
    # Remove any existing SECRET_KEY line
    grep -v '^SECRET_KEY=' "$SECRETS_ENV_FILE" > "$SECRETS_ENV_FILE.tmp"
    mv "$SECRETS_ENV_FILE.tmp" "$SECRETS_ENV_FILE"
    # Add new SECRET_KEY
    echo "SECRET_KEY=$DJANGO_SECRET" >> "$SECRETS_ENV_FILE"
    echo -e "${GREEN}Updated secrets.env with new SECRET_KEY${NC}"
else
    echo "SECRET_KEY=$DJANGO_SECRET" > "$SECRETS_ENV_FILE"
    echo -e "${GREEN}Created secrets.env with new SECRET_KEY${NC}"
fi

# Generate JWT SECRET_KEY
echo -e "${BLUE}2. JWT SECRET_KEY${NC}"
JWT_SECRET=$(cat <<EOF | $PYTHON_CMD
import secrets
print(secrets.token_urlsafe(50))
EOF
)
echo "   $JWT_SECRET"
echo ""

# Generate Database Passwords
echo -e "${BLUE}3. Database Passwords${NC}"
STAGING_DB_PASSWORD=$(cat <<EOF | $PYTHON_CMD
import secrets
print(secrets.token_urlsafe(32))
EOF
)
echo "   STAGING_DB_PASSWORD: $STAGING_DB_PASSWORD"

PROD_DB_PASSWORD=$(cat <<EOF | $PYTHON_CMD
import secrets
print(secrets.token_urlsafe(32))
EOF
)
echo "   PROD_DB_PASSWORD: $PROD_DB_PASSWORD"
echo ""

# Generate Redis Passwords
echo -e "${BLUE}4. Redis Passwords${NC}"
STAGING_REDIS_PASSWORD=$(cat <<EOF | $PYTHON_CMD
import secrets
print(secrets.token_urlsafe(32))
EOF
)
echo "   STAGING_REDIS_PASSWORD: $STAGING_REDIS_PASSWORD"

PROD_REDIS_PASSWORD=$(cat <<EOF | $PYTHON_CMD
import secrets
print(secrets.token_urlsafe(32))
EOF
)
echo "   PROD_REDIS_PASSWORD: $PROD_REDIS_PASSWORD"
echo ""

# Save to file
if [ -f "/.dockerenv" ]; then
    SAVE_FILE="y"
    echo -e "${YELLOW}Docker detected: automatically saving secrets to file.${NC}"
else
    echo -e "${YELLOW}Would you like to save these secrets to a file? (y/n)${NC}"
    read -r SAVE_FILE
fi

if [[ "$SAVE_FILE" =~ ^[Yy]$ ]]; then
    OUTPUT_FILE="secrets-$(date +%Y%m%d-%H%M%S).txt"

    cat > "$OUTPUT_FILE" <<EOF
# SmartHR360 Generated Secrets
# Generated on: $(date)
#
# IMPORTANT:
# - Add these to GitHub Secrets (Settings → Secrets and variables → Actions)
# - DO NOT commit this file to git
# - Store securely and delete after use

# ============================================
# Application Secrets
# ============================================

DJANGO_SECRET_KEY=$DJANGO_SECRET
JWT_SECRET_KEY=$JWT_SECRET

# ============================================
# Staging Database
# ============================================

STAGING_DB_USER=smarthr360_staging
STAGING_DB_PASSWORD=$STAGING_DB_PASSWORD

# ============================================
# Production Database
# ============================================

PROD_DB_USER=smarthr360_prod
PROD_DB_PASSWORD=$PROD_DB_PASSWORD

# ============================================
# Staging Redis
# ============================================

STAGING_REDIS_PASSWORD=$STAGING_REDIS_PASSWORD

# ============================================
# Production Redis
# ============================================

PROD_REDIS_PASSWORD=$PROD_REDIS_PASSWORD

# ============================================
# Cloud Provider (choose one)
# ============================================

# For Local Kubernetes:
CLOUD_PROVIDER=local
# KUBE_CONFIG=<base64 encoded kubeconfig>
# Get with: cat ~/.kube/config | base64

# For AWS EKS:
# CLOUD_PROVIDER=aws
# AWS_ACCESS_KEY_ID=<your-access-key>
# AWS_SECRET_ACCESS_KEY=<your-secret-key>
# AWS_REGION=us-east-1
# EKS_CLUSTER_NAME=smarthr360-cluster

# For GCP GKE:
# CLOUD_PROVIDER=gcp
# GCP_CREDENTIALS=<service-account-json>
# GCP_PROJECT=<your-project>
# GCP_ZONE=us-central1-a
# GKE_CLUSTER_NAME=smarthr360-cluster

# For Azure AKS:
# CLOUD_PROVIDER=azure
# AZURE_CREDENTIALS=<service-principal-json>
# AZURE_RESOURCE_GROUP=smarthr360-rg
# AKS_CLUSTER_NAME=smarthr360-cluster

# ============================================
# Optional: Monitoring & Notifications
# ============================================

# ELASTIC_APM_SECRET_TOKEN=<your-token>
# SENTRY_DSN=<your-dsn>
# SLACK_WEBHOOK_URL=<your-webhook>
# CODECOV_TOKEN=<your-token>

EOF

    echo -e "${GREEN}✓ Secrets saved to: $OUTPUT_FILE${NC}"
    echo ""
    echo -e "${RED}IMPORTANT SECURITY NOTICE:${NC}"
    echo "  1. This file contains sensitive information"
    echo "  2. Add these secrets to GitHub now"
    echo "  3. Delete this file after use: rm $OUTPUT_FILE"
    echo "  4. Never commit this file to git"
    echo ""
fi

# Instructions
echo -e "${GREEN}"
echo "════════════════════════════════════════════════════════════"
echo "          How to Add Secrets to GitHub"
echo "════════════════════════════════════════════════════════════"
echo -e "${NC}"

echo "1. Go to your repository settings:"
echo "   https://github.com/NawfalRAZOUK7/smarthr360_m3_future_skills/settings/secrets/actions"
echo ""

echo "2. Click 'New repository secret'"
echo ""

echo "3. Add each secret one by one:"
echo ""
echo "   Required secrets:"
echo "   ├─ CLOUD_PROVIDER (local/aws/gcp/azure)"
echo "   ├─ DJANGO_SECRET_KEY"
echo "   ├─ JWT_SECRET_KEY"
echo "   ├─ STAGING_DB_USER (smarthr360_staging)"
echo "   ├─ STAGING_DB_PASSWORD"
echo "   ├─ STAGING_REDIS_PASSWORD"
echo "   ├─ PROD_DB_USER (smarthr360_prod)"
echo "   ├─ PROD_DB_PASSWORD"
echo "   └─ PROD_REDIS_PASSWORD"
echo ""

echo "   For local Kubernetes:"
echo "   └─ KUBE_CONFIG (base64 encoded ~/.kube/config)"
echo ""

echo "   For AWS EKS (if using):"
echo "   ├─ AWS_ACCESS_KEY_ID"
echo "   ├─ AWS_SECRET_ACCESS_KEY"
echo "   ├─ AWS_REGION"
echo "   └─ EKS_CLUSTER_NAME"
echo ""

echo "   Optional (monitoring):"
echo "   ├─ ELASTIC_APM_SECRET_TOKEN"
echo "   ├─ SENTRY_DSN"
echo "   ├─ SLACK_WEBHOOK_URL"
echo "   └─ CODECOV_TOKEN"
echo ""

# Local Kubernetes helper
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}For local Kubernetes (Docker Desktop/Minikube):${NC}"
echo ""
echo "Run this to copy your kubeconfig to clipboard:"
echo ""
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "  cat ~/.kube/config | base64 | pbcopy"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "  cat ~/.kube/config | base64 | xclip -selection clipboard"
else
    echo "  cat ~/.kube/config | base64"
fi
echo ""
echo "Then add as KUBE_CONFIG secret in GitHub"
echo ""

echo -e "${GREEN}"
echo "════════════════════════════════════════════════════════════"
echo "                    Next Steps"
echo "════════════════════════════════════════════════════════════"
echo -e "${NC}"

echo "After adding secrets to GitHub:"
echo ""
echo "1. Install ArgoCD:"
echo "   ./scripts/install-argocd.sh"
echo ""
echo "2. Deploy applications:"
echo "   ./scripts/deploy-argocd-apps.sh"
echo ""
echo "3. Verify setup:"
echo "   ./scripts/verify-pipeline.sh"
echo ""
echo "4. Test the pipeline:"
echo "   git checkout -b feature/test"
echo "   git push origin feature/test"
echo ""

echo "For detailed instructions, see: SETUP_GUIDE.md"
