# future_skills/api/views.py

import os

from django.conf import settings
from django.db import transaction
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from ..models import (
    EconomicReport,
    Employee,
    FutureSkillPrediction,
    HRInvestmentRecommendation,
    MarketTrend,
    Skill,
    TrainingRun,
)
from ..permissions import IsHRStaff, IsHRStaffOrManager
from ..services.prediction_engine import recalculate_predictions
from ..services.file_parser import parse_employee_file
from ..services.recommendation_engine import generate_recommendations_from_predictions
from .serializers import (
    AddSkillToEmployeeSerializer,
    BulkEmployeeImportSerializer,
    BulkPredictRequestSerializer,
    EconomicReportSerializer,
    EmployeeSerializer,
    FutureSkillPredictionSerializer,
    HRInvestmentRecommendationSerializer,
    MarketTrendSerializer,
    PredictSkillsRequestSerializer,
    PredictSkillsResponseSerializer,
    RecommendSkillsRequestSerializer,
    RemoveSkillFromEmployeeSerializer,
    TrainingRunDetailSerializer,
    TrainingRunSerializer,
    TrainModelRequestSerializer,
    TrainModelResponseSerializer,
)

# Error messages constants
ERROR_MESSAGES = {
    "HORIZON_YEARS_INTEGER": "horizon_years must be an integer.",
}


class BulkEmployeeProcessingMixin:
    """Shared helpers for bulk employee operations."""

    def _process_employee_batch(self, employees_data):
        created_count = 0
        updated_count = 0
        errors = []

        with transaction.atomic():
            for idx, employee_data in enumerate(employees_data):
                try:
                    if self._upsert_employee(employee_data):
                        updated_count += 1
                    else:
                        created_count += 1
                except Exception as exc:  # pragma: no cover - defensive
                    errors.append(self._format_employee_error(idx, employee_data, exc))

        return {
            "created_count": created_count,
            "updated_count": updated_count,
            "failed_count": len(errors),
            "errors": errors,
        }

    def _upsert_employee(self, employee_data):
        email = employee_data.get("email")
        existing_employee = Employee.objects.filter(email=email).first()

        if existing_employee:
            for field, value in employee_data.items():
                if field != "id":
                    setattr(existing_employee, field, value)
            existing_employee.save()
            return True

        Employee.objects.create(**employee_data)
        return False

    def _format_employee_error(self, idx, employee_data, exc):
        return {
            "row": idx + 1,
            "email": employee_data.get("email", "unknown"),
            "error": str(exc),
        }

    def _maybe_generate_predictions(
        self,
        *,
        auto_predict,
        horizon_years,
        request_user,
        trigger,
    ):
        if not auto_predict:
            return False, 0, []

        try:
            total_predictions = recalculate_predictions(
                horizon_years=horizon_years,
                run_by=request_user if getattr(request_user, "is_authenticated", False) else None,
                parameters={"trigger": trigger},
            )
            return True, total_predictions, []
        except Exception as exc:  # pragma: no cover - defensive
            return (
                False,
                0,
                [
                    {
                        "row": None,
                        "email": None,
                        "error": f"Prediction generation failed: {exc}",
                    }
                ],
            )

    def _determine_status_label(self, failed_count):
        return "success" if failed_count == 0 else "partial_success"

    def _determine_http_status(self, failed_count):
        return (
            status.HTTP_201_CREATED
            if failed_count == 0
            else status.HTTP_207_MULTI_STATUS
        )


class FutureSkillPredictionPagination(PageNumberPagination):
    """
    Custom pagination for future skill predictions.
    """

    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class EmployeePagination(PageNumberPagination):
    """
    Custom pagination for employees.
    """

    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


@extend_schema(
    tags=["Predictions"],
    summary="List future skill predictions",
    description="""Retrieve a paginated list of future skill predictions with optional filters.

    **Permissions**: HR Staff or Manager

    **Filters**:
    - `job_role_id`: Filter by specific job role
    - `horizon_years`: Filter by prediction horizon (e.g., 3, 5, 10 years)

    **Pagination**: Results are paginated with 10 items per page by default.
    Use `page` and `page_size` query parameters to control pagination.

    **Example**: `/api/future-skills/?job_role_id=1&horizon_years=5&page=1&page_size=20`
    """,
    parameters=[
        OpenApiParameter(
            name="job_role_id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description="Filter predictions for a specific job role ID",
            required=False,
        ),
        OpenApiParameter(
            name="horizon_years",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description="Filter by prediction horizon in years (e.g., 3, 5, 10)",
            required=False,
        ),
        OpenApiParameter(
            name="page",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description="Page number for pagination",
            required=False,
        ),
        OpenApiParameter(
            name="page_size",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description="Number of items per page (max 100)",
            required=False,
        ),
    ],
    responses={
        200: FutureSkillPredictionSerializer(many=True),
        401: OpenApiTypes.OBJECT,
        403: OpenApiTypes.OBJECT,
    },
)
class FutureSkillPredictionListAPIView(ListAPIView):
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
    serializer_class = FutureSkillPredictionSerializer
    pagination_class = FutureSkillPredictionPagination
    queryset = FutureSkillPrediction.objects.all().order_by("-created_at", "id")

    def get_queryset(self):
        queryset = super().get_queryset()

        job_role_id = self.request.query_params.get("job_role_id")
        horizon_years = self.request.query_params.get("horizon_years")

        if job_role_id is not None:
            queryset = queryset.filter(job_role_id=job_role_id)

        if horizon_years is not None:
            try:
                horizon = int(horizon_years)
                queryset = queryset.filter(horizon_years=horizon)
            except ValueError:
                # Return empty queryset for invalid horizon_years
                # This will result in a valid paginated response with empty results
                return queryset.none()

        return queryset


