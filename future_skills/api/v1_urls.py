"""
API v1 URLs (Deprecated)

This is the original API version, now deprecated.
Will be sunset on 2026-06-01.

Please migrate to v2: /api/v2/
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    BulkEmployeeImportAPIView,
    BulkEmployeeUploadAPIView,
    BulkPredictAPIView,
    EconomicReportListAPIView,
    EmployeeViewSet,
    FutureSkillPredictionListAPIView,
    HRInvestmentRecommendationListAPIView,
    MarketTrendListAPIView,
    PredictSkillsAPIView,
    RecalculateFutureSkillsAPIView,
    RecommendSkillsAPIView,
    TrainingRunDetailAPIView,
    TrainingRunListAPIView,
    TrainModelAPIView,
)

app_name = "v1"

# Router for ViewSets
router = DefaultRouter()
router.register(r"employees", EmployeeViewSet, basename="employee")

urlpatterns = [
    # Include router URLs
    path("", include(router.urls)),
    # Predictions
    path(
        "future-skills/",
        FutureSkillPredictionListAPIView.as_view(),
        name="future-skills-list",
    ),
    path(
        "future-skills/recalculate/",
        RecalculateFutureSkillsAPIView.as_view(),
        name="future-skills-recalculate",
    ),
    # Market data
    path(
        "market-trends/",
        MarketTrendListAPIView.as_view(),
        name="market-trends-list",
    ),
    path(
        "economic-reports/",
        EconomicReportListAPIView.as_view(),
        name="economic-reports-list",
    ),
    # HR recommendations
    path(
        "hr-investment-recommendations/",
        HRInvestmentRecommendationListAPIView.as_view(),
        name="hr-investment-recommendations-list",
    ),
    # ML operations
    path(
        "predict-skills/",
        PredictSkillsAPIView.as_view(),
        name="predict-skills",
    ),
    path(
        "recommend-skills/",
        RecommendSkillsAPIView.as_view(),
        name="recommend-skills",
    ),
    path(
        "bulk-predict/",
        BulkPredictAPIView.as_view(),
        name="bulk-predict",
    ),
    # Bulk operations
    path(
        "bulk-import/employees/",
        BulkEmployeeImportAPIView.as_view(),
        name="employee-bulk-import",
    ),
    path(
        "bulk-upload/employees/",
        BulkEmployeeUploadAPIView.as_view(),
        name="employee-bulk-upload",
    ),
    # Training
    path(
        "train-model/",
        TrainModelAPIView.as_view(),
        name="train-model",
    ),
    path(
        "training-runs/",
        TrainingRunListAPIView.as_view(),
        name="training-runs-list",
    ),
    path(
        "training-runs/<int:pk>/",
        TrainingRunDetailAPIView.as_view(),
        name="training-runs-detail",
    ),
]
