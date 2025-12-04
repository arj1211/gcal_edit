from __future__ import annotations

from typing import TYPE_CHECKING, List

from calendar_service import DEFAULT_TIMEZONE

if TYPE_CHECKING:
    from cli.calendar_cli import CalendarCLI


def handle_create(cli: "CalendarCLI", args: List[str]) -> None:
    name = cli.prompt_field("Calendar name")
    if not name:
        print("Calendar name required.")
        return
    tz = cli.prompt_field("Time zone", DEFAULT_TIMEZONE)
    calendar_id = cli.manager.ensure_calendar(name, time_zone=tz)
    if calendar_id:
        print(f"Created or found calendar {name}.")
        cli.refresh_calendar_list()
    else:
        print("Failed to create calendar.")
