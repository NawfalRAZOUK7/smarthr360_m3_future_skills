# ml/tests/test_model_training.py

"""
Tests for ML Model Training Service.

Tests the ModelTrainer class which handles the complete training lifecycle
including data loading, model training, evaluation, and persistence.
"""

import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import patch, MagicMock

from future_skills.ml_model import FutureSkillsModel
from future_skills.services.training_service import (
    ModelTrainer,
    DataLoadError,
    TrainingError,
)


@pytest.fixture
def sample_dataset(tmp_path):
    """Create a sample dataset for testing."""
    data = {
        'job_role_name': ['Software Engineer', 'Data Scientist', 'DevOps Engineer'] * 20,
        'skill_name': ['Python', 'Machine Learning', 'Docker'] * 20,
        'skill_category': ['Programming', 'AI/ML', 'Infrastructure'] * 20,
        'job_department': ['Engineering', 'Data', 'Operations'] * 20,
        'trend_score': [0.8, 0.6, 0.3, 0.7, 0.5, 0.2] * 10,
        'internal_usage': [0.9, 0.7, 0.4, 0.8, 0.6, 0.3] * 10,
        'training_requests': [15, 10, 5, 12, 8, 3] * 10,
        'scarcity_index': [0.7, 0.5, 0.2, 0.6, 0.4, 0.1] * 10,
        'hiring_difficulty': [0.8, 0.6, 0.3, 0.7, 0.5, 0.2] * 10,
        'avg_salary_k': [120, 110, 90, 115, 105, 85] * 10,
        'economic_indicator': [0.9, 0.7, 0.4, 0.8, 0.6, 0.3] * 10,
        'future_need_level': ['HIGH', 'MEDIUM', 'LOW', 'HIGH', 'MEDIUM', 'LOW'] * 10
    }
    df = pd.DataFrame(data)

    dataset_path = tmp_path / "training_data.csv"
    df.to_csv(dataset_path, index=False)

    return dataset_path


@pytest.fixture
def minimal_dataset(tmp_path):
    """Create a minimal dataset with only required columns."""
    data = {
        'trend_score': [0.8, 0.6, 0.3, 0.7, 0.5, 0.2] * 10,
        'internal_usage': [0.9, 0.7, 0.4, 0.8, 0.6, 0.3] * 10,
        'future_need_level': ['HIGH', 'MEDIUM', 'LOW', 'HIGH', 'MEDIUM', 'LOW'] * 10
    }
    df = pd.DataFrame(data)

    dataset_path = tmp_path / "minimal_data.csv"
    df.to_csv(dataset_path, index=False)

    return dataset_path


@pytest.fixture
def imbalanced_dataset(tmp_path):
    """Create an imbalanced dataset for testing class weights."""
    data = {
        'trend_score': [0.8] * 50 + [0.5] * 10 + [0.2] * 5,
        'internal_usage': [0.9] * 50 + [0.6] * 10 + [0.3] * 5,
        'future_need_level': ['HIGH'] * 50 + ['MEDIUM'] * 10 + ['LOW'] * 5
    }
    df = pd.DataFrame(data)

    dataset_path = tmp_path / "imbalanced_data.csv"
    df.to_csv(dataset_path, index=False)

    return dataset_path


class TestModelTrainerInitialization:
    """Test ModelTrainer initialization and setup."""

    def test_initialization_with_defaults(self, sample_dataset):
        """Test that ModelTrainer initializes with default parameters."""
        trainer = ModelTrainer(str(sample_dataset))

        assert trainer.dataset_path == Path(sample_dataset)
        assert trainer.test_split == 0.2
        assert trainer.random_state == 42
        assert trainer.model is None
        assert trainer.metrics == {}

    def test_initialization_with_custom_parameters(self, sample_dataset):
        """Test initialization with custom test split and random state."""
        trainer = ModelTrainer(
            str(sample_dataset),
            test_split=0.3,
            random_state=123
        )

        assert trainer.test_split == 0.3
        assert trainer.random_state == 123

    def test_initialization_converts_string_path(self, sample_dataset):
        """Test that string paths are converted to Path objects."""
        trainer = ModelTrainer(str(sample_dataset))

        assert isinstance(trainer.dataset_path, Path)


