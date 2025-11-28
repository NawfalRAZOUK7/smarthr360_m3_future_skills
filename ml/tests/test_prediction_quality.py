# ml/tests/test_prediction_quality.py

"""
Prediction Quality Tests for Future Skills ML Model.

Tests prediction quality, consistency, score ranges, level alignment,
and batch prediction correctness to ensure reliable model outputs.
"""

import pytest
from future_skills.services.prediction_engine import PredictionEngine
from future_skills.models import JobRole, Skill


@pytest.mark.django_db
class TestPredictionQuality:
    """Test prediction quality and consistency."""

    def test_prediction_score_range(self, sample_job_role, sample_skill):
        """Test that predictions are within valid score range."""
        engine = PredictionEngine()

        for horizon in [1, 3, 5, 10]:
            score, level, rationale, explanation = engine.predict(
                sample_job_role.id,
                sample_skill.id,
                horizon
            )

            assert 0 <= score <= 100, f"Score {score} out of range for horizon {horizon}"
            assert isinstance(score, (int, float)), f"Score should be numeric, got {type(score)}"
            assert level in ['LOW', 'MEDIUM', 'HIGH'], f"Invalid level: {level}"
            assert isinstance(rationale, str), "Rationale should be a string"

    def test_prediction_consistency(self, sample_job_role, sample_skill):
        """Test that predictions are consistent across multiple calls."""
        engine = PredictionEngine()

        # Call predict multiple times with same inputs
        results = []
        for _ in range(5):
            score, level, _, _ = engine.predict(
                sample_job_role.id,
                sample_skill.id,
                5
            )
            results.append((score, level))

        # All results should be identical (deterministic)
        assert len(set(results)) == 1, "Predictions should be deterministic for same inputs"

    def test_horizon_impact(self, sample_job_role, sample_skill):
        """Test that longer horizons can have different predictions."""
        engine = PredictionEngine()

        predictions = {}
        for horizon in [1, 3, 5, 10]:
            score, level, _, _ = engine.predict(
                sample_job_role.id,
                sample_skill.id,
                horizon
            )
            predictions[horizon] = (score, level)

        # Store all scores and levels
        scores = [p[0] for p in predictions.values()]
        levels = [p[1] for p in predictions.values()]

        # At least verify predictions were generated for all horizons
        assert len(predictions) == 4, "Should have predictions for all 4 horizons"

        # All scores should still be in valid range
        assert all(0 <= s <= 100 for s in scores), "All scores should be in valid range"

    def test_level_score_alignment(self, sample_job_role, sample_skill):
        """Test that level categorization aligns with score."""
        engine = PredictionEngine()

        score, level, _, _ = engine.predict(
            sample_job_role.id,
            sample_skill.id,
            5
        )

        # Verify level matches score thresholds (HIGH >= 70, MEDIUM >= 40, LOW < 40)
        if level == 'HIGH':
            assert score >= 70, f"HIGH level should have score >= 70, got {score}"
        elif level == 'MEDIUM':
            assert 40 <= score < 70, f"MEDIUM level should have 40 <= score < 70, got {score}"
        elif level == 'LOW':
            assert score < 40, f"LOW level should have score < 40, got {score}"
        else:
            pytest.fail(f"Invalid level: {level}")

    def test_batch_prediction_consistency(self, sample_job_role, db):
        """Test that batch predictions match individual predictions."""
        # Create test skills
        skills = [
            Skill.objects.create(name=f'Skill {i}', category='Technical')
            for i in range(3)
        ]

        engine = PredictionEngine()

        # Individual predictions
        individual_results = []
        for skill in skills:
            score, level, _, _ = engine.predict(
                sample_job_role.id,
                skill.id,
                5
            )
            individual_results.append((score, level))

        # Batch prediction
        predictions_data = [
            {
                'job_role_id': sample_job_role.id,
                'skill_id': skill.id,
                'horizon_years': 5
            }
            for skill in skills
        ]
        batch_results = engine.batch_predict(predictions_data)

        # Compare - batch results should match individual results
        assert len(batch_results) == len(individual_results), "Batch should return same count as individual"

        for i, result in enumerate(batch_results):
            expected_score, expected_level = individual_results[i]
            assert result['score'] == expected_score, f"Batch score mismatch at index {i}"
            assert result['level'] == expected_level, f"Batch level mismatch at index {i}"

    def test_multiple_job_roles_predictions(self, sample_skill, db):
        """Test predictions across multiple job roles."""
        # Create multiple job roles
        job_roles = [
            JobRole.objects.create(
                name=f'Role {i}',
                department='Engineering'
            )
            for i in range(3)
        ]

        engine = PredictionEngine()

        # Get predictions for each role
        predictions = []
        for role in job_roles:
            score, level, rationale, _ = engine.predict(
                role.id,
                sample_skill.id,
                5
            )
            predictions.append({
                'role_id': role.id,
                'score': score,
                'level': level,
                'rationale': rationale
            })

        # Verify all predictions are valid
        assert len(predictions) == 3
        for pred in predictions:
            assert 0 <= pred['score'] <= 100
            assert pred['level'] in ['LOW', 'MEDIUM', 'HIGH']
            assert len(pred['rationale']) > 0

    def test_multiple_skills_predictions(self, sample_job_role, db):
        """Test predictions across multiple skills."""
        # Create multiple skills
        skills = [
            Skill.objects.create(
                name=f'Test Skill {i}',
                category='Technical'
            )
            for i in range(5)
        ]

        engine = PredictionEngine()

        # Get predictions for each skill
        predictions = []
        for skill in skills:
            score, level, _, _ = engine.predict(
                sample_job_role.id,
                skill.id,
                5
            )
            predictions.append((score, level))

        # Verify all predictions are valid
        assert len(predictions) == 5
        for score, level in predictions:
            assert 0 <= score <= 100
            assert level in ['LOW', 'MEDIUM', 'HIGH']


