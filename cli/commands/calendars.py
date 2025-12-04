from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from cli.calendar_cli import CalendarCLI


def handle_calendars(cli: "CalendarCLI", args: List[str]) -> None:
    cli.refresh_calendar_list()
    if not cli.calendars:
        print("No calendars available.")
        return
    for idx, cal in enumerate(cli.calendars, start=1):
        print(f"{idx}. {cal.get('summary', 'Unnamed')} (ID {cal.get('id', 'unknown')})")


def handle_select(cli: "CalendarCLI", args: List[str]) -> None:
    if not args:
        print("Usage: select <number|calendar-id>")
        return
    chosen = _choose_calendar(cli.calendars, args[0])
    if not chosen:
        return
    cli.selected_calendar_id = chosen.get("id")
    cli.selected_calendar_name = chosen.get("summary", "Unnamed")
    print(f"Selected calendar: {cli.selected_calendar_name}")
    cli.refresh_events()
    from cli.commands.rules import handle_rules

    handle_rules(cli, [])


def _choose_calendar(
    calendars: List[Dict[str, Any]], identifier: str
) -> Dict[str, Any] | None:
    if identifier.isdigit():
        index = int(identifier) - 1
        if 0 <= index < len(calendars):
            return calendars[index]
        print("Index out of range.")
        return None
    matches = [cal for cal in calendars if cal.get("id") == identifier]
    if matches:
        return matches[0]
    print("No calendar found with that ID.")
    return None
