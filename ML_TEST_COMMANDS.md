# ML Testing Commands

Complete guide for running ML tests in SmartHR360 Future Skills module.

## Quick Reference

```bash
# Run all ML tests (88 tests)
make test-ml

# Run only ML unit tests (70 tests)
make test-ml-unit

# Run only ML integration tests (18 tests)
make test-ml-integration

# Run slow ML tests (performance tests)
make test-ml-slow
```

---

## Detailed Commands

### 1. Run All ML Tests (Recommended)

**Command:**
```bash
make test-ml
```

**What it runs:**
```bash
pytest -v -m ml \
  --cov=future_skills.services.prediction_engine \
  --cov=ml \
  --cov-report=html \
  --cov-report=term-missing
```

**Includes:**
- All 70 ML unit tests (ml/tests/)
- All 18 ML integration tests (tests/integration/test_ml_integration.py)
- **Total: 88 tests**
- Coverage report for ML modules
- HTML coverage report in `htmlcov/`

**Expected Output:**
```
88 passed in ~8.3s
Coverage: 37%
```

---

### 2. Run ML Unit Tests Only

**Command:**
```bash
make test-ml-unit
```

**What it runs:**
```bash
pytest ml/tests/ -v \
  --cov=ml \
  --cov-report=term-missing
```

**Includes:**
- test_model_training.py (32 tests)
- test_prediction_quality.py (26 tests)
- test_model_monitoring.py (12 tests)
- **Total: 70 tests**

**Expected Output:**
```
70 passed in ~6.8s
```

---

### 3. Run ML Integration Tests Only

**Command:**
```bash
make test-ml-integration
```

**What it runs:**
```bash
pytest tests/integration/test_ml_integration.py -v \
  --cov=future_skills.services.prediction_engine \
  --cov-report=term-missing
```

**Includes:**
- TestMLIntegration (5 tests)
- TestMLPredictionQuality (3 tests)
- TestMLRecalculationIntegration (3 tests)
- TestMLErrorHandling (3 tests)
- TestMLPerformanceIntegration (2 tests)
- TestMLMonitoringIntegration (2 tests)
- **Total: 18 tests**

**Expected Output:**
```
18 passed in ~3.1s
```

---

### 4. Run Slow ML Tests

**Command:**
```bash
make test-ml-slow
```

**What it runs:**
```bash
pytest -v -m "ml and slow" \
  --cov=future_skills.services.prediction_engine \
  --cov=ml \
  --cov-report=term-missing
```

**Includes:**
- Performance tests (batch predictions, concurrent operations)
- Tests marked with `@pytest.mark.slow`
- Large dataset processing tests

**Use Case:**
- Pre-deployment performance validation
- Performance regression testing
- Not run in CI/CD by default

---

## Direct pytest Commands

For more control, use pytest directly:

### Run All ML Tests
```bash
pytest -v -m ml \
  --cov=future_skills.services.prediction_engine \
  --cov=ml \
  --cov-report=html \
  --cov-report=term-missing
```

### Run Specific Test File
```bash
# Training tests
pytest ml/tests/test_model_training.py -v

# Prediction quality tests
pytest ml/tests/test_prediction_quality.py -v

# Monitoring tests
pytest ml/tests/test_model_monitoring.py -v

# Integration tests
pytest tests/integration/test_ml_integration.py -v
```

### Run Specific Test Class
```bash
# Run all tests in TestModelTraining
pytest ml/tests/test_model_training.py::TestModelTraining -v

# Run all tests in TestMLIntegration
pytest tests/integration/test_ml_integration.py::TestMLIntegration -v
```

### Run Specific Test Method
```bash
# Run single test
pytest ml/tests/test_model_training.py::TestModelTraining::test_train_model_success -v

# Run prediction quality test
pytest ml/tests/test_prediction_quality.py::TestPredictionQuality::test_predict_returns_valid_scores -v
```

### Run with Different Markers
```bash
# Run only fast ML tests
pytest -v -m "ml and not slow"

# Run ML integration tests
pytest -v -m "ml and integration"

# Run ML API tests
pytest -v -m "ml and api"
```

---

## Coverage Reports

### Generate HTML Coverage Report
```bash
make test-ml
# Open htmlcov/index.html in browser
```

### Generate JSON Coverage Report
```bash
pytest -v -m ml \
  --cov=future_skills.services.prediction_engine \
  --cov=ml \
  --cov-report=json
# Output: coverage.json
```