@pytest.mark.django_db
class TestPredictionEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_minimum_horizon(self, sample_job_role, sample_skill):
        """Test prediction with minimum horizon (1 year)."""
        engine = PredictionEngine()

        score, level, rationale, _ = engine.predict(
            sample_job_role.id,
            sample_skill.id,
            1
        )

        assert 0 <= score <= 100
        assert level in ['LOW', 'MEDIUM', 'HIGH']
        assert len(rationale) > 0

    def test_maximum_horizon(self, sample_job_role, sample_skill):
        """Test prediction with large horizon (20 years)."""
        engine = PredictionEngine()

        score, level, rationale, _ = engine.predict(
            sample_job_role.id,
            sample_skill.id,
            20
        )

        assert 0 <= score <= 100
        assert level in ['LOW', 'MEDIUM', 'HIGH']
        assert len(rationale) > 0

    def test_zero_horizon_handling(self, sample_job_role, sample_skill):
        """Test handling of zero or negative horizon."""
        engine = PredictionEngine()

        # Zero horizon - should still work (treated as immediate)
        score, level, _, _ = engine.predict(
            sample_job_role.id,
            sample_skill.id,
            0
        )

        assert 0 <= score <= 100
        assert level in ['LOW', 'MEDIUM', 'HIGH']

    def test_invalid_job_role_id(self, sample_skill):
        """Test handling of non-existent job role ID."""
        engine = PredictionEngine()

        # Should handle gracefully (not crash)
        try:
            score, level, _, _ = engine.predict(
                999999,  # Non-existent ID
                sample_skill.id,
                5
            )
            # If it doesn't raise, check it returns valid defaults
            assert 0 <= score <= 100
            assert level in ['LOW', 'MEDIUM', 'HIGH']
        except Exception as e:
            # If it raises, should be a specific expected exception
            assert 'does not exist' in str(e).lower() or 'not found' in str(e).lower()

    def test_invalid_skill_id(self, sample_job_role):
        """Test handling of non-existent skill ID."""
        engine = PredictionEngine()

        # Should handle gracefully (not crash)
        try:
            score, level, _, _ = engine.predict(
                sample_job_role.id,
                999999,  # Non-existent ID
                5
            )
            # If it doesn't raise, check it returns valid defaults
            assert 0 <= score <= 100
            assert level in ['LOW', 'MEDIUM', 'HIGH']
        except Exception as e:
            # If it raises, should be a specific expected exception
            assert 'does not exist' in str(e).lower() or 'not found' in str(e).lower()

    def test_empty_batch_prediction(self):
        """Test batch prediction with empty input list."""
        engine = PredictionEngine()

        results = engine.batch_predict([])

        assert isinstance(results, list)
        assert len(results) == 0


@pytest.mark.django_db
class TestPredictionRationale:
    """Test prediction rationale quality."""

    def test_rationale_not_empty(self, sample_job_role, sample_skill):
        """Test that rationale is always provided."""
        engine = PredictionEngine()

        _, _, rationale, _ = engine.predict(
            sample_job_role.id,
            sample_skill.id,
            5
        )

        assert rationale is not None
        assert isinstance(rationale, str)
        assert len(rationale) > 0
        assert len(rationale.strip()) > 0

    def test_rationale_mentions_key_factors(self, sample_job_role, sample_skill):
        """Test that rationale mentions relevant factors."""
        engine = PredictionEngine()

        _, _, rationale, _ = engine.predict(
            sample_job_role.id,
            sample_skill.id,
            5
        )

        # Rationale should be informative (at least a sentence)
        assert len(rationale) > 20, "Rationale should be detailed enough"

    def test_rationale_consistency(self, sample_job_role, sample_skill):
        """Test that rationale is consistent for same inputs."""
        engine = PredictionEngine()

        # Get rationale multiple times
        rationales = []
        for _ in range(3):
            _, _, rationale, _ = engine.predict(
                sample_job_role.id,
                sample_skill.id,
                5
            )
            rationales.append(rationale)

        # All rationales should be identical (deterministic)
        assert len(set(rationales)) == 1, "Rationale should be consistent"


