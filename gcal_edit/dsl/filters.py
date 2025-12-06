import re
from typing import Any, Callable, Dict, List, Optional

FilterFn = Callable[[Dict[str, Any]], bool]


def filter_events(events: List[Dict[str, Any]], remainder: str) -> List[Dict[str, Any]]:
    filters = parse_event_filters(remainder)
    if not filters:
        return events
    return [event for event in events if all(f(event) for f in filters)]


def parse_event_filters(remainder: str) -> List[FilterFn]:
    segments = [seg.strip() for seg in remainder.split("|") if seg.strip()]
    filters: List[FilterFn] = []
    for segment in segments:
        normalized = segment.strip()
        if normalized.startswith("(") and normalized.endswith(")"):
            normalized = normalized[1:-1].strip()
        clauses = [
            clause.strip()
            for clause in re.split(r"\s*&\s*", normalized)
            if clause.strip()
        ]
        clause_filters: List[FilterFn] = []
        for clause in clauses:
            clause_filter = _build_event_clause_filter(clause)
            if clause_filter:
                clause_filters.append(clause_filter)
        if clause_filters:
            filters.append(
                lambda event, clause_filters=clause_filters: all(
                    clause_filter(event) for clause_filter in clause_filters
                )
            )
    return filters


def _build_event_clause_filter(clause: str) -> Optional[FilterFn]:
    match = re.match(
        r"^(?P<field>\w+)\s*(?P<op><=|>=|!=|=|<|>|match)\s*(?P<value>.+)$",
        clause,
        re.IGNORECASE,
    )
    if not match:
        print(f"Skipping invalid filter clause: {clause}")
        return None
    field = match.group("field")
    op = match.group("op").lower()
    value = _strip_filter_value(match.group("value"))
    if op == "match":
        try:
            pattern = re.compile(value)
        except re.error:
            print(f"Invalid regex in clause: {clause}")
            return None

        return lambda event, field=field, pattern=pattern: bool(
            pattern.search(_get_event_field_value(event, field))
        )

    def comparator(event: Dict[str, Any], field=field, value=value) -> bool:
        actual = _get_event_field_value(event, field)
        if op == "=":
            return actual == value
        if op == "!=":
            return actual != value
        if op == "<":
            return actual < value
        if op == ">":
            return actual > value
        if op == "<=":
            return actual <= value
        if op == ">=":
            return actual >= value
        return False

    return comparator


def _strip_filter_value(value: str) -> str:
    candidate = value.strip()
    if (
        len(candidate) >= 2
        and candidate[0] == candidate[-1]
        and candidate[0] in {'"', "'"}
    ):
        return candidate[1:-1]
    return candidate


def _get_event_field_value(event: Dict[str, Any], field: str) -> str:
    normalized = field.lower()
    if normalized in {"start", "start_date"}:
        return (
            event.get("start", {}).get("dateTime")
            or event.get("start", {}).get("date", "")
            or ""
        )
    if normalized in {"end", "end_date"}:
        return (
            event.get("end", {}).get("dateTime")
            or event.get("end", {}).get("date", "")
            or ""
        )
    if normalized in {"name", "summary", "title"}:
        return event.get("summary", "") or ""
    if normalized == "recurrence":
        return ", ".join(event.get("recurrence", []))
    if normalized in {"location", "venue"}:
        return event.get("location", "") or ""
    if normalized in {"id", "event_id"}:
        return event.get("id", "") or ""
    return str(event.get(field, ""))
