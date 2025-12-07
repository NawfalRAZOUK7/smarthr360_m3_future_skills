# ml/experiment_future_skills_models.py

"""
ML model experimentation script for Future Skills.

This script tests multiple ML algorithms on the same dataset to compare their performance:
- RandomForest (current baseline)
- XGBoost (optimized gradient boosting)
- LightGBM (fast and efficient gradient boosting)
- Logistic Regression (regularized linear model)

Objective: Demonstrate architecture extensibility and establish model selection
policy based on objective metrics.

Usage:
    python ml/scripts/experiment_future_skills_models.py --csv artifacts/datasets/future_skills_dataset.csv
"""

import argparse
import json
import logging
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
)
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Suppress warnings for cleaner output
warnings.filterwarnings("ignore")

ALLOWED_LEVELS = {"LOW", "MEDIUM", "HIGH"}
RANDOM_STATE = 42
MARKDOWN_SEPARATOR = "\n---\n\n"

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
DATASETS_DIR = ARTIFACTS_DIR / "datasets"
RESULTS_DIR = ARTIFACTS_DIR / "results"
JOBLIB_CACHE_DIR = ARTIFACTS_DIR / "cache" / "joblib"

for directory in (ARTIFACTS_DIR, DATASETS_DIR, RESULTS_DIR, JOBLIB_CACHE_DIR):
    directory.mkdir(parents=True, exist_ok=True)

DEFAULT_DATASET = DATASETS_DIR / "future_skills_dataset.csv"
DEFAULT_RESULTS_JSON = RESULTS_DIR / "experiment_results.json"
DEFAULT_MARKDOWN = RESULTS_DIR / "MODEL_COMPARISON.md"


def load_dataset(csv_path: Path) -> pd.DataFrame:
    """Load and validate the dataset."""
    if not csv_path.exists():
        raise FileNotFoundError(f"Dataset CSV introuvable : {csv_path}")

    df = pd.read_csv(csv_path)

    if "future_need_level" not in df.columns:
        raise ValueError(
            "La colonne target 'future_need_level' est absente du dataset."
        )

    before = len(df)
    df = df[df["future_need_level"].isin(ALLOWED_LEVELS)].copy()
    after = len(df)

    if after == 0:
        raise ValueError(
            "Aucune ligne valide avec future_need_level dans {LOW, MEDIUM, HIGH}."
        )

    if after < before:
        print(
            f"[WARN] {before - after} ligne(s) ignorée(s) car future_need_level "
            f"n'était pas dans {ALLOWED_LEVELS}."
        )

    return df


def prepare_data(
    df: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.Series, List[str], List[str]]:
    """Prepare features and target, identify categorical and numeric features."""

    feature_cols = [
        "job_role_name",
        "skill_name",
        "skill_category",
        "job_department",
        "trend_score",
        "internal_usage",
        "training_requests",
        "scarcity_index",
        "hiring_difficulty",
        "avg_salary_k",
        "economic_indicator",
    ]
    target_col = "future_need_level"

    # Check for missing columns and use available ones
    available_features = [c for c in feature_cols if c in df.columns]
    missing_cols = [c for c in feature_cols if c not in df.columns]

    if missing_cols:
        print(f"[WARN] Colonnes manquantes (ignorées) : {missing_cols}")

    if not available_features:
        raise ValueError("Aucune feature disponible dans le dataset!")

    X = df[available_features].copy()
    y = df[target_col].copy()

    # Identify categorical and numeric features dynamically
    categorical_features = []
    numeric_features = []

    for col in available_features:
        if df[col].dtype == "object" or df[col].dtype.name == "category":
            categorical_features.append(col)
        else:
            numeric_features.append(col)

    return X, y, categorical_features, numeric_features


def create_preprocessor(
    categorical_features: List[str], numeric_features: List[str]
) -> ColumnTransformer:
    """Create the preprocessing pipeline."""
    categorical_transformer = OneHotEncoder(handle_unknown="ignore")
    numeric_transformer = StandardScaler()

    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", categorical_transformer, categorical_features),
            ("num", numeric_transformer, numeric_features),
        ]
    )

    return preprocessor


