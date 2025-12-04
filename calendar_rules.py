import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional

RULES_PATH = Path("calendar_rules.json")
DEFAULT_RECURRENCE = ["RRULE:FREQ=YEARLY"]
DEFAULT_REMINDERS = [
    {"method": "popup", "minutes": 14 * 24 * 60},
    {"method": "popup", "minutes": 2 * 24 * 60},
    {"method": "popup", "minutes": 0},
]


class CalendarRulesManager:
    """Persist calendar-level defaults for reminders and recurrences."""

    def __init__(self, path: Path = RULES_PATH):
        self.path = path
        self._rules: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            self._rules = {}
            return
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                content = json.load(fh)
            self._rules = content.get("calendars", {})
        except json.JSONDecodeError:
            self._rules = {}

    def _save(self) -> None:
        data = {"calendars": self._rules}
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)

    def get_rule(self, calendar_id: str) -> Dict[str, Any]:
        """Return saved defaults for the provided calendar, or fallback values."""
        rule = self._rules.get(calendar_id)
        if not rule:
            return {
                "recurrence": DEFAULT_RECURRENCE.copy(),
                "reminders": deepcopy(DEFAULT_REMINDERS),
                "description_template": "",
            }
        return {
            "recurrence": rule.get("recurrence", DEFAULT_RECURRENCE).copy(),
            "reminders": deepcopy(rule.get("reminders", DEFAULT_REMINDERS)),
            "description_template": rule.get("description_template", ""),
        }

    def set_rule(
        self,
        calendar_id: str,
        name: str,
        recurrence: Optional[List[str]] = None,
        reminder_minutes: Optional[List[int]] = None,
        description_template: Optional[str] = None,
    ) -> None:
        """Create or update the rule set for a calendar."""
        overrides = []
        if reminder_minutes:
            overrides = [
                {"method": "popup", "minutes": minute} for minute in reminder_minutes
            ]
        elif reminder_minutes == []:
            overrides = []
        else:
            overrides = DEFAULT_REMINDERS

        self._rules[calendar_id] = {
            "name": name,
            "recurrence": recurrence or DEFAULT_RECURRENCE,
            "reminders": overrides,
            "description_template": description_template or "",
        }
        self._save()

    def list_rules(self) -> Dict[str, Dict[str, Any]]:
        """Return all persisted rules with calendar IDs."""
        return self._rules

    def clear_rule(self, calendar_id: str) -> None:
        """Remove saved defaults for the calendar."""
        if calendar_id in self._rules:
            del self._rules[calendar_id]
            self._save()
