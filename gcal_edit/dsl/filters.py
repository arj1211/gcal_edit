import re
from typing import Any, Callable, Dict, List, Optional

FilterFn = Callable[[Dict[str, Any]], bool]


def filter_events(events: List[Dict[str, Any]], remainder: str) -> List[Dict[str, Any]]:
    """
    Filters a list of events based on a pipe-separated string of filter expressions.
    Each segment in the pipe is treated as an AND condition.
    Inside each segment, we support boolean logic (AND/OR) via a simple recursive parser.
    """
    # Split by pipe to get individual 'where' clauses (which are implicitly ANDed)
    # Note: The caller (handlers.py) joins multiple filter lines with " | ".
    # So "where A | where B" becomes "A | B".
    segments = [seg.strip() for seg in remainder.split("|") if seg.strip()]

    if not segments:
        return events

    # Compile all filter functions
    filters: List[FilterFn] = []
    for segment in segments:
        fn = parse_boolean_expression(segment)
        if fn:
            filters.append(fn)

    # Apply all filters
    return [event for event in events if all(f(event) for f in filters)]


def parse_boolean_expression(expression: str) -> Optional[FilterFn]:
    """
    Parses a boolean expression string like "(A or B) and C".
    Returns a FilterFn or None if parsing fails.
    """
    # This is a simplified parser. For a full robust parser, we'd need a tokenizer and AST.
    # For now, we'll handle simple cases and rely on Python's eval for complex logic
    # IF we can safely map the variables.
    # BUT eval is dangerous. Let's stick to a custom recursive parser for AND/OR.

    # Normalize
    expr = expression.strip()

    # Handle Parentheses (simplest case: outer parens)
    if expr.startswith("(") and expr.endswith(")"):
        # Check if these are matching outer parens
        depth = 0
        is_outer = True
        for i, char in enumerate(expr[:-1]):
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    is_outer = False
                    break
        if is_outer:
            return parse_boolean_expression(expr[1:-1])

    # Split by OR (lowest precedence)
    # We need to split by ' or ' but respect parentheses
    or_parts = _split_respecting_parens(expr, " or ")
    if len(or_parts) > 1:
        sub_filters = [parse_boolean_expression(p) for p in or_parts]
        # Filter out Nones
        valid_subs = [f for f in sub_filters if f]
        if not valid_subs:
            return None
        return lambda event: any(f(event) for f in valid_subs)

    # Split by AND (higher precedence)
    and_parts = _split_respecting_parens(expr, " and ")
    if len(and_parts) > 1:
        sub_filters = [parse_boolean_expression(p) for p in and_parts]
        valid_subs = [f for f in sub_filters if f]
        if not valid_subs:
            return None
        return lambda event: all(f(event) for f in valid_subs)

    # Also support '&' as AND for backward compatibility/convenience
    amp_parts = _split_respecting_parens(expr, "&")
    if len(amp_parts) > 1:
        sub_filters = [parse_boolean_expression(p) for p in amp_parts]
        valid_subs = [f for f in sub_filters if f]
        if not valid_subs:
            return None
        return lambda event: all(f(event) for f in valid_subs)

    # Base case: Single clause
    return _build_event_clause_filter(expr)


def _split_respecting_parens(text: str, separator: str) -> List[str]:
    """Splits text by separator, ignoring separators inside parentheses."""
    parts = []
    current = []
    depth = 0
    sep_len = len(separator)
    i = 0
    while i < len(text):
        if text[i] == "(":
            depth += 1
            current.append(text[i])
            i += 1
        elif text[i] == ")":
            depth -= 1
            current.append(text[i])
            i += 1
        elif depth == 0 and text[i : i + sep_len].lower() == separator:
            parts.append("".join(current))
            current = []
            i += sep_len
        else:
            current.append(text[i])
            i += 1
    parts.append("".join(current))
    return parts


def _build_event_clause_filter(clause: str) -> Optional[FilterFn]:
    clause = clause.strip()
    match = re.match(
        r"^(?P<field>\w+)\s*(?P<op><=|>=|!=|=|<|>|match)\s*(?P<value>.+)$",
        clause,
        re.IGNORECASE,
    )
    if not match:
        # print(f"Skipping invalid filter clause: {clause}") # Reduce noise
        return None
    field = match.group("field")
    op = match.group("op").lower()
    value = _strip_filter_value(match.group("value"))

    if op == "match":
        try:
            pattern = re.compile(
                value, re.IGNORECASE
            )  # Default to case-insensitive for convenience
        except re.error:
            print(f"Invalid regex in clause: {clause}")
            return None

        return lambda event, field=field, pattern=pattern: bool(
            pattern.search(_get_event_field_value(event, field))
        )

    def comparator(event: Dict[str, Any], field=field, value=value) -> bool:
        actual = _get_event_field_value(event, field)
        # Simple string comparison for now.
        # TODO: Add date/int parsing for smarter comparisons
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
    if normalized == "description":
        return event.get("description", "")
    if normalized in {"location", "venue"}:
        return event.get("location", "") or ""
    if normalized in {"id", "event_id"}:
        return event.get("id", "") or ""
    if normalized == "recurrence":
        return ", ".join(event.get("recurrence", []))
    return str(event.get(field, ""))
