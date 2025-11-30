"""Extended tests for ModelTrainer to improve coverage from 46% to 50%+.

This test module focuses on:
- Error handling and exception paths
- MLflow integration scenarios
- Model versioning and promotion logic
- Failed training run tracking
- Edge cases in data loading and preprocessing
- Pipeline building edge cases
- Model persistence error scenarios
- Feature importance edge cases

Target: Improve coverage from 46% to 50%+
"""

import pytest
import pandas as pd
from unittest.mock import patch, MagicMock, PropertyMock
from datetime import datetime

from future_skills.services.training_service import (
    ModelTrainer,
    DataLoadError,
    TrainingError,
    ModelTrainerError,
)


# ============================================================================
# Test Exception Classes
# ============================================================================


class TestExceptionHierarchy:
    """Test custom exception classes."""

    def test_data_load_error_is_model_trainer_error(self):
        """Test that DataLoadError inherits from ModelTrainerError."""
        error = DataLoadError("Test error")
        assert isinstance(error, ModelTrainerError)
        assert isinstance(error, Exception)

    def test_training_error_is_model_trainer_error(self):
        """Test that TrainingError inherits from ModelTrainerError."""
        error = TrainingError("Test error")
        assert isinstance(error, ModelTrainerError)
        assert isinstance(error, Exception)

    def test_exceptions_can_be_raised_and_caught(self):
        """Test that custom exceptions work properly."""
        with pytest.raises(DataLoadError, match="Data error"):
            raise DataLoadError("Data error")

        with pytest.raises(TrainingError, match="Training error"):
            raise TrainingError("Training error")

        with pytest.raises(ModelTrainerError):
            raise DataLoadError("Any model trainer error")


# ============================================================================
# Test Data Loading Edge Cases
# ============================================================================


