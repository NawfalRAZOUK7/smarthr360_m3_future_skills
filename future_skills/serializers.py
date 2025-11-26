# future_skills/serializers.py

from rest_framework import serializers

from .models import Skill, JobRole, MarketTrend, FutureSkillPrediction


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
