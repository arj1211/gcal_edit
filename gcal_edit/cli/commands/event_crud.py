from __future__ import annotations

from typing import TYPE_CHECKING, List

from gcal_edit.dsl.handlers import (
    handle_add as dsl_add,
)
from gcal_edit.dsl.handlers import (
    handle_delete as dsl_delete,
)
from gcal_edit.dsl.handlers import (
    handle_edit as dsl_edit,
)
from gcal_edit.dsl.handlers import (
    handle_transfer as dsl_transfer,
)
from gcal_edit.dsl.types import DSLAction, ExecutionContext
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

    # Delegate to DSL handler
    action = DSLAction(
        verb="add",
        assignments={"name": summary, "date": date, "description": description},
    )
    context = ExecutionContext(
        calendar_id=cli.selected_calendar_id, calendar_name=cli.selected_calendar_name
    )
    dsl_add(cli.dsl, action, context)


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

    # Delegate to DSL handler
    action = DSLAction(
        verb="edit",
        assignments={"name": summary, "date": date, "description": description},
    )
    context = ExecutionContext(
        calendar_id=cli.selected_calendar_id,
        calendar_name=cli.selected_calendar_name,
        filtered_events=[event],
    )
    dsl_edit(cli.dsl, action, context)


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

    event = cli.manager.get_event(cli.selected_calendar_id, event_id)
    if not event:
        print("Event not found.")
        return

    # Delegate to DSL handler
    action = DSLAction(verb="delete")
    context = ExecutionContext(
        calendar_id=cli.selected_calendar_id,
        calendar_name=cli.selected_calendar_name,
        filtered_events=[event],
    )
    dsl_delete(cli.dsl, action, context)


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

    event = cli.manager.get_event(cli.selected_calendar_id, event_id)
    if not event:
        print("Event not found.")
        return

    target = cli.prompt_field("Target calendar name or ID")
    delete_source = cli.prompt_field("Delete from source? (y/N)", "N").lower() in (
        "y",
        "yes",
    )

    # Delegate to DSL handler
    action = DSLAction(
        verb="transfer",
        target_calendar=target,
        assignments={"delete_source": "true" if delete_source else "false"},
    )
    context = ExecutionContext(
        calendar_id=cli.selected_calendar_id,
        calendar_name=cli.selected_calendar_name,
        filtered_events=[event],
    )
    dsl_transfer(cli.dsl, action, context)
    print("Event transferred." if new_id else "Transfer failed.")
