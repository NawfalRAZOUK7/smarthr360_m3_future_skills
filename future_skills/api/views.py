# future_skills/api/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from ..models import FutureSkillPrediction, MarketTrend, EconomicReport, HRInvestmentRecommendation, Employee
from .serializers import (
    FutureSkillPredictionSerializer,
    MarketTrendSerializer,
    EconomicReportSerializer,
    HRInvestmentRecommendationSerializer,
    EmployeeSerializer,
    PredictSkillsRequestSerializer,
    PredictSkillsResponseSerializer,
    RecommendSkillsRequestSerializer,
    BulkPredictRequestSerializer,
)

from ..services.prediction_engine import recalculate_predictions
from ..permissions import IsHRStaff, IsHRStaffOrManager
from ..services.recommendation_engine import generate_recommendations_from_predictions


# Error messages constants
ERROR_MESSAGES = {
    'HORIZON_YEARS_INTEGER': 'horizon_years must be an integer.',
}


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
                    {"detail": ERROR_MESSAGES['HORIZON_YEARS_INTEGER']},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        serializer = FutureSkillPredictionSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RecalculateFutureSkillsAPIView(APIView):
    """
    Recalcule toutes les prédictions FutureSkillPrediction
    via le moteur de règles simple puis génère les recommandations RH..

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
                {"detail": ERROR_MESSAGES['HORIZON_YEARS_INTEGER']},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 1) Recalculer les prédictions avec traçabilité utilisateur + paramètres
        total_predictions = recalculate_predictions(
            horizon_years=horizon_years,
            run_by=request.user,
            parameters={
                "trigger": "api",
                # engine / horizon_years / model_version seront complétés par recalculate_predictions
            },
        )

        # 2) Générer les recommandations RH à partir des prédictions HIGH
        total_recommendations = generate_recommendations_from_predictions(
            horizon_years=horizon_years
        )

        return Response(
            {
                "horizon_years": horizon_years,
                "total_predictions": total_predictions,
                "total_recommendations": total_recommendations,
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

class HRInvestmentRecommendationListAPIView(APIView):
    """
    Liste les recommandations RH générées à partir des prédictions
    de compétences futures.

    Filtres :
      - horizon_years
      - skill_id
      - job_role_id
      - priority_level
    """

    permission_classes = [IsHRStaffOrManager]

    def get(self, request, *args, **kwargs):
        queryset = HRInvestmentRecommendation.objects.select_related("skill", "job_role")

        horizon_years = request.query_params.get("horizon_years")
        skill_id = request.query_params.get("skill_id")
        job_role_id = request.query_params.get("job_role_id")
        priority_level = request.query_params.get("priority_level")

        if horizon_years is not None:
            try:
                h = int(horizon_years)
                queryset = queryset.filter(horizon_years=h)
            except ValueError:
                return Response(
                    {"detail": ERROR_MESSAGES['HORIZON_YEARS_INTEGER']},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if skill_id is not None:
            queryset = queryset.filter(skill_id=skill_id)

        if job_role_id is not None:
            queryset = queryset.filter(job_role_id=job_role_id)

        if priority_level is not None:
            queryset = queryset.filter(priority_level=priority_level)

        serializer = HRInvestmentRecommendationSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class EmployeeViewSet(ModelViewSet):
    """
    ViewSet for Employee CRUD operations.
    
    Provides:
    - GET /api/employees/ - List all employees
    - POST /api/employees/ - Create new employee
    - GET /api/employees/{id}/ - Get employee detail
    - PUT/PATCH /api/employees/{id}/ - Update employee
    - DELETE /api/employees/{id}/ - Delete employee
    """
    queryset = Employee.objects.select_related("job_role").all()
    serializer_class = EmployeeSerializer
    permission_classes = [IsHRStaffOrManager]


class PredictSkillsAPIView(APIView):
    """
    Generate skill predictions for a specific employee.
    
    POST /api/predict-skills/
    Body: {
        "employee_id": 1,
        "current_skills": ["Python", "Django"],  # optional override
        "department": "Engineering"  # optional override
    }
    
    Returns: List of predicted skills with scores and levels
    """
    permission_classes = [IsHRStaffOrManager]

    def post(self, request, *args, **kwargs):
        # Validate input
        input_serializer = PredictSkillsRequestSerializer(data=request.data)
        if not input_serializer.is_valid():
            return Response(
                input_serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get employee
        employee_id = input_serializer.validated_data['employee_id']
        employee = Employee.objects.select_related('job_role').get(pk=employee_id)

        if not employee.job_role:
            return Response(
                {"detail": "Employee has no associated job role."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get predictions for this employee's job role
        predictions = FutureSkillPrediction.objects.filter(
            job_role=employee.job_role
        ).select_related('skill').order_by('-score')[:10]

        # Format response
        results = []
        for pred in predictions:
            results.append({
                'skill_name': pred.skill.name,
                'skill_id': pred.skill.id,
                'level': pred.level,
                'score': pred.score,
                'rationale': pred.rationale or ''
            })

        response_serializer = PredictSkillsResponseSerializer(results, many=True)
        return Response(response_serializer.data, status=status.HTTP_200_OK)


class RecommendSkillsAPIView(APIView):
    """
    Generate personalized skill recommendations for an employee.
    
    POST /api/recommend-skills/
    Body: {
        "employee_id": 1,
        "exclude_current": true
    }
    
    Returns: List of recommended skills (excluding current skills if specified)
    """
    permission_classes = [IsHRStaffOrManager]

    def post(self, request, *args, **kwargs):
        # Validate input
        input_serializer = RecommendSkillsRequestSerializer(data=request.data)
        if not input_serializer.is_valid():
            return Response(
                input_serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get employee
        employee_id = input_serializer.validated_data['employee_id']
        exclude_current = input_serializer.validated_data['exclude_current']
        
        employee = Employee.objects.select_related('job_role').get(pk=employee_id)

        if not employee.job_role:
            return Response(
                {"detail": "Employee has no associated job role."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get high priority predictions for this job role
        predictions = FutureSkillPrediction.objects.filter(
            job_role=employee.job_role,
            level__in=['HIGH', 'MEDIUM']
        ).select_related('skill').order_by('-score')

        # Filter out current skills if requested
        if exclude_current:
            current_skill_names = [s.lower() for s in employee.current_skills]
            predictions = predictions.exclude(
                skill__name__icontains=lambda name: any(cs in name.lower() for cs in current_skill_names)
            )
            # Manual filtering since Django ORM doesn't support complex icontains with list
            filtered_predictions = []
            for pred in predictions:
                if not any(cs in pred.skill.name.lower() for cs in current_skill_names):
                    filtered_predictions.append(pred)
            predictions = filtered_predictions[:10]
        else:
            predictions = list(predictions[:10])

        # Format response
        results = []
        for pred in predictions:
            results.append({
                'skill_name': pred.skill.name,
                'skill_id': pred.skill.id,
                'level': pred.level,
                'score': pred.score,
                'rationale': pred.rationale or ''
            })

        response_serializer = PredictSkillsResponseSerializer(results, many=True)
        return Response(response_serializer.data, status=status.HTTP_200_OK)


class BulkPredictAPIView(APIView):
    """
    Generate predictions for multiple employees at once.
    
    POST /api/bulk-predict/
    Body: {
        "employee_ids": [1, 2, 3, 4, 5]
    }
    
    Returns: Predictions for each employee
    """
    permission_classes = [IsHRStaffOrManager]

    def post(self, request, *args, **kwargs):
        # Validate input
        input_serializer = BulkPredictRequestSerializer(data=request.data)
        if not input_serializer.is_valid():
            return Response(
                input_serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        employee_ids = input_serializer.validated_data['employee_ids']
        
        # Get all employees with their job roles
        employees = Employee.objects.filter(
            pk__in=employee_ids
        ).select_related('job_role')

        # Generate predictions for each
        results = {}
        for employee in employees:
            if not employee.job_role:
                results[employee.id] = {
                    'error': 'No associated job role'
                }
                continue

            predictions = FutureSkillPrediction.objects.filter(
                job_role=employee.job_role
            ).select_related('skill').order_by('-score')[:5]

            employee_predictions = []
            for pred in predictions:
                employee_predictions.append({
                    'skill_name': pred.skill.name,
                    'skill_id': pred.skill.id,
                    'level': pred.level,
                    'score': pred.score,
                    'rationale': pred.rationale or ''
                })

            results[employee.id] = employee_predictions

        return Response(results, status=status.HTTP_200_OK)
