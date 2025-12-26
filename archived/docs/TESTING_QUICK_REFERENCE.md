# Testing Quick Reference

**Quick commands for common testing scenarios**

---

## Basic Commands

### Run Tests

```bash
# All tests
pytest

# Specific file
pytest future_skills/tests/test_api_architecture.py

# Specific class
pytest future_skills/tests/test_api_architecture.py::APIVersioningTestCase

# Specific test
pytest future_skills/tests/test_api_architecture.py::APIVersioningTestCase::test_v2_url_path_versioning

# Verbose output
pytest -v

# Show print statements
pytest -s

# Stop on first failure
pytest -x

# Stop after N failures
pytest --maxfail=3
```

### Run by Markers

```bash
# API tests only
pytest -m api

# Integration tests
pytest -m integration

# Exclude slow tests
pytest -m "not slow"

# Middleware tests
pytest -m middleware

# Throttling tests
pytest -m throttling

# Smoke tests (quick validation)
pytest -m smoke

# Combine markers
pytest -m "api and not slow"
pytest -m "integration or unit"
```

### Parallel Execution

```bash
# Install plugin
pip install pytest-xdist

# Run with 4 workers
pytest -n 4

# Auto-detect CPU count
pytest -n auto
```

---

## Coverage Commands

### Generate Reports

```bash
# HTML report
pytest --cov=future_skills --cov-report=html
open htmlcov/index.html

# Terminal report
pytest --cov=future_skills --cov-report=term

# Terminal with missing lines
pytest --cov=future_skills --cov-report=term-missing

# XML report (for CI)
pytest --cov=future_skills --cov-report=xml

# Multiple reports
pytest --cov=future_skills --cov-report=html --cov-report=xml --cov-report=term

# Branch coverage
pytest --cov=future_skills --cov-branch --cov-report=html
```

### Coverage Analysis

```bash
# Specific module
pytest --cov=future_skills.api --cov-report=html

# Check threshold
pytest --cov=future_skills --cov-fail-under=80

# Show uncovered lines
pytest --cov=future_skills --cov-report=term-missing
```

---

## Debugging

### Debug Failed Tests

```bash
# Show full traceback
pytest --tb=long

# Show local variables
pytest --tb=long --showlocals

# Drop into debugger on failure
pytest --pdb

# Drop into debugger on first failure
pytest -x --pdb

# Show captured output for failed tests
pytest --tb=short -v
```

### Rerun Failed Tests

```bash
# Run only last failed
pytest --lf

# Run last failed first, then others
pytest --ff

# List tests that would run (dry-run)
pytest --collect-only
```

### Performance Analysis

```bash
# Show 10 slowest tests
pytest --durations=10

# Show all test durations
pytest --durations=0

# Profile with timing
pytest --durations=0 -v
```

---

## Common Workflows

### Pre-commit Check

```bash
# Fast validation (skip slow tests)
pytest -m "not slow" --maxfail=3
```

### Before Push

```bash
# Run all tests with coverage
pytest --cov=future_skills --cov-report=term-missing --cov-fail-under=80
```

### Continuous Development

```bash
# Install watch plugin
pip install pytest-watch

# Auto-run on file changes
ptw

# Auto-run with options
ptw -- -m "not slow" --cov=future_skills
```

### CI/CD Pipeline

```bash
# Full test suite with coverage
pytest --cov=future_skills --cov-report=xml --cov-report=html --cov-fail-under=70
```

### Quick Smoke Test

```bash
# Run smoke tests only (fastest validation)
pytest -m smoke -v
```

---

## Test Categories

### By Type

```bash
# Unit tests
pytest -m unit

# Integration tests
pytest -m integration

# API tests
pytest -m api

# ML tests
pytest future_skills/tests/test_prediction_engine.py
```

### By Feature

```bash
# API versioning
pytest -m versioning

# Rate limiting/throttling
pytest -m throttling

# Caching
pytest -m caching

# Performance monitoring
pytest -m monitoring future_skills/tests/test_middleware.py

# All architecture features
pytest future_skills/tests/test_api_architecture.py
```

### By Speed

```bash
# Fast tests only
pytest -m "not slow"

# Slow tests only
pytest -m slow

# Quick validation (smoke + unit)
pytest -m "smoke or unit"
```

---

## Environment Setup

### Configure Django Settings

```bash
# Use test settings
export DJANGO_SETTINGS_MODULE=config.settings.test

# Or inline
DJANGO_SETTINGS_MODULE=config.settings.test pytest
```

### Database Management

```bash
# Create test database
pytest --create-db

# Reuse existing test database (faster)
pytest --reuse-db

# Keep test database after run
pytest --reuse-db --keepdb
```

### Cache Management

```python
# In tests
from django.core.cache import cache

def setUp(self):
    cache.clear()

def tearDown(self):
    cache.clear()
```

---

## Makefile Shortcuts

Add to your `Makefile`:

```makefile
# Run all tests
.PHONY: test
test:
	pytest

# Fast tests (skip slow)
.PHONY: test-fast
test-fast:
	pytest -m "not slow"

# With coverage
.PHONY: test-coverage
test-coverage:
	pytest --cov=future_skills --cov-report=html
	@echo "Open htmlcov/index.html to view report"

# Smoke tests
.PHONY: test-smoke
test-smoke:
	pytest -m smoke

# Watch mode
.PHONY: test-watch
test-watch:
	ptw -- -m "not slow"

# Parallel execution
.PHONY: test-parallel
test-parallel:
	pytest -n auto

# Full CI test suite
.PHONY: test-ci
test-ci:
	pytest --cov=future_skills --cov-report=xml --cov-fail-under=70
```

