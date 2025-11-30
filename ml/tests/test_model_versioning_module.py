"""
Comprehensive tests for ml/model_versioning.py module.

Tests cover:
- ModelStage and ModelFramework enums
- ModelMetrics validation and operations
- ModelMetadata creation and methods
- ModelVersion comparison and operations
- ModelVersionManager version management
- create_model_version helper function
"""

from datetime import datetime
from unittest.mock import patch

import pytest

from ml.model_versioning import (
    ModelFramework,
    ModelMetadata,
    ModelMetrics,
    ModelStage,
    ModelVersion,
    ModelVersionManager,
    create_model_version,
)


class TestModelStageEnum:
    """Tests for ModelStage enum."""

    def test_model_stage_values(self):
        """Test that all model stages have correct values."""
        assert ModelStage.DEVELOPMENT == "Development"
        assert ModelStage.STAGING == "Staging"
        assert ModelStage.PRODUCTION == "Production"
        assert ModelStage.ARCHIVED == "Archived"
        assert ModelStage.FAILED == "Failed"

    def test_model_stage_membership(self):
        """Test ModelStage membership."""
        assert "Development" in [stage.value for stage in ModelStage]
        assert "Production" in [stage.value for stage in ModelStage]


class TestModelFrameworkEnum:
    """Tests for ModelFramework enum."""

    def test_model_framework_values(self):
        """Test that all frameworks are represented."""
        assert ModelFramework.SCIKIT_LEARN == "scikit-learn"
        assert ModelFramework.TENSORFLOW == "tensorflow"
        assert ModelFramework.PYTORCH == "pytorch"
        assert ModelFramework.XGBOOST == "xgboost"
        assert ModelFramework.LIGHTGBM == "lightgbm"
        assert ModelFramework.CATBOOST == "catboost"
        assert ModelFramework.CUSTOM == "custom"

    def test_framework_membership(self):
        """Test framework membership."""
        frameworks = [f.value for f in ModelFramework]
        assert "scikit-learn" in frameworks
        assert "pytorch" in frameworks


class TestModelMetrics:
    """Tests for ModelMetrics class."""

    def test_create_metrics_with_valid_values(self):
        """Test creating metrics with valid values."""
        metrics = ModelMetrics(
            accuracy=0.95, precision=0.92, recall=0.88, f1_score=0.90, roc_auc=0.93
        )
        assert metrics.accuracy == 0.95
        assert metrics.precision == 0.92
        assert metrics.f1_score == 0.90

    def test_metrics_validation_range(self):
        """Test that metrics are validated to be in [0, 1] range."""
        with pytest.raises(Exception):  # Pydantic validation error
            ModelMetrics(accuracy=1.5)

        with pytest.raises(Exception):
            ModelMetrics(precision=-0.1)

    def test_custom_metrics(self):
        """Test custom metrics dictionary."""
        metrics = ModelMetrics(
            accuracy=0.95, custom_metrics={"mae": 0.05, "custom_score": 0.88}
        )
        assert metrics.custom_metrics["mae"] == 0.05
        assert metrics.custom_metrics["custom_score"] == 0.88

    def test_custom_metrics_validation_non_numeric(self):
        """Test that custom metrics must be numeric."""
        with pytest.raises(Exception):  # Validation error
            ModelMetrics(custom_metrics={"invalid": "string_value"})

    def test_get_primary_metric_standard(self):
        """Test getting standard primary metric."""
        metrics = ModelMetrics(accuracy=0.95, f1_score=0.90)
        assert metrics.get_primary_metric("accuracy") == 0.95
        assert metrics.get_primary_metric("f1_score") == 0.90

    def test_get_primary_metric_custom(self):
        """Test getting custom primary metric."""
        metrics = ModelMetrics(accuracy=0.95, custom_metrics={"custom_score": 0.88})
        assert metrics.get_primary_metric("custom_score") == 0.88

    def test_get_primary_metric_missing(self):
        """Test getting missing metric returns 0.0."""
        metrics = ModelMetrics(accuracy=0.95)
        assert metrics.get_primary_metric("nonexistent") == 0.0

    def test_get_primary_metric_none_value(self):
        """Test handling None values in metrics."""
        metrics = ModelMetrics(accuracy=None, precision=0.90)
        assert metrics.get_primary_metric("accuracy") == 0.0

    def test_to_dict(self):
        """Test converting metrics to dictionary."""
        metrics = ModelMetrics(
            accuracy=0.95, f1_score=0.90, custom_metrics={"mae": 0.05}
        )
        metrics_dict = metrics.to_dict()
        assert metrics_dict["accuracy"] == 0.95
        assert metrics_dict["f1_score"] == 0.90
        assert metrics_dict["mae"] == 0.05

    def test_training_and_inference_time(self):
        """Test training and inference time metrics."""
        metrics = ModelMetrics(accuracy=0.95, training_time=120.5, inference_time=5.2)
        assert metrics.training_time == 120.5
        assert metrics.inference_time == 5.2

    def test_log_loss_metric(self):
        """Test log loss metric (no upper bound)."""
        metrics = ModelMetrics(log_loss=0.25)
        assert metrics.log_loss == 0.25


