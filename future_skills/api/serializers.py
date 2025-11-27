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
