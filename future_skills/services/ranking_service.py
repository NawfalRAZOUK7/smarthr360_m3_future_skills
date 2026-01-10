"""Service helpers for Top-N skill rankings."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any, Dict, List, Optional

from django.db.models import Max

from future_skills.models import FutureSkillLabel, FutureSkillPrediction

ALLOWED_GROUP_BY = {"department", "sector", "job_role", "skill_category", "overall"}


def _resolve_group_key(prediction: FutureSkillPrediction, group_by: str) -> str:
    if group_by in {"department", "sector"}:
        return (prediction.job_role.department or "General").strip() or "General"
    if group_by == "job_role":
        return (prediction.job_role.name or f"JobRole {prediction.job_role_id}").strip()
    if group_by == "skill_category":
        return (prediction.skill.category or "General").strip() or "General"
    return "overall"


def _resolve_label_group_key(label: FutureSkillLabel, group_by: str) -> str:
    if group_by in {"department", "sector"}:
        return (label.job_role.department or "General").strip() or "General"
    if group_by == "job_role":
        return (label.job_role.name or f"JobRole {label.job_role_id}").strip()
    if group_by == "skill_category":
        return (label.skill.category or "General").strip() or "General"
    return "overall"


def evaluate_top_n_relevance(
    *,
    horizon_years: int,
    as_of_date: Optional[date],
    group_by: str,
    top_n: int,
) -> Dict[str, Any]:
    """Compute a proxy hit-rate for Top-N rankings using GOLD labels when available."""
    relevance = {
        "as_of_date": as_of_date,
        "group_by": group_by,
        "top_n": top_n,
        "groups_evaluated": 0,
        "groups_with_labels": 0,
        "hits": 0,
        "hit_rate": None,
        "qualitative_required": True,
    }

    if as_of_date is None:
        return relevance

    label_qs = FutureSkillLabel.objects.filter(
        as_of_date=as_of_date,
        horizon_months=horizon_years * 12,
        level=FutureSkillLabel.LEVEL_HIGH,
    ).select_related("job_role", "skill")

    if not label_qs.exists():
        return relevance

    relevance["qualitative_required"] = False
    label_groups: Dict[str, set[int]] = defaultdict(set)
    for label in label_qs:
        group_key = _resolve_label_group_key(label, group_by)
        label_groups[group_key].add(label.skill_id)

    rankings = get_top_skill_rankings(
        horizon_years=horizon_years,
        as_of_date=as_of_date,
        group_by=group_by,
        top_n=top_n,
        normalize=True,
    )

    groups_with_labels = 0
    hits = 0
    for group in rankings.get("groups", []):
        group_key = group.get("group_key")
        label_skill_ids = label_groups.get(group_key)
        if not label_skill_ids:
            continue
        groups_with_labels += 1
        top_skill_ids = {item.get("skill", {}).get("id") for item in group.get("items", [])}
        if top_skill_ids & label_skill_ids:
            hits += 1

    relevance["groups_evaluated"] = len(rankings.get("groups", []))
    relevance["groups_with_labels"] = groups_with_labels
    relevance["hits"] = hits
    if groups_with_labels:
        relevance["hit_rate"] = round(hits / groups_with_labels, 4)

    return relevance


def get_top_skill_rankings(
    *,
    horizon_years: int = 5,
    as_of_date: Optional[date] = None,
    group_by: str = "department",
    top_n: int = 5,
    normalize: bool = True,
    include_relevance: bool = False,
) -> Dict[str, Any]:
    """Return Top-N rankings grouped by the requested dimension."""
    if top_n <= 0:
        top_n = 0

    group_by = (group_by or "department").lower()
    if group_by not in ALLOWED_GROUP_BY:
        raise ValueError(f"group_by must be one of {sorted(ALLOWED_GROUP_BY)}")

    queryset = (
        FutureSkillPrediction.objects.filter(horizon_years=horizon_years)
        .select_related("job_role", "skill")
        .order_by("-score")
    )

    if as_of_date:
        queryset = queryset.filter(as_of_date=as_of_date)
    else:
        latest_date = (
            queryset.exclude(as_of_date__isnull=True).aggregate(Max("as_of_date")).get("as_of_date__max")
        )
        if latest_date:
            queryset = queryset.filter(as_of_date=latest_date)
            as_of_date = latest_date

    groups: Dict[str, List[FutureSkillPrediction]] = defaultdict(list)
    for prediction in queryset:
        group_key = _resolve_group_key(prediction, group_by)
        groups[group_key].append(prediction)

    response_groups = []
    normalization_method = "min_max_group" if normalize else "none"

    for group_key in sorted(groups.keys()):
        group_predictions = groups[group_key]
        if not group_predictions:
            continue

        scores = [float(pred.score) for pred in group_predictions]
        min_score = min(scores)
        max_score = max(scores)
        span = max_score - min_score

        sorted_predictions = sorted(
            group_predictions,
            key=lambda pred: (pred.score, pred.skill.name or ""),
            reverse=True,
        )

        items = []
        for index, pred in enumerate(sorted_predictions[:top_n], start=1):
            normalized_score = None
            if normalize:
                normalized_score = 1.0 if span == 0 else (float(pred.score) - min_score) / span

            items.append(
                {
                    "rank": index,
                    "score": float(pred.score),
                    "score_normalized": round(normalized_score, 4) if normalized_score is not None else None,
                    "level": pred.level,
                    "horizon_years": pred.horizon_years,
                    "as_of_date": pred.as_of_date,
                    "job_role": {
                        "id": pred.job_role_id,
                        "name": pred.job_role.name,
                        "department": pred.job_role.department,
                        "description": pred.job_role.description,
                    },
                    "skill": {
                        "id": pred.skill_id,
                        "name": pred.skill.name,
                        "category": pred.skill.category,
                        "description": pred.skill.description,
                    },
                    "job_department": pred.job_role.department or "General",
                    "skill_category": pred.skill.category or "General",
                }
            )

        response_groups.append(
            {
                "group_key": group_key,
                "group_label": group_key,
                "total_predictions": len(group_predictions),
                "min_score": round(min_score, 2),
                "max_score": round(max_score, 2),
                "items": items,
            }
        )

    response = {
        "group_by": group_by,
        "horizon_years": horizon_years,
        "as_of_date": as_of_date,
        "top_n": top_n,
        "normalize": normalize,
        "normalization_method": normalization_method,
        "groups": response_groups,
    }
    if include_relevance:
        response["relevance"] = evaluate_top_n_relevance(
            horizon_years=horizon_years,
            as_of_date=as_of_date,
            group_by=group_by,
            top_n=top_n,
        )
    return response
