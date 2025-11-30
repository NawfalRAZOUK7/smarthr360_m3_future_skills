"""
Comprehensive tests for ml/mlflow_config.py module.

Tests cover:
- MLflowConfig initialization and configuration
- Tracking URI, artifact location, and backend store setup
- Experiment creation and management
- Run tracking and context managers
- Model registration and versioning
- Model stage transitions
- Run searching and filtering
- Cleanup operations
- Global instance management
"""

import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

from ml.mlflow_config import (
    MLflowConfig,
    get_mlflow_config,
    get_mlflow_client,
    initialize_mlflow,
)


class TestMLflowConfigInitialization:
    """Tests for MLflowConfig initialization."""

    @patch("ml.mlflow_config.settings")
    @patch.dict("os.environ", {}, clear=True)
    def test_init_default_configuration(self, mock_settings):
        """Test initialization with default configuration."""
        mock_settings.BASE_DIR = Path("/tmp/test")
        mock_settings.MLFLOW_TRACKING_URI = None
        mock_settings.MLFLOW_ARTIFACT_LOCATION = None
        mock_settings.MLFLOW_BACKEND_STORE_URI = None

        config = MLflowConfig()

        assert config.tracking_uri is not None
        assert config.artifact_location is not None
        assert config.backend_store_uri is not None
        assert config.client is None
        assert config._initialized is False

    @patch("ml.mlflow_config.settings")
    @patch.dict("os.environ", {"MLFLOW_TRACKING_URI": "http://mlflow-server:5000"})
    def test_tracking_uri_from_environment(self, mock_settings):
        """Test tracking URI is read from environment variable."""
        config = MLflowConfig()
        assert config.tracking_uri == "http://mlflow-server:5000"

    @patch("ml.mlflow_config.settings")
    @patch.dict("os.environ", {}, clear=True)
    def test_tracking_uri_from_settings(self, mock_settings):
        """Test tracking URI is read from Django settings."""
        mock_settings.MLFLOW_TRACKING_URI = "http://localhost:5000"
        mock_settings.BASE_DIR = Path("/tmp/test")

        config = MLflowConfig()
        assert config.tracking_uri == "http://localhost:5000"

    @patch("ml.mlflow_config.settings")
    @patch.dict("os.environ", {}, clear=True)
    def test_tracking_uri_default_file_based(self, mock_settings):
        """Test default file-based tracking URI is created."""
        mock_settings.BASE_DIR = Path("/tmp/test")
        mock_settings.MLFLOW_TRACKING_URI = None

        config = MLflowConfig()
        assert "file://" in config.tracking_uri
        assert "mlruns" in config.tracking_uri

    @patch("ml.mlflow_config.settings")
    @patch.dict("os.environ", {"MLFLOW_ARTIFACT_LOCATION": "/custom/artifacts"})
    def test_artifact_location_from_environment(self, mock_settings):
        """Test artifact location from environment."""
        config = MLflowConfig()
        assert config.artifact_location == "/custom/artifacts"

    @patch("ml.mlflow_config.settings")
    @patch.dict("os.environ", {}, clear=True)
    def test_artifact_location_from_settings(self, mock_settings):
        """Test artifact location from Django settings."""
        mock_settings.MLFLOW_ARTIFACT_LOCATION = "/settings/artifacts"
        mock_settings.BASE_DIR = Path("/tmp/test")

        config = MLflowConfig()
        assert config.artifact_location == "/settings/artifacts"

    @patch("ml.mlflow_config.settings")
    @patch.dict(
        "os.environ", {"MLFLOW_BACKEND_STORE_URI": "postgresql://db:5432/mlflow"}
    )
    def test_backend_store_uri_from_environment(self, mock_settings):
        """Test backend store URI from environment."""
        config = MLflowConfig()
        assert config.backend_store_uri == "postgresql://db:5432/mlflow"

    @patch("ml.mlflow_config.settings")
    @patch.dict("os.environ", {}, clear=True)
    def test_backend_store_uri_default_sqlite(self, mock_settings):
        """Test default SQLite backend store URI."""
        mock_settings.BASE_DIR = Path("/tmp/test")
        mock_settings.MLFLOW_BACKEND_STORE_URI = None

        config = MLflowConfig()
        assert "sqlite:///" in config.backend_store_uri
        assert "mlflow.db" in config.backend_store_uri


