# SmartHR360 - Future Skills Project Structure

## 📁 Project Overview

This document provides a comprehensive overview of the project structure after completing the reorganization and modernization phases.

## 🗂️ Directory Structure

```
smarthr360_m3_future_skills/
├── .github/                          # GitHub Actions CI/CD
│   └── workflows/
│       └── ci.yml                   # CI/CD pipeline configuration
├── config/                           # Django project configuration
│   ├── settings/                    # Settings split by environment
│   │   ├── base.py                  # Base settings
│   │   ├── development.py           # Development settings
│   │   ├── production.py            # Production settings
│   │   └── test.py                  # Test settings
│   ├── urls.py                      # Main URL configuration
│   ├── wsgi.py                      # WSGI configuration
│   └── asgi.py                      # ASGI configuration
├── docs/                            # Documentation
│   ├── architecture/                # Architecture documentation
│   ├── api/                         # API documentation
│   ├── deployment/                  # Deployment guides
│   └── development/                 # Development guides
│       └── quick_commands.md        # Quick reference commands
├── future_skills/                   # Main Django app
│   ├── api/                         # API layer (separated)
│   │   ├── views.py                 # API views
│   │   ├── serializers.py           # API serializers
│   │   └── urls.py                  # API URLs
│   ├── services/                    # Business logic services
│   │   ├── prediction_engine.py     # ML prediction service
│   │   └── recommendation_engine.py # Recommendation service
│   ├── management/                  # Custom Django commands
│   │   └── commands/
│   ├── migrations/                  # Database migrations
│   ├── tests/                       # Unit tests
│   ├── models.py                    # Data models
│   ├── admin.py                     # Django admin configuration
│   └── permissions.py               # Custom permissions
├── ml/                              # Machine Learning
│   ├── models/                      # Trained ML models
│   ├── notebooks/                   # Jupyter notebooks
│   │   ├── dataset_analysis.ipynb
│   │   └── explainability_analysis.ipynb
│   ├── scripts/                     # ML scripts
│   ├── data/                        # ML datasets
│   ├── results/                     # Experiment results
│   ├── docs/                        # ML documentation
│   ├── experiment_future_skills_models.py
│   ├── evaluate_future_skills_models.py
│   └── README.md
├── scripts/                         # Utility scripts
│   ├── setup_dev.sh                # Development setup
│   ├── run_tests.sh                # Test runner
│   ├── docker_build.sh             # Docker management
│   ├── ml_train.sh                 # ML workflow
│   └── README.md                   # Scripts documentation
├── tests/                           # Integration & E2E tests
│   ├── integration/                 # Integration tests
│   │   ├── test_prediction_flow.py
│   │   └── test_api_endpoints.py
│   ├── e2e/                        # End-to-end tests
│   │   └── test_user_journeys.py
│   ├── fixtures/                    # Test fixtures
│   │   └── common.py
│   ├── conftest.py                 # Pytest configuration
│   └── README.md                   # Testing documentation
├── .env.example                     # Environment variables template
├── .gitignore                       # Git ignore rules
├── .pre-commit-config.yaml         # Pre-commit hooks
├── docker-compose.yml              # Docker development config
├── docker-compose.prod.yml         # Docker production config
├── Dockerfile                       # Docker image definition
├── Makefile                         # Project automation
├── manage.py                        # Django management script
├── pytest.ini                       # Pytest configuration
├── requirements.txt                 # Production dependencies
├── requirements-dev.txt            # Development dependencies
├── requirements_ml.txt             # ML dependencies
└── README.md                        # Project documentation
```

## 🎯 Key Features

### 1. **Environment-Based Settings**

- Settings split by environment (development, production, test)
- Environment variables management with python-decouple
- Database URL configuration with dj-database-url

### 2. **Comprehensive Testing**

- Unit tests in `future_skills/tests/`
- Integration tests in `tests/integration/`
- End-to-end tests in `tests/e2e/`
- 30+ reusable fixtures in `tests/conftest.py`
- Coverage reporting with pytest-cov

### 3. **CI/CD Pipeline**

- GitHub Actions workflow
- Multi-version Python testing (3.11, 3.12)
- PostgreSQL service integration
- Code quality checks (Black, Flake8, isort)
- Security scanning (Bandit, Safety)
- Coverage reporting to Codecov

### 4. **Development Tools**

- Pre-commit hooks for code quality
- Utility scripts for common tasks
- Makefile for project automation
- Docker support for development and production

### 5. **Machine Learning Pipeline**

- Organized ML directory structure
- Model experiment tracking
- Evaluation and comparison tools
- Explainability analysis notebooks
- MLOps documentation

### 6. **API Architecture**

- Separated API layer in `future_skills/api/`
- RESTful API with Django REST Framework
- Clear separation of concerns
- Comprehensive API documentation

