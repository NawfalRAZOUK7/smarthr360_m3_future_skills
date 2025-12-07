# future_skills/api/serializers.py

import logging

from django.conf import settings
from django.db import transaction
from rest_framework import serializers

from ..models import (
    EconomicReport,
    Employee,
    FutureSkillPrediction,
    HRInvestmentRecommendation,
    JobRole,
    MarketTrend,
    Skill,
    TrainingRun,
)

logger = logging.getLogger(__name__)


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ["id", "name", "category", "description"]


class JobRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobRole
        fields = ["id", "name", "department", "description"]


class MarketTrendSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketTrend
        fields = [
            "id",
            "title",
            "source_name",
            "year",
            "sector",
            "trend_score",
            "description",
            "created_at",
        ]


class EconomicReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = EconomicReport
        fields = [
            "id",
            "title",
            "source_name",
            "year",
            "indicator",
            "value",
            "sector",
            "created_at",
        ]


class FutureSkillPredictionSerializer(serializers.ModelSerializer):
    job_role = JobRoleSerializer(read_only=True)
    skill = SkillSerializer(read_only=True)

    # Optionnel : exposer aussi les IDs pour un futur POST/PUT si besoin
    job_role_id = serializers.PrimaryKeyRelatedField(
        source="job_role",
        queryset=JobRole.objects.all(),
        write_only=True,
        required=False,
    )
    skill_id = serializers.PrimaryKeyRelatedField(
        source="skill",
        queryset=Skill.objects.all(),
        write_only=True,
        required=False,
    )

    class Meta:
        model = FutureSkillPrediction
        fields = [
            "id",
            "job_role",
            "skill",
            "job_role_id",
            "skill_id",
            "horizon_years",
            "score",
            "level",
            "rationale",
            "created_at",
        ]


class HRInvestmentRecommendationSerializer(serializers.ModelSerializer):
    skill = SkillSerializer(read_only=True)
    job_role = JobRoleSerializer(read_only=True)

    class Meta:
        model = HRInvestmentRecommendation
        fields = [
            "id",
            "skill",
            "job_role",
            "horizon_years",
            "priority_level",
            "recommended_action",
            "budget_hint",
            "rationale",
            "created_at",
        ]


class EmployeeSerializer(serializers.ModelSerializer):
    job_role = JobRoleSerializer(read_only=True)

    job_role_id = serializers.PrimaryKeyRelatedField(
        source="job_role",
        queryset=JobRole.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Employee
        fields = [
            "id",
            "name",
            "email",
            "department",
            "position",
            "job_role",
            "job_role_id",
            "current_skills",
            "date_joined",
        ]
        read_only_fields = ["date_joined"]


class PredictSkillsRequestSerializer(serializers.Serializer):
    """
    Input serializer for skill prediction endpoint.
    """

    employee_id = serializers.IntegerField(required=True)
    current_skills = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
    )
    department = serializers.CharField(required=False, allow_blank=True)

    def validate_employee_id(self, value):
        """Validate that the employee exists."""
        from ..models import Employee

        try:
            Employee.objects.get(pk=value)
        except Employee.DoesNotExist:
            raise serializers.ValidationError(
                f"Employee with id {value} does not exist."
            )
        return value


class PredictSkillsResponseSerializer(serializers.Serializer):
    """
    Output serializer for skill prediction endpoint.
    """

    skill_name = serializers.CharField()
    skill_id = serializers.IntegerField()
    level = serializers.CharField()
    score = serializers.FloatField()
    rationale = serializers.CharField(allow_blank=True)


class RecommendSkillsRequestSerializer(serializers.Serializer):
    """
    Input serializer for skill recommendation endpoint.
    """

    employee_id = serializers.IntegerField(required=True)
    exclude_current = serializers.BooleanField(default=True)

    def validate_employee_id(self, value):
        """Validate that the employee exists."""
        from ..models import Employee

        try:
            Employee.objects.get(pk=value)
        except Employee.DoesNotExist:
            raise serializers.ValidationError(
                f"Employee with id {value} does not exist."
            )
        return value


class BulkPredictRequestSerializer(serializers.Serializer):
    """
    Input serializer for bulk prediction endpoint.
    """

    employee_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=True,
        allow_empty=False,
    )

    def validate_employee_ids(self, value):
        """Validate that all employees exist."""
        from ..models import Employee

        existing_ids = set(
            Employee.objects.filter(pk__in=value).values_list("pk", flat=True)
        )
        missing_ids = set(value) - existing_ids
        if missing_ids:
            raise serializers.ValidationError(
                f"Employees with ids {list(missing_ids)} do not exist."
            )
        return value


