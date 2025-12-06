from __future__ import annotations

from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from gcal_edit.cli.calendar_cli import CalendarCLI


def handle_rules(cli: "CalendarCLI", args: List[str]) -> None:
    if not cli.require_calendar():
        return
    rule = cli.rules.get_rule(cli.selected_calendar_id)
    recurrence = rule.get("recurrence", [])
    reminders = [
        str(reminder.get("minutes", 0)) for reminder in rule.get("reminders", [])
    ]
    print("Recurrence:", recurrence)
    print("Reminders:", reminders)
    if template := rule.get("description_template"):
        print("Description template:", template)


def handle_set_rules(cli: "CalendarCLI", args: List[str]) -> None:
    if not cli.require_calendar():
        return
    recurrence_raw = cli.prompt_field("Recurrence rules (comma separated)")
    reminder_raw = cli.prompt_field("Reminder minutes (comma separated)")
    template = cli.prompt_field("Description template", "")
    recurrence = [item.strip() for item in recurrence_raw.split(",") if item.strip()]
    reminder_minutes = [
        int(part.strip()) for part in reminder_raw.split(",") if part.strip().isdigit()
    ]
    cli.rules.set_rule(
        cli.selected_calendar_id,
        cli.selected_calendar_name or "",
        recurrence=recurrence or None,
        reminder_minutes=reminder_minutes if reminder_minutes else None,
        description_template=template,
    )
    print("Rules updated.")
