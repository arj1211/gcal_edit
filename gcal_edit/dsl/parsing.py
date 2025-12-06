import re
from pathlib import Path
from typing import List

from gcal_edit.dsl.types import DSLAction, DSLBlock

CALENDAR_SELECTOR = re.compile(r"calendar\[(?P<quote>['\"])(?P<id>.+?)(?P=quote)\]")
PATH_LITERAL = re.compile(r"['\"](?P<path>[^'\"]+)['\"]")


def parse_script(path: Path) -> List[DSLBlock]:
    with open(path, "r", encoding="utf-8") as fh:
        lines = fh.readlines()
    blocks: List[DSLBlock] = []
    current_block: DSLBlock | None = None
    current_action: DSLAction | None = None
    for raw in lines:
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("calendar["):
            if current_block:
                blocks.append(current_block)
            selector, remainder = stripped.split(">", 1)
            calendar_match = CALENDAR_SELECTOR.search(selector)
            if not calendar_match:
                continue
            calendar_name = calendar_match.group("id")
            current_block = DSLBlock(calendar_name=calendar_name)
            action_text = remainder.strip()
            current_action = parse_action_line(action_text)
            current_block.actions.append(current_action)
        elif stripped.startswith(">") and current_block:
            action_text = stripped[1:].strip()
            current_action = parse_action_line(action_text)
            current_block.actions.append(current_action)
        elif stripped.startswith("|") and current_action:
            clause = stripped[1:].strip()
            if clause.startswith("where "):
                current_action.filters.append(clause[len("where ") :].strip())
            elif clause.startswith("set "):
                assignment = clause[len("set ") :].split("=", 1)
                key = assignment[0].strip().lower()
                value = assignment[1].strip() if len(assignment) > 1 else ""
                current_action.assignments[key] = _strip_literal_value(value)
            else:
                current_action.filters.append(clause)
        else:
            if current_action and stripped:
                current_action.filters.append(stripped)
    if current_block:
        blocks.append(current_block)
    return blocks


def parse_action_line(action_text: str) -> DSLAction:
    verb = action_text.split()[0]
    action = DSLAction(verb=verb)
    remainder = action_text[len(verb) :].strip()
    if verb == "transfer" and remainder:
        if "calendar[" in remainder:
            match = CALENDAR_SELECTOR.search(remainder)
            if match:
                action.target_calendar = match.group("id")
    if verb in {"export", "import", "batch"}:
        path_match = PATH_LITERAL.search(remainder)
        if path_match:
            action.path = path_match.group("path")
    return action


def _strip_literal_value(value: str) -> str:
    candidate = value.strip()
    if (
        len(candidate) >= 2
        and candidate[0] == candidate[-1]
        and candidate[0] in {'"', "'"}
    ):
        body = candidate[1:-1]
        return body.replace(f"\\{candidate[0]}", candidate[0])
    return candidate
