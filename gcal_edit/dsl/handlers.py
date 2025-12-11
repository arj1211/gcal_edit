from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING, Any, Callable, Dict, List

from gcal_edit.dsl.filters import filter_events
from gcal_edit.dsl.helpers import (
    create_reminder,
    normalize_recurrence,
    parse_duration_string,
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

    if context.dry_run:
        print(
            f"[Dry Run] Would transfer {len(context.filtered_events)} events to {target}"
        )
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

    if recurrence_value:
        recurrence = normalize_recurrence(recurrence_value)
    else:
        recurrence = None

    if reminders_value:
        reminder_minutes = parse_reminder_minutes(reminders_value)
        reminders = [create_reminder(minutes) for minutes in reminder_minutes]
    else:
        reminders = None

    if context.dry_run:
        print(
            f"[Dry Run] Would add event '{summary}' on {date_value} to {context.calendar_name}"
        )
        if description:
            print(f"          Description: {description}")
        if recurrence:
            print(f"          Recurrence: {recurrence}")
        if reminders:
            print(f"          Reminders: {reminders}")
        return

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
    clean_keys = {"offsets", "interval_days", "count", "verb", "idx"}
    assignment = {k: v for k, v in action.assignments.items() if k not in clean_keys}

    # Determine base date and direction
    start_val = assignment.get("start")
    end_val = assignment.get("end") or assignment.get("deadline")

    if start_val:
        try:
            base_date = date.fromisoformat(start_val)
            direction = 1
        except ValueError:
            print(f"Invalid start date for series: {start_val}")
            return
    elif end_val:
        try:
            base_date = date.fromisoformat(end_val)
            direction = -1
        except ValueError:
            print(f"Invalid end/deadline date for series: {end_val}")
            return
    else:
        print("Series action requires a start date or end/deadline date.")
        return

    # Parse offsets or interval
    offsets_value = action.assignments.get("offsets")
    interval_value = action.assignments.get("interval_days")
    count_value = action.assignments.get("count")
    idx_value = action.assignments.get("idx")

    offsets: List[timedelta] = []
    indices: List[Any] = []

    if idx_value:
        # Parse idx list like "(1, 2, 3)" or "1,2,3"
        raw_idx = idx_value.strip()
        if raw_idx.startswith("(") and raw_idx.endswith(")"):
            raw_idx = raw_idx[1:-1]
        indices = [i.strip() for i in raw_idx.split(",") if i.strip()]

    if offsets_value:
        # Parse offsets list like "1 week, 2 days"
        offsets = [
            parse_duration_string(seg)
            for seg in offsets_value.split(",")
            if seg.strip()
        ]

        # If indices not provided, generate 1-based indices
        if not indices:
            indices = list(range(1, len(offsets) + 1))

    elif interval_value and count_value:
        interval = int(interval_value)
        count = int(count_value)
        offsets = [timedelta(days=interval * i) for i in range(count)]
        if not indices:
            indices = list(range(1, count + 1))
    else:
        print("Series action needs either offsets or interval+count.")
        return

    # Validate lengths match if both provided
    if len(indices) != len(offsets):
        print(f"Mismatch: {len(indices)} indices provided for {len(offsets)} offsets.")
        # Truncate to shorter length to be safe? Or error? Let's error.
        return

    target_verb = action.assignments.get("verb", "add")
    name_template = assignment.get("name", "series event {index}")

    for i, offset in enumerate(offsets):
        idx = indices[i]
        # Apply direction (add if forward, subtract if backward)
        # Note: offset is always positive duration, direction handles sign
        if direction == 1:
            event_date = base_date + offset
        else:
            event_date = base_date - offset

        # Interpolate name
        # Support both {index} and %idx styles
        try:
            final_name = name_template.replace("%idx", str(idx)).format(
                index=idx, idx=idx, offset=offset, date=event_date.isoformat()
            )
        except Exception as e:
            print(f"Error formatting name template '{name_template}': {e}")
            final_name = name_template

        decorated = {
            **assignment,
            "date": event_date.isoformat(),
            "name": final_name,
        }

        # Remove start/end from decorated to avoid confusion in child action?
        # Actually 'add' handler expects 'date', so we are good.

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

    if context.dry_run:
        print(
            f"[Dry Run] Would delete {len(events)} events from {context.calendar_name}"
        )
        for event in events[:5]:  # Show first 5 as sample
            print(
                f"          - {event.get('summary', 'No Title')} ({event.get('start', {}).get('date') or event.get('start', {}).get('dateTime')})"
            )
        if len(events) > 5:
            print(f"          ... and {len(events) - 5} more.")
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

    if context.dry_run:
        print(f"[Dry Run] Would edit {len(events)} events in {context.calendar_name}")
        print(f"          Updates: {assignment}")
        return

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


def handle_create(
    interpreter: "DSLInterpreter", action: DSLAction, context: ExecutionContext
) -> None:
    assignment = action.assignments
    name = assignment.get("name") or assignment.get("summary") or context.calendar_name
    if not name:
        print("Create action needs a calendar name.")
        return
    tz = assignment.get("time_zone") or DEFAULT_TIMEZONE

    if context.dry_run:
        print(f"[Dry Run] Would create calendar '{name}' with time zone '{tz}'")
        return

    calendar_id = interpreter.manager.ensure_calendar(name, time_zone=tz)
    if calendar_id:
        context.calendar_id = calendar_id
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

    if context.dry_run:
        print(f"[Dry Run] Would export events from {context.calendar_name} to {path}")
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

    if context.dry_run:
        print(f"[Dry Run] Would import events from {path} into {context.calendar_name}")
        return

    interpreter.manager.import_from_csv(
        context.calendar_id,
        path,
        recurrence=None,
        reminders=None,
    )
    print(f"Imported events from {path} into {context.calendar_name}")


def handle_batch(
    interpreter: "DSLInterpreter", action: DSLAction, context: ExecutionContext
) -> None:
    path = action.path or action.assignments.get("path")
    if not path:
        print("Batch action needs a path to the CSV file.")
        return

    if context.dry_run:
        print(
            f"[Dry Run] Would process batch operations from {path} for {context.calendar_name}"
        )
        return

    interpreter.manager.batch_edit_from_csv(
        context.calendar_id,
        path,
        recurrence=None,
        reminders=None,
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
    "create": handle_create,
    "export": handle_export,
    "import": handle_import,
    "batch": handle_batch,
}
