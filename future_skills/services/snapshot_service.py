"""Helpers for snapshot-based feature extraction and silver labels."""

import calendar
import math
import random
import statistics
from datetime import date
from typing import Optional

from future_skills.models import EconomicReport, FutureSkillSnapshot, MarketTrend

TECHNICAL_KEYWORDS = [
    "python",
    "ia",
    "data",
    "cloud",
    "devops",
    "machine learning",
    "blockchain",
    "cybersecurity",
    "kubernetes",
    "java",
    "javascript",
    "aws",
    "azure",
    "docker",
    "sql",
    "nosql",
]

SENIOR_KEYWORDS = ["senior", "lead", "manager", "director", "chief", "head"]

IT_DEPARTMENTS = ["IT", "Tech", "Data", "Engineering", "R&D"]
BASELINE_DATE = date(2019, 1, 1)
STABILITY_VOLATILITY_THRESHOLD = 0.05
PERSISTENCE_THRESHOLD = 0.6
LOW_SAMPLE_THRESHOLD = 10.0

DEFAULT_TIME_FEATURES = {
    "trend_momentum": 0.0,
    "trend_acceleration": 0.0,
    "trend_volatility": 0.0,
    "trend_persistence": 0.0,
    "internal_usage_momentum": 0.0,
    "training_requests_momentum": 0.0,
    "internal_usage_lag_1": 0.0,
    "internal_usage_lag_2": 0.0,
    "internal_usage_roll_mean_3": 0.0,
    "training_requests_lag_1": 0.0,
    "training_requests_lag_2": 0.0,
    "training_requests_roll_mean_3": 0.0,
    "economic_indicator_lag_1": 0.0,
    "economic_indicator_lag_2": 0.0,
    "economic_indicator_roll_mean_3": 0.0,
    "trend_stability_flag": 0.0,
    "internal_usage_stability_flag": 0.0,
    "training_requests_stability_flag": 0.0,
    "data_quality_window_coverage": 0.0,
    "data_quality_missing_flag": 1.0,
    "data_quality_stale_flag": 0.0,
    "data_quality_low_sample_flag": 0.0,
    "forecast_trend_score": 0.0,
    "forecast_internal_usage": 0.0,
    "forecast_training_requests": 0.0,
    "forecast_need_score": 0.0,
}


