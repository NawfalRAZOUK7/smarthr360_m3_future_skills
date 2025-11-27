# SmartHR360 CI/CD and Development Scripts

This directory contains utility scripts to streamline development, testing, and deployment workflows.

## 📋 Available Scripts

### 1. `setup_dev.sh` - Development Environment Setup

Complete setup script for new developers or fresh environment setup.

**Usage:**

```bash
./scripts/setup_dev.sh
```

**Features:**

- Creates and activates virtual environment
- Installs all dependencies (production, dev, ML)
- Creates `.env` from `.env.example`
- Runs database migrations
- Optional: Creates superuser
- Optional: Seeds Future Skills data
- Optional: Installs pre-commit hooks
- Optional: Runs tests to verify setup

---

### 2. `run_tests.sh` - Test Runner

Convenient test execution with various options.

**Usage:**

```bash
./scripts/run_tests.sh [TEST_TYPE] [OPTIONS]
```

**Test Types:**

- `all` - Run all tests with coverage (default)
- `unit` - Unit tests only
- `integration` - Integration tests
- `e2e` - End-to-end tests
- `fast` - Fast tests (exclude slow)
- `ml` - ML-related tests
- `api` - API tests
- `coverage` - Detailed coverage report
- `failed` - Re-run last failed tests
- `specific <path>` - Run specific test

**Examples:**

```bash
./scripts/run_tests.sh                    # All tests
./scripts/run_tests.sh unit               # Unit tests
./scripts/run_tests.sh integration -vv    # Integration with verbose
./scripts/run_tests.sh specific tests/integration/test_prediction_flow.py
```

---

### 3. `docker_build.sh` - Docker Management

Simplifies Docker operations for development and production.

**Usage:**

```bash
./scripts/docker_build.sh [COMMAND] [OPTIONS]
```

**Commands:**

- `dev` - Start development environment
- `prod` - Start production environment
- `build [env]` - Build Docker image
- `stop [env]` - Stop containers
- `restart [env]` - Restart containers
- `logs [service]` - Show service logs
- `shell` - Open shell in web container
- `migrate` - Run migrations in container
- `test` - Run tests in container
- `clean` - Clean all Docker resources
- `status` - Show container status

**Examples:**

```bash
./scripts/docker_build.sh dev             # Start dev environment
./scripts/docker_build.sh logs web        # Show web logs
./scripts/docker_build.sh shell           # Open shell
./scripts/docker_build.sh build prod      # Build production
```

---

### 4. `ml_train.sh` - ML Workflow Management

Manages machine learning model training and evaluation.

**Usage:**

```bash
./scripts/ml_train.sh [COMMAND] [OPTIONS]
```

**Commands:**

- `prepare` - Prepare dataset from database
- `experiment` - Run model experiments
- `evaluate` - Evaluate trained models
- `train [model]` - Train specific model
- `predict <emp_id>` - Generate predictions
- `explainability` - Run explainability analysis
- `dataset-analysis` - Run dataset analysis
- `compare` - Compare model performance
- `monitor` - Check monitoring metrics
- `retrain` - Retrain all models
- `clean` - Clean ML artifacts

**Examples:**

```bash
./scripts/ml_train.sh prepare             # Prepare dataset
./scripts/ml_train.sh experiment          # Run experiments
./scripts/ml_train.sh predict 123         # Predict for employee
./scripts/ml_train.sh compare             # Compare models
```

---

## 🚀 Quick Start

### First Time Setup

```bash
# Clone repository
git clone <repository-url>
cd smarthr360_m3_future_skills

# Run setup script
./scripts/setup_dev.sh

# Activate environment
source .venv/bin/activate

# Start development server
python manage.py runserver
```

### Daily Development Workflow

```bash
# Activate environment
source .venv/bin/activate

# Run fast tests before committing
./scripts/run_tests.sh fast

# Run pre-commit checks
pre-commit run --all-files

# Commit changes
git add .
git commit -m "Your message"
```

### Docker Development

```bash
# Start development environment
./scripts/docker_build.sh dev

# View logs
./scripts/docker_build.sh logs web

# Run migrations
./scripts/docker_build.sh migrate

# Stop environment
./scripts/docker_build.sh stop
```

### ML Workflow

```bash
# Prepare and train models
./scripts/ml_train.sh prepare
./scripts/ml_train.sh experiment

# Evaluate results
./scripts/ml_train.sh compare
./scripts/ml_train.sh explainability

# Make predictions
./scripts/ml_train.sh predict <employee_id>
```

---

## 🔧 Pre-commit Hooks

The project uses pre-commit hooks for code quality. Install with:

```bash
pip install pre-commit
pre-commit install
```

### Available Hooks:

- **Black** - Code formatting
- **isort** - Import sorting
- **Flake8** - Linting
- **Bandit** - Security checks
- **Django checks** - Django validation
- **pydocstyle** - Docstring validation
- **detect-secrets** - Secret detection

### Manual Run:

```bash
# Run all hooks
pre-commit run --all-files

# Run specific hook
pre-commit run black --all-files
```

---

## 📊 CI/CD Pipeline

GitHub Actions workflow (`.github/workflows/ci.yml`) automatically:

1. **Tests**

   - Runs on Python 3.11 and 3.12
   - PostgreSQL service for testing
   - Unit, integration, and E2E tests
   - Coverage reporting to Codecov

2. **Code Quality**

   - Black formatting check
   - Flake8 linting
   - isort import sorting
   - Bandit security scanning
   - Safety dependency checks

3. **Docker**

   - Builds Docker image
   - Tests production configuration

4. **Documentation**
   - Validates documentation structure
   - Checks documentation links

### Workflow Triggers:

- Push to `main` or `develop` branches
- Pull requests to `main` or `develop`

---

## 📝 Environment Variables

Scripts respect these environment variables:

- `DJANGO_SETTINGS_MODULE` - Django settings module
- `DATABASE_URL` - Database connection string
- `DEBUG` - Debug mode flag
- `SECRET_KEY` - Django secret key

See `.env.example` for complete list.

---

## 🐛 Troubleshooting

### Script Permission Denied

```bash
chmod +x scripts/*.sh
```

### Virtual Environment Issues

```bash
rm -rf .venv
./scripts/setup_dev.sh
```

### Docker Issues

```bash
./scripts/docker_build.sh clean
./scripts/docker_build.sh dev
```

### Test Failures

```bash
# Re-run failed tests
./scripts/run_tests.sh failed

# Run with more verbosity
./scripts/run_tests.sh all -vv
```

---

## 📚 Additional Resources

- [Testing Documentation](../tests/README.md)
- [Development Guide](../docs/development/)
- [Deployment Guide](../docs/deployment/)
- [ML Documentation](../ml/README.md)

---

## 🤝 Contributing

1. Run setup: `./scripts/setup_dev.sh`
2. Create feature branch
3. Make changes
4. Run tests: `./scripts/run_tests.sh`
5. Run pre-commit: `pre-commit run --all-files`
6. Submit pull request

The CI pipeline will automatically validate your changes.