class TestDataLoadingEdgeCases:
    """Test edge cases in data loading and validation."""

    def test_load_data_with_all_invalid_labels(self, tmp_path):
        """Test error when all rows have invalid labels."""
        data = {
            "trend_score": [0.8, 0.6, 0.3] * 5,
            "internal_usage": [0.9, 0.7, 0.4] * 5,
            "future_need_level": ["INVALID", "WRONG", "BAD"] * 5,
        }
        df = pd.DataFrame(data)
        dataset_path = tmp_path / "all_invalid.csv"
        df.to_csv(dataset_path, index=False)

        trainer = ModelTrainer(str(dataset_path))

        with pytest.raises(DataLoadError, match="No valid rows"):
            trainer.load_data()

    def test_load_data_with_parser_error(self, tmp_path):
        """Test handling of malformed CSV files."""
        dataset_path = tmp_path / "malformed.csv"
        # Write malformed CSV (unmatched quotes, inconsistent columns)
        dataset_path.write_text(
            'trend_score,"internal_usage\n0.8,"0.9\n0.6,0.7"extra"\n'
        )

        trainer = ModelTrainer(str(dataset_path))

        with pytest.raises(DataLoadError, match="Failed to parse CSV"):
            trainer.load_data()

    def test_load_data_with_no_features_available(self, tmp_path):
        """Test error when dataset has target but no feature columns."""
        data = {
            "unknown_column_1": [1, 2, 3] * 5,
            "unknown_column_2": [4, 5, 6] * 5,
            "future_need_level": ["HIGH", "MEDIUM", "LOW"] * 5,
        }
        df = pd.DataFrame(data)
        dataset_path = tmp_path / "no_features.csv"
        df.to_csv(dataset_path, index=False)

        trainer = ModelTrainer(str(dataset_path))

        with pytest.raises(DataLoadError, match="No features available"):
            trainer.load_data()

    def test_load_data_logs_missing_features(self, tmp_path, caplog):
        """Test that missing features are logged as warnings."""
        # Only include 2 out of many expected features
        data = {
            "trend_score": [0.8, 0.6, 0.3] * 10,
            "internal_usage": [0.9, 0.7, 0.4] * 10,
            "future_need_level": ["HIGH", "MEDIUM", "LOW"] * 10,
        }
        df = pd.DataFrame(data)
        dataset_path = tmp_path / "partial_features.csv"
        df.to_csv(dataset_path, index=False)

        trainer = ModelTrainer(str(dataset_path))

        with caplog.at_level("WARNING"):
            trainer.load_data()

        # Should log missing features
        assert any("Missing features" in record.message for record in caplog.records)
        assert len(trainer.missing_features) > 0

    def test_load_data_with_extreme_imbalance(self, tmp_path, caplog):
        """Test handling of extreme class imbalance (ratio > 10)."""
        # 95 HIGH, 4 MEDIUM, 1 LOW = ratio of 95:1
        data = {
            "trend_score": [0.8] * 95 + [0.5] * 4 + [0.2] * 1,
            "internal_usage": [0.9] * 95 + [0.6] * 4 + [0.3] * 1,
            "future_need_level": ["HIGH"] * 95 + ["MEDIUM"] * 4 + ["LOW"] * 1,
        }
        df = pd.DataFrame(data)
        dataset_path = tmp_path / "extreme_imbalance.csv"
        df.to_csv(dataset_path, index=False)

        trainer = ModelTrainer(str(dataset_path))

        with caplog.at_level("WARNING"):
            trainer.load_data()

        # Should warn about imbalance
        assert any("imbalance" in record.message.lower() for record in caplog.records)

    def test_load_data_unexpected_error(self, tmp_path):
        """Test handling of unexpected errors during data loading."""
        dataset_path = tmp_path / "test.csv"

        # Create valid CSV first
        data = {"trend_score": [0.8, 0.6] * 5, "future_need_level": ["HIGH", "LOW"] * 5}
        df = pd.DataFrame(data)
        df.to_csv(dataset_path, index=False)

        trainer = ModelTrainer(str(dataset_path))

        # Mock pd.read_csv to raise unexpected error
        with patch("pandas.read_csv", side_effect=RuntimeError("Unexpected error")):
            with pytest.raises(DataLoadError, match="Unexpected error loading data"):
                trainer.load_data()

    def test_identify_feature_types_edge_cases(self, tmp_path):
        """Test feature type identification with mixed types."""
        data = {
            "categorical_1": ["A", "B", "C"] * 10,
            "categorical_2": pd.Categorical(["X", "Y", "Z"] * 10),
            "numeric_1": [1, 2, 3] * 10,
            "numeric_2": [1.5, 2.5, 3.5] * 10,
            "future_need_level": ["HIGH", "MEDIUM", "LOW"] * 10,
        }
        df = pd.DataFrame(data)
        dataset_path = tmp_path / "mixed_types.csv"
        df.to_csv(dataset_path, index=False)

        trainer = ModelTrainer(str(dataset_path))
        trainer.load_data()

        # Check that types are correctly identified
        assert len(trainer.categorical_features) >= 2
        assert len(trainer.numeric_features) >= 2


# ============================================================================
# Test Training Error Scenarios
# ============================================================================


