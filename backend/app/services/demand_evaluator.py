from __future__ import annotations

from datetime import datetime, timedelta


# Activity type -> base demand weight (0-1)
TYPE_WEIGHTS: dict[str, float] = {
    "exam": 0.9,
    "concert": 0.8,
    "exhibition": 0.7,
    "sports": 0.6,
    "festival": 0.5,
    "conference": 0.4,
    "other": 0.3,
}

# Attendee brackets -> scale score (0-1)
def _scale_score(attendees: int | None) -> float:
    if attendees is None:
        return 0.3
    if attendees >= 50000:
        return 1.0
    if attendees >= 10000:
        return 0.8
    if attendees >= 5000:
        return 0.6
    if attendees >= 1000:
        return 0.4
    return 0.3


# Duration score (0-1): longer events -> higher demand
def _duration_score(start_time: datetime, end_time: datetime) -> float:
    days = (end_time - start_time).days + 1
    if days >= 7:
        return 1.0
    if days >= 3:
        return 0.7
    if days >= 2:
        return 0.4
    return 0.2


# Proximity score (0-1): events within 7 days get bonus
def _proximity_score(start_time: datetime, now: datetime | None = None) -> float:
    if now is None:
        now = datetime.utcnow()
    days_until = (start_time - now).days
    if days_until < 0:
        return 0.1  # already started
    if days_until <= 3:
        return 1.0
    if days_until <= 7:
        return 0.7
    if days_until <= 14:
        return 0.4
    return 0.2


def evaluate_demand(
    activity_type: str,
    estimated_attendees: int | None,
    start_time: datetime,
    end_time: datetime,
    now: datetime | None = None,
) -> tuple[str, float]:
    """Evaluate demand level and score for an activity.

    Returns (demand_level, demand_score):
        demand_level: "high" | "medium" | "low"
        demand_score: 0.0 - 1.0
    """
    type_w = TYPE_WEIGHTS.get(activity_type, TYPE_WEIGHTS["other"])
    scale_s = _scale_score(estimated_attendees)
    dur_s = _duration_score(start_time, end_time)
    prox_s = _proximity_score(start_time, now)

    # Weighted combination
    score = 0.40 * type_w + 0.30 * scale_s + 0.15 * dur_s + 0.15 * prox_s
    score = round(min(max(score, 0.0), 1.0), 2)

    if score >= 0.7:
        level = "high"
    elif score >= 0.4:
        level = "medium"
    else:
        level = "low"

    return level, score