class TestMLflowConfigSetup:
    """Tests for MLflowConfig setup method."""

    @patch("ml.mlflow_config.mlflow")
    @patch("ml.mlflow_config.MlflowClient")
    @patch("ml.mlflow_config.settings")
    def test_setup_initializes_mlflow(
        self, mock_settings, mock_client_class, mock_mlflow
    ):
        """Test that setup initializes MLflow correctly."""
        mock_settings.BASE_DIR = Path("/tmp/test")
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_experiment_by_name.return_value = Mock()

        config = MLflowConfig()
        config.setup()

        assert config._initialized is True
        assert config.client is not None
        mock_mlflow.set_tracking_uri.assert_called_once()
        mock_mlflow.set_experiment.assert_called_once()

    @patch("ml.mlflow_config.mlflow")
    @patch("ml.mlflow_config.MlflowClient")
    @patch("ml.mlflow_config.settings")
    def test_setup_idempotent(self, mock_settings, mock_client_class, mock_mlflow):
        """Test that setup can be called multiple times safely."""
        mock_settings.BASE_DIR = Path("/tmp/test")
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_experiment_by_name.return_value = Mock()

        config = MLflowConfig()
        config.setup()
        config.setup()  # Should not reinitialize

        # Should only be called once
        assert mock_mlflow.set_tracking_uri.call_count == 1

    @patch("ml.mlflow_config.mlflow")
    @patch("ml.mlflow_config.MlflowClient")
    @patch("ml.mlflow_config.settings")
    def test_setup_creates_default_experiments(
        self, mock_settings, mock_client_class, mock_mlflow
    ):
        """Test that setup creates default experiments."""
        mock_settings.BASE_DIR = Path("/tmp/test")
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_experiment_by_name.return_value = (
            None  # Experiments don't exist
        )
        mock_client.create_experiment.return_value = "exp_123"

        config = MLflowConfig()
        config.setup()

        # Should create 4 default experiments
        assert mock_client.create_experiment.call_count == 4

    @patch("ml.mlflow_config.mlflow")
    @patch("ml.mlflow_config.MlflowClient")
    @patch("ml.mlflow_config.settings")
    def test_setup_skips_existing_experiments(
        self, mock_settings, mock_client_class, mock_mlflow
    ):
        """Test that existing experiments are not recreated."""
        mock_settings.BASE_DIR = Path("/tmp/test")
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_experiment_by_name.return_value = Mock()  # Experiment exists

        config = MLflowConfig()
        config.setup()

        # Should not create any experiments
        mock_client.create_experiment.assert_not_called()

    @patch("ml.mlflow_config.mlflow")
    @patch("ml.mlflow_config.MlflowClient")
    @patch("ml.mlflow_config.settings")
    def test_setup_handles_initialization_error(
        self, mock_settings, mock_client_class, mock_mlflow
    ):
        """Test error handling during setup."""
        mock_settings.BASE_DIR = Path("/tmp/test")
        mock_mlflow.set_tracking_uri.side_effect = Exception("Connection failed")

        config = MLflowConfig()

        with pytest.raises(Exception, match="Connection failed"):
            config.setup()

        assert config._initialized is False


