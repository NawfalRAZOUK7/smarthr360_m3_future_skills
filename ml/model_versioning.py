# ml/model_versioning.py

"""
Model Versioning System for SmartHR360.

Provides semantic versioning, model metadata management, and version comparison
for ML models with integration to MLflow Model Registry.

Features:
- Semantic versioning (MAJOR.MINOR.PATCH)
- Model metadata tracking (metrics, parameters, timestamps)
- Version comparison and promotion logic
- Integration with Django models and MLflow
- Model lineage tracking

Usage:
    from ml.model_versioning import ModelVersion, ModelVersionManager

    # Create new model version
    version = ModelVersion(
        major=1,
        minor=0,
        patch=0,
        metrics={"accuracy": 0.95, "f1_score": 0.94},
        model_path="/path/to/model.pkl"
    )

    # Manage versions
    manager = ModelVersionManager()
    manager.register_version(version)

    # Compare versions
    is_better = manager.should_promote(new_version, current_version)
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import semver
from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)


class ModelStage(str, Enum):
    """Model lifecycle stages."""

    DEVELOPMENT = "Development"
    STAGING = "Staging"
    PRODUCTION = "Production"
    ARCHIVED = "Archived"
    FAILED = "Failed"


class ModelFramework(str, Enum):
    """Supported ML frameworks."""

    SCIKIT_LEARN = "scikit-learn"
    TENSORFLOW = "tensorflow"
    PYTORCH = "pytorch"
    XGBOOST = "xgboost"
    LIGHTGBM = "lightgbm"
    CATBOOST = "catboost"
    CUSTOM = "custom"


class ModelMetrics(BaseModel):
    """Model performance metrics."""

    accuracy: Optional[float] = Field(None, ge=0.0, le=1.0)
    precision: Optional[float] = Field(None, ge=0.0, le=1.0)
    recall: Optional[float] = Field(None, ge=0.0, le=1.0)
    f1_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    roc_auc: Optional[float] = Field(None, ge=0.0, le=1.0)
    log_loss: Optional[float] = Field(None, ge=0.0)
    training_time: Optional[float] = Field(None, ge=0.0, description="Training time in seconds")
    inference_time: Optional[float] = Field(None, ge=0.0, description="Average inference time in ms")

    # Custom metrics
    custom_metrics: Dict[str, float] = Field(default_factory=dict)

    class Config:
        extra = "allow"  # Allow additional metrics

    @validator("custom_metrics")
    def validate_custom_metrics(cls, v):
        """Ensure all custom metrics are numeric."""
        for key, value in v.items():
            if not isinstance(value, (int, float)):
                raise ValueError(f"Custom metric '{key}' must be numeric")
        return v

    def get_primary_metric(self, metric_name: str = "accuracy") -> float:
        """Get the primary metric for comparison."""
        if metric_name in ["accuracy", "precision", "recall", "f1_score", "roc_auc"]:
            return getattr(self, metric_name, 0.0) or 0.0
        return self.custom_metrics.get(metric_name, 0.0)

    def to_dict(self) -> Dict[str, float]:
        """Convert metrics to dictionary."""
        metrics_dict = {k: v for k, v in self.dict().items() if v is not None and k != "custom_metrics"}
        metrics_dict.update(self.custom_metrics)
        return metrics_dict


class ModelMetadata(BaseModel):
    """Comprehensive model metadata."""

    model_id: str = Field(..., description="Unique model identifier")
    version_string: str = Field(..., description="Semantic version string")

    # Model info
    framework: ModelFramework = ModelFramework.SCIKIT_LEARN
    algorithm: Optional[str] = Field(None, description="Algorithm name (e.g., RandomForest)")
    model_path: Optional[str] = Field(None, description="Path to model file")
    model_size_mb: Optional[float] = Field(None, ge=0.0)

    # Training info
    training_dataset_size: Optional[int] = Field(None, ge=0)
    training_features: List[str] = Field(default_factory=list)
    target_classes: List[str] = Field(default_factory=list)
    hyperparameters: Dict[str, Any] = Field(default_factory=dict)

    # Performance
    metrics: ModelMetrics = Field(default_factory=ModelMetrics)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    trained_at: Optional[datetime] = None
    deployed_at: Optional[datetime] = None

    # Lifecycle
    stage: ModelStage = ModelStage.DEVELOPMENT
    tags: Dict[str, str] = Field(default_factory=dict)
    description: Optional[str] = None

    # Lineage
    parent_version: Optional[str] = None
    mlflow_run_id: Optional[str] = None
    mlflow_model_uri: Optional[str] = None

    class Config:
        use_enum_values = True

    def get_version(self) -> semver.VersionInfo:
        """Get semantic version object."""
        return semver.VersionInfo.parse(self.version_string)

    def is_production(self) -> bool:
        """Check if model is in production."""
        return self.stage == ModelStage.PRODUCTION

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with serializable types."""
        data = self.dict()
        # Convert datetime to ISO format
        for key in ["created_at", "trained_at", "deployed_at"]:
            if data.get(key):
                data[key] = data[key].isoformat()
        return data