Usage:

```bash
make test
make test-fast
make test-coverage
make test-smoke
```

---

## Troubleshooting

### Common Issues

**Tests fail with "Database access not allowed"**:

```python
# Add decorator to test class/method
import pytest

@pytest.mark.django_db
class MyTestCase:
    pass
```

**Tests fail with import errors**:

```bash
# Check PYTHONPATH
export PYTHONPATH=/path/to/project:$PYTHONPATH

# Or use pytest discovery
pytest --collect-only
```

**Tests hang or timeout**:

```bash
# Install timeout plugin
pip install pytest-timeout

# Run with timeout
pytest --timeout=30
```

**Flaky tests**:

```bash
# Install plugin for reruns
pip install pytest-rerunfailures

# Rerun failed tests up to 3 times
pytest --reruns 3
```

### Clear Cache

```bash
# Clear pytest cache
pytest --cache-clear

# Clear Python cache
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
```

---

## Useful Aliases

Add to your `.bashrc` or `.zshrc`:

```bash
# Quick test aliases
alias pt='pytest'
alias ptf='pytest -m "not slow"'
alias ptc='pytest --cov=future_skills --cov-report=html'
alias pts='pytest -m smoke'
alias ptv='pytest -vv -s'
alias ptd='pytest --pdb'
alias ptl='pytest --lf'

# Coverage aliases
alias cov='pytest --cov=future_skills --cov-report=term-missing'
alias covh='pytest --cov=future_skills --cov-report=html && open htmlcov/index.html'

# Debug aliases
alias ptdbg='pytest -vv -s --pdb --tb=long'
alias ptslow='pytest --durations=10'
```

---

## Test Output Examples

### Successful Test Run

```
================================ test session starts =================================
platform darwin -- Python 3.12.0, pytest-7.4.3, pluggy-1.3.0
django: version: 5.2.8, settings: config.settings.test
rootdir: /path/to/project
configfile: pytest.ini
plugins: django-4.7.0, cov-4.1.0
collected 256 items

future_skills/tests/test_api_architecture.py ...................... [ 16%]
future_skills/tests/test_middleware.py ................          [ 32%]
future_skills/tests/test_throttling.py .....................      [ 48%]
future_skills/tests/test_api.py .........................        [ 72%]
future_skills/tests/test_prediction_engine.py .............      [100%]

================================ 256 passed in 15.23s ================================
```

### Coverage Report

```
---------- coverage: platform darwin, python 3.12.0 -----------
Name                                          Stmts   Miss  Cover   Missing
---------------------------------------------------------------------------
future_skills/__init__.py                         2      0   100%
future_skills/api/__init__.py                     0      0   100%
future_skills/api/middleware.py                 125     15    88%   45-48, 67, 89-92
future_skills/api/monitoring.py                  85      8    90%   34, 56-59
future_skills/api/throttling.py                 110     12    89%   78-82, 101
future_skills/api/versioning.py                  78      6    92%   45, 67
future_skills/models.py                         245     18    92%
future_skills/services/prediction_engine.py     180     20    88%
---------------------------------------------------------------------------
TOTAL                                          1850    125    91%
```

### Failed Test Example

```
================================== FAILURES ======================================
_________________________ test_rate_limiting_works ______________________________

self = <test_throttling.UserRateThrottleTestCase testMethod=test_rate_limiting_works>

    def test_rate_limiting_works(self):
        """Test that rate limiting enforces limits."""
        for i in range(1001):
            response = self.client.get('/api/v2/predictions/')
>           if i < 1000:
E           AssertionError: Rate limit not enforced

future_skills/tests/test_throttling.py:45: AssertionError
========================= short test summary info ================================
FAILED future_skills/tests/test_throttling.py::UserRateThrottleTestCase::test_rate_limiting_works
========================= 1 failed, 255 passed in 16.78s =========================
```

---

## Quick Tips

1. **Run fast tests frequently**: `pytest -m "not slow"`
2. **Use coverage to find gaps**: `pytest --cov=future_skills --cov-report=term-missing`
3. **Debug with pdb**: `pytest --pdb -x` (stop on first failure, drop to debugger)
4. **Run tests in parallel**: `pytest -n auto` (much faster)
5. **Watch mode for development**: `ptw -- -m "not slow"`
6. **Mark slow tests**: Use `@pytest.mark.slow` decorator
7. **Use fixtures**: Share setup code across tests
8. **Mock external calls**: Don't hit real APIs/services in tests
9. **Keep tests independent**: Each test should run in isolation
10. **Test edge cases**: Empty data, invalid input, boundary conditions

---

## Resources

- Full Guide: [TESTING_GUIDE.md](./TESTING_GUIDE.md)
- pytest Documentation: https://docs.pytest.org/
- pytest-django: https://pytest-django.readthedocs.io/
- Coverage.py: https://coverage.readthedocs.io/

---

**Last Updated**: 2025-11-28  
**Quick Access**: Keep this file bookmarked for fast reference!
