#!/bin/bash
# Quick Verification Script
# This script checks if the CI/CD pipeline is working correctly

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
echo "║        SmartHR360 - CI/CD Pipeline Verification           ║"
echo "╔════════════════════════════════════════════════════════════╗"
echo -e "${NC}"

ERRORS=0

# Check kubectl
echo -e "${YELLOW}Checking kubectl...${NC}"
if command -v kubectl &> /dev/null; then
    echo -e "${GREEN}✓ kubectl is installed${NC}"
else
    echo -e "${RED}✗ kubectl not found${NC}"
    ((ERRORS++))
fi

# Check cluster connection
echo ""
echo -e "${YELLOW}Checking Kubernetes cluster connection...${NC}"
if kubectl cluster-info &> /dev/null; then
    CLUSTER_INFO=$(kubectl cluster-info | head -n 1)
    echo -e "${GREEN}✓ Connected to cluster${NC}"
    echo "  $CLUSTER_INFO"
else
    echo -e "${RED}✗ Cannot connect to Kubernetes cluster${NC}"
    ((ERRORS++))
fi

# Check ArgoCD installation
echo ""
echo -e "${YELLOW}Checking ArgoCD installation...${NC}"
if kubectl get namespace argocd &> /dev/null; then
    echo -e "${GREEN}✓ ArgoCD namespace exists${NC}"

    # Check ArgoCD pods
    READY_PODS=$(kubectl get pods -n argocd --field-selector=status.phase=Running --no-headers 2>/dev/null | wc -l | tr -d ' ')
    TOTAL_PODS=$(kubectl get pods -n argocd --no-headers 2>/dev/null | wc -l | tr -d ' ')

    if [ "$READY_PODS" -eq "$TOTAL_PODS" ] && [ "$TOTAL_PODS" -gt 0 ]; then
        echo -e "${GREEN}✓ All ArgoCD pods are running ($READY_PODS/$TOTAL_PODS)${NC}"
    else
        echo -e "${YELLOW}! Some ArgoCD pods are not ready ($READY_PODS/$TOTAL_PODS)${NC}"
    fi
else
    echo -e "${RED}✗ ArgoCD namespace not found${NC}"
    echo "  Run: ./scripts/install-argocd.sh"
    ((ERRORS++))
fi

# Check ArgoCD applications
echo ""
echo -e "${YELLOW}Checking ArgoCD applications...${NC}"
if kubectl get applications -n argocd &> /dev/null; then
    APP_COUNT=$(kubectl get applications -n argocd --no-headers 2>/dev/null | wc -l | tr -d ' ')

    if [ "$APP_COUNT" -gt 0 ]; then
        echo -e "${GREEN}✓ Found $APP_COUNT ArgoCD application(s)${NC}"

        # Check each expected application
        for APP in smarthr360-dev smarthr360-staging smarthr360-production; do
            if kubectl get application "$APP" -n argocd &> /dev/null; then
                HEALTH=$(kubectl get application "$APP" -n argocd -o jsonpath='{.status.health.status}' 2>/dev/null || echo "Unknown")
                SYNC=$(kubectl get application "$APP" -n argocd -o jsonpath='{.status.sync.status}' 2>/dev/null || echo "Unknown")

                if [ "$HEALTH" == "Healthy" ] && [ "$SYNC" == "Synced" ]; then
                    echo -e "${GREEN}  ✓ $APP: Health=$HEALTH, Sync=$SYNC${NC}"
                else
                    echo -e "${YELLOW}  ! $APP: Health=$HEALTH, Sync=$SYNC${NC}"
                fi
            else
                echo -e "${RED}  ✗ $APP not found${NC}"
            fi
        done
    else
        echo -e "${YELLOW}! No ArgoCD applications found${NC}"
        echo "  Run: ./scripts/deploy-argocd-apps.sh"
    fi
else
    echo -e "${RED}✗ Cannot query ArgoCD applications${NC}"
    ((ERRORS++))
fi

# Check namespaces
echo ""
echo -e "${YELLOW}Checking application namespaces...${NC}"
for NS in smarthr360-dev smarthr360-staging smarthr360; do
    if kubectl get namespace "$NS" &> /dev/null; then
        POD_COUNT=$(kubectl get pods -n "$NS" --no-headers 2>/dev/null | wc -l | tr -d ' ')
        RUNNING_COUNT=$(kubectl get pods -n "$NS" --field-selector=status.phase=Running --no-headers 2>/dev/null | wc -l | tr -d ' ')

        if [ "$POD_COUNT" -gt 0 ]; then
            if [ "$RUNNING_COUNT" -eq "$POD_COUNT" ]; then
                echo -e "${GREEN}  ✓ $NS: All pods running ($RUNNING_COUNT/$POD_COUNT)${NC}"
            else
                echo -e "${YELLOW}  ! $NS: Some pods not running ($RUNNING_COUNT/$POD_COUNT)${NC}"
            fi
        else
            echo -e "${YELLOW}  ! $NS: No pods found${NC}"
        fi
    else
        echo -e "${YELLOW}  ! $NS: Namespace not found${NC}"
    fi
