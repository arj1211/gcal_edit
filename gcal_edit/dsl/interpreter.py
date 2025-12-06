from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

from gcal_edit.dsl.handlers import HANDLER_MAP, HandlerFn
from gcal_edit.dsl.parsing import parse_script
from gcal_edit.dsl.types import DSLBlock, ExecutionContext
from gcal_edit.service.calendar_rules import CalendarRulesManager
from gcal_edit.service.calendar_service import (
    CalendarManager,
    authenticate_google_calendar,
)


class DSLInterpreter:
    def __init__(self) -> None:
        service = authenticate_google_calendar()
        self.manager = CalendarManager(service)
        self.rules = CalendarRulesManager()
        self.calendars = self.manager.list_calendars()

    def run(self, script_path: Path) -> None:
        for block in parse_script(script_path):
            calendar_id = self.resolve_calendar(block.calendar_name)
            if not calendar_id:
                print(f"Skipping block: calendar '{block.calendar_name}' not found")
                continue
            context = ExecutionContext(
                calendar_id=calendar_id, calendar_name=block.calendar_name
            )
            for action in block.actions:
                handler = self._get_handler(action.verb)
                if not handler:
                    print(
                        f"Unknown action '{action.verb}' in block for {block.calendar_name}"
                    )
                    continue
                handler(self, action, context)

    def resolve_calendar(self, identifier: str) -> Optional[str]:
        for calendar in self.calendars:
            if (
                calendar.get("summary", "") == identifier
                or calendar.get("id") == identifier
            ):
                return calendar.get("id")
        self.calendars = self.manager.list_calendars()
        for calendar in self.calendars:
            if (
                calendar.get("summary", "") == identifier
                or calendar.get("id") == identifier
            ):
                return calendar.get("id")
        return None

    def _get_handler(self, verb: str) -> Optional[HandlerFn]:
        normalized = verb.replace("-", "_")
        return HANDLER_MAP.get(verb) or HANDLER_MAP.get(normalized)