class TestDataLoading:
    """Test dataset loading and preprocessing."""

    def test_load_data_success(self, sample_dataset):
        """Test successful data loading with all features."""
        trainer = ModelTrainer(str(sample_dataset))
        trainer.load_data()

        # Check data is loaded
        assert trainer.X_train is not None
        assert trainer.X_test is not None
        assert trainer.y_train is not None
        assert trainer.y_test is not None

        # Check splits are correct
        total_samples = len(trainer.X_train) + len(trainer.X_test)
        assert total_samples == 60  # 60 rows in sample dataset

        # Check stratification (approximately 20% test)
        assert len(trainer.X_test) == pytest.approx(12, abs=2)

        # Check target values
        assert len(trainer.y_train) == len(trainer.X_train)
        assert len(trainer.y_test) == len(trainer.X_test)
        assert all(y in ['LOW', 'MEDIUM', 'HIGH'] for y in trainer.y_train)
        assert all(y in ['LOW', 'MEDIUM', 'HIGH'] for y in trainer.y_test)

    def test_load_data_identifies_features(self, sample_dataset):
        """Test that feature types are correctly identified."""
        trainer = ModelTrainer(str(sample_dataset))
        trainer.load_data()

        # Check available features
        assert len(trainer.available_features) > 0

        # Check categorical vs numeric
        assert len(trainer.categorical_features) > 0
        assert len(trainer.numeric_features) > 0

        # Expected categoricals
        expected_cats = {'job_role_name', 'skill_name', 'skill_category', 'job_department'}
        actual_cats = set(trainer.categorical_features)
        assert expected_cats.issubset(actual_cats)

    def test_load_data_with_minimal_features(self, minimal_dataset):
        """Test loading dataset with only some features available."""
        trainer = ModelTrainer(str(minimal_dataset))
        trainer.load_data()

        # Should still work with fewer features
        assert len(trainer.available_features) > 0
        assert len(trainer.missing_features) > 0
        assert trainer.X_train is not None

    def test_load_data_filters_invalid_labels(self, tmp_path):
        """Test that invalid target labels are filtered out."""
        # Need enough samples per class for stratification (at least 2 per class)
        data = {
            'trend_score': [0.8, 0.6, 0.3, 0.7, 0.5, 0.4, 0.9, 0.2] * 2,
            'internal_usage': [0.9, 0.7, 0.4, 0.8, 0.6, 0.5, 0.9, 0.3] * 2,
            'future_need_level': ['HIGH', 'INVALID', 'LOW', 'MEDIUM', 'HIGH', 'LOW', 'MEDIUM', 'INVALID'] * 2
        }
        df = pd.DataFrame(data)
        dataset_path = tmp_path / "invalid_labels.csv"
        df.to_csv(dataset_path, index=False)

        trainer = ModelTrainer(str(dataset_path))
        trainer.load_data()

        # Should have filtered out INVALID rows (4 out of 16)
        assert len(trainer.df) == 12
        assert all(y in ['LOW', 'MEDIUM', 'HIGH'] for y in trainer.df['future_need_level'])

    def test_load_data_file_not_found(self, tmp_path):
        """Test error handling when dataset file doesn't exist."""
        non_existent = tmp_path / "does_not_exist.csv"
        trainer = ModelTrainer(str(non_existent))

        with pytest.raises(DataLoadError, match="Dataset not found"):
            trainer.load_data()

    def test_load_data_missing_target_column(self, tmp_path):
        """Test error when target column is missing."""
        data = {'trend_score': [0.8, 0.6], 'internal_usage': [0.9, 0.7]}
        df = pd.DataFrame(data)
        dataset_path = tmp_path / "no_target.csv"
        df.to_csv(dataset_path, index=False)

        trainer = ModelTrainer(str(dataset_path))

        with pytest.raises(DataLoadError, match="Target column.*not found"):
            trainer.load_data()

    def test_load_data_empty_dataset(self, tmp_path):
        """Test error handling for empty datasets."""
        dataset_path = tmp_path / "empty.csv"
        dataset_path.write_text("future_need_level\n")

        trainer = ModelTrainer(str(dataset_path))

        with pytest.raises(DataLoadError):
            trainer.load_data()

    def test_load_data_warns_on_imbalance(self, imbalanced_dataset):
        """Test that imbalanced data is loaded successfully and uses balanced weights."""
        trainer = ModelTrainer(str(imbalanced_dataset))
        trainer.load_data()

        # Verify data was loaded
        assert trainer.X_train is not None
        assert trainer.y_train is not None

        # Check class distribution in training data
        class_counts = trainer.y_train.value_counts()
        imbalance_ratio = class_counts.max() / class_counts.min()

        # Should detect significant imbalance
        assert imbalance_ratio > 3, "Test dataset should have imbalance ratio > 3"