def get_models_to_test() -> Dict[str, Dict[str, Any]]:
    """
    Define all models to test with their configurations.

    Returns:
        Dict with model name as key and dict containing 'estimator' and 'params'.
    """
    models = {
        "RandomForest": {
            "estimator": RandomForestClassifier(
                n_estimators=200,
                random_state=RANDOM_STATE,
                class_weight="balanced",
                n_jobs=-1,
            ),
            "params": {
                "n_estimators": 200,
                "max_depth": None,
                "class_weight": "balanced",
            },
            "description": "Baseline actuelle - Ensemble d'arbres de décision",
        },
        "RandomForest_tuned": {
            "estimator": RandomForestClassifier(
                n_estimators=300,
                max_depth=20,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=RANDOM_STATE,
                class_weight="balanced",
                n_jobs=-1,
            ),
            "params": {
                "n_estimators": 300,
                "max_depth": 20,
                "min_samples_split": 5,
                "min_samples_leaf": 2,
                "class_weight": "balanced",
            },
            "description": "RandomForest avec hyperparamètres ajustés",
        },
        "LogisticRegression": {
            "estimator": LogisticRegression(
                random_state=RANDOM_STATE,
                max_iter=1000,
                class_weight="balanced",
                multi_class="multinomial",
                solver="lbfgs",
                C=1.0,
            ),
            "params": {
                "C": 1.0,
                "max_iter": 1000,
                "class_weight": "balanced",
                "multi_class": "multinomial",
            },
            "description": "Modèle linéaire régularisé - Simple et rapide",
        },
    }

    # Try to import XGBoost
    try:
        import xgboost as xgb

        models["XGBoost"] = {
            "estimator": xgb.XGBClassifier(
                n_estimators=200,
                learning_rate=0.1,
                max_depth=6,
                random_state=RANDOM_STATE,
                eval_metric="mlogloss",
                use_label_encoder=False,
            ),
            "params": {
                "n_estimators": 200,
                "learning_rate": 0.1,
                "max_depth": 6,
            },
            "description": "Gradient Boosting optimisé - Haute performance",
        }
    except Exception as e:
        logger.warning(f"XGBoost not available: {type(e).__name__}")
        logger.info(
            "To use XGBoost: pip install xgboost && brew install libomp (macOS)"
        )

    # Try to import LightGBM
    try:
        import lightgbm as lgb

        models["LightGBM"] = {
            "estimator": lgb.LGBMClassifier(
                n_estimators=200,
                learning_rate=0.1,
                max_depth=6,
                random_state=RANDOM_STATE,
                class_weight="balanced",
                verbose=-1,
            ),
            "params": {
                "n_estimators": 200,
                "learning_rate": 0.1,
                "max_depth": 6,
                "class_weight": "balanced",
            },
            "description": "Gradient Boosting rapide et efficace en mémoire",
        }
    except Exception as e:
        logger.warning(f"LightGBM not available: {type(e).__name__}")
        logger.info("To use LightGBM: pip install lightgbm")

    return models