class TestMLflowConfigRunTracking:
    """Tests for run tracking functionality."""

    @patch("ml.mlflow_config.mlflow")
    @patch("ml.mlflow_config.MlflowClient")
    @patch("ml.mlflow_config.settings")
    def test_start_run_basic(self, mock_settings, mock_client_class, mock_mlflow):
        """Test starting a basic run."""
        mock_settings.BASE_DIR = Path("/tmp/test")
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_experiment_by_name.return_value = Mock()

        mock_run = Mock()
        mock_mlflow.start_run.return_value.__enter__ = Mock(return_value=mock_run)
        mock_mlflow.start_run.return_value.__exit__ = Mock(return_value=False)

        config = MLflowConfig()
        config.setup()

        with config.start_run(run_name="test_run") as run:
            assert run == mock_run

        mock_mlflow.start_run.assert_called_once()

    @patch("ml.mlflow_config.mlflow")
    @patch("ml.mlflow_config.MlflowClient")
    @patch("ml.mlflow_config.settings")
    def test_start_run_with_tags(self, mock_settings, mock_client_class, mock_mlflow):
        """Test starting a run with custom tags."""
        mock_settings.BASE_DIR = Path("/tmp/test")
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_experiment_by_name.return_value = Mock()

        mock_run = Mock()
        mock_mlflow.start_run.return_value.__enter__ = Mock(return_value=mock_run)
        mock_mlflow.start_run.return_value.__exit__ = Mock(return_value=False)

        config = MLflowConfig()
        config.setup()

        tags = {"environment": "test", "version": "1.0"}
        with config.start_run(run_name="test_run", tags=tags):
            pass

        mock_mlflow.set_tags.assert_called_once_with(tags)

    @patch("ml.mlflow_config.mlflow")
    @patch("ml.mlflow_config.MlflowClient")
    @patch("ml.mlflow_config.settings")
    def test_start_run_with_experiment_name(
        self, mock_settings, mock_client_class, mock_mlflow
    ):
        """Test starting a run in specific experiment."""
        mock_settings.BASE_DIR = Path("/tmp/test")
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_experiment_by_name.return_value = Mock()

        mock_run = Mock()
        mock_mlflow.start_run.return_value.__enter__ = Mock(return_value=mock_run)
        mock_mlflow.start_run.return_value.__exit__ = Mock(return_value=False)

        config = MLflowConfig()
        config.setup()

        with config.start_run(experiment_name="custom-experiment"):
            pass

        # Should set experiment before starting run
        calls = mock_mlflow.set_experiment.call_args_list
        assert any(call[0][0] == "custom-experiment" for call in calls)

    @patch("ml.mlflow_config.mlflow")
    @patch("ml.mlflow_config.MlflowClient")
    @patch("ml.mlflow_config.settings")
    def test_start_run_nested(self, mock_settings, mock_client_class, mock_mlflow):
        """Test starting a nested run."""
        mock_settings.BASE_DIR = Path("/tmp/test")
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_experiment_by_name.return_value = Mock()

        mock_run = Mock()
        mock_mlflow.start_run.return_value.__enter__ = Mock(return_value=mock_run)
        mock_mlflow.start_run.return_value.__exit__ = Mock(return_value=False)

        config = MLflowConfig()
        config.setup()

        with config.start_run(nested=True):
            pass

        mock_mlflow.start_run.assert_called_with(run_name=None, nested=True)

    @patch("ml.mlflow_config.mlflow")
    @patch("ml.mlflow_config.MlflowClient")
    @patch("ml.mlflow_config.settings")
    def test_start_run_auto_initializes(
        self, mock_settings, mock_client_class, mock_mlflow
    ):
        """Test that start_run auto-initializes if not setup."""
        mock_settings.BASE_DIR = Path("/tmp/test")
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_experiment_by_name.return_value = Mock()

        mock_run = Mock()
        mock_mlflow.start_run.return_value.__enter__ = Mock(return_value=mock_run)
        mock_mlflow.start_run.return_value.__exit__ = Mock(return_value=False)

        config = MLflowConfig()
        # Don't call setup()

        with config.start_run():
            pass

        assert config._initialized is True

    @patch("ml.mlflow_config.mlflow")
    @patch("ml.mlflow_config.MlflowClient")
    @patch("ml.mlflow_config.settings")
    def test_start_run_logs_system_tags(
        self, mock_settings, mock_client_class, mock_mlflow
    ):
        """Test that system tags are logged automatically."""
        mock_settings.BASE_DIR = Path("/tmp/test")
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_experiment_by_name.return_value = Mock()

        mock_run = Mock()
        mock_mlflow.start_run.return_value.__enter__ = Mock(return_value=mock_run)
        mock_mlflow.start_run.return_value.__exit__ = Mock(return_value=False)

        config = MLflowConfig()
        config.setup()

        with config.start_run():
            pass

        # Check that system tags were set
        set_tag_calls = mock_mlflow.set_tag.call_args_list
        tag_names = [call[0][0] for call in set_tag_calls]
        assert "mlflow.source.name" in tag_names
        assert "mlflow.user" in tag_names

    @patch("ml.mlflow_config.mlflow")
    @patch("ml.mlflow_config.MlflowClient")
    @patch("ml.mlflow_config.settings")
    def test_start_run_handles_error(
        self, mock_settings, mock_client_class, mock_mlflow
    ):
        """Test error handling in run context."""
        mock_settings.BASE_DIR = Path("/tmp/test")
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_experiment_by_name.return_value = Mock()

        # Simulate error during run
        mock_mlflow.start_run.return_value.__enter__ = Mock(
            side_effect=Exception("Run error")
        )

        config = MLflowConfig()
        config.setup()

        with pytest.raises(Exception, match="Run error"):
            with config.start_run():
                pass