done

# Check secrets
echo ""
echo -e "${YELLOW}Checking required secrets...${NC}"
for NS in smarthr360-dev smarthr360-staging smarthr360; do
    if kubectl get namespace "$NS" &> /dev/null; then
        if kubectl get secret -n "$NS" 2>/dev/null | grep -q "smarthr360-secrets"; then
            echo -e "${GREEN}  ✓ $NS: Application secrets exist${NC}"
        else
            echo -e "${YELLOW}  ! $NS: Application secrets not found${NC}"
        fi

        if kubectl get secret -n "$NS" 2>/dev/null | grep -q "ghcr-secret"; then
            echo -e "${GREEN}  ✓ $NS: Registry credentials exist${NC}"
        else
            echo -e "${YELLOW}  ! $NS: Registry credentials not found${NC}"
        fi
    fi
done

# Check ingress
echo ""
echo -e "${YELLOW}Checking ingress resources...${NC}"
for NS in smarthr360-dev smarthr360-staging smarthr360; do
    if kubectl get namespace "$NS" &> /dev/null; then
        INGRESS_COUNT=$(kubectl get ingress -n "$NS" --no-headers 2>/dev/null | wc -l | tr -d ' ')
        if [ "$INGRESS_COUNT" -gt 0 ]; then
            echo -e "${GREEN}  ✓ $NS: Ingress configured${NC}"
        else
            echo -e "${YELLOW}  ! $NS: No ingress found${NC}"
        fi
    fi
done

# Check GitHub Actions
echo ""
echo -e "${YELLOW}Checking GitHub workflows...${NC}"
if [ -f ".github/workflows/ci.yml" ]; then
    echo -e "${GREEN}✓ CI workflow exists${NC}"
else
    echo -e "${RED}✗ CI workflow not found${NC}"
    ((ERRORS++))
fi

if [ -f ".github/workflows/cd-staging.yml" ]; then
    echo -e "${GREEN}✓ CD Staging workflow exists${NC}"
else
    echo -e "${RED}✗ CD Staging workflow not found${NC}"
    ((ERRORS++))
fi

if [ -f ".github/workflows/cd-production.yml" ]; then
    echo -e "${GREEN}✓ CD Production workflow exists${NC}"
else
    echo -e "${RED}✗ CD Production workflow not found${NC}"
    ((ERRORS++))
fi

# Check deployment scripts
echo ""
echo -e "${YELLOW}Checking deployment scripts...${NC}"
for SCRIPT in blue-green-deploy.sh canary-deploy.sh rollback.sh; do
    if [ -f "scripts/$SCRIPT" ] && [ -x "scripts/$SCRIPT" ]; then
        echo -e "${GREEN}✓ scripts/$SCRIPT is executable${NC}"
    else
        echo -e "${YELLOW}! scripts/$SCRIPT not found or not executable${NC}"
    fi
done

# Check kustomize overlays
echo ""
echo -e "${YELLOW}Checking Kustomize overlays...${NC}"
for ENV in dev staging production; do
    if [ -f "k8s/overlays/$ENV/kustomization.yaml" ]; then
        echo -e "${GREEN}✓ k8s/overlays/$ENV/kustomization.yaml exists${NC}"
    else
        echo -e "${RED}✗ k8s/overlays/$ENV/kustomization.yaml not found${NC}"
        ((ERRORS++))
    fi
done

# Summary
echo ""
echo -e "${BLUE}"
echo "════════════════════════════════════════════════════════════"
echo -e "${NC}"

if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed! CI/CD pipeline is ready.${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Configure GitHub secrets (see SETUP_GUIDE.md)"
    echo "2. Push code to trigger CI/CD pipeline"
    echo "3. Monitor deployments in ArgoCD UI"
else
    echo -e "${YELLOW}⚠ Found $ERRORS issue(s). Please review above.${NC}"
    echo ""
    echo "Setup steps:"
    echo "1. Install ArgoCD: ./scripts/install-argocd.sh"
    echo "2. Deploy applications: ./scripts/deploy-argocd-apps.sh"
    echo "3. Configure secrets (see SETUP_GUIDE.md)"
fi

echo ""
echo "For detailed setup instructions, see: SETUP_GUIDE.md"
echo "For quick commands, see: docs/CI_CD_QUICK_REFERENCE.md"
