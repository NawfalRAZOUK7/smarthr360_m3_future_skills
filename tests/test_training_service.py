#!/usr/bin/env python
"""
Test script for ModelTrainer service.

Run from Django shell:
    python manage.py shell < test_training_service.py

Or as a standalone test:
    python manage.py test_training_service
"""

import os
import sys

import django

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from pathlib import Path

from future_skills.services.training_service import DataLoadError, ModelTrainer, TrainingError


def test_training_service():
    """Test the ModelTrainer service."""

    print("=" * 70)
    print("Testing ModelTrainer Service")
    print("=" * 70)

    # Dataset path
    dataset_path = Path("ml/data/future_skills_dataset.csv")

    if not dataset_path.exists():
        print(f"❌ Dataset not found: {dataset_path}")
        return

    try:
        # Initialize trainer
        print("\n1️⃣  Initializing ModelTrainer...")
        trainer = ModelTrainer(
            dataset_path=str(dataset_path), test_split=0.2, random_state=42
        )
        print("✅ Trainer initialized")

        # Load data
        print("\n2️⃣  Loading data...")
        trainer.load_data()
        print(
            f"✅ Data loaded: {len(trainer.X_train)} train, {len(trainer.X_test)} test"
        )
        print(f"   Features: {len(trainer.available_features)}")
        print(f"   Categorical: {trainer.categorical_features}")
        print(f"   Numeric: {trainer.numeric_features}")

        # Train model
        print("\n3️⃣  Training model...")
        metrics = trainer.train(n_estimators=50)  # Small for testing
        print(f"✅ Training completed in {trainer.training_duration_seconds:.2f}s")
        print(f"   Accuracy:  {metrics['accuracy']:.2%}")
        print(f"   Precision: {metrics['precision']:.2%}")
        print(f"   Recall:    {metrics['recall']:.2%}")
        print(f"   F1-Score:  {metrics['f1_score']:.2%}")

        # Feature importance
        print("\n4️⃣  Extracting feature importance...")
        importance = trainer.get_feature_importance()
        print(f"✅ Got {len(importance)} feature importances")
        print("   Top 5:")
        for i, (feat, imp) in enumerate(list(importance.items())[:5]):
            print(f"     {i+1}. {feat}: {imp:.4f}")

        # Save model
        print("\n5️⃣  Saving model...")
        model_path = Path("ml/models/test_service_model.pkl")
        trainer.save_model(str(model_path))
        print(f"✅ Model saved: {model_path} ({model_path.stat().st_size} bytes)")

        # Save training run
        print("\n6️⃣  Saving training run to database...")
        training_run = trainer.save_training_run(
            model_version="test_service_v1",
            model_path=str(model_path),
            notes="Test run from training_service.py",
        )
        print(f"✅ Training run saved: ID={training_run.id}")
        print(f"   Status: {training_run.status}")
        print(f"   Hyperparameters: {training_run.hyperparameters}")

        print("\n" + "=" * 70)
        print("✅ ALL TESTS PASSED!")
        print("=" * 70)

        # Cleanup
        if model_path.exists():
            model_path.unlink()
            print(f"\n🧹 Cleaned up test model: {model_path}")

    except DataLoadError as e:
        print(f"\n❌ Data Load Error: {e}")
        sys.exit(1)
    except TrainingError as e:
        print(f"\n❌ Training Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    test_training_service()
