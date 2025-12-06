from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from gcal_edit.cli.calendar_cli import CalendarCLI


def handle_script(cli: "CalendarCLI", args: List[str]) -> None:
    path = args[0] if args else cli.prompt_field("Script path")
    if not path:
        print("Script path required.")
        return
    script_path = Path(path)
    cli.run_script(script_path)
