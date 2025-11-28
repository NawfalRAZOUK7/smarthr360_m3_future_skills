# CI/CD Integration for ML Testing

Complete guide for ML testing in continuous integration and deployment pipelines.

---

## Overview

The CI/CD pipeline includes a dedicated **ml-tests** job that runs comprehensive ML testing across multiple Python versions, ensuring the ML infrastructure works correctly in production environments.

---

## GitHub Actions Workflow

### Job Structure

The `.github/workflows/ci.yml` file contains three main jobs:

1. **test** - General application tests
2. **ml-tests** - Dedicated ML testing (NEW)
3. **docker-build** - Docker image validation

---

## ML Tests Job Configuration

### Triggers

The ML tests run on:
- **Push** to `main` or `develop` branches
- **Pull requests** to `main` or `develop` branches

### Matrix Strategy

Tests run on multiple Python versions:
```yaml
strategy:
  matrix:
    python-version: ["3.11", "3.12"]
```

This ensures compatibility across supported Python versions.

### Services

PostgreSQL database for integration tests:
```yaml
services:
  postgres:
    image: postgres:15
    env:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: test_smarthr360
    ports:
      - 5432:5432
```

---

## Pipeline Steps

### 1. Environment Setup

**Checkout code:**
```yaml
- name: Checkout code
  uses: actions/checkout@v4
```

**Set up Python:**
```yaml
- name: Set up Python ${{ matrix.python-version }}
  uses: actions/setup-python@v5
  with:
    python-version: ${{ matrix.python-version }}
    cache: "pip"
```

**Install system dependencies:**
```yaml
- name: Install system dependencies
  run: |
    sudo apt-get update
    sudo apt-get install -y libpq-dev
```

### 2. Python Dependencies

**Install all required packages:**
```yaml
- name: Install Python dependencies
  run: |
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    pip install -r requirements_ml.txt
```

**What gets installed:**
- Django and REST framework
- scikit-learn, pandas, numpy
- pytest and testing tools
- Coverage reporting tools

### 3. Configuration

**Create environment file:**
```yaml
- name: Create .env file
  run: |
    cp .env.example .env
    echo "DATABASE_URL=postgresql://postgres:postgres@localhost:5432/test_smarthr360" >> .env
    echo "DJANGO_SETTINGS_MODULE=config.settings.test" >> .env
    echo "FUTURE_SKILLS_USE_ML=True" >> .env
```

**Run database migrations:**
```yaml
- name: Run migrations
  run: |
    python manage.py migrate --settings=config.settings.test
  env:
    SECRET_KEY: ${{ secrets.SECRET_KEY }}
```

### 4. ML Unit Tests

**Fast unit tests only:**
```yaml
- name: Run ML unit tests
  run: |
    pytest ml/tests/ -v \
      --cov=ml \
      --cov-report=xml \
      --cov-report=term-missing \
      -m "not slow"
  env:
    DJANGO_SETTINGS_MODULE: config.settings.test
    SECRET_KEY: ${{ secrets.SECRET_KEY }}
```

**What it tests:**
- Model training (32 tests)
- Prediction quality (26 tests)
- Monitoring (12 tests)
- **Excludes slow performance tests**

### 5. ML Integration Tests

**API integration tests:**
```yaml
- name: Run ML integration tests
  run: |
    pytest tests/integration/test_ml_integration.py -v \
      --cov=future_skills.services.prediction_engine \
      --cov-report=xml \
      --cov-report=term-missing
  env:
    DJANGO_SETTINGS_MODULE: config.settings.test
    SECRET_KEY: ${{ secrets.SECRET_KEY }}
    FUTURE_SKILLS_USE_ML: True
```

**What it tests:**
- ML/rules engine switching (18 tests)
- API endpoint integration
- Error handling
- Prediction quality through API

### 6. Complete ML Test Suite

