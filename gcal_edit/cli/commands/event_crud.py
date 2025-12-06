from __future__ import annotations

from typing import TYPE_CHECKING, List

from gcal_edit.service.calendar_service import DEFAULT_TIMEZONE

if TYPE_CHECKING:
    from gcal_edit.cli.calendar_cli import CalendarCLI


def handle_add(cli: "CalendarCLI", args: List[str]) -> None:
    if not cli.require_calendar():
        return
    summary = cli.prompt_field("Summary")
    date = cli.prompt_field("Date (YYYY-MM-DD)")
    description = cli.prompt_field("Description", "")
    if not summary or not date:
        print("Summary and date are required.")
        return
    rule = cli.rules.get_rule(cli.selected_calendar_id)
    event_id = cli.manager.add_event(
        cli.selected_calendar_id,
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


def handle_edit(cli: "CalendarCLI", args: List[str]) -> None:
    if not cli.require_calendar():
        return
    if not args:
        print("Usage: edit <event-index|event-id>")
        return
    cli.refresh_events()
    event_id = cli.resolve_event_by_index(args[0])
    if not event_id:
        return
    event = cli.manager.get_event(cli.selected_calendar_id, event_id)
    if not event:
        print("Event not found.")
        return
    summary = cli.prompt_field("Summary", event.get("summary", ""))
    date = cli.prompt_field("Date (YYYY-MM-DD)", event.get("start", {}).get("date", ""))
    description = cli.prompt_field("Description", event.get("description", ""))
    success = cli.manager.update_event(
        cli.selected_calendar_id,
        event_id,
        summary=summary or None,
        date=date or None,
        description=description or None,
    )
    print("Event updated." if success else "Failed to update event.")


def handle_delete(cli: "CalendarCLI", args: List[str]) -> None:
    if not cli.require_calendar():
        return
    if not args:
        print("Usage: delete <event-index|event-id>")
        return
    cli.refresh_events()
    event_id = cli.resolve_event_by_index(args[0])
    if not event_id:
        return
    success = cli.manager.delete_event(cli.selected_calendar_id, event_id)
    print("Event deleted." if success else "Failed to delete event.")


def handle_transfer(cli: "CalendarCLI", args: List[str]) -> None:
    if not cli.require_calendar():
        return
    if not args:
        print("Usage: transfer <event-index|event-id>")
        return
    cli.refresh_events()
    event_id = cli.resolve_event_by_index(args[0])
    if not event_id:
        return
    target = cli.prompt_field("Target calendar name or ID")
    delete_source = cli.prompt_field("Delete from source? (y/N)", "N").lower() in (
        "y",
        "yes",
    )
    target_id = cli.manager.ensure_calendar(target, time_zone=DEFAULT_TIMEZONE)
    if not target_id:
        print("Could not find or create the target calendar.")
        return
    new_id = cli.manager.transfer_event(
        cli.selected_calendar_id,
        target_id,
        event_id,
        delete_source=delete_source,
    )
    print("Event transferred." if new_id else "Transfer failed.")
