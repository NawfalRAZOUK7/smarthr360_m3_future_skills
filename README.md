# Environment Setup

1. Copy `.env.docker.example` to `.env.docker` and update values as needed.
2. Copy `secrets.example` to `secrets.env` and update secrets.
   Entrypoint scripts for each service are located in `scripts/entrypoints/` and are referenced in the respective Dockerfiles only. Do not modify entrypoints in setup scripts.

## Dockerfiles

All main Dockerfiles are modular and multi-stage. Legacy Dockerfiles have been archived in the `archived/` directory. Only modular Dockerfiles are used for builds.

## Volumes and Artifacts

ML models and other shared assets are handled via Docker volumes, not copied in Dockerfiles. See `docker-compose.yml` for volume configuration. Dockerfiles only copy runtime code and trained models from builder stages.

## 🐳 Docker Build Best Practices

To ensure fast builds and efficient layer caching, follow these Dockerfile guidelines:

- **Copy requirements first:**
  - Place `COPY requirements*.txt ./` (or similar) before copying the rest of your code.
  - Run `pip install` immediately after copying requirements, so this layer is only rebuilt when dependencies change.
- **Copy code last:**
  - Only copy the main app code after dependencies are installed. This maximizes Docker cache reuse.
- **Use multi-stage builds:**
  - Separate build-time and runtime dependencies. Only copy what’s needed for runtime into the final image.
- **Minimize final image size:**
  - Only include runtime code, assets, and entrypoints in the final stage.
- **Leverage .dockerignore:**
  - Exclude files/folders not needed in the image (e.g., `.git`, `__pycache__`, local data, docs).
- **Document produced files:**
  - See `DOCKER_PRODUCED_FILES_PER_STAGE.md` for what each build stage outputs.

For reference, see the main service Dockerfiles and [DOCKER_PRODUCED_FILES_PER_STAGE.md](DOCKER_PRODUCED_FILES_PER_STAGE.md).

## 🚦 CI/CD Test & Lint Container (Planned)

A dedicated CI/CD pipeline stage or container for running tests, linting, and security checks is planned for future implementation. This will further modularize and centralize quality checks, separate from build/runtime images.

- See `.github/workflows/ci.yml` for current pipeline steps (test, lint, security, coverage, ML tests).
- When ready, a dedicated test/lint container or job will be added for improved isolation and maintainability.

**Status:** _Pending (to be implemented in future CI/CD enhancements)_

## 🧪 Local Testing & Linting

To ensure code quality and correctness, run tests and linting locally before committing changes.

### 1. Environment Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

### 2. Running Tests

- **All tests:**
  ```bash
  ./scripts/run_tests.sh
  # or
  pytest
  ```
- **Unit tests only:**
  ```bash
  ./scripts/run_tests.sh unit
  # or
  pytest future_skills/tests/
  ```
- **Integration tests:**
  ```bash
  ./scripts/run_tests.sh integration
  # or
  pytest tests/integration/
  ```
- **End-to-end tests:**
  ```bash
  ./scripts/run_tests.sh e2e
  # or
  pytest tests/e2e/
  ```
- **Coverage report:**
  ```bash
  ./scripts/run_tests.sh coverage
  # or
  pytest --cov=future_skills --cov-report=html
  open htmlcov/index.html
  ```
- **More options:** See `tests/README.md` and `scripts/run_tests.sh --help` for advanced usage and markers (e.g., `ml`, `api`, `fast`, `failed`).

### 3. Linting & Code Quality

- **Lint with flake8:**
  ```bash
  flake8
  ```
- **Format with black:**
  ```bash
  black .
  ```
- **Sort imports with isort:**
  ```bash
  isort .
  ```
- **Type check with mypy:**
  ```bash
  mypy future_skills/
  ```
- **Run all pre-commit hooks:**
  ```bash
  pre-commit run --all-files
  ```

### 4. More Info

- See `tests/README.md` for detailed testing instructions, structure, and best practices.
- See `scripts/README.md` for available scripts and automation.
- All dev/test tools are in `requirements-dev.txt`.

# SmartHR360 - M3 Future Skills

AI-powered future skills prediction and recommendation system for HR management.

## 🚀 Quick Start

# 8. Run development server

python manage.py runserver

````

## 🐳 Docker Compose Onboarding