class TestTrainingErrorScenarios:
    """Test error handling during model training."""

    def test_train_handles_mlflow_setup_error(self, tmp_path):
        """Test graceful handling when MLflow setup fails."""
        # Create valid dataset
        data = {
            "trend_score": [0.8, 0.6, 0.3] * 20,
            "internal_usage": [0.9, 0.7, 0.4] * 20,
            "future_need_level": ["HIGH", "MEDIUM", "LOW"] * 20,
        }
        df = pd.DataFrame(data)
        dataset_path = tmp_path / "test.csv"
        df.to_csv(dataset_path, index=False)

        trainer = ModelTrainer(str(dataset_path))
        trainer.load_data()

        # Mock MLflow to raise error during setup
        with patch(
            "future_skills.services.training_service.get_mlflow_config"
        ) as mock_config:
            mock_config.return_value.setup.side_effect = Exception(
                "MLflow connection failed"
            )

            with pytest.raises(TrainingError, match="Model training failed"):
                trainer.train()

    def test_train_handles_model_fit_error(self, tmp_path):
        """Test handling when model.fit() raises an error."""
        data = {
            "trend_score": [0.8, 0.6, 0.3] * 20,
            "internal_usage": [0.9, 0.7, 0.4] * 20,
            "future_need_level": ["HIGH", "MEDIUM", "LOW"] * 20,
        }
        df = pd.DataFrame(data)
        dataset_path = tmp_path / "test.csv"
        df.to_csv(dataset_path, index=False)

        trainer = ModelTrainer(str(dataset_path))
        trainer.load_data()

        # Mock the pipeline's fit method to raise error
        with patch.object(trainer, "_build_pipeline") as mock_build:
            mock_pipeline = MagicMock()
            mock_pipeline.fit.side_effect = ValueError("Invalid training data")
            mock_build.return_value = mock_pipeline

            with pytest.raises(TrainingError, match="Model training failed"):
                trainer.train()

        # Check that training time was still recorded
        assert trainer.training_duration_seconds >= 0

    def test_train_logs_mlflow_run_id(self, tmp_path, caplog):
        """Test that MLflow run ID is logged after training."""
        data = {
            "trend_score": [0.8, 0.6, 0.3] * 20,
            "internal_usage": [0.9, 0.7, 0.4] * 20,
            "future_need_level": ["HIGH", "MEDIUM", "LOW"] * 20,
        }
        df = pd.DataFrame(data)
        dataset_path = tmp_path / "test.csv"
        df.to_csv(dataset_path, index=False)

        trainer = ModelTrainer(str(dataset_path))
        trainer.load_data()

        # Mock MLflow to capture run_id
        with patch(
            "future_skills.services.training_service.get_mlflow_config"
        ) as mock_config:
            mock_run = MagicMock()
            mock_run.info.run_id = "test-run-id-12345"
            mock_config.return_value.start_run.return_value.__enter__.return_value = (
                mock_run
            )

            with caplog.at_level("INFO"):
                trainer.train(n_estimators=10)

            # Check that run_id was logged
            assert any(
                "test-run-id-12345" in record.message for record in caplog.records
            )
            assert trainer.mlflow_run_id == "test-run-id-12345"


# ============================================================================
# Test Model Evaluation Edge Cases
# ============================================================================


class TestEvaluationEdgeCases:
    """Test edge cases in model evaluation."""

    def test_evaluate_handles_prediction_error(self, tmp_path):
        """Test handling when model.predict() fails during evaluation."""
        data = {
            "trend_score": [0.8, 0.6, 0.3] * 20,
            "internal_usage": [0.9, 0.7, 0.4] * 20,
            "future_need_level": ["HIGH", "MEDIUM", "LOW"] * 20,
        }
        df = pd.DataFrame(data)
        dataset_path = tmp_path / "test.csv"
        df.to_csv(dataset_path, index=False)

        trainer = ModelTrainer(str(dataset_path))
        trainer.load_data()
        trainer.train(n_estimators=10)

        # Mock predict to raise error
        with patch.object(
            trainer.model, "predict", side_effect=RuntimeError("Prediction failed")
        ):
            with pytest.raises(TrainingError, match="Model evaluation failed"):
                trainer.evaluate(trainer.X_test, trainer.y_test)

    def test_compute_per_class_metrics_with_zero_support(self, tmp_path):
        """Test per-class metrics calculation when a class has zero support."""
        # This is a tricky scenario - create test where prediction never produces a class
        data = {
            "trend_score": [0.8, 0.6, 0.3] * 20,
            "internal_usage": [0.9, 0.7, 0.4] * 20,
            "future_need_level": ["HIGH", "MEDIUM", "LOW"] * 20,
        }
        df = pd.DataFrame(data)
        dataset_path = tmp_path / "test.csv"
        df.to_csv(dataset_path, index=False)

        trainer = ModelTrainer(str(dataset_path))
        trainer.load_data()
        trainer.train(n_estimators=10)

        # Create a confusion matrix with zero support for one class
        import numpy as np

        cm = np.array(
            [
                [0, 0, 0],  # LOW class has zero support
                [0, 5, 1],  # MEDIUM
                [0, 1, 4],  # HIGH
            ]
        )

        per_class = trainer._compute_per_class_metrics(cm)

        # Should handle zero support gracefully
        assert per_class["LOW"]["support"] == 0
        assert per_class["LOW"]["accuracy"] == 0.0


