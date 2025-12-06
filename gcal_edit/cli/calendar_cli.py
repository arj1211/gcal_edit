from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from gcal_edit.cli.command_router import COMMAND_HANDLERS
from gcal_edit.dsl import DSLInterpreter
from gcal_edit.service.calendar_rules import CalendarRulesManager
from gcal_edit.service.calendar_service import (
    CalendarManager,
    authenticate_google_calendar,
)


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
        self.dsl = DSLInterpreter()
        self.refresh_calendar_list()

    def refresh_calendar_list(self) -> None:
        self.calendars = self.manager.list_calendars()

    def refresh_events(self) -> None:
        if not self.selected_calendar_id:
            self.events = []
            return
        self.events = self.manager.list_events(self.selected_calendar_id)

    def require_calendar(self) -> bool:
        if not self.selected_calendar_id:
            print("Select a calendar first (use the calendars and select commands).")
            return False
        return True

    def resolve_event_by_index(self, reference: str) -> Optional[str]:
        if reference.isdigit():
            idx = int(reference) - 1
            if 0 <= idx < len(self.events):
                return self.events[idx].get("id")
            print("Event index out of range.")
            return None
        return reference

    def prompt_field(self, label: str, default: str | None = None) -> str:
        prompt = f"{label}" + (f" [{default}]" if default else "") + ": "
        value = input(prompt).strip()
        return value if value else (default or "")

    def run_script(self, script_path: Path) -> None:
        try:
            self.dsl.run(script_path)
        except FileNotFoundError:
            print(f"Script file not found: {script_path}")
        except Exception as exc:
            print(f"Unable to run script {script_path}: {exc}")

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
            handler = COMMAND_HANDLERS.get(command)
            if handler:
                handler(self, args)
            else:
                print("Unknown command. Type help to list available commands.")
