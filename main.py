import re
from typing import Any, Callable, Dict, List, Optional

from calendar_rules import CalendarRulesManager
from calendar_service import (
    DEFAULT_TIMEZONE,
    CalendarManager,
    authenticate_google_calendar,
)

COMMANDS = {
    "calendars": "List available calendars",
    "select": "Select a calendar by its number or ID",
    "events": "Show events for the current calendar",
    "add": "Add a new event",
    "edit": "Edit an existing event",
    "delete": "Delete an event",
    "transfer": "Transfer an event to another calendar",
    "rules": "Show the current calendar's rule set",
    "set-rules": "Update recurrence/reminders for the selected calendar",
    "export": "Export events to CSV",
    "import": "Import events from CSV",
    "batch": "Run a batch CSV action",
    "create": "Create a new calendar",
    "help": "Show this command list",
    "quit": "Exit the CLI",
}


class CalendarCLI:
    """Simple interactive CLI that drives the Google Calendar helpers."""

    prompt = "gcal> "

    def __init__(self) -> None:
        service = authenticate_google_calendar()
        self.manager = CalendarManager(service)
        self.rules = CalendarRulesManager()
        self.calendars: List[Dict[str, Any]] = []
        self.selected_calendar_id: Optional[str] = None
        self.selected_calendar_name: str = ""
        self.events: List[Dict[str, Any]] = []
        self.last_command_remainder: str = ""
        self.refresh_calendar_list()

    def refresh_calendar_list(self) -> None:
        self.calendars = self.manager.list_calendars()

    def run(self) -> None:
        print("Google Calendar CLI (type help for commands)")
        while True:
            try:
                raw = input(self.prompt).strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not raw:
                continue
            parts = raw.split(None, 1)
            command = parts[0].lower()
            remainder = parts[1].strip() if len(parts) > 1 else ""
            self.last_command_remainder = remainder
            args = remainder.split()
            if command in {"quit", "exit"}:
                break
            handler = getattr(self, f"command_{command.replace('-', '_')}", None)
            if handler:
                handler(args)
            else:
                print("Unknown command. Type help to list available commands.")

    def command_calendars(self, args: List[str]) -> None:
        self.refresh_calendar_list()
        if not self.calendars:
            print("No calendars available.")
            return
        for idx, cal in enumerate(self.calendars, start=1):
            print(
                f"{idx}. {cal.get('summary', 'Unnamed')} (ID {cal.get('id', 'unknown')})"
            )

    def select_calendar_by_index(self, identifier: str) -> bool:
        if identifier.isdigit():
            number = int(identifier) - 1
            if 0 <= number < len(self.calendars):
                chosen = self.calendars[number]
            else:
                print("Index out of range.")
                return False
        else:
            matches = [cal for cal in self.calendars if cal.get("id") == identifier]
            if matches:
                chosen = matches[0]
            else:
                print("No calendar found with that ID.")
                return False
        self.selected_calendar_id = chosen.get("id")
        self.selected_calendar_name = chosen.get("summary", "Unnamed")
        print(f"Selected calendar: {self.selected_calendar_name}")
        return True

    def command_select(self, args: List[str]) -> None:
        if not args:
            print("Usage: select <number|calendar-id>")
            return
        if self.select_calendar_by_index(args[0]):
            self.refresh_events()
            self.command_rules([])

    def refresh_events(self) -> None:
        if not self.selected_calendar_id:
            self.events = []
            return
        self.events = self.manager.list_events(self.selected_calendar_id)

    def command_events(self, args: List[str]) -> None:
        if not self.require_calendar():
            return
        self.refresh_events()
        if not self.events:
            print("No events for this calendar.")
            return

        def event_sort_key(event: Dict[str, Any]) -> tuple[str, str, str, str]:
            start = event.get("start", {}).get("date") or event.get("start", {}).get(
                "dateTime", ""
            )
            end = event.get("end", {}).get("date") or event.get("end", {}).get(
                "dateTime", ""
            )
            recurrence = "-".join(event.get("recurrence", []) or [])
            summary = event.get("summary", "")
            return start, end, recurrence, summary

        sorted_events = sorted(self.events, key=event_sort_key)
        filtered_events = self._apply_event_filters(
            sorted_events, self.last_command_remainder
        )
        if not filtered_events:
            print("No events for this calendar.")
            return

        header = [
            "Index",
            "Name",
            "Start Date",
            "End Date",
            "Recurrence Schedule",
            "Location",
            "Event ID",
        ]
        column_limits = {
            "Index": 6,
            "Name": 30,
            "Start Date": 30,
            "End Date": 30,
            "Recurrence Schedule": 30,
            "Location": 30,
            "Event ID": 30,
        }

        def clamp(value: str, max_len: int) -> str:
            if len(value) <= max_len:
                return value
            if max_len <= 3:
                return value[:max_len]
            return value[: max_len - 3] + "..."

        display_rows: List[List[str]] = []
        for index, event in enumerate(filtered_events, start=1):
            start = event.get("start", {}).get("date") or event.get("start", {}).get(
                "dateTime", ""
            )
            end = event.get("end", {}).get("date") or event.get("end", {}).get(
                "dateTime", ""
            )
            recurrence = ", ".join(event.get("recurrence", []))
            location = event.get("location", "")
            row = [
                str(index),
                event.get("summary", "Unnamed event"),
                start,
                end,
                recurrence or "-",
                location,
                event.get("id", ""),
            ]
            display_rows.append(
                [
                    clamp(str(value), column_limits.get(header[idx], 30))
                    for idx, value in enumerate(row)
                ]
            )

        col_widths: List[int] = []
        for idx, column_name in enumerate(header):
            max_len = len(column_name)
            for row in display_rows:
                max_len = max(max_len, len(row[idx]))
            col_widths.append(max_len)

        line = " | ".join(
            header_item.ljust(col_widths[idx]) for idx, header_item in enumerate(header)
        )
        separator = " | ".join("-" * width for width in col_widths)
        print(line)
        print(separator)
        for row in display_rows:
            print(
                " | ".join(row[idx].ljust(col_widths[idx]) for idx in range(len(row)))
            )

    def _apply_event_filters(
        self, events: List[Dict[str, Any]], remainder: str
    ) -> List[Dict[str, Any]]:
        filters = self._parse_event_filters(remainder)
        if not filters:
            return events
        filtered: List[Dict[str, Any]] = []
        for event in events:
            if all(f(event) for f in filters):
                filtered.append(event)
        return filtered

    def _parse_event_filters(
        self, remainder: str
    ) -> List[Callable[[Dict[str, Any]], bool]]:
        segments = [seg.strip() for seg in remainder.split("|") if seg.strip()]
        filters: List[Callable[[Dict[str, Any]], bool]] = []
        for segment in segments:
            normalized = segment.strip()
            if normalized.startswith("(") and normalized.endswith(")"):
                normalized = normalized[1:-1].strip()
            clauses = [
                clause.strip()
                for clause in re.split(r"\s*&\s*", normalized)
                if clause.strip()
            ]
            clause_filters = []
            for clause in clauses:
                clause_filter = self._build_event_clause_filter(clause)
                if clause_filter:
                    clause_filters.append(clause_filter)
            if clause_filters:
                filters.append(
                    lambda event, clause_filters=clause_filters: all(
                        clause_filter(event) for clause_filter in clause_filters
                    )
                )
        return filters

    def _build_event_clause_filter(
        self, clause: str
    ) -> Optional[Callable[[Dict[str, Any]], bool]]:
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
        value = self._strip_filter_value(match.group("value"))
        if op == "match":
            try:
                pattern = re.compile(value)
            except re.error:
                print(f"Invalid regex in clause: {clause}")
                return None

            return lambda event, field=field, pattern=pattern: bool(
                pattern.search(self._get_event_field_value(event, field))
            )

        def comparator(event: Dict[str, Any], field=field, value=value) -> bool:
            actual = self._get_event_field_value(event, field)
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

    def _strip_filter_value(self, value: str) -> str:
        candidate = value.strip()
        if (
            len(candidate) >= 2
            and candidate[0] == candidate[-1]
            and candidate[0] in {"'", '"'}
        ):
            return candidate[1:-1]
        return candidate

    def _get_event_field_value(self, event: Dict[str, Any], field: str) -> str:
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

    def require_calendar(self) -> bool:
        if not self.selected_calendar_id:
            print("Select a calendar first (use the calendars and select commands).")
            return False
        return True

    def prompt_field(self, label: str, default: str | None = None) -> str:
        prompt = f"{label}" + (f" [{default}]" if default else "") + ": "
        value = input(prompt).strip()
        return value if value else (default or "")

    def command_add(self, args: List[str]) -> None:
        if not self.require_calendar():
            return
        summary = self.prompt_field("Summary")
        date = self.prompt_field("Date (YYYY-MM-DD)")
        description = self.prompt_field("Description", "")
        if not summary or not date:
            print("Summary and date are required.")
            return
        rule = self.rules.get_rule(self.selected_calendar_id)
        event_id = self.manager.add_event(
            self.selected_calendar_id,
            summary,
            date,
            description=description or None,
            recurrence=rule.get("recurrence"),
            reminders=rule.get("reminders"),
        )
        if event_id:
            print("Event added.")
        else:
            print("Failed to add event.")

    def resolve_event_by_index(self, reference: str) -> Optional[str]:
        if reference.isdigit():
            idx = int(reference) - 1
            if 0 <= idx < len(self.events):
                return self.events[idx].get("id")
            print("Event index out of range.")
            return None
        return reference

    def command_edit(self, args: List[str]) -> None:
        if not self.require_calendar():
            return
        if not args:
            print("Usage: edit <event-index|event-id>")
            return
        self.refresh_events()
        event_id = self.resolve_event_by_index(args[0])
        if not event_id:
            return
        event = self.manager.get_event(self.selected_calendar_id, event_id)
        if not event:
            print("Event not found.")
            return
        summary = self.prompt_field("Summary", event.get("summary", ""))
        date = self.prompt_field(
            "Date (YYYY-MM-DD)", event.get("start", {}).get("date", "")
        )
        description = self.prompt_field("Description", event.get("description", ""))
        success = self.manager.update_event(
            self.selected_calendar_id,
            event_id,
            summary=summary or None,
            date=date or None,
            description=description or None,
        )
        print("Event updated." if success else "Failed to update event.")

    def command_delete(self, args: List[str]) -> None:
        if not self.require_calendar():
            return
        if not args:
            print("Usage: delete <event-index|event-id>")
            return
        self.refresh_events()
        event_id = self.resolve_event_by_index(args[0])
        if not event_id:
            return
        success = self.manager.delete_event(self.selected_calendar_id, event_id)
        print("Event deleted." if success else "Failed to delete event.")

    def command_transfer(self, args: List[str]) -> None:
        if not self.require_calendar():
            return
        if not args:
            print("Usage: transfer <event-index|event-id>")
            return
        self.refresh_events()
        event_id = self.resolve_event_by_index(args[0])
        if not event_id:
            return
        target = self.prompt_field("Target calendar name or ID")
        delete_source = self.prompt_field("Delete from source? (y/N)", "N").lower() in (
            "y",
            "yes",
        )
        target_id = self.manager.ensure_calendar(target, time_zone=DEFAULT_TIMEZONE)
        if not target_id:
            print("Could not find or create the target calendar.")
            return
        new_id = self.manager.transfer_event(
            self.selected_calendar_id,
            target_id,
            event_id,
            delete_source=delete_source,
        )
        print("Event transferred." if new_id else "Transfer failed.")

    def command_rules(self, args: List[str]) -> None:
        if not self.require_calendar():
            return
        rule = self.rules.get_rule(self.selected_calendar_id)
        recurrence = rule.get("recurrence", [])
        reminders = [
            str(reminder.get("minutes", 0)) for reminder in rule.get("reminders", [])
        ]
        print("Recurrence:", recurrence)
        print("Reminders:", reminders)
        if template := rule.get("description_template"):
            print("Description template:", template)

    def command_set_rules(self, args: List[str]) -> None:
        if not self.require_calendar():
            return
        recurrence_raw = self.prompt_field("Recurrence rules (comma separated)")
        reminder_raw = self.prompt_field("Reminder minutes (comma separated)")
        template = self.prompt_field("Description template", "")
        recurrence = [
            item.strip() for item in recurrence_raw.split(",") if item.strip()
        ]
        reminder_minutes = [
            int(part.strip())
            for part in reminder_raw.split(",")
            if part.strip().isdigit()
        ]
        self.rules.set_rule(
            self.selected_calendar_id,
            self.selected_calendar_name or "",
            recurrence=recurrence or None,
            reminder_minutes=reminder_minutes if reminder_minutes else None,
            description_template=template,
        )
        print("Rules updated.")

    def command_export(self, args: List[str]) -> None:
        if not self.require_calendar():
            return
        path = (
            args[0] if args else self.prompt_field("Export path", "special_dates.csv")
        )
        success = self.manager.export_to_csv(self.selected_calendar_id, path)
        print("Export complete." if success else "Export failed.")

    def command_import(self, args: List[str]) -> None:
        if not self.require_calendar():
            return
        path = (
            args[0] if args else self.prompt_field("Import path", "special_dates.csv")
        )
        rule = self.rules.get_rule(self.selected_calendar_id)
        stats = self.manager.import_from_csv(
            self.selected_calendar_id,
            path,
            recurrence=rule.get("recurrence"),
            reminders=rule.get("reminders"),
        )
        print(f"Import added={stats['added']} skipped={stats['skipped']}")

    def command_batch(self, args: List[str]) -> None:
        if not self.require_calendar():
            return
        path = (
            args[0] if args else self.prompt_field("Batch file path", "batch_edits.csv")
        )
        rule = self.rules.get_rule(self.selected_calendar_id)
        stats = self.manager.batch_edit_from_csv(
            self.selected_calendar_id,
            path,
            recurrence=rule.get("recurrence"),
            reminders=rule.get("reminders"),
        )
        print(
            f"Batch add={stats['added']} update={stats['updated']} delete={stats['deleted']} skipped={stats['skipped']}"
        )

    def command_create(self, args: List[str]) -> None:
        name = self.prompt_field("Calendar name")
        if not name:
            print("Calendar name required.")
            return
        tz = self.prompt_field("Time zone", DEFAULT_TIMEZONE)
        calendar_id = self.manager.ensure_calendar(name, time_zone=tz)
        if calendar_id:
            print(f"Created or found calendar {name}.")
            self.refresh_calendar_list()
        else:
            print("Failed to create calendar.")

    def command_help(self, args: List[str]) -> None:
        for command, description in COMMANDS.items():
            print(f"{command}: {description}")


if __name__ == "__main__":
    CalendarCLI().run()