def add_months(base_date: date, months: int) -> date:
    """Return a date offset by the given number of months."""
    if months == 0:
        return base_date

    month_index = base_date.month - 1 + months
    year = base_date.year + month_index // 12
    month = month_index % 12 + 1
    day = min(base_date.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def normalize_training_requests(training_requests: float, max_requests: float = 100.0) -> float:
    """Normalize training requests to [0, 1]."""
    if max_requests <= 0:
        return 0.0
    value = training_requests / max_requests
    return max(0.0, min(1.0, value))


def get_market_trend_for_context(job_role, skill, as_of_date: Optional[date] = None) -> float:
    """Fetch the most relevant market trend score for this context."""
    trends = MarketTrend.objects.all()
    if as_of_date:
        trends = trends.filter(year__lte=as_of_date.year)

    if job_role.department:
        trend = trends.filter(sector__icontains=job_role.department).order_by("-year", "-trend_score").first()
        if trend:
            return max(0.0, min(1.0, float(trend.trend_score)))

    if skill.category:
        trend = trends.filter(sector__icontains=skill.category).order_by("-year", "-trend_score").first()
        if trend:
            return max(0.0, min(1.0, float(trend.trend_score)))

    trend = (trends.filter(sector__iexact="Tech").order_by("-year", "-trend_score").first()) or trends.order_by(
        "-year", "-trend_score"
    ).first()

    if trend:
        return max(0.0, min(1.0, float(trend.trend_score)))

    return 0.5


def get_economic_indicator(job_role, as_of_date: Optional[date] = None) -> float:
    """Return a normalized economic indicator value for the job role context."""
    reports = EconomicReport.objects.all()
    if as_of_date:
        reports = reports.filter(year__lte=as_of_date.year)

    dept = job_role.department or "Tech"
    report = reports.filter(sector__icontains=dept).order_by("-year").first()

    if report:
        normalized = report.value / 100.0
        return max(0.0, min(1.0, normalized))

    return 0.5


def compute_time_features(
    window_snapshots: list[FutureSkillSnapshot],
    *,
    expected_window_months: int | None = None,
    as_of_date: date | None = None,
    horizon_months: int | None = None,
) -> dict:
    """Compute time-derived features from a snapshot window."""
    if not window_snapshots:
        features = DEFAULT_TIME_FEATURES.copy()
        if expected_window_months:
            features["data_quality_window_coverage"] = 0.0
            features["data_quality_missing_flag"] = 1.0
        if as_of_date:
            features["data_quality_stale_flag"] = 1.0
        return features

    window_snapshots = sorted(window_snapshots, key=lambda snap: snap.as_of_date)

    trend_values = [snap.trend_score for snap in window_snapshots]
    internal_values = [snap.internal_usage for snap in window_snapshots]
    training_values = [normalize_training_requests(snap.training_requests) for snap in window_snapshots]
    economic_values = [snap.economic_indicator for snap in window_snapshots]

    trend_deltas = [trend_values[i] - trend_values[i - 1] for i in range(1, len(trend_values))]
    internal_deltas = [internal_values[i] - internal_values[i - 1] for i in range(1, len(internal_values))]
    training_deltas = [training_values[i] - training_values[i - 1] for i in range(1, len(training_values))]

    trend_momentum = trend_deltas[-1]
    trend_acceleration = trend_deltas[-1] - trend_deltas[-2] if len(trend_deltas) > 1 else 0.0
    trend_volatility = statistics.pstdev(trend_values) if len(trend_values) > 1 else 0.0
    trend_persistence = (
        sum(1 for delta in trend_deltas if delta > 0) / len(trend_deltas) if trend_deltas else 0.0
    )

    internal_momentum = internal_deltas[-1] if internal_deltas else 0.0
    training_momentum = training_deltas[-1] if training_deltas else 0.0

    def _lag(values: list[float], offset: int) -> float:
        if len(values) > offset:
            return values[-(offset + 1)]
        return values[0]

    internal_lag_1 = _lag(internal_values, 1)
    internal_lag_2 = _lag(internal_values, 2)
    training_lag_1 = _lag(training_values, 1)
    training_lag_2 = _lag(training_values, 2)
    economic_lag_1 = _lag(economic_values, 1)
    economic_lag_2 = _lag(economic_values, 2)

    internal_roll_mean_3 = statistics.mean(internal_values[-3:])
    training_roll_mean_3 = statistics.mean(training_values[-3:])
    economic_roll_mean_3 = statistics.mean(economic_values[-3:])

    internal_volatility = statistics.pstdev(internal_values) if len(internal_values) > 1 else 0.0
    training_volatility = statistics.pstdev(training_values) if len(training_values) > 1 else 0.0

    internal_persistence = (
        sum(1 for delta in internal_deltas if delta > 0) / len(internal_deltas) if internal_deltas else 0.0
    )
    training_persistence = (
        sum(1 for delta in training_deltas if delta > 0) / len(training_deltas) if training_deltas else 0.0
    )

    trend_stability_flag = (
        1.0 if trend_volatility <= STABILITY_VOLATILITY_THRESHOLD and trend_persistence >= PERSISTENCE_THRESHOLD else 0.0
    )
    internal_usage_stability_flag = (
        1.0 if internal_volatility <= STABILITY_VOLATILITY_THRESHOLD and internal_persistence >= PERSISTENCE_THRESHOLD else 0.0
    )
    training_requests_stability_flag = (
        1.0 if training_volatility <= STABILITY_VOLATILITY_THRESHOLD and training_persistence >= PERSISTENCE_THRESHOLD else 0.0
    )

    expected = expected_window_months or len(window_snapshots)
    window_coverage = len(window_snapshots) / expected if expected else 0.0
    missing_flag = 1.0 if expected and len(window_snapshots) < expected else 0.0
    latest_date = window_snapshots[-1].as_of_date
    stale_flag = 1.0 if as_of_date and latest_date < as_of_date else 0.0
    low_sample_flag = 1.0 if window_snapshots[-1].training_requests < LOW_SAMPLE_THRESHOLD else 0.0

    features = {
        "trend_momentum": round(trend_momentum, 4),
        "trend_acceleration": round(trend_acceleration, 4),
        "trend_volatility": round(trend_volatility, 4),
        "trend_persistence": round(trend_persistence, 4),
        "internal_usage_momentum": round(internal_momentum, 4),
        "training_requests_momentum": round(training_momentum, 4),
        "internal_usage_lag_1": round(internal_lag_1, 4),
        "internal_usage_lag_2": round(internal_lag_2, 4),
        "internal_usage_roll_mean_3": round(internal_roll_mean_3, 4),
        "training_requests_lag_1": round(training_lag_1, 4),
        "training_requests_lag_2": round(training_lag_2, 4),
        "training_requests_roll_mean_3": round(training_roll_mean_3, 4),
        "economic_indicator_lag_1": round(economic_lag_1, 4),
        "economic_indicator_lag_2": round(economic_lag_2, 4),
        "economic_indicator_roll_mean_3": round(economic_roll_mean_3, 4),
        "trend_stability_flag": trend_stability_flag,
        "internal_usage_stability_flag": internal_usage_stability_flag,
        "training_requests_stability_flag": training_requests_stability_flag,
        "data_quality_window_coverage": round(window_coverage, 4),
        "data_quality_missing_flag": missing_flag,
        "data_quality_stale_flag": stale_flag,
        "data_quality_low_sample_flag": low_sample_flag,
    }

    forecast_features = compute_forecast_features(
        window_snapshots,
        horizon_months=horizon_months,
    )
    features.update(forecast_features)
    return features


def get_time_features(
    *,
    job_role_id: int,
    skill_id: int,
    as_of_date: date,
    window_months: int = 6,
    horizon_months: int | None = None,
) -> dict:
    """Fetch snapshot window and compute time-derived features."""
    aligned_date = as_of_date.replace(day=1)
    dates = [add_months(aligned_date, -offset) for offset in range(window_months - 1, -1, -1)]
    snapshots = list(
        FutureSkillSnapshot.objects.filter(
            job_role_id=job_role_id,
            skill_id=skill_id,
            as_of_date__in=dates,
        )
    )
    return compute_time_features(
        snapshots,
        expected_window_months=window_months,
        as_of_date=aligned_date,
        horizon_months=horizon_months,
    )


def apply_time_drift(
    base_value: float,
    snapshot_date: date,
    *,
    drift_per_month: float,
    seasonal_amplitude: float,
    noise_amplitude: float,
    rand: random.Random,
    minimum: float = 0.0,
    maximum: float = 1.0,
) -> float:
    """Apply deterministic drift/seasonality/noise to a base signal."""
    months_since_start = (snapshot_date.year - BASELINE_DATE.year) * 12 + (snapshot_date.month - BASELINE_DATE.month)
    seasonal = math.sin(months_since_start / 6.0) * seasonal_amplitude
    drift = months_since_start * drift_per_month
    noise = rand.uniform(-noise_amplitude, noise_amplitude)  # nosec B311
    value = base_value + drift + seasonal + noise
    return max(minimum, min(maximum, value))


def estimate_scarcity_index(job_role, skill, internal_usage: float) -> float:
    """Estimate scarcity index (0-1) based on internal usage and context."""
    base_scarcity = 1.0 - internal_usage

    skill_name_lower = (skill.name or "").lower()
    is_technical = any(keyword in skill_name_lower for keyword in TECHNICAL_KEYWORDS)

    is_it_dept = any(dept in (job_role.department or "") for dept in IT_DEPARTMENTS)

    scarcity = base_scarcity
    if is_technical:
        scarcity = min(1.0, scarcity + 0.15)
    if is_it_dept:
        scarcity = min(1.0, scarcity + 0.10)

    return max(0.0, min(1.0, scarcity))


def estimate_hiring_difficulty(job_role, skill, scarcity_index: float, rand: Optional[random.Random] = None) -> float:
    """Estimate hiring difficulty (0-1) for a job_role/skill."""
    difficulty = scarcity_index

    skill_name_lower = (skill.name or "").lower()
    is_technical = any(keyword in skill_name_lower for keyword in TECHNICAL_KEYWORDS)

    job_name_lower = (job_role.name or "").lower()
    is_senior = any(keyword in job_name_lower for keyword in SENIOR_KEYWORDS)

    if is_technical:
        difficulty = min(1.0, difficulty + 0.20)
    if is_senior:
        difficulty = min(1.0, difficulty + 0.15)

    rand_source = rand or random
    difficulty = difficulty * rand_source.uniform(0.90, 1.10)  # nosec B311

    return max(0.0, min(1.0, difficulty))


def estimate_avg_salary(job_role, skill, hiring_difficulty: float, rand: Optional[random.Random] = None) -> float:
    """Estimate average salary in K/year for a job_role/skill."""
    dept = job_role.department or "Other"
    base_salaries = {
        "IT": 50.0,
        "Tech": 50.0,
        "Data": 55.0,
        "Engineering": 52.0,
        "RH": 40.0,
        "Finance": 48.0,
        "Marketing": 42.0,
        "Sales": 45.0,
    }
    base_salary = base_salaries.get(dept, 40.0)

    job_name_lower = (job_role.name or "").lower()
    is_senior = any(keyword in job_name_lower for keyword in SENIOR_KEYWORDS)

    if is_senior:
        base_salary *= 1.5

    skill_name_lower = (skill.name or "").lower()
    is_technical = any(keyword in skill_name_lower for keyword in TECHNICAL_KEYWORDS)

    if is_technical:
        base_salary *= 1.2

    base_salary = base_salary * (1.0 + hiring_difficulty * 0.4)

    rand_source = rand or random
    salary = base_salary * rand_source.uniform(0.85, 1.15)  # nosec B311

    return round(salary, 2)


def compute_interaction_features(job_role, skill) -> dict:
    """Compute sector/role interaction features."""
    dept = (job_role.department or "").strip()
    dept_lower = dept.lower()
    role_name_lower = (job_role.name or "").lower()
    skill_name_lower = (skill.name or "").lower()
    skill_category_lower = (skill.category or "").lower()

    is_it_department = 1.0 if any(dept_name.lower() == dept_lower for dept_name in IT_DEPARTMENTS) else 0.0
    is_senior_role = 1.0 if any(keyword in role_name_lower for keyword in SENIOR_KEYWORDS) else 0.0
    is_technical_skill = 1.0 if any(keyword in skill_name_lower for keyword in TECHNICAL_KEYWORDS) else 0.0

    dept_skill_alignment = 0.0
    if dept_lower and skill_category_lower:
        if dept_lower in skill_category_lower or skill_category_lower in dept_lower:
            dept_skill_alignment = 1.0
    if is_it_department and is_technical_skill:
        dept_skill_alignment = 1.0

    return {
        "is_it_department": is_it_department,
        "is_senior_role": is_senior_role,
        "is_technical_skill": is_technical_skill,
        "dept_skill_alignment": dept_skill_alignment,
    }


def compute_forecast_features(
    window_snapshots: list[FutureSkillSnapshot],
    *,
    horizon_months: int | None,
) -> dict:
    """Forecast key signals and map into a projected need score."""
    if not window_snapshots or horizon_months is None:
        return {
            "forecast_trend_score": 0.0,
            "forecast_internal_usage": 0.0,
            "forecast_training_requests": 0.0,
            "forecast_need_score": 0.0,
        }

    window_snapshots = sorted(window_snapshots, key=lambda snap: snap.as_of_date)
    base_month = window_snapshots[0].as_of_date.year * 12 + window_snapshots[0].as_of_date.month
    x_values = [
        (snap.as_of_date.year * 12 + snap.as_of_date.month) - base_month for snap in window_snapshots
    ]

    def _forecast(values: list[float]) -> float:
        if len(values) < 2:
            return values[-1]
        x_avg = sum(x_values) / len(x_values)
        y_avg = sum(values) / len(values)
        denom = sum((x - x_avg) ** 2 for x in x_values)
        if denom == 0:
            return values[-1]
        slope = sum((x - x_avg) * (y - y_avg) for x, y in zip(x_values, values)) / denom
        intercept = y_avg - slope * x_avg
        target_x = x_values[-1] + horizon_months
        return intercept + slope * target_x

    trend_values = [snap.trend_score for snap in window_snapshots]
    internal_values = [snap.internal_usage for snap in window_snapshots]
    training_values = [snap.training_requests for snap in window_snapshots]

    forecast_trend = max(0.0, min(1.0, _forecast(trend_values)))
    forecast_internal = max(0.0, min(1.0, _forecast(internal_values)))
    forecast_training = max(0.0, _forecast(training_values))

    training_norm = normalize_training_requests(forecast_training)
    score_0_1 = 0.5 * forecast_trend + 0.3 * forecast_internal + 0.2 * training_norm
    forecast_need_score = round(max(0.0, min(1.0, score_0_1)) * 100.0, 2)

    return {
        "forecast_trend_score": round(forecast_trend, 4),
        "forecast_internal_usage": round(forecast_internal, 4),
        "forecast_training_requests": round(forecast_training, 4),
        "forecast_need_score": forecast_need_score,
    }
