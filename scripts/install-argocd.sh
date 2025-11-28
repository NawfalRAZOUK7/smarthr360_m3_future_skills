#!/bin/bash
# ArgoCD Installation and Setup Script
# This script installs ArgoCD and sets up initial configuration

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
echo "║          SmartHR360 - ArgoCD Installation Script          ║"
echo "╔════════════════════════════════════════════════════════════╗"
echo -e "${NC}"

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}✗ kubectl not found. Please install kubectl first.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ kubectl found${NC}"

# Check cluster connection
if ! kubectl cluster-info &> /dev/null; then
    echo -e "${RED}✗ Cannot connect to Kubernetes cluster.${NC}"
    echo "Please configure kubectl to connect to your cluster."
    exit 1
fi
echo -e "${GREEN}✓ Connected to Kubernetes cluster${NC}"

# Step 1: Install ArgoCD
echo ""
echo -e "${BLUE}Step 1: Installing ArgoCD...${NC}"

if kubectl get namespace argocd &> /dev/null; then
    echo -e "${YELLOW}ArgoCD namespace already exists. Skipping creation.${NC}"
else
    kubectl create namespace argocd
    echo -e "${GREEN}✓ Created argocd namespace${NC}"
fi

echo "Installing ArgoCD components..."
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

echo "Waiting for ArgoCD to be ready (this may take 2-3 minutes)..."
kubectl wait --for=condition=ready pod -n argocd -l app.kubernetes.io/name=argocd-server --timeout=300s

echo -e "${GREEN}✓ ArgoCD installed successfully${NC}"

# Step 2: Get initial admin password
echo ""
echo -e "${BLUE}Step 2: Retrieving admin credentials...${NC}"

PASSWORD=$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d)

echo -e "${GREEN}✓ Admin credentials:${NC}"
echo "   Username: admin"
echo "   Password: $PASSWORD"
echo ""
echo -e "${YELLOW}Please save these credentials securely!${NC}"
echo "You should change the password after first login."

# Step 3: Set up port forwarding
echo ""
echo -e "${BLUE}Step 3: Setting up access to ArgoCD UI...${NC}"

echo "Starting port-forward in background..."
kubectl port-forward svc/argocd-server -n argocd 8080:443 > /dev/null 2>&1 &
PORT_FORWARD_PID=$!

sleep 3

echo -e "${GREEN}✓ ArgoCD UI is now accessible at: https://localhost:8080${NC}"
echo ""
echo -e "${YELLOW}Note: You may see a certificate warning - this is expected for local setup.${NC}"
echo "Accept the warning to proceed."

# Step 4: Install ArgoCD CLI (optional)
echo ""
echo -e "${BLUE}Step 4: ArgoCD CLI installation (optional)${NC}"
echo "Would you like to install the ArgoCD CLI? (y/n)"
read -r INSTALL_CLI

if [[ "$INSTALL_CLI" =~ ^[Yy]$ ]]; then
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            echo "Installing ArgoCD CLI via Homebrew..."
            brew install argocd
            echo -e "${GREEN}✓ ArgoCD CLI installed${NC}"
        else
            echo -e "${YELLOW}Homebrew not found. Installing manually...${NC}"
            curl -sSL -o /usr/local/bin/argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-darwin-amd64
            chmod +x /usr/local/bin/argocd
            echo -e "${GREEN}✓ ArgoCD CLI installed${NC}"
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        echo "Installing ArgoCD CLI for Linux..."
        sudo curl -sSL -o /usr/local/bin/argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
        sudo chmod +x /usr/local/bin/argocd
        echo -e "${GREEN}✓ ArgoCD CLI installed${NC}"
    else
        echo -e "${YELLOW}Unsupported OS for automatic installation.${NC}"
        echo "Please install manually from: https://argo-cd.readthedocs.io/en/stable/cli_installation/"
    fi

    # Login with CLI
    echo ""
    echo "Logging in to ArgoCD CLI..."
    sleep 2
    argocd login localhost:8080 --username admin --password "$PASSWORD" --insecure

    echo ""
    echo -e "${YELLOW}To change admin password:${NC}"
    echo "  argocd account update-password"
else
    echo "Skipping CLI installation."
fi

# Step 5: Install ArgoCD Notifications (optional)
echo ""
echo -e "${BLUE}Step 5: ArgoCD Notifications (optional)${NC}"
echo "Would you like to install ArgoCD Notifications for Slack integration? (y/n)"
read -r INSTALL_NOTIFICATIONS

if [[ "$INSTALL_NOTIFICATIONS" =~ ^[Yy]$ ]]; then
    echo "Installing ArgoCD Notifications..."
    kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj-labs/argocd-notifications/stable/manifests/install.yaml

    echo ""
    echo -e "${YELLOW}To configure Slack notifications, run:${NC}"
    echo "  kubectl create secret generic argocd-notifications-secret -n argocd \\"
    echo "    --from-literal=slack-token=<your-slack-webhook-url>"

    echo -e "${GREEN}✓ ArgoCD Notifications installed${NC}"
else
    echo "Skipping notifications installation."
fi

# Summary
echo ""
echo -e "${GREEN}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║              ArgoCD Installation Complete!                 ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo "Next steps:"
echo "1. Access ArgoCD UI: https://localhost:8080"
echo "2. Login with username 'admin' and the password shown above"
echo "3. Change the admin password after first login"
echo "4. Deploy ArgoCD applications:"
echo "   kubectl apply -f argocd/project-production.yaml"
echo "   kubectl apply -f argocd/application-dev.yaml"
echo "   kubectl apply -f argocd/application-staging.yaml"
echo "   kubectl apply -f argocd/application-production.yaml"
echo ""
echo "For detailed instructions, see: SETUP_GUIDE.md"
echo ""
echo -e "${YELLOW}Port-forward is running in background (PID: $PORT_FORWARD_PID)${NC}"
echo "To stop it later: kill $PORT_FORWARD_PID"
echo ""
echo "Or run in foreground:"
echo "  kubectl port-forward svc/argocd-server -n argocd 8080:443"
