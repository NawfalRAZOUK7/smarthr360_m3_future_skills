"""Stable cross-service demand API (consumed by smarthr360-career-sim).

GET /api/future-skills/demand/                     all skills, latest demand
GET /api/future-skills/demand/?horizon_years=3
GET /api/future-skills/demand/?job_role=Developer
GET /api/future-skills/demand/history/?skill_code=PY   signal time series

Response schema (STABLE — sibling services parse this):
{
  "generated_at": iso8601,
  "count": int,
  "results": [
    {"skill_code": "PY"|null, "skill_name": "Python",
     "demand_level": "LOW"|"MEDIUM"|"HIGH",
     "score": 0-100, "horizon_years": int, "job_roles_count": int,
     "confidence": 0-1|null, "model_version": str|null,
     "explanation": str|null}
  ]
}

Aggregation: per skill, the strongest prediction (max score) across job
roles at the requested horizon (or across all horizons by default).
`skill_code` is the canonical platform code (ADR-007) when mapped.
"""

from __future__ import annotations

from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from future_skills.models import FutureSkillPrediction, FutureSkillSnapshot, Skill


def _confidence(prediction) -> float | None:
    """Best available confidence: explanation.confidence, else the
    probability of the predicted class."""
    explanation = prediction.explanation or {}
    if isinstance(explanation, dict) and explanation.get("confidence") is not None:
        try:
            return round(float(explanation["confidence"]), 3)
        except (TypeError, ValueError):
            pass
    probabilities = prediction.probabilities or {}
    key = f"p_{prediction.level.lower()}"
    if probabilities.get(key) is not None:
        try:
            return round(float(probabilities[key]), 3)
        except (TypeError, ValueError):
            pass
    return None


def _explanation_summary(prediction) -> str | None:
    explanation = prediction.explanation or {}
    if isinstance(explanation, dict):
        text = explanation.get("text") or prediction.rationale
    else:
        text = prediction.rationale
    if not text:
        return None
    text = str(text).strip()
    return text[:277] + "..." if len(text) > 280 else text


class DemandBySkillAPIView(APIView):
    # explicit contract: platform token required regardless of the
    # service's default permission settings
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = FutureSkillPrediction.objects.select_related(
            "skill", "job_role"
        )

        horizon = request.query_params.get("horizon_years")
        if horizon:
            try:
                queryset = queryset.filter(horizon_years=int(horizon))
            except (TypeError, ValueError):
                return Response(
                    {"detail": "horizon_years must be an integer."}, status=400
                )
        job_role = request.query_params.get("job_role")
        if job_role:
            queryset = queryset.filter(job_role__name__iexact=job_role)

        best: dict[int, FutureSkillPrediction] = {}
        roles: dict[int, set] = {}
        for prediction in queryset:
            skill_id = prediction.skill_id
            roles.setdefault(skill_id, set()).add(prediction.job_role_id)
            current = best.get(skill_id)
            if current is None or prediction.score > current.score:
                best[skill_id] = prediction

        results = []
        for skill_id, prediction in best.items():
            skill = prediction.skill
            results.append(
                {
                    "skill_code": skill.platform_code,
                    "skill_name": skill.name,
                    "demand_level": prediction.level,
                    "score": round(prediction.score, 1),
                    "horizon_years": prediction.horizon_years,
                    "job_roles_count": len(roles[skill_id]),
                    "confidence": _confidence(prediction),
                    "model_version": prediction.model_version or None,
                    "explanation": _explanation_summary(prediction),
                }
            )
        results.sort(key=lambda row: -row["score"])

        return Response(
            {
                "generated_at": timezone.now().isoformat(),
                "count": len(results),
                "results": results,
            }
        )


class DemandHistoryAPIView(APIView):
    """Signal time series for one skill, from silver-label snapshots.

    GET /api/future-skills/demand/history/?skill_code=PY  (or ?skill_name=)
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        code = request.query_params.get("skill_code")
        name = request.query_params.get("skill_name")
        if not code and not name:
            return Response(
                {"detail": "skill_code or skill_name is required."}, status=400
            )
        skill = (
            Skill.objects.filter(platform_code__iexact=code).first()
            if code
            else Skill.objects.filter(name__iexact=name).first()
        )
        if skill is None:
            return Response({"detail": "Unknown skill."}, status=404)

        snapshots = (
            FutureSkillSnapshot.objects.filter(skill=skill)
            .order_by("as_of_date")
        )
        series = [
            {
                "date": snapshot.as_of_date.isoformat(),
                "trend_score": round(snapshot.trend_score, 3),
                "scarcity_index": round(snapshot.scarcity_index, 3),
                "hiring_difficulty": round(snapshot.hiring_difficulty, 3),
                "internal_usage": round(snapshot.internal_usage, 3),
            }
            for snapshot in snapshots
        ]

        trend = None
        if len(series) >= 2:
            delta = series[-1]["trend_score"] - series[0]["trend_score"]
            trend = "rising" if delta > 0.05 else (
                "falling" if delta < -0.05 else "stable"
            )

        return Response(
            {
                "skill_code": skill.platform_code,
                "skill_name": skill.name,
                "points": len(series),
                "trend": trend,
                "series": series,
            }
        )