def train_and_evaluate_model(
    model_name: str,
    model_config: Dict[str, Any],
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    y_train: pd.Series,
    y_test: pd.Series,
    preprocessor: ColumnTransformer,
    class_labels: List[str],
) -> Dict[str, Any]:
    """
    Train a model and compute all evaluation metrics.

    Args:
        class_labels: List of class labels present in the dataset (e.g., ['LOW', 'MEDIUM', 'HIGH'])

    Returns:
        Dictionary with all metrics and model information.
    """
    logger.info(f"\n{'=' * 70}")
    logger.info(f"🔬 Experimentation: {model_name}")
    logger.info(f"   Description: {model_config['description']}")
    logger.info(f"{'=' * 70}")

    start_time = datetime.now()

    # Create pipeline
    pipeline = Pipeline(
        steps=[
            ("preprocess", preprocessor),
            ("clf", model_config["estimator"]),
        ],
        memory=str(JOBLIB_CACHE_DIR),  # Cache transformers for better performance
    )

    # Train
    print("[INFO] Entraînement en cours...")
    pipeline.fit(X_train, y_train)

    training_time = (datetime.now() - start_time).total_seconds()

    # Predict
    y_pred = pipeline.predict(X_test)

    # Compute metrics
    accuracy = accuracy_score(y_test, y_pred)

    # Compute per-class metrics first
    precision_per_class, recall_per_class, f1_per_class, support = (
        precision_recall_fscore_support(
            y_test, y_pred, labels=class_labels, average=None
        )
    )

    # Compute weighted metrics
    precision_weighted, recall_weighted, f1_weighted, _ = (
        precision_recall_fscore_support(
            y_test, y_pred, labels=class_labels, average="weighted"
        )
    )

    # Per-class metrics
    cm = confusion_matrix(y_test, y_pred, labels=class_labels)
    per_class_metrics = {}

    for i, level in enumerate(class_labels):
        if cm.sum(axis=1)[i] > 0:
            class_accuracy = cm[i, i] / cm.sum(axis=1)[i]
            per_class_metrics[level] = {
                "accuracy": round(float(class_accuracy), 4),
                "support": int(support[i]),
                "precision": round(float(precision_per_class[i]), 4),
                "recall": round(float(recall_per_class[i]), 4),
                "f1": round(float(f1_per_class[i]), 4),
            }

    # Cross-validation score (on train set for comparison)
    logger.info("Cross-validation (5-fold) in progress...")
    cv_scores = cross_val_score(
        pipeline, X_train, y_train, cv=5, scoring="f1_weighted", n_jobs=-1
    )
    cv_mean = cv_scores.mean()
    cv_std = cv_scores.std()

    # Print results
    logger.info("\n📊 Results:")
    logger.info(f"   • Accuracy        : {accuracy:.4f}")
    logger.info(f"   • Precision (W)   : {precision_weighted:.4f}")
    logger.info(f"   • Recall (W)      : {recall_weighted:.4f}")
    logger.info(f"   • F1-score (W)    : {f1_weighted:.4f}")
    logger.info(f"   • CV F1-score     : {cv_mean:.4f} (+/- {cv_std:.4f})")
    logger.info(f"   • Training time   : {training_time:.2f}s")

    logger.info("\n📈 Per-class accuracy:")
    for level, metrics in per_class_metrics.items():
        logger.info(
            f"   • {level:7s} : {metrics['accuracy']:.2%} (n={metrics['support']})"
        )

    # Classification report
    logger.info("\n📋 Classification Report:")
    logger.info("\n" + classification_report(y_test, y_pred, digits=4))

    # Confusion matrix
    logger.info("🔲 Confusion Matrix:")

    # Dynamic header based on actual classes
    header = "   Prediction → |"
    for label in class_labels:
        header += f" {label[:3]:3s} |"
    logger.info(header)
    logger.info("   " + "-" * (len(header) - 4))

    for i, level in enumerate(class_labels):
        row = f"   {level:7s}    |"
        for j in range(len(class_labels)):
            row += f" {cm[i, j]:3d} |"
        logger.info(row)

    # Return all metrics
    results = {
        "model_name": model_name,
        "description": model_config["description"],
        "hyperparameters": model_config["params"],
        "metrics": {
            "accuracy": round(float(accuracy), 4),
            "precision_weighted": round(float(precision_weighted), 4),
            "recall_weighted": round(float(recall_weighted), 4),
            "f1_weighted": round(float(f1_weighted), 4),
            "cv_f1_mean": round(float(cv_mean), 4),
            "cv_f1_std": round(float(cv_std), 4),
            "per_class": per_class_metrics,
        },
        "training_time_seconds": round(training_time, 2),
        "confusion_matrix": cm.tolist(),
    }

    return results