# ============================================================================
# Test Model Persistence Error Scenarios
# ============================================================================


class TestModelPersistenceErrors:
    """Test error handling in model save operations."""

    def test_save_model_handles_permission_error(self, tmp_path):
        """Test handling when model save fails due to permissions."""
        data = {
            "trend_score": [0.8, 0.6, 0.3] * 20,
            "internal_usage": [0.9, 0.7, 0.4] * 20,
            "future_need_level": ["HIGH", "MEDIUM", "LOW"] * 20,
        }
        df = pd.DataFrame(data)
        dataset_path = tmp_path / "test.csv"
        df.to_csv(dataset_path, index=False)

        trainer = ModelTrainer(str(dataset_path))
        trainer.load_data()
        trainer.train(n_estimators=10)

        # Mock joblib.dump to raise PermissionError
        with patch(
            "future_skills.services.training_service.joblib.dump",
            side_effect=PermissionError("Permission denied"),
        ):
            with pytest.raises(TrainingError, match="Model save failed"):
                trainer.save_model(str(tmp_path / "model.pkl"))

    def test_save_model_handles_disk_full_error(self, tmp_path):
        """Test handling when disk is full during save."""
        data = {
            "trend_score": [0.8, 0.6, 0.3] * 20,
            "internal_usage": [0.9, 0.7, 0.4] * 20,
            "future_need_level": ["HIGH", "MEDIUM", "LOW"] * 20,
        }
        df = pd.DataFrame(data)
        dataset_path = tmp_path / "test.csv"
        df.to_csv(dataset_path, index=False)

        trainer = ModelTrainer(str(dataset_path))
        trainer.load_data()
        trainer.train(n_estimators=10)

        with patch(
            "future_skills.services.training_service.joblib.dump",
            side_effect=OSError("No space left on device"),
        ):
            with pytest.raises(TrainingError, match="Model save failed"):
                trainer.save_model(str(tmp_path / "model.pkl"))


# ============================================================================
# Test Feature Importance Edge Cases
# ============================================================================


class TestFeatureImportanceEdgeCases:
    """Test edge cases in feature importance extraction."""

    def test_get_feature_importance_without_categorical_features(self, tmp_path):
        """Test feature importance when only numeric features present."""
        # Only numeric features
        data = {
            "trend_score": [0.8, 0.6, 0.3] * 20,
            "internal_usage": [0.9, 0.7, 0.4] * 20,
            "training_requests": [15, 10, 5] * 20,
            "future_need_level": ["HIGH", "MEDIUM", "LOW"] * 20,
        }
        df = pd.DataFrame(data)
        dataset_path = tmp_path / "numeric_only.csv"
        df.to_csv(dataset_path, index=False)

        trainer = ModelTrainer(str(dataset_path))
        trainer.load_data()
        trainer.train(n_estimators=10)

        importance = trainer.get_feature_importance()

        # Should still work with only numeric features
        assert len(importance) > 0
        assert all(isinstance(v, float) for v in importance.values())

    def test_get_feature_importance_handles_extraction_error(self, tmp_path):
        """Test handling when feature importance extraction fails."""
        data = {
            "trend_score": [0.8, 0.6, 0.3] * 20,
            "internal_usage": [0.9, 0.7, 0.4] * 20,
            "future_need_level": ["HIGH", "MEDIUM", "LOW"] * 20,
        }
        df = pd.DataFrame(data)
        dataset_path = tmp_path / "test.csv"
        df.to_csv(dataset_path, index=False)

        trainer = ModelTrainer(str(dataset_path))
        trainer.load_data()
        trainer.train(n_estimators=10)

        # Mock feature importance to raise error
        with patch.object(
            trainer.model.named_steps["clf"],
            "feature_importances_",
            new_callable=PropertyMock,
        ) as mock_importance:
            mock_importance.side_effect = AttributeError("Feature importance error")

            # Should return empty dict on error
            importance = trainer.get_feature_importance()
            assert importance == {}

    def test_get_feature_importance_with_feature_count_mismatch(self, tmp_path, caplog):
        """Test handling when feature count doesn't match importance array."""
        data = {
            "trend_score": [0.8, 0.6, 0.3] * 20,
            "internal_usage": [0.9, 0.7, 0.4] * 20,
            "future_need_level": ["HIGH", "MEDIUM", "LOW"] * 20,
        }
        df = pd.DataFrame(data)
        dataset_path = tmp_path / "test.csv"
        df.to_csv(dataset_path, index=False)

        trainer = ModelTrainer(str(dataset_path))
        trainer.load_data()
        trainer.train(n_estimators=10)

        # Mock to create mismatch
        import numpy as np

        with patch.object(
            trainer.model.named_steps["clf"],
            "feature_importances_",
            new=np.array([0.5, 0.3]),
        ):  # Wrong number of features
            with caplog.at_level("WARNING"):
                importance = trainer.get_feature_importance()

            # Should log warning and return empty dict
            assert any(
                "Feature count mismatch" in record.message for record in caplog.records
            )
            assert importance == {}