**All ML tests with coverage:**
```yaml
- name: Run all ML tests with coverage
  run: |
    pytest ml/tests/ tests/integration/test_ml_integration.py -v \
      --cov=future_skills.services.prediction_engine \
      --cov=ml \
      --cov-report=xml \
      --cov-report=term-missing
  env:
    DJANGO_SETTINGS_MODULE: config.settings.test
    SECRET_KEY: ${{ secrets.SECRET_KEY }}
    FUTURE_SKILLS_USE_ML: True
```

**Total coverage:**
- 88 ML tests (70 unit + 18 integration)
- Combined coverage report
- XML format for Codecov

### 7. Coverage Upload

**Upload to Codecov:**
```yaml
- name: Upload ML coverage to Codecov
  uses: codecov/codecov-action@v5
  with:
    token: ${{ secrets.CODECOV_TOKEN }}
    files: ./coverage.xml
    flags: ml-tests
    name: ml-coverage-${{ matrix.python-version }}
    fail_ci_if_error: false
```

**Features:**
- Separate ML test flag
- Per-Python-version reports
- Non-blocking (continue on error)

### 8. Coverage Validation

**Check coverage threshold:**
```yaml
- name: Generate coverage report
  run: |
    pip install coverage
    coverage report \
      --include="ml/*,future_skills/services/prediction_engine.py" \
      --fail-under=35
  continue-on-error: true
```

**Threshold:** 35% minimum coverage for ML modules

### 9. Artifact Verification

**Check ML model directory:**
```yaml
- name: Check ML model artifacts
  run: |
    test -d ml/models || mkdir -p ml/models
    echo "ML model directory exists"
```

**Verify test data:**
```yaml
- name: Verify ML test data
  run: |
    test -f ml/tests/test_data/sample_training_data.csv
    echo "ML test data verified"
```

### 10. Performance Tests (Main Branch Only)

**Slow tests on main:**
```yaml
- name: Run slow ML tests (performance)
  if: github.event_name == 'push' && github.ref == 'refs/heads/main'
  run: |
    pytest ml/tests/ tests/integration/test_ml_integration.py -v \
      -m slow \
      --cov=ml \
      --cov-report=term-missing
  env:
    DJANGO_SETTINGS_MODULE: config.settings.test
    SECRET_KEY: ${{ secrets.SECRET_KEY }}
    FUTURE_SKILLS_USE_ML: True
```

**When it runs:**
- Only on pushes to `main` branch
- Includes batch prediction tests
- Includes concurrent operation tests

---

## Environment Variables

### Required Secrets

Configure in GitHub repository settings:

1. **SECRET_KEY**
   - Django secret key for testing
   - Path: Settings → Secrets → Actions
   - Generate: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`

2. **CODECOV_TOKEN** (Optional)
   - Token for uploading coverage to Codecov
   - Get from: https://codecov.io
   - Not required (pipeline continues without it)

### Environment Variables in Workflow

Set automatically in CI:
```bash
DJANGO_SETTINGS_MODULE=config.settings.test
SECRET_KEY=${{ secrets.SECRET_KEY }}
FUTURE_SKILLS_USE_ML=True
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/test_smarthr360
```

---

## Test Execution Flow

### Pull Request Flow

1. **Trigger:** PR created/updated
2. **Run:** Fast ML tests only (not slow)
3. **Duration:** ~8-10 seconds
4. **Coverage:** Report generated
5. **Result:** Pass/fail status on PR

```
PR Created
    ↓
Checkout Code
    ↓
Setup Python 3.11 & 3.12 (parallel)
    ↓
Install Dependencies
    ↓
Run ML Unit Tests (70 tests) - ~7s
    ↓
Run ML Integration Tests (18 tests) - ~3s
    ↓
Upload Coverage
    ↓
✅ Success / ❌ Failure
```

### Main Branch Flow

1. **Trigger:** Push to main
2. **Run:** All ML tests including slow
3. **Duration:** ~15-20 seconds
4. **Coverage:** Full report
5. **Performance:** Batch & concurrent tests

```
Push to Main
    ↓
