#!/bin/bash

# SmartHR360 Development Environment Setup Script
# This script sets up a complete development environment for the SmartHR360 project

set -e  # Exit on error

echo "🚀 SmartHR360 Development Environment Setup"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Check Python version
print_info "Checking Python version..."
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed. Please install Python 3.11 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
print_success "Python $PYTHON_VERSION detected"

# Create virtual environment
print_info "Creating virtual environment..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    print_success "Virtual environment created"
else
    print_info "Virtual environment already exists"
fi

# Activate virtual environment
print_info "Activating virtual environment..."
source .venv/bin/activate
print_success "Virtual environment activated"

# Upgrade pip
print_info "Upgrading pip..."
pip install --upgrade pip --quiet
print_success "pip upgraded"

# Install dependencies
print_info "Installing Python dependencies..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    print_success "Production dependencies installed"
else
    print_error "requirements.txt not found"
    exit 1
fi

if [ -f "requirements-dev.txt" ]; then
    pip install -r requirements-dev.txt
    print_success "Development dependencies installed"
fi

if [ -f "requirements_ml.txt" ]; then
    pip install -r requirements_ml.txt
    print_success "ML dependencies installed"
fi

# Create .env file if it doesn't exist
print_info "Setting up environment variables..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        print_success ".env file created from .env.example"
        print_info "Please update .env with your actual configuration"
    else
        print_error ".env.example not found"
    fi
else
    print_info ".env file already exists"
fi

# Run migrations
print_info "Running database migrations..."
python manage.py migrate --settings=config.settings.development
print_success "Database migrations completed"

# Create superuser prompt
echo ""
read -p "Do you want to create a superuser? (y/n): " create_superuser
if [ "$create_superuser" = "y" ] || [ "$create_superuser" = "Y" ]; then
    python manage.py createsuperuser --settings=config.settings.development
    print_success "Superuser created"
fi

# Seed future skills data
echo ""
read -p "Do you want to seed Future Skills data? (y/n): " seed_data
if [ "$seed_data" = "y" ] || [ "$seed_data" = "Y" ]; then
    print_info "Seeding Future Skills data..."
    python manage.py seed_future_skills --settings=config.settings.development
    print_success "Future Skills data seeded"
fi

# Install pre-commit hooks
echo ""
read -p "Do you want to install pre-commit hooks? (y/n): " install_hooks
if [ "$install_hooks" = "y" ] || [ "$install_hooks" = "Y" ]; then
    print_info "Installing pre-commit hooks..."
    pip install pre-commit
    pre-commit install
    print_success "Pre-commit hooks installed"
fi

# Run tests
echo ""
read -p "Do you want to run tests to verify setup? (y/n): " run_tests
if [ "$run_tests" = "y" ] || [ "$run_tests" = "Y" ]; then
    print_info "Running tests..."
    python manage.py check --settings=config.settings.development
    pytest future_skills/tests/ -v --tb=short
    print_success "Tests completed"
fi

# Final summary
echo ""
echo "=========================================="
print_success "Development environment setup complete!"
echo ""
echo "Next steps:"
echo "  1. Activate virtual environment: source .venv/bin/activate"
echo "  2. Update .env with your configuration"
echo "  3. Run development server: python manage.py runserver"
echo "  4. Access admin panel: http://127.0.0.1:8000/admin/"
echo "  5. Access API docs: http://127.0.0.1:8000/api/docs/"
echo ""
echo "Useful commands:"
echo "  - Run tests: pytest"
echo "  - Run specific tests: pytest tests/integration/"
echo "  - Coverage report: pytest --cov=future_skills --cov-report=html"
echo "  - Code formatting: black ."
echo "  - Linting: flake8"
echo "  - Pre-commit check: pre-commit run --all-files"
echo "=========================================="