### View Coverage Summary
```bash
pytest -v -m ml \
  --cov=future_skills.services.prediction_engine \
  --cov=ml \
  --cov-report=term
```

---

## Test Filtering Examples

### Skip Slow Tests
```bash
pytest ml/tests/ -v -m "not slow"
```

### Run Only Integration Tests
```bash
pytest tests/integration/ -v -m integration
```

### Run Tests by Keyword
```bash
# Run tests with "prediction" in name
pytest ml/tests/ -v -k prediction

# Run tests with "monitoring" in name
pytest ml/tests/ -v -k monitoring

# Run tests with "quality" in name
pytest ml/tests/ -v -k quality
```

---

## Continuous Integration

### CI/CD Pipeline Commands

**Fast CI (Pull Requests):**
```bash
# Run fast ML tests only
pytest -v -m "ml and not slow" \
  --cov=future_skills.services.prediction_engine \
  --cov=ml \
  --cov-report=xml
```

**Full CI (Main Branch):**
```bash
# Run all ML tests including slow
pytest -v -m ml \
  --cov=future_skills.services.prediction_engine \
  --cov=ml \
  --cov-report=xml \
  --cov-report=html
```

---

## Troubleshooting

### Test Discovery Issues
```bash
# List all ML tests without running
pytest --collect-only -m ml

# List tests in specific file
pytest --collect-only ml/tests/test_model_training.py
```

### Debug Mode
```bash
# Run with print statements visible
pytest ml/tests/ -v -s

# Run with Python debugger on failure
pytest ml/tests/ -v --pdb
```

### Verbose Output
```bash
# Maximum verbosity
pytest ml/tests/ -vv

# Show full diff on assertion failures
pytest ml/tests/ -v --tb=long
```

### Re-run Failed Tests
```bash
# Run only last failed tests
pytest --lf -v

# Run failed first, then all
pytest --ff -v
```

---

## Expected Test Results

### Current Status (Feature 6 Complete)

| Test Suite | Tests | Status | Time |
|------------|-------|--------|------|
| ML Unit Tests | 70 | ✅ 100% | ~6.8s |
| ML Integration Tests | 18 | ✅ 100% | ~3.1s |
| **Total ML Tests** | **88** | **✅ 100%** | **~8.3s** |

### Coverage Metrics

| Module | Coverage |
|--------|----------|
| ml.training_service | 85% |
| ml.prediction_engine | 78% |
| future_skills.services.prediction_engine | 28% |
| **Overall ML Coverage** | **37%** |

---

## Test Organization

```
ml/tests/
├── test_data/
│   └── sample_training_data.csv (74 rows)
├── test_model_training.py (32 tests)
│   ├── TestModelTraining (15 tests)
│   ├── TestModelPersistence (6 tests)
│   ├── TestModelFeatures (5 tests)
│   ├── TestTrainingDataValidation (3 tests)
│   └── TestCrossValidation (3 tests)
├── test_prediction_quality.py (26 tests)
│   ├── TestPredictionQuality (6 tests)
│   ├── TestConfidenceScores (5 tests)
│   ├── TestPredictionConsistency (4 tests)
│   ├── TestEdgeCases (5 tests)
│   ├── TestMultipleHorizons (3 tests)
│   └── TestSkillRecommendations (3 tests)
└── test_model_monitoring.py (12 tests)
    ├── TestModelMonitoring (10 tests)
    └── TestMonitoringIntegration (2 tests)

tests/integration/
└── test_ml_integration.py (18 tests)
    ├── TestMLIntegration (5 tests)
    ├── TestMLPredictionQuality (3 tests)
    ├── TestMLRecalculationIntegration (3 tests)
    ├── TestMLErrorHandling (3 tests)
    ├── TestMLPerformanceIntegration (2 tests)
    └── TestMLMonitoringIntegration (2 tests)
```

---

## Quick Commands Summary

```bash
# Most common commands
make test-ml                    # Run all ML tests (88 tests)
make test-ml-unit              # Unit tests only (70 tests)
make test-ml-integration       # Integration tests only (18 tests)
make test-ml-slow              # Performance tests only

# Direct pytest commands
pytest -v -m ml                # All ML tests
pytest -v -m "ml and not slow" # Fast ML tests only
pytest ml/tests/ -v            # ML unit tests
pytest tests/integration/test_ml_integration.py -v  # ML integration tests
```

---

**Last Updated:** November 28, 2025  
**Feature 6 Status:** ✅ Complete (88/88 tests passing)
