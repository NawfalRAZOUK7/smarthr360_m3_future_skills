#!/bin/bash

##############################################################################
# Blue-Green Deployment Script for SmartHR360
#
# This script performs a blue-green deployment by creating a new "green"
# deployment alongside the existing "blue" deployment, then switching traffic
# after validation.
##############################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="${NAMESPACE:-smarthr360}"
NEW_VERSION="${1}"
CURRENT_COLOR=""
NEW_COLOR=""

if [ -z "$NEW_VERSION" ]; then
    echo -e "${RED}Error: Version tag required${NC}"
    echo "Usage: $0 <version-tag>"
    echo "Example: $0 v1.2.0"
    exit 1
fi

echo -e "${BLUE}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     SmartHR360 Blue-Green Deployment                ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Version: ${NEW_VERSION}${NC}"
echo -e "${GREEN}Namespace: ${NAMESPACE}${NC}"
echo ""

# Function to get current active color
get_current_color() {
    # Check which color is currently active in service selector
    CURRENT_COLOR=$(kubectl get service smarthr360-api -n $NAMESPACE -o jsonpath='{.spec.selector.color}' 2>/dev/null || echo "")

    if [ -z "$CURRENT_COLOR" ]; then
        # No color label exists, assume blue is current
        CURRENT_COLOR="blue"
        # Add color label to current deployment
        kubectl patch deployment smarthr360-api -n $NAMESPACE -p '{"spec":{"template":{"metadata":{"labels":{"color":"blue"}}}}}' || true
    fi

    echo "$CURRENT_COLOR"
}

# Function to determine new color
get_new_color() {
    if [ "$CURRENT_COLOR" == "blue" ]; then
        echo "green"
    else
        echo "blue"
    fi
}

# Get colors
CURRENT_COLOR=$(get_current_color)
NEW_COLOR=$(get_new_color)

echo -e "${YELLOW}Current active color: ${CURRENT_COLOR}${NC}"
echo -e "${YELLOW}New deployment color: ${NEW_COLOR}${NC}"
echo ""

# Step 1: Create new deployment with new version
echo -e "${BLUE}Step 1: Creating ${NEW_COLOR} deployment...${NC}"

kubectl get deployment smarthr360-api-${CURRENT_COLOR} -n $NAMESPACE -o yaml 2>/dev/null || \
    kubectl get deployment smarthr360-api -n $NAMESPACE -o yaml | \
    sed "s/name: smarthr360-api/name: smarthr360-api-${CURRENT_COLOR}/" | \
    kubectl apply -f -

# Create new green/blue deployment
kubectl get deployment smarthr360-api-${CURRENT_COLOR} -n $NAMESPACE -o yaml | \
    sed "s/name: smarthr360-api-${CURRENT_COLOR}/name: smarthr360-api-${NEW_COLOR}/" | \
    sed "s/color: ${CURRENT_COLOR}/color: ${NEW_COLOR}/" | \
    sed "s|image: .*/smarthr360-api:.*|image: ghcr.io/your-org/smarthr360-api:${NEW_VERSION}|" | \
    kubectl apply -f -

echo -e "${GREEN}✅ ${NEW_COLOR} deployment created${NC}"

# Step 2: Wait for new deployment to be ready
echo -e "${BLUE}Step 2: Waiting for ${NEW_COLOR} deployment to be ready...${NC}"

kubectl rollout status deployment/smarthr360-api-${NEW_COLOR} -n $NAMESPACE --timeout=10m

echo -e "${GREEN}✅ ${NEW_COLOR} deployment is ready${NC}"

# Step 3: Run smoke tests on new deployment
echo -e "${BLUE}Step 3: Running smoke tests on ${NEW_COLOR} deployment...${NC}"

# Port forward to new deployment for testing
NEW_POD=$(kubectl get pod -n $NAMESPACE -l app=smarthr360-api,color=${NEW_COLOR} -o jsonpath='{.items[0].metadata.name}')
kubectl port-forward -n $NAMESPACE $NEW_POD 8001:8000 &
PF_PID=$!