# ============================================================================
# Test TrainingRun Saving and Model Versioning
# ============================================================================


class TestTrainingRunSaving:
    """Test saving training runs with model versioning."""

    @patch("future_skills.services.training_service.TrainingRun")
    @patch("future_skills.services.training_service.create_model_version")
    @patch("future_skills.services.training_service.ModelVersionManager")
    def test_save_training_run_with_auto_promotion(
        self, mock_manager_class, mock_create_version, mock_training_run, tmp_path
    ):
        """Test auto-promotion logic when new model improves metrics."""
        data = {
            "trend_score": [0.8, 0.6, 0.3] * 20,
            "internal_usage": [0.9, 0.7, 0.4] * 20,
            "future_need_level": ["HIGH", "MEDIUM", "LOW"] * 20,
        }
        df = pd.DataFrame(data)
        dataset_path = tmp_path / "test.csv"
        df.to_csv(dataset_path, index=False)

        trainer = ModelTrainer(str(dataset_path))
        trainer.load_data()
        trainer.train(n_estimators=10)

        model_path = tmp_path / "model.pkl"
        trainer.save_model(str(model_path))

        # Mock version manager
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        # Mock existing production version
        mock_prod_version = MagicMock()
        mock_manager.get_production_version.return_value = mock_prod_version

        # Mock should_promote to return True
        mock_manager.should_promote.return_value = (True, "F1-score improved by 5%")

        # Mock create method
        mock_training_run.objects.create.return_value = MagicMock(id=123)

        trainer.save_training_run(
            model_version="v2.0.0", model_path=str(model_path), auto_promote=True
        )

        # Verify promotion was attempted
        assert mock_manager.should_promote.called
        assert mock_manager.register_version.call_count >= 2  # Initial + promotion

    @patch("future_skills.services.training_service.TrainingRun")
    @patch("future_skills.services.training_service.create_model_version")
    @patch("future_skills.services.training_service.ModelVersionManager")
    def test_save_training_run_no_promotion_when_not_improved(
        self, mock_manager_class, mock_create_version, mock_training_run, tmp_path
    ):
        """Test that model is not promoted when metrics don't improve."""
        data = {
            "trend_score": [0.8, 0.6, 0.3] * 20,
            "internal_usage": [0.9, 0.7, 0.4] * 20,
            "future_need_level": ["HIGH", "MEDIUM", "LOW"] * 20,
        }
        df = pd.DataFrame(data)
        dataset_path = tmp_path / "test.csv"
        df.to_csv(dataset_path, index=False)

        trainer = ModelTrainer(str(dataset_path))
        trainer.load_data()
        trainer.train(n_estimators=10)

        model_path = tmp_path / "model.pkl"
        trainer.save_model(str(model_path))

        # Mock version manager
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_prod_version = MagicMock()
        mock_manager.get_production_version.return_value = mock_prod_version

        # Mock should_promote to return False
        mock_manager.should_promote.return_value = (False, "Metrics not improved")

        mock_training_run.objects.create.return_value = MagicMock(id=123)

        trainer.save_training_run(
            model_version="v2.0.0", model_path=str(model_path), auto_promote=True
        )

        # Should call register_version only once (no promotion)
        assert mock_manager.register_version.call_count == 1

    @patch("future_skills.services.training_service.TrainingRun")
    @patch("future_skills.services.training_service.create_model_version")
    @patch("future_skills.services.training_service.ModelVersionManager")
    def test_save_training_run_first_model_auto_promotes(
        self, mock_manager_class, mock_create_version, mock_training_run, tmp_path
    ):
        """Test that first model is automatically promoted to production."""
        data = {
            "trend_score": [0.8, 0.6, 0.3] * 20,
            "internal_usage": [0.9, 0.7, 0.4] * 20,
            "future_need_level": ["HIGH", "MEDIUM", "LOW"] * 20,
        }
        df = pd.DataFrame(data)
        dataset_path = tmp_path / "test.csv"
        df.to_csv(dataset_path, index=False)

        trainer = ModelTrainer(str(dataset_path))
        trainer.load_data()
        trainer.train(n_estimators=10)

        model_path = tmp_path / "model.pkl"
        trainer.save_model(str(model_path))

        # Mock version manager with no existing production version
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.get_production_version.return_value = None  # No existing model

        mock_training_run.objects.create.return_value = MagicMock(id=123)

        trainer.save_training_run(
            model_version="v1.0.0", model_path=str(model_path), auto_promote=True
        )

        # Should register twice (initial + auto-promotion)
        assert mock_manager.register_version.call_count >= 2

    @patch("future_skills.services.training_service.TrainingRun")
    @patch("future_skills.services.training_service.create_model_version")
    @patch("future_skills.services.training_service.ModelVersionManager")
    @patch("future_skills.services.training_service.get_mlflow_config")
    def test_save_training_run_handles_mlflow_transition_error(
        self,
        mock_mlflow,
        mock_manager_class,
        mock_create_version,
        mock_training_run,
        tmp_path,
        caplog,
    ):
        """Test graceful handling when MLflow stage transition fails."""
        data = {
            "trend_score": [0.8, 0.6, 0.3] * 20,
            "internal_usage": [0.9, 0.7, 0.4] * 20,
            "future_need_level": ["HIGH", "MEDIUM", "LOW"] * 20,
        }
        df = pd.DataFrame(data)
        dataset_path = tmp_path / "test.csv"
        df.to_csv(dataset_path, index=False)

        trainer = ModelTrainer(str(dataset_path))
        trainer.load_data()
        trainer.train(n_estimators=10)

        model_path = tmp_path / "model.pkl"
        trainer.save_model(str(model_path))

        # Mock version manager to trigger promotion
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_prod_version = MagicMock()
        mock_manager.get_production_version.return_value = mock_prod_version
        mock_manager.should_promote.return_value = (True, "Improved")

        # Mock MLflow to raise error during transition
        mock_mlflow_config = MagicMock()
        mock_mlflow_config.transition_model_stage.side_effect = Exception(
            "MLflow error"
        )
        mock_mlflow.return_value = mock_mlflow_config

        mock_training_run.objects.create.return_value = MagicMock(id=123)

        with caplog.at_level("WARNING"):
            # Should not raise exception, just log warning
            trainer.save_training_run(
                model_version="v2.0.0", model_path=str(model_path), auto_promote=True
            )

        # Should log warning about MLflow failure
        assert any(
            "Failed to transition MLflow stage" in record.message
            for record in caplog.records
        )

    def test_save_training_run_handles_database_error(self, tmp_path):
        """Test handling when database save fails."""
        data = {
            "trend_score": [0.8, 0.6, 0.3] * 20,
            "internal_usage": [0.9, 0.7, 0.4] * 20,
            "future_need_level": ["HIGH", "MEDIUM", "LOW"] * 20,
        }
        df = pd.DataFrame(data)
        dataset_path = tmp_path / "test.csv"
        df.to_csv(dataset_path, index=False)

        trainer = ModelTrainer(str(dataset_path))
        trainer.load_data()
        trainer.train(n_estimators=10)

        model_path = tmp_path / "model.pkl"
        trainer.save_model(str(model_path))

        # Mock create_model_version to raise error
        with patch(
            "future_skills.services.training_service.create_model_version",
            side_effect=Exception("Database connection error"),
        ):
            with pytest.raises(TrainingError, match="Failed to save training run"):
                trainer.save_training_run(
                    model_version="v1.0.0", model_path=str(model_path)
                )


