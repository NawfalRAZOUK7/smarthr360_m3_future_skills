# future_skills/services/training_service.py

"""
Training Service for Future Skills ML Model.

Provides a clean OOP interface for training ML models with proper error handling,
logging, and integration with Django's TrainingRun model for MLOps tracking.
"""

import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import joblib
import pandas as pd
from django.conf import settings
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from future_skills.models import TrainingRun

logger = logging.getLogger(__name__)


class ModelTrainerError(Exception):
    """Base exception for ModelTrainer errors."""
    pass


class DataLoadError(ModelTrainerError):
    """Exception raised when data loading fails."""
    pass


class TrainingError(ModelTrainerError):
    """Exception raised when model training fails."""
    pass


class ModelTrainer:
    """
    ML Model Trainer for Future Skills prediction.

    Handles the complete training lifecycle:
    - Data loading and validation
    - Model training with hyperparameter tuning
    - Evaluation and metrics collection
    - Model persistence
    - MLOps tracking via TrainingRun model

    Example:
        >>> trainer = ModelTrainer(
        ...     dataset_path="ml/data/future_skills_dataset.csv",
        ...     test_split=0.2
        ... )
        >>> trainer.load_data()
        >>> metrics = trainer.train(n_estimators=200, random_state=42)
        >>> trainer.save_model("ml/models/future_skills_model.pkl")
        >>> trainer.save_training_run(model_version="v1.0", user=request.user)
    """

    ALLOWED_LEVELS = {"LOW", "MEDIUM", "HIGH"}
    TARGET_COLUMN = "future_need_level"

    FEATURE_COLUMNS = [
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

    def __init__(
        self,
        dataset_path: str,
        test_split: float = 0.2,
        random_state: int = 42
    ):
        """
        Initialize ModelTrainer.

        Args:
            dataset_path: Path to the training dataset CSV
            test_split: Proportion of data for test set (0.0 to 1.0)
            random_state: Random seed for reproducibility
        """
        self.dataset_path = Path(dataset_path)
        self.test_split = test_split
        self.random_state = random_state

        # Data containers
        self.df: Optional[pd.DataFrame] = None
        self.X_train: Optional[pd.DataFrame] = None
        self.X_test: Optional[pd.DataFrame] = None
        self.y_train: Optional[pd.Series] = None
        self.y_test: Optional[pd.Series] = None
        self.available_features: List[str] = []
        self.missing_features: List[str] = []
        self.categorical_features: List[str] = []
        self.numeric_features: List[str] = []

        # Model and metrics
        self.model: Optional[Pipeline] = None
        self.metrics: Dict[str, Any] = {}
        self.per_class_metrics: Dict[str, Dict[str, float]] = {}
        self.feature_importance: Dict[str, float] = {}

        # Training tracking
        self.training_start_time: Optional[datetime] = None
        self.training_end_time: Optional[datetime] = None
        self.training_duration_seconds: float = 0.0
        self.hyperparameters: Dict[str, Any] = {}

        logger.info(f"ModelTrainer initialized: dataset={dataset_path}, test_split={test_split}")

    def load_data(self) -> None:
        """
        Load and preprocess dataset from CSV.

        Validates data, filters invalid target values, identifies feature types,
        and splits into train/test sets.

        Raises:
            DataLoadError: If dataset is not found or invalid
        """
        logger.info(f"Loading dataset from: {self.dataset_path}")

        if not self.dataset_path.exists():
            raise DataLoadError(f"Dataset not found: {self.dataset_path}")

        try:
            # Load CSV
            self.df = pd.read_csv(self.dataset_path)
            logger.info(f"Loaded {len(self.df)} rows")

            # Validate target column
            if self.TARGET_COLUMN not in self.df.columns:
                raise DataLoadError(
                    f"Target column '{self.TARGET_COLUMN}' not found in dataset. "
                    f"Available columns: {list(self.df.columns)}"
                )

            # Filter valid target levels
            before_count = len(self.df)
            self.df = self.df[self.df[self.TARGET_COLUMN].isin(self.ALLOWED_LEVELS)].copy()
            after_count = len(self.df)

            if after_count == 0:
                raise DataLoadError(
                    f"No valid rows with {self.TARGET_COLUMN} in {self.ALLOWED_LEVELS}"
                )

            if after_count < before_count:
                filtered = before_count - after_count
                logger.warning(f"Filtered {filtered} rows with invalid target values")

            # Identify available features
            self.available_features = [
                col for col in self.FEATURE_COLUMNS if col in self.df.columns
            ]
            self.missing_features = [
                col for col in self.FEATURE_COLUMNS if col not in self.df.columns
            ]

            if not self.available_features:
                raise DataLoadError("No features available in dataset")

            if self.missing_features:
                logger.warning(f"Missing features (will be ignored): {self.missing_features}")

            logger.info(f"Using {len(self.available_features)} features")

            # Identify feature types
            self._identify_feature_types()

            # Prepare X and y
            X = self.df[self.available_features].copy()
            y = self.df[self.TARGET_COLUMN].copy()

            # Log class distribution
            class_counts = y.value_counts()
            logger.info(f"Class distribution: {class_counts.to_dict()}")

            # Check class imbalance
            imbalance_ratio = class_counts.max() / class_counts.min()
            logger.info(f"Class imbalance ratio: {imbalance_ratio:.2f}")
            if imbalance_ratio > 3:
                logger.warning(
                    f"Class imbalance detected (ratio={imbalance_ratio:.2f}). "
                    "Using balanced class weights."
                )

            # Train/test split
            self.X_train, self.X_test, self.y_train, self.y_test = train_test_split(
                X, y,
                test_size=self.test_split,
                random_state=self.random_state,
                stratify=y
            )

            logger.info(
                f"Split complete: train={len(self.X_train)}, test={len(self.X_test)}"
            )

        except pd.errors.EmptyDataError:
            raise DataLoadError("Dataset is empty")
        except pd.errors.ParserError as e:
            raise DataLoadError(f"Failed to parse CSV: {str(e)}")
        except Exception as e:
            raise DataLoadError(f"Unexpected error loading data: {str(e)}")

    def _identify_feature_types(self) -> None:
        """Identify categorical vs numeric features."""
        self.categorical_features = []
        self.numeric_features = []

        for col in self.available_features:
            if self.df[col].dtype in ['object', 'category']:
                self.categorical_features.append(col)
            else:
                self.numeric_features.append(col)

        logger.info(f"Categorical features: {self.categorical_features}")
        logger.info(f"Numeric features: {self.numeric_features}")

    def train(self, **hyperparameters) -> Dict[str, Any]:
        """
        Train the Random Forest model with specified hyperparameters.

        Args:
            **hyperparameters: Hyperparameters for RandomForestClassifier
                - n_estimators (int): Number of trees (default: 200)
                - max_depth (int): Max tree depth (default: None)
                - min_samples_split (int): Min samples to split (default: 2)
                - min_samples_leaf (int): Min samples in leaf (default: 1)
                - class_weight (str): Class weighting strategy (default: 'balanced')

        Returns:
            Dictionary containing training metrics

        Raises:
            TrainingError: If training fails
        """
        if self.X_train is None or self.y_train is None:
            raise TrainingError("Data not loaded. Call load_data() first.")

        logger.info("Starting model training")
        self.training_start_time = datetime.now()

        try:
            # Default hyperparameters
            self.hyperparameters = {
                'n_estimators': hyperparameters.get('n_estimators', 200),
                'max_depth': hyperparameters.get('max_depth', None),
                'min_samples_split': hyperparameters.get('min_samples_split', 2),
                'min_samples_leaf': hyperparameters.get('min_samples_leaf', 1),
                'class_weight': hyperparameters.get('class_weight', 'balanced'),
                'random_state': self.random_state,
                'n_jobs': -1,
            }

            logger.info(f"Hyperparameters: {self.hyperparameters}")

            # Build pipeline
            self.model = self._build_pipeline()

            # Train
            logger.info("Fitting model...")
            self.model.fit(self.X_train, self.y_train)

            self.training_end_time = datetime.now()
            self.training_duration_seconds = (
                self.training_end_time - self.training_start_time
            ).total_seconds()

            logger.info(f"Training completed in {self.training_duration_seconds:.2f}s")

            # Evaluate
            self.metrics = self.evaluate(self.X_test, self.y_test)

            # Feature importance
            self.feature_importance = self.get_feature_importance()

            return self.metrics

        except Exception as e:
            self.training_end_time = datetime.now()
            self.training_duration_seconds = (
                self.training_end_time - self.training_start_time
            ).total_seconds()
            logger.error(f"Training failed after {self.training_duration_seconds:.2f}s: {str(e)}")
            raise TrainingError(f"Model training failed: {str(e)}")

    def _build_pipeline(self) -> Pipeline:
        """Build scikit-learn pipeline with preprocessing and model."""
        # Categorical transformer
        categorical_transformer = OneHotEncoder(handle_unknown="ignore")

        # Numeric transformer
        numeric_transformer = StandardScaler()

        # Column transformer
        preprocessor = ColumnTransformer(
            transformers=[
                ("cat", categorical_transformer, self.categorical_features),
                ("num", numeric_transformer, self.numeric_features),
            ]
        )

        # Classifier
        clf = RandomForestClassifier(**self.hyperparameters)

        # Pipeline
        pipeline = Pipeline(
            steps=[
                ("preprocess", preprocessor),
                ("clf", clf),
            ],
            memory='auto'  # Cache transformers  # noqa: S106
        )

        return pipeline

    def evaluate(self, X_test: pd.DataFrame, y_test: pd.Series) -> Dict[str, Any]:
        """
        Evaluate model performance on test set.

        Args:
            X_test: Test features
            y_test: Test labels

        Returns:
            Dictionary with accuracy, precision, recall, F1, and per-class metrics

        Raises:
            TrainingError: If evaluation fails
        """
        if self.model is None:
            raise TrainingError("Model not trained. Call train() first.")

        logger.info("Evaluating model on test set")

        try:
            # Predictions
            y_pred = self.model.predict(X_test)

            # Overall metrics
            accuracy = accuracy_score(y_test, y_pred)
            precision, recall, f1, _ = precision_recall_fscore_support(
                y_test, y_pred,
                labels=["LOW", "MEDIUM", "HIGH"],
                average="weighted",
                zero_division=0
            )

            logger.info(f"Accuracy: {accuracy:.4f}")
            logger.info(f"Precision: {precision:.4f}")
            logger.info(f"Recall: {recall:.4f}")
            logger.info(f"F1-Score: {f1:.4f}")

            # Confusion matrix
            cm = confusion_matrix(y_test, y_pred, labels=["LOW", "MEDIUM", "HIGH"])
            logger.info(f"Confusion matrix:\n{cm}")

            # Per-class metrics
            self.per_class_metrics = self._compute_per_class_metrics(cm)

            # Classification report
            report = classification_report(y_test, y_pred, digits=4)
            logger.info(f"Classification report:\n{report}")

            metrics = {
                "accuracy": float(accuracy),
                "precision": float(precision),
                "recall": float(recall),
                "f1_score": float(f1),
                "per_class": self.per_class_metrics,
                "confusion_matrix": cm.tolist(),
            }

            return metrics

        except Exception as e:
            logger.error(f"Evaluation failed: {str(e)}")
            raise TrainingError(f"Model evaluation failed: {str(e)}")

    def _compute_per_class_metrics(self, cm) -> Dict[str, Dict[str, float]]:
        """Calculate per-class accuracy and support from confusion matrix."""
        per_class = {}

        for i, level in enumerate(["LOW", "MEDIUM", "HIGH"]):
            support = int(cm.sum(axis=1)[i])
            if support > 0:
                accuracy = float(cm[i, i] / support)
            else:
                accuracy = 0.0

            per_class[level] = {
                "accuracy": round(accuracy, 4),
                "support": support
            }
            logger.info(f"  {level}: accuracy={accuracy:.2%}, support={support}")

        return per_class

    def save_model(self, path: str) -> None:
        """
        Save trained model to disk using joblib.

        Args:
            path: File path where model will be saved (.pkl extension)

        Raises:
            TrainingError: If model save fails
        """
        if self.model is None:
            raise TrainingError("No model to save. Call train() first.")

        model_path = Path(path)
        model_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            logger.info(f"Saving model to: {model_path}")
            joblib.dump(self.model, model_path)
            logger.info(f"Model saved successfully: {model_path.stat().st_size} bytes")

        except Exception as e:
            logger.error(f"Failed to save model: {str(e)}")
            raise TrainingError(f"Model save failed: {str(e)}")

    def get_feature_importance(self) -> Dict[str, float]:
        """
        Extract feature importance from trained Random Forest.

        Returns:
            Dictionary mapping feature names to importance scores

        Raises:
            TrainingError: If feature importance extraction fails
        """
        if self.model is None:
            raise TrainingError("Model not trained. Call train() first.")

        try:
            clf = self.model.named_steps["clf"]  # noqa: PD011

            if not hasattr(clf, 'feature_importances_'):
                logger.warning("Model does not support feature importance")
                return {}

            # Get feature names after preprocessing
            preprocessor = self.model.named_steps["preprocess"]  # noqa: PD011

            cat_features = []
            if self.categorical_features:
                cat_transformer = preprocessor.named_transformers_['cat']  # noqa: PD011
                if hasattr(cat_transformer, 'get_feature_names_out'):
                    cat_features = cat_transformer.get_feature_names_out(
                        self.categorical_features
                    ).tolist()

            all_features = cat_features + self.numeric_features

            if len(all_features) != len(clf.feature_importances_):
                logger.warning(
                    f"Feature count mismatch: {len(all_features)} vs "
                    f"{len(clf.feature_importances_)}"
                )
                return {}

            # Create importance dict
            importance = {
                feat: float(imp)
                for feat, imp in zip(all_features, clf.feature_importances_)
            }

            # Sort by importance
            sorted_importance = dict(
                sorted(importance.items(), key=lambda x: x[1], reverse=True)
            )

            # Log top 10
            logger.info("Top 10 important features:")
            for i, (feat, imp) in enumerate(list(sorted_importance.items())[:10]):
                logger.info(f"  {i+1}. {feat}: {imp:.4f}")

            return sorted_importance

        except Exception as e:
            logger.error(f"Failed to extract feature importance: {str(e)}")
            return {}

    def save_training_run(
        self,
        model_version: str,
        model_path: str,
        user=None,
        notes: str = ""
    ) -> TrainingRun:
        """
        Save training run to database for MLOps tracking.

        Args:
            model_version: Version identifier (e.g., 'v1.0', 'production_jan2024')
            model_path: Path where model was saved
            user: Django User who initiated training (None for CLI)
            notes: Optional notes about this training run

        Returns:
            Created TrainingRun instance

        Raises:
            TrainingError: If saving fails
        """
        if self.metrics is None or not self.metrics:
            raise TrainingError("No metrics available. Call train() first.")

        try:
            logger.info(f"Saving training run: version={model_version}")

            training_run = TrainingRun.objects.create(
                run_date=self.training_start_time or datetime.now(),
                model_version=model_version,
                model_path=str(model_path),
                dataset_path=str(self.dataset_path),
                test_split=self.test_split,
                n_estimators=self.hyperparameters.get('n_estimators', 200),
                random_state=self.random_state,
                accuracy=self.metrics['accuracy'],
                precision=self.metrics['precision'],
                recall=self.metrics['recall'],
                f1_score=self.metrics['f1_score'],
                total_samples=len(self.df) if self.df is not None else 0,
                train_samples=len(self.X_train) if self.X_train is not None else 0,
                test_samples=len(self.X_test) if self.X_test is not None else 0,
                training_duration_seconds=self.training_duration_seconds,
                per_class_metrics=self.per_class_metrics,
                features_used=self.available_features,
                trained_by=user,
                notes=notes,
                status='COMPLETED',
                hyperparameters=self.hyperparameters,
            )

            logger.info(f"Training run saved: ID={training_run.id}")
            return training_run

        except Exception as e:
            logger.error(f"Failed to save training run: {str(e)}")
            raise TrainingError(f"Failed to save training run: {str(e)}")

    def save_failed_training_run(
        self,
        model_version: str,
        error_message: str,
        user=None,
        notes: str = ""
    ) -> TrainingRun:
        """
        Save failed training run to database for tracking.

        Args:
            model_version: Version identifier
            error_message: Error that caused failure
            user: Django User who initiated training
            notes: Optional notes

        Returns:
            Created TrainingRun instance with FAILED status
        """
        try:
            logger.info(f"Saving failed training run: version={model_version}")

            training_run = TrainingRun.objects.create(
                run_date=self.training_start_time or datetime.now(),
                model_version=model_version,
                model_path="",
                dataset_path=str(self.dataset_path),
                test_split=self.test_split,
                n_estimators=self.hyperparameters.get('n_estimators', 200),
                random_state=self.random_state,
                accuracy=0.0,
                precision=0.0,
                recall=0.0,
                f1_score=0.0,
                total_samples=0,
                train_samples=0,
                test_samples=0,
                training_duration_seconds=self.training_duration_seconds,
                per_class_metrics={},
                features_used=[],
                trained_by=user,
                notes=notes,
                status='FAILED',
                error_message=error_message,
                hyperparameters=self.hyperparameters or {},
            )

            logger.info(f"Failed training run saved: ID={training_run.id}")
            return training_run

        except Exception as e:
            logger.error(f"Failed to save failed training run: {str(e)}")
            raise
