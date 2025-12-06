from __future__ import annotations

from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from gcal_edit.cli.calendar_cli import CalendarCLI


def handle_export(cli: "CalendarCLI", args: List[str]) -> None:
    if not cli.require_calendar():
        return
    path = args[0] if args else cli.prompt_field("Export path", "special_dates.csv")
    success = cli.manager.export_to_csv(cli.selected_calendar_id, path)
    print("Export complete." if success else "Export failed.")


def handle_import(cli: "CalendarCLI", args: List[str]) -> None:
    if not cli.require_calendar():
        return
    path = args[0] if args else cli.prompt_field("Import path", "special_dates.csv")
    rule = cli.rules.get_rule(cli.selected_calendar_id)
    stats = cli.manager.import_from_csv(
        cli.selected_calendar_id,
        path,
        recurrence=rule.get("recurrence"),
        reminders=rule.get("reminders"),
    )
    print(f"Import added={stats['added']} skipped={stats['skipped']}")


def handle_batch(cli: "CalendarCLI", args: List[str]) -> None:
    if not cli.require_calendar():
        return
    path = args[0] if args else cli.prompt_field("Batch file path", "batch_edits.csv")
    rule = cli.rules.get_rule(cli.selected_calendar_id)
    stats = cli.manager.batch_edit_from_csv(
        cli.selected_calendar_id,
        path,
        recurrence=rule.get("recurrence"),
        reminders=rule.get("reminders"),
    )
    print(
        f"Batch add={stats['added']} update={stats['updated']} delete={stats['deleted']} skipped={stats['skipped']}"
    )
