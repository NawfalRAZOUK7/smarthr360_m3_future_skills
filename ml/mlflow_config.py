# ml/mlflow_config.py

"""
MLflow Configuration and Integration for SmartHR360.

Provides centralized configuration for MLflow tracking, experiment management,
and model registry integration with Django settings.

Features:
- Automatic experiment creation and management
- Model registry integration
- Artifact storage configuration
- Run tracking and tagging
- Integration with Django settings

Usage:
    from ml.mlflow_config import MLflowConfig, get_mlflow_client

    # Initialize MLflow
    config = MLflowConfig()
    config.setup()

    # Get client for operations
    client = get_mlflow_client()

    # Start tracking run
    with config.start_run(run_name="training_v1") as run:
        mlflow.log_param("n_estimators", 100)
        mlflow.log_metric("accuracy", 0.95)
"""

import logging
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Optional, Any, List
from datetime import datetime

import mlflow
from mlflow.tracking import MlflowClient
from mlflow.entities import ViewType
from django.conf import settings

logger = logging.getLogger(__name__)


class MLflowConfig:
    """
    Centralized MLflow configuration for SmartHR360.

    Manages MLflow tracking URI, experiments, and model registry.
    """

    # Default experiment names
    DEFAULT_EXPERIMENT = "future-skills-prediction"
    TRAINING_EXPERIMENT = "model-training"
    EVALUATION_EXPERIMENT = "model-evaluation"
    PRODUCTION_EXPERIMENT = "production-monitoring"

    # Model registry names
    MODEL_NAME = "future-skills-model"

    # Artifact locations
    ARTIFACTS_PATH = "mlruns"
    MODELS_PATH = "models"

    def __init__(self):
        """Initialize MLflow configuration."""
        self.tracking_uri = self._get_tracking_uri()
        self.artifact_location = self._get_artifact_location()
        self.backend_store_uri = self._get_backend_store_uri()
        self.client: Optional[MlflowClient] = None
        self._initialized = False

    def _get_tracking_uri(self) -> str:
        """
        Get MLflow tracking URI from settings or environment.

        Priority:
        1. MLFLOW_TRACKING_URI environment variable
        2. Django settings.MLFLOW_TRACKING_URI
        3. Default local file-based tracking
        """
        tracking_uri = os.environ.get(
            'MLFLOW_TRACKING_URI',
            getattr(settings, 'MLFLOW_TRACKING_URI', None)
        )

        if not tracking_uri:
            # Default to local file-based tracking
            base_dir = getattr(settings, 'BASE_DIR', Path.cwd())
            mlruns_dir = base_dir / 'mlruns'
            mlruns_dir.mkdir(exist_ok=True)
            tracking_uri = f"file://{mlruns_dir.absolute()}"

        return tracking_uri

    def _get_artifact_location(self) -> str:
        """Get artifact storage location."""
        artifact_location = os.environ.get(
            'MLFLOW_ARTIFACT_LOCATION',
            getattr(settings, 'MLFLOW_ARTIFACT_LOCATION', None)
        )

        if not artifact_location:
            base_dir = getattr(settings, 'BASE_DIR', Path.cwd())
            artifacts_dir = base_dir / 'mlruns' / 'artifacts'
            artifacts_dir.mkdir(parents=True, exist_ok=True)
            artifact_location = str(artifacts_dir.absolute())

        return artifact_location

    def _get_backend_store_uri(self) -> str:
        """
        Get backend store URI for MLflow tracking database.

        Supports PostgreSQL, MySQL, SQLite, or file-based storage.
        """
        backend_uri = os.environ.get(
            'MLFLOW_BACKEND_STORE_URI',
            getattr(settings, 'MLFLOW_BACKEND_STORE_URI', None)
        )

        if not backend_uri:
            # Default to SQLite database
            base_dir = getattr(settings, 'BASE_DIR', Path.cwd())
            db_path = base_dir / 'mlruns' / 'mlflow.db'
            db_path.parent.mkdir(parents=True, exist_ok=True)
            backend_uri = f"sqlite:///{db_path.absolute()}"

        return backend_uri

    def setup(self) -> None:
        """
        Initialize MLflow tracking and experiments.

        This should be called once during application startup.
        """
        if self._initialized:
            logger.debug("MLflow already initialized")
            return

        try:
            # Set tracking URI
            mlflow.set_tracking_uri(self.tracking_uri)
            logger.info(f"MLflow tracking URI set to: {self.tracking_uri}")

            # Initialize client
            self.client = MlflowClient(tracking_uri=self.tracking_uri)

            # Create default experiments
            self._create_default_experiments()

            # Set default experiment
            mlflow.set_experiment(self.DEFAULT_EXPERIMENT)

            self._initialized = True
            logger.info("MLflow initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize MLflow: {e}")
            raise

    def _create_default_experiments(self) -> None:
        """Create default experiments if they don't exist."""
        experiments = [
            (self.DEFAULT_EXPERIMENT, "Main future skills prediction experiments"),
            (self.TRAINING_EXPERIMENT, "Model training and hyperparameter tuning"),
            (self.EVALUATION_EXPERIMENT, "Model evaluation and validation"),
            (self.PRODUCTION_EXPERIMENT, "Production model monitoring and drift detection"),
        ]

        for exp_name, description in experiments:
            try:
                experiment = self.client.get_experiment_by_name(exp_name)
                if experiment is None:
                    exp_id = self.client.create_experiment(
                        name=exp_name,
                        artifact_location=f"{self.artifact_location}/{exp_name}",
                        tags={"description": description, "created_at": datetime.now().isoformat()}
                    )
                    logger.info(f"Created experiment '{exp_name}' with ID: {exp_id}")
                else:
                    logger.debug(f"Experiment '{exp_name}' already exists")
            except Exception as e:
                logger.error(f"Failed to create experiment '{exp_name}': {e}")

    @contextmanager
    def start_run(
        self,
        run_name: Optional[str] = None,
        experiment_name: Optional[str] = None,
        tags: Optional[Dict[str, Any]] = None,
        nested: bool = False
    ):
        """
        Context manager for MLflow run tracking.

        Args:
            run_name: Name for the run
            experiment_name: Experiment to log to (default: DEFAULT_EXPERIMENT)
            tags: Dictionary of tags to apply to the run
            nested: Whether this is a nested run

        Usage:
            with config.start_run(run_name="training"):
                mlflow.log_param("learning_rate", 0.01)
                mlflow.log_metric("accuracy", 0.95)
        """
        if not self._initialized:
            self.setup()

        if experiment_name:
            mlflow.set_experiment(experiment_name)

        try:
            with mlflow.start_run(run_name=run_name, nested=nested) as run:
                # Log default tags
                if tags:
                    mlflow.set_tags(tags)

                # Log system info
                mlflow.set_tag("mlflow.source.name", "smarthr360")
                mlflow.set_tag("mlflow.user", os.environ.get('USER', 'unknown'))

                yield run

        except Exception as e:
            logger.error(f"Error in MLflow run: {e}")
            raise

    def log_model_metrics(
        self,
        metrics: Dict[str, float],
        step: Optional[int] = None
    ) -> None:
        """
        Log multiple metrics at once.

        Args:
            metrics: Dictionary of metric names and values
            step: Optional step number for tracking over time
        """
        for metric_name, metric_value in metrics.items():
            mlflow.log_metric(metric_name, metric_value, step=step)

    def log_model_params(self, params: Dict[str, Any]) -> None:
        """
        Log multiple parameters at once.

        Args:
            params: Dictionary of parameter names and values
        """
        mlflow.log_params(params)

    def log_artifact_directory(self, local_dir: str, artifact_path: Optional[str] = None) -> None:
        """
        Log a directory as an artifact.

        Args:
            local_dir: Path to local directory
            artifact_path: Optional path within artifact store
        """
        mlflow.log_artifacts(local_dir, artifact_path=artifact_path)

    def register_model(
        self,
        model_uri: str,
        model_name: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        description: Optional[str] = None
    ) -> Any:
        """
        Register a model in MLflow Model Registry.

        Args:
            model_uri: URI of the model (e.g., "runs:/<run_id>/model")
            model_name: Name to register model under (default: MODEL_NAME)
            tags: Optional tags for the model version
            description: Optional description

        Returns:
            ModelVersion object
        """
        if not self._initialized:
            self.setup()

        model_name = model_name or self.MODEL_NAME

        try:
            # Register model
            model_version = mlflow.register_model(
                model_uri=model_uri,
                name=model_name,
                tags=tags
            )

            # Update description if provided
            if description:
                self.client.update_model_version(
                    name=model_name,
                    version=model_version.version,
                    description=description
                )

            logger.info(
                f"Registered model '{model_name}' version {model_version.version}"
            )

            return model_version

        except Exception as e:
            logger.error(f"Failed to register model: {e}")
            raise

    def transition_model_stage(
        self,
        model_name: str,
        version: str,
        stage: str,
        archive_existing: bool = True
    ) -> None:
        """
        Transition a model version to a different stage.

        Args:
            model_name: Name of the registered model
            version: Version number to transition
            stage: Target stage ("Staging", "Production", "Archived", "None")
            archive_existing: Whether to archive existing versions in target stage
        """
        if not self._initialized:
            self.setup()

        try:
            self.client.transition_model_version_stage(
                name=model_name,
                version=version,
                stage=stage,
                archive_existing_versions=archive_existing
            )

            logger.info(
                f"Transitioned model '{model_name}' version {version} to {stage}"
            )

        except Exception as e:
            logger.error(f"Failed to transition model stage: {e}")
            raise

    def get_latest_model_version(
        self,
        model_name: Optional[str] = None,
        stage: Optional[str] = None
    ) -> Optional[Any]:
        """
        Get the latest version of a registered model.

        Args:
            model_name: Name of the model (default: MODEL_NAME)
            stage: Optional stage filter ("Staging", "Production", etc.)

        Returns:
            Latest ModelVersion or None
        """
        if not self._initialized:
            self.setup()

        model_name = model_name or self.MODEL_NAME

        try:
            versions = self.client.search_model_versions(f"name='{model_name}'")

            if stage:
                versions = [v for v in versions if v.current_stage == stage]

            if not versions:
                return None

            # Sort by version number (descending)
            versions.sort(key=lambda v: int(v.version), reverse=True)

            return versions[0]

        except Exception as e:
            logger.error(f"Failed to get latest model version: {e}")
            return None

    def get_production_model_uri(self, model_name: Optional[str] = None) -> Optional[str]:
        """
        Get the URI of the current production model.

        Args:
            model_name: Name of the model (default: MODEL_NAME)

        Returns:
            Model URI string or None
        """
        model_name = model_name or self.MODEL_NAME
        latest_version = self.get_latest_model_version(model_name, stage="Production")

        if latest_version:
            return f"models:/{model_name}/{latest_version.version}"

        return None

    def search_runs(
        self,
        experiment_name: Optional[str] = None,
        filter_string: str = "",
        max_results: int = 100,
        order_by: Optional[List[str]] = None
    ) -> List[Any]:
        """
        Search for runs in an experiment.

        Args:
            experiment_name: Name of experiment to search (default: DEFAULT_EXPERIMENT)
            filter_string: Filter expression (e.g., "metrics.accuracy > 0.9")
            max_results: Maximum number of results
            order_by: List of order_by clauses

        Returns:
            List of Run objects
        """
        if not self._initialized:
            self.setup()

        experiment_name = experiment_name or self.DEFAULT_EXPERIMENT
        experiment = self.client.get_experiment_by_name(experiment_name)

        if not experiment:
            logger.warning(f"Experiment '{experiment_name}' not found")
            return []

        try:
            runs = self.client.search_runs(
                experiment_ids=[experiment.experiment_id],
                filter_string=filter_string,
                max_results=max_results,
                order_by=order_by or ["start_time DESC"]
            )

            return runs

        except Exception as e:
            logger.error(f"Failed to search runs: {e}")
            return []

    def get_best_run(
        self,
        experiment_name: Optional[str] = None,
        metric_name: str = "accuracy",
        ascending: bool = False
    ) -> Optional[Any]:
        """
        Get the best run based on a metric.

        Args:
            experiment_name: Name of experiment
            metric_name: Metric to optimize
            ascending: Whether lower is better (for loss metrics)

        Returns:
            Best Run object or None
        """
        order_direction = "ASC" if ascending else "DESC"
        order_by = [f"metrics.{metric_name} {order_direction}"]

        runs = self.search_runs(
            experiment_name=experiment_name,
            max_results=1,
            order_by=order_by
        )

        return runs[0] if runs else None

    def cleanup_old_runs(
        self,
        experiment_name: str,
        days_to_keep: int = 90,
        dry_run: bool = True
    ) -> int:
        """
        Clean up old runs from an experiment.

        Args:
            experiment_name: Name of experiment to clean
            days_to_keep: Number of days to retain runs
            dry_run: If True, only log what would be deleted

        Returns:
            Number of runs deleted (or would be deleted)
        """
        if not self._initialized:
            self.setup()

        experiment = self.client.get_experiment_by_name(experiment_name)
        if not experiment:
            return 0

        try:
            # Calculate cutoff timestamp
            from datetime import timedelta
            cutoff = datetime.now() - timedelta(days=days_to_keep)
            cutoff_ts = int(cutoff.timestamp() * 1000)

            # Find old runs
            runs = self.client.search_runs(
                experiment_ids=[experiment.experiment_id],
                filter_string=f"start_time < {cutoff_ts}",
                run_view_type=ViewType.ACTIVE_ONLY
            )

            deleted_count = 0
            for run in runs:
                if dry_run:
                    logger.info(f"Would delete run: {run.info.run_id}")
                else:
                    self.client.delete_run(run.info.run_id)
                    logger.info(f"Deleted run: {run.info.run_id}")
                deleted_count += 1

            return deleted_count

        except Exception as e:
            logger.error(f"Failed to cleanup runs: {e}")
            return 0


# Global instance
_mlflow_config: Optional[MLflowConfig] = None


def get_mlflow_config() -> MLflowConfig:
    """
    Get or create the global MLflowConfig instance.

    Returns:
        MLflowConfig instance
    """
    global _mlflow_config

    if _mlflow_config is None:
        _mlflow_config = MLflowConfig()
        _mlflow_config.setup()

    return _mlflow_config


def get_mlflow_client() -> MlflowClient:
    """
    Get the MLflow tracking client.

    Returns:
        MlflowClient instance
    """
    config = get_mlflow_config()
    return config.client


def initialize_mlflow() -> None:
    """
    Initialize MLflow for the application.

    Should be called during Django app startup.
    """
    config = get_mlflow_config()
    logger.info("MLflow initialized for SmartHR360")
