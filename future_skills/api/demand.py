"""Stable cross-service demand API (consumed by smarthr360-career-sim).

GET /api/future-skills/demand/            all skills, latest demand
GET /api/future-skills/demand/?horizon_years=3

Response schema (STABLE — sibling services parse this):
{
  "generated_at": iso8601,
  "count": int,
  "results": [
    {"skill_code": "PY"|null, "skill_name": "Python",
     "demand_level": "LOW"|"MEDIUM"|"HIGH",
     "score": 0-100, "horizon_years": int, "job_roles_count": int}
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

from future_skills.models import FutureSkillPrediction


class DemandBySkillAPIView(APIView):
    # explicit contract: platform token required regardless of the
    # service's default permission settings
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = FutureSkillPrediction.objects.select_related("skill")

        horizon = request.query_params.get("horizon_years")
        if horizon:
            try:
                queryset = queryset.filter(horizon_years=int(horizon))
            except (TypeError, ValueError):
                return Response(
                    {"detail": "horizon_years must be an integer."}, status=400
                )

        best: dict[int, dict] = {}
        roles: dict[int, set] = {}
        for prediction in queryset:
            skill = prediction.skill
            roles.setdefault(skill.id, set()).add(prediction.job_role_id)
            current = best.get(skill.id)
            if current is None or prediction.score > current["score"]:
                best[skill.id] = {
                    "skill_code": skill.platform_code,
                    "skill_name": skill.name,
                    "demand_level": prediction.level,
                    "score": round(prediction.score, 1),
                    "horizon_years": prediction.horizon_years,
                }

        results = [
            {**entry, "job_roles_count": len(roles[skill_id])}
            for skill_id, entry in best.items()
        ]
        results.sort(key=lambda row: -row["score"])

        return Response(
            {
                "generated_at": timezone.now().isoformat(),
                "count": len(results),
                "results": results,
            }
        )
