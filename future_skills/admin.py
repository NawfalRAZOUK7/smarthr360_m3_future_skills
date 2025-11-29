from django.contrib import admin
from .models import (
    Skill,
    JobRole,
    MarketTrend,
    FutureSkillPrediction,
    PredictionRun,
    TrainingRun,
    EconomicReport,
    HRInvestmentRecommendation,
    Employee,
)


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ("name", "category")
    search_fields = ("name", "category")
    list_filter = ("category",)


@admin.register(JobRole)
class JobRoleAdmin(admin.ModelAdmin):
    list_display = ("name", "department")
    search_fields = ("name", "department")
    list_filter = ("department",)


@admin.register(MarketTrend)
class MarketTrendAdmin(admin.ModelAdmin):
    list_display = ("title", "source_name", "year", "sector", "trend_score")
    search_fields = ("title", "source_name", "sector")
    list_filter = ("year", "sector")
    ordering = ("-year", "-trend_score")


@admin.register(FutureSkillPrediction)
class FutureSkillPredictionAdmin(admin.ModelAdmin):
    list_display = (
        "job_role",
        "skill",
        "horizon_years",
        "level",
        "score",
        "created_at",
    )
    search_fields = ("job_role__name", "skill__name")
    list_filter = ("horizon_years", "level", "job_role", "skill")
    autocomplete_fields = ("job_role", "skill")
    date_hierarchy = "created_at"


@admin.register(PredictionRun)
class PredictionRunAdmin(admin.ModelAdmin):
    list_display = (
        "run_date",
        "description",
        "total_predictions",
        "run_by",
        "short_parameters",
    )
    list_filter = ("run_date", "run_by")
    search_fields = ("description", "run_by__username")
    date_hierarchy = "run_date"

    def short_parameters(self, obj):
        if not obj.parameters:
            return "-"
        text = str(obj.parameters)
        return text if len(text) < 80 else text[:77] + "..."

    short_parameters.short_description = "Paramètres"

    def short_description(self, obj):
        if not obj.description:
            return "-"
        return (
            (obj.description[:60] + "...")
            if len(obj.description) > 60
            else obj.description
        )

    short_description.short_description = "Description"


@admin.register(TrainingRun)
class TrainingRunAdmin(admin.ModelAdmin):
    list_display = (
        "run_date",
        "model_version",
        "status",
        "accuracy",
        "f1_score",
        "initiated_by",
    )
    list_filter = ("status", "run_date")
    readonly_fields = (
        "run_date",
        "training_duration_seconds",
        "accuracy",
        "precision",
        "recall",
        "f1_score",
        "total_samples",
        "train_samples",
        "test_samples",
        "per_class_metrics",
        "features_used",
        "hyperparameters",
    )
    fieldsets = (
        (
            "Basic Info",
            {"fields": ("run_date", "trained_by", "status", "model_version")},
        ),
        ("Dataset", {"fields": ("dataset_path", "total_samples", "test_samples")}),
        ("Metrics", {"fields": ("accuracy", "precision", "recall", "f1_score")}),
        (
            "Advanced",
            {
                "fields": (
                    "hyperparameters",
                    "features_used",
                    "per_class_metrics",
                    "error_message",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    def initiated_by(self, obj):
        """Display the user who initiated the training."""
        return obj.trained_by.username if obj.trained_by else "-"

    initiated_by.short_description = "Initiated By"
    initiated_by.admin_order_field = "trained_by"

    def training_duration(self, obj):
        """Display training duration in human-readable format."""
        seconds = obj.training_duration_seconds
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}m"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}h"

    training_duration.short_description = "Duration"
    training_duration.admin_order_field = "training_duration_seconds"


@admin.register(EconomicReport)
class EconomicReportAdmin(admin.ModelAdmin):
    list_display = ("title", "indicator", "year", "sector", "value")
    list_filter = ("year", "sector")
    search_fields = ("title", "indicator", "source_name")
    date_hierarchy = "created_at"


@admin.register(HRInvestmentRecommendation)
class HRInvestmentRecommendationAdmin(admin.ModelAdmin):
    list_display = (
        "skill",
        "job_role",
        "horizon_years",
        "priority_level",
        "recommended_action",
        "created_at",
    )
    list_filter = (
        "horizon_years",
        "priority_level",
        "recommended_action",
        "skill",
        "job_role",
    )
    search_fields = ("skill__name", "job_role__name")
    date_hierarchy = "created_at"


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "email",
        "department",
        "position",
        "job_role",
        "date_joined",
    )
    search_fields = ("name", "email", "department", "position", "job_role__name")
    list_filter = ("department", "job_role", "date_joined")
    autocomplete_fields = ("job_role",)
    date_hierarchy = "date_joined"
