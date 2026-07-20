# future_skills/api/urls.py

"""URL configuration for the future_skills API.

Defines all REST API endpoints for future skills predictions, employee management,
market trends, economic reports, HR recommendations, and ML model training.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .demand import DemandBySkillAPIView, DemandHistoryAPIView
from .views import (
    BulkEmployeeImportAPIView,
    BulkEmployeeUploadAPIView,
    BulkPredictAPIView,
    DashboardScopeAPIView,
    DriftReportAPIView,
    DriftSeriesAPIView,
    EconomicReportListAPIView,
    EmployeeViewSet,
    EvaluationMetricsAPIView,
    FrontendConfusionMatrixAPIView,
    FrontendPredictionListAPIView,
    FrontendTaxonomyAPIView,
    FrontendJobAPIView,
    FrontendJobDetailAPIView,
    LabelsPredAlignmentAPIView,
    SnapshotSummaryAPIView,
    MetricsHistoryAPIView,
    FutureSkillPredictionListAPIView,
    FutureSkillTopRankingsAPIView,
    HRInvestmentRecommendationListAPIView,
    MarketTrendListAPIView,
    PredictSkillsAPIView,
    RecalculateFutureSkillsAPIView,
    PredictionRunDetailAPIView,
    DriftAPIView,
    RecommendSkillsAPIView,
    TrainingRunDetailAPIView,
    TrainingRunListAPIView,
    TrainModelAPIView,
    TrainingDatasetUploadAPIView,
)

# Router for ViewSets
router = DefaultRouter()
router.register(r"employees", EmployeeViewSet, basename="employee")

urlpatterns = [
    # Frontend-friendly read-only endpoints
    # Stable cross-service demand API (ADR-007; consumed by career-sim)
    path("demand/", DemandBySkillAPIView.as_view(), name="demand-by-skill"),
    path("demand/history/", DemandHistoryAPIView.as_view(), name="demand-history"),

    path("frontend/drift-report/", DriftReportAPIView.as_view(), name="frontend-drift-report"),
    path("frontend/confusion-matrix/", FrontendConfusionMatrixAPIView.as_view(), name="frontend-confusion-matrix"),
    path("frontend/evaluation-metrics/", EvaluationMetricsAPIView.as_view(), name="frontend-evaluation-metrics"),
    path("frontend/taxonomy/", FrontendTaxonomyAPIView.as_view(), name="frontend-taxonomy"),
    path("frontend/predictions/", FrontendPredictionListAPIView.as_view(), name="frontend-predictions"),
    path("frontend/snapshots/", SnapshotSummaryAPIView.as_view(), name="frontend-snapshots"),
    path("frontend/labels-vs-preds/", LabelsPredAlignmentAPIView.as_view(), name="frontend-labels-vs-preds"),
    path("frontend/metrics-history/", MetricsHistoryAPIView.as_view(), name="frontend-metrics-history"),
    path("frontend/drift-series/", DriftSeriesAPIView.as_view(), name="frontend-drift-series"),
    path("frontend/dashboard-scope/", DashboardScopeAPIView.as_view(), name="frontend-dashboard-scope"),
    path("frontend/jobs/", FrontendJobAPIView.as_view(), name="frontend-jobs"),
    path("frontend/jobs/<str:job_id>/", FrontendJobDetailAPIView.as_view(), name="frontend-jobs-detail"),
    # Include router URLs (employee-list, employee-detail, etc.)
    path("", include(router.urls)),
    # Default predictions endpoint (Accept header/default version = v2)
    path(
        "predictions/",
        FutureSkillPredictionListAPIView.as_view(),
        name="predictions-default",
    ),
    path(
        "predictions/top-rankings/",
        FutureSkillTopRankingsAPIView.as_view(),
        name="predictions-top-rankings",
    ),
    # Liste des prédictions
    path(
        "future-skills/",
        FutureSkillPredictionListAPIView.as_view(),
        name="future-skills-list",
    ),
    path(
        "future-skills/top-rankings/",
        FutureSkillTopRankingsAPIView.as_view(),
        name="future-skills-top-rankings",
    ),
    # Recalcul des prédictions
    path(
        "future-skills/recalculate/",
        RecalculateFutureSkillsAPIView.as_view(),
        name="future-skills-recalculate",
    ),
    path("future-skills/prediction-runs/<int:pk>/", PredictionRunDetailAPIView.as_view(), name="prediction-run-detail"),
    path("future-skills/drift/", DriftAPIView.as_view(), name="future-skills-drift"),
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
    # ========================================================================
    # Training API Endpoints (Sections 2.4 & 2.6)
    # ========================================================================
    # Train new model (Section 2.4: training/train/)
    path(
        "training/train/",
        TrainModelAPIView.as_view(),
        name="training-train-model",
    ),
    path("training/dataset/", TrainingDatasetUploadAPIView.as_view(), name="training-dataset-upload"),
    path("future-skills/training/dataset/", TrainingDatasetUploadAPIView.as_view(), name="future-skills-training-dataset-upload"),
    # Train new model - Alternative endpoint (Section 2.6: training/start/)
    path(
        "training/start/",
        TrainModelAPIView.as_view(),
        name="training-start",
    ),
    # List all training runs with pagination (Section 2.6)
    path(
        "training/runs/",
        TrainingRunListAPIView.as_view(),
        name="training-runs",
    ),
    # Get specific training run details (Section 2.6)
    path(
        "training/runs/<int:pk>/",
        TrainingRunDetailAPIView.as_view(),
        name="training-run-detail",
    ),
]
