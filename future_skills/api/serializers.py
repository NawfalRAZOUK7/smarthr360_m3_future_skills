# future_skills/api/serializers.py

from rest_framework import serializers

from ..models import (
    Skill,
    JobRole,
    MarketTrend,
    FutureSkillPrediction,
    EconomicReport,
    HRInvestmentRecommendation,
    Employee,
)

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
            raise serializers.ValidationError(f"Employee with id {value} does not exist.")
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
            raise serializers.ValidationError(f"Employee with id {value} does not exist.")
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
        existing_ids = set(Employee.objects.filter(pk__in=value).values_list('pk', flat=True))
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
        help_text="List of employees to import"
    )
    auto_predict = serializers.BooleanField(
        default=True,
        help_text="Automatically generate predictions after import"
    )
    horizon_years = serializers.IntegerField(
        default=5,
        min_value=1,
        max_value=10,
        help_text="Prediction horizon in years"
    )

    def validate_employees(self, value):
        """
        Validate employee data:
        - Check for duplicate emails within the import batch
        - Validate that all job_roles exist
        """
        emails = []
        errors = []

        for idx, employee_data in enumerate(value):
            # Check for duplicate emails in batch
            email = employee_data.get('email')
            if email:
                if email in emails:
                    errors.append({
                        'index': idx,
                        'email': email,
                        'error': f"Duplicate email '{email}' found in import batch"
                    })
                emails.append(email)

            # Check if job_role exists (if provided)
            job_role_id = employee_data.get('job_role_id')
            if job_role_id:
                try:
                    JobRole.objects.get(pk=job_role_id)
                except JobRole.DoesNotExist:
                    errors.append({
                        'index': idx,
                        'email': email,
                        'error': f"JobRole with id {job_role_id} does not exist"
                    })

        if errors:
            raise serializers.ValidationError({
                'validation_errors': errors,
                'message': 'One or more employees failed validation'
            })

        return value

    def create(self, validated_data):
        """
        Bulk create/update employees and optionally generate predictions.
        Returns summary of operation.
        """
        from ..models import Employee
        from django.db import transaction

        employees_data = validated_data['employees']
        auto_predict = validated_data['auto_predict']
        horizon_years = validated_data['horizon_years']

        created = []
        updated = []
        failed = []

        with transaction.atomic():
            for employee_data in employees_data:
                try:
                    email = employee_data.get('email')

                    # Try to find existing employee by email
                    existing_employee = Employee.objects.filter(email=email).first()

                    if existing_employee:
                        # Update existing employee
                        for field, value in employee_data.items():
                            if field != 'id':  # Don't update ID
                                setattr(existing_employee, field, value)
                        existing_employee.save()
                        updated.append({
                            'id': existing_employee.id,
                            'email': existing_employee.email,
                            'name': existing_employee.name
                        })
                    else:
                        # Create new employee
                        new_employee = Employee.objects.create(**employee_data)
                        created.append({
                            'id': new_employee.id,
                            'email': new_employee.email,
                            'name': new_employee.name
                        })

                except Exception as e:
                    failed.append({
                        'email': employee_data.get('email'),
                        'error': str(e)
                    })

        # Generate predictions if requested
        predictions_generated = 0
        if auto_predict:
            from ..services.prediction_engine import recalculate_predictions

            all_employees = created + updated
            for emp_data in all_employees:
                try:
                    employee = Employee.objects.get(pk=emp_data['id'])
                    if employee.job_role:
                        recalculate_predictions(
                            job_role_id=employee.job_role.id,
                            horizon_years=horizon_years
                        )
                        predictions_generated += 1
                except Exception:
                    pass  # Silently fail prediction generation

        return {
            'summary': {
                'total': len(employees_data),
                'created': len(created),
                'updated': len(updated),
                'failed': len(failed)
            },
            'created': created,
            'updated': updated,
            'failed': failed,
            'predictions_generated': predictions_generated if auto_predict else None
        }
