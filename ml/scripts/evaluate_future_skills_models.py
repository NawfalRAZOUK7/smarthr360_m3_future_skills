#!/usr/bin/env python3
"""Evaluation script to compare ML model vs Rule-based engine performance.

This script:
1. Loads the enriched dataset
2. Calculates predictions using both approaches:
   - Rule-based engine (calculate_level)
   - ML model (trained pipeline)
3. Compares performance using multiple metrics:
   - Accuracy
   - F1-score (macro, weighted, per-class)
   - Confusion matrix
   - Classification report
4. Generates a comparative report

Usage:
django.setup()

    python ml/evaluate_future_skills_models.py [--dataset PATH] [--model PATH] [--output PATH]
"""

import argparse
import json
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
import os
import sys
from pathlib import Path
from typing import Any, Dict

# Ensure project root is in sys.path for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import joblib
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
)

BASE_DIR = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
DATASETS_DIR = ARTIFACTS_DIR / "datasets"
MODELS_DIR = ARTIFACTS_DIR / "models"
RESULTS_DIR = ARTIFACTS_DIR / "results"

for directory in (ARTIFACTS_DIR, DATASETS_DIR, MODELS_DIR, RESULTS_DIR):
    directory.mkdir(parents=True, exist_ok=True)

# Configure Django settings and setup before importing Django-dependent modules
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.development"
import django

django.setup()

# Now import Django-dependent modules after Django is set up
from future_skills.services.prediction_engine import calculate_level

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LABEL_ORDER = ["LOW", "MEDIUM", "HIGH"]


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def load_dataset(csv_path: Path) -> pd.DataFrame:
    """Load and validate the dataset."""
    if not csv_path.exists():
        raise FileNotFoundError(f"Dataset not found: {csv_path}")

    df = pd.read_csv(csv_path)

    # Validate required columns
    required_cols = [
        "future_need_level",
        "trend_score",
        "internal_usage",
        "training_requests",
    ]

    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Filter valid labels
    valid_df = df[df["future_need_level"].isin(LABEL_ORDER)].copy()

    logger.info(f"Loaded {len(df)} rows, {len(valid_df)} valid")
    if len(valid_df) < len(df):
        logger.warning(f"Filtered out {len(df) - len(valid_df)} invalid labels")

    return valid_df


def load_ml_model(model_path: Path):
    """Load the trained ML pipeline."""
    if not model_path.exists():
        raise FileNotFoundError(f"ML model not found: {model_path}")

    pipeline = joblib.load(model_path)
    logger.info(f"Loaded ML model from {model_path}")
    return pipeline


def predict_with_rules(df: pd.DataFrame) -> pd.Series:
    """Generate predictions using the rule-based engine."""
    predictions = []

    for _, row in df.iterrows():
        level, _ = calculate_level(
            trend_score=row["trend_score"],
            internal_usage=row["internal_usage"],
            training_requests=row["training_requests"],
        )
        predictions.append(level)

    logger.info(f"Generated {len(predictions)} rule-based predictions")
    return pd.Series(predictions, index=df.index)


def predict_with_ml(df: pd.DataFrame, pipeline) -> pd.Series:
    """Generate predictions using the ML model."""
    # Identify features used by the model
    # Get features from the pipeline's preprocessor
    try:
        preprocessor = pipeline.named_steps["preprocess"]
        feature_names = []

        for name, transformer, cols in preprocessor.transformers_:
            if name != "remainder":
                feature_names.extend(cols)

        # Use only available features
        available_features = [col for col in feature_names if col in df.columns]

        if not available_features:
            raise ValueError("No common features between model and dataset")

        X = df[available_features].copy()
        predictions = pipeline.predict(X)

        logger.info(f"Generated {len(predictions)} ML predictions using {len(available_features)} features")
        return pd.Series(predictions, index=df.index)

    except Exception as e:
        logger.error(f"Failed to generate ML predictions: {e}")
        # Fallback: try with common feature set
        common_features = [
            "job_role_name",
            "skill_name",
            "trend_score",
            "internal_usage",
            "training_requests",
        ]
        available = [col for col in common_features if col in df.columns]

        if available:
            logger.info(f"Attempting with fallback features: {available}")
            X = df[available].copy()
            predictions = pipeline.predict(X)
            return pd.Series(predictions, index=df.index)
        else:
            raise