class TestModelMetadata:
    """Tests for ModelMetadata class."""

    def test_create_metadata_minimal(self):
        """Test creating metadata with minimal required fields."""
        metadata = ModelMetadata(model_id="test_model", version_string="1.0.0")
        assert metadata.model_id == "test_model"
        assert metadata.version_string == "1.0.0"
        assert metadata.framework == ModelFramework.SCIKIT_LEARN
        assert metadata.stage == ModelStage.DEVELOPMENT

    def test_create_metadata_comprehensive(self):
        """Test creating metadata with all fields."""
        metrics = ModelMetrics(accuracy=0.95, f1_score=0.90)
        metadata = ModelMetadata(
            model_id="model_123",
            version_string="2.1.0",
            framework=ModelFramework.PYTORCH,
            algorithm="ResNet50",
            model_path="/path/to/model.pth",
            model_size_mb=150.5,
            training_dataset_size=10000,
            training_features=["feature1", "feature2"],
            target_classes=["class_a", "class_b"],
            hyperparameters={"lr": 0.001, "epochs": 50},
            metrics=metrics,
            stage=ModelStage.PRODUCTION,
            tags={"env": "prod", "team": "ml"},
            description="Production model",
            parent_version="2.0.0",
            mlflow_run_id="run_123",
        )
        assert metadata.model_id == "model_123"
        assert metadata.algorithm == "ResNet50"
        assert metadata.model_size_mb == 150.5
        assert metadata.training_dataset_size == 10000
        assert len(metadata.training_features) == 2
        assert metadata.stage == ModelStage.PRODUCTION

    def test_get_version(self):
        """Test getting semantic version object."""
        metadata = ModelMetadata(model_id="test", version_string="1.2.3")
        version = metadata.get_version()
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3

    def test_is_production(self):
        """Test checking if model is in production."""
        prod_metadata = ModelMetadata(
            model_id="test", version_string="1.0.0", stage=ModelStage.PRODUCTION
        )
        dev_metadata = ModelMetadata(
            model_id="test", version_string="1.0.1", stage=ModelStage.DEVELOPMENT
        )
        assert prod_metadata.is_production() is True
        assert dev_metadata.is_production() is False

    def test_to_dict_serialization(self):
        """Test converting metadata to dictionary with datetime serialization."""
        metadata = ModelMetadata(
            model_id="test",
            version_string="1.0.0",
            trained_at=datetime(2024, 1, 15, 10, 30),
        )
        data = metadata.to_dict()
        assert data["model_id"] == "test"
        assert "2024-01-15" in data["trained_at"]

    def test_default_timestamps(self):
        """Test that created_at has default value."""
        metadata = ModelMetadata(model_id="test", version_string="1.0.0")
        assert metadata.created_at is not None
        assert isinstance(metadata.created_at, datetime)

    def test_hyperparameters_storage(self):
        """Test storing complex hyperparameters."""
        hyperparams = {
            "learning_rate": 0.001,
            "batch_size": 32,
            "optimizer": "adam",
            "layers": [128, 64, 32],
        }
        metadata = ModelMetadata(
            model_id="test", version_string="1.0.0", hyperparameters=hyperparams
        )
        assert metadata.hyperparameters["learning_rate"] == 0.001
        assert len(metadata.hyperparameters["layers"]) == 3


