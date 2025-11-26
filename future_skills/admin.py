from django.contrib import admin
from .models import Skill, JobRole, MarketTrend, FutureSkillPrediction, PredictionRun


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
    list_display = ("run_date", "total_predictions", "short_description")
    date_hierarchy = "run_date"

    def short_description(self, obj):
        if not obj.description:
            return "-"
        return (obj.description[:60] + "...") if len(obj.description) > 60 else obj.description

    short_description.short_description = "Description"
