# SmartHR360 - M3 Future Skills

AI-powered future skills prediction and recommendation system for HR management.

## 🚀 Quick Start

```bash
# 1. Setup virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements-dev.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your settings (see Configuration section below)

# 4. Validate configuration
python manage.py validate_config

# 5. Run migrations
python manage.py migrate

# 6. Seed initial data
python manage.py seed_future_skills

# 7. Create superuser
python manage.py createsuperuser

# 8. Run development server
python manage.py runserver
```

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