class TestMLflowConfigLogging:
    """Tests for logging methods."""

    @patch("ml.mlflow_config.mlflow")
    def test_log_model_metrics(self, mock_mlflow):
        """Test logging multiple metrics."""
        config = MLflowConfig()
        metrics = {"accuracy": 0.95, "f1_score": 0.90, "precision": 0.92}

        config.log_model_metrics(metrics)

        assert mock_mlflow.log_metric.call_count == 3

    @patch("ml.mlflow_config.mlflow")
    def test_log_model_metrics_with_step(self, mock_mlflow):
        """Test logging metrics with step."""
        config = MLflowConfig()
        metrics = {"loss": 0.25}

        config.log_model_metrics(metrics, step=10)

        mock_mlflow.log_metric.assert_called_once_with("loss", 0.25, step=10)

    @patch("ml.mlflow_config.mlflow")
    def test_log_model_params(self, mock_mlflow):
        """Test logging multiple parameters."""
        config = MLflowConfig()
        params = {"n_estimators": 100, "max_depth": 10, "learning_rate": 0.01}

        config.log_model_params(params)

        mock_mlflow.log_params.assert_called_once_with(params)

    @patch("ml.mlflow_config.mlflow")
    def test_log_artifact_directory(self, mock_mlflow):
        """Test logging artifact directory."""
        config = MLflowConfig()

        config.log_artifact_directory("/path/to/artifacts")

        mock_mlflow.log_artifacts.assert_called_once_with(
            "/path/to/artifacts", artifact_path=None
        )

    @patch("ml.mlflow_config.mlflow")
    def test_log_artifact_directory_with_path(self, mock_mlflow):
        """Test logging artifact directory with custom path."""
        config = MLflowConfig()

        config.log_artifact_directory("/path/to/artifacts", artifact_path="models")

        mock_mlflow.log_artifacts.assert_called_once_with(
            "/path/to/artifacts", artifact_path="models"
        )


class TestMLflowConfigModelRegistry:
    """Tests for model registry operations."""

    @patch("ml.mlflow_config.mlflow")
    @patch("ml.mlflow_config.MlflowClient")
    @patch("ml.mlflow_config.settings")
    def test_register_model_basic(self, mock_settings, mock_client_class, mock_mlflow):
        """Test basic model registration."""
        mock_settings.BASE_DIR = Path("/tmp/test")
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_experiment_by_name.return_value = Mock()

        mock_version = Mock()
        mock_version.version = "1"
        mock_mlflow.register_model.return_value = mock_version

        config = MLflowConfig()
        config.setup()

        result = config.register_model("runs:/run123/model")

        assert result == mock_version
        mock_mlflow.register_model.assert_called_once()

    @patch("ml.mlflow_config.mlflow")
    @patch("ml.mlflow_config.MlflowClient")
    @patch("ml.mlflow_config.settings")
    def test_register_model_with_custom_name(
        self, mock_settings, mock_client_class, mock_mlflow
    ):
        """Test registering model with custom name."""
        mock_settings.BASE_DIR = Path("/tmp/test")
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_experiment_by_name.return_value = Mock()

        mock_version = Mock()
        mock_version.version = "1"
        mock_mlflow.register_model.return_value = mock_version

        config = MLflowConfig()
        config.setup()

        config.register_model("runs:/run123/model", model_name="custom-model")

        call_kwargs = mock_mlflow.register_model.call_args[1]
        assert call_kwargs["name"] == "custom-model"

    @patch("ml.mlflow_config.mlflow")
    @patch("ml.mlflow_config.MlflowClient")
    @patch("ml.mlflow_config.settings")
    def test_register_model_with_tags(
        self, mock_settings, mock_client_class, mock_mlflow
    ):
        """Test registering model with tags."""
        mock_settings.BASE_DIR = Path("/tmp/test")
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_experiment_by_name.return_value = Mock()

        mock_version = Mock()
        mock_version.version = "1"
        mock_mlflow.register_model.return_value = mock_version

        config = MLflowConfig()
        config.setup()

        tags = {"env": "production", "version": "1.0"}
        config.register_model("runs:/run123/model", tags=tags)

        call_kwargs = mock_mlflow.register_model.call_args[1]
        assert call_kwargs["tags"] == tags

    @patch("ml.mlflow_config.mlflow")
    @patch("ml.mlflow_config.MlflowClient")
    @patch("ml.mlflow_config.settings")
    def test_register_model_with_description(
        self, mock_settings, mock_client_class, mock_mlflow
    ):
        """Test registering model with description."""
        mock_settings.BASE_DIR = Path("/tmp/test")
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_experiment_by_name.return_value = Mock()

        mock_version = Mock()
        mock_version.version = "1"
        mock_mlflow.register_model.return_value = mock_version

        config = MLflowConfig()
        config.setup()

        config.register_model("runs:/run123/model", description="Production model v1")

        mock_client.update_model_version.assert_called_once()

    @patch("ml.mlflow_config.mlflow")
    @patch("ml.mlflow_config.MlflowClient")
    @patch("ml.mlflow_config.settings")
    def test_register_model_auto_initializes(
        self, mock_settings, mock_client_class, mock_mlflow
    ):
        """Test that register_model auto-initializes."""
        mock_settings.BASE_DIR = Path("/tmp/test")
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_experiment_by_name.return_value = Mock()

        mock_version = Mock()
        mock_mlflow.register_model.return_value = mock_version

        config = MLflowConfig()
        # Don't call setup()

        config.register_model("runs:/run123/model")

        assert config._initialized is True

    @patch("ml.mlflow_config.mlflow")
    @patch("ml.mlflow_config.MlflowClient")
    @patch("ml.mlflow_config.settings")
    def test_register_model_handles_error(
        self, mock_settings, mock_client_class, mock_mlflow
    ):
        """Test error handling during model registration."""
        mock_settings.BASE_DIR = Path("/tmp/test")
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_experiment_by_name.return_value = Mock()

        mock_mlflow.register_model.side_effect = Exception("Registration failed")

        config = MLflowConfig()
        config.setup()

        with pytest.raises(Exception, match="Registration failed"):
            config.register_model("runs:/run123/model")

    @patch("ml.mlflow_config.MlflowClient")
    @patch("ml.mlflow_config.settings")
    def test_transition_model_stage(self, mock_settings, mock_client_class):
        """Test transitioning model stage."""
        mock_settings.BASE_DIR = Path("/tmp/test")
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_experiment_by_name.return_value = Mock()

        config = MLflowConfig()
        config.setup()

        config.transition_model_stage("my-model", "1", "Production")

        mock_client.transition_model_version_stage.assert_called_once_with(
            name="my-model",
            version="1",
            stage="Production",
            archive_existing_versions=True,
        )

    @patch("ml.mlflow_config.MlflowClient")
    @patch("ml.mlflow_config.settings")
    def test_transition_model_stage_no_archive(self, mock_settings, mock_client_class):
        """Test transitioning model stage without archiving."""
        mock_settings.BASE_DIR = Path("/tmp/test")
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_experiment_by_name.return_value = Mock()

        config = MLflowConfig()
        config.setup()

        config.transition_model_stage(
            "my-model", "1", "Staging", archive_existing=False
        )

        call_kwargs = mock_client.transition_model_version_stage.call_args[1]
        assert call_kwargs["archive_existing_versions"] is False

    @patch("ml.mlflow_config.MlflowClient")
    @patch("ml.mlflow_config.settings")
    def test_transition_model_stage_handles_error(
        self, mock_settings, mock_client_class
    ):
        """Test error handling during stage transition."""
        mock_settings.BASE_DIR = Path("/tmp/test")
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_experiment_by_name.return_value = Mock()
        mock_client.transition_model_version_stage.side_effect = Exception(
            "Transition failed"
        )

        config = MLflowConfig()
        config.setup()

        with pytest.raises(Exception, match="Transition failed"):
            config.transition_model_stage("my-model", "1", "Production")