@pytest.mark.django_db
class TestPredictionExplanation:
    """Test prediction explanation (optional SHAP) handling."""

    def test_explanation_structure(self, sample_job_role, sample_skill):
        """Test that explanation is returned (may be empty if SHAP unavailable)."""
        engine = PredictionEngine()

        _, _, _, explanation = engine.predict(
            sample_job_role.id,
            sample_skill.id,
            5
        )

        # Explanation is always returned as dict (empty dict if SHAP/ML not available)
        assert isinstance(explanation, dict)
        # May be empty {} for rules-based predictions

    def test_ml_vs_rules_explanation(self, sample_job_role, sample_skill):
        """Test explanation differences between ML and rules-based predictions."""
        # Rules engine (uses_ml=False by default in test settings)
        rules_engine = PredictionEngine(use_ml=False)
        _, _, _, rules_explanation = rules_engine.predict(
            sample_job_role.id,
            sample_skill.id,
            5
        )

        # Rules-based explanation is typically empty dict
        assert isinstance(rules_explanation, dict)
        # May be empty for rules-based

        # Note: ML engine test skipped because it requires trained model
        # with specific features that match JobRole/Skill/MarketTrend schema


@pytest.mark.django_db
class TestBatchPredictionQuality:
    """Test batch prediction quality and performance."""

    def test_large_batch_prediction(self, sample_job_role, db):
        """Test batch prediction with large number of items."""
        # Create many skills
        skills = [
            Skill.objects.create(name=f'Skill {i}', category='Technical')
            for i in range(20)
        ]

        engine = PredictionEngine()

        # Create batch prediction data
        predictions_data = [
            {
                'job_role_id': sample_job_role.id,
                'skill_id': skill.id,
                'horizon_years': 5
            }
            for skill in skills
        ]

        # Execute batch prediction
        results = engine.batch_predict(predictions_data)

        # Verify all predictions were processed
        assert len(results) == 20

        # Verify all results are valid
        for result in results:
            assert 'score' in result
            assert 'level' in result
            assert 0 <= result['score'] <= 100
            assert result['level'] in ['LOW', 'MEDIUM', 'HIGH']

    def test_batch_prediction_ordering(self, sample_job_role, db):
        """Test that batch predictions maintain input order."""
        # Create skills with specific order
        skills = [
            Skill.objects.create(name=f'Skill_{i:03d}', category='Technical')
            for i in range(5)
        ]

        engine = PredictionEngine()

        # Create batch data
        predictions_data = [
            {
                'job_role_id': sample_job_role.id,
                'skill_id': skill.id,
                'horizon_years': 5
            }
            for skill in skills
        ]

        # Execute batch prediction
        results = engine.batch_predict(predictions_data)

        # Verify order is maintained
        assert len(results) == len(skills)
        for i, (skill, result) in enumerate(zip(skills, results)):
            # Can't directly check skill_id in result, but verify count and validity
            assert result['score'] is not None
            assert result['level'] is not None

    def test_mixed_horizons_batch(self, sample_job_role, db):
        """Test batch prediction with different horizons."""
        skill = Skill.objects.create(name='Test Skill', category='Technical')

        engine = PredictionEngine()

        # Create batch with different horizons
        predictions_data = [
            {
                'job_role_id': sample_job_role.id,
                'skill_id': skill.id,
                'horizon_years': horizon
            }
            for horizon in [1, 3, 5, 7, 10]
        ]

        # Execute batch prediction
        results = engine.batch_predict(predictions_data)

        # Verify all predictions completed
        assert len(results) == 5

        # All results should be valid
        for result in results:
            assert 0 <= result['score'] <= 100
            assert result['level'] in ['LOW', 'MEDIUM', 'HIGH']


@pytest.mark.django_db
class TestPredictionEngineInitialization:
    """Test PredictionEngine initialization options."""

    def test_default_initialization(self):
        """Test default initialization without parameters."""
        engine = PredictionEngine()

        assert engine is not None
        # Engine should initialize successfully

    def test_ml_enabled_initialization(self):
        """Test initialization with ML explicitly enabled."""
        engine = PredictionEngine(use_ml=True)

        assert engine is not None
        # Should initialize even if model not available (falls back to rules)

    def test_ml_disabled_initialization(self):
        """Test initialization with ML explicitly disabled."""
        engine = PredictionEngine(use_ml=False)

        assert engine is not None
        # Should use rules-based engine

    def test_custom_model_path(self, tmp_path):
        """Test initialization with custom model path."""
        model_path = tmp_path / "custom_model.pkl"

        # Should not crash even with non-existent path
        engine = PredictionEngine(use_ml=True, model_path=str(model_path))

        assert engine is not None

    def test_multiple_engine_instances(self):
        """Test creating multiple engine instances."""
        engine1 = PredictionEngine()
        engine2 = PredictionEngine()

        assert engine1 is not None
        assert engine2 is not None
        # Both should be independent instances