## 🚀 Quick Start

### First Time Setup

```bash
# Clone and setup
git clone <repository-url>
cd smarthr360_m3_future_skills
make setup

# Activate environment
source .venv/bin/activate

# Start development server
make serve
```

### Daily Development

```bash
# Activate environment
source .venv/bin/activate

# Run tests
make test-fast

# Format code
make format

# Lint code
make lint

# Quick check before commit
make quick-check
```

### Docker Development

```bash
# Start development environment
make docker-up

# View logs
make docker-logs

# Stop environment
make docker-down
```

## 📊 Project Statistics

### Code Organization

- **Apps**: 1 main Django app (future_skills)
- **Models**: Employee, FutureSkill, FutureSkillPrediction, etc.
- **API Endpoints**: ~15+ RESTful endpoints
- **Tests**: 100+ test cases across unit, integration, and E2E
- **Coverage**: Target 80%+

### Technology Stack

- **Backend**: Django 5.2, DRF 3.16
- **Python**: 3.11+
- **Database**: PostgreSQL (production), SQLite (development)
- **ML**: scikit-learn, SHAP, LIME
- **Testing**: pytest, pytest-django, pytest-cov
- **CI/CD**: GitHub Actions
- **Containerization**: Docker, docker-compose

## 📖 Documentation Links

### Development

- [Quick Commands Guide](docs/development/quick_commands.md)
- [Testing Documentation](tests/README.md)
- [Scripts Documentation](scripts/README.md)

### Architecture

- [System Architecture](docs/architecture/)
- [API Documentation](docs/api/)

### Deployment

- [Deployment Guide](docs/deployment/)
- [Docker Guide](docs/deployment/docker.md)

### Machine Learning

- [ML Documentation](ml/README.md)
- [MLOps Guide](ml/MLOPS_GUIDE.md)
- [Model Registry](ml/MODEL_REGISTRY.md)

## 🔄 Development Workflow

### 1. Feature Development

```bash
# Create feature branch
git checkout -b feature/new-feature

# Make changes and test
make test-fast

# Format and lint
make format
make lint

# Commit with pre-commit hooks
git commit -m "feat: add new feature"

# Push and create PR
git push origin feature/new-feature
```

### 2. Testing Strategy

- **Unit Tests**: Fast, isolated, test individual components
- **Integration Tests**: Test component interactions
- **E2E Tests**: Test complete user workflows
- **ML Tests**: Test ML pipeline and models

### 3. Code Quality

- **Black**: Code formatting (line-length=120)
- **isort**: Import sorting
- **Flake8**: Linting
- **Bandit**: Security checks
- **Pre-commit**: Automated checks before commit

### 4. CI/CD Process

1. Push code to GitHub
2. GitHub Actions runs CI pipeline
3. Tests, linting, and security checks
4. Coverage reporting
5. Docker build validation
6. Merge if all checks pass

## 🎨 Code Style Guidelines

### Python

- **Line Length**: 120 characters
- **Import Order**: stdlib → third-party → local (isort)
- **Formatting**: Black
- **Docstrings**: Google style
- **Type Hints**: Encouraged for public APIs

### Django

- **Settings**: Environment-based, no secrets in code
- **URLs**: RESTful patterns
- **Views**: Class-based views for consistency
- **Models**: Clear field names, docstrings
- **Tests**: One test class per model/view/service

## 🔧 Maintenance

### Regular Tasks

```bash
# Update dependencies
pip install --upgrade -r requirements-dev.txt

# Run full test suite
make test

# Check for security issues
pre-commit run --all-files

# Clean temporary files
make clean-all
```

### ML Model Updates

```bash
# Retrain models
make ml-retrain

# Compare performance
make ml-compare

# Update production model if improved
# Update MODEL_PATH in settings
```

## 📈 Future Enhancements

### Planned Features

- [ ] GraphQL API support
- [ ] Real-time predictions with WebSockets
- [ ] Model A/B testing framework
- [ ] Advanced monitoring with Prometheus
- [ ] Kubernetes deployment configurations

### Infrastructure Improvements

- [ ] Multi-stage Docker builds
- [ ] CDN integration for static files
- [ ] Database read replicas
- [ ] Redis caching layer
- [ ] Elasticsearch for search

## 🤝 Contributing

1. Follow the code style guidelines
2. Write tests for new features
3. Update documentation
4. Run `make quick-check` before committing
5. Create meaningful commit messages
6. Submit PR with clear description

## 📞 Support

- **Documentation**: Check `docs/` directory
- **Issues**: GitHub Issues
- **Quick Commands**: `make help`
- **Scripts Help**: `./scripts/<script>.sh help`

---

**Last Updated**: Phase 9 - Makefile and Documentation Updates
**Version**: 1.0.0
**Status**: Production Ready
