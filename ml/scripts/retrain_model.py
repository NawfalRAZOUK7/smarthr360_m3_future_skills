#!/usr/bin/env python3
"""
Script d'orchestration pour le retraining automatisé du modèle Future Skills.

Ce script automatise le workflow complet:
1. Export du dataset depuis la base de données
2. Entraînement du modèle avec versioning
3. Génération des métadonnées
4. Mise à jour du registre des modèles

Usage:
    python ml/retrain_model.py --version v2
    python ml/retrain_model.py --version v2 --n-estimators 300 --auto-update-settings
"""

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def run_command(cmd: list, description: str) -> int:
    """Execute a shell command and return exit code."""
    print(f"\n{'='*60}")
    print(f"🔄 {description}")
    print(f"{'='*60}")
    print(f"Commande: {' '.join(cmd)}\n")

    result = subprocess.run(cmd, capture_output=False)

    if result.returncode != 0:
        print(f"\n❌ ERREUR: {description} a échoué (code {result.returncode})")
        return result.returncode

    print(f"\n✅ {description} terminé avec succès")
    return 0


def update_settings_file(model_version: str, model_path: Path):
    """Update config/settings.py with new model version and path."""
    settings_path = Path(__file__).resolve().parent.parent / "config" / "settings.py"

    if not settings_path.exists():
        print(f"⚠️  Fichier settings.py introuvable: {settings_path}")
        return False

    with open(settings_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Update FUTURE_SKILLS_MODEL_VERSION
    import re

    content = re.sub(
        r'FUTURE_SKILLS_MODEL_VERSION\s*=\s*["\'][^"\']* ["\']',
        f'FUTURE_SKILLS_MODEL_VERSION = "ml_random_forest_{model_version}"',
        content,
    )

    # Update FUTURE_SKILLS_MODEL_PATH
    model_filename = model_path.name
    content = re.sub(
        r'FUTURE_SKILLS_MODEL_PATH\s*=\s*BASE_DIR\s*/\s*"ml"\s*/\s*"[^"]*"',
        f'FUTURE_SKILLS_MODEL_PATH = BASE_DIR / "ml" / "{model_filename}"',
        content,
    )

    with open(settings_path, "w", encoding="utf-8") as f:
        f.write(content)

    print("✅ settings.py mis à jour:")
    print(f"   - FUTURE_SKILLS_MODEL_VERSION = 'ml_random_forest_{model_version}'")
    print(f"   - FUTURE_SKILLS_MODEL_PATH = BASE_DIR / 'ml' / '{model_filename}'")
    return True


def update_registry(metadata_path: Path):
    """Add entry to MODEL_REGISTRY.md for the new model version."""
    registry_path = Path(__file__).resolve().parent / "MODEL_REGISTRY.md"

    if not registry_path.exists():
        print(f"⚠️  Fichier MODEL_REGISTRY.md introuvable: {registry_path}")
        return False

    # Read metadata
    import json

    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    version = metadata["model_version"]
    date = datetime.fromisoformat(metadata["training_date"]).strftime("%Y-%m-%d")
    samples = metadata["dataset"]["total_samples"]
    accuracy = metadata["metrics"]["accuracy"] * 100
    f1_score = metadata["metrics"]["f1_weighted"]
    n_estimators = metadata["hyperparameters"]["n_estimators"]

    # Create registry entry
    new_entry = f"| {version} | {date} | future_skills_dataset.csv | {samples} | {accuracy:.2f}% | {f1_score:.4f} | {n_estimators} | Auto-generated |"

    # Read registry
    with open(registry_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Find insertion point (after table header)
    insert_idx = None
    for i, line in enumerate(lines):
        if line.startswith("| Version | Date"):
            # Skip the header separator line
            insert_idx = i + 2
            break

    if insert_idx is None:
        print("⚠️  Impossible de trouver le tableau dans MODEL_REGISTRY.md")
        return False

    # Insert new entry
    lines.insert(insert_idx, new_entry + "\n")

    # Write back
    with open(registry_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"✅ MODEL_REGISTRY.md mis à jour avec la version {version}")
    return True


def main():
    base_dir = Path(__file__).resolve().parent
    project_root = base_dir.parent

    parser = argparse.ArgumentParser(description="Orchestration complète du retraining du modèle Future Skills")
    parser.add_argument("--version", type=str, required=True, help="Version du modèle (ex: v2, v3, v2.1)")
    parser.add_argument("--n-estimators", type=int, default=200, help="Nombre d'arbres dans RandomForest (défaut: 200)")
    parser.add_argument("--test-size", type=float, default=0.2, help="Proportion du set de test (défaut: 0.2)")
    parser.add_argument(
        "--auto-update-settings",
        action="store_true",
        help="Mise à jour automatique de config/settings.py avec la nouvelle version",
    )
    parser.add_argument(
        "--skip-export", action="store_true", help="Sauter l'export du dataset (utiliser le CSV existant)"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("🚀 RETRAINING AUTOMATISÉ - FUTURE SKILLS ML")
    print("=" * 60)
    print(f"Version cible: {args.version}")
    print(f"N_estimators: {args.n_estimators}")
    print(f"Test size: {args.test_size}")
    print(f"Auto-update settings: {args.auto_update_settings}")
    print("=" * 60)

    # Step 1: Export dataset (unless skipped)
    if not args.skip_export:
        export_cmd = [sys.executable, str(project_root / "manage.py"), "export_future_skills_dataset"]

        if run_command(export_cmd, "Étape 1/3: Export du dataset") != 0:
            print("\n❌ Retraining interrompu à l'étape 1")
            return 1
    else:
        print("\n⏭️  Étape 1/3: Export du dataset (SKIP)")

    # Step 2: Train model
    model_path = base_dir / "models" / f"future_skills_model_{args.version}.pkl"

    train_cmd = [
        sys.executable,
        str(base_dir / "scripts" / "train_future_skills_model.py"),
        "--csv",
        str(base_dir / "data" / "future_skills_dataset.csv"),
        "--output",
        str(base_dir / "models" / f"future_skills_model_{args.version}.pkl"),
        "--version",
        args.version,
        "--n-estimators",
        str(args.n_estimators),
        "--test-size",
        str(args.test_size),
    ]

    if run_command(train_cmd, "Étape 2/3: Entraînement du modèle") != 0:
        print("\n❌ Retraining interrompu à l'étape 2")
        return 1

    # Step 3: Update registry and optionally settings
    print(f"\n{'='*60}")
    print("📝 Étape 3/3: Mise à jour de la documentation")
    print(f"{'='*60}")

    metadata_path = model_path.with_suffix(".json")

    if not metadata_path.exists():
        print(f"⚠️  Fichier de métadonnées introuvable: {metadata_path}")
    else:
        update_registry(metadata_path)

    if args.auto_update_settings:
        print("\n🔧 Mise à jour automatique de config/settings.py...")
        update_settings_file(args.version, model_path)
        print("\n⚠️  ATTENTION: Redémarrez le serveur Django pour appliquer les changements!")
    else:
        print("\n💡 Pour déployer ce modèle en production, mettez à jour manuellement:")
        print("   - config/settings.py:")
        print(f"     FUTURE_SKILLS_MODEL_VERSION = 'ml_random_forest_{args.version}'")
        print(f"     FUTURE_SKILLS_MODEL_PATH = BASE_DIR / 'ml' / '{model_path.name}'")

    print("\n" + "=" * 60)
    print("✅ RETRAINING TERMINÉ AVEC SUCCÈS")
    print("=" * 60)
    print(f"📦 Modèle: {model_path}")
    print(f"📊 Métadonnées: {metadata_path}")
    print("📋 Registre: ml/MODEL_REGISTRY.md")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
