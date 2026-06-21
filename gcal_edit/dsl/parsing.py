import re
from pathlib import Path
from typing import List, Optional, Tuple

from gcal_edit.dsl.types import DSLAction, DSLBlock

CALENDAR_SELECTOR = re.compile(r"calendar\[(?P<quote>['\"])(?P<id>.+?)(?P=quote)\]")
PATH_LITERAL = re.compile(r"['\"](?P<path>[^'\"]+)['\"]")


def parse_script(path: Path) -> List[DSLBlock]:
    with open(path, "r", encoding="utf-8") as fh:
        lines = fh.readlines()
    blocks: List[DSLBlock] = []
    current_block: DSLBlock | None = None
    current_action: DSLAction | None = None

    # Pre-process lines to handle multi-line statements if needed,
    # but for now we assume line-based structure with pipe continuations.

    for raw in lines:
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # Case 1: New Block Start "calendar['...'] > action"
        if stripped.startswith("calendar["):
            if current_block:
                blocks.append(current_block)

            # Split on first '>' to separate selector from action
            parts = stripped.split(">", 1)
            selector = parts[0].strip()
            remainder = parts[1].strip() if len(parts) > 1 else ""

            calendar_match = CALENDAR_SELECTOR.search(selector)
            if not calendar_match:
                print(f"Invalid calendar selector: {selector}")
                continue

            calendar_name = calendar_match.group("id")
            current_block = DSLBlock(calendar_name=calendar_name)

            if remainder:
                current_action = parse_action_line(remainder)
                current_block.actions.append(current_action)
            else:
                current_action = None

        # Case 2: New Action in current block "> action"
        elif stripped.startswith(">") and current_block:
            action_text = stripped[1:].strip()
            current_action = parse_action_line(action_text)
            current_block.actions.append(current_action)

        # Case 3: Pipe continuation "| where ..." or "| set ..."
        elif stripped.startswith("|") and current_action:
            clause = stripped[1:].strip()
            _parse_pipe_clause(current_action, clause)

        # Case 4: Implicit continuation (legacy support, maybe deprecated?)
        else:
            if current_action and stripped:
                # Treat as a filter if it doesn't start with special chars
                # But ideally we enforce pipes. For now, let's assume it's a filter.
                current_action.filters.append(stripped)

    if current_block:
        blocks.append(current_block)
    return blocks


def _parse_pipe_clause(action: DSLAction, clause: str) -> None:
    """Parses a pipe clause and updates the action."""
    # Handle 'where' clauses
    if clause.startswith("where "):
        filter_expr = clause[len("where ") :].strip()
        action.filters.append(filter_expr)

    # Handle 'set' clauses
    elif clause.startswith("set "):
        assignment_body = clause[len("set ") :].strip()
        # Split on first '=' only
        if "=" in assignment_body:
            key_part, value_part = assignment_body.split("=", 1)
            key = key_part.strip().lower()
            value = _strip_literal_value(value_part.strip())
            action.assignments[key] = value
        else:
            print(f"Invalid assignment clause: {clause}")

    # Fallback: treat as raw filter (legacy behavior)
    else:
        action.filters.append(clause)


def parse_action_line(action_text: str) -> DSLAction:
    """Parses the verb line, e.g. 'transfer to calendar["B"]'"""
    parts = action_text.split(None, 1)
    verb = parts[0]
    remainder = parts[1].strip() if len(parts) > 1 else ""

    action = DSLAction(verb=verb)

    # Special handling for 'transfer' target
    if verb == "transfer" and remainder:
        match = CALENDAR_SELECTOR.search(remainder)
        if match:
            action.target_calendar = match.group("id")

    # Special handling for file paths in export/import/batch
    if verb in {"export", "import", "batch"}:
        path_match = PATH_LITERAL.search(remainder)
        if path_match:
            action.path = path_match.group("path")

    return action


def _strip_literal_value(value: str) -> str:
    """Removes surrounding quotes from a string value."""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        # TODO: Handle escaped quotes properly here if needed
        return value[1:-1]
    return value
