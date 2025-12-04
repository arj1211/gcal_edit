import argparse
import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from calendar_rules import CalendarRulesManager
from calendar_service import (
    DEFAULT_TIMEZONE,
    CalendarManager,
    authenticate_google_calendar,
)
from dsl_filters import filter_events

CALENDAR_SELECTOR = re.compile(r"calendar\[(?P<quote>['\"])(?P<id>.+?)(?P=quote)\]")
PATH_LITERAL = re.compile(r"['\"](?P<path>[^'\"]+)['\"]")


@dataclass
class DSLAction:
    verb: str
    target_calendar: Optional[str] = None
    path: Optional[str] = None
    filters: List[str] = field(default_factory=list)
    assignments: Dict[str, str] = field(default_factory=dict)


@dataclass
class DSLBlock:
    calendar_name: str
    actions: List[DSLAction] = field(default_factory=list)


@dataclass
class ExecutionContext:
    calendar_id: str
    calendar_name: str
    filtered_events: List[Dict[str, Any]] = field(default_factory=list)


class DSLInterpreter:
    def __init__(self) -> None:
        service = authenticate_google_calendar()
        self.manager = CalendarManager(service)
        self.rules = CalendarRulesManager()
        self.calendars = self.manager.list_calendars()

    def run(self, script_path: Path) -> None:
        for block in parse_script(script_path):
            calendar_id = self.resolve_calendar(block.calendar_name)
            if not calendar_id:
                print(f"Skipping block: calendar '{block.calendar_name}' not found")
                continue
            context = ExecutionContext(
                calendar_id=calendar_id, calendar_name=block.calendar_name
            )
            for action in block.actions:
                handler = getattr(self, f"_handle_{action.verb}", None)
                if not handler:
                    print(
                        f"Unknown action '{action.verb}' in block for {block.calendar_name}"
                    )
                    continue
                handler(action, context)

    def resolve_calendar(self, identifier: str) -> Optional[str]:
        for calendar in self.calendars:
            if (
                calendar.get("summary", "") == identifier
                or calendar.get("id") == identifier
            ):
                return calendar.get("id")
        # try to refresh list if not found
        self.calendars = self.manager.list_calendars()
        for calendar in self.calendars:
            if (
                calendar.get("summary", "") == identifier
                or calendar.get("id") == identifier
            ):
                return calendar.get("id")
        return None

    def _handle_events(self, action: DSLAction, context: ExecutionContext) -> None:
        events = self.manager.list_events(context.calendar_id)
        remainder = " | ".join(action.filters)
        filtered = filter_events(events, remainder)
        context.filtered_events = filtered
        print(f"{len(filtered)} events matched filters in {context.calendar_name}")

    def _handle_transfer(self, action: DSLAction, context: ExecutionContext) -> None:
        if not context.filtered_events:
            print(
                "No filtered events to transfer; run 'events' first to build a selection."
            )
            return
        target = action.target_calendar
        if not target:
            print("Transfer action requires a target calendar.")
            return
        target_id = self.resolve_calendar(target)
        if not target_id:
            target_id = self.manager.ensure_calendar(target, time_zone=DEFAULT_TIMEZONE)
        delete_source = action.assignments.get("delete_source", "false").lower() in (
            "true",
            "yes",
            "1",
        )
        for event_data in context.filtered_events:
            event_id = event_data.get("id")
            if not event_id:
                continue
            result = self.manager.transfer_event(
                context.calendar_id, target_id, event_id, delete_source=delete_source
            )
            if result:
                print(f"Transferred event {event_id} to {target}")
        recurrence_value = action.assignments.get("recurrence")
        reminders_value = action.assignments.get("reminders")
        if recurrence_value or reminders_value:
            reminder_minutes = (
                parse_reminder_minutes(reminders_value) if reminders_value else None
            )
            recurrence_list = (
                normalize_recurrence(recurrence_value) if recurrence_value else None
            )
            self.rules.set_rule(
                target_id,
                target,
                recurrence=recurrence_list,
                reminder_minutes=reminder_minutes,
            )
            print(f"Updated rules for {target} after transfer.")

    def _handle_add(self, action: DSLAction, context: ExecutionContext) -> None:
        summary = action.assignments.get("name") or action.assignments.get("summary")
        date = action.assignments.get("date")
        if not summary or not date:
            print("Add action requires both summary/name and date.")
            return
        description = action.assignments.get("description")
        recurrence_value = action.assignments.get("recurrence")
        reminders_value = action.assignments.get("reminders")
        recurrence = normalize_recurrence(recurrence_value)
        reminder_minutes = (
            parse_reminder_minutes(reminders_value) if reminders_value else None
        )
        reminders = (
            [create_reminder(minutes) for minutes in reminder_minutes]
            if reminder_minutes
            else None
        )
        event_id = self.manager.add_event(
            context.calendar_id,
            summary,
            date,
            description=description,
            recurrence=recurrence,
            reminders=reminders,
        )
        if event_id:
            print(f"Added event '{summary}' to {context.calendar_name}")

    def _handle_series(self, action: DSLAction, context: ExecutionContext) -> None:
        clean_keys = {"offsets", "interval_days", "count", "verb"}
        assignment = {
            k: v for k, v in action.assignments.items() if k not in clean_keys
        }
        base = assignment.get("start")
        if not base:
            print("Series action requires a start date.")
            return
        try:
            base_date = date.fromisoformat(base)
        except ValueError:
            print(f"Invalid start date for series: {base}")
            return
        offsets_value = action.assignments.get("offsets")
        interval_value = action.assignments.get("interval_days")
        count_value = action.assignments.get("count")
        offsets: List[int] = []
        if offsets_value:
            offsets = [
                int(seg.strip()) for seg in offsets_value.split(",") if seg.strip()
            ]
        elif interval_value and count_value:
            interval = int(interval_value)
            count = int(count_value)
            offsets = [interval * idx for idx in range(count)]
        else:
            print("Series action needs either offsets or interval+count.")
            return
        target_verb = action.assignments.get("verb", "add")
        name_template = assignment.get("name", "series event {index}")
        for idx, offset in enumerate(offsets, start=1):
            event_date = base_date + timedelta(days=offset)
            decorated = {
                **assignment,
                "date": event_date.isoformat(),
                "name": name_template.format(
                    index=idx, offset=offset, date=event_date.isoformat()
                ),
            }
            child = DSLAction(verb=target_verb, assignments=decorated)
            handler = getattr(self, f"_handle_{target_verb}", None)
            if handler:
                handler(child, context)
            else:
                print(f"Series cannot run unsupported verb '{target_verb}'")

    def _selected_events(self, context: ExecutionContext) -> List[Dict[str, Any]]:
        if context.filtered_events:
            return context.filtered_events
        return []

    def _handle_delete(self, action: DSLAction, context: ExecutionContext) -> None:
        events = self._selected_events(context)
        if not events:
            print("No filtered events to delete; run 'events' first.")
            return
        for event_data in events:
            event_id = event_data.get("id")
            if not event_id:
                continue
            success = self.manager.delete_event(context.calendar_id, event_id)
            if success:
                print(f"Deleted event {event_id} from {context.calendar_name}")

    def _handle_edit(self, action: DSLAction, context: ExecutionContext) -> None:
        events = self._selected_events(context)
        if not events:
            print("No filtered events to edit; run 'events' first.")
            return
        assignment = action.assignments
        for event_data in events:
            event_id = event_data.get("id")
            if not event_id:
                continue
            success = self.manager.update_event(
                context.calendar_id,
                event_id,
                summary=assignment.get("name") or assignment.get("summary"),
                date=assignment.get("date"),
                description=assignment.get("description"),
            )
            if success:
                print(f"Updated event {event_id} in {context.calendar_name}")

    def _handle_rules(self, action: DSLAction, context: ExecutionContext) -> None:
        rule = self.rules.get_rule(context.calendar_id)
        recurrence = rule.get("recurrence", [])
        reminders = [
            str(reminder.get("minutes", 0)) for reminder in rule.get("reminders", [])
        ]
        print(
            f"Rules for {context.calendar_name}: recurrence={recurrence} reminders={reminders}"
        )

    def _handle_set_rules(self, action: DSLAction, context: ExecutionContext) -> None:
        assignment = action.assignments
        recurrence_value = assignment.get("recurrence")
        reminders_value = assignment.get("reminders")
        template = assignment.get("description_template")
        recurrence = normalize_recurrence(recurrence_value)
        reminder_minutes = (
            parse_reminder_minutes(reminders_value) if reminders_value else None
        )
        self.rules.set_rule(
            context.calendar_id,
            context.calendar_name,
            recurrence=recurrence or None,
            reminder_minutes=reminder_minutes if reminder_minutes else None,
            description_template=template,
        )
        print(f"Updated rules for {context.calendar_name}")

    def _handle_create(self, action: DSLAction, context: ExecutionContext) -> None:
        assignment = action.assignments
        name = assignment.get("name") or assignment.get("summary")
        if not name:
            print("Create action needs a calendar name via set name=...")
            return
        tz = assignment.get("time_zone") or DEFAULT_TIMEZONE
        calendar_id = self.manager.ensure_calendar(name, time_zone=tz)
        if calendar_id:
            print(f"Created or found calendar {name}")
        else:
            print(f"Failed to create calendar {name}")

    def _handle_export(self, action: DSLAction, context: ExecutionContext) -> None:
        path = action.path or action.assignments.get("path")
        if not path:
            print("Export action needs a path (e.g. export to 'path.csv').")
            return
        self.manager.export_to_csv(context.calendar_id, path)
        print(f"Exported {context.calendar_name} to {path}")

    def _handle_import(self, action: DSLAction, context: ExecutionContext) -> None:
        path = action.path or action.assignments.get("path")
        if not path:
            print("Import action needs a path (e.g. import from 'rows.csv').")
            return
        rule = self.rules.get_rule(context.calendar_id)
        self.manager.import_from_csv(
            context.calendar_id,
            path,
            recurrence=rule.get("recurrence"),
            reminders=rule.get("reminders"),
        )
        print(f"Imported events from {path} into {context.calendar_name}")

    def _handle_batch(self, action: DSLAction, context: ExecutionContext) -> None:
        path = action.path or action.assignments.get("path")
        if not path:
            print("Batch action needs a path to the CSV file.")
            return
        rule = self.rules.get_rule(context.calendar_id)
        self.manager.batch_edit_from_csv(
            context.calendar_id,
            path,
            recurrence=rule.get("recurrence"),
            reminders=rule.get("reminders"),
        )
        print(f"Processed batch CSV {path} for {context.calendar_name}")


def parse_script(path: Path) -> List[DSLBlock]:
    with open(path, "r", encoding="utf-8") as fh:
        lines = fh.readlines()
    blocks: List[DSLBlock] = []
    current_block: Optional[DSLBlock] = None
    current_action: Optional[DSLAction] = None
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
                current_action.assignments[key] = value
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a gcal-edit DSL script")
    parser.add_argument("script", type=Path, help="Path to the DSL file")
    args = parser.parse_args()
    DSLInterpreter().run(args.script)


if __name__ == "__main__":
    main()
