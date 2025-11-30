# ml/tests/conftest.py

"""
Pytest configuration and fixtures for ML tests.

Imports fixtures from the main tests/conftest.py to make them available
for ML-specific tests.
"""

import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock
import sys

import pytest

# Add parent directory to path to import from tests.conftest
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.conftest import (
    sample_skill,
    sample_job_role,
    sample_future_skill_prediction,
    regular_user,
    admin_user,
)


@pytest.fixture(scope="session", autouse=True)
def mlflow_test_environment():
    """
    Set up MLflow test environment for all ML tests.
    Creates necessary directories and sets environment variables.
    """
    # Create temporary MLflow directory and its parent
    test_base_dir = Path("/tmp/test")
    test_base_dir.mkdir(parents=True, exist_ok=True)

    mlflow_dir = test_base_dir / "mlruns"
    mlflow_dir.mkdir(parents=True, exist_ok=True)

    # Set MLflow environment variables for testing
    os.environ["MLFLOW_TRACKING_URI"] = f"file://{mlflow_dir}"
    os.environ["MLFLOW_ARTIFACT_LOCATION"] = str(mlflow_dir / "artifacts")

    yield mlflow_dir

    # Cleanup after all tests
    if test_base_dir.exists():
        shutil.rmtree(test_base_dir, ignore_errors=True)


@pytest.fixture
def mock_mlflow_run():
    """
    Create a properly configured Mock for MLflow run context manager.
    Supports 'with' statements and has proper attributes.
    """
    mock_run = MagicMock()
    mock_run.__enter__ = MagicMock(return_value=mock_run)
    mock_run.__exit__ = MagicMock(return_value=False)
    mock_run.info.run_id = "test-run-id-12345"
    return mock_run


@pytest.fixture
def mock_mlflow_config():
    """
    Create a properly configured Mock for MLflowConfig.
    """
    mock_config = MagicMock()
    mock_config.tracking_uri = "file:///tmp/test/mlruns"
    mock_config.experiment_name = "test-experiment"
    mock_config.artifact_location = "/tmp/test/mlruns/artifacts"

    # Set up start_run to return a context manager
    mock_run = MagicMock()
    mock_run.__enter__ = MagicMock(return_value=mock_run)
    mock_run.__exit__ = MagicMock(return_value=False)
    mock_run.info.run_id = "test-run-id-12345"

    mock_config.start_run.return_value = mock_run
    mock_config.setup.return_value = None

    return mock_config


@pytest.fixture(autouse=True)
def auto_mock_mlflow(monkeypatch, settings):
    """
    Automatically mock MLflow for all ML tests to avoid FileNotFoundError.
    This ensures tests don't fail due to missing MLflow infrastructure.
    Also ensures Django settings return proper values instead of MagicMocks.
    """
    # Ensure Django settings have proper values for MLflow
    test_base_dir = Path("/tmp/test")
    test_mlflow_dir = test_base_dir / "mlruns"

    # Set Django settings to actual values (not MagicMocks)
    settings.BASE_DIR = test_base_dir
    settings.MLFLOW_TRACKING_URI = f"file://{test_mlflow_dir}"
    settings.MLFLOW_ARTIFACT_LOCATION = str(test_mlflow_dir / "artifacts")

    mock_config = MagicMock()
    mock_config.tracking_uri = f"file://{test_mlflow_dir}"
    mock_config.experiment_name = "test-experiment"

    # Set up start_run to return a context manager
    mock_run = MagicMock()
    mock_run.__enter__ = MagicMock(return_value=mock_run)
    mock_run.__exit__ = MagicMock(return_value=False)
    mock_run.info.run_id = "test-run-id-12345"

    mock_config.start_run.return_value = mock_run
    mock_config.setup.return_value = None

    # Patch get_mlflow_config to return our mock
    def mock_get_mlflow_config():
        return mock_config

    monkeypatch.setattr("ml.mlflow_config.get_mlflow_config", mock_get_mlflow_config)

    # Also patch in the training_service module if it's already imported
    try:
        monkeypatch.setattr(
            "future_skills.services.training_service.get_mlflow_config",
            mock_get_mlflow_config,
        )
    except AttributeError:
        pass  # Module not imported yet

    # Mock mlflow logging functions
    try:
        import mlflow

        monkeypatch.setattr("mlflow.log_params", MagicMock())
        monkeypatch.setattr("mlflow.log_param", MagicMock())
        monkeypatch.setattr("mlflow.log_metric", MagicMock())
        monkeypatch.setattr("mlflow.log_metrics", MagicMock())
        monkeypatch.setattr("mlflow.log_artifact", MagicMock())
        monkeypatch.setattr("mlflow.sklearn.log_model", MagicMock())
        monkeypatch.setattr("mlflow.set_tag", MagicMock())
    except (ImportError, AttributeError):
        pass  # mlflow not available yet

    return mock_config


# Re-export fixtures so they're available in ml/tests
__all__ = [
    "sample_skill",
    "sample_job_role",
    "sample_future_skill_prediction",
    "regular_user",
    "admin_user",
    "mlflow_test_environment",
    "mock_mlflow_run",
    "mock_mlflow_config",
]