def save_results(results: List[Dict[str, Any]], output_path: Path):
    """Save experiment results to JSON file."""
    experiment_data = {
        "experiment_date": datetime.now().isoformat(),
        "random_state": RANDOM_STATE,
        "test_size": 0.2,
        "models_tested": len(results),
        "results": results,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(experiment_data, f, indent=2, ensure_ascii=False)

    logger.info(f"\n✅ Results saved to: {output_path}")


def _build_main_comparison_table(sorted_results: list) -> str:
    """Build the main comparison table section."""
    md = "| Rang | Modèle | Accuracy | Precision | Recall | F1-Score | CV F1 (±std) | Temps (s) |\n"
    md += "|------|--------|----------|-----------|--------|----------|--------------|----------|\n"

    for i, result in enumerate(sorted_results, 1):
        metrics = result["metrics"]
        # Assign medal based on rank
        if i == 1:
            medal = "🥇"
        elif i == 2:
            medal = "🥈"
        elif i == 3:
            medal = "🥉"
        else:
            medal = f"{i}."

        md += f"| {medal} | **{result['model_name']}** | "
        md += f"{metrics['accuracy']:.4f} | "
        md += f"{metrics['precision_weighted']:.4f} | "
        md += f"{metrics['recall_weighted']:.4f} | "
        md += f"{metrics['f1_weighted']:.4f} | "
        md += f"{metrics['cv_f1_mean']:.4f} (±{metrics['cv_f1_std']:.4f}) | "
        md += f"{result['training_time_seconds']:.2f} |\n"

    return md


def _add_best_model_highlight(best_model: dict) -> str:
    """Add best model highlight section."""
    md = f"\n### 🏆 Meilleur Modèle : {best_model['model_name']}\n\n"
    md += f"- **F1-Score** : {best_model['metrics']['f1_weighted']:.4f}\n"
    md += f"- **Accuracy** : {best_model['metrics']['accuracy']:.4f}\n"
    md += f"- **Description** : {best_model['description']}\n"
    md += f"- **Temps d'entraînement** : {best_model['training_time_seconds']:.2f}s\n\n"
    return md


def _add_per_class_performance(sorted_results: list, class_labels: list) -> str:
    """Add per-class performance section."""
    md = MARKDOWN_SEPARATOR
    md += "## 📈 Performance par Classe\n\n"

    for level in class_labels:
        md += f"### Classe : {level}\n\n"
        md += "| Modèle | Accuracy | Support |\n"
        md += "|--------|----------|----------|\n"

        for result in sorted_results:
            if level in result["metrics"]["per_class"]:
                pc = result["metrics"]["per_class"][level]
                md += f"| {result['model_name']} | {pc['accuracy']:.2%} | {pc['support']} |\n"

        md += "\n"

    return md


def _add_model_configurations(sorted_results: list) -> str:
    """Add detailed model configurations section."""
    md = MARKDOWN_SEPARATOR
    md += "## ⚙️ Configurations des Modèles\n\n"

    for result in sorted_results:
        md += f"### {result['model_name']}\n\n"
        md += f"**Description** : {result['description']}\n\n"
        md += "**Hyperparamètres** :\n"
        for param, value in result["hyperparameters"].items():
            md += f"- `{param}` = {value}\n"
        md += "\n"

    return md


def _add_recommendations_section(best_model: dict, results: list) -> str:
    """Add recommendations section."""
    md = MARKDOWN_SEPARATOR
    md += "## 💡 Recommandations\n\n"
    md += "### Choix du Modèle en Production\n\n"

    best_f1 = best_model["metrics"]["f1_weighted"]
    baseline = next((r for r in results if r["model_name"] == "RandomForest"), None)

    if baseline:
        baseline_f1 = baseline["metrics"]["f1_weighted"]
        improvement = ((best_f1 - baseline_f1) / baseline_f1) * 100

        md += f"**Baseline (RandomForest)** : F1-score = {baseline_f1:.4f}\n\n"

        if best_model["model_name"] != "RandomForest":
            md += f"**Meilleure alternative** : {best_model['model_name']} "
            md += f"(amélioration de {improvement:+.2f}%)\n\n"
        else:
            md += "**Conclusion** : RandomForest reste le meilleur choix.\n\n"

    md += "### Critères de Sélection\n\n"
    md += "1. **Performance** : F1-score pondéré (objectif principal)\n"
    md += "2. **Stabilité** : Variance du cross-validation (CV std faible préféré)\n"
    md += "3. **Interprétabilité** : Capacité à expliquer les prédictions (important pour l'audit)\n"
    md += "4. **Temps d'entraînement** : Contraintes de réentraînement régulier\n"
    md += "5. **Maintenance** : Simplicité de mise à jour et de déploiement\n\n"

    md += "### Politique de Choix de Modèle\n\n"
    md += "**Le modèle RandomForest est actuellement retenu pour les raisons suivantes** :\n\n"
    md += "- ✅ **Stabilité** : Performance robuste sur différents ensembles de validation\n"
    md += "- ✅ **Simplicité** : Pas de dépendances complexes (pure scikit-learn)\n"
    md += "- ✅ **Interprétabilité** : Feature importance facilement calculable\n"
    md += "- ✅ **Maintenance** : Entraînement et déploiement simples\n"
    md += "- ✅ **Pas de sur-apprentissage** : Bonne généralisation grâce à l'ensemble d'arbres\n\n"

    md += "**Architecture extensible** :\n\n"
    md += "L'architecture de la pipeline supporte le remplacement par un autre modèle "
    md += "tant que l'interface de prédiction `(level: LOW/MEDIUM/HIGH, score: 0-100)` reste identique.\n\n"

    md += "Pour changer de modèle, il suffit de :\n"
    md += "1. Remplacer l'estimateur dans `ml/scripts/train_future_skills_model.py`\n"
    md += "2. Réentraîner avec `python ml/scripts/train_future_skills_model.py`\n"
    md += "3. Recharger le nouveau modèle dans `future_skills/ml_model.py`\n"
    md += "4. Aucun changement nécessaire dans les APIs ou la logique métier\n\n"

    md += MARKDOWN_SEPARATOR
    md += "## 🔄 Prochaines Étapes\n\n"
    md += "- [ ] Tester l'hyperparameter tuning (GridSearch/RandomSearch)\n"
    md += "- [ ] Évaluer l'impact de features additionnelles\n"
    md += "- [ ] Monitorer les performances en production\n"
    md += "- [ ] Définir un seuil de dégradation pour déclencher un réentraînement\n"

    return md


def generate_comparison_table(
    results: List[Dict[str, Any]], class_labels: List[str]
) -> str:
    """Generate a markdown table comparing all models."""

    if not results:
        return "# ⚠️ Aucun résultat d'expérimentation disponible\n\nAucun modèle n'a pu être entraîné avec succès.\n"

    # Sort by F1-score
    sorted_results = sorted(
        results, key=lambda x: x["metrics"]["f1_weighted"], reverse=True
    )

    md = "# 🔬 Comparaison des Modèles - Future Skills Prediction\n\n"
    md += f"**Date de l'expérimentation** : {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
    md += MARKDOWN_SEPARATOR
    md += "## 📊 Tableau Comparatif Global\n\n"

    # Main comparison table
    md += _build_main_comparison_table(sorted_results)

    # Best model highlight
    best_model = sorted_results[0]
    md += _add_best_model_highlight(best_model)

    # Per-class performance
    md += _add_per_class_performance(sorted_results, class_labels)

    # Model configurations
    md += _add_model_configurations(sorted_results)

    # Recommendations
    md += _add_recommendations_section(best_model, results)

    return md


def main():
    parser = argparse.ArgumentParser(
        description="Expérimente plusieurs modèles ML pour Future Skills."
    )
    parser.add_argument(
        "--csv",
        type=str,
        default=str(DEFAULT_DATASET),
        help=f"Chemin vers le dataset CSV (par défaut: {DEFAULT_DATASET})",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=str(DEFAULT_RESULTS_JSON),
        help="Output path for JSON results.",
    )
    parser.add_argument(
        "--markdown",
        type=str,
        default=str(DEFAULT_MARKDOWN),
        help="Output path for markdown report.",
    )

    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("🔬 MODEL EXPERIMENTATION - FUTURE SKILLS PREDICTION")
    logger.info("=" * 70)
    logger.info(f"Dataset: {args.csv}")
    logger.info(f"Random state: {RANDOM_STATE}")
    logger.info("=" * 70)

    # Load and prepare data
    csv_path = Path(args.csv)
    df = load_dataset(csv_path)

    X, y, categorical_features, numeric_features = prepare_data(df)

    print("\n📊 Informations du Dataset :")
    print(f"   • Nombre d'exemples : {len(df)}")
    print(f"   • Features catégorielles : {categorical_features}")
    print(f"   • Features numériques : {numeric_features}")
    print("\n📈 Distribution des classes :")
    for level, count in y.value_counts().items():
        print(f"   • {level:7s} : {count:4d} ({count / len(y) * 100:.1f}%)")

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_STATE, stratify=y
    )

    print(f"\n✂️  Split : Train={len(X_train)}, Test={len(X_test)}")

    # Create preprocessor (shared by all models)
    preprocessor = create_preprocessor(categorical_features, numeric_features)

    # Get all models to test
    models = get_models_to_test()

    print(f"\n🎯 Modèles à tester : {list(models.keys())}")

    # Get class labels from the data
    class_labels = sorted(y.unique().tolist())
    print(f"📌 Classes détectées : {class_labels}")

    # Train and evaluate each model
    all_results = []

    for model_name, model_config in models.items():
        try:
            results = train_and_evaluate_model(
                model_name=model_name,
                model_config=model_config,
                X_train=X_train,
                X_test=X_test,
                y_train=y_train,
                y_test=y_test,
                preprocessor=preprocessor,
                class_labels=class_labels,
            )
            all_results.append(results)
        except Exception as e:
            print(f"\n❌ Erreur lors de l'entraînement de {model_name} : {e}")
            import traceback

            traceback.print_exc()
            continue

    if not all_results:
        print("\n❌ ERREUR : Aucun modèle n'a pu être entraîné avec succès!")
        return

    # Save results
    output_path = Path(args.output)
    save_results(all_results, output_path)

    # Generate markdown report
    markdown_path = Path(args.markdown)
    markdown_content = generate_comparison_table(all_results, class_labels)

    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    with open(markdown_path, "w", encoding="utf-8") as f:
        f.write(markdown_content)

    print(f"✅ Rapport markdown sauvegardé dans : {markdown_path}")

    # Print summary
    print("\n" + "=" * 70)
    print("📊 RÉSUMÉ DE L'EXPÉRIMENTATION")
    print("=" * 70)

    sorted_results = sorted(
        all_results, key=lambda x: x["metrics"]["f1_weighted"], reverse=True
    )

    print("\n🏆 Classement par F1-score :\n")
    for i, result in enumerate(sorted_results, 1):
        # Assign medal based on rank
        if i == 1:
            medal = "🥇"
        elif i == 2:
            medal = "🥈"
        elif i == 3:
            medal = "🥉"
        else:
            medal = f"{i}."
        f1 = result["metrics"]["f1_weighted"]
        acc = result["metrics"]["accuracy"]
        time = result["training_time_seconds"]
        print(
            f"   {medal} {result['model_name']:20s} | F1={f1:.4f} | Acc={acc:.4f} | {time:.2f}s"
        )

    print("\n" + "=" * 70)
    print("✅ Expérimentation terminée avec succès!")
    print("=" * 70)


if __name__ == "__main__":
    main()