# ============================================================================
# Test Failed Training Run Tracking
# ============================================================================


class TestFailedTrainingRunTracking:
    """Test tracking of failed training runs."""

    @patch("future_skills.services.training_service.TrainingRun")
    def test_save_failed_training_run_creates_record(self, mock_training_run, tmp_path):
        """Test that failed runs are recorded in database."""
        data = {
            "trend_score": [0.8, 0.6, 0.3] * 20,
            "future_need_level": ["HIGH", "MEDIUM", "LOW"] * 20,
        }
        df = pd.DataFrame(data)
        dataset_path = tmp_path / "test.csv"
        df.to_csv(dataset_path, index=False)

        trainer = ModelTrainer(str(dataset_path))
        trainer.training_start_time = datetime.now()
        trainer.training_duration_seconds = 10.5

        mock_training_run.objects.create.return_value = MagicMock(id=456)

        failed_run = trainer.save_failed_training_run(
            model_version="v1.0.0",
            error_message="Training failed due to insufficient data",
            notes="Test failed run",
        )

        # Verify create was called
        assert mock_training_run.objects.create.called
        call_kwargs = mock_training_run.objects.create.call_args[1]

        # Check status is FAILED
        assert call_kwargs["status"] == "FAILED"
        assert (
            call_kwargs["error_message"] == "Training failed due to insufficient data"
        )
        assert call_kwargs["model_version"] == "v1.0.0"

        # Check metrics are zero
        assert call_kwargs["accuracy"] == 0.0
        assert call_kwargs["f1_score"] == 0.0

    @patch("future_skills.services.training_service.TrainingRun")
    def test_save_failed_training_run_handles_save_error(
        self, mock_training_run, tmp_path
    ):
        """Test handling when saving failed run itself fails."""
        data = {"trend_score": [0.8], "future_need_level": ["HIGH"]}
        df = pd.DataFrame(data)
        dataset_path = tmp_path / "test.csv"
        df.to_csv(dataset_path, index=False)

        trainer = ModelTrainer(str(dataset_path))

        # Mock create to raise error
        mock_training_run.objects.create.side_effect = Exception("DB error")

        # Should re-raise the exception
        with pytest.raises(Exception, match="DB error"):
            trainer.save_failed_training_run(
                model_version="v1.0.0", error_message="Original training error"
            )


