# CI/CD Quick Reference

Quick commands and information for ML testing in CI/CD pipelines.

---

## GitHub Actions Status

**Workflow File:** `.github/workflows/ci.yml`  
**ML Tests Job:** `ml-tests`  
**Python Versions:** 3.11, 3.12  
**Database:** PostgreSQL 15

---

## What Runs When

### On Pull Request
✅ Fast ML tests (88 tests, ~8-10s)
- ML unit tests (70 tests)
- ML integration tests (18 tests)
- Excludes slow performance tests

### On Push to Main
✅ All ML tests including slow (90 tests, ~15-20s)
- All fast tests
- Performance tests (2 tests)
- Batch prediction benchmarks
- Concurrent operation tests

---

## Pipeline Steps

1. **Setup** - Python 3.11 & 3.12 in parallel
2. **Install** - Dependencies from requirements.txt & requirements_ml.txt
3. **Configure** - Database connection & ML settings
4. **Test** - Run all ML tests with coverage
5. **Report** - Upload coverage to Codecov
6. **Validate** - Check 35% coverage threshold
7. **Verify** - Test data and model artifacts

---

## Test Commands in CI

```bash
# ML unit tests (fast)
pytest ml/tests/ -v --cov=ml -m "not slow"

# ML integration tests
pytest tests/integration/test_ml_integration.py -v --cov=future_skills.services.prediction_engine

# All ML tests
pytest ml/tests/ tests/integration/test_ml_integration.py -v --cov=ml --cov=future_skills.services.prediction_engine

# Slow tests (main branch only)
pytest ml/tests/ tests/integration/test_ml_integration.py -v -m slow
```

---

## Environment Variables

Required in CI:
```bash
DJANGO_SETTINGS_MODULE=config.settings.test
SECRET_KEY=${{ secrets.SECRET_KEY }}
FUTURE_SKILLS_USE_ML=True
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/test_smarthr360
```

---

## Coverage Requirements

**Minimum:** 35%  
**Current:** 37%  
**Modules:**
- ml/* (all ML code)
- future_skills/services/prediction_engine.py

---

## Quick Debugging

### View logs
```
GitHub → Actions → Failed workflow → ml-tests job → Failed step
```

### Reproduce locally
```bash
export DJANGO_SETTINGS_MODULE=config.settings.test
export FUTURE_SKILLS_USE_ML=True
pytest ml/tests/ tests/integration/test_ml_integration.py -v
```

### Check specific Python version
```bash
pyenv install 3.11.7
pyenv local 3.11.7
make test-ml
```

---

## Common Issues & Fixes

**Issue:** Missing ML dependencies  
**Fix:** `pip install -r requirements_ml.txt`

**Issue:** Test data not found  
**Fix:** Ensure `ml/tests/test_data/sample_training_data.csv` committed

**Issue:** Database connection failed  
**Fix:** Check PostgreSQL service in workflow

**Issue:** Coverage below 35%  
**Fix:** Add more tests or adjust threshold

---

## Badges

Add to README.md:

```markdown
![CI Status](https://github.com/NawfalRAZOUK7/smarthr360_m3_future_skills/workflows/CI/badge.svg)
![Coverage](https://codecov.io/gh/NawfalRAZOUK7/smarthr360_m3_future_skills/branch/main/graph/badge.svg)
```

---

## Next Steps

After setup:
1. ✅ Push changes to trigger workflow
2. ✅ Check Actions tab for results
3. ✅ Add CODECOV_TOKEN secret (optional)
4. ✅ Monitor coverage trends
5. ✅ Update badges in README

---

For complete documentation, see: `docs/CI_CD_ML_TESTING.md`