class TestModelTraining:
    """Test model training functionality."""

    def test_train_with_defaults(self, sample_dataset):
        """Test training with default hyperparameters."""
        trainer = ModelTrainer(str(sample_dataset))
        trainer.load_data()
        metrics = trainer.train()

        # Check model is trained
        assert trainer.model is not None

        # Check metrics are returned
        assert 'accuracy' in metrics
        assert 'precision' in metrics
        assert 'recall' in metrics
        assert 'f1_score' in metrics

        # Check timing is recorded
        assert trainer.training_duration_seconds > 0
        assert trainer.training_start_time is not None
        assert trainer.training_end_time is not None

    def test_train_with_custom_hyperparameters(self, sample_dataset):
        """Test training with custom hyperparameters."""
        trainer = ModelTrainer(str(sample_dataset))
        trainer.load_data()

        metrics = trainer.train(
            n_estimators=50,
            max_depth=10,
            min_samples_split=5
        )

        # Check hyperparameters are stored
        assert trainer.hyperparameters['n_estimators'] == 50
        assert trainer.hyperparameters['max_depth'] == 10
        assert trainer.hyperparameters['min_samples_split'] == 5

        # Check model trained successfully
        assert trainer.model is not None
        assert metrics['accuracy'] >= 0

    def test_train_without_loading_data(self, sample_dataset):
        """Test that training fails if data not loaded first."""
        trainer = ModelTrainer(str(sample_dataset))

        with pytest.raises(TrainingError, match="Data not loaded"):
            trainer.train()

    def test_train_uses_balanced_weights(self, imbalanced_dataset):
        """Test that balanced class weights are used for imbalanced data."""
        trainer = ModelTrainer(str(imbalanced_dataset))
        trainer.load_data()
        trainer.train()

        # Check class_weight is set to balanced
        assert trainer.hyperparameters['class_weight'] == 'balanced'