To run the full stack with Docker Compose (web, celery, nginx, db, redis):

```bash
# 1. Copy Docker environment template
cp .env.docker.example .env.docker

# 2. Edit .env.docker with your settings (see comments in the file)

# 3. (Optional) For secrets, copy and edit:
cp secrets.example secrets.env
# Then configure secrets.env with sensitive values (do NOT commit this file)

# 4. Start all services
docker-compose up --build

# 5. Access the app at http://localhost:8000
````

**Notes:**

### Environment & Secrets Onboarding

- `.env.docker.example`: Template for Docker Compose environment variables (non-sensitive, safe to commit)
- `.env.docker`: Actual Docker Compose environment file (should not be committed)
- `secrets.env`: Your actual secrets file (never commit this)

**Onboarding steps:**

1. Copy `.env.docker.example` to `.env.docker` and fill in required values.
2. Copy `secrets.example` to `secrets.env` and fill in secrets as needed.
   For local (non-Docker) development, continue to use `.env` and `.env.example` as before.

```bash
# 1. Setup virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements-dev.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your settings (see Configuration section below)

---v---+   +--v--+         +----v-----+
# 4. Validate configuration
-------+   +-----+         +----------+
python manage.py validate_config

# 5. Run migrations
python manage.py migrate
# 6. Seed initial data
python manage.py createsuperuser

# 8. Run development server
python manage.py runserver
```

## 🐍 Python Versions

- Use Python 3.12 (or 3.11/3.10) when you need `shap`/`numba` support.
- You can also keep a latest-Python venv (e.g., 3.14), but `shap`/`numba` will be skipped there.
- Example dual-venv setup:
  - `python3.12 -m venv .venv312 && source .venv312/bin/activate && pip install -r requirements.txt`
  - `python3.14 -m venv .venv314 && source .venv314/bin/activate && pip install -r requirements.txt`
  - Activate the venv that matches your workload (`shap`/ML → 3.12; general use → 3.14).

## ⚙️ Configuration

SmartHR360 uses environment variables for configuration. See the [Configuration Guide](docs/CONFIGURATION.md) for complete details.

### Quick Setup

1. **Copy environment template:**

   ```bash
   cp .env.example .env
   ```

2. **Generate secret key:**

   ```bash
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```

3. **Edit .env file** with your generated secret key and other settings

4. **Validate configuration:**
   ```bash
   python manage.py validate_config
   ```

### Essential Environment Variables

- `SECRET_KEY` - Django secret key (required, 50+ characters)
- `DEBUG` - Debug mode (default: False, True for development)
- `ALLOWED_HOSTS` - Comma-separated list of allowed hosts
- `DATABASE_URL` - Database connection URL
- `FUTURE_SKILLS_USE_ML` - Enable ML predictions (default: True)

📖 **See [Configuration Quick Reference](docs/CONFIGURATION_QUICK_REFERENCE.md)** for all variables

## 📚 Documentation

### Main Documentation

- **[Configuration Guide](docs/CONFIGURATION.md)** - Complete environment configuration guide
- **[Configuration Quick Reference](docs/CONFIGURATION_QUICK_REFERENCE.md)** - Quick commands and common settings
- **[API Documentation](docs/API_DOCUMENTATION.md)** - Complete API reference with examples
- **[Admin Guide](docs/ADMIN_GUIDE.md)** - Administrator's guide for HR staff
- **[Project Structure](PROJECT_STRUCTURE.md)** - Detailed project organization
- **[Architecture Overview](docs/architecture/)** - System architecture documentation

### Development Resources

- **[Development Guide](docs/development/)** - Setup and development workflow
- **[Testing Guide](docs/development/testing.md)** - Testing strategies and commands
- **[Quick Commands](docs/development/quick_commands.md)** - Common development commands

### API Architecture

- **[API Architecture Guide](docs/API_ARCHITECTURE.md)** - Complete API architecture and features
- **[API Quick Reference](docs/API_QUICK_REFERENCE.md)** - Quick commands and examples

**Key Features**:

- API versioning (v1 deprecated, v2 current)
- Multi-tier rate limiting (100-5000 requests/hour)
- Performance monitoring and caching
- Health check endpoints for Kubernetes
- Redis-ready caching with intelligent fallback
- Comprehensive request logging and metrics

### Testing Strategy

- **[Testing Guide](docs/TESTING_GUIDE.md)** - Comprehensive testing strategy and best practices
- **[Testing Quick Reference](docs/TESTING_QUICK_REFERENCE.md)** - Quick commands and common scenarios

**Key Features**:

- 250+ tests with 91% overall coverage
- Integration tests for API architecture (versioning, throttling, monitoring)
- Unit tests for middleware and throttling components
- pytest with markers for selective test execution
- Coverage reporting with HTML/XML output
- CI/CD ready with parallel execution support

### Database Optimization

- **[Database Optimization Guide](docs/DATABASE_OPTIMIZATION.md)** - Complete optimization strategy and performance guide
- **[Database Quick Reference](docs/DATABASE_OPTIMIZATION_QUICK_REFERENCE.md)** - Quick commands and best practices

**Key Features**:

- 38 strategic indexes across 9 models
- 60-85% query performance improvement
- Optimized for ForeignKey relationships and common filters
- Production-ready with monitoring and maintenance guides

### ML Documentation

- **[ML Architecture](docs/ml/)** - Machine learning system overview
- **[Model Training](docs/MODELTRAINER_QUICK_REFERENCE.md)** - Training workflow guide
- **[Training API](docs/TRAINING_API_QUICK_REFERENCE.md)** - Training API endpoints

### Release Information

- **[Release Notes](RELEASE_NOTES.md)** - Version history and changes
- **[Documentation Summary](DOCUMENTATION_SUMMARY.md)** - Complete feature documentation
- **[Milestones](docs/milestones/)** - Feature completion summaries

## 🧪 Testing

SmartHR360 includes comprehensive test coverage with integration and unit tests.

### Quick Start

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=future_skills --cov-report=html
open htmlcov/index.html  # View coverage report

# Run fast tests (skip slow tests)
pytest -m "not slow"

# Run specific test category
pytest -m api           # API tests
pytest -m middleware    # Middleware tests
pytest -m throttling    # Throttling tests

# Run specific test file
pytest future_skills/tests/test_api_architecture.py

# Run with parallel execution (faster)
pytest -n auto
```