class TestMLflowConfigModelRetrieval:
    """Tests for model version retrieval."""

    @patch("ml.mlflow_config.MlflowClient")
    @patch("ml.mlflow_config.settings")
    def test_get_latest_model_version(self, mock_settings, mock_client_class):
        """Test getting latest model version."""
        mock_settings.BASE_DIR = Path("/tmp/test")
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_experiment_by_name.return_value = Mock()

        mock_v1 = Mock()
        mock_v1.version = "1"
        mock_v2 = Mock()
        mock_v2.version = "2"
        mock_client.search_model_versions.return_value = [mock_v1, mock_v2]

        config = MLflowConfig()
        config.setup()

        result = config.get_latest_model_version()

        assert result == mock_v2

    @patch("ml.mlflow_config.MlflowClient")
    @patch("ml.mlflow_config.settings")
    def test_get_latest_model_version_with_stage_filter(
        self, mock_settings, mock_client_class
    ):
        """Test getting latest model version filtered by stage."""
        mock_settings.BASE_DIR = Path("/tmp/test")
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_experiment_by_name.return_value = Mock()

        mock_v1 = Mock()
        mock_v1.version = "1"
        mock_v1.current_stage = "Production"
        mock_v2 = Mock()
        mock_v2.version = "2"
        mock_v2.current_stage = "Staging"
        mock_client.search_model_versions.return_value = [mock_v1, mock_v2]

        config = MLflowConfig()
        config.setup()

        result = config.get_latest_model_version(stage="Production")

        assert result == mock_v1

    @patch("ml.mlflow_config.MlflowClient")
    @patch("ml.mlflow_config.settings")
    def test_get_latest_model_version_no_versions(
        self, mock_settings, mock_client_class
    ):
        """Test getting latest version when none exist."""
        mock_settings.BASE_DIR = Path("/tmp/test")
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_experiment_by_name.return_value = Mock()
        mock_client.search_model_versions.return_value = []

        config = MLflowConfig()
        config.setup()

        result = config.get_latest_model_version()

        assert result is None

    @patch("ml.mlflow_config.MlflowClient")
    @patch("ml.mlflow_config.settings")
    def test_get_latest_model_version_handles_error(
        self, mock_settings, mock_client_class
    ):
        """Test error handling when retrieving model version."""
        mock_settings.BASE_DIR = Path("/tmp/test")
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_experiment_by_name.return_value = Mock()
        mock_client.search_model_versions.side_effect = Exception("Search failed")

        config = MLflowConfig()
        config.setup()

        result = config.get_latest_model_version()

        assert result is None

    @patch("ml.mlflow_config.MlflowClient")
    @patch("ml.mlflow_config.settings")
    def test_get_production_model_uri(self, mock_settings, mock_client_class):
        """Test getting production model URI."""
        mock_settings.BASE_DIR = Path("/tmp/test")
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_experiment_by_name.return_value = Mock()

        mock_version = Mock()
        mock_version.version = "3"
        mock_version.current_stage = "Production"
        mock_client.search_model_versions.return_value = [mock_version]

        config = MLflowConfig()
        config.setup()

        uri = config.get_production_model_uri()

        assert "models:/future-skills-model/3" in uri

    @patch("ml.mlflow_config.MlflowClient")
    @patch("ml.mlflow_config.settings")
    def test_get_production_model_uri_no_production(
        self, mock_settings, mock_client_class
    ):
        """Test getting production URI when no production model exists."""
        mock_settings.BASE_DIR = Path("/tmp/test")
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_experiment_by_name.return_value = Mock()
        mock_client.search_model_versions.return_value = []

        config = MLflowConfig()
        config.setup()

        uri = config.get_production_model_uri()

        assert uri is None


