import re
from datetime import timedelta
from typing import Any, Dict, List, Optional


def normalize_recurrence(value: Optional[str]) -> Optional[List[str]]:
    if not value:
        return None
    lookup = {
        "yearly": "RRULE:FREQ=YEARLY",
        "monthly": "RRULE:FREQ=MONTHLY",
        "weekly": "RRULE:FREQ=WEEKLY",
        "daily": "RRULE:FREQ=DAILY",
    }
    candidate = value.strip().lower()
    if candidate in lookup:
        return [lookup[candidate]]
    return [value]


def parse_duration_string(value: str) -> timedelta:
    """Parses a single duration string like '1 week' or '3 days' into a timedelta."""
    value = value.strip().lower()
    match = re.match(r"(?P<count>\d+)\s*(?P<unit>\w+)", value)
    if not match:
        # Fallback: assume it's just days if it's a number
        if value.isdigit():
            return timedelta(days=int(value))
        return timedelta(days=0)

    amount = int(match.group("count"))
    unit = match.group("unit")

    if unit.startswith("week"):
        return timedelta(weeks=amount)
    if unit.startswith("day"):
        return timedelta(days=amount)
    if unit.startswith("hour"):
        return timedelta(hours=amount)
    if unit.startswith("minute"):
        return timedelta(minutes=amount)

    return timedelta(days=0)


def parse_reminder_minutes(value: str) -> List[int]:
    fragments = [frag.strip() for frag in value.split(",") if frag.strip()]
    units = {
        "week": 7 * 24 * 60,
        "weeks": 7 * 24 * 60,
        "day": 24 * 60,
        "days": 24 * 60,
        "hour": 60,
        "hours": 60,
        "minute": 1,
        "minutes": 1,
    }
    results: List[int] = []
    for frag in fragments:
        match = re.match(r"(?P<count>\d+)\s*(?P<unit>\w+)", frag)
        if not match:
            continue
        amount = int(match.group("count"))
        unit = match.group("unit").lower()
        multiplier = units.get(unit, None)
        if multiplier:
            results.append(amount * multiplier)
    return results


def create_reminder(minutes: int) -> Dict[str, Any]:
    return {"method": "popup", "minutes": minutes}