@extend_schema(
    tags=["Predictions"],
    summary="Recalculate all predictions",
    description="""Trigger a complete recalculation of all future skill predictions using ML or rules engine.

    **Permissions**: HR Staff only (DRH/Responsable RH)

    **Process**:
    1. Recalculates predictions for all job role × skill combinations
    2. Uses ML model if available, falls back to rules engine
    3. Generates HR investment recommendations for HIGH predictions
    4. Creates a PredictionRun record for traceability

    **Use Cases**:
    - After training a new ML model
    - When market trends or economic data changes
    - Periodic updates (monthly/quarterly)
    - When switching between ML and rules engine

    **Performance**: May take several seconds for large datasets (500+ combinations).
    Consider using async execution for production.

    **Example Request**:
    ```json
    {
      "horizon_years": 5
    }
    ```
    """,
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "horizon_years": {
                    "type": "integer",
                    "description": "Prediction horizon in years",
                    "default": 5,
                    "example": 5,
                }
            },
        }
    },
    examples=[
        OpenApiExample(
            "Default 5-year horizon",
            value={"horizon_years": 5},
            request_only=True,
        ),
        OpenApiExample(
            "10-year strategic planning",
            value={"horizon_years": 10},
            request_only=True,
        ),
    ],
    responses={
        200: {
            "type": "object",
            "properties": {
                "horizon_years": {"type": "integer"},
                "total_predictions": {"type": "integer"},
                "total_recommendations": {"type": "integer"},
            },
            "example": {
                "horizon_years": 5,
                "total_predictions": 357,
                "total_recommendations": 42,
            },
        },
        400: OpenApiTypes.OBJECT,
        401: OpenApiTypes.OBJECT,
        403: OpenApiTypes.OBJECT,
    },
)
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
                {"detail": ERROR_MESSAGES["HORIZON_YEARS_INTEGER"]},
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
        queryset = HRInvestmentRecommendation.objects.select_related(
            "skill", "job_role"
        )

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
                    {"detail": ERROR_MESSAGES["HORIZON_YEARS_INTEGER"]},
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
    - POST /api/employees/{id}/add-skill/ - Add skill to employee (Section 4.2)
    - POST /api/employees/{id}/remove-skill/ - Remove skill from employee (Section 4.2)
    - PUT /api/employees/{id}/skills/ - Update all employee skills (Section 4.2)
    """

    queryset = Employee.objects.select_related("job_role").all()
    serializer_class = EmployeeSerializer
    permission_classes = [IsHRStaffOrManager]
    pagination_class = EmployeePagination

    @action(detail=True, methods=["post"], url_path="add-skill")
    def add_skill(self, request, pk=None):
        """
        Add a skill to an employee's skills ManyToMany relationship.
        POST /api/employees/{id}/add-skill/
        Body: {"skill_id": 5}
        """
        employee = self.get_object()
        serializer = AddSkillToEmployeeSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        skill_id = serializer.validated_data["skill_id"]
        skill = Skill.objects.get(pk=skill_id)

        # Add skill using ManyToMany .add() method
        if skill not in employee.skills.all():
            employee.skills.add(skill)
            return Response(
                {
                    "message": f'Skill "{skill.name}" added successfully',
                    "skills": [s.name for s in employee.skills.all()],
                },
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {
                    "message": f'Skill "{skill.name}" already exists',
                    "skills": [s.name for s in employee.skills.all()],
                },
                status=status.HTTP_200_OK,
            )

    @action(detail=True, methods=["post"], url_path="remove-skill")
    def remove_skill(self, request, pk=None):
        """
        Remove a skill from an employee's skills ManyToMany relationship.
        POST /api/employees/{id}/remove-skill/
        Body: {"skill_id": 5}
        """
        employee = self.get_object()
        serializer = RemoveSkillFromEmployeeSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        skill_id = serializer.validated_data["skill_id"]
        skill = Skill.objects.get(pk=skill_id)

        # Remove skill using ManyToMany .remove() method
        if skill in employee.skills.all():
            employee.skills.remove(skill)
            return Response(
                {
                    "message": f'Skill "{skill.name}" removed successfully',
                    "skills": [s.name for s in employee.skills.all()],
                },
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {
                    "message": f'Skill "{skill.name}" not found in employee skills',
                    "skills": [s.name for s in employee.skills.all()],
                },
                status=status.HTTP_404_NOT_FOUND,
            )

    @action(detail=True, methods=["put"], url_path="skills")
    def update_skills(self, request, pk=None):
        """
        Replace all employee skills at once using ManyToMany .set().
        PUT /api/employees/{id}/skills/
        Body: {"skill_ids": [1, 2, 3]}
        """
        employee = self.get_object()
        skill_ids = request.data.get("skill_ids", [])

        if not isinstance(skill_ids, list):
            return Response(
                {"error": "skill_ids must be a list"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate all skill IDs exist
        skills = Skill.objects.filter(id__in=skill_ids)
        if skills.count() != len(skill_ids):
            return Response(
                {"error": "One or more invalid skill IDs"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Replace all skills using ManyToMany .set() method
        employee.skills.set(skills)

        return Response(
            {
                "message": "Skills updated successfully",
                "skills": [s.name for s in employee.skills.all()],
            },
            status=status.HTTP_200_OK,
        )


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
            return Response(input_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Get employee
        employee_id = input_serializer.validated_data["employee_id"]
        employee = Employee.objects.select_related("job_role").get(pk=employee_id)

        if not employee.job_role:
            return Response(
                {"detail": "Employee has no associated job role."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get predictions for this employee's job role
        predictions = (
            FutureSkillPrediction.objects.filter(job_role=employee.job_role)
            .select_related("skill")
            .order_by("-score")[:10]
        )

        # Format response
        results = []
        for pred in predictions:
            results.append(
                {
                    "skill_name": pred.skill.name,
                    "skill_id": pred.skill.id,
                    "level": pred.level,
                    "score": pred.score,
                    "rationale": pred.rationale or "",
                }
            )

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
            return Response(input_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Get employee
        employee_id = input_serializer.validated_data["employee_id"]
        exclude_current = input_serializer.validated_data["exclude_current"]

        employee = Employee.objects.select_related("job_role").get(pk=employee_id)

        if not employee.job_role:
            return Response(
                {"detail": "Employee has no associated job role."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get high priority predictions for this job role
        predictions = (
            FutureSkillPrediction.objects.filter(
                job_role=employee.job_role, level__in=["HIGH", "MEDIUM"]
            )
            .select_related("skill")
            .order_by("-score")
        )

        # Filter out current skills if requested
        if exclude_current:
            current_skill_names = [s.lower() for s in employee.current_skills]
            predictions = predictions.exclude(
                skill__name__icontains=lambda name: any(
                    cs in name.lower() for cs in current_skill_names
                )
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
            results.append(
                {
                    "skill_name": pred.skill.name,
                    "skill_id": pred.skill.id,
                    "level": pred.level,
                    "score": pred.score,
                    "rationale": pred.rationale or "",
                }
            )

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
            return Response(input_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        employee_ids = input_serializer.validated_data["employee_ids"]

        # Get all employees with their job roles
        employees = Employee.objects.filter(pk__in=employee_ids).select_related(
            "job_role"
        )

        # Generate predictions for each
        results = {}
        for employee in employees:
            if not employee.job_role:
                results[employee.id] = {"error": "No associated job role"}
                continue

            predictions = (
                FutureSkillPrediction.objects.filter(job_role=employee.job_role)
                .select_related("skill")
                .order_by("-score")[:5]
            )

            employee_predictions = []
            for pred in predictions:
                employee_predictions.append(
                    {
                        "skill_name": pred.skill.name,
                        "skill_id": pred.skill.id,
                        "level": pred.level,
                        "score": pred.score,
                        "rationale": pred.rationale or "",
                    }
                )

            results[employee.id] = employee_predictions

        return Response(results, status=status.HTTP_200_OK)


class BulkEmployeeImportAPIView(BulkEmployeeProcessingMixin, APIView):
    """
    Bulk import/update employees from JSON data with automatic prediction generation.

    This endpoint allows HR staff (DRH/Responsable RH) to create or update multiple
    employees in a single API call. The operation is performed within a database
    transaction to ensure data consistency.

    **Endpoint:** `POST /api/bulk-import/employees/`

    **Authentication:** Required (Token/Session)

    **Permissions:** IsHRStaff (DRH or Responsable RH groups only)

    **Request Body (JSON):**
    ```json
    {
        "employees": [
            {
                "first_name": "John",
                "last_name": "Doe",
                "email": "john.doe@company.com",
                "job_role_id": 1,
                "skills": ["Python", "Django", "REST API"]
            },
            {
                "first_name": "Jane",
                "last_name": "Smith",
                "email": "jane.smith@company.com",
                "job_role_id": 2,
                "skills": ["JavaScript", "React", "Node.js"]
            }
        ],
        "auto_predict": true,
        "horizon_years": 5
    }
    ```

    **Request Parameters:**
    - `employees` (required): List of employee objects to import
      - `first_name` (required): Employee's first name
      - `last_name` (required): Employee's last name
      - `email` (required): Unique email address
      - `job_role_id` (required): Valid JobRole ID
      - `skills` (optional): List of skill names
    - `auto_predict` (optional, default=true): Generate predictions after import
    - `horizon_years` (optional, default=5): Prediction horizon in years

    **Success Response (201 CREATED):**
    ```json
    {
        "status": "success",
        "created": 5,
        "updated": 0,
        "failed": 0,
        "errors": [],
        "predictions_generated": true,
        "total_predictions": 15
    }
    ```

    **Partial Success Response (207 MULTI-STATUS):**
    ```json
    {
        "status": "partial_success",
        "created": 3,
        "updated": 1,
        "failed": 2,
        "errors": [
            {
                "row": 2,
                "email": "duplicate@company.com",
                "error": "Employee with this email already exists"
            },
            {
                "row": 5,
                "email": "invalid@company.com",
                "error": "Job role with ID 999 does not exist"
            }
        ],
        "predictions_generated": true,
        "total_predictions": 12
    }
    ```

    **Error Response (400 BAD REQUEST):**
    ```json
    {
        "employees": [
            "This field is required."
        ]
    }
    ```

    **Behavior:**
    - Checks for existing employees by email
    - Creates new employees if email doesn't exist
    - Updates existing employees if email matches
    - Validates job_role_id existence before processing
    - Detects duplicate emails within the batch
    - Generates predictions for all job roles after successful import
    - Returns detailed error information for failed rows
    - Uses transaction.atomic() for data integrity

    **Example cURL:**
    ```bash
    curl -X POST http://localhost:8000/api/bulk-import/employees/ \
      -H "Authorization: Bearer YOUR_TOKEN" \
      -H "Content-Type: application/json" \
      -d @employees.json
    ```

    **See Also:**
    - BulkEmployeeUploadAPIView for file upload support
    - BulkEmployeeImportSerializer for validation details
    - docs/BULK_IMPORT_COMPLETION_SUMMARY.md for comprehensive guide
    """

    permission_classes = [IsHRStaff]  # Only DRH/Responsable RH

    def post(self, request, *args, **kwargs):
        input_serializer = BulkEmployeeImportSerializer(data=request.data)
        if not input_serializer.is_valid():
            return Response(input_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated = input_serializer.validated_data
        batch_results = self._process_employee_batch(validated["employees"])
        predictions_generated, total_predictions, prediction_errors = (
            self._maybe_generate_predictions(
                auto_predict=validated["auto_predict"],
                horizon_years=validated["horizon_years"],
                request_user=request.user,
                trigger="bulk_employee_import",
            )
        )

        errors = batch_results["errors"] + prediction_errors
        response_data = {
            "status": self._determine_status_label(batch_results["failed_count"]),
            "created": batch_results["created_count"],
            "updated": batch_results["updated_count"],
            "failed": batch_results["failed_count"],
            "errors": errors,
            "predictions_generated": predictions_generated,
            "total_predictions": total_predictions if predictions_generated else 0,
        }

        return Response(
            response_data,
            status=self._determine_http_status(batch_results["failed_count"]),
        )


class BulkEmployeeUploadAPIView(BulkEmployeeProcessingMixin, APIView):
    """
    File upload endpoint for bulk employee import from CSV/Excel/JSON files.

    This endpoint allows HR staff to upload CSV, Excel, or JSON files containing
    employee data for bulk import. Files are validated, parsed, and processed
    using the same logic as BulkEmployeeImportAPIView.

    **Endpoint:** `POST /api/bulk-upload/employees/`

    **Authentication:** Required (Token/Session)

    **Permissions:** IsHRStaff (DRH or Responsable RH groups only)

    **Content-Type:** `multipart/form-data`

    **Form Parameters:**
    - `file` (required): File to upload (CSV/Excel/JSON)
      - Max size: 10 MB
      - Extensions: .csv, .xlsx, .xls, .json
      - MIME types: text/csv, application/vnd.ms-excel,
        application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,
        application/json
    - `auto_predict` (optional, default=true): Generate predictions after import
    - `horizon_years` (optional, default=5): Prediction horizon in years

    **Supported File Formats:**

    1. **CSV Format (.csv):**
    ```csv
    first_name,last_name,email,job_role_id,skills
    John,Doe,john.doe@company.com,1,"Python;Django;REST API"
    Jane,Smith,jane.smith@company.com,2,"JavaScript;React;Node.js"
    ```

    2. **Excel Format (.xlsx, .xls):**
    Same columns as CSV, but in Excel spreadsheet format

    3. **JSON Format (.json):**
    ```json
    [
        {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@company.com",
            "job_role_id": 1,
            "skills": ["Python", "Django", "REST API"]
        },
        {
            "first_name": "Jane",
            "last_name": "Smith",
            "email": "jane.smith@company.com",
            "job_role_id": 2,
            "skills": ["JavaScript", "React", "Node.js"]
        }
    ]
    ```

    **Skill Format Support (CSV/Excel):**
    - Semicolon-separated: `"Python;Django;REST API"`
    - Comma-separated: `"Python,Django,REST API"`
    - JSON array string: `"[\"Python\", \"Django\", \"REST API\"]"`

    **Success Response (201 CREATED):**
    ```json
    {
        "status": "success",
        "message": "File uploaded and processed successfully",
        "filename": "employees.csv",
        "created": 5,
        "updated": 0,
        "failed": 0,
        "errors": [],
        "predictions_generated": true,
        "total_predictions": 15
    }
    ```

    **File Validation Errors (400 BAD REQUEST):**
    ```json
    {
        "error": "File size exceeds 10MB limit"
    }
    ```
    ```json
    {
        "error": "Invalid file type. Allowed: .csv, .xlsx, .xls, .json"
    }
    ```
    ```json
    {
        "error": "MIME type text/plain not allowed"
    }
    ```

    **Parsing Errors (400 BAD REQUEST):**
    ```json
    {
        "status": "error",
        "message": "File parsing failed",
        "errors": [
            {
                "row": 3,
                "error": "Missing required field: email"
            },
            {
                "row": 7,
                "error": "Invalid email format"
            }
        ]
    }
    ```

    **Behavior:**
    - Validates file size (max 10MB)
    - Validates file extension (.csv, .xlsx, .xls, .json)
    - Validates MIME type for security
    - Parses file using appropriate parser (CSV/Excel/JSON)
    - Handles multiple encoding formats (UTF-8, Latin-1)
    - Creates/updates employees based on email
    - Generates predictions after successful import
    - Returns detailed error information per row
    - Uses transaction.atomic() for data integrity

    **Example cURL (CSV):**
    ```bash
    curl -X POST http://localhost:8000/api/bulk-upload/employees/ \
      -H "Authorization: Bearer YOUR_TOKEN" \
      -F "file=@employees.csv"
    ```

    **Example cURL (Excel):**
    ```bash
    curl -X POST http://localhost:8000/api/bulk-upload/employees/ \
      -H "Authorization: Bearer YOUR_TOKEN" \
      -F "file=@employees.xlsx" \
      -F "auto_predict=true" \
      -F "horizon_years=10"
    ```

    **Example Python Requests:**
    ```python
    import requests

    url = 'http://localhost:8000/api/bulk-upload/employees/'
    headers = {'Authorization': 'Bearer YOUR_TOKEN'}
    files = {'file': open('employees.csv', 'rb')}
    data = {'auto_predict': 'true', 'horizon_years': '5'}

    response = requests.post(url, headers=headers, files=files, data=data)
    print(response.json())
    ```

    **Template File:**
    A sample CSV template is available at:
    `future_skills/services/employees_import_template.csv`

    **See Also:**
    - BulkEmployeeImportAPIView for JSON data import
    - file_parser.py module for parsing implementation
    - docs/BULK_IMPORT_COMPLETION_SUMMARY.md for comprehensive guide
    """

    permission_classes = [IsHRStaff]  # Only DRH/Responsable RH

    # File upload limits
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".json"}
    ALLOWED_MIME_TYPES = {
        "text/csv",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/json",
    }

    def post(self, request, *args, **kwargs):
        try:
            uploaded_file = self._get_uploaded_file(request)
            filename, file_extension = self._validate_file_metadata(uploaded_file)
            employees = self._parse_uploaded_employees(uploaded_file, file_extension)
        except ValidationError as exc:
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:  # pragma: no cover - defensive
            return Response(
                self._build_generic_file_error(str(exc)),
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = BulkEmployeeImportSerializer(
            data=self._build_import_payload(request, employees)
        )
        if not serializer.is_valid():
            return Response(
                {
                    "status": "error",
                    "message": "Validation failed",
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        validated = serializer.validated_data
        batch_results = self._process_employee_batch(validated["employees"])
        predictions_generated, total_predictions, prediction_errors = (
            self._maybe_generate_predictions(
                auto_predict=validated["auto_predict"],
                horizon_years=validated["horizon_years"],
                request_user=request.user,
                trigger="bulk_employee_upload",
            )
        )

        errors = batch_results["errors"] + prediction_errors
        response_data = {
            "status": self._determine_status_label(batch_results["failed_count"]),
            "message": f"File processed: {filename}",
            "file_info": {
                "filename": filename,
                "size_bytes": uploaded_file.size,
                "format": file_extension,
            },
            "created": batch_results["created_count"],
            "updated": batch_results["updated_count"],
            "failed": batch_results["failed_count"],
            "errors": errors,
            "predictions_generated": predictions_generated,
            "total_predictions": total_predictions if predictions_generated else 0,
        }

        return Response(
            response_data,
            status=self._determine_http_status(batch_results["failed_count"]),
        )

    def _get_uploaded_file(self, request):
        if "file" not in request.FILES:
            raise ValidationError(
                {
                    "status": "error",
                    "message": "No file provided",
                    "errors": [{"field": "file", "error": "File is required"}],
                }
            )
        return request.FILES["file"]

    def _validate_file_metadata(self, uploaded_file):
        if uploaded_file.size > self.MAX_FILE_SIZE:
            raise ValidationError(
                {
                    "status": "error",
                    "message": "File too large",
                    "errors": [
                        {
                            "field": "file",
                            "error": f"File size exceeds maximum limit of {self.MAX_FILE_SIZE / (1024 * 1024):.1f}MB",
                        }
                    ],
                }
            )

        filename = uploaded_file.name
        _, file_extension = os.path.splitext(filename)
        file_extension = file_extension.lower()

        if file_extension not in self.ALLOWED_EXTENSIONS:
            allowed = ", ".join(sorted(self.ALLOWED_EXTENSIONS))
            raise ValidationError(
                {
                    "status": "error",
                    "message": "Invalid file type",
                    "errors": [
                        {
                            "field": "file",
                            "error": f"File type {file_extension} not supported. Allowed: {allowed}",
                        }
                    ],
                }
            )

        content_type = uploaded_file.content_type
        if content_type and content_type not in self.ALLOWED_MIME_TYPES:
            raise ValidationError(
                {
                    "status": "error",
                    "message": "Invalid file format",
                    "errors": [
                        {
                            "field": "file",
                            "error": f"MIME type {content_type} not allowed",
                        }
                    ],
                }
            )

        return filename, file_extension

    def _parse_uploaded_employees(self, uploaded_file, file_extension):
        if file_extension == ".json":
            employees, parse_errors = self._parse_json_file(uploaded_file)
        else:
            employees, parse_errors = parse_employee_file(uploaded_file, file_extension)

        if parse_errors:
            raise ValidationError(
                {
                    "status": "error",
                    "message": "File parsing failed",
                    "errors": parse_errors,
                }
            )

        if not employees:
            raise ValidationError(
                {
                    "status": "error",
                    "message": "No valid employee data found in file",
                    "errors": [
                        {
                            "field": "file",
                            "error": "File contains no valid employee records",
                        }
                    ],
                }
            )

        return employees

    def _build_import_payload(self, request, employees):
        auto_predict = request.data.get("auto_predict", "true").lower() in [
            "true",
            "1",
            "yes",
        ]
        try:
            horizon_years = int(request.data.get("horizon_years", 5))
        except ValueError:
            horizon_years = 5

        return {
            "employees": employees,
            "auto_predict": auto_predict,
            "horizon_years": horizon_years,
        }

    def _build_generic_file_error(self, message):
        return {
            "status": "error",
            "message": "Failed to process file",
            "errors": [{"field": "file", "error": message}],
        }

    def _parse_json_file(self, file):
        """
        Parse JSON file containing employee data.

        Expected format:
        {
            "employees": [
                {
                    "name": "John Doe",
                    "email": "john@example.com",
                    "department": "Engineering",
                    "position": "Developer",
                    "job_role_id": 1,
                    "current_skills": ["Python", "Django"]
                }
            ]
        }

        OR simple array:
        [
            {"name": "John Doe", "email": "john@example.com", ...}
        ]
        """
        import json

        try:
            file.seek(0)
            data = json.load(file)

            # Handle both formats
            if isinstance(data, dict) and "employees" in data:
                employees = data["employees"]
            elif isinstance(data, list):
                employees = data
            else:
                return [], [
                    {
                        "row": 0,
                        "field": "file",
                        "error": 'Invalid JSON format. Expected array or object with "employees" key',
                    }
                ]

            # Validate each employee
            validated_employees = []
            errors = []

            for idx, emp in enumerate(employees):
                if not isinstance(emp, dict):
                    errors.append(
                        {
                            "row": idx + 1,
                            "field": "employee",
                            "error": "Each employee must be an object",
                        }
                    )
                    continue

                # Basic validation
                required_fields = ["name", "email", "department", "position"]
                missing_fields = [f for f in required_fields if not emp.get(f)]

                if missing_fields:
                    errors.append(
                        {
                            "row": idx + 1,
                            "field": ", ".join(missing_fields),
                            "error": f'Missing required fields: {", ".join(missing_fields)}',
                        }
                    )
                    continue

                validated_employees.append(emp)

            return validated_employees, errors

        except json.JSONDecodeError as e:
            return [], [{"row": 0, "field": "file", "error": f"Invalid JSON: {str(e)}"}]
        except Exception as e:
            return [], [
                {"row": 0, "field": "file", "error": f"Failed to parse JSON: {str(e)}"}
            ]


# ============================================================================
# Training API Views (Section 2.4)
# ============================================================================


class TrainingRunPagination(PageNumberPagination):
    """
    Custom pagination for training runs.
    """

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


@extend_schema(
    tags=["Training"],
    summary="Train new ML model",
    description="""Train a new machine learning model for future skill predictions.

    **Permissions**: HR Staff only (DRH/Responsable RH)

    **Execution Modes**:

    1. **Synchronous** (default, `async_training=false`):
       - Training executes immediately in the request
       - Returns complete metrics when finished
       - Suitable for small datasets or development
       - May timeout on large datasets

    2. **Asynchronous** (`async_training=true`):
       - Training executes in background via Celery
       - Returns immediately with task ID
       - Check status via `/api/training/runs/{id}/`
       - Recommended for production and large datasets

    **Training Process**:
    1. Loads and validates dataset
    2. Performs train/test split
    3. Trains Random Forest classifier with hyperparameters
    4. Evaluates on test set (accuracy, precision, recall, F1)
    5. Saves model to `artifacts/models/` directory
    6. Records metrics in TrainingRun

    **Hyperparameters**:
    - `n_estimators`: Number of trees (default: 100)
    - `max_depth`: Maximum tree depth (default: 15)
    - `min_samples_split`: Min samples to split node (default: 5)
    - `min_samples_leaf`: Min samples at leaf (default: 2)
    - `random_state`: Random seed (default: 42)

    **Model Versioning**:
    Provide a descriptive version string (e.g., "v2.1_optimized", "prod_2024_q4").
    If omitted, auto-generates timestamp-based version.

    **Example Request (Sync)**:
    ```json
    {
    "dataset_path": "artifacts/datasets/future_skills_dataset.csv",
      "test_split": 0.2,
      "hyperparameters": {
        "n_estimators": 150,
        "max_depth": 20
      },
      "model_version": "v2.1_production",
      "notes": "Optimized model for Q4 2024",
      "async_training": false
    }
    ```

    **Example Request (Async)**:
    ```json
    {
    "dataset_path": "artifacts/datasets/future_skills_dataset.csv",
      "test_split": 0.2,
      "async_training": true,
      "model_version": "v2.2_background"
    }
    ```
    """,
    request=TrainModelRequestSerializer,
    examples=[
        OpenApiExample(
            "Synchronous training with custom hyperparameters",
            value={
                "dataset_path": "artifacts/datasets/future_skills_dataset.csv",
                "test_split": 0.2,
                "hyperparameters": {
                    "n_estimators": 150,
                    "max_depth": 20,
                    "min_samples_split": 5,
                },
                "model_version": "v2.1_prod",
                "notes": "Production model with enhanced parameters",
                "async_training": False,
            },
            request_only=True,
        ),
        OpenApiExample(
            "Asynchronous background training",
            value={
                "dataset_path": "artifacts/datasets/future_skills_dataset.csv",
                "test_split": 0.25,
                "async_training": True,
                "model_version": "v3.0_background",
                "notes": "Large dataset training in background",
            },
            request_only=True,
        ),
    ],
    responses={
        200: TrainModelResponseSerializer,
        201: TrainModelResponseSerializer,
        400: OpenApiTypes.OBJECT,
        401: OpenApiTypes.OBJECT,
        403: OpenApiTypes.OBJECT,
        500: OpenApiTypes.OBJECT,
    },
)
class TrainModelAPIView(APIView):
    """
    Train a new ML model (synchronous or asynchronous execution).

    POST /api/training/train/

    Body:
    {
        "dataset_path": "artifacts/datasets/future_skills_dataset.csv",
        "test_split": 0.2,
        "hyperparameters": {
            "n_estimators": 100,
            "max_depth": 15,
            "min_samples_split": 5
        },
        "model_version": "v3.0",
        "notes": "Production model with optimized parameters",
        "async_training": false  // Optional: use Celery for background training
    }

    Synchronous Mode (async_training=false, default):
    Returns:
    {
        "training_run_id": 10,
        "status": "COMPLETED",
        "message": "Training completed successfully",
        "model_version": "v3.0",
        "metrics": {
            "accuracy": 0.9861,
            "f1_score": 0.9860,
            ...
        }
    }

    Asynchronous Mode (async_training=true):
    Returns:
    {
        "training_run_id": 10,
        "status": "RUNNING",
        "message": "Training started in background",
        "model_version": "v3.0",
        "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    }
    """

    permission_classes = [IsHRStaff]

    def post(self, request, *args, **kwargs):
        """
        Train a new model synchronously or asynchronously.
        """
        import logging
        from datetime import datetime
        from pathlib import Path

        from ..services.training_service import (
            DataLoadError,
            ModelTrainer,
            TrainingError,
        )

        logger = logging.getLogger("future_skills.api.views")

        # Validate request data
        request_serializer = TrainModelRequestSerializer(data=request.data)
        if not request_serializer.is_valid():
            return Response(
                {"error": "Invalid request data", "details": request_serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        validated_data = request_serializer.validated_data
        dataset_path = validated_data.get("dataset_path")
        test_split = validated_data.get("test_split")
        hyperparameters = validated_data.get("hyperparameters", {})
        notes = validated_data.get("notes", "")

        # Check if async training is requested (Section 2.5)
        async_training = request.data.get("async_training", False)

        # Generate model version if not provided
        model_version = validated_data.get("model_version")
        if not model_version:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            model_version = f"api_v{timestamp}"

        # Create initial TrainingRun record with RUNNING status
        training_run = TrainingRun.objects.create(
            model_version=model_version,
            model_path="",  # Will be updated after training
            dataset_path=dataset_path,
            test_split=test_split,
            status="RUNNING",
            accuracy=0.0,
            precision=0.0,
            recall=0.0,
            f1_score=0.0,
            total_samples=0,
            train_samples=0,
            test_samples=0,
            training_duration_seconds=0.0,
            trained_by=request.user,
            notes=notes,
            hyperparameters=hyperparameters,
        )

        logger.info(
            f"Training started: run_id={training_run.id}, "
            f"version={model_version}, user={request.user.username}, "
            f"async={async_training}"
        )

        # === ASYNC MODE: Dispatch Celery task (Section 2.5) ===
        if async_training:
            try:
                from ..tasks import train_model_task

                # Dispatch the training task to Celery
                task = train_model_task.delay(
                    training_run_id=training_run.id,
                    dataset_path=dataset_path,
                    test_split=test_split,
                    hyperparameters=hyperparameters,
                )

                logger.info(
                    f"Celery task dispatched: task_id={task.id}, "
                    f"training_run_id={training_run.id}"
                )

                # Return immediately with RUNNING status
                return Response(
                    {
                        "training_run_id": training_run.id,
                        "status": "RUNNING",
                        "message": "Training started in background. Check status with GET /api/training/runs/<id>/",
                        "model_version": model_version,
                        "task_id": task.id,
                    },
                    status=status.HTTP_202_ACCEPTED,
                )

            except Exception as e:
                # If Celery fails, fall back to sync or return error
                training_run.status = "FAILED"
                training_run.error_message = f"Failed to dispatch Celery task: {str(e)}"
                training_run.save()

                logger.error(
                    f"Celery dispatch failed: run_id={training_run.id}, error={str(e)}"
                )

                return Response(
                    {
                        "training_run_id": training_run.id,
                        "status": "FAILED",
                        "message": "Failed to start background training. Redis/Celery may not be available.",
                        "error": str(e),
                    },
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )

        # === SYNC MODE: Train immediately (Section 2.4) ===

        try:
            # Initialize trainer
            trainer = ModelTrainer(
                dataset_path=dataset_path,
                test_split=test_split,
                random_state=hyperparameters.get("random_state", 42),
            )

            # Load data
            trainer.load_data()
            logger.info(
                f"Data loaded: {len(trainer.X_train)} train, {len(trainer.X_test)} test"
            )

            # Train model with provided hyperparameters
            metrics = trainer.train(**hyperparameters)
            logger.info(f"Training completed: accuracy={metrics['accuracy']:.2%}")

            # Save model
            model_dir = settings.ML_MODELS_DIR
            model_dir.mkdir(parents=True, exist_ok=True)
            model_path = model_dir / f"{model_version}.pkl"
            trainer.save_model(str(model_path))
            logger.info(f"Model saved: {model_path}")

            # Update training run with success
            training_run.status = "COMPLETED"
            training_run.model_path = str(model_path)
            training_run.accuracy = metrics["accuracy"]
            training_run.precision = metrics["precision"]
            training_run.recall = metrics["recall"]
            training_run.f1_score = metrics["f1_score"]
            training_run.total_samples = len(trainer.X_train) + len(trainer.X_test)
            training_run.train_samples = len(trainer.X_train)
            training_run.test_samples = len(trainer.X_test)
            training_run.training_duration_seconds = trainer.training_duration_seconds
            training_run.per_class_metrics = metrics.get("per_class_metrics", {})
            training_run.features_used = (
                list(trainer.X_train.columns)
                if hasattr(trainer.X_train, "columns")
                else []
            )

            # Update hyperparameters from trainer
            if hasattr(trainer, "hyperparameters"):
                training_run.hyperparameters = trainer.hyperparameters

            training_run.save()

            logger.info(
                f"Training run updated: id={training_run.id}, "
                f"status={training_run.status}, accuracy={training_run.accuracy:.2%}"
            )

            # Prepare response
            response_data = {
                "training_run_id": training_run.id,
                "status": training_run.status,
                "message": f"Training completed successfully in {training_run.training_duration_seconds:.2f}s",
                "model_version": model_version,
                "metrics": {
                    "accuracy": training_run.accuracy,
                    "precision": training_run.precision,
                    "recall": training_run.recall,
                    "f1_score": training_run.f1_score,
                    "training_duration_seconds": training_run.training_duration_seconds,
                },
            }

            response_serializer = TrainModelResponseSerializer(response_data)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except DataLoadError as e:
            # Update training run with failure
            training_run.status = "FAILED"
            training_run.error_message = f"Data loading error: {str(e)}"
            training_run.save()

            logger.error(
                f"Training failed (data load): run_id={training_run.id}, error={str(e)}"
            )

            return Response(
                {
                    "training_run_id": training_run.id,
                    "status": "FAILED",
                    "message": "Training failed due to data loading error",
                    "error": str(e),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except TrainingError as e:
            # Update training run with failure
            training_run.status = "FAILED"
            training_run.error_message = f"Training error: {str(e)}"
            training_run.save()

            logger.error(
                f"Training failed (training): run_id={training_run.id}, error={str(e)}"
            )

            return Response(
                {
                    "training_run_id": training_run.id,
                    "status": "FAILED",
                    "message": "Training failed during model training",
                    "error": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        except Exception as e:
            # Update training run with unexpected failure
            training_run.status = "FAILED"
            training_run.error_message = f"Unexpected error: {str(e)}"
            training_run.save()

            logger.error(
                f"Training failed (unexpected): run_id={training_run.id}, error={str(e)}",
                exc_info=True,
            )

            return Response(
                {
                    "training_run_id": training_run.id,
                    "status": "FAILED",
                    "message": "Training failed due to unexpected error",
                    "error": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@extend_schema(
    tags=["Training"],
    summary="List all training runs",
    description="""Retrieve a paginated list of all model training runs with metrics and status.

    **Permissions**: HR Staff or Manager

    **Filters**:
    - `status`: Filter by training status (RUNNING, COMPLETED, FAILED)
    - `trained_by`: Filter by username who initiated training
    - `page`: Page number for pagination
    - `page_size`: Number of items per page (max 100)

    **Use Cases**:
    - Monitor ongoing training jobs
    - Review historical training results
    - Compare model versions and performance
    - Audit training activities

    **Example**: `/api/training/runs/?status=COMPLETED&trained_by=admin&page=1`
    """,
    parameters=[
        OpenApiParameter(
            name="status",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description="Filter by status (RUNNING, COMPLETED, FAILED)",
            required=False,
            enum=["RUNNING", "COMPLETED", "FAILED"],
        ),
        OpenApiParameter(
            name="trained_by",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description="Filter by username who initiated training",
            required=False,
        ),
        OpenApiParameter(
            name="page",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description="Page number",
            required=False,
        ),
        OpenApiParameter(
            name="page_size",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description="Items per page (max 100)",
            required=False,
        ),
    ],
    responses={
        200: TrainingRunSerializer(many=True),
        401: OpenApiTypes.OBJECT,
        403: OpenApiTypes.OBJECT,
    },
)
class TrainingRunListAPIView(ListAPIView):
    """
    List all training runs with pagination.

    GET /api/training/runs/

    Query params:
    - page: Page number (default: 1)
    - page_size: Items per page (default: 20, max: 100)
    - status: Filter by status (RUNNING, COMPLETED, FAILED)
    - trained_by: Filter by username

    Returns paginated list of training runs with basic metrics.
    """

    permission_classes = [IsHRStaffOrManager]
    serializer_class = TrainingRunSerializer
    pagination_class = TrainingRunPagination

    def get_queryset(self):
        """
        Get filtered queryset based on query parameters.
        """
        queryset = TrainingRun.objects.select_related("trained_by").all()

        # Filter by status
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter.upper())

        # Filter by username
        trained_by = self.request.query_params.get("trained_by")
        if trained_by:
            queryset = queryset.filter(trained_by__username=trained_by)

        return queryset


@extend_schema(
    tags=["Training"],
    summary="Get training run details",
    description="""Retrieve detailed information about a specific training run.

    **Permissions**: HR Staff or Manager

    **Returns**:
    - **Basic Info**: ID, version, status, timestamps
    - **Performance Metrics**: Accuracy, precision, recall, F1 score
    - **Per-Class Metrics**: Detailed metrics for each prediction level (HIGH, MEDIUM, LOW)
    - **Model Configuration**: Hyperparameters used during training
    - **Dataset Info**: Sample counts, feature list, train/test split
    - **Error Details**: Error messages if training failed
    - **Execution Info**: Duration, trained by user

    **Use Cases**:
    - Review specific model performance
    - Debug failed training runs
    - Compare hyperparameter configurations
    - Audit model versioning and traceability

    **Example**: `/api/training/runs/42/`
    """,
    responses={
        200: TrainingRunDetailSerializer,
        401: OpenApiTypes.OBJECT,
        403: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
    },
)
class TrainingRunDetailAPIView(RetrieveAPIView):
    """
    Get detailed information about a specific training run.

    GET /api/training/runs/<id>/

    Returns full training run details including:
    - All metrics (accuracy, precision, recall, f1)
    - Per-class metrics
    - Feature importance
    - Hyperparameters
    - Dataset information
    - Error messages (if failed)
    """

    permission_classes = [IsHRStaffOrManager]
    serializer_class = TrainingRunDetailSerializer
    queryset = TrainingRun.objects.select_related("trained_by").all()