@dataclass
class ModelVersion:
    """
    Semantic version for ML models.

    Version format: MAJOR.MINOR.PATCH
    - MAJOR: Incompatible changes (new features, breaking changes)
    - MINOR: Backward-compatible changes (improvements, tuning)
    - PATCH: Bug fixes, small improvements
    """

    major: int
    minor: int
    patch: int
    prerelease: Optional[str] = None  # e.g., "alpha", "beta", "rc.1"
    build: Optional[str] = None  # e.g., "20240115"

    metadata: Optional[ModelMetadata] = None

    def __str__(self) -> str:
        """String representation."""
        version = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            version += f"-{self.prerelease}"
        if self.build:
            version += f"+{self.build}"
        return version

    def __repr__(self) -> str:
        return f"ModelVersion({str(self)})"

    def __eq__(self, other: "ModelVersion") -> bool:
        """Check equality."""
        if not isinstance(other, ModelVersion):
            return False
        return str(self) == str(other)

    def __lt__(self, other: "ModelVersion") -> bool:
        """Compare versions."""
        if not isinstance(other, ModelVersion):
            return NotImplemented
        return semver.compare(str(self), str(other)) < 0

    def __le__(self, other: "ModelVersion") -> bool:
        return self < other or self == other

    def __gt__(self, other: "ModelVersion") -> bool:
        if not isinstance(other, ModelVersion):
            return NotImplemented
        return semver.compare(str(self), str(other)) > 0

    def __ge__(self, other: "ModelVersion") -> bool:
        return self > other or self == other

    @classmethod
    def from_string(cls, version_string: str) -> "ModelVersion":
        """Create ModelVersion from string.

        Supports both standard SemVer format (1.0.0) and 'v' prefixed format (v1.0.0).
        """
        try:
            # Strip leading 'v' or 'V' prefix if present
            cleaned_version = version_string.lstrip("vV")
            parsed = semver.VersionInfo.parse(cleaned_version)
            return cls(
                major=parsed.major,
                minor=parsed.minor,
                patch=parsed.patch,
                prerelease=parsed.prerelease or None,
                build=parsed.build or None,
            )
        except ValueError as e:
            raise ValueError(f"Invalid version string '{version_string}': {e}")

    def bump_major(self) -> "ModelVersion":
        """Create new version with bumped major number."""
        return ModelVersion(self.major + 1, 0, 0)

    def bump_minor(self) -> "ModelVersion":
        """Create new version with bumped minor number."""
        return ModelVersion(self.major, self.minor + 1, 0)

    def bump_patch(self) -> "ModelVersion":
        """Create new version with bumped patch number."""
        return ModelVersion(self.major, self.minor, self.patch + 1)

    def is_prerelease(self) -> bool:
        """Check if this is a prerelease version."""
        return self.prerelease is not None

    def is_stable(self) -> bool:
        """Check if this is a stable release."""
        return not self.is_prerelease()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = {
            "version": str(self),
            "major": self.major,
            "minor": self.minor,
            "patch": self.patch,
        }
        if self.prerelease:
            data["prerelease"] = self.prerelease
        if self.build:
            data["build"] = self.build
        if self.metadata:
            data["metadata"] = self.metadata.to_dict()
        return data


