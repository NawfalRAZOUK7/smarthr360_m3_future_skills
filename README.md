# SmartHR360 - M3 Future Skills

AI-powered future skills prediction and recommendation system for HR management.

## 🚀 Quick Start

```bash
# Setup virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements-dev.txt

# Run migrations
python manage.py migrate

# Seed initial data
python manage.py seed_future_skills

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

## 📚 Documentation

- [API Documentation](docs/api/)
- [ML Architecture](docs/ml/)
- [Development Guide](docs/development/)
- [Testing Guide](docs/development/testing.md)
- [Quick Commands](docs/development/quick_commands.md)

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=future_skills --cov-report=html

# Run specific test file
pytest future_skills/tests/test_api.py
```

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
