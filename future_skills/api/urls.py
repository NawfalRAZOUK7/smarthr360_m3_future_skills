# future_skills/api/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
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
)

# Router for ViewSets
router = DefaultRouter()
router.register(r"employees", EmployeeViewSet, basename="employee")

urlpatterns = [
    # Include router URLs (employee-list, employee-detail, etc.)
    path("", include(router.urls)),

    # Liste des prédictions
    path(
        "future-skills/",
        FutureSkillPredictionListAPIView.as_view(),
        name="future-skills-list",
    ),

    # Recalcul des prédictions
    path(
        "future-skills/recalculate/",
        RecalculateFutureSkillsAPIView.as_view(),
        name="future-skills-recalculate",
    ),

    # (Optionnel) Liste des tendances marché
    path(
        "market-trends/",
        MarketTrendListAPIView.as_view(),
        name="market-trends-list",
    ),

    # Liste des rapports Economiques
    path(
        "economic-reports/",
        EconomicReportListAPIView.as_view(),
        name="economic-reports-list",
    ),

    # List of HR Investment Recommendations
    path(
        "hr-investment-recommendations/",
        HRInvestmentRecommendationListAPIView.as_view(),
        name="hr-investment-recommendations-list",
    ),

    # Prediction endpoints
    path(
        "predict-skills/",
        PredictSkillsAPIView.as_view(),
        name="futureskill-predict-skills",
    ),

    # Recommendation endpoints
    path(
        "recommend-skills/",
        RecommendSkillsAPIView.as_view(),
        name="futureskill-recommend-skills",
    ),

    # Bulk prediction endpoint
    path(
        "bulk-predict/",
        BulkPredictAPIView.as_view(),
        name="futureskill-bulk-predict",
    ),

    # Bulk employee import endpoint (JSON data) - placed before router to avoid conflicts
    path(
        "bulk-import/employees/",
        BulkEmployeeImportAPIView.as_view(),
        name="employee-bulk-import",
    ),

    # Bulk employee upload endpoint (File upload)
    path(
        "bulk-upload/employees/",
        BulkEmployeeUploadAPIView.as_view(),
        name="employee-bulk-upload",
    ),
]