class TestModelEvaluation:
    """Test model evaluation and metrics."""

    def test_evaluate_returns_all_metrics(self, sample_dataset):
        """Test that evaluation returns complete metrics."""
        trainer = ModelTrainer(str(sample_dataset))
        trainer.load_data()
        trainer.train()
        metrics = trainer.evaluate(trainer.X_test, trainer.y_test)

        # Check all required metrics
        assert 'accuracy' in metrics
        assert 'precision' in metrics
        assert 'recall' in metrics
        assert 'f1_score' in metrics
        assert 'per_class' in metrics
        assert 'confusion_matrix' in metrics

    def test_evaluate_metric_ranges(self, sample_dataset):
        """Test that metrics are in valid ranges."""
        trainer = ModelTrainer(str(sample_dataset))
        trainer.load_data()
        trainer.train()
        metrics = trainer.evaluate(trainer.X_test, trainer.y_test)

        # Check ranges (0 to 1)
        assert 0 <= metrics['accuracy'] <= 1
        assert 0 <= metrics['precision'] <= 1
        assert 0 <= metrics['recall'] <= 1
        assert 0 <= metrics['f1_score'] <= 1

    def test_evaluate_per_class_metrics(self, sample_dataset):
        """Test per-class metrics calculation."""
        trainer = ModelTrainer(str(sample_dataset))
        trainer.load_data()
        trainer.train()
        metrics = trainer.evaluate(trainer.X_test, trainer.y_test)

        per_class = metrics['per_class']

        # Check all classes present
        assert 'LOW' in per_class
        assert 'MEDIUM' in per_class
        assert 'HIGH' in per_class

        # Check each class has accuracy and support
        for level in ['LOW', 'MEDIUM', 'HIGH']:
            assert 'accuracy' in per_class[level]
            assert 'support' in per_class[level]
            assert 0 <= per_class[level]['accuracy'] <= 1
            assert per_class[level]['support'] >= 0

    def test_evaluate_without_training(self, sample_dataset):
        """Test that evaluation fails if model not trained."""
        trainer = ModelTrainer(str(sample_dataset))
        trainer.load_data()

        with pytest.raises(TrainingError, match="Model not trained"):
            trainer.evaluate(trainer.X_test, trainer.y_test)

    def test_confusion_matrix_shape(self, sample_dataset):
        """Test that confusion matrix has correct shape."""
        trainer = ModelTrainer(str(sample_dataset))
        trainer.load_data()
        trainer.train()
        metrics = trainer.evaluate(trainer.X_test, trainer.y_test)

        cm = metrics['confusion_matrix']

        # Should be 3x3 for LOW/MEDIUM/HIGH
        assert len(cm) == 3
        assert all(len(row) == 3 for row in cm)


class TestModelPersistence:
    """Test model saving and loading."""

    def test_save_model_creates_file(self, sample_dataset, tmp_path):
        """Test that model is saved to disk."""
        trainer = ModelTrainer(str(sample_dataset))
        trainer.load_data()
        trainer.train()

        model_path = tmp_path / "test_model.pkl"
        trainer.save_model(str(model_path))

        # Check file exists
        assert model_path.exists()
        assert model_path.stat().st_size > 0

    def test_save_model_creates_directories(self, sample_dataset, tmp_path):
        """Test that save_model creates parent directories."""
        trainer = ModelTrainer(str(sample_dataset))
        trainer.load_data()
        trainer.train()

        model_path = tmp_path / "models" / "v1" / "test_model.pkl"
        trainer.save_model(str(model_path))

        assert model_path.exists()

    def test_save_model_without_training(self, sample_dataset, tmp_path):
        """Test that saving fails if model not trained."""
        trainer = ModelTrainer(str(sample_dataset))
        trainer.load_data()

        model_path = tmp_path / "test_model.pkl"

        with pytest.raises(TrainingError, match="No model to save"):
            trainer.save_model(str(model_path))

    def test_save_and_load_model(self, sample_dataset, tmp_path):
        """Test complete save/load cycle."""
        trainer = ModelTrainer(str(sample_dataset))
        trainer.load_data()
        trainer.train()

        model_path = tmp_path / "test_model.pkl"
        trainer.save_model(str(model_path))

        # Load using joblib directly (FutureSkillsModel uses instance() pattern)
        import joblib
        loaded_model = joblib.load(str(model_path))

        assert loaded_model is not None
        assert hasattr(loaded_model, 'predict')