class TestMLflowConfigRunSearch:
    """Tests for run search functionality."""

    @patch("ml.mlflow_config.MlflowClient")
    @patch("ml.mlflow_config.settings")
    def test_search_runs_basic(self, mock_settings, mock_client_class):
        """Test basic run search."""
        mock_settings.BASE_DIR = Path("/tmp/test")
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_experiment = Mock()
        mock_experiment.experiment_id = "exp123"
        mock_client.get_experiment_by_name.return_value = mock_experiment

        mock_runs = [Mock(), Mock()]
        mock_client.search_runs.return_value = mock_runs

        config = MLflowConfig()
        config.setup()

        results = config.search_runs()

        assert len(results) == 2
        mock_client.search_runs.assert_called_once()

    @patch("ml.mlflow_config.MlflowClient")
    @patch("ml.mlflow_config.settings")
    def test_search_runs_with_filter(self, mock_settings, mock_client_class):
        """Test searching runs with filter."""
        mock_settings.BASE_DIR = Path("/tmp/test")
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_experiment = Mock()
        mock_experiment.experiment_id = "exp123"
        mock_client.get_experiment_by_name.return_value = mock_experiment
        mock_client.search_runs.return_value = []

        config = MLflowConfig()
        config.setup()

        config.search_runs(filter_string="metrics.accuracy > 0.9")

        call_kwargs = mock_client.search_runs.call_args[1]
        assert call_kwargs["filter_string"] == "metrics.accuracy > 0.9"

    @patch("ml.mlflow_config.MlflowClient")
    @patch("ml.mlflow_config.settings")
    def test_search_runs_with_max_results(self, mock_settings, mock_client_class):
        """Test searching runs with max results limit."""
        mock_settings.BASE_DIR = Path("/tmp/test")
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_experiment = Mock()
        mock_experiment.experiment_id = "exp123"
        mock_client.get_experiment_by_name.return_value = mock_experiment
        mock_client.search_runs.return_value = []

        config = MLflowConfig()
        config.setup()

        config.search_runs(max_results=50)

        call_kwargs = mock_client.search_runs.call_args[1]
        assert call_kwargs["max_results"] == 50

    @patch("ml.mlflow_config.MlflowClient")
    @patch("ml.mlflow_config.settings")
    def test_search_runs_with_order_by(self, mock_settings, mock_client_class):
        """Test searching runs with custom ordering."""
        mock_settings.BASE_DIR = Path("/tmp/test")
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_experiment = Mock()
        mock_experiment.experiment_id = "exp123"
        mock_client.get_experiment_by_name.return_value = mock_experiment
        mock_client.search_runs.return_value = []

        config = MLflowConfig()
        config.setup()

        config.search_runs(order_by=["metrics.accuracy DESC"])

        call_kwargs = mock_client.search_runs.call_args[1]
        assert call_kwargs["order_by"] == ["metrics.accuracy DESC"]

    @patch("ml.mlflow_config.MlflowClient")
    @patch("ml.mlflow_config.settings")
    def test_search_runs_experiment_not_found(self, mock_settings, mock_client_class):
        """Test searching runs when experiment doesn't exist."""
        mock_settings.BASE_DIR = Path("/tmp/test")
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_experiment_by_name.return_value = None

        config = MLflowConfig()
        config.setup()

        results = config.search_runs(experiment_name="nonexistent")

        assert results == []

    @patch("ml.mlflow_config.MlflowClient")
    @patch("ml.mlflow_config.settings")
    def test_search_runs_handles_error(self, mock_settings, mock_client_class):
        """Test error handling during run search."""
        mock_settings.BASE_DIR = Path("/tmp/test")
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_experiment = Mock()
        mock_experiment.experiment_id = "exp123"
        mock_client.get_experiment_by_name.return_value = mock_experiment
        mock_client.search_runs.side_effect = Exception("Search failed")

        config = MLflowConfig()
        config.setup()

        results = config.search_runs()

        assert results == []

    @patch("ml.mlflow_config.MlflowClient")
    @patch("ml.mlflow_config.settings")
    def test_get_best_run(self, mock_settings, mock_client_class):
        """Test getting best run by metric."""
        mock_settings.BASE_DIR = Path("/tmp/test")
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_experiment = Mock()
        mock_experiment.experiment_id = "exp123"
        mock_client.get_experiment_by_name.return_value = mock_experiment

        mock_best_run = Mock()
        mock_client.search_runs.return_value = [mock_best_run]

        config = MLflowConfig()
        config.setup()

        result = config.get_best_run(metric_name="accuracy")

        assert result == mock_best_run
        call_kwargs = mock_client.search_runs.call_args[1]
        assert "accuracy DESC" in call_kwargs["order_by"][0]

    @patch("ml.mlflow_config.MlflowClient")
    @patch("ml.mlflow_config.settings")
    def test_get_best_run_ascending(self, mock_settings, mock_client_class):
        """Test getting best run with ascending order (loss metric)."""
        mock_settings.BASE_DIR = Path("/tmp/test")
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_experiment = Mock()
        mock_experiment.experiment_id = "exp123"
        mock_client.get_experiment_by_name.return_value = mock_experiment

        mock_best_run = Mock()
        mock_client.search_runs.return_value = [mock_best_run]

        config = MLflowConfig()
        config.setup()

        result = config.get_best_run(metric_name="loss", ascending=True)

        call_kwargs = mock_client.search_runs.call_args[1]
        assert "loss ASC" in call_kwargs["order_by"][0]

    @patch("ml.mlflow_config.MlflowClient")
    @patch("ml.mlflow_config.settings")
    def test_get_best_run_no_runs(self, mock_settings, mock_client_class):
        """Test getting best run when no runs exist."""
        mock_settings.BASE_DIR = Path("/tmp/test")
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_experiment = Mock()
        mock_experiment.experiment_id = "exp123"
        mock_client.get_experiment_by_name.return_value = mock_experiment
        mock_client.search_runs.return_value = []

        config = MLflowConfig()
        config.setup()

        result = config.get_best_run()

        assert result is None