class TestModelVersion:
    """Tests for ModelVersion class."""

    def test_create_version_basic(self):
        """Test creating basic version."""
        version = ModelVersion(major=1, minor=0, patch=0)
        assert version.major == 1
        assert version.minor == 0
        assert version.patch == 0

    def test_version_string_representation(self):
        """Test string representation of version."""
        version = ModelVersion(1, 2, 3)
        assert str(version) == "1.2.3"

    def test_version_with_prerelease(self):
        """Test version with prerelease tag."""
        version = ModelVersion(1, 0, 0, prerelease="alpha")
        assert str(version) == "1.0.0-alpha"

    def test_version_with_build(self):
        """Test version with build metadata."""
        version = ModelVersion(1, 0, 0, build="20240115")
        assert str(version) == "1.0.0+20240115"

    def test_version_with_prerelease_and_build(self):
        """Test version with both prerelease and build."""
        version = ModelVersion(1, 0, 0, prerelease="beta.1", build="20240115")
        assert str(version) == "1.0.0-beta.1+20240115"

    def test_version_repr(self):
        """Test repr representation."""
        version = ModelVersion(1, 2, 3)
        assert repr(version) == "ModelVersion(1.2.3)"

    def test_version_equality(self):
        """Test version equality comparison."""
        v1 = ModelVersion(1, 0, 0)
        v2 = ModelVersion(1, 0, 0)
        v3 = ModelVersion(1, 0, 1)
        assert v1 == v2
        assert v1 != v3

    def test_version_equality_non_version(self):
        """Test equality with non-version object."""
        version = ModelVersion(1, 0, 0)
        assert version != "1.0.0"
        assert version != 1

    def test_version_less_than(self):
        """Test less than comparison."""
        v1 = ModelVersion(1, 0, 0)
        v2 = ModelVersion(1, 0, 1)
        v3 = ModelVersion(2, 0, 0)
        assert v1 < v2
        assert v1 < v3
        assert v2 < v3

    def test_version_less_than_non_version(self):
        """Test less than with non-version returns NotImplemented."""
        version = ModelVersion(1, 0, 0)
        result = version.__lt__("1.0.0")
        assert result == NotImplemented

    def test_version_greater_than(self):
        """Test greater than comparison."""
        v1 = ModelVersion(2, 0, 0)
        v2 = ModelVersion(1, 0, 1)
        v3 = ModelVersion(1, 0, 0)
        assert v1 > v2
        assert v1 > v3
        assert v2 > v3

    def test_version_greater_than_non_version(self):
        """Test greater than with non-version returns NotImplemented."""
        version = ModelVersion(1, 0, 0)
        result = version.__gt__("1.0.0")
        assert result == NotImplemented

    def test_version_less_than_or_equal(self):
        """Test less than or equal comparison."""
        v1 = ModelVersion(1, 0, 0)
        v2 = ModelVersion(1, 0, 0)
        v3 = ModelVersion(1, 0, 1)
        assert v1 <= v2
        assert v1 <= v3

    def test_version_greater_than_or_equal(self):
        """Test greater than or equal comparison."""
        v1 = ModelVersion(1, 0, 1)
        v2 = ModelVersion(1, 0, 1)
        v3 = ModelVersion(1, 0, 0)
        assert v1 >= v2
        assert v1 >= v3

    def test_from_string_basic(self):
        """Test creating version from string."""
        version = ModelVersion.from_string("1.2.3")
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3

    def test_from_string_with_v_prefix(self):
        """Test creating version from string with 'v' prefix."""
        version = ModelVersion.from_string("v1.2.3")
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3

    def test_from_string_with_uppercase_v(self):
        """Test creating version from string with 'V' prefix."""
        version = ModelVersion.from_string("V2.0.1")
        assert version.major == 2
        assert version.minor == 0
        assert version.patch == 1

    def test_from_string_with_prerelease(self):
        """Test parsing version with prerelease."""
        version = ModelVersion.from_string("1.0.0-alpha")
        assert version.major == 1
        assert version.prerelease == "alpha"

    def test_from_string_with_build(self):
        """Test parsing version with build metadata."""
        version = ModelVersion.from_string("1.0.0+20240115")
        assert version.major == 1
        assert version.build == "20240115"

    def test_from_string_invalid(self):
        """Test that invalid version string raises error."""
        with pytest.raises(ValueError, match="Invalid version string"):
            ModelVersion.from_string("invalid")

        with pytest.raises(ValueError):
            ModelVersion.from_string("1.0")

    def test_bump_major(self):
        """Test bumping major version."""
        version = ModelVersion(1, 2, 3)
        bumped = version.bump_major()
        assert str(bumped) == "2.0.0"

    def test_bump_minor(self):
        """Test bumping minor version."""
        version = ModelVersion(1, 2, 3)
        bumped = version.bump_minor()
        assert str(bumped) == "1.3.0"

    def test_bump_patch(self):
        """Test bumping patch version."""
        version = ModelVersion(1, 2, 3)
        bumped = version.bump_patch()
        assert str(bumped) == "1.2.4"

    def test_is_prerelease(self):
        """Test checking if version is prerelease."""
        stable = ModelVersion(1, 0, 0)
        prerelease = ModelVersion(1, 0, 0, prerelease="alpha")
        assert stable.is_prerelease() is False
        assert prerelease.is_prerelease() is True

    def test_is_stable(self):
        """Test checking if version is stable."""
        stable = ModelVersion(1, 0, 0)
        prerelease = ModelVersion(1, 0, 0, prerelease="beta")
        assert stable.is_stable() is True
        assert prerelease.is_stable() is False

    def test_to_dict_basic(self):
        """Test converting version to dictionary."""
        version = ModelVersion(1, 2, 3)
        data = version.to_dict()
        assert data["version"] == "1.2.3"
        assert data["major"] == 1
        assert data["minor"] == 2
        assert data["patch"] == 3

    def test_to_dict_with_prerelease_and_build(self):
        """Test to_dict with prerelease and build."""
        version = ModelVersion(1, 0, 0, prerelease="rc.1", build="20240115")
        data = version.to_dict()
        assert data["prerelease"] == "rc.1"
        assert data["build"] == "20240115"

    def test_to_dict_with_metadata(self):
        """Test to_dict includes metadata."""
        metadata = ModelMetadata(model_id="test", version_string="1.0.0")
        version = ModelVersion(1, 0, 0, metadata=metadata)
        data = version.to_dict()
        assert "metadata" in data
        assert data["metadata"]["model_id"] == "test"


