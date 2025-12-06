from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING, Any, Callable, Dict, List

from gcal_edit.dsl.filters import filter_events
from gcal_edit.dsl.helpers import (
    create_reminder,
    normalize_recurrence,
    parse_reminder_minutes,
)
from gcal_edit.dsl.types import DSLAction, ExecutionContext
from gcal_edit.service.calendar_service import DEFAULT_TIMEZONE

if TYPE_CHECKING:
    from gcal_edit.dsl.interpreter import DSLInterpreter

HandlerFn = Callable[["DSLInterpreter", DSLAction, ExecutionContext], None]


def handle_events(
    interpreter: "DSLInterpreter", action: DSLAction, context: ExecutionContext
) -> None:
    events = interpreter.manager.list_events(context.calendar_id)
    remainder = " | ".join(action.filters)
    filtered = filter_events(events, remainder)
    context.filtered_events = filtered
    print(f"{len(filtered)} events matched filters in {context.calendar_name}")


def handle_transfer(
    interpreter: "DSLInterpreter", action: DSLAction, context: ExecutionContext
) -> None:
    if not _has_selected_events(context):
        print(
            "No filtered events to transfer; run 'events' first to build a selection."
        )
        return
    target = action.target_calendar
    if not target:
        print("Transfer action requires a target calendar.")
        return
    target_id = interpreter.resolve_calendar(target)
    if not target_id:
        target_id = interpreter.manager.ensure_calendar(
            target, time_zone=DEFAULT_TIMEZONE
        )
    delete_source = action.assignments.get("delete_source", "false").lower() in (
        "true",
        "yes",
        "1",
    )
    for event_data in context.filtered_events:
        event_id = event_data.get("id")
        if not event_id:
            continue
        result = interpreter.manager.transfer_event(
            context.calendar_id, target_id, event_id, delete_source=delete_source
        )
        if result:
            print(f"Transferred event {event_id} to {target}")
    recurrence_value = action.assignments.get("recurrence")
    reminders_value = action.assignments.get("reminders")
    if recurrence_value or reminders_value:
        reminder_minutes = (
            parse_reminder_minutes(reminders_value) if reminders_value else None
        )
        recurrence_list = (
            normalize_recurrence(recurrence_value) if recurrence_value else None
        )
        interpreter.rules.set_rule(
            target_id,
            target,
            recurrence=recurrence_list,
            reminder_minutes=reminder_minutes,
        )
        print(f"Updated rules for {target} after transfer.")


def handle_add(
    interpreter: "DSLInterpreter", action: DSLAction, context: ExecutionContext
) -> None:
    summary = action.assignments.get("name") or action.assignments.get("summary")
    date_value = action.assignments.get("date")
    if not summary or not date_value:
        print("Add action requires both summary/name and date.")
        return
    description = action.assignments.get("description")
    recurrence_value = action.assignments.get("recurrence")
    reminders_value = action.assignments.get("reminders")
    recurrence = normalize_recurrence(recurrence_value)
    reminder_minutes = (
        parse_reminder_minutes(reminders_value) if reminders_value else None
    )
    reminders = (
        [create_reminder(minutes) for minutes in reminder_minutes]
        if reminder_minutes
        else None
    )
    event_id = interpreter.manager.add_event(
        context.calendar_id,
        summary,
        date_value,
        description=description,
        recurrence=recurrence,
        reminders=reminders,
    )
    if event_id:
        print(f"Added event '{summary}' to {context.calendar_name}")


def handle_series(
    interpreter: "DSLInterpreter", action: DSLAction, context: ExecutionContext
) -> None:
    clean_keys = {"offsets", "interval_days", "count", "verb"}
    assignment = {k: v for k, v in action.assignments.items() if k not in clean_keys}
    base = assignment.get("start")
    if not base:
        print("Series action requires a start date.")
        return
    try:
        base_date = date.fromisoformat(base)
    except ValueError:
        print(f"Invalid start date for series: {base}")
        return
    offsets_value = action.assignments.get("offsets")
    interval_value = action.assignments.get("interval_days")
    count_value = action.assignments.get("count")
    offsets: List[int] = []
    if offsets_value:
        offsets = [int(seg.strip()) for seg in offsets_value.split(",") if seg.strip()]
    elif interval_value and count_value:
        interval = int(interval_value)
        count = int(count_value)
        offsets = [interval * idx for idx in range(count)]
    else:
        print("Series action needs either offsets or interval+count.")
        return
    target_verb = action.assignments.get("verb", "add")
    name_template = assignment.get("name", "series event {index}")
    for idx, offset in enumerate(offsets, start=1):
        event_date = base_date + timedelta(days=offset)
        decorated = {
            **assignment,
            "date": event_date.isoformat(),
            "name": name_template.format(
                index=idx, offset=offset, date=event_date.isoformat()
            ),
        }
        child = DSLAction(verb=target_verb, assignments=decorated)
        handler = HANDLER_MAP.get(target_verb)
        if handler:
            handler(interpreter, child, context)
        else:
            print(f"Series cannot run unsupported verb '{target_verb}'")