class TestMLflowConfigCleanup:
    """Tests for cleanup operations."""

    @patch("ml.mlflow_config.MlflowClient")
    @patch("ml.mlflow_config.settings")
    @patch("ml.mlflow_config.datetime")
    def test_cleanup_old_runs_dry_run(
        self, mock_datetime, mock_settings, mock_client_class
    ):
        """Test cleanup in dry-run mode."""
        mock_settings.BASE_DIR = Path("/tmp/test")
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Mock datetime for cutoff calculation
        now = datetime(2024, 1, 15, 10, 0)
        mock_datetime.now.return_value = now

        mock_experiment = Mock()
        mock_experiment.experiment_id = "exp123"
        mock_client.get_experiment_by_name.return_value = mock_experiment

        mock_run = Mock()
        mock_run.info.run_id = "run123"
        mock_client.search_runs.return_value = [mock_run]

        config = MLflowConfig()
        config.setup()

        count = config.cleanup_old_runs(
            "test-experiment", days_to_keep=90, dry_run=True
        )

        assert count == 1
        mock_client.delete_run.assert_not_called()

    @patch("ml.mlflow_config.MlflowClient")
    @patch("ml.mlflow_config.settings")
    @patch("ml.mlflow_config.datetime")
    def test_cleanup_old_runs_delete(
        self, mock_datetime, mock_settings, mock_client_class
    ):
        """Test cleanup with actual deletion."""
        mock_settings.BASE_DIR = Path("/tmp/test")
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        now = datetime(2024, 1, 15, 10, 0)
        mock_datetime.now.return_value = now

        mock_experiment = Mock()
        mock_experiment.experiment_id = "exp123"
        mock_client.get_experiment_by_name.return_value = mock_experiment

        mock_run = Mock()
        mock_run.info.run_id = "run123"
        mock_client.search_runs.return_value = [mock_run]

        config = MLflowConfig()
        config.setup()

        count = config.cleanup_old_runs(
            "test-experiment", days_to_keep=30, dry_run=False
        )

        assert count == 1
        mock_client.delete_run.assert_called_once_with("run123")

    @patch("ml.mlflow_config.MlflowClient")
    @patch("ml.mlflow_config.settings")
    def test_cleanup_old_runs_experiment_not_found(
        self, mock_settings, mock_client_class
    ):
        """Test cleanup when experiment doesn't exist."""
        mock_settings.BASE_DIR = Path("/tmp/test")
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_experiment_by_name.return_value = None

        config = MLflowConfig()
        config.setup()

        count = config.cleanup_old_runs("nonexistent")

        assert count == 0

    @patch("ml.mlflow_config.MlflowClient")
    @patch("ml.mlflow_config.settings")
    def test_cleanup_old_runs_handles_error(self, mock_settings, mock_client_class):
        """Test error handling during cleanup."""
        mock_settings.BASE_DIR = Path("/tmp/test")
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_experiment = Mock()
        mock_client.get_experiment_by_name.return_value = mock_experiment
        mock_client.search_runs.side_effect = Exception("Search failed")

        config = MLflowConfig()
        config.setup()

        count = config.cleanup_old_runs("test-experiment")

        assert count == 0


