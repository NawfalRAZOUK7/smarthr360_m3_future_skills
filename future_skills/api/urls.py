# future_skills/api/urls.py

from django.urls import path

from .views import (
    FutureSkillPredictionListAPIView,
    RecalculateFutureSkillsAPIView,
    MarketTrendListAPIView,
    EconomicReportListAPIView,  # ⬅️ ajoute ceci
    HRInvestmentRecommendationListAPIView,  # ⬅️
)

urlpatterns = [
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
]