# ============================================================================
# Test Pipeline Building
# ============================================================================


class TestPipelineBuilding:
    """Test edge cases in pipeline construction."""

    def test_build_pipeline_with_only_categorical_features(self, tmp_path):
        """Test pipeline when only categorical features present."""
        data = {
            "job_role_name": ["Engineer", "Scientist", "Manager"] * 20,
            "skill_name": ["Python", "R", "Excel"] * 20,
            "future_need_level": ["HIGH", "MEDIUM", "LOW"] * 20,
        }
        df = pd.DataFrame(data)
        dataset_path = tmp_path / "categorical_only.csv"
        df.to_csv(dataset_path, index=False)

        trainer = ModelTrainer(str(dataset_path))
        trainer.load_data()

        # Should build pipeline successfully
        pipeline = trainer._build_pipeline()
        assert pipeline is not None
        assert "preprocess" in pipeline.named_steps
        assert "clf" in pipeline.named_steps

    def test_build_pipeline_with_empty_categorical_list(self, tmp_path):
        """Test pipeline when categorical_features list is empty."""
        data = {
            "trend_score": [0.8, 0.6, 0.3] * 20,
            "internal_usage": [0.9, 0.7, 0.4] * 20,
            "future_need_level": ["HIGH", "MEDIUM", "LOW"] * 20,
        }
        df = pd.DataFrame(data)
        dataset_path = tmp_path / "numeric_only.csv"
        df.to_csv(dataset_path, index=False)

        trainer = ModelTrainer(str(dataset_path))
        trainer.load_data()

        # Should have empty categorical list
        assert len(trainer.categorical_features) == 0
        assert len(trainer.numeric_features) > 0

        # Should still build pipeline
        pipeline = trainer._build_pipeline()
        assert pipeline is not None