class TestModelVersionManager:
    """Tests for ModelVersionManager class."""

    def test_manager_initialization(self, tmp_path):
        """Test initializing version manager."""
        manager = ModelVersionManager(storage_path=tmp_path)
        assert manager.storage_path == tmp_path
        assert manager.versions == []

    def test_manager_creates_storage_directory(self, tmp_path):
        """Test that manager creates storage directory."""
        storage_path = tmp_path / "versions"
        manager = ModelVersionManager(storage_path=storage_path)
        assert storage_path.exists()

    def test_register_version(self, tmp_path):
        """Test registering a new version."""
        manager = ModelVersionManager(storage_path=tmp_path)
        version = ModelVersion(1, 0, 0)
        manager.register_version(version)
        assert len(manager.versions) == 1
        assert manager.versions[0] == version

    def test_register_duplicate_version(self, tmp_path):
        """Test that duplicate versions are not registered twice."""
        manager = ModelVersionManager(storage_path=tmp_path)
        version = ModelVersion(1, 0, 0)
        manager.register_version(version)
        manager.register_version(version)
        assert len(manager.versions) == 1

    def test_versions_sorted_descending(self, tmp_path):
        """Test that versions are kept sorted (newest first)."""
        manager = ModelVersionManager(storage_path=tmp_path)
        v1 = ModelVersion(1, 0, 0)
        v2 = ModelVersion(2, 0, 0)
        v3 = ModelVersion(1, 5, 0)
        manager.register_version(v1)
        manager.register_version(v2)
        manager.register_version(v3)
        assert manager.versions[0] == v2
        assert manager.versions[1] == v3
        assert manager.versions[2] == v1

    def test_get_latest_version(self, tmp_path):
        """Test getting latest version."""
        manager = ModelVersionManager(storage_path=tmp_path)
        v1 = ModelVersion(1, 0, 0)
        v2 = ModelVersion(2, 0, 0)
        manager.register_version(v1)
        manager.register_version(v2)
        latest = manager.get_latest_version()
        assert latest == v2

    def test_get_latest_version_empty(self, tmp_path):
        """Test getting latest version from empty manager."""
        manager = ModelVersionManager(storage_path=tmp_path)
        assert manager.get_latest_version() is None

    def test_get_latest_version_by_stage(self, tmp_path):
        """Test getting latest version filtered by stage."""
        manager = ModelVersionManager(storage_path=tmp_path)

        metadata1 = ModelMetadata(
            model_id="m1", version_string="1.0.0", stage=ModelStage.PRODUCTION
        )
        metadata2 = ModelMetadata(
            model_id="m2", version_string="2.0.0", stage=ModelStage.DEVELOPMENT
        )

        v1 = ModelVersion(1, 0, 0, metadata=metadata1)
        v2 = ModelVersion(2, 0, 0, metadata=metadata2)

        manager.register_version(v1)
        manager.register_version(v2)

        prod_version = manager.get_latest_version(stage=ModelStage.PRODUCTION)
        assert prod_version == v1

    def test_get_latest_version_stable_only(self, tmp_path):
        """Test getting latest stable version."""
        manager = ModelVersionManager(storage_path=tmp_path)
        v1 = ModelVersion(1, 0, 0)
        v2 = ModelVersion(2, 0, 0, prerelease="beta")
        manager.register_version(v1)
        manager.register_version(v2)

        latest_stable = manager.get_latest_version(stable_only=True)
        assert latest_stable == v1

    def test_get_production_version(self, tmp_path):
        """Test getting production version."""
        manager = ModelVersionManager(storage_path=tmp_path)

        metadata = ModelMetadata(
            model_id="test", version_string="1.0.0", stage=ModelStage.PRODUCTION
        )
        version = ModelVersion(1, 0, 0, metadata=metadata)
        manager.register_version(version)

        prod_version = manager.get_production_version()
        assert prod_version == version

    def test_should_promote_no_current_version(self, tmp_path):
        """Test promotion when no current version exists."""
        manager = ModelVersionManager(storage_path=tmp_path)
        new_version = ModelVersion(1, 0, 0)
        should_promote, reason = manager.should_promote(new_version)
        assert should_promote is True
        assert "No current production model" in reason

    def test_should_promote_new_version_no_metrics(self, tmp_path):
        """Test that versions without metrics are not promoted."""
        manager = ModelVersionManager(storage_path=tmp_path)

        current_metadata = ModelMetadata(
            model_id="current", version_string="1.0.0", stage=ModelStage.PRODUCTION
        )
        current_version = ModelVersion(1, 0, 0, metadata=current_metadata)
        new_version = ModelVersion(2, 0, 0)

        should_promote, reason = manager.should_promote(new_version, current_version)
        assert should_promote is False
        assert "no metrics" in reason

    def test_should_promote_current_version_no_metrics(self, tmp_path):
        """Test promotion when current version has no metrics."""
        manager = ModelVersionManager(storage_path=tmp_path)

        current_metadata = ModelMetadata(model_id="current", version_string="1.0.0")
        current_version = ModelVersion(1, 0, 0, metadata=current_metadata)

        new_metadata = ModelMetadata(
            model_id="new", version_string="2.0.0", metrics=ModelMetrics(accuracy=0.95)
        )
        new_version = ModelVersion(2, 0, 0, metadata=new_metadata)

        should_promote, reason = manager.should_promote(new_version, current_version)
        assert should_promote is True
        assert (
            "Current version has no metrics" in reason
            or "improvement" in reason.lower()
        )

    def test_should_promote_with_improvement(self, tmp_path):
        """Test promotion when new version has improvement."""
        manager = ModelVersionManager(storage_path=tmp_path)

        current_metadata = ModelMetadata(
            model_id="current",
            version_string="1.0.0",
            metrics=ModelMetrics(accuracy=0.85),
        )
        current_version = ModelVersion(1, 0, 0, metadata=current_metadata)

        new_metadata = ModelMetadata(
            model_id="new", version_string="2.0.0", metrics=ModelMetrics(accuracy=0.90)
        )
        new_version = ModelVersion(2, 0, 0, metadata=new_metadata)

        should_promote, reason = manager.should_promote(
            new_version, current_version, improvement_threshold=0.01
        )
        assert should_promote is True
        assert "improvement" in reason.lower()
        assert "0.85" in reason
        assert "0.90" in reason

    def test_should_promote_insufficient_improvement(self, tmp_path):
        """Test promotion rejected when improvement is insufficient."""
        manager = ModelVersionManager(storage_path=tmp_path)

        current_metadata = ModelMetadata(
            model_id="current",
            version_string="1.0.0",
            metrics=ModelMetrics(accuracy=0.85),
        )
        current_version = ModelVersion(1, 0, 0, metadata=current_metadata)

        new_metadata = ModelMetadata(
            model_id="new", version_string="2.0.0", metrics=ModelMetrics(accuracy=0.855)
        )
        new_version = ModelVersion(2, 0, 0, metadata=new_metadata)

        should_promote, reason = manager.should_promote(
            new_version, current_version, improvement_threshold=0.01
        )
        assert should_promote is False
        assert "Insufficient improvement" in reason

    def test_should_promote_custom_metric(self, tmp_path):
        """Test promotion using custom metric."""
        manager = ModelVersionManager(storage_path=tmp_path)

        current_metadata = ModelMetadata(
            model_id="current",
            version_string="1.0.0",
            metrics=ModelMetrics(custom_metrics={"custom_score": 0.80}),
        )
        current_version = ModelVersion(1, 0, 0, metadata=current_metadata)

        new_metadata = ModelMetadata(
            model_id="new",
            version_string="2.0.0",
            metrics=ModelMetrics(custom_metrics={"custom_score": 0.90}),
        )
        new_version = ModelVersion(2, 0, 0, metadata=new_metadata)

        should_promote, reason = manager.should_promote(
            new_version,
            current_version,
            metric_name="custom_score",
            improvement_threshold=0.05,
        )
        assert should_promote is True

    def test_auto_version_first_version(self, tmp_path):
        """Test auto-versioning when no versions exist."""
        manager = ModelVersionManager(storage_path=tmp_path)
        new_version = manager.auto_version()
        assert str(new_version) == "1.0.0"

    def test_auto_version_patch(self, tmp_path):
        """Test auto-versioning with patch bump."""
        manager = ModelVersionManager(storage_path=tmp_path)
        current = ModelVersion(1, 2, 3)
        manager.register_version(current)

        new_version = manager.auto_version(change_type="patch")
        assert str(new_version) == "1.2.4"

    def test_auto_version_minor(self, tmp_path):
        """Test auto-versioning with minor bump."""
        manager = ModelVersionManager(storage_path=tmp_path)
        current = ModelVersion(1, 2, 3)
        manager.register_version(current)

        new_version = manager.auto_version(change_type="minor")
        assert str(new_version) == "1.3.0"

    def test_auto_version_major(self, tmp_path):
        """Test auto-versioning with major bump."""
        manager = ModelVersionManager(storage_path=tmp_path)
        current = ModelVersion(1, 2, 3)
        manager.register_version(current)

        new_version = manager.auto_version(change_type="major")
        assert str(new_version) == "2.0.0"

    def test_auto_version_with_specific_base(self, tmp_path):
        """Test auto-versioning from specific base version."""
        manager = ModelVersionManager(storage_path=tmp_path)
        base_version = ModelVersion(3, 0, 0)

        new_version = manager.auto_version(
            current_version=base_version, change_type="minor"
        )
        assert str(new_version) == "3.1.0"

    def test_get_version_history(self, tmp_path):
        """Test getting version history."""
        manager = ModelVersionManager(storage_path=tmp_path)
        v1 = ModelVersion(1, 0, 0)
        v2 = ModelVersion(2, 0, 0)
        v3 = ModelVersion(3, 0, 0)

        manager.register_version(v1)
        manager.register_version(v2)
        manager.register_version(v3)

        history = manager.get_version_history()
        assert len(history) == 3
        assert history[0] == v3  # Newest first

    def test_get_version_history_with_limit(self, tmp_path):
        """Test getting limited version history."""
        manager = ModelVersionManager(storage_path=tmp_path)
        for i in range(5):
            manager.register_version(ModelVersion(i, 0, 0))

        history = manager.get_version_history(limit=2)
        assert len(history) == 2

    def test_get_version_history_by_stage(self, tmp_path):
        """Test filtering version history by stage."""
        manager = ModelVersionManager(storage_path=tmp_path)

        prod_metadata = ModelMetadata(
            model_id="m1", version_string="1.0.0", stage=ModelStage.PRODUCTION
        )
        dev_metadata = ModelMetadata(
            model_id="m2", version_string="2.0.0", stage=ModelStage.DEVELOPMENT
        )

        v1 = ModelVersion(1, 0, 0, metadata=prod_metadata)
        v2 = ModelVersion(2, 0, 0, metadata=dev_metadata)

        manager.register_version(v1)
        manager.register_version(v2)

        prod_history = manager.get_version_history(stage=ModelStage.PRODUCTION)
        assert len(prod_history) == 1
        assert prod_history[0] == v1

    def test_compare_versions(self, tmp_path):
        """Test comparing two versions."""
        manager = ModelVersionManager(storage_path=tmp_path)

        metadata1 = ModelMetadata(
            model_id="m1",
            version_string="1.0.0",
            metrics=ModelMetrics(accuracy=0.85, precision=0.80),
        )
        metadata2 = ModelMetadata(
            model_id="m2",
            version_string="2.0.0",
            metrics=ModelMetrics(accuracy=0.90, precision=0.88),
        )

        v1 = ModelVersion(1, 0, 0, metadata=metadata1)
        v2 = ModelVersion(2, 0, 0, metadata=metadata2)

        comparison = manager.compare_versions(v1, v2)

        assert comparison["version1"] == "1.0.0"
        assert comparison["version2"] == "2.0.0"
        assert comparison["newer"] is False
        assert comparison["metrics"]["accuracy"]["version1"] == 0.85
        assert comparison["metrics"]["accuracy"]["version2"] == 0.90
        assert comparison["metrics"]["accuracy"]["diff"] == pytest.approx(
            -0.05, abs=1e-9
        )

    def test_compare_versions_custom_metrics(self, tmp_path):
        """Test comparing versions with custom metrics."""
        manager = ModelVersionManager(storage_path=tmp_path)

        metadata1 = ModelMetadata(
            model_id="m1", version_string="1.0.0", metrics=ModelMetrics(accuracy=0.85)
        )
        metadata2 = ModelMetadata(
            model_id="m2", version_string="2.0.0", metrics=ModelMetrics(accuracy=0.90)
        )

        v1 = ModelVersion(1, 0, 0, metadata=metadata1)
        v2 = ModelVersion(2, 0, 0, metadata=metadata2)

        comparison = manager.compare_versions(v1, v2, metrics=["accuracy", "f1_score"])
        assert "accuracy" in comparison["metrics"]
        assert "f1_score" in comparison["metrics"]

    def test_archive_old_versions(self, tmp_path):
        """Test archiving old versions."""
        manager = ModelVersionManager(storage_path=tmp_path)

        for i in range(10):
            metadata = ModelMetadata(
                model_id=f"m{i}",
                version_string=f"{i}.0.0",
                stage=ModelStage.DEVELOPMENT,
            )
            version = ModelVersion(i, 0, 0, metadata=metadata)
            manager.register_version(version)

        archived_count = manager.archive_old_versions(keep_latest=5)
        assert archived_count == 5

        # Check that old versions are archived
        for version in manager.versions[5:]:
            assert version.metadata.stage == ModelStage.ARCHIVED

    def test_archive_keeps_production_versions(self, tmp_path):
        """Test that production versions are kept even when archiving."""
        manager = ModelVersionManager(storage_path=tmp_path)

        # Add old production version
        prod_metadata = ModelMetadata(
            model_id="prod", version_string="1.0.0", stage=ModelStage.PRODUCTION
        )
        prod_version = ModelVersion(1, 0, 0, metadata=prod_metadata)
        manager.register_version(prod_version)

        # Add newer dev versions
        for i in range(10):
            dev_metadata = ModelMetadata(
                model_id=f"dev{i}",
                version_string=f"{i + 2}.0.0",
                stage=ModelStage.DEVELOPMENT,
            )
            version = ModelVersion(i + 2, 0, 0, metadata=dev_metadata)
            manager.register_version(version)

        manager.archive_old_versions(keep_latest=5, keep_production=True)

        # Production version should not be archived
        assert prod_version.metadata.stage == ModelStage.PRODUCTION

    def test_save_and_load_versions(self, tmp_path):
        """Test saving and loading version history."""
        manager1 = ModelVersionManager(storage_path=tmp_path)
        version = ModelVersion(1, 2, 3)
        manager1.register_version(version)

        # Create new manager with same storage path
        manager2 = ModelVersionManager(storage_path=tmp_path)
        assert len(manager2.versions) == 1
        assert str(manager2.versions[0]) == "1.2.3"

    def test_load_versions_with_metadata(self, tmp_path):
        """Test loading versions with metadata."""
        manager1 = ModelVersionManager(storage_path=tmp_path)

        metadata = ModelMetadata(
            model_id="test_model",
            version_string="1.0.0",
            metrics=ModelMetrics(accuracy=0.95),
        )
        version = ModelVersion(1, 0, 0, metadata=metadata)
        manager1.register_version(version)

        # Reload
        manager2 = ModelVersionManager(storage_path=tmp_path)
        loaded_version = manager2.versions[0]
        assert loaded_version.metadata is not None
        assert loaded_version.metadata.model_id == "test_model"

    def test_load_versions_file_not_exists(self, tmp_path):
        """Test loading when versions file doesn't exist."""
        manager = ModelVersionManager(storage_path=tmp_path)
        assert manager.versions == []

    @patch("builtins.open", side_effect=IOError("Read error"))
    def test_load_versions_error_handling(self, mock_open, tmp_path):
        """Test error handling when loading versions fails."""
        # Create a versions file first
        versions_file = tmp_path / "versions.json"
        versions_file.write_text('{"versions": []}')

        # Now try to load with error
        manager = ModelVersionManager(storage_path=tmp_path)
        # Should handle error gracefully
        assert manager.versions == []