sleep 5

# Test endpoints
SMOKE_TEST_FAILED=0

echo "Testing health endpoint..."
if ! curl -f http://localhost:8001/api/health/ -s > /dev/null; then
    echo -e "${RED}❌ Health check failed${NC}"
    SMOKE_TEST_FAILED=1
else
    echo -e "${GREEN}✅ Health check passed${NC}"
fi

echo "Testing skills endpoint..."
if ! curl -f http://localhost:8001/api/skills/ -s > /dev/null; then
    echo -e "${RED}❌ Skills endpoint failed${NC}"
    SMOKE_TEST_FAILED=1
else
    echo -e "${GREEN}✅ Skills endpoint passed${NC}"
fi

# Cleanup port forward
kill $PF_PID 2>/dev/null || true

if [ $SMOKE_TEST_FAILED -eq 1 ]; then
    echo -e "${RED}❌ Smoke tests failed. Aborting deployment.${NC}"
    echo -e "${YELLOW}Cleaning up ${NEW_COLOR} deployment...${NC}"
    kubectl delete deployment smarthr360-api-${NEW_COLOR} -n $NAMESPACE
    exit 1
fi

echo -e "${GREEN}✅ All smoke tests passed${NC}"

# Step 4: Switch traffic
echo -e "${BLUE}Step 4: Switching traffic to ${NEW_COLOR} deployment...${NC}"
read -p "Continue with traffic switch? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo -e "${YELLOW}Deployment cancelled by user${NC}"
    echo -e "${YELLOW}${NEW_COLOR} deployment is running but not receiving traffic${NC}"
    echo -e "${YELLOW}To switch manually: kubectl patch service smarthr360-api -n $NAMESPACE -p '{\"spec\":{\"selector\":{\"color\":\"${NEW_COLOR}\"}}}'${NC}"
    exit 0
fi

# Update service to point to new color
kubectl patch service smarthr360-api -n $NAMESPACE -p "{\"spec\":{\"selector\":{\"color\":\"${NEW_COLOR}\"}}}"

echo -e "${GREEN}✅ Traffic switched to ${NEW_COLOR}${NC}"

# Step 5: Monitor new deployment
echo -e "${BLUE}Step 5: Monitoring new deployment for 2 minutes...${NC}"

for i in {1..12}; do
    echo -n "."
    sleep 10

    # Check for errors
    ERROR_COUNT=$(kubectl logs -n $NAMESPACE -l color=${NEW_COLOR} --since=30s | grep ERROR | wc -l || echo "0")
    if [ $ERROR_COUNT -gt 5 ]; then
        echo ""
        echo -e "${YELLOW}⚠️  Warning: High error count detected: $ERROR_COUNT${NC}"
    fi
done

echo ""
echo -e "${GREEN}✅ Monitoring complete${NC}"

# Step 6: Cleanup old deployment
echo -e "${BLUE}Step 6: Cleaning up ${CURRENT_COLOR} deployment...${NC}"
read -p "Remove old ${CURRENT_COLOR} deployment? (yes/no): " CLEANUP

if [ "$CLEANUP" == "yes" ]; then
    kubectl delete deployment smarthr360-api-${CURRENT_COLOR} -n $NAMESPACE
    echo -e "${GREEN}✅ ${CURRENT_COLOR} deployment removed${NC}"
else
    echo -e "${YELLOW}${CURRENT_COLOR} deployment kept for manual cleanup${NC}"
fi

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     Blue-Green Deployment Complete!                  ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Active deployment: ${NEW_COLOR}${NC}"
echo -e "${GREEN}Version: ${NEW_VERSION}${NC}"
echo ""
echo -e "${YELLOW}To rollback:${NC}"
echo -e "${YELLOW}kubectl patch service smarthr360-api -n $NAMESPACE -p '{\"spec\":{\"selector\":{\"color\":\"${CURRENT_COLOR}\"}}}'${NC}"
