from __future__ import annotations

from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from gcal_edit.cli.calendar_cli import CalendarCLI


def handle_help(cli: "CalendarCLI", args: List[str]) -> None:
    from gcal_edit.cli.command_router import COMMANDS

    for command, description in COMMANDS.items():
        print(f"{command}: {description}")