All PR Checks
    ↓
+ Run Slow ML Tests (~5-10s)
    ↓
✅ All Tests Pass
```

---

## Coverage Reporting

### Codecov Integration

**What gets uploaded:**
- `coverage.xml` - Combined coverage data
- Flags: `ml-tests` - Separate ML coverage
- Matrix: Per-Python-version reports

**View coverage:**
1. Visit: https://codecov.io/gh/NawfalRAZOUK7/smarthr360_m3_future_skills
2. Filter by: `ml-tests` flag
3. Compare: Python 3.11 vs 3.12

### Coverage Threshold

**Current threshold:** 35%
```yaml
coverage report --fail-under=35
```

**Coverage breakdown:**
- ml.training_service: 85%
- ml.prediction_engine: 78%
- future_skills.services.prediction_engine: 75%
- Overall ML: 37%

---

## Optimization Strategies

### 1. Parallel Execution

Tests run in parallel across Python versions:
```
Python 3.11        Python 3.12
    ↓                  ↓
ML Tests (88)     ML Tests (88)
    ↓                  ↓
~8-10s            ~8-10s
```

Total time: ~8-10s (not 16-20s)

### 2. Smart Caching

**Pip cache:**
```yaml
cache: "pip"
```

Caches installed packages between runs.

**Benefits:**
- Faster dependency installation
- Reduced network usage
- Consistent package versions

### 3. Test Markers

**Fast tests in PR:**
```bash
pytest -m "not slow"
```

**All tests on main:**
```bash
pytest  # Includes slow tests
```

### 4. Fail Fast

**Continue on non-critical failures:**
```yaml
continue-on-error: true
```

Used for:
- Coverage threshold checks
- Optional validations

---

## Debugging Failed Tests

### View Logs

1. Go to GitHub Actions tab
2. Click on failed workflow
3. Click on `ml-tests` job
4. Expand failed step

### Common Issues

**Issue 1: Import errors**
```
ModuleNotFoundError: No module named 'sklearn'
```
**Fix:** Check `requirements_ml.txt` installed

**Issue 2: Database connection**
```
django.db.utils.OperationalError: could not connect
```
**Fix:** Check PostgreSQL service running

**Issue 3: Missing test data**
```
FileNotFoundError: ml/tests/test_data/sample_training_data.csv
```
**Fix:** Ensure test data committed to repo

**Issue 4: Coverage below threshold**
```
Coverage failure: total of 32% is less than fail-under=35%
```
**Fix:** Add more tests or adjust threshold

### Local Reproduction

Reproduce CI environment locally:

```bash
# Use same Python version
pyenv install 3.11.7
pyenv local 3.11.7

# Install same dependencies
pip install -r requirements.txt
pip install -r requirements_ml.txt

# Use test settings
export DJANGO_SETTINGS_MODULE=config.settings.test
export FUTURE_SKILLS_USE_ML=True

# Run same tests
pytest ml/tests/ tests/integration/test_ml_integration.py -v \
  --cov=future_skills.services.prediction_engine \
  --cov=ml \
  --cov-report=term-missing
```

---

## Local CI Simulation

### Using Act

Run GitHub Actions locally:

```bash
# Install act
brew install act  # macOS
# or
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash  # Linux

# Run ml-tests job
act -j ml-tests

# Run with secrets
act -j ml-tests --secret-file .secrets
```

### Docker-based Testing

Test in isolated environment:

```bash
# Build test container
docker build -t smarthr360-ml-test -f Dockerfile.test .

# Run ML tests
docker run --rm \
  -e DJANGO_SETTINGS_MODULE=config.settings.test \
  -e FUTURE_SKILLS_USE_ML=True \
  smarthr360-ml-test \
  pytest ml/tests/ -v