class TestCreateModelVersionHelper:
    """Tests for create_model_version helper function."""

    def test_create_model_version_basic(self):
        """Test creating model version with basic parameters."""
        version = create_model_version(
            version_string="1.0.0",
            metrics={"accuracy": 0.95, "f1_score": 0.90},
            model_path="/path/to/model.pkl",
        )
        assert str(version) == "1.0.0"
        assert version.metadata is not None
        assert version.metadata.metrics.accuracy == 0.95

    def test_create_model_version_with_framework(self):
        """Test creating version with specific framework."""
        version = create_model_version(
            version_string="2.0.0",
            metrics={"accuracy": 0.92},
            model_path="/path/to/model.pth",
            framework="pytorch",
        )
        assert version.metadata.framework == ModelFramework.PYTORCH

    def test_create_model_version_with_algorithm(self):
        """Test creating version with algorithm."""
        version = create_model_version(
            version_string="1.0.0",
            metrics={"accuracy": 0.88},
            model_path="/path/to/model.pkl",
            algorithm="RandomForest",
        )
        assert version.metadata.algorithm == "RandomForest"

    def test_create_model_version_with_hyperparameters(self):
        """Test creating version with hyperparameters."""
        hyperparams = {"n_estimators": 100, "max_depth": 10}
        version = create_model_version(
            version_string="1.0.0",
            metrics={"accuracy": 0.90},
            model_path="/path/to/model.pkl",
            hyperparameters=hyperparams,
        )
        assert version.metadata.hyperparameters["n_estimators"] == 100

    def test_create_model_version_with_stage(self):
        """Test creating version with specific stage."""
        version = create_model_version(
            version_string="1.0.0",
            metrics={"accuracy": 0.95},
            model_path="/path/to/model.pkl",
            stage="Production",
        )
        assert version.metadata.stage == ModelStage.PRODUCTION

    def test_create_model_version_with_custom_model_id(self):
        """Test creating version with custom model ID."""
        version = create_model_version(
            version_string="1.0.0",
            metrics={"accuracy": 0.95},
            model_path="/path/to/model.pkl",
            model_id="custom_model_123",
        )
        assert version.metadata.model_id == "custom_model_123"

    def test_create_model_version_default_model_id(self):
        """Test that default model ID is generated."""
        version = create_model_version(
            version_string="1.0.0",
            metrics={"accuracy": 0.95},
            model_path="/path/to/model.pkl",
        )
        assert "model_1.0.0" in version.metadata.model_id

    def test_create_model_version_with_additional_kwargs(self):
        """Test creating version with additional metadata fields."""
        version = create_model_version(
            version_string="1.0.0",
            metrics={"accuracy": 0.95},
            model_path="/path/to/model.pkl",
            description="Test model",
            tags={"env": "test"},
            mlflow_run_id="run_123",
        )
        assert version.metadata.description == "Test model"
        assert version.metadata.tags["env"] == "test"
        assert version.metadata.mlflow_run_id == "run_123"

    def test_create_model_version_v_prefix(self):
        """Test creating version with 'v' prefix in version string."""
        version = create_model_version(
            version_string="v1.0.0",
            metrics={"accuracy": 0.95},
            model_path="/path/to/model.pkl",
        )
        assert str(version) == "1.0.0"
        assert version.metadata.version_string == "v1.0.0"
