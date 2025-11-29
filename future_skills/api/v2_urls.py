"""
API v2 URLs (Current)

This is the current API version with enhanced features:
- Improved error handling
- Better pagination (cursor-based available)
- Enhanced filtering and search
- Consistent datetime formatting (ISO 8601)
- Bulk operation optimizations
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from ..views import (
    FutureSkillPredictionListAPIView,
    RecalculateFutureSkillsAPIView,
    MarketTrendListAPIView,
    EconomicReportListAPIView,
    HRInvestmentRecommendationListAPIView,
    EmployeeViewSet,
    PredictSkillsAPIView,
    RecommendSkillsAPIView,
    BulkPredictAPIView,
    BulkEmployeeImportAPIView,
    BulkEmployeeUploadAPIView,
    TrainModelAPIView,
    TrainingRunListAPIView,
    TrainingRunDetailAPIView,
)

app_name = 'v2'

# Router for ViewSets
router = DefaultRouter()
router.register(r"employees", EmployeeViewSet, basename="employee")

urlpatterns = [
    # Include router URLs
    path("", include(router.urls)),

    # Predictions
    path(
        "predictions/",  # v2: renamed from future-skills/
        FutureSkillPredictionListAPIView.as_view(),
        name="predictions-list",
    ),
    path(
        "predictions/recalculate/",
        RecalculateFutureSkillsAPIView.as_view(),
        name="predictions-recalculate",
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
        "recommendations/",  # v2: shortened from hr-investment-recommendations/
        HRInvestmentRecommendationListAPIView.as_view(),
        name="recommendations-list",
    ),

    # ML operations
    path(
        "ml/predict/",  # v2: namespaced under ml/
        PredictSkillsAPIView.as_view(),
        name="ml-predict",
    ),
    path(
        "ml/recommend/",  # v2: namespaced under ml/
        RecommendSkillsAPIView.as_view(),
        name="ml-recommend",
    ),
    path(
        "ml/bulk-predict/",  # v2: namespaced under ml/
        BulkPredictAPIView.as_view(),
        name="ml-bulk-predict",
    ),
    path(
        "ml/train/",  # v2: namespaced under ml/
        TrainModelAPIView.as_view(),
        name="ml-train",
    ),

    # Bulk operations
    path(
        "bulk/employees/import/",  # v2: better organization
        BulkEmployeeImportAPIView.as_view(),
        name="bulk-employees-import",
    ),
    path(
        "bulk/employees/upload/",  # v2: better organization
        BulkEmployeeUploadAPIView.as_view(),
        name="bulk-employees-upload",
    ),

    # Training runs
    path(
        "ml/training-runs/",  # v2: namespaced under ml/
        TrainingRunListAPIView.as_view(),
        name="ml-training-runs-list",
    ),
    path(
        "ml/training-runs/<int:pk>/",  # v2: namespaced under ml/
        TrainingRunDetailAPIView.as_view(),
        name="ml-training-runs-detail",
    ),
]
