from django.contrib import admin
from .models import (
    Skill,
    JobRole,
    MarketTrend,
    FutureSkillPrediction,
    PredictionRun,
    EconomicReport,   # ⬅️ ajoute ceci
    HRInvestmentRecommendation,  # ⬅️ ajoute ceci
    Employee,  # ⬅️ nouveau
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
    list_display = ("job_role", "skill", "horizon_years", "level", "score", "created_at")
    search_fields = ("job_role__name", "skill__name")
    list_filter = ("horizon_years", "level", "job_role", "skill")
    autocomplete_fields = ("job_role", "skill")
    date_hierarchy = "created_at"


@admin.register(PredictionRun)
class PredictionRunAdmin(admin.ModelAdmin):
    list_display = ("run_date", "description", "total_predictions", "run_by", "short_parameters")
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
        return (obj.description[:60] + "...") if len(obj.description) > 60 else obj.description
    short_description.short_description = "Description"


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
    list_display = ("name", "email", "department", "position", "job_role", "date_joined")
    search_fields = ("name", "email", "department", "position", "job_role__name")
    list_filter = ("department", "job_role", "date_joined")
    autocomplete_fields = ("job_role",)
    date_hierarchy = "date_joined"
