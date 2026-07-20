# future_skills/services/training_service.py

"""Training service for the Future Skills ML model.

Provides a clean OOP interface for training ML models with proper error handling,
logging, and integration with Django's TrainingRun model for MLOps tracking.
"""

import logging
import re
from datetime import datetime
from importlib.metadata import version
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import mlflow
import mlflow.sklearn
import pandas as pd
from django.conf import settings
from mlflow.models import infer_signature
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    brier_score_loss,
    classification_report,
    cohen_kappa_score,
    confusion_matrix,
    precision_recall_fscore_support,
)
from sklearn.model_selection import ParameterGrid, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from future_skills.models import TrainingRun
from future_skills.services.prediction_engine import calculate_level
from future_skills.services.slice_performance_metrics import update_slice_performance_metrics
from ml.mlflow_config import get_mlflow_config
from ml.model_versioning import ModelFramework, ModelStage, ModelVersionManager, create_model_version

logger = logging.getLogger(__name__)


class ModelTrainerError(Exception):
    """Base exception for ModelTrainer errors."""


class DataLoadError(ModelTrainerError):
    """Exception raised when data loading fails."""


class TrainingError(ModelTrainerError):
    """Exception raised when model training fails."""


class ModelTrainer:
    """ML Model Trainer for Future Skills prediction.

    Handles the complete training lifecycle:
    - Data loading and validation
    - Model training with hyperparameter tuning
    - Evaluation and metrics collection
    - Model persistence
    - MLOps tracking via TrainingRun model

    Example:
        >>> trainer = ModelTrainer(
        ...     dataset_path="artifacts/datasets/future_skills_dataset.csv",
        ...     test_split=0.2
        ... )
        >>> trainer.load_data()
        >>> metrics = trainer.train(n_estimators=200, random_state=42)
        >>> trainer.save_model("artifacts/models/future_skills_model.pkl")
        >>> trainer.save_training_run(model_version="v1.0", user=request.user)
    """

    ALLOWED_LEVELS = {"LOW", "MEDIUM", "HIGH"}
    TARGET_COLUMN = "future_need_level"
    LABEL_PROVENANCE_COLUMN = "label_provenance"
    AS_OF_DATE_COLUMN = "as_of_date"
    DEFAULT_ALLOWED_PROVENANCE = ["SILVER", "GOLD"]

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
        "trend_momentum",
        "trend_acceleration",
        "trend_volatility",
        "trend_persistence",
        "internal_usage_momentum",
        "training_requests_momentum",
        "internal_usage_lag_1",
        "internal_usage_lag_2",
        "internal_usage_roll_mean_3",
        "training_requests_lag_1",
        "training_requests_lag_2",
        "training_requests_roll_mean_3",
        "economic_indicator_lag_1",
        "economic_indicator_lag_2",
        "economic_indicator_roll_mean_3",
        "trend_stability_flag",
        "internal_usage_stability_flag",
        "training_requests_stability_flag",
        "data_quality_window_coverage",
        "data_quality_missing_flag",
        "data_quality_stale_flag",
        "data_quality_low_sample_flag",
        "is_it_department",
        "is_senior_role",
        "is_technical_skill",
        "dept_skill_alignment",
        "forecast_trend_score",
        "forecast_internal_usage",
        "forecast_training_requests",
        "forecast_need_score",
    ]

    def __init__(
        self,
        dataset_path: str,
        test_split: float = 0.2,
        random_state: int = 42,
        allowed_label_provenance: Optional[List[str]] = None,
        use_time_split: bool = True,
        enable_nested_cv: bool | None = None,
    ):
        """Initialize ModelTrainer.

        Args:
            dataset_path: Path to the training dataset CSV
            test_split: Proportion of data for test set (0.0 to 1.0)
            random_state: Random seed for reproducibility
        """
        self.dataset_path = Path(dataset_path)
        self.test_split = test_split
        self.random_state = random_state
        self.allowed_label_provenance = (
            [value.upper() for value in allowed_label_provenance] if allowed_label_provenance else None
        )
        self.use_time_split = use_time_split
        self.enable_nested_cv = (
            bool(enable_nested_cv)
            if enable_nested_cv is not None
            else bool(getattr(settings, "FUTURE_SKILLS_ENABLE_NESTED_CV", False))
        )
        self.min_slice_size = int(getattr(settings, "FUTURE_SKILLS_MIN_SLICE_SIZE", 30))

        # Data containers
        self.df: Optional[pd.DataFrame] = None
        self.x_train: Optional[pd.DataFrame] = None
        self.x_test: Optional[pd.DataFrame] = None
        self.x_valid: Optional[pd.DataFrame] = None
        self.y_train: Optional[pd.Series] = None
        self.y_test: Optional[pd.Series] = None
        self.y_valid: Optional[pd.Series] = None
        self.available_features: List[str] = []
        self.missing_features: List[str] = []
        self.categorical_features: List[str] = []
        self.numeric_features: List[str] = []
        self.label_provenance_counts: Dict[str, int] = {}
        self.as_of_date_range: Optional[Dict[str, str]] = None
        self.time_split_used = False
        self.holdout_window: Optional[Dict[str, str]] = None
        self.validation_window: Optional[Dict[str, str]] = None

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
        self.mlflow_run_id: Optional[str] = None  # MLflow run tracking

        logger.info(f"ModelTrainer initialized: dataset={dataset_path}, test_split={test_split}")

    # Backwards-compatible accessors for legacy code/tests expecting uppercase attrs
    @property
    def X_train(self):
        """Return the training feature set."""
        return self.x_train

    @property
    def X_test(self):
        """Return the test feature set."""
        return self.x_test

    @property
    def Y_train(self):
        """Return the training labels."""
        return self.y_train

    @property
    def Y_test(self):
        """Return the test labels."""
        return self.y_test

    def load_data(self) -> None:
        """Load and preprocess dataset from CSV.

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
                raise DataLoadError(f"No valid rows with {self.TARGET_COLUMN} in {self.ALLOWED_LEVELS}")

            if after_count < before_count:
                filtered = before_count - after_count
                logger.warning(f"Filtered {filtered} rows with invalid target values")

            # Apply default label provenance policy when column exists
            if self.LABEL_PROVENANCE_COLUMN in self.df.columns and self.allowed_label_provenance is None:
                self.allowed_label_provenance = self.DEFAULT_ALLOWED_PROVENANCE.copy()
                logger.info(
                    "Defaulting allowed label provenance to %s",
                    self.allowed_label_provenance,
                )

            # Filter by label provenance if requested and available
            if self.LABEL_PROVENANCE_COLUMN in self.df.columns:
                provenance_series = self.df[self.LABEL_PROVENANCE_COLUMN].astype(str).str.upper()
                if self.allowed_label_provenance:
                    allowed_set = set(self.allowed_label_provenance)
                    before_count = len(self.df)
                    self.df = self.df[provenance_series.isin(allowed_set)].copy()
                    after_count = len(self.df)
                    if after_count == 0:
                        raise DataLoadError(
                            f"No rows match allowed label provenance {sorted(allowed_set)}"
                        )
                    if after_count < before_count:
                        logger.info(f"Filtered {before_count - after_count} rows by label provenance")
                    provenance_series = self.df[self.LABEL_PROVENANCE_COLUMN].astype(str).str.upper()

                self.label_provenance_counts = provenance_series.value_counts().to_dict()
                if self.label_provenance_counts == {"BRONZE": len(self.df)}:
                    logger.warning("Dataset contains only BRONZE labels; use SILVER/GOLD for final training.")
            elif self.allowed_label_provenance:
                logger.warning(
                    "Label provenance filtering requested but column missing; proceeding without filter."
                )

            # Capture as_of_date range if available
            if self.AS_OF_DATE_COLUMN in self.df.columns:
                as_of_series = pd.to_datetime(self.df[self.AS_OF_DATE_COLUMN], errors="coerce")
                if as_of_series.notna().any():
                    self.as_of_date_range = {
                        "min": as_of_series.min().date().isoformat(),
                        "max": as_of_series.max().date().isoformat(),
                    }

            # Identify available features
            self.available_features = [col for col in self.FEATURE_COLUMNS if col in self.df.columns]
            self.missing_features = [col for col in self.FEATURE_COLUMNS if col not in self.df.columns]

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
                    f"Class imbalance detected (ratio={imbalance_ratio:.2f}). " "Using balanced class weights."
                )

            # Train/test split (time-based when possible)
            if self.use_time_split and self.AS_OF_DATE_COLUMN in self.df.columns:
                as_of_series = pd.to_datetime(self.df[self.AS_OF_DATE_COLUMN], errors="coerce")
                if as_of_series.notna().sum() >= 2 and as_of_series.nunique() > 1:
                    df_sorted = self.df.copy()
                    df_sorted["_as_of_date"] = as_of_series
                    df_sorted = df_sorted.sort_values("_as_of_date")
                    split_index = int(len(df_sorted) * (1 - self.test_split))
                    if 0 < split_index < len(df_sorted):
                        X_sorted = df_sorted[self.available_features].copy()
                        y_sorted = df_sorted[self.TARGET_COLUMN].copy()
                        self.x_train = X_sorted.iloc[:split_index]
                        self.x_test = X_sorted.iloc[split_index:]
                        self.y_train = y_sorted.iloc[:split_index]
                        self.y_test = y_sorted.iloc[split_index:]
                        self.time_split_used = True
                        train_end = df_sorted["_as_of_date"].iloc[split_index - 1].date()
                        test_start = df_sorted["_as_of_date"].iloc[split_index].date()
                        test_end = df_sorted["_as_of_date"].iloc[-1].date()
                        self.holdout_window = {
                            "train_end": train_end.isoformat(),
                            "test_start": test_start.isoformat(),
                            "test_end": test_end.isoformat(),
                        }
                        logger.info(
                            "Time-based split complete: train=%d, test=%d",
                            len(self.x_train),
                            len(self.x_test),
                        )

                        if not self.enable_nested_cv:
                            train_df = df_sorted.iloc[:split_index].copy()
                            train_dates = sorted(train_df["_as_of_date"].unique())
                            if len(train_dates) >= 2:
                                validation_date = train_dates[-1]
                                train_mask = train_df["_as_of_date"] < validation_date
                                validation_mask = train_df["_as_of_date"] == validation_date
                                if train_mask.any() and validation_mask.any():
                                    self.x_valid = train_df.loc[validation_mask, self.available_features].copy()
                                    self.y_valid = train_df.loc[validation_mask, self.TARGET_COLUMN].copy()
                                    self.x_train = train_df.loc[train_mask, self.available_features].copy()
                                    self.y_train = train_df.loc[train_mask, self.TARGET_COLUMN].copy()
                                    self.validation_window = {
                                        "train_end": pd.Timestamp(train_dates[-2]).date().isoformat(),
                                        "validation_date": pd.Timestamp(validation_date).date().isoformat(),
                                    }
                                    logger.info(
                                        "Validation window set: date=%s (train=%d, valid=%d)",
                                        self.validation_window["validation_date"],
                                        len(self.x_train),
                                        len(self.x_valid),
                                    )
                    else:
                        logger.warning("Time-based split not possible; falling back to random split.")
                else:
                    logger.warning("Insufficient as_of_date values; falling back to random split.")

            if not self.time_split_used:
                self.x_train, self.x_test, self.y_train, self.y_test = train_test_split(
                    X,
                    y,
                    test_size=self.test_split,
                    random_state=self.random_state,
                    stratify=y,
                )

                logger.info(f"Split complete: train={len(self.x_train)}, test={len(self.x_test)}")

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
            if self.df[col].dtype in ["object", "category"]:
                self.categorical_features.append(col)
            else:
                self.numeric_features.append(col)

        logger.info(f"Categorical features: {self.categorical_features}")
        logger.info(f"Numeric features: {self.numeric_features}")

    def train(self, **hyperparameters) -> Dict[str, Any]:
        """Train the Random Forest model with specified hyperparameters.

        Integrates with MLflow for experiment tracking.

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
        if self.x_train is None or self.y_train is None:
            raise TrainingError("Data not loaded. Call load_data() first.")

        logger.info("Starting model training with MLflow tracking")
        self.training_start_time = datetime.now()

        try:
            # Initialize MLflow
            mlflow_config = get_mlflow_config()
            mlflow_config.setup()

            # Default hyperparameters
            self.hyperparameters = {
                "n_estimators": hyperparameters.get("n_estimators", 200),
                "max_depth": hyperparameters.get("max_depth", None),
                "min_samples_split": hyperparameters.get("min_samples_split", 2),
                "min_samples_leaf": hyperparameters.get("min_samples_leaf", 1),
                "class_weight": hyperparameters.get("class_weight", "balanced"),
                "random_state": self.random_state,
                "n_jobs": -1,
            }

            logger.info(f"Hyperparameters: {self.hyperparameters}")

            # Start MLflow run
            with mlflow_config.start_run(
                run_name=f"training_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                experiment_name="model-training",
            ) as run:
                # Log hyperparameters
                mlflow.log_params(self.hyperparameters)
                mlflow.log_param("test_split", self.test_split)
                mlflow.log_param("random_state", self.random_state)
                mlflow.log_param("dataset_path", str(self.dataset_path))
                mlflow.log_param("total_samples", len(self.df) if self.df is not None else 0)
                mlflow.log_param("train_samples", len(self.x_train))
                mlflow.log_param("test_samples", len(self.x_test))

                # Build pipeline
                self.model = self._build_pipeline()

                # Train
                logger.info("Fitting model...")
                self.model.fit(self.x_train, self.y_train)

                self.training_end_time = datetime.now()
                self.training_duration_seconds = (self.training_end_time - self.training_start_time).total_seconds()

                logger.info(f"Training completed in {self.training_duration_seconds:.2f}s")

                # Log training time
                mlflow.log_metric("training_duration_seconds", self.training_duration_seconds)

                # Evaluate
                self.metrics = self.evaluate(self.x_test, self.y_test)
                validation_metrics = self._evaluate_split(self.x_valid, self.y_valid)
                if validation_metrics:
                    self.metrics["validation"] = validation_metrics

                # Log metrics to MLflow
                base_metrics = {
                    "accuracy": self.metrics["accuracy"],
                    "precision": self.metrics["precision"],
                    "recall": self.metrics["recall"],
                    "f1_score": self.metrics["f1_score"],
                    "kappa": self.metrics.get("kappa", 0.0),
                    "weighted_kappa": self.metrics.get("weighted_kappa", 0.0),
                    "macro_f1": self.metrics.get("macro_f1", 0.0),
                    "balanced_accuracy": self.metrics.get("balanced_accuracy", 0.0),
                }
                if self.metrics.get("brier_score") is not None:
                    base_metrics["brier_score"] = self.metrics["brier_score"]
                mlflow.log_metrics(base_metrics)

                # Log per-class metrics
                for level, level_metrics in self.metrics.get("per_class", {}).items():
                    mlflow.log_metric(f"{level}_accuracy", level_metrics["accuracy"])
                    mlflow.log_metric(f"{level}_support", level_metrics["support"])

                # Feature importance
                self.feature_importance = self.get_feature_importance()

                # Log top 10 features
                if self.feature_importance:
                    for i, (feat, imp) in enumerate(list(self.feature_importance.items())[:10]):
                        mlflow.log_metric(f"feature_importance_{i + 1}_{feat}", imp)

                # Record a complete, reproducible model contract. Supplying the
                # signature, input example, and runtime requirement also avoids
                # MLflow spawning a second environment-inference process.
                input_example = self.x_train.head(min(5, len(self.x_train))).copy()
                # MLflow schemas cannot represent missing values in integer
                # columns. Record numeric inputs as doubles so the persisted
                # signature remains compatible with real inference payloads.
                integer_columns = input_example.select_dtypes(include=["integer"]).columns
                input_example[integer_columns] = input_example[integer_columns].astype("float64")
                signature = infer_signature(input_example, self.model.predict(input_example))
                mlflow.sklearn.log_model(
                    self.model,
                    "model",
                    registered_model_name="future-skills-model",
                    signature=signature,
                    input_example=input_example,
                    pip_requirements=[f"scikit-learn=={version('scikit-learn')}"],
                )

                # Store run_id for later use
                self.mlflow_run_id = run.info.run_id
                logger.info(f"MLflow run ID: {self.mlflow_run_id}")

                return self.metrics

        except Exception as e:
            self.training_end_time = datetime.now()
            self.training_duration_seconds = (self.training_end_time - self.training_start_time).total_seconds()
            logger.error(f"Training failed after {self.training_duration_seconds:.2f}s: {str(e)}")
            raise TrainingError(f"Model training failed: {str(e)}")

    def _build_pipeline(self, hyperparameters: Optional[Dict[str, Any]] = None) -> Pipeline:
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
        clf = RandomForestClassifier(**(hyperparameters or self.hyperparameters))

        # Pipeline
        pipeline = Pipeline(
            steps=[
                ("preprocess", preprocessor),
                ("clf", clf),
            ],
            memory=str(settings.ML_JOBLIB_CACHE_DIR),  # Cache transformers  # noqa: S106
        )

        return pipeline

    def evaluate(
        self,
        x_test: Optional[pd.DataFrame] = None,
        y_test: Optional[pd.Series] = None,
    ) -> Dict[str, Any]:
        """Evaluate model performance on test set.

        Args:
            x_test: Test features
            y_test: Test labels

        Returns:
            Dictionary with accuracy, precision, recall, F1, and per-class metrics

        Raises:
            TrainingError: If evaluation fails
        """
        if self.model is None:
            raise TrainingError("Model not trained. Call train() first.")

        if x_test is None or y_test is None:
            if self.x_test is None or self.y_test is None:
                raise TrainingError("Test data missing. Call load_data() first.")
            x_test = self.x_test
            y_test = self.y_test

        logger.info("Evaluating model on test set")

        try:
            # Predictions
            y_pred = self.model.predict(x_test)

            # Overall metrics
            accuracy = accuracy_score(y_test, y_pred)
            precision, recall, f1, _ = precision_recall_fscore_support(
                y_test,
                y_pred,
                labels=["LOW", "MEDIUM", "HIGH"],
                average="weighted",
                zero_division=0,
            )
            macro_precision, macro_recall, macro_f1, _ = precision_recall_fscore_support(
                y_test,
                y_pred,
                labels=["LOW", "MEDIUM", "HIGH"],
                average="macro",
                zero_division=0,
            )
            balanced_accuracy = balanced_accuracy_score(y_test, y_pred)

            logger.info(f"Accuracy: {accuracy:.4f}")
            logger.info(f"Precision: {precision:.4f}")
            logger.info(f"Recall: {recall:.4f}")
            logger.info(f"F1-Score: {f1:.4f}")
            logger.info(f"Macro F1: {macro_f1:.4f}")
            logger.info(f"Balanced accuracy: {balanced_accuracy:.4f}")

            # Agreement metrics
            kappa = 0.0
            weighted_kappa = 0.0
            try:
                if pd.Series(y_test).nunique() > 1 and pd.Series(y_pred).nunique() > 1:
                    kappa = cohen_kappa_score(y_test, y_pred)
                    weighted_kappa = cohen_kappa_score(y_test, y_pred, weights="quadratic")
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"Kappa computation failed: {exc}")
            logger.info(f"Cohen's kappa: {kappa:.4f}")
            logger.info(f"Weighted kappa (quadratic): {weighted_kappa:.4f}")

            # Confusion matrix
            cm = confusion_matrix(y_test, y_pred, labels=["LOW", "MEDIUM", "HIGH"])
            logger.info(f"Confusion matrix:\n{cm}")

            # Per-class metrics
            self.per_class_metrics = self._compute_per_class_metrics(y_test, y_pred, cm)

            # Brier score (multi-class, macro average)
            brier_score = None
            if hasattr(self.model, "predict_proba"):
                try:
                    y_proba = self.model.predict_proba(x_test)
                    class_labels = list(getattr(self.model, "classes_", ["LOW", "MEDIUM", "HIGH"]))
                    brier_values = []
                    for idx, label in enumerate(class_labels):
                        y_true_binary = (y_test == label).astype(int)
                        brier_values.append(brier_score_loss(y_true_binary, y_proba[:, idx]))
                    if brier_values:
                        brier_score = float(sum(brier_values) / len(brier_values))
                        logger.info(f"Brier score (macro): {brier_score:.4f}")
                except Exception as exc:  # noqa: BLE001
                    logger.warning(f"Brier score computation failed: {exc}")

            # Classification report
            report = classification_report(y_test, y_pred, digits=4)
            logger.info(f"Classification report:\n{report}")

            metrics = {
                "accuracy": float(accuracy),
                "precision": float(precision),
                "recall": float(recall),
                "f1_score": float(f1),
                "macro_precision": float(macro_precision),
                "macro_recall": float(macro_recall),
                "macro_f1": float(macro_f1),
                "balanced_accuracy": float(balanced_accuracy),
                "kappa": float(kappa),
                "weighted_kappa": float(weighted_kappa),
                "brier_score": brier_score,
                "per_class": self.per_class_metrics,
                "per_class_metrics": self.per_class_metrics,
                "confusion_matrix": cm.tolist(),
            }

            walk_forward = self._run_walk_forward_evaluation()
            if walk_forward:
                metrics["walk_forward"] = walk_forward

            slice_metrics = self._compute_slice_metrics(x_test, y_test, y_pred)
            if slice_metrics:
                metrics["slice_metrics"] = slice_metrics
                update_slice_performance_metrics(slice_metrics=slice_metrics)

            rules_baseline = self._compute_rules_baseline_metrics(x_test, y_test)
            if rules_baseline:
                metrics["rules_baseline"] = rules_baseline

            nested_cv = self._run_nested_time_cv()
            if nested_cv:
                metrics["nested_cv"] = nested_cv

            return metrics

        except Exception as e:
            logger.error(f"Evaluation failed: {str(e)}")
            raise TrainingError(f"Model evaluation failed: {str(e)}")

    def _compute_per_class_metrics(self, y_true, y_pred, cm) -> Dict[str, Dict[str, float]]:
        """Calculate per-class precision/recall/F1 and accuracy."""
        labels = ["LOW", "MEDIUM", "HIGH"]
        precision, recall, f1, support = precision_recall_fscore_support(
            y_true,
            y_pred,
            labels=labels,
            average=None,
            zero_division=0,
        )

        per_class = {}
        for i, level in enumerate(labels):
            class_support = int(support[i])
            accuracy = float(cm[i, i] / class_support) if class_support > 0 else 0.0
            per_class[level] = {
                "precision": round(float(precision[i]), 4),
                "recall": round(float(recall[i]), 4),
                "f1": round(float(f1[i]), 4),
                "accuracy": round(accuracy, 4),
                "support": class_support,
            }
            logger.info(
                "  %s: precision=%.2f, recall=%.2f, f1=%.2f, support=%d",
                level,
                precision[i],
                recall[i],
                f1[i],
                class_support,
            )

        return per_class

    def _summarize_metrics(self, y_true, y_pred) -> Dict[str, Any]:
        """Return a consistent metric bundle for a given slice."""
        accuracy = accuracy_score(y_true, y_pred)
        macro_precision, macro_recall, macro_f1, _ = precision_recall_fscore_support(
            y_true,
            y_pred,
            labels=["LOW", "MEDIUM", "HIGH"],
            average="macro",
            zero_division=0,
        )
        balanced_accuracy = balanced_accuracy_score(y_true, y_pred)
        cm = confusion_matrix(y_true, y_pred, labels=["LOW", "MEDIUM", "HIGH"])
        per_class = self._compute_per_class_metrics(y_true, y_pred, cm)

        return {
            "accuracy": float(accuracy),
            "macro_precision": float(macro_precision),
            "macro_recall": float(macro_recall),
            "macro_f1": float(macro_f1),
            "balanced_accuracy": float(balanced_accuracy),
            "confusion_matrix": cm.tolist(),
            "per_class": per_class,
            "support": int(len(y_true)),
        }

    def _compute_slice_metrics(
        self,
        x_test: pd.DataFrame,
        y_test: pd.Series,
        y_pred,
    ) -> Dict[str, Any]:
        """Compute metrics by department, job role, and skill category."""
        if x_test is None or y_test is None:
            return {}

        y_pred_series = pd.Series(y_pred, index=y_test.index)
        slice_metrics: Dict[str, Any] = {"min_slice_size": self.min_slice_size}

        slice_specs = {
            "job_department": "by_department",
            "job_role_name": "by_job_role",
            "skill_category": "by_skill_category",
        }

        for column, bucket in slice_specs.items():
            if column not in x_test.columns:
                continue
            bucket_metrics: Dict[str, Any] = {}
            groups = x_test[column].fillna("Unknown")
            for group_value, indices in groups.groupby(groups).groups.items():
                if len(indices) < self.min_slice_size:
                    continue
                y_true_slice = y_test.loc[indices]
                y_pred_slice = y_pred_series.loc[indices]
                bucket_metrics[str(group_value)] = self._summarize_metrics(y_true_slice, y_pred_slice)
            if bucket_metrics:
                slice_metrics[bucket] = bucket_metrics

        return slice_metrics if len(slice_metrics) > 1 else {}

    def _compute_rules_baseline_metrics(
        self,
        x_test: pd.DataFrame,
        y_test: pd.Series,
    ) -> Dict[str, Any] | None:
        """Evaluate the rules engine as a baseline on the test split."""
        if x_test is None or y_test is None:
            return None

        required_cols = {"trend_score", "internal_usage", "training_requests"}
        if not required_cols.issubset(x_test.columns):
            logger.warning("Rules baseline skipped (missing columns: %s)", sorted(required_cols - set(x_test.columns)))
            return None

        y_pred_rules = []
        for row in x_test.itertuples(index=False):
            level, _ = calculate_level(
                trend_score=float(getattr(row, "trend_score")),
                internal_usage=float(getattr(row, "internal_usage")),
                training_requests=float(getattr(row, "training_requests")),
            )
            y_pred_rules.append(level)

        y_pred_series = pd.Series(y_pred_rules, index=y_test.index)
        return self._summarize_metrics(y_test, y_pred_series)

    def _evaluate_split(self, x_split: pd.DataFrame, y_split: pd.Series) -> Optional[Dict[str, Any]]:
        """Evaluate a specific split without mutating main metrics."""
        if self.model is None:
            return None
        if x_split is None or y_split is None or x_split.empty:
            return None

        y_pred = self.model.predict(x_split)
        accuracy = accuracy_score(y_split, y_pred)
        precision, recall, f1, _ = precision_recall_fscore_support(
            y_split,
            y_pred,
            labels=["LOW", "MEDIUM", "HIGH"],
            average="weighted",
            zero_division=0,
        )
        macro_precision, macro_recall, macro_f1, _ = precision_recall_fscore_support(
            y_split,
            y_pred,
            labels=["LOW", "MEDIUM", "HIGH"],
            average="macro",
            zero_division=0,
        )
        balanced_accuracy = balanced_accuracy_score(y_split, y_pred)

        kappa = 0.0
        weighted_kappa = 0.0
        if pd.Series(y_split).nunique() > 1 and pd.Series(y_pred).nunique() > 1:
            kappa = cohen_kappa_score(y_split, y_pred)
            weighted_kappa = cohen_kappa_score(y_split, y_pred, weights="quadratic")

        brier_score = None
        if hasattr(self.model, "predict_proba"):
            try:
                y_proba = self.model.predict_proba(x_split)
                class_labels = list(getattr(self.model, "classes_", ["LOW", "MEDIUM", "HIGH"]))
                brier_values = []
                for idx, label in enumerate(class_labels):
                    y_true_binary = (y_split == label).astype(int)
                    brier_values.append(brier_score_loss(y_true_binary, y_proba[:, idx]))
                if brier_values:
                    brier_score = float(sum(brier_values) / len(brier_values))
            except Exception:  # noqa: BLE001
                brier_score = None

        cm = confusion_matrix(y_split, y_pred, labels=["LOW", "MEDIUM", "HIGH"])
        per_class = self._compute_per_class_metrics(y_split, y_pred, cm)

        return {
            "accuracy": float(accuracy),
            "precision": float(precision),
            "recall": float(recall),
            "f1_score": float(f1),
            "macro_precision": float(macro_precision),
            "macro_recall": float(macro_recall),
            "macro_f1": float(macro_f1),
            "balanced_accuracy": float(balanced_accuracy),
            "kappa": float(kappa),
            "weighted_kappa": float(weighted_kappa),
            "brier_score": brier_score,
            "per_class": per_class,
            "confusion_matrix": cm.tolist(),
            "support": int(len(y_split)),
        }

    def _run_walk_forward_evaluation(
        self,
        min_train_dates: int = 3,
        max_folds: int = 5,
    ) -> Optional[Dict[str, Any]]:
        """Run walk-forward evaluation when enough temporal history exists."""
        if self.df is None or self.AS_OF_DATE_COLUMN not in self.df.columns:
            return None

        as_of_series = pd.to_datetime(self.df[self.AS_OF_DATE_COLUMN], errors="coerce")
        if as_of_series.notna().sum() < 2:
            return None

        df_sorted = self.df.copy()
        df_sorted["_as_of_date"] = as_of_series
        df_sorted = df_sorted.dropna(subset=["_as_of_date"]).sort_values("_as_of_date")

        unique_dates = sorted(df_sorted["_as_of_date"].unique())
        if len(unique_dates) < min_train_dates + 1:
            return None

        fold_indices = list(range(min_train_dates - 1, len(unique_dates) - 1))
        if len(fold_indices) > max_folds:
            fold_indices = fold_indices[-max_folds:]

        folds = []
        metrics_accumulator: Dict[str, List[float]] = {
            "accuracy": [],
            "precision": [],
            "recall": [],
            "f1_score": [],
            "macro_f1": [],
            "balanced_accuracy": [],
            "kappa": [],
            "weighted_kappa": [],
            "brier_score": [],
        }

        for idx in fold_indices:
            train_end = unique_dates[idx]
            test_date = unique_dates[idx + 1]

            train_df = df_sorted[df_sorted["_as_of_date"] <= train_end]
            test_df = df_sorted[df_sorted["_as_of_date"] == test_date]
            if train_df.empty or test_df.empty:
                continue

            x_train = train_df[self.available_features].copy()
            y_train = train_df[self.TARGET_COLUMN].copy()
            x_test = test_df[self.available_features].copy()
            y_test = test_df[self.TARGET_COLUMN].copy()

            model = self._build_pipeline()
            model.fit(x_train, y_train)
            y_pred = model.predict(x_test)

            accuracy = accuracy_score(y_test, y_pred)
            precision, recall, f1, _ = precision_recall_fscore_support(
                y_test,
                y_pred,
                labels=["LOW", "MEDIUM", "HIGH"],
                average="weighted",
                zero_division=0,
            )
            _macro_precision, _macro_recall, macro_f1, _ = precision_recall_fscore_support(
                y_test,
                y_pred,
                labels=["LOW", "MEDIUM", "HIGH"],
                average="macro",
                zero_division=0,
            )
            balanced_accuracy = balanced_accuracy_score(y_test, y_pred)

            kappa = 0.0
            weighted_kappa = 0.0
            if pd.Series(y_test).nunique() > 1 and pd.Series(y_pred).nunique() > 1:
                kappa = cohen_kappa_score(y_test, y_pred)
                weighted_kappa = cohen_kappa_score(y_test, y_pred, weights="quadratic")

            brier_score = None
            if hasattr(model, "predict_proba"):
                try:
                    y_proba = model.predict_proba(x_test)
                    class_labels = list(getattr(model, "classes_", ["LOW", "MEDIUM", "HIGH"]))
                    brier_values = []
                    for label_index, label in enumerate(class_labels):
                        y_true_binary = (y_test == label).astype(int)
                        brier_values.append(brier_score_loss(y_true_binary, y_proba[:, label_index]))
                    if brier_values:
                        brier_score = float(sum(brier_values) / len(brier_values))
                except Exception:  # noqa: BLE001
                    brier_score = None

            fold_metrics = {
                "accuracy": float(accuracy),
                "precision": float(precision),
                "recall": float(recall),
                "f1_score": float(f1),
                "macro_f1": float(macro_f1),
                "balanced_accuracy": float(balanced_accuracy),
                "kappa": float(kappa),
                "weighted_kappa": float(weighted_kappa),
                "brier_score": brier_score,
            }

            folds.append(
                {
                    "train_end": pd.Timestamp(train_end).date().isoformat(),
                    "test_date": pd.Timestamp(test_date).date().isoformat(),
                    "train_samples": len(x_train),
                    "test_samples": len(x_test),
                    "metrics": fold_metrics,
                }
            )

            for key, value in fold_metrics.items():
                if value is None:
                    continue
                metrics_accumulator[key].append(float(value))

        if not folds:
            return None

        mean_metrics = {}
        for key, values in metrics_accumulator.items():
            if values:
                mean_metrics[key] = round(sum(values) / len(values), 4)

        return {
            "strategy": "expanding_window",
            "min_train_dates": min_train_dates,
            "max_folds": max_folds,
            "fold_count": len(folds),
            "mean_metrics": mean_metrics,
            "folds": folds,
        }

    def _run_nested_time_cv(
        self,
        min_train_dates: int = 4,
        max_folds: int = 3,
    ) -> Optional[Dict[str, Any]]:
        """Run nested time-based CV with a simple hyperparameter grid."""
        if not self.enable_nested_cv:
            return None
        if self.df is None or self.AS_OF_DATE_COLUMN not in self.df.columns:
            return None

        as_of_series = pd.to_datetime(self.df[self.AS_OF_DATE_COLUMN], errors="coerce")
        if as_of_series.notna().sum() < 2:
            return None

        df_sorted = self.df.copy()
        df_sorted["_as_of_date"] = as_of_series
        df_sorted = df_sorted.dropna(subset=["_as_of_date"]).sort_values("_as_of_date")

        unique_dates = sorted(df_sorted["_as_of_date"].unique())
        if len(unique_dates) < min_train_dates + 1:
            return None

        outer_indices = list(range(min_train_dates - 1, len(unique_dates) - 1))
        if len(outer_indices) > max_folds:
            outer_indices = outer_indices[-max_folds:]

        base_params = self.hyperparameters or {
            "n_estimators": 200,
            "max_depth": None,
            "min_samples_split": 2,
            "min_samples_leaf": 1,
            "class_weight": "balanced",
            "random_state": self.random_state,
            "n_jobs": -1,
        }
        grid = getattr(settings, "FUTURE_SKILLS_NESTED_CV_GRID", None)
        if not grid:
            grid = [
                {"max_depth": base_params.get("max_depth", None)},
                {"max_depth": 10},
            ]
        grid = list(ParameterGrid(grid))

        folds = []
        for idx in outer_indices:
            train_end = unique_dates[idx]
            test_date = unique_dates[idx + 1]

            train_df = df_sorted[df_sorted["_as_of_date"] <= train_end]
            test_df = df_sorted[df_sorted["_as_of_date"] == test_date]
            if train_df.empty or test_df.empty:
                continue

            inner_dates = sorted(train_df["_as_of_date"].unique())
            best_params = base_params
            best_score = -1.0

            if len(inner_dates) >= 2:
                inner_train_end = inner_dates[-2]
                inner_val_date = inner_dates[-1]
                inner_train_df = train_df[train_df["_as_of_date"] <= inner_train_end]
                inner_val_df = train_df[train_df["_as_of_date"] == inner_val_date]

                if not inner_train_df.empty and not inner_val_df.empty:
                    for params in grid:
                        candidate = {**base_params, **params}
                        model = self._build_pipeline(candidate)
                        model.fit(inner_train_df[self.available_features], inner_train_df[self.TARGET_COLUMN])
                        val_pred = model.predict(inner_val_df[self.available_features])
                        _, _, macro_f1, _ = precision_recall_fscore_support(
                            inner_val_df[self.TARGET_COLUMN],
                            val_pred,
                            labels=["LOW", "MEDIUM", "HIGH"],
                            average="macro",
                            zero_division=0,
                        )
                        if macro_f1 > best_score:
                            best_score = float(macro_f1)
                            best_params = candidate

            model = self._build_pipeline(best_params)
            model.fit(train_df[self.available_features], train_df[self.TARGET_COLUMN])
            test_pred = model.predict(test_df[self.available_features])

            fold_metrics = self._summarize_metrics(test_df[self.TARGET_COLUMN], test_pred)
            fold_metrics["best_params"] = {
                key: best_params.get(key)
                for key in ("n_estimators", "max_depth", "min_samples_split", "min_samples_leaf", "class_weight")
                if key in best_params
            }

            folds.append(
                {
                    "train_end": pd.Timestamp(train_end).date().isoformat(),
                    "test_date": pd.Timestamp(test_date).date().isoformat(),
                    "train_samples": len(train_df),
                    "test_samples": len(test_df),
                    "metrics": fold_metrics,
                }
            )

        if not folds:
            return None

        mean_metrics = {}
        for key in ("accuracy", "macro_f1", "balanced_accuracy"):
            values = [fold["metrics"][key] for fold in folds if key in fold["metrics"]]
            if values:
                mean_metrics[key] = round(sum(values) / len(values), 4)

        return {
            "strategy": "nested_time_cv",
            "min_train_dates": min_train_dates,
            "max_folds": max_folds,
            "fold_count": len(folds),
            "mean_metrics": mean_metrics,
            "folds": folds,
        }

    def save_model(self, path: str) -> None:
        """Save the trained model to disk using joblib.

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
        """Extract feature importance from trained Random Forest.

        Returns:
            Dictionary mapping feature names to importance scores

        Raises:
            TrainingError: If feature importance extraction fails
        """
        if self.model is None:
            raise TrainingError("Model not trained. Call train() first.")

        try:
            clf = self.model.named_steps["clf"]  # noqa: PD011

            if not hasattr(clf, "feature_importances_"):
                logger.warning("Model does not support feature importance")
                return {}

            # Get feature names after preprocessing
            preprocessor = self.model.named_steps["preprocess"]  # noqa: PD011

            cat_features = []
            if self.categorical_features:
                cat_transformer = preprocessor.named_transformers_["cat"]  # noqa: PD011
                if hasattr(cat_transformer, "get_feature_names_out"):
                    cat_features = cat_transformer.get_feature_names_out(self.categorical_features).tolist()

            all_features = cat_features + self.numeric_features

            if len(all_features) != len(clf.feature_importances_):
                logger.warning(f"Feature count mismatch: {len(all_features)} vs " f"{len(clf.feature_importances_)}")
                return {}

            # Create importance dict
            importance = {feat: float(imp) for feat, imp in zip(all_features, clf.feature_importances_)}

            # Sort by importance
            sorted_importance = dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))

            # Log top 10
            logger.info("Top 10 important features:")
            for i, (feat, imp) in enumerate(list(sorted_importance.items())[:10]):
                logger.info(f"  {i + 1}. {feat}: {imp:.4f}")

            return sorted_importance

        except Exception as e:
            logger.error(f"Failed to extract feature importance: {str(e)}")
            return {}

    def save_training_run(
        self,
        model_version: str,
        model_path: str,
        user=None,
        notes: str = "",
        auto_promote: bool = True,
    ) -> TrainingRun:
        """Save training run to database for MLOps tracking.

        Integrates with model versioning and promotion logic.

        Args:
            model_version: Version identifier (e.g., 'v1.0.0', 'v1.1.0')
            model_path: Path where model was saved
            user: Django User who initiated training (None for CLI)
            notes: Optional notes about this training run
            auto_promote: Whether to automatically promote if metrics improve (default: True)

        Returns:
            Created TrainingRun instance

        Raises:
            TrainingError: If saving fails
        """
        if self.metrics is None or not self.metrics:
            raise TrainingError("No metrics available. Call train() first.")

        try:
            logger.info(f"Saving training run: version={model_version}")

            version_manager = ModelVersionManager()
            version_obj = self._build_version_metadata(model_version=model_version, model_path=model_path, notes=notes)
            version_manager.register_version(version_obj)
            logger.info(f"Registered model version: {model_version}")

            promotion_info = self._handle_auto_promotion(
                version_manager=version_manager,
                version_obj=version_obj,
                auto_promote=auto_promote,
            )

            training_run = self._create_training_run_record(
                model_version=model_version,
                model_path=model_path,
                user=user,
                notes=notes,
                promotion_info=promotion_info,
            )

            self._log_promotion(promotion_info)
            return training_run

        except Exception as e:
            logger.error(f"Failed to save training run: {str(e)}")
            raise TrainingError(f"Failed to save training run: {str(e)}")

    def _build_version_metadata(self, *, model_version: str, model_path: str, notes: str):
        """Create the ModelVersion instance with consistent metadata."""

        def _semver_fallback(version: str) -> str:
            # Generate a semver-compatible build metadata string for arbitrary tags
            cleaned = re.sub(r"[^A-Za-z0-9]+", "-", version).strip("-") or "manual"
            return f"0.0.0+{cleaned}"

        try:
            return create_model_version(
                version_string=model_version,
                metrics={
                    "accuracy": self.metrics["accuracy"],
                    "precision": self.metrics["precision"],
                    "recall": self.metrics["recall"],
                    "f1_score": self.metrics["f1_score"],
                    "training_time": self.training_duration_seconds,
                },
                model_path=model_path,
                framework=ModelFramework.SCIKIT_LEARN,
                algorithm="RandomForestClassifier",
                hyperparameters=self.hyperparameters,
                training_dataset_size=(len(self.x_train) if self.x_train is not None else 0),
                training_features=self.available_features,
                target_classes=["LOW", "MEDIUM", "HIGH"],
                mlflow_run_id=getattr(self, "mlflow_run_id", None),
                stage=ModelStage.STAGING,
                description=notes or f"Model trained on {datetime.now().strftime('%Y-%m-%d')}",
                original_version=model_version,
            )
        except ValueError:
            fallback_version = _semver_fallback(model_version)
            logger.warning(
                "Non-semver model_version '%s' detected; using fallback '%s'",
                model_version,
                fallback_version,
            )
            return create_model_version(
                version_string=fallback_version,
                metrics={
                    "accuracy": self.metrics["accuracy"],
                    "precision": self.metrics["precision"],
                    "recall": self.metrics["recall"],
                    "f1_score": self.metrics["f1_score"],
                    "training_time": self.training_duration_seconds,
                },
                model_path=model_path,
                framework=ModelFramework.SCIKIT_LEARN,
                algorithm="RandomForestClassifier",
                hyperparameters=self.hyperparameters,
                training_dataset_size=(len(self.x_train) if self.x_train is not None else 0),
                training_features=self.available_features,
                target_classes=["LOW", "MEDIUM", "HIGH"],
                mlflow_run_id=getattr(self, "mlflow_run_id", None),
                stage=ModelStage.STAGING,
                description=notes or f"Model trained on {datetime.now().strftime('%Y-%m-%d')}",
                original_version=model_version,
            )

    def _handle_auto_promotion(
        self,
        *,
        version_manager: ModelVersionManager,
        version_obj,
        auto_promote: bool,
    ) -> Optional[str]:
        """Determine whether the new model should be promoted to production."""
        if not auto_promote:
            return None

        prod_version = version_manager.get_production_version()
        if prod_version:
            should_promote, reason = version_manager.should_promote(
                new_version=version_obj,
                current_version=prod_version,
                metric_name="f1_score",
                improvement_threshold=0.01,
            )

            if should_promote:
                logger.info(f"Promoting model to production: {reason}")
                version_obj.metadata.stage = ModelStage.PRODUCTION
                version_manager.register_version(version_obj)
                self._transition_mlflow_model()
                return reason

            logger.info(f"Not promoting model: {reason}")
            return f"Not promoted: {reason}"

        logger.info("No existing production model. Auto-promoting first model.")
        version_obj.metadata.stage = ModelStage.PRODUCTION
        version_manager.register_version(version_obj)
        return "First model - automatically promoted to production"

    def _transition_mlflow_model(self) -> None:
        """Ensure MLflow registry mirrors the promotion decision."""
        mlflow_config = get_mlflow_config()
        try:
            latest_version = mlflow_config.get_latest_model_version(model_name="future-skills-model")
            if latest_version:
                mlflow_config.transition_model_stage(
                    model_name="future-skills-model",
                    version=str(latest_version.version),
                    stage="Production",
                    archive_existing=True,
                )
                logger.info("Transitioned MLflow model to Production")
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Failed to transition MLflow stage: {exc}")

    def _create_training_run_record(
        self,
        *,
        model_version: str,
        model_path: str,
        user,
        notes: str,
        promotion_info: Optional[str],
    ) -> TrainingRun:
        """Persist the TrainingRun entry with consistent metadata."""
        dataset_metadata = {
            "label_provenance_counts": self.label_provenance_counts,
            "as_of_date_range": self.as_of_date_range,
            "time_split_used": self.time_split_used,
            "allowed_label_provenance": self.allowed_label_provenance,
            "use_time_split": self.use_time_split,
            "holdout_window": self.holdout_window,
            "validation_window": self.validation_window,
            "min_slice_size": self.min_slice_size,
            "nested_cv_enabled": self.enable_nested_cv,
        }
        evaluation_metrics = {
            "confusion_matrix": self.metrics.get("confusion_matrix"),
            "kappa": self.metrics.get("kappa"),
            "weighted_kappa": self.metrics.get("weighted_kappa"),
            "brier_score": self.metrics.get("brier_score"),
            "macro_precision": self.metrics.get("macro_precision"),
            "macro_recall": self.metrics.get("macro_recall"),
            "macro_f1": self.metrics.get("macro_f1"),
            "balanced_accuracy": self.metrics.get("balanced_accuracy"),
            "per_class": self.metrics.get("per_class"),
            "slice_metrics": self.metrics.get("slice_metrics"),
            "rules_baseline": self.metrics.get("rules_baseline"),
            "walk_forward": self.metrics.get("walk_forward"),
            "nested_cv": self.metrics.get("nested_cv"),
            "validation": self.metrics.get("validation"),
        }
        training_run = TrainingRun.objects.create(
            run_date=self.training_start_time or datetime.now(),
            model_version=model_version,
            model_path=str(model_path),
            dataset_path=str(self.dataset_path),
            test_split=self.test_split,
            n_estimators=self.hyperparameters.get("n_estimators", 200),
            random_state=self.random_state,
            accuracy=self.metrics["accuracy"],
            precision=self.metrics["precision"],
            recall=self.metrics["recall"],
            f1_score=self.metrics["f1_score"],
            total_samples=len(self.df) if self.df is not None else 0,
            train_samples=len(self.x_train) if self.x_train is not None else 0,
            test_samples=len(self.x_test) if self.x_test is not None else 0,
            training_duration_seconds=self.training_duration_seconds,
            per_class_metrics=self.per_class_metrics,
            evaluation_metrics=evaluation_metrics,
            dataset_metadata=dataset_metadata,
            features_used=self.available_features,
            trained_by=user,
            notes=(
                f"{notes}\n\nMLflow Run ID: {getattr(self, 'mlflow_run_id', 'N/A')}\n" f"{promotion_info or ''}"
            ).strip(),
            status="COMPLETED",
            hyperparameters=self.hyperparameters,
        )

        logger.info(f"Training run saved: ID={training_run.id}")
        return training_run

    @staticmethod
    def _log_promotion(promotion_info: Optional[str]) -> None:
        """Log promotion details when available."""
        if promotion_info:
            logger.info(f"Promotion: {promotion_info}")

    def save_failed_training_run(
        self, model_version: str, error_message: str, user=None, notes: str = ""
    ) -> TrainingRun:
        """Save failed training run to database for tracking.

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

            dataset_metadata = {
                "label_provenance_counts": self.label_provenance_counts,
                "as_of_date_range": self.as_of_date_range,
                "time_split_used": self.time_split_used,
                "allowed_label_provenance": self.allowed_label_provenance,
                "use_time_split": self.use_time_split,
            }
            training_run = TrainingRun.objects.create(
                run_date=self.training_start_time or datetime.now(),
                model_version=model_version,
                model_path="",
                dataset_path=str(self.dataset_path),
                test_split=self.test_split,
                n_estimators=self.hyperparameters.get("n_estimators", 200),
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
                evaluation_metrics={},
                dataset_metadata=dataset_metadata,
                features_used=[],
                trained_by=user,
                notes=notes,
                status="FAILED",
                error_message=error_message,
                hyperparameters=self.hyperparameters or {},
            )

            logger.info(f"Failed training run saved: ID={training_run.id}")
            return training_run

        except Exception as e:
            logger.error(f"Failed to save failed training run: {str(e)}")
            raise
