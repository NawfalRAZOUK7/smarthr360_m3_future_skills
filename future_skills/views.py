# future_skills/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from .models import FutureSkillPrediction, MarketTrend, EconomicReport
from .serializers import (
    FutureSkillPredictionSerializer,
    MarketTrendSerializer,
    EconomicReportSerializer,
)
from .services.prediction_engine import recalculate_predictions
from .permissions import IsHRStaff, IsHRStaffOrManager


class FutureSkillPredictionListAPIView(APIView):
    """
    Liste les prédictions de compétences futures.

    Filtres possibles (query params):
      - job_role_id
      - horizon_years
    Exemple :
      GET /api/future-skills/?job_role_id=1&horizon_years=5
    """

    # DRH + Responsable RH + Manager
    permission_classes = [IsHRStaffOrManager]

    def get(self, request, *args, **kwargs):
        queryset = FutureSkillPrediction.objects.all()

        job_role_id = request.query_params.get("job_role_id")
        horizon_years = request.query_params.get("horizon_years")

        if job_role_id is not None:
            queryset = queryset.filter(job_role_id=job_role_id)

        if horizon_years is not None:
            try:
                horizon = int(horizon_years)
                queryset = queryset.filter(horizon_years=horizon)
            except ValueError:
                return Response(
                    {"detail": "horizon_years must be an integer."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        serializer = FutureSkillPredictionSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RecalculateFutureSkillsAPIView(APIView):
    """
    Recalcule toutes les prédictions FutureSkillPrediction
    via le moteur de règles simple.

    Body JSON optionnel :
      {
        "horizon_years": 5
      }
    """

    # Seulement DRH / Responsable RH (staff RH)
    permission_classes = [IsHRStaff]

    def post(self, request, *args, **kwargs):
        horizon_years = request.data.get("horizon_years", 5)

        try:
            horizon_years = int(horizon_years)
        except (TypeError, ValueError):
            return Response(
                {"detail": "horizon_years must be an integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        total = recalculate_predictions(horizon_years=horizon_years)

        return Response(
            {
                "horizon_years": horizon_years,
                "total_predictions": total,
            },
            status=status.HTTP_200_OK,
        )


class MarketTrendListAPIView(APIView):
    """
    Liste les tendances marché utilisées pour alimenter le module 3.

    Filtres possibles :
      - year
      - sector
    Exemple :
      GET /api/market-trends/?year=2025&sector=Tech
    """

    # DRH + Responsable RH + Manager (lecture)
    permission_classes = [IsHRStaffOrManager]

    def get(self, request, *args, **kwargs):
        queryset = MarketTrend.objects.all()

        year = request.query_params.get("year")
        sector = request.query_params.get("sector")

        if year is not None:
            try:
                year_int = int(year)
                queryset = queryset.filter(year=year_int)
            except ValueError:
                return Response(
                    {"detail": "year must be an integer."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if sector is not None:
            queryset = queryset.filter(sector__iexact=sector)

        serializer = MarketTrendSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class EconomicReportListAPIView(APIView):
    """
    Liste les rapports / indicateurs économiques utilisés par le module 3.

    Filtres possibles :
      - year
      - sector
      - indicator (contient)
    """

    permission_classes = [IsHRStaffOrManager]

    def get(self, request, *args, **kwargs):
        queryset = EconomicReport.objects.all()

        year = request.query_params.get("year")
        sector = request.query_params.get("sector")
        indicator = request.query_params.get("indicator")

        if year is not None:
            try:
                year_int = int(year)
                queryset = queryset.filter(year=year_int)
            except ValueError:
                return Response(
                    {"detail": "year must be an integer."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if sector is not None:
            queryset = queryset.filter(sector__iexact=sector)

        if indicator is not None:
            queryset = queryset.filter(indicator__icontains=indicator)

        serializer = EconomicReportSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
