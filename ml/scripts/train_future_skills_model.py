# ml/train_future_skills_model.py

"""
Script d'entraînement du modèle ML pour le Module 3 - Future Skills.

- Charge le dataset CSV généré par la commande :
    python manage.py export_future_skills_dataset
- Construit un pipeline scikit-learn :
    - OneHotEncoder pour job_role_name et skill_name
    - StandardScaler pour les features numériques
    - RandomForestClassifier comme modèle de classification
- Enregistre le pipeline complet (préprocessing + modèle) dans :
    ml/future_skills_model_vX.pkl (avec versioning)
- Génère un fichier de métadonnées JSON pour traçabilité MLOps

Ce script est volontairement indépendant de Django (pas besoin de settings).
"""

import argparse
import json
import os
from datetime import datetime
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    accuracy_score,
    precision_recall_fscore_support,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


ALLOWED_LEVELS = {"LOW", "MEDIUM", "HIGH"}


def load_dataset(csv_path: Path) -> pd.DataFrame:
    if not csv_path.exists():
        raise FileNotFoundError(f"Dataset CSV introuvable : {csv_path}")

    df = pd.read_csv(csv_path)

    # Vérifier que la cible est bien présente
    if "future_need_level" not in df.columns:
        raise ValueError(
            "La colonne target 'future_need_level' est absente du dataset."
        )

    # Filtrer sur les niveaux autorisés (LOW / MEDIUM / HIGH)
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


def build_pipeline(categorical_features, numeric_features) -> Pipeline:
    """
    Construit un pipeline complet :
      - ColumnTransformer (OneHot + StandardScaler)
      - RandomForestClassifier
    """
    categorical_transformer = OneHotEncoder(
        handle_unknown="ignore"
    )

    numeric_transformer = StandardScaler()

    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", categorical_transformer, categorical_features),
            ("num", numeric_transformer, numeric_features),
        ]
    )

    clf = RandomForestClassifier(
        n_estimators=200,
        random_state=42,
        class_weight="balanced",
        n_jobs=-1,
    )

    pipeline = Pipeline(
        steps=[
            ("preprocess", preprocessor),
            ("clf", clf),
        ]
    )

    return pipeline


def train_model(
    csv_path: Path,
    output_model_path: Path,
    model_version: str = "v1",
    test_size: float = 0.2,
    random_state: int = 42,
    n_estimators: int = 200,
):
    """
    Train the Future Skills ML model and save with metadata.
    
    Args:
        csv_path: Path to the input dataset CSV
        output_model_path: Path where the model will be saved
        model_version: Version identifier (e.g., 'v1', 'v2', 'v2.1')
        test_size: Proportion of test set
        random_state: Random seed for reproducibility
        n_estimators: Number of trees in RandomForest
    """
    training_start_time = datetime.now()
    
    print(f"[INFO] Chargement du dataset : {csv_path}")
    df = load_dataset(csv_path)

    # Définir les features et la cible (UPDATED with new features)
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
        if df[col].dtype == 'object' or df[col].dtype.name == 'category':
            categorical_features.append(col)
        else:
            numeric_features.append(col)

    print(f"[INFO] Features catégorielles : {categorical_features}")
    print(f"[INFO] Features numériques : {numeric_features}")
    print(f"[INFO] Nombre total d'exemples : {len(df)}")
    print("[INFO] Répartition des classes :")
    print(y.value_counts())

    # Check for class imbalance
    class_counts = y.value_counts()
    imbalance_ratio = class_counts.max() / class_counts.min()
    print(f"[INFO] Ratio de déséquilibre : {imbalance_ratio:.2f}")
    if imbalance_ratio > 3:
        print("[WARN] Déséquilibre des classes détecté. Utilisation de class_weight='balanced'")

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=random_state,
        stratify=y,
    )

    print(f"[INFO] Taille train : {len(X_train)}, test : {len(X_test)}")

    # Build pipeline with custom n_estimators
    categorical_transformer = OneHotEncoder(handle_unknown="ignore")
    numeric_transformer = StandardScaler()

    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", categorical_transformer, categorical_features),
            ("num", numeric_transformer, numeric_features),
        ]
    )

    clf = RandomForestClassifier(
        n_estimators=n_estimators,
        random_state=random_state,
        class_weight="balanced",
        n_jobs=-1,
    )

    pipeline = Pipeline(
        steps=[
            ("preprocess", preprocessor),
            ("clf", clf),
        ]
    )

    print(f"[INFO] Entraînement du modèle RandomForestClassifier (n_estimators={n_estimators})...")
    pipeline.fit(X_train, y_train)

    training_end_time = datetime.now()
    training_duration = (training_end_time - training_start_time).total_seconds()

    # Evaluation
    print("[INFO] Évaluation sur le set de test :")
    y_pred = pipeline.predict(X_test)
    
    # Compute metrics
    accuracy = accuracy_score(y_test, y_pred)
    precision, recall, f1, support = precision_recall_fscore_support(
        y_test, y_pred, labels=["LOW", "MEDIUM", "HIGH"], average="weighted"
    )
    
    print("\nClassification report :")
    print(classification_report(y_test, y_pred, digits=4))

    print("\nMatrice de confusion :")
    cm = confusion_matrix(y_test, y_pred, labels=["LOW", "MEDIUM", "HIGH"])
    print(cm)
    
    # Calculate per-class metrics
    per_class_metrics = {}
    print("\nPrécision par classe :")
    for i, level in enumerate(["LOW", "MEDIUM", "HIGH"]):
        if cm.sum(axis=1)[i] > 0:
            class_accuracy = cm[i, i] / cm.sum(axis=1)[i]
            per_class_metrics[level] = {
                "accuracy": round(float(class_accuracy), 4),
                "support": int(support[i])
            }
            print(f"  {level}: {class_accuracy:.2%} (support: {support[i]})")

    # Feature importance
    clf = pipeline.named_steps["clf"]
    print(f"[INFO] Classes apprises par le modèle : {clf.classes_}")
    
    feature_importance_dict = {}
    if hasattr(clf, 'feature_importances_'):
        print("\n[INFO] Importance des features :")
        preprocessor = pipeline.named_steps["preprocess"]
        
        # Get feature names after preprocessing
        cat_features = []
        if categorical_features:
            cat_transformer = preprocessor.named_transformers_['cat']
            if hasattr(cat_transformer, 'get_feature_names_out'):
                cat_features = cat_transformer.get_feature_names_out(categorical_features).tolist()
        
        all_features = cat_features + numeric_features
        
        if len(all_features) == len(clf.feature_importances_):
            feature_importance = sorted(
                zip(all_features, clf.feature_importances_),
                key=lambda x: x[1],
                reverse=True
            )
            for feat, importance in feature_importance[:10]:  # Top 10
                print(f"  {feat}: {importance:.4f}")
                feature_importance_dict[feat] = float(importance)

    # Sauvegarde du pipeline complet
    output_model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, output_model_path)
    print(f"\n[SUCCESS] Modèle sauvegardé dans : {output_model_path}")

    # Generate and save metadata
    metadata = {
        "model_version": model_version,
        "training_date": training_start_time.isoformat(),
        "training_duration_seconds": round(training_duration, 2),
        "dataset": {
            "csv_path": str(csv_path),
            "total_samples": len(df),
            "train_samples": len(X_train),
            "test_samples": len(X_test),
            "features_used": available_features,
            "features_missing": missing_cols,
            "categorical_features": categorical_features,
            "numeric_features": numeric_features,
            "class_distribution": {k: int(v) for k, v in class_counts.items()},
            "imbalance_ratio": round(float(imbalance_ratio), 2),
        },
        "hyperparameters": {
            "n_estimators": n_estimators,
            "random_state": random_state,
            "test_size": test_size,
            "class_weight": "balanced",
        },
        "metrics": {
            "accuracy": round(float(accuracy), 4),
            "precision_weighted": round(float(precision), 4),
            "recall_weighted": round(float(recall), 4),
            "f1_weighted": round(float(f1), 4),
            "per_class": per_class_metrics,
        },
        "feature_importance_top10": dict(list(feature_importance_dict.items())[:10]),
        "model_classes": clf.classes_.tolist(),
    }

    # Save metadata JSON
    metadata_path = output_model_path.with_suffix('.json')
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    print(f"[SUCCESS] Métadonnées sauvegardées dans : {metadata_path}")
    print(f"[SUCCESS] Le modèle utilise {len(available_features)} features")
    
    return metadata