def calculate_metrics(y_true: pd.Series, y_pred: pd.Series, name: str) -> Dict[str, Any]:
    """Calculate comprehensive metrics for predictions."""
    # Overall metrics
    accuracy = accuracy_score(y_true, y_pred)

    # F1 scores
    f1_macro = f1_score(y_true, y_pred, average="macro", labels=LABEL_ORDER)
    f1_weighted = f1_score(y_true, y_pred, average="weighted", labels=LABEL_ORDER)

    # Per-class metrics
    precision, recall, f1_per_class, support = precision_recall_fscore_support(
        y_true, y_pred, labels=LABEL_ORDER, zero_division=0
    )

    # Confusion matrix
    cm = confusion_matrix(y_true, y_pred, labels=LABEL_ORDER)

    # Classification report (as dict)
    report = classification_report(y_true, y_pred, labels=LABEL_ORDER, output_dict=True, zero_division=0)

    metrics = {
        "name": name,
        "accuracy": float(accuracy),
        "f1_macro": float(f1_macro),
        "f1_weighted": float(f1_weighted),
        "per_class": {
            label: {
                "precision": float(precision[i]),
                "recall": float(recall[i]),
                "f1_score": float(f1_per_class[i]),
                "support": int(support[i]),
            }
            for i, label in enumerate(LABEL_ORDER)
        },
        "confusion_matrix": cm.tolist(),
        "classification_report": report,
    }

    return metrics


def print_metrics_summary(metrics: Dict[str, Any]):
    """Print a readable summary of metrics."""
    logger.info("\n" + "=" * 70)
    logger.info(f" {metrics['name']} - Performance Summary")
    logger.info("=" * 70)
    logger.info(f"  Accuracy:      {metrics['accuracy']:.4f}")
    logger.info(f"  F1 (Macro):    {metrics['f1_macro']:.4f}")
    logger.info(f"  F1 (Weighted): {metrics['f1_weighted']:.4f}")
    logger.info("\n  Per-Class Metrics:")
    logger.info(f"  {'-' * 66}")
    logger.info(f"  {'Class':<10} {'Precision':<12} {'Recall':<12} {'F1-Score':<12} {'Support':<10}")
    logger.info(f"  {'-' * 66}")

    for label in LABEL_ORDER:
        pc = metrics["per_class"][label]
        logger.info(
            f"  {label:<10} {pc['precision']:<12.4f} {pc['recall']:<12.4f} "
            f"{pc['f1_score']:<12.4f} {pc['support']:<10}"
        )

    logger.info("\n  Confusion Matrix:")
    logger.info(f"  {'-' * 66}")
    actual_vs_pred = "Actual \\ Pred"
    logger.info(f"  {actual_vs_pred:<15} {LABEL_ORDER[0]:<10} {LABEL_ORDER[1]:<10} {LABEL_ORDER[2]:<10}")
    logger.info(f"  {'-' * 66}")

    cm = metrics["confusion_matrix"]
    for i, label in enumerate(LABEL_ORDER):
        logger.info(f"  {label:<15} {cm[i][0]:<10} {cm[i][1]:<10} {cm[i][2]:<10}")

    logger.info("=" * 70 + "\n")


def _compare_metric(rules_val: float, ml_val: float) -> tuple:
    """Compare a single metric between rule-based and ML model.

    Returns: (difference, percentage_difference, winner_label)
    """
    diff = ml_val - rules_val
    diff_pct = (diff / rules_val * 100) if rules_val > 0 else 0

    if abs(diff) < 0.01:
        winner = "🤝 Tie"
    elif diff > 0:
        winner = "🤖 ML Model"
    else:
        winner = "📐 Rules"

    return diff, diff_pct, winner


