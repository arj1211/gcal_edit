from __future__ import annotations

from typing import Callable, Dict, List

from gcal_edit.cli.commands.calendars import handle_calendars, handle_select
from gcal_edit.cli.commands.create import handle_create
from gcal_edit.cli.commands.csv import handle_batch, handle_export, handle_import
from gcal_edit.cli.commands.event_crud import (
    handle_add,
    handle_delete,
    handle_edit,
    handle_transfer,
)
from gcal_edit.cli.commands.events import handle_events
from gcal_edit.cli.commands.help import handle_help
from gcal_edit.cli.commands.script import handle_script

COMMANDS: Dict[str, str] = {
    "calendars": "List available calendars",
    "select": "Select a calendar by its number or ID",
    "events": "Show events for the current calendar",
    "add": "Add a new event",
    "edit": "Edit an existing event",
    "delete": "Delete an event",
    "transfer": "Transfer an event to another calendar",
    "export": "Export events to CSV",
    "import": "Import events from CSV",
    "batch": "Run a batch CSV action",
    "create": "Create a new calendar",
    "script": "Run a DSL script",
    "help": "Show this command list",
    "quit": "Exit the CLI",
}

Handler = Callable[["CalendarCLI", List[str]], None]

COMMAND_HANDLERS: Dict[str, Handler] = {
    "calendars": handle_calendars,
    "select": handle_select,
    "events": handle_events,
    "add": handle_add,
    "edit": handle_edit,
    "delete": handle_delete,
    "transfer": handle_transfer,
    "export": handle_export,
    "import": handle_import,
    "batch": handle_batch,
    "create": handle_create,
    "script": handle_script,
    "help": handle_help,
}
