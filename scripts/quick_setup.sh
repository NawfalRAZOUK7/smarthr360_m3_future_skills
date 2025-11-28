#!/bin/bash
# ==============================================================================
# Quick Setup Script for SmartHR360 Deployment
# ==============================================================================

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}"
cat << "EOF"
╔═══════════════════════════════════════════════════════════════╗
║              SmartHR360 Quick Setup                          ║
║              Interactive Configuration                        ║
╚═══════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

# Collect information
echo -e "${GREEN}Step 1: Container Registry Configuration${NC}"
echo ""
read -p "Container Registry (e.g., docker.io, ghcr.io, gcr.io): " REGISTRY
REGISTRY=${REGISTRY:-docker.io}

read -p "Registry Username/Namespace: " USERNAME
USERNAME=${USERNAME:-your-username}

read -p "Image Tag (default: v1.0.0): " IMAGE_TAG
IMAGE_TAG=${IMAGE_TAG:-v1.0.0}

echo ""
echo -e "${GREEN}Step 2: Domain Configuration${NC}"
echo ""
read -p "Your Domain Name (e.g., example.com): " DOMAIN
DOMAIN=${DOMAIN:-smarthr360.com}

read -p "Admin Email: " ADMIN_EMAIL
ADMIN_EMAIL=${ADMIN_EMAIL:-admin@${DOMAIN}}

echo ""
echo -e "${GREEN}Step 3: What would you like to do?${NC}"
echo ""
echo "1) Generate secrets only"
echo "2) Build Docker images only"
echo "3) Full deployment preparation (secrets + build + push)"
echo "4) Update manifests only (with existing images)"
echo ""
read -p "Enter your choice (1-4): " CHOICE

# Export variables
export DOCKER_REGISTRY="$REGISTRY"
export DOCKER_USERNAME="$USERNAME"
export IMAGE_TAG="$IMAGE_TAG"
export DOMAIN="$DOMAIN"
export ADMIN_EMAIL="$ADMIN_EMAIL"

# Execute based on choice
case $CHOICE in
    1)
        echo ""
        echo -e "${BLUE}Generating secrets...${NC}"
        ./scripts/prepare_deployment.sh --skip-build --skip-push
        ;;
    2)
        echo ""
        echo -e "${BLUE}Building Docker images...${NC}"
        ./scripts/prepare_deployment.sh --skip-secrets --skip-push
        ;;
    3)
        echo ""
        echo -e "${BLUE}Running full deployment preparation...${NC}"
        ./scripts/prepare_deployment.sh
        ;;
    4)
        echo ""
        echo -e "${BLUE}Updating manifests only...${NC}"
        ./scripts/prepare_deployment.sh --skip-secrets --skip-build --skip-push
        ;;
    *)
        echo -e "${YELLOW}Invalid choice. Exiting.${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}✅ Setup completed!${NC}"
echo ""
echo "Next steps:"
echo "1. Review the generated files (especially .secrets.env)"
echo "2. Check DEPLOYMENT_CHECKLIST.md for deployment instructions"
echo "3. Deploy to your Kubernetes cluster"
echo ""
