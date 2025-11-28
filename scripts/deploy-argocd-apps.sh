#!/bin/bash
# Deploy ArgoCD Applications Script
# This script deploys all ArgoCD applications to your cluster

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
echo "║     SmartHR360 - Deploy ArgoCD Applications Script        ║"
echo "╔════════════════════════════════════════════════════════════╗"
echo -e "${NC}"

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}✗ kubectl not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ kubectl found${NC}"

# Check if ArgoCD is installed
if ! kubectl get namespace argocd &> /dev/null; then
    echo -e "${RED}✗ ArgoCD namespace not found${NC}"
    echo "Please install ArgoCD first: ./scripts/install-argocd.sh"
    exit 1
fi
echo -e "${GREEN}✓ ArgoCD is installed${NC}"

# Check if argocd CLI is available
if command -v argocd &> /dev/null; then
    HAS_CLI=true
    echo -e "${GREEN}✓ ArgoCD CLI found${NC}"
else
    HAS_CLI=false
    echo -e "${YELLOW}! ArgoCD CLI not found (optional)${NC}"
fi

# Step 1: Deploy Production Project
echo ""
echo -e "${BLUE}Step 1: Deploying Production Project (RBAC and policies)...${NC}"

if kubectl apply -f argocd/project-production.yaml; then
    echo -e "${GREEN}✓ Production project deployed${NC}"
else
    echo -e "${RED}✗ Failed to deploy production project${NC}"
    exit 1
fi

# Wait a moment for project to be created
sleep 2

# Step 2: Deploy Applications
echo ""
echo -e "${BLUE}Step 2: Deploying ArgoCD Applications...${NC}"

# Dev Application
echo ""
echo -e "${YELLOW}Deploying Dev application...${NC}"
if kubectl apply -f argocd/application-dev.yaml; then
    echo -e "${GREEN}✓ Dev application deployed${NC}"
else
    echo -e "${RED}✗ Failed to deploy dev application${NC}"
fi

# Staging Application
echo ""
echo -e "${YELLOW}Deploying Staging application...${NC}"
if kubectl apply -f argocd/application-staging.yaml; then
    echo -e "${GREEN}✓ Staging application deployed${NC}"
else
    echo -e "${RED}✗ Failed to deploy staging application${NC}"
fi

# Production Application
echo ""
echo -e "${YELLOW}Deploying Production application...${NC}"
if kubectl apply -f argocd/application-production.yaml; then
    echo -e "${GREEN}✓ Production application deployed${NC}"
else
    echo -e "${RED}✗ Failed to deploy production application${NC}"
fi

# Step 3: Verify deployment
echo ""
echo -e "${BLUE}Step 3: Verifying applications...${NC}"

sleep 3

if $HAS_CLI; then
    echo ""
    echo "Application status:"
    argocd app list
else
    echo ""
    kubectl get applications -n argocd
fi

# Step 4: Initial sync
echo ""
echo -e "${BLUE}Step 4: Initial synchronization${NC}"
echo ""
echo "ArgoCD applications are now deployed but not yet synced."
echo "You need to perform an initial sync for each application."
echo ""

if $HAS_CLI; then
    echo -e "${YELLOW}Would you like to sync applications now? (y/n)${NC}"
    read -r DO_SYNC

    if [[ "$DO_SYNC" =~ ^[Yy]$ ]]; then
        echo ""
        echo "Syncing dev application..."
        argocd app sync smarthr360-dev

        echo ""
        echo "Syncing staging application..."
        argocd app sync smarthr360-staging

        echo ""
        echo -e "${YELLOW}Production requires manual approval.${NC}"
        echo "To sync production when ready:"
        echo "  argocd app sync smarthr360-production"

        echo ""
        echo -e "${GREEN}✓ Dev and Staging synced${NC}"
    else
        echo "Skipping sync. Sync manually when ready."
    fi
else
    echo "To sync applications manually:"
    echo ""
    echo "Option 1: Using kubectl"
    echo "  kubectl patch application smarthr360-dev -n argocd \\"
    echo "    --type merge -p '{\"operation\":{\"initiatedBy\":{\"username\":\"admin\"},\"sync\":{}}}'"
    echo ""
    echo "Option 2: Using ArgoCD UI"
    echo "  1. Access https://localhost:8080"
    echo "  2. Click on each application"
    echo "  3. Click SYNC button"
    echo "  4. Click SYNCHRONIZE"
    echo ""
    echo "Option 3: Install ArgoCD CLI"
    echo "  brew install argocd  # macOS"
    echo "  argocd login localhost:8080"
    echo "  argocd app sync smarthr360-dev"
fi

# Step 5: Show next steps
echo ""
echo -e "${GREEN}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║          ArgoCD Applications Deployed!                     ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo "Applications deployed:"
echo "  • smarthr360-dev (namespace: smarthr360-dev)"
echo "  • smarthr360-staging (namespace: smarthr360-staging)"
echo "  • smarthr360-production (namespace: smarthr360)"
echo ""

echo "To monitor application status:"
if $HAS_CLI; then
    echo "  argocd app list"
    echo "  argocd app get smarthr360-dev"
    echo "  argocd app get smarthr360-staging"
else
    echo "  kubectl get applications -n argocd"
    echo "  kubectl describe application smarthr360-dev -n argocd"
fi

echo ""
echo "To view application logs:"
echo "  kubectl logs -n smarthr360-dev -l component=api"
echo "  kubectl logs -n smarthr360-staging -l component=api"
echo ""

echo "To check pod status:"
echo "  kubectl get pods -n smarthr360-dev"
echo "  kubectl get pods -n smarthr360-staging"
echo "  kubectl get pods -n smarthr360"
echo ""

echo "ArgoCD UI: https://localhost:8080"
echo ""

echo -e "${YELLOW}Note: Make sure you have:${NC}"
echo "  1. Configured GitHub secrets for CI/CD workflows"
echo "  2. Created Docker registry credentials"
echo "  3. Set up database secrets"
echo ""
echo "See SETUP_GUIDE.md for detailed instructions."
