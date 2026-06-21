from __future__ import annotations

from typing import TYPE_CHECKING, List

from gcal_edit.dsl.handlers import handle_create as dsl_create
from gcal_edit.dsl.types import DSLAction, ExecutionContext
from gcal_edit.service.calendar_service import DEFAULT_TIMEZONE

if TYPE_CHECKING:
    from gcal_edit.cli.calendar_cli import CalendarCLI


def handle_create(cli: "CalendarCLI", args: List[str]) -> None:
    name = cli.prompt_field("Calendar name")
    if not name:
        print("Calendar name required.")
        return
    tz = cli.prompt_field("Time zone", DEFAULT_TIMEZONE)

    # Delegate to DSL handler
    action = DSLAction(verb="create", assignments={"name": name, "time_zone": tz})
    # Context doesn't really matter for create, but we need one
    context = ExecutionContext(calendar_id="", calendar_name="")
    dsl_create(cli.dsl, action, context)

    # Refresh list after creation
    cli.refresh_calendar_list()
