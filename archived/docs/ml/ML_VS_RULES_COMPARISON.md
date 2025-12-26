# 📊 ML vs Rule-Based Engine - Performance Comparison Report

**Generated:** 2025-11-27 10:02:06

## 1. Overall Performance Comparison

| Metric | Rule-Based | ML Model | Difference | Winner |
|--------|------------|----------|------------|--------|
| Accuracy | 0.6723 | 0.9972 | +0.3249 (+48.33%) | 🤖 ML Model |
| F1 (Macro) | 0.2836 | 0.6646 | +0.3810 (+134.33%) | 🤖 ML Model |
| F1 (Weighted) | 0.5488 | 0.9972 | +0.4484 (+81.69%) | 🤖 ML Model |

## 2. Per-Class F1-Score Comparison

| Class | Rule-Based | ML Model | Difference | Winner |
|-------|------------|----------|------------|--------|
| LOW | 0.0000 | 0.0000 | +0.0000 (+0.00%) | 🤝 Tie |
| MEDIUM | 0.8020 | 0.9979 | +0.1959 (+24.42%) | 🤖 ML Model |
| HIGH | 0.0488 | 0.9958 | +0.9470 (+1941.42%) | 🤖 ML Model |

## 3. Confusion Matrices

### Rule-Based Engine

| Actual \ Predicted | LOW | MEDIUM | HIGH |
|-------------------|-----|--------|------|
| **LOW** | 0 | 0 | 0 |
| **MEDIUM** | 0 | 237 | 0 |
| **HIGH** | 0 | 117 | 3 |

### ML Model

| Actual \ Predicted | LOW | MEDIUM | HIGH |
|-------------------|-----|--------|------|
| **LOW** | 0 | 0 | 0 |
| **MEDIUM** | 0 | 237 | 0 |
| **HIGH** | 0 | 1 | 119 |

## 4. Discussion & Analysis

### 4.1 Overall Assessment

**🤖 ML Model Advantage:** The ML model outperforms the rule-based engine on 3 out of 3 key metrics.

### 4.2 When ML is Better

- **MEDIUM class:** +0.1959 F1-score improvement
- **HIGH class:** +0.9470 F1-score improvement

### 4.3 When Performance is Similar

- **LOW class:** Similar performance (diff: 0.0000)

### 4.4 Limitations & Considerations

⚠️ **Important Context:**

1. **Simulated Data:** This evaluation uses simulated/enriched dataset
2. **Training Set Overlap:** ML model may have seen similar patterns during training
3. **Rule Transparency:** Rule-based engine is fully interpretable and explainable
4. **ML Complexity:** ML model requires training data and periodic retraining
5. **Production Use:** Consider using ML when significant performance gains justify complexity

## 5. Recommendations

### ✅ Recommend ML Model for Production

**Reasons:**
- Superior performance on 3/3 key metrics
- Overall accuracy improvement: 0.3249

**Next Steps:**
- Validate on real-world data before deployment
- Set up monitoring for model performance drift
- Establish retraining pipeline

---
*This report was generated automatically by evaluate_future_skills_models.py*