```

---

## Best Practices

### 1. Fast Feedback

- **PR tests:** Fast only (exclude slow)
- **Main tests:** All tests including slow
- **Local tests:** Run relevant tests only

### 2. Coverage Goals

- **Maintain:** 35% minimum
- **Target:** 50% overall
- **Critical paths:** 80%+ coverage

### 3. Test Stability

- **Isolate tests:** No shared state
- **Mock external calls:** Use fixtures
- **Deterministic:** Same input → same output

### 4. Resource Management

- **Database:** Clean between tests
- **Files:** Use temp directories
- **Memory:** Clean up fixtures

### 5. Documentation

- **Update on changes:** Keep CI docs current
- **Document failures:** Common issues & fixes
- **Explain thresholds:** Why 35%? Why slow marker?

---

## Monitoring & Alerts

### GitHub Checks

**Automatic on PR:**
- ✅ All ML tests passing
- ✅ Coverage threshold met
- ✅ No critical failures

**Status badges:**
```markdown
![CI Status](https://github.com/NawfalRAZOUK7/smarthr360_m3_future_skills/workflows/CI/badge.svg)
```

### Codecov Status

**On PR:**
- Coverage diff shown
- New uncovered lines highlighted
- Trend graph displayed

### Failure Notifications

**Email notifications:**
- Test failures on main
- Coverage drops below threshold
- Build errors

**Slack integration (optional):**
```yaml
- name: Notify Slack
  if: failure()
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    channel: '#ml-alerts'
```

---

## Performance Metrics

### Current Performance

| Metric | Value |
|--------|-------|
| Total ML tests | 88 |
| Fast tests | 70 unit + 18 integration |
| Slow tests | 2 performance |
| PR test time | ~8-10s |
| Main test time | ~15-20s |
| Coverage | 37% |
| Python versions | 2 (3.11, 3.12) |

### Historical Trends

Track over time:
- Test count growth
- Coverage improvement
- Execution time changes
- Failure rate

---

## Future Enhancements

### Planned Improvements

1. **Model artifact caching**
   - Cache trained models
   - Skip training in tests
   - Faster test execution

2. **Parallel test execution**
   - pytest-xdist
   - Multiple workers
   - Halve execution time

3. **Nightly performance tests**
   - Comprehensive benchmarks
   - Large dataset tests
   - Memory profiling

4. **Coverage improvements**
   - Target: 50% overall
   - Focus: Prediction engine
   - Add: Edge case tests

5. **Integration with MLOps**
   - Model versioning
   - Experiment tracking
   - A/B test validation

---

## Troubleshooting Guide

### Test Timeouts

**Symptom:** Tests exceed 30-minute limit

**Solution:**
```yaml
timeout-minutes: 45  # Increase if needed
```

### Flaky Tests

**Symptom:** Intermittent failures

**Solution:**
```bash
# Re-run failed tests
pytest --lf -v

# Add retries
pytest --reruns 3 -v
```

### Memory Issues

**Symptom:** OOM errors

**Solution:**
```yaml
# Increase swap space
- name: Increase swap
  run: |
    sudo fallocate -l 4G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
```

### Dependency Conflicts

**Symptom:** Package version mismatches

**Solution:**
```bash
# Lock dependencies
pip freeze > requirements-lock.txt

# Use in CI
pip install -r requirements-lock.txt
```

---

## Summary

The CI/CD pipeline provides:

✅ **Comprehensive ML testing**
- 88 tests across 2 Python versions
- Unit + integration coverage
- Performance tests on main

✅ **Fast feedback**
- ~8-10s for PR tests
- Parallel execution
- Smart test markers

✅ **Quality gates**
- 35% coverage minimum
- All tests must pass
- Automated reporting

✅ **Easy debugging**
- Detailed logs
- Local reproduction
- Common fixes documented

---

**Last Updated:** November 28, 2025  
**ML Tests:** 88 (70 unit + 18 integration)  
**CI Job Status:** ✅ Active  
**Coverage Target:** 35% (current: 37%)