class ModelVersionManager:
    """
    Manages model versions and promotion logic.

    Handles version comparison, promotion decisions, and version history.
    """

    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize version manager.

        Args:
            storage_path: Path to store version metadata
        """
        self.storage_path = storage_path or Path("ml/versions")
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.versions: List[ModelVersion] = []
        self._load_versions()

    def _load_versions(self) -> None:
        """Load version history from storage."""
        versions_file = self.storage_path / "versions.json"
        if versions_file.exists():
            try:
                with open(versions_file, "r") as f:
                    data = json.load(f)
                    for version_data in data.get("versions", []):
                        version = ModelVersion.from_string(version_data["version"])
                        if "metadata" in version_data:
                            version.metadata = ModelMetadata(**version_data["metadata"])
                        self.versions.append(version)
            except Exception as e:
                logger.error(f"Failed to load version history: {e}")

    def _save_versions(self) -> None:
        """Save version history to storage."""
        versions_file = self.storage_path / "versions.json"
        try:
            data = {
                "versions": [v.to_dict() for v in self.versions],
                "updated_at": datetime.now().isoformat(),
            }
            with open(versions_file, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save version history: {e}")

    def register_version(self, version: ModelVersion) -> None:
        """
        Register a new model version.

        Args:
            version: ModelVersion to register
        """
        if version in self.versions:
            logger.warning(f"Version {version} already registered")
            return

        self.versions.append(version)
        self.versions.sort(reverse=True)  # Keep sorted (newest first)
        self._save_versions()

        logger.info(f"Registered model version: {version}")

    def get_latest_version(
        self, stage: Optional[ModelStage] = None, stable_only: bool = False
    ) -> Optional[ModelVersion]:
        """
        Get the latest version, optionally filtered by stage.

        Args:
            stage: Filter by lifecycle stage
            stable_only: If True, only return stable (non-prerelease) versions

        Returns:
            Latest ModelVersion or None
        """
        filtered_versions = self.versions

        if stage:
            filtered_versions = [v for v in filtered_versions if v.metadata and v.metadata.stage == stage]

        if stable_only:
            filtered_versions = [v for v in filtered_versions if v.is_stable()]

        return filtered_versions[0] if filtered_versions else None

    def get_production_version(self) -> Optional[ModelVersion]:
        """Get current production version."""
        return self.get_latest_version(stage=ModelStage.PRODUCTION)

    def should_promote(
        self,
        new_version: ModelVersion,
        current_version: Optional[ModelVersion] = None,
        metric_name: str = "accuracy",
        improvement_threshold: float = 0.01,
    ) -> Tuple[bool, str]:
        """
        Determine if new version should be promoted.

        Args:
            new_version: New model version to evaluate
            current_version: Current version to compare against (default: production)
            metric_name: Metric to compare
            improvement_threshold: Minimum improvement required (e.g., 0.01 = 1%)

        Returns:
            Tuple of (should_promote, reason)
        """
        if current_version is None:
            current_version = self.get_production_version()

        # If no current version, promote by default
        if current_version is None:
            return True, "No current production model"

        # Check if both versions have metrics
        if not new_version.metadata or not new_version.metadata.metrics:
            return False, "New version has no metrics"

        if not current_version.metadata or not current_version.metadata.metrics:
            return True, "Current version has no metrics"

        # Compare metrics
        new_metric = new_version.metadata.metrics.get_primary_metric(metric_name)
        current_metric = current_version.metadata.metrics.get_primary_metric(metric_name)

        improvement = new_metric - current_metric

        if improvement < improvement_threshold:
            return False, (f"Insufficient improvement: {improvement:.4f} " f"(threshold: {improvement_threshold:.4f})")

        return True, (
            f"Significant improvement: {improvement:.4f} " f"({metric_name}: {current_metric:.4f} → {new_metric:.4f})"
        )

    def auto_version(self, current_version: Optional[ModelVersion] = None, change_type: str = "patch") -> ModelVersion:
        """
        Automatically generate next version number.

        Args:
            current_version: Base version (default: latest)
            change_type: Type of change ("major", "minor", "patch")

        Returns:
            New ModelVersion
        """
        if current_version is None:
            current_version = self.get_latest_version()

        if current_version is None:
            # First version
            return ModelVersion(1, 0, 0)

        if change_type == "major":
            return current_version.bump_major()
        elif change_type == "minor":
            return current_version.bump_minor()
        else:
            return current_version.bump_patch()

    def get_version_history(
        self, limit: Optional[int] = None, stage: Optional[ModelStage] = None
    ) -> List[ModelVersion]:
        """
        Get version history.

        Args:
            limit: Maximum number of versions to return
            stage: Filter by stage

        Returns:
            List of ModelVersion objects
        """
        versions = self.versions

        if stage:
            versions = [v for v in versions if v.metadata and v.metadata.stage == stage]

        if limit:
            versions = versions[:limit]

        return versions

    def compare_versions(
        self,
        version1: ModelVersion,
        version2: ModelVersion,
        metrics: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Compare two model versions.

        Args:
            version1: First version
            version2: Second version
            metrics: List of metrics to compare

        Returns:
            Comparison dictionary
        """
        if metrics is None:
            metrics = ["accuracy", "precision", "recall", "f1_score"]

        comparison = {
            "version1": str(version1),
            "version2": str(version2),
            "newer": version1 > version2,
            "metrics": {},
        }

        if version1.metadata and version2.metadata:
            for metric in metrics:
                val1 = version1.metadata.metrics.get_primary_metric(metric)
                val2 = version2.metadata.metrics.get_primary_metric(metric)

                comparison["metrics"][metric] = {
                    "version1": val1,
                    "version2": val2,
                    "diff": val1 - val2,
                    "improvement": ((val1 - val2) / val2 * 100) if val2 > 0 else 0,
                }

        return comparison

    def archive_old_versions(self, keep_latest: int = 5, keep_production: bool = True) -> int:
        """
        Archive old model versions.

        Args:
            keep_latest: Number of latest versions to keep
            keep_production: Whether to keep production versions

        Returns:
            Number of versions archived
        """
        archived_count = 0

        for i, version in enumerate(self.versions):
            if i < keep_latest:
                continue

            if keep_production and version.metadata:
                if version.metadata.stage == ModelStage.PRODUCTION:
                    continue

            if version.metadata:
                version.metadata.stage = ModelStage.ARCHIVED
                archived_count += 1

        if archived_count > 0:
            self._save_versions()
            logger.info(f"Archived {archived_count} model versions")

        return archived_count