def _add_overall_comparison(report_lines: list, rules_metrics: dict, ml_metrics: dict) -> tuple:
    """Add overall performance comparison section.

    Returns: (ml_wins, rules_wins, ties)
    """
    report_lines.append("## 1. Overall Performance Comparison")
    report_lines.append("")
    report_lines.append("| Metric | Rule-Based | ML Model | Difference | Winner |")
    report_lines.append("|--------|------------|----------|------------|--------|")

    metrics_to_compare = [
        ("Accuracy", "accuracy"),
        ("F1 (Macro)", "f1_macro"),
        ("F1 (Weighted)", "f1_weighted"),
    ]

    ml_wins = rules_wins = ties = 0

    for metric_name, metric_key in metrics_to_compare:
        rules_val = rules_metrics[metric_key]
        ml_val = ml_metrics[metric_key]
        diff, diff_pct, winner = _compare_metric(rules_val, ml_val)

        # Count wins
        if abs(diff) < 0.01:
            ties += 1
        elif diff > 0:
            ml_wins += 1
        else:
            rules_wins += 1

        report_lines.append(
            f"| {metric_name} | {rules_val:.4f} | {ml_val:.4f} | " f"{diff:+.4f} ({diff_pct:+.2f}%) | {winner} |"
        )

    report_lines.append("")
    return ml_wins, rules_wins, ties


def _add_per_class_comparison(report_lines: list, rules_metrics: dict, ml_metrics: dict):
    """Add per-class F1-score comparison section."""
    report_lines.append("## 2. Per-Class F1-Score Comparison")
    report_lines.append("")
    report_lines.append("| Class | Rule-Based | ML Model | Difference | Winner |")
    report_lines.append("|-------|------------|----------|------------|--------|")

    for label in LABEL_ORDER:
        rules_f1 = rules_metrics["per_class"][label]["f1_score"]
        ml_f1 = ml_metrics["per_class"][label]["f1_score"]
        diff, diff_pct, winner = _compare_metric(rules_f1, ml_f1)

        report_lines.append(
            f"| {label} | {rules_f1:.4f} | {ml_f1:.4f} | " f"{diff:+.4f} ({diff_pct:+.2f}%) | {winner} |"
        )

    report_lines.append("")


def _add_confusion_matrices(report_lines: list, rules_metrics: dict, ml_metrics: dict):
    """Add confusion matrices section."""
    report_lines.append("## 3. Confusion Matrices")
    report_lines.append("")

    for name, metrics in [
        ("Rule-Based Engine", rules_metrics),
        ("ML Model", ml_metrics),
    ]:
        report_lines.append(f"### {name}")
        report_lines.append("")
        report_lines.append("| Actual \\ Predicted | LOW | MEDIUM | HIGH |")
        report_lines.append("|-------------------|-----|--------|------|")

        cm = metrics["confusion_matrix"]
        for i, label in enumerate(LABEL_ORDER):
            report_lines.append(f"| **{label}** | {cm[i][0]} | {cm[i][1]} | {cm[i][2]} |")

        report_lines.append("")