class BulkEmployeeImportSerializer(serializers.Serializer):
    """
    Input serializer for bulk employee import endpoint.
    Supports creating/updating multiple employees and optionally generating predictions.
    """

    employees = serializers.ListField(
        child=EmployeeSerializer(),
        allow_empty=False,
        help_text="List of employees to import",
    )
    auto_predict = serializers.BooleanField(
        default=True, help_text="Automatically generate predictions after import"
    )
    horizon_years = serializers.IntegerField(
        default=5, min_value=1, max_value=10, help_text="Prediction horizon in years"
    )

    def validate_employees(self, value):
        """
        Validate employee data:
        - Check for duplicate emails within the import batch
        - Validate that all job_roles exist
        """
        errors = []
        errors.extend(self._collect_duplicate_email_errors(value))
        errors.extend(self._collect_missing_job_role_errors(value))

        if errors:
            raise serializers.ValidationError(
                {
                    "validation_errors": errors,
                    "message": "One or more employees failed validation",
                }
            )

        return value

    def _collect_duplicate_email_errors(self, employees):
        errors = []
        seen_emails = set()

        for idx, employee_data in enumerate(employees):
            email = employee_data.get("email")
            if not email:
                continue
            if email in seen_emails:
                errors.append(
                    {
                        "index": idx,
                        "email": email,
                        "error": f"Duplicate email '{email}' found in import batch",
                    }
                )
            else:
                seen_emails.add(email)

        return errors

    def _collect_missing_job_role_errors(self, employees):
        job_role_ids = {
            employee.get("job_role_id")
            for employee in employees
            if employee.get("job_role_id")
        }

        if not job_role_ids:
            return []

        existing_ids = set(
            JobRole.objects.filter(pk__in=job_role_ids).values_list("id", flat=True)
        )
        missing_ids = job_role_ids - existing_ids

        if not missing_ids:
            return []

        errors = []
        for idx, employee_data in enumerate(employees):
            job_role_id = employee_data.get("job_role_id")
            if job_role_id in missing_ids:
                errors.append(
                    {
                        "index": idx,
                        "email": employee_data.get("email"),
                        "error": f"JobRole with id {job_role_id} does not exist",
                    }
                )

        return errors

    def create(self, validated_data):
        """
        Bulk create/update employees and optionally generate predictions.
        Returns summary of operation.
        """
        employees_data = validated_data["employees"]
        auto_predict = validated_data["auto_predict"]
        horizon_years = validated_data["horizon_years"]

        created, updated, failed = self._upsert_employees(employees_data)

        predictions_generated = (
            self._trigger_prediction_recalculation(horizon_years)
            if auto_predict
            else None
        )

        return {
            "summary": {
                "total": len(employees_data),
                "created": len(created),
                "updated": len(updated),
                "failed": len(failed),
            },
            "created": created,
            "updated": updated,
            "failed": failed,
            "predictions_generated": predictions_generated,
        }

    def _upsert_employees(self, employees_data):
        """Create or update employees inside a single transaction."""

        created = []
        updated = []
        failed = []

        with transaction.atomic():
            for employee_data in employees_data:
                try:
                    employee, was_created = self._persist_employee(employee_data)
                    summary = {
                        "id": employee.id,
                        "email": employee.email,
                        "name": employee.name,
                    }
                    if was_created:
                        created.append(summary)
                    else:
                        updated.append(summary)
                except Exception as exc:  # noqa: BLE001
                    failed.append(
                        {"email": employee_data.get("email"), "error": str(exc)}
                    )

        return created, updated, failed

    def _persist_employee(self, employee_data):
        """Return the saved Employee instance and whether it was created."""

        email = employee_data.get("email")
        existing_employee = Employee.objects.filter(email=email).first()

        if existing_employee:
            for field, value in employee_data.items():
                if field != "id":
                    setattr(existing_employee, field, value)
            existing_employee.save()
            return existing_employee, False

        new_employee = Employee.objects.create(**employee_data)
        return new_employee, True

    def _trigger_prediction_recalculation(self, horizon_years: int) -> int:
        """Kick off a single batch prediction recalculation."""

        from ..services.prediction_engine import recalculate_predictions

        try:
            return recalculate_predictions(
                horizon_years=horizon_years,
                parameters={"trigger": "bulk_employee_import"},
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Failed to generate predictions after bulk import: %s", exc
            )
            return 0


# ============================================================================
# Training API Serializers (Section 2.4)
# ============================================================================