def main():
    base_dir = Path(__file__).resolve().parent.parent

    default_csv = base_dir / "data" / "future_skills_dataset.csv"
    default_model = base_dir / "models" / "future_skills_model.pkl"

    parser = argparse.ArgumentParser(
        description="Entraîne le modèle ML pour le Module 3 - Future Skills."
    )
    parser.add_argument(
        "--csv",
        type=str,
        default=str(default_csv),
        help=f"Chemin vers le dataset CSV (par défaut: {default_csv})",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=str(default_model),
        help=f"Chemin de sortie du modèle .pkl (par défaut: {default_model})",
    )
    parser.add_argument(
        "--version",
        type=str,
        default="v1",
        help="Version du modèle (ex: v1, v2, v2.1). Utilisé pour la traçabilité.",
    )
    parser.add_argument(
        "--test-size",
        type=float,
        default=0.2,
        help="Proportion du set de test (par défaut: 0.2).",
    )
    parser.add_argument(
        "--random-state",
        type=int,
        default=42,
        help="Seed aléatoire (par défaut: 42).",
    )
    parser.add_argument(
        "--n-estimators",
        type=int,
        default=200,
        help="Nombre d'arbres dans RandomForest (par défaut: 200).",
    )

    args = parser.parse_args()

    csv_path = Path(args.csv)
    output_model_path = Path(args.output)

    # If version is provided and output doesn't include version, add it
    if args.version and args.version not in output_model_path.stem:
        output_model_path = output_model_path.parent / f"{output_model_path.stem}_{args.version}.pkl"
        print(f"[INFO] Nom du modèle ajusté avec version : {output_model_path}")

    metadata = train_model(
        csv_path=csv_path,
        output_model_path=output_model_path,
        model_version=args.version,
        test_size=args.test_size,
        random_state=args.random_state,
        n_estimators=args.n_estimators,
    )
    
    print("\n" + "="*60)
    print("📊 RÉSUMÉ DE L'ENTRAÎNEMENT")
    print("="*60)
    print(f"Version: {metadata['model_version']}")
    print(f"Date: {metadata['training_date']}")
    print(f"Durée: {metadata['training_duration_seconds']}s")
    print(f"Précision: {metadata['metrics']['accuracy']:.2%}")
    print(f"F1-score: {metadata['metrics']['f1_weighted']:.4f}")
    print("="*60)


if __name__ == "__main__":
    main()