def _add_discussion_section(
    report_lines: list,
    rules_metrics: dict,
    ml_metrics: dict,
    ml_wins: int,
    rules_wins: int,
    metrics_count: int,
):
    """Add discussion and analysis section."""
    report_lines.append("## 4. Discussion & Analysis")
    report_lines.append("")
    report_lines.append("### 4.1 Overall Assessment")
    report_lines.append("")

    if ml_wins > rules_wins:
        report_lines.append(
            f"**🤖 ML Model Advantage:** The ML model outperforms the rule-based engine "
            f"on {ml_wins} out of {metrics_count} key metrics."
        )
    elif rules_wins > ml_wins:
        report_lines.append(
            f"**📐 Rule-Based Advantage:** The rule-based engine outperforms the ML model "
            f"on {rules_wins} out of {metrics_count} key metrics."
        )
    else:
        report_lines.append(
            "**🤝 Comparable Performance:** Both approaches show similar performance " "across key metrics."
        )

    report_lines.append("")

    # ML advantages
    report_lines.append("### 4.2 When ML is Better")
    report_lines.append("")

    ml_advantages = []
    for label in LABEL_ORDER:
        diff = ml_metrics["per_class"][label]["f1_score"] - rules_metrics["per_class"][label]["f1_score"]
        if diff > 0.02:
            ml_advantages.append(f"- **{label} class:** +{diff:.4f} F1-score improvement")

    if ml_advantages:
        report_lines.extend(ml_advantages)
    else:
        report_lines.append("- No significant per-class advantages detected (threshold: 0.02)")

    report_lines.append("")

    # Similar performance
    report_lines.append("### 4.3 When Performance is Similar")
    report_lines.append("")

    similar_classes = []
    for label in LABEL_ORDER:
        diff = abs(ml_metrics["per_class"][label]["f1_score"] - rules_metrics["per_class"][label]["f1_score"])
        if diff <= 0.02:
            similar_classes.append(f"- **{label} class:** Similar performance (diff: {diff:.4f})")

    if similar_classes:
        report_lines.extend(similar_classes)
    else:
        report_lines.append("- All classes show significant differences")

    report_lines.append("")

    # Limitations
    report_lines.append("### 4.4 Limitations & Considerations")
    report_lines.append("")
    report_lines.append("⚠️ **Important Context:**")
    report_lines.append("")
    report_lines.append("1. **Simulated Data:** This evaluation uses simulated/enriched dataset")
    report_lines.append("2. **Training Set Overlap:** ML model may have seen similar patterns during training")
    report_lines.append("3. **Rule Transparency:** Rule-based engine is fully interpretable and explainable")
    report_lines.append("4. **ML Complexity:** ML model requires training data and periodic retraining")
    report_lines.append(
        "5. **Production Use:** Consider using ML when significant performance gains justify complexity"
    )
    report_lines.append("")


def _add_recommendations(
    report_lines: list,
    rules_metrics: dict,
    ml_metrics: dict,
    ml_wins: int,
    rules_wins: int,
    metrics_count: int,
):
    """Add recommendations section."""
    report_lines.append("## 5. Recommendations")
    report_lines.append("")

    if ml_wins > rules_wins:
        report_lines.append("### ✅ Recommend ML Model for Production")
        report_lines.append("")
        report_lines.append("**Reasons:**")
        report_lines.append(f"- Superior performance on {ml_wins}/{metrics_count} key metrics")
        report_lines.append(
            f"- Overall accuracy improvement: {(ml_metrics['accuracy'] - rules_metrics['accuracy']):.4f}"
        )
        report_lines.append("")
        report_lines.append("**Next Steps:**")
        report_lines.append("- Validate on real-world data before deployment")
        report_lines.append("- Set up monitoring for model performance drift")
        report_lines.append("- Establish retraining pipeline")
    else:
        report_lines.append("### ⚖️ Consider Hybrid or Rule-Based Approach")
        report_lines.append("")
        report_lines.append("**Reasons:**")
        report_lines.append("- Rule-based engine shows competitive performance")
        report_lines.append("- Simpler to maintain and explain")
        report_lines.append("- No training data or retraining required")
        report_lines.append("")
        report_lines.append("**Alternatives:**")
        report_lines.append("- Use ML model for specific classes where it excels")
        report_lines.append("- Collect more diverse training data")
        report_lines.append("- Enhance rule-based engine with domain expertise")