# ============================================================================
# Test Integration with MLflow
# ============================================================================


class TestMLflowIntegration:
    """Test MLflow logging and tracking integration."""

    @patch("future_skills.services.training_service.get_mlflow_config")
    @patch("future_skills.services.training_service.mlflow")
    def test_train_logs_all_parameters_to_mlflow(
        self, mock_mlflow, mock_config, tmp_path
    ):
        """Test that all training parameters are logged to MLflow."""
        data = {
            "trend_score": [0.8, 0.6, 0.3] * 20,
            "internal_usage": [0.9, 0.7, 0.4] * 20,
            "future_need_level": ["HIGH", "MEDIUM", "LOW"] * 20,
        }
        df = pd.DataFrame(data)
        dataset_path = tmp_path / "test.csv"
        df.to_csv(dataset_path, index=False)

        trainer = ModelTrainer(str(dataset_path))
        trainer.load_data()

        # Mock MLflow
        mock_run = MagicMock()
        mock_run.info.run_id = "test-run-123"
        mock_config.return_value.start_run.return_value.__enter__.return_value = (
            mock_run
        )

        trainer.train(n_estimators=100, max_depth=15)

        # Verify parameters were logged
        assert mock_mlflow.log_params.called
        assert mock_mlflow.log_param.called

        # Verify metrics were logged
        assert mock_mlflow.log_metrics.called
        assert mock_mlflow.log_metric.called

        # Verify model was logged
        assert mock_mlflow.sklearn.log_model.called

    @patch("future_skills.services.training_service.get_mlflow_config")
    def test_train_logs_per_class_metrics_to_mlflow(self, mock_config, tmp_path):
        """Test that per-class metrics are logged to MLflow."""
        data = {
            "trend_score": [0.8, 0.6, 0.3] * 20,
            "internal_usage": [0.9, 0.7, 0.4] * 20,
            "future_need_level": ["HIGH", "MEDIUM", "LOW"] * 20,
        }
        df = pd.DataFrame(data)
        dataset_path = tmp_path / "test.csv"
        df.to_csv(dataset_path, index=False)

        trainer = ModelTrainer(str(dataset_path))
        trainer.load_data()

        with patch("future_skills.services.training_service.mlflow") as mock_mlflow:
            mock_run = MagicMock()
            mock_run.info.run_id = "test-run-123"
            mock_config.return_value.start_run.return_value.__enter__.return_value = (
                mock_run
            )

            trainer.train(n_estimators=10)

            # Check that per-class metrics were logged
            log_metric_calls = [
                call[0][0] for call in mock_mlflow.log_metric.call_args_list
            ]

            # Should have LOW_, MEDIUM_, HIGH_ prefixed metrics
            assert any(
                "LOW_" in str(call) or "MEDIUM_" in str(call) or "HIGH_" in str(call)
                for call in log_metric_calls
            )
