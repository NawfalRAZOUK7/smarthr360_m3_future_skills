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
    ml/future_skills_model.pkl

Ce script est volontairement indépendant de Django (pas besoin de settings).
"""

import argparse
import os
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
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
    test_size: float = 0.2,
    random_state: int = 42,
):
    print(f"[INFO] Chargement du dataset : {csv_path}")
    df = load_dataset(csv_path)

    # Définir les features et la cible
    feature_cols = [
        "job_role_name",
        "skill_name",
        "trend_score",
        "internal_usage",
        "training_requests",
        "scarcity_index",
    ]
    target_col = "future_need_level"

    missing_cols = [c for c in feature_cols if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Colonnes manquantes dans le dataset : {missing_cols}")

    X = df[feature_cols].copy()
    y = df[target_col].copy()

    categorical_features = ["job_role_name", "skill_name"]
    numeric_features = [
        "trend_score",
        "internal_usage",
        "training_requests",
        "scarcity_index",
    ]

    print(f"[INFO] Nombre total d'exemples : {len(df)}")
    print("[INFO] Répartition des classes :")
    print(y.value_counts())

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=random_state,
        stratify=y,
    )

    print(f"[INFO] Taille train : {len(X_train)}, test : {len(X_test)}")

    pipeline = build_pipeline(
        categorical_features=categorical_features,
        numeric_features=numeric_features,
    )

    print("[INFO] Entraînement du modèle RandomForestClassifier...")
    pipeline.fit(X_train, y_train)

    print("[INFO] Évaluation sur le set de test :")
    y_pred = pipeline.predict(X_test)
    print("\nClassification report :")
    print(classification_report(y_test, y_pred, digits=4))

    print("Matrice de confusion :")
    print(confusion_matrix(y_test, y_pred, labels=["LOW", "MEDIUM", "HIGH"]))

    # Exemple : récupérer les classes pour info
    clf = pipeline.named_steps["clf"]
    print(f"[INFO] Classes apprises par le modèle : {clf.classes_}")

    # Sauvegarde du pipeline complet
    output_model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, output_model_path)

    print(f"[SUCCESS] Modèle sauvegardé dans : {output_model_path}")


def main():
    base_dir = Path(__file__).resolve().parent

    default_csv = base_dir / "future_skills_dataset.csv"
    default_model = base_dir / "future_skills_model.pkl"

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

    args = parser.parse_args()

    csv_path = Path(args.csv)
    output_model_path = Path(args.output)

    train_model(
        csv_path=csv_path,
        output_model_path=output_model_path,
        test_size=args.test_size,
        random_state=args.random_state,
    )


if __name__ == "__main__":
    main()