### Test Coverage

| Component  | Coverage |
| ---------- | -------- |
| Overall    | 91%      |
| API Layer  | 92%      |
| Middleware | 88%      |
| Services   | 88%      |
| Models     | 92%      |

### Documentation

- **[Testing Guide](docs/TESTING_GUIDE.md)** - Complete testing strategy, writing tests, best practices
- **[Testing Quick Reference](docs/TESTING_QUICK_REFERENCE.md)** - Quick commands and troubleshooting

📖 See the [Testing Guide](docs/TESTING_GUIDE.md) for comprehensive documentation on:

- Test structure and organization
- Writing tests for APIs, middleware, and services
- Running tests with coverage
- CI/CD integration
- Debugging and troubleshooting

## 🤖 Machine Learning

The system uses machine learning models for:

- Future skills prediction
- Skill recommendations
- Career path analysis

See [ML Documentation](ml/docs/) for details.

## 📋 Make Commands

```bash
make install    # Install all dependencies
make test       # Run tests
make lint       # Check code quality
make format     # Format code
make migrate    # Run database migrations
make seed       # Seed initial data
```

## 🛠️ Technology Stack

- **Backend**: Django 5.2, Django REST Framework
- **ML**: scikit-learn, SHAP, LIME
- **Database**: SQLite (dev), PostgreSQL (prod)
- **Testing**: pytest, pytest-django

## 📦 Project Structure

```
smarthr360_m3_future_skills/
├── config/              # Django settings
├── future_skills/       # Main app
│   ├── api/            # API layer
│   ├── services/       # Business logic
│   ├── tests/          # Unit tests
│   └── management/     # Django commands
├── ml/                 # Machine learning
│   ├── models/         # Trained models
│   ├── scripts/        # Training scripts
│   └── notebooks/      # Analysis notebooks
├── docs/               # Documentation
└── tests/              # Integration tests
```

## 🤝 Contributing

1. Create a feature branch
2. Make your changes
3. Run tests: `pytest`
4. Format code: `make format`
5. Submit pull request

## 📄 License

Internal project - All rights reserved

# Test

Test CI/CD Pipeline - 1764377202