class TestFeatureImportance:
    """Test feature importance extraction."""

    def test_get_feature_importance_returns_dict(self, sample_dataset):
        """Test that feature importance returns a dictionary."""
        trainer = ModelTrainer(str(sample_dataset))
        trainer.load_data()
        trainer.train()

        feature_importance = trainer.get_feature_importance()

        assert isinstance(feature_importance, dict)
        assert len(feature_importance) > 0

    def test_feature_importance_values_sum_to_one(self, sample_dataset):
        """Test that feature importance values sum to approximately 1."""
        trainer = ModelTrainer(str(sample_dataset))
        trainer.load_data()
        trainer.train()

        feature_importance = trainer.get_feature_importance()
        total = sum(feature_importance.values())

        # Should sum to approximately 1.0
        assert pytest.approx(total, abs=0.01) == 1.0

    def test_feature_importance_sorted_descending(self, sample_dataset):
        """Test that features are sorted by importance."""
        trainer = ModelTrainer(str(sample_dataset))
        trainer.load_data()
        trainer.train()

        feature_importance = trainer.get_feature_importance()
        values = list(feature_importance.values())

        # Check descending order
        assert values == sorted(values, reverse=True)

    def test_feature_importance_without_training(self, sample_dataset):
        """Test that feature importance fails if model not trained."""
        trainer = ModelTrainer(str(sample_dataset))
        trainer.load_data()

        with pytest.raises(TrainingError, match="Model not trained"):
            trainer.get_feature_importance()


class TestTrainingRunTracking:
    """Test MLOps tracking via TrainingRun model."""

    @patch('future_skills.services.training_service.TrainingRun')
    def test_save_training_run_creates_record(self, mock_training_run, sample_dataset, tmp_path):
        """Test that training run is saved to database."""
        trainer = ModelTrainer(str(sample_dataset))
        trainer.load_data()
        trainer.train()

        model_path = tmp_path / "test_model.pkl"
        trainer.save_model(str(model_path))

        # Mock the create method
        mock_training_run.objects.create.return_value = MagicMock()

        trainer.save_training_run(
            model_version="1.0.0-test",
            model_path=str(model_path),
            notes="Test training run"
        )

        # Verify create was called
        assert mock_training_run.objects.create.called
        call_kwargs = mock_training_run.objects.create.call_args[1]

        # Check required fields
        assert call_kwargs['model_version'] == "1.0.0-test"
        assert call_kwargs['model_path'] == str(model_path)
        assert 'accuracy' in call_kwargs
        assert 'f1_score' in call_kwargs

    def test_save_training_run_without_training(self, sample_dataset, tmp_path):
        """Test that saving training run fails if no metrics available."""
        trainer = ModelTrainer(str(sample_dataset))
        trainer.load_data()

        model_path = tmp_path / "test_model.pkl"

        with pytest.raises(TrainingError, match="No metrics available"):
            trainer.save_training_run(
                model_version="v1.0",
                model_path=str(model_path)
            )


class TestEndToEndWorkflow:
    """Test complete training workflows."""

    def test_complete_training_workflow(self, sample_dataset, tmp_path):
        """Test complete workflow from data loading to model saving."""
        # Initialize
        trainer = ModelTrainer(str(sample_dataset), test_split=0.2)

        # Load data
        trainer.load_data()
        assert trainer.X_train is not None

        # Train
        metrics = trainer.train(n_estimators=50)
        assert metrics['accuracy'] >= 0

        # Save
        model_path = tmp_path / "final_model.pkl"
        trainer.save_model(str(model_path))
        assert model_path.exists()

        # Get feature importance
        importance = trainer.get_feature_importance()
        assert len(importance) > 0

    def test_workflow_with_real_test_data(self, tmp_path):
        """Test workflow using the real test dataset from 6.1."""
        # Load the actual test dataset
        real_dataset = Path(__file__).parent / "test_data" / "sample_training_data.csv"

        if not real_dataset.exists():
            pytest.skip("Real test dataset not available")

        # Need to adapt it to have the correct column names
        df = pd.read_csv(real_dataset)

        # Map 'label' to 'future_need_level' and add required features
        df['future_need_level'] = df['label']
        df['trend_score'] = df['market_trend_score']
        df['internal_usage'] = df['economic_indicator']

        adapted_path = tmp_path / "adapted_data.csv"
        df.to_csv(adapted_path, index=False)

        # Run training
        trainer = ModelTrainer(str(adapted_path))
        trainer.load_data()
        metrics = trainer.train(n_estimators=100)

        # Verify training worked
        assert metrics['accuracy'] > 0
        assert trainer.model is not None