class TestGlobalHelperFunctions:
    """Tests for global helper functions."""

    @patch("ml.mlflow_config.MLflowConfig")
    def test_get_mlflow_config_creates_instance(self, mock_config_class):
        """Test that get_mlflow_config creates instance."""
        mock_instance = Mock()
        mock_config_class.return_value = mock_instance

        # Reset global instance
        import ml.mlflow_config

        ml.mlflow_config._mlflow_config = None

        result = get_mlflow_config()

        assert result == mock_instance
        mock_instance.setup.assert_called_once()

    @patch("ml.mlflow_config.MLflowConfig")
    def test_get_mlflow_config_returns_existing(self, mock_config_class):
        """Test that get_mlflow_config returns existing instance."""
        mock_instance = Mock()

        # Set global instance
        import ml.mlflow_config

        ml.mlflow_config._mlflow_config = mock_instance

        result = get_mlflow_config()

        assert result == mock_instance
        # Should not create new instance
        mock_config_class.assert_not_called()

    @patch("ml.mlflow_config.get_mlflow_config")
    def test_get_mlflow_client(self, mock_get_config):
        """Test getting MLflow client."""
        mock_config = Mock()
        mock_client = Mock()
        mock_config.client = mock_client
        mock_get_config.return_value = mock_config

        result = get_mlflow_client()

        assert result == mock_client

    @patch("ml.mlflow_config.get_mlflow_config")
    def test_initialize_mlflow(self, mock_get_config):
        """Test initialize_mlflow helper."""
        mock_config = Mock()
        mock_get_config.return_value = mock_config

        initialize_mlflow()

        mock_get_config.assert_called_once()


class TestMLflowConfigConstants:
    """Tests for class constants."""

    def test_default_experiment_names(self):
        """Test that default experiment names are defined."""
        assert MLflowConfig.DEFAULT_EXPERIMENT == "future-skills-prediction"
        assert MLflowConfig.TRAINING_EXPERIMENT == "model-training"
        assert MLflowConfig.EVALUATION_EXPERIMENT == "model-evaluation"
        assert MLflowConfig.PRODUCTION_EXPERIMENT == "production-monitoring"

    def test_model_registry_names(self):
        """Test model registry constants."""
        assert MLflowConfig.MODEL_NAME == "future-skills-model"

    def test_artifact_paths(self):
        """Test artifact path constants."""
        assert MLflowConfig.ARTIFACTS_PATH == "mlruns"
        assert MLflowConfig.MODELS_PATH == "models"