def handle_delete(
    interpreter: "DSLInterpreter", action: DSLAction, context: ExecutionContext
) -> None:
    events = _selected_events(context)
    if not events:
        print("No filtered events to delete; run 'events' first.")
        return
    for event_data in events:
        event_id = event_data.get("id")
        if not event_id:
            continue
        success = interpreter.manager.delete_event(context.calendar_id, event_id)
        if success:
            print(f"Deleted event {event_id} from {context.calendar_name}")


def handle_edit(
    interpreter: "DSLInterpreter", action: DSLAction, context: ExecutionContext
) -> None:
    events = _selected_events(context)
    if not events:
        print("No filtered events to edit; run 'events' first.")
        return
    assignment = action.assignments
    for event_data in events:
        event_id = event_data.get("id")
        if not event_id:
            continue
        success = interpreter.manager.update_event(
            context.calendar_id,
            event_id,
            summary=assignment.get("name") or assignment.get("summary"),
            date=assignment.get("date"),
            description=assignment.get("description"),
        )
        if success:
            print(f"Updated event {event_id} in {context.calendar_name}")


def handle_rules(
    interpreter: "DSLInterpreter", action: DSLAction, context: ExecutionContext
) -> None:
    rule = interpreter.rules.get_rule(context.calendar_id)
    recurrence = rule.get("recurrence", [])
    reminders = [
        str(reminder.get("minutes", 0)) for reminder in rule.get("reminders", [])
    ]
    print(
        f"Rules for {context.calendar_name}: recurrence={recurrence} reminders={reminders}"
    )


def handle_set_rules(
    interpreter: "DSLInterpreter", action: DSLAction, context: ExecutionContext
) -> None:
    assignment = action.assignments
    recurrence_value = assignment.get("recurrence")
    reminders_value = assignment.get("reminders")
    template = assignment.get("description_template")
    recurrence = normalize_recurrence(recurrence_value)
    reminder_minutes = (
        parse_reminder_minutes(reminders_value) if reminders_value else None
    )
    interpreter.rules.set_rule(
        context.calendar_id,
        context.calendar_name,
        recurrence=recurrence or None,
        reminder_minutes=reminder_minutes if reminder_minutes else None,
        description_template=template,
    )
    print(f"Updated rules for {context.calendar_name}")


def handle_create(
    interpreter: "DSLInterpreter", action: DSLAction, context: ExecutionContext
) -> None:
    assignment = action.assignments
    name = assignment.get("name") or assignment.get("summary")
    if not name:
        print("Create action needs a calendar name via set name=...")
        return
    tz = assignment.get("time_zone") or DEFAULT_TIMEZONE
    calendar_id = interpreter.manager.ensure_calendar(name, time_zone=tz)
    if calendar_id:
        print(f"Created or found calendar {name}")
    else:
        print(f"Failed to create calendar {name}")


def handle_export(
    interpreter: "DSLInterpreter", action: DSLAction, context: ExecutionContext
) -> None:
    path = action.path or action.assignments.get("path")
    if not path:
        print("Export action needs a path (e.g. export to 'path.csv').")
        return
    interpreter.manager.export_to_csv(context.calendar_id, path)
    print(f"Exported {context.calendar_name} to {path}")


def handle_import(
    interpreter: "DSLInterpreter", action: DSLAction, context: ExecutionContext
) -> None:
    path = action.path or action.assignments.get("path")
    if not path:
        print("Import action needs a path (e.g. import from 'rows.csv').")
        return
    rule = interpreter.rules.get_rule(context.calendar_id)
    interpreter.manager.import_from_csv(
        context.calendar_id,
        path,
        recurrence=rule.get("recurrence"),
        reminders=rule.get("reminders"),
    )
    print(f"Imported events from {path} into {context.calendar_name}")


def handle_batch(
    interpreter: "DSLInterpreter", action: DSLAction, context: ExecutionContext
) -> None:
    path = action.path or action.assignments.get("path")
    if not path:
        print("Batch action needs a path to the CSV file.")
        return
    rule = interpreter.rules.get_rule(context.calendar_id)
    interpreter.manager.batch_edit_from_csv(
        context.calendar_id,
        path,
        recurrence=rule.get("recurrence"),
        reminders=rule.get("reminders"),
    )
    print(f"Processed batch CSV {path} for {context.calendar_name}")


def _has_selected_events(context: ExecutionContext) -> bool:
    return bool(context.filtered_events)


def _selected_events(context: ExecutionContext) -> List[Dict[str, Any]]:
    return context.filtered_events if context.filtered_events else []


HANDLER_MAP: Dict[str, HandlerFn] = {
    "events": handle_events,
    "transfer": handle_transfer,
    "add": handle_add,
    "series": handle_series,
    "delete": handle_delete,
    "edit": handle_edit,
    "rules": handle_rules,
    "set_rules": handle_set_rules,
    "set-rules": handle_set_rules,
    "create": handle_create,
    "export": handle_export,
    "import": handle_import,
    "batch": handle_batch,
}