class TrainingRunSerializer(serializers.ModelSerializer):
    """
    Serializer for TrainingRun model - read-only for listing.
    """

    trained_by_username = serializers.CharField(
        source="trained_by.username", read_only=True, allow_null=True
    )

    class Meta:
        model = TrainingRun
        fields = [
            "id",
            "run_date",
            "model_version",
            "status",
            "accuracy",
            "precision",
            "recall",
            "f1_score",
            "training_duration_seconds",
            "trained_by_username",
        ]
        read_only_fields = fields


class TrainingRunDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for TrainingRun - includes all fields.
    """

    trained_by_username = serializers.CharField(
        source="trained_by.username", read_only=True, allow_null=True
    )

    class Meta:
        model = TrainingRun
        fields = [
            "id",
            "run_date",
            "model_version",
            "model_path",
            "dataset_path",
            "status",
            "error_message",
            # Metrics
            "accuracy",
            "precision",
            "recall",
            "f1_score",
            # Dataset info
            "total_samples",
            "train_samples",
            "test_samples",
            "test_split",
            # Training config
            "n_estimators",
            "random_state",
            "hyperparameters",
            "training_duration_seconds",
            # Additional info
            "per_class_metrics",
            "features_used",
            "trained_by_username",
            "notes",
        ]
        read_only_fields = fields


class TrainModelRequestSerializer(serializers.Serializer):
    """
    Request serializer for training a new model.

    Section 2.5: Added async_training parameter for Celery background tasks.
    """

    dataset_path = serializers.CharField(
        required=False,
        default=str(settings.ML_DATASETS_DIR / "future_skills_dataset.csv"),
        help_text="Path to the training dataset CSV file",
    )
    test_split = serializers.FloatField(
        required=False,
        default=0.2,
        min_value=0.1,
        max_value=0.5,
        help_text="Test set split ratio (0.1 to 0.5)",
    )
    hyperparameters = serializers.JSONField(
        required=False,
        default=dict,
        help_text="Model hyperparameters (n_estimators, max_depth, etc.)",
    )
    model_version = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Version identifier (auto-generated if not provided)",
    )
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Optional notes about this training run",
    )
    async_training = serializers.BooleanField(
        required=False,
        default=False,
        help_text="Use Celery for background training (Section 2.5)",
    )

    def validate_hyperparameters(self, value):
        """
        Validate hyperparameters are sensible values.
        """
        if not isinstance(value, dict):
            raise serializers.ValidationError("Hyperparameters must be a dictionary")

        # Validate n_estimators if provided
        if "n_estimators" in value:
            n_est = value["n_estimators"]
            if not isinstance(n_est, int) or n_est < 1 or n_est > 1000:
                raise serializers.ValidationError(
                    "n_estimators must be an integer between 1 and 1000"
                )

        # Validate max_depth if provided
        if "max_depth" in value and value["max_depth"] is not None:
            max_d = value["max_depth"]
            if not isinstance(max_d, int) or max_d < 1 or max_d > 100:
                raise serializers.ValidationError(
                    "max_depth must be an integer between 1 and 100 or null"
                )

        return value


class TrainModelResponseSerializer(serializers.Serializer):
    """
    Response serializer for training endpoint.

    Section 2.5: Added task_id for async Celery tasks.
    """

    training_run_id = serializers.IntegerField(
        help_text="ID of the created TrainingRun record"
    )
    status = serializers.CharField(
        help_text="Training status (RUNNING, COMPLETED, FAILED)"
    )
    message = serializers.CharField(help_text="Human-readable status message")
    model_version = serializers.CharField(
        help_text="Version identifier of the trained model"
    )
    metrics = serializers.JSONField(
        required=False, help_text="Training metrics (if completed synchronously)"
    )
    task_id = serializers.CharField(
        required=False, help_text="Celery task ID (if async_training=true)"
    )


# ============================================================================
# Skill Assignment Serializers (Section 4.1)
# ============================================================================


class AddSkillToEmployeeSerializer(serializers.Serializer):
    """
    Serializer for adding a skill to an employee.

    Validates that the skill_id exists before assignment.
    """

    skill_id = serializers.IntegerField(required=True)

    def validate_skill_id(self, value):
        from ..models import Skill

        try:
            Skill.objects.get(pk=value)
        except Skill.DoesNotExist:
            raise serializers.ValidationError(f"Skill with id {value} does not exist.")
        return value


class RemoveSkillFromEmployeeSerializer(serializers.Serializer):
    """
    Serializer for removing a skill from an employee.
    """

    skill_id = serializers.IntegerField(required=True)


class UpdateEmployeeSkillsSerializer(serializers.Serializer):
    """
    Serializer for updating all employee skills at once.

    Replaces the entire current_skills list with the provided skills.
    """

    current_skills = serializers.ListField(
        child=serializers.CharField(), allow_empty=True
    )
