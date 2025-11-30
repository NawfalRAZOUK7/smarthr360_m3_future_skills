# future_skills/management/commands/train_future_skills_model.py

"""
Management command to train the Future Skills ML model.

Wraps the ml/scripts/train_future_skills_model.py training script,
logging execution details to the TrainingRun database model.

Usage:
    python manage.py train_future_skills_model
    python manage.py train_future_skills_model --dataset ml/data/custom_dataset.csv
    python manage.py train_future_skills_model --version v2 --n-estimators 300
    python manage.py train_future_skills_model --test-split 0.25 --random-state 123
"""

import sys
from datetime import datetime
from pathlib import Path
import importlib.util

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from future_skills.models import TrainingRun

# Load the training module dynamically
ML_SCRIPTS_DIR = Path(settings.BASE_DIR) / "ml" / "scripts"
TRAIN_SCRIPT_PATH = ML_SCRIPTS_DIR / "train_future_skills_model.py"

spec = importlib.util.spec_from_file_location("train_module", TRAIN_SCRIPT_PATH)
train_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(train_module)


class Command(BaseCommand):
    help = "Train the Future Skills ML model and log execution to TrainingRun database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dataset",
            type=str,
            default=None,
            help="Path to the training dataset CSV (default: ml/data/future_skills_dataset.csv)",
        )
        parser.add_argument(
            "--model-version",
            type=str,
            default=None,
            help="Model version identifier (default: auto-generate based on timestamp)",
        )
        parser.add_argument(
            "--save-path",
            type=str,
            default=None,
            help="Path where model will be saved (default: settings.FUTURE_SKILLS_MODEL_PATH)",
        )
        parser.add_argument(
            "--test-split",
            type=float,
            default=0.2,
            help="Test set split ratio (default: 0.2 = 20%%)",
        )
        parser.add_argument(
            "--n-estimators",
            type=int,
            default=200,
            help="Number of trees in RandomForest (default: 200)",
        )
        parser.add_argument(
            "--random-state",
            type=int,
            default=42,
            help="Random seed for reproducibility (default: 42)",
        )
        parser.add_argument(
            "--notes",
            type=str,
            default="",
            help="Additional notes about this training run",
        )

    def handle(self, *args, **options):
        # Parse arguments
        dataset_path = options["dataset"]
        model_version = options["model_version"]
        save_path = options["save_path"]
        test_split = options["test_split"]
        n_estimators = options["n_estimators"]
        random_state = options["random_state"]
        notes = options["notes"]

        # Default paths
        base_dir = Path(settings.BASE_DIR)
        if dataset_path is None:
            dataset_path = base_dir / "ml" / "data" / "future_skills_dataset.csv"
        else:
            dataset_path = Path(dataset_path)

        if save_path is None:
            save_path = Path(settings.FUTURE_SKILLS_MODEL_PATH)
        else:
            save_path = Path(save_path)

        # Auto-generate version if not provided
        if model_version is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            model_version = f"v_{timestamp}"

        # Validate dataset exists
        if not dataset_path.exists():
            raise CommandError(f"Dataset not found: {dataset_path}")

        # Display training configuration
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write(self.style.SUCCESS("🚀 TRAINING FUTURE SKILLS ML MODEL"))
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write(f"📊 Dataset:       {dataset_path}")
        self.stdout.write(f"🏷️  Version:       {model_version}")
        self.stdout.write(f"💾 Save path:     {save_path}")
        self.stdout.write(f"🔀 Test split:    {test_split * 100:.0f}%")
        self.stdout.write(f"🌲 Estimators:    {n_estimators}")
        self.stdout.write(f"🎲 Random state:  {random_state}")
        if notes:
            self.stdout.write(f"📝 Notes:         {notes}")
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write("")

        # Record start time
        training_start = datetime.now()

        try:
            # Call the training function from ml/scripts/train_future_skills_model.py
            metadata = train_module.train_model(
                csv_path=dataset_path,
                output_model_path=save_path,
                model_version=model_version,
                test_size=test_split,
                random_state=random_state,
                n_estimators=n_estimators,
            )

            # Extract metrics from metadata
            training_end = datetime.now()
            training_duration = (training_end - training_start).total_seconds()

            # Prepare hyperparameters dict
            hyperparameters = {
                "n_estimators": n_estimators,
                "random_state": random_state,
                "test_size": test_split,
                "class_weight": "balanced",
            }

            # Create TrainingRun database record
            training_run = TrainingRun.objects.create(
                model_version=model_version,
                model_path=str(save_path),
                dataset_path=str(dataset_path),
                test_split=test_split,
                n_estimators=n_estimators,
                random_state=random_state,
                accuracy=metadata["metrics"]["accuracy"],
                precision=metadata["metrics"]["precision_weighted"],
                recall=metadata["metrics"]["recall_weighted"],
                f1_score=metadata["metrics"]["f1_weighted"],
                total_samples=metadata["dataset"]["total_samples"],
                train_samples=metadata["dataset"]["train_samples"],
                test_samples=metadata["dataset"]["test_samples"],
                training_duration_seconds=training_duration,
                per_class_metrics=metadata["metrics"].get("per_class", {}),
                features_used=metadata["dataset"].get("features_used", []),
                trained_by=None,  # CLI execution, no user
                notes=notes,
                status="COMPLETED",
                hyperparameters=hyperparameters,
            )

            # Success summary
            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS("=" * 70))
            self.stdout.write(self.style.SUCCESS("✅ TRAINING COMPLETED SUCCESSFULLY"))
            self.stdout.write(self.style.SUCCESS("=" * 70))
            self.stdout.write(f"🏷️  Version:      {model_version}")
            self.stdout.write(f"🎯 Accuracy:     {metadata['metrics']['accuracy']:.2%}")
            self.stdout.write(
                f"📊 Precision:    {metadata['metrics']['precision_weighted']:.2%}"
            )
            self.stdout.write(
                f"🎪 Recall:       {metadata['metrics']['recall_weighted']:.2%}"
            )
            self.stdout.write(
                f"🎭 F1-Score:     {metadata['metrics']['f1_weighted']:.2%}"
            )
            self.stdout.write(f"⏱️  Duration:     {training_duration:.1f} seconds")
            self.stdout.write(f"💾 Model saved:  {save_path}")
            self.stdout.write(f"🗄️  Database ID:  {training_run.id}")
            self.stdout.write(self.style.SUCCESS("=" * 70))

            # Per-class accuracy summary
            if "per_class" in metadata["metrics"]:
                self.stdout.write("")
                self.stdout.write("📈 Per-Class Metrics:")
                for level, metrics in metadata["metrics"]["per_class"].items():
                    acc = metrics["accuracy"]
                    support = metrics["support"]
                    self.stdout.write(f"   {level:7s}: {acc:.2%} (n={support})")

            self.stdout.write("")

        except Exception as e:
            # Log failed training run to database
            training_end = datetime.now()
            training_duration = (training_end - training_start).total_seconds()

            hyperparameters = {
                "n_estimators": n_estimators,
                "random_state": random_state,
                "test_size": test_split,
            }

            TrainingRun.objects.create(
                model_version=model_version,
                model_path=str(save_path),
                dataset_path=str(dataset_path),
                test_split=test_split,
                n_estimators=n_estimators,
                random_state=random_state,
                accuracy=0.0,
                precision=0.0,
                recall=0.0,
                f1_score=0.0,
                total_samples=0,
                train_samples=0,
                test_samples=0,
                training_duration_seconds=training_duration,
                trained_by=None,
                notes=notes,
                status="FAILED",
                error_message=str(e),
                hyperparameters=hyperparameters,
            )

            self.stdout.write(self.style.ERROR(f"❌ Training failed: {str(e)}"))
            self.stdout.write(
                self.style.ERROR(f"⏱️  Failed after: {training_duration:.1f} seconds")
            )
            raise CommandError(f"Training failed: {str(e)}")
