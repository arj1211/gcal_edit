from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from gcal_edit.cli.calendar_cli import CalendarCLI


def handle_calendars(cli: "CalendarCLI", args: List[str]) -> None:
    cli.refresh_calendar_list()
    if not cli.calendars:
        print("No calendars available.")
        return
    for idx, cal in enumerate(cli.calendars, start=1):
        print(f"{idx}. {cal.get('summary', 'Unnamed')} (ID {cal.get('id', 'unknown')})")


def handle_select(cli: "CalendarCLI", args: List[str]) -> None:
    if not args:
        print("Usage: select <number|calendar-id|calendar-name>")
        return
    # Join args to allow spaces in calendar names (e.g. "select My Calendar")
    identifier = " ".join(args)
    chosen = _choose_calendar(cli.calendars, identifier)
    if not chosen:
        return
    cli.selected_calendar_id = chosen.get("id")
    cli.selected_calendar_name = chosen.get("summary", "Unnamed")
    print(f"Selected calendar: {cli.selected_calendar_name}")
    cli.refresh_events()


def _choose_calendar(
    calendars: List[Dict[str, Any]], identifier: str
) -> Dict[str, Any] | None:
    # 1. Try Index
    if identifier.isdigit():
        index = int(identifier) - 1
        if 0 <= index < len(calendars):
            return calendars[index]
        # If it's a digit but out of range, it might be a calendar name that happens to be a number?
        # Unlikely, but let's fall through just in case, or just return None as before.
        # The original code returned None. Let's stick to that for digits to avoid confusion.
        print("Index out of range.")
        return None

    # 2. Try Exact ID
    matches = [cal for cal in calendars if cal.get("id") == identifier]
    if matches:
        return matches[0]

    # 3. Try Name (Case-insensitive)
    lower_id = identifier.lower()
    name_matches = [
        cal for cal in calendars if cal.get("summary", "").lower() == lower_id
    ]
    if len(name_matches) == 1:
        return name_matches[0]
    elif len(name_matches) > 1:
        print(
            f"Multiple calendars found with name '{identifier}'. Please use ID or Index."
        )
        return None

    # 4. Try Partial Name (Case-insensitive)
    partial_matches = [
        cal for cal in calendars if lower_id in cal.get("summary", "").lower()
    ]
    if len(partial_matches) == 1:
        return partial_matches[0]
    elif len(partial_matches) > 1:
        print(f"Multiple calendars match '{identifier}'. Please be more specific.")
        return None

    print("No calendar found with that ID or Name.")
    return None
