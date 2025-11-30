# Coverage Thresholds Configuration

## Overview

This project uses different coverage thresholds for different modules to balance code quality with practical development constraints.

## Current Thresholds

### Main Application (70%)

- **Modules**: `future_skills/`, `config/`
- **Threshold**: 70%
- **Rationale**: Core business logic should maintain high coverage
- **CI Job**: `test` job - "Run tests with coverage"

### ML Module (40%)

- **Modules**: `ml/`
- **Threshold**: 40%
- **Rationale**: ML code includes complex algorithms, experimental features, and model training code that is harder to unit test
- **CI Jobs**:
  - `ml-tests` job - "Run ML unit tests"
  - `ml-tests` job - "Run all ML tests with coverage"
  - `ml-tests` job - "Run slow ML tests (performance)"

### Integration Tests (50%)

- **Modules**: `future_skills.services.prediction_engine`
- **Threshold**: 50%
- **Rationale**: Integration tests focus on service interactions
- **CI Job**: `ml-tests` job - "Run ML integration tests"

## Configuration

### pytest.ini

- **Does NOT** include `--cov-fail-under` in global `addopts`
- Coverage thresholds are set per-job in CI workflow
- This allows different modules to have different standards

### CI Workflow (.github/workflows/ci.yml)

Each pytest command includes its own `--cov-fail-under=X` flag:

```yaml
# Main tests (70%)
pytest --cov=future_skills --cov-fail-under=70 -v

# ML tests (40%)
pytest ml/tests/ --cov=ml --cov-fail-under=40 -m "not slow"

# Integration tests (50%)
pytest tests/integration/test_ml_integration.py --cov=future_skills.services.prediction_engine --cov-fail-under=50
```

## Why Different Thresholds?

### High Coverage (70%) for Core Business Logic

- Critical path code
- Well-defined business rules
- Easier to write comprehensive unit tests
- Direct impact on user functionality

### Lower Coverage (40%) for ML Module

- Complex mathematical operations
- Model training requires data and time
- Many code paths depend on model state
- Testing requires mock datasets and trained models
- Focus on integration tests over unit tests

### Medium Coverage (50%) for Integration Tests

- Tests service interactions
- More complex setup required
- Covers end-to-end scenarios

## Future Improvements

To increase ML module coverage:

1. Add tests for `ml/monitoring.py` (currently 18%)
2. Add tests for `ml/model_versioning.py` (currently 33%)
3. Add tests for `ml/mlflow_config.py` (currently 46%)
4. Improve `future_skills/services/explanation_engine.py` (currently 10%)

Target: Gradually increase ML coverage to 50-60% over time.

## Running Tests Locally

```bash
# Run main tests with 70% threshold
pytest --cov=future_skills --cov-fail-under=70 -v

# Run ML tests with 40% threshold
pytest ml/tests/ --cov=ml --cov-fail-under=40 -v

# Run specific test without coverage threshold
pytest ml/tests/test_model_training.py --no-cov -v
```

## References

- pytest.ini: Global pytest configuration
- .github/workflows/ci.yml: CI/CD pipeline with per-job thresholds
- TODO list: Coverage improvement tasks
