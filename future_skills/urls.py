# future_skills/urls.py

from django.urls import path

from .views import (
    FutureSkillPredictionListAPIView,
    RecalculateFutureSkillsAPIView,
    MarketTrendListAPIView,
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
]