def generate_comparison_report(
    rules_metrics: Dict[str, Any],
    ml_metrics: Dict[str, Any],
    output_path: Path,
):
    """Generate a detailed comparison report."""
    report_lines = []

    report_lines.append("# 📊 ML vs Rule-Based Engine - Performance Comparison Report")
    report_lines.append("")
    report_lines.append(f"**Generated:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("")

    # Overall comparison
    ml_wins, rules_wins, ties = _add_overall_comparison(report_lines, rules_metrics, ml_metrics)
    metrics_count = ml_wins + rules_wins + ties

    # Per-class comparison
    _add_per_class_comparison(report_lines, rules_metrics, ml_metrics)

    # Confusion matrices
    _add_confusion_matrices(report_lines, rules_metrics, ml_metrics)

    # Discussion
    _add_discussion_section(report_lines, rules_metrics, ml_metrics, ml_wins, rules_wins, metrics_count)

    # Recommendations
    _add_recommendations(report_lines, rules_metrics, ml_metrics, ml_wins, rules_wins, metrics_count)

    report_lines.append("")
    report_lines.append("---")
    report_lines.append("*This report was generated automatically by evaluate_future_skills_models.py*")

    # Write report
    report_content = "\n".join(report_lines)
    output_path.write_text(report_content, encoding="utf-8")
    print(f"[INFO] Comparison report written to: {output_path}")

    return report_content


def main():
    """Main entry point for evaluating ML model vs rule-based engine performance.

    Parses command line arguments, loads data and models, generates predictions
    using both approaches, calculates comprehensive metrics, and generates
    comparison reports. Supports evaluation of rule-based engine only if ML
    model is not available.
    """
    parser = argparse.ArgumentParser(description="Compare ML model vs Rule-based engine performance")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DATASETS_DIR / "future_skills_dataset.csv",
        help="Path to the dataset CSV file",
    )
    parser.add_argument(
        "--model",
        type=Path,
        default=MODELS_DIR / "future_skills_model.pkl",
        help="Path to the trained ML model",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=RESULTS_DIR / "ML_VS_RULES_COMPARISON.md",
        help="Path for the output comparison report",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=RESULTS_DIR / "evaluation_results.json",
        help="Path for JSON output with detailed metrics",
    )

    args = parser.parse_args()

    print("\n" + "=" * 70)
    print(" Future Skills - ML vs Rules Evaluation")
    print("=" * 70 + "\n")

    # Load dataset
    df = load_dataset(args.dataset)
    y_true = df["future_need_level"]

    # Load ML model
    try:
        ml_pipeline = load_ml_model(args.model)
        has_ml_model = True
    except FileNotFoundError as e:
        print(f"[WARN] {e}")
        print("[WARN] Will only evaluate rule-based engine")
        has_ml_model = False

    # Generate predictions
    print("\n[STEP 1] Generating predictions with rule-based engine...")
    y_pred_rules = predict_with_rules(df)

    if has_ml_model:
        print("[STEP 2] Generating predictions with ML model...")
        try:
            y_pred_ml = predict_with_ml(df, ml_pipeline)
        except Exception as e:
            print(f"[ERROR] Failed to generate ML predictions: {e}")
            print("[INFO] Continuing with rule-based evaluation only")
            has_ml_model = False

    # Calculate metrics
    print("\n[STEP 3] Calculating metrics...")
    rules_metrics = calculate_metrics(y_true, y_pred_rules, "Rule-Based Engine")
    print_metrics_summary(rules_metrics)

    if has_ml_model:
        ml_metrics = calculate_metrics(y_true, y_pred_ml, "ML Model")
        print_metrics_summary(ml_metrics)

        # Generate comparison report
        print("[STEP 4] Generating comparison report...")
        generate_comparison_report(rules_metrics, ml_metrics, args.output)

        # Save JSON results
        results = {
            "evaluation_date": pd.Timestamp.now().isoformat(),
            "dataset_path": str(args.dataset),
            "dataset_size": len(df),
            "rule_based_engine": rules_metrics,
            "ml_model": ml_metrics,
        }

        with open(args.json_output, "w") as f:
            json.dump(results, f, indent=2)

        print(f"[INFO] JSON results saved to: {args.json_output}")
    else:
        print("\n[INFO] ML model not available, skipping comparison")
        print("[INFO] Only rule-based metrics calculated")

    print("\n✅ Evaluation complete!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
