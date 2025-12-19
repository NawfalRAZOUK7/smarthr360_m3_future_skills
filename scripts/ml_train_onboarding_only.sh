#!/bin/bash
# ml_train.sh - Onboarding and training entrypoint for ML workflows (local/dev)
# Modular, user-friendly onboarding for ML training and prediction

set -e

# --- Color Variables ---
RED="\033[0;31m"
GREEN="\033[0;32m"
YELLOW="\033[1;33m"
BLUE="\033[0;34m"
CYAN="\033[0;36m"
NC="\033[0m" # No Color

# --- Help Message ---
show_help() {
  echo -e "${CYAN}Usage:${NC} $0 [options]"
  echo -e "\nOptions:"
  echo -e "  --help, -h         Show this help message and exit"
  echo -e "\nThis script sets up onboarding for ML training and prediction workflows."
  echo -e "It ensures secrets.env, .env, and required directories are present, and checks for a Python virtual environment."
  echo -e "\n${YELLOW}Docker users:${NC} For containerized onboarding, use ${BLUE}scripts/docker-setup.sh${NC} instead."
}

if [[ "$1" == "--help" || "$1" == "-h" ]]; then
  show_help
  exit 0
fi

# --- Virtual Environment Check ---
if [[ -z "$VIRTUAL_ENV" ]]; then
  echo -e "${YELLOW}Warning:${NC} You are not in a Python virtual environment."
  echo -e "It's recommended to activate your venv before running ML training."
  read -p "Continue anyway? (y/N): " cont
  if [[ ! "$cont" =~ ^[Yy]$ ]]; then
    echo -e "${RED}Aborting.${NC}"
    exit 1
  fi
else
  echo -e "${GREEN}Virtual environment detected:${NC} $VIRTUAL_ENV"
fi

# --- Onboarding: secrets.env ---
if [[ ! -f "secrets.env" ]]; then
  if [[ -f "secrets.example" ]]; then
    cp secrets.example secrets.env
    echo -e "${YELLOW}Created secrets.env from secrets.example. Please edit secrets.env with your ML secrets (e.g., S3, API keys).${NC}"
  else
    echo -e "${RED}Missing secrets.env and secrets.example! Please provide ML secrets for training/prediction.${NC}"
  fi
else
  echo -e "${GREEN}secrets.env found.${NC}"
fi

# --- Onboarding: .env ---
if [[ ! -f ".env" ]]; then
  if [[ -f ".env.example" ]]; then
    cp .env.example .env
    echo -e "${YELLOW}Created .env from .env.example. Please edit .env with required environment variables for ML workflows.${NC}"
  else
    echo -e "${RED}Missing .env and .env.example! Please provide environment variables for ML workflows.${NC}"
  fi
else
  echo -e "${GREEN}.env found.${NC}"
fi

# --- Ensure Required Directories ---
for dir in artifacts models results datasets; do
  if [[ ! -d "$dir" ]]; then
    mkdir -p "$dir"
    echo -e "${YELLOW}Created missing directory: $dir${NC}"
  else
    echo -e "${GREEN}Directory exists: $dir${NC}"
  fi
done

# --- ML Training Logic ---
echo -e "${CYAN}Starting ML training...${NC}"
# Example: Replace with your actual ML training command
python3 -m ml.train "$@"
status=$?
if [[ $status -eq 0 ]]; then
  echo -e "${GREEN}ML training completed successfully.${NC}"
else
  echo -e "${RED}ML training failed with exit code $status.${NC}"
  exit $status
fi