def create_model_version(
    version_string: str,
    metrics: Dict[str, float],
    model_path: str,
    framework: str = "scikit-learn",
    algorithm: Optional[str] = None,
    hyperparameters: Optional[Dict[str, Any]] = None,
    stage: str = "Development",
    **kwargs,
) -> ModelVersion:
    """
    Helper function to create a ModelVersion with metadata.

    Args:
        version_string: Semantic version string (e.g., "1.0.0")
        metrics: Dictionary of performance metrics
        model_path: Path to model file
        framework: ML framework used
        algorithm: Algorithm name
        hyperparameters: Model hyperparameters
        stage: Lifecycle stage
        **kwargs: Additional metadata fields

    Returns:
        ModelVersion instance
    """
    version = ModelVersion.from_string(version_string)

    # Create metrics object
    model_metrics = ModelMetrics(**metrics)

    # Create metadata
    metadata = ModelMetadata(
        model_id=kwargs.get("model_id", f"model_{version_string}"),
        version_string=version_string,
        framework=ModelFramework(framework),
        algorithm=algorithm,
        model_path=model_path,
        hyperparameters=hyperparameters or {},
        metrics=model_metrics,
        stage=ModelStage(stage),
        **{k: v for k, v in kwargs.items() if k not in ["model_id"]},
    )

    version.metadata = metadata

    return version
