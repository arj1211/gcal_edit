from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List

from dsl_filters import filter_events

if TYPE_CHECKING:
    from cli.calendar_cli import CalendarCLI


def handle_events(cli: "CalendarCLI", args: List[str]) -> None:
    if not cli.require_calendar():
        return
    cli.refresh_events()
    if not cli.events:
        print("No events for this calendar.")
        return

    def event_sort_key(event: Dict[str, Any]) -> tuple[str, str, str, str]:
        start = event.get("start", {}).get("date") or event.get("start", {}).get(
            "dateTime", ""
        )
        end = event.get("end", {}).get("date") or event.get("end", {}).get(
            "dateTime", ""
        )
        recurrence = "-".join(event.get("recurrence", []) or [])
        summary = event.get("summary", "")
        return start, end, recurrence, summary

    sorted_events = sorted(cli.events, key=event_sort_key)
    filtered_events = filter_events(sorted_events, cli.last_command_remainder)
    if not filtered_events:
        print("No events for this calendar.")
        return

    header = [
        "Index",
        "Name",
        "Start Date",
        "End Date",
        "Recurrence Schedule",
        "Location",
        "Event ID",
    ]
    column_limits = {
        "Index": 6,
        "Name": 30,
        "Start Date": 30,
        "End Date": 30,
        "Recurrence Schedule": 30,
        "Location": 30,
        "Event ID": 30,
    }

    def clamp(value: str, max_len: int) -> str:
        if len(value) <= max_len:
            return value
        if max_len <= 3:
            return value[:max_len]
        return value[: max_len - 3] + "..."

    display_rows: List[List[str]] = []
    for index, event in enumerate(filtered_events, start=1):
        start = event.get("start", {}).get("date") or event.get("start", {}).get(
            "dateTime", ""
        )
        end = event.get("end", {}).get("date") or event.get("end", {}).get(
            "dateTime", ""
        )
        recurrence = ", ".join(event.get("recurrence", []))
        location = event.get("location", "")
        row = [
            str(index),
            event.get("summary", "Unnamed event"),
            start,
            end,
            recurrence or "-",
            location,
            event.get("id", ""),
        ]
        display_rows.append(
            [
                clamp(str(value), column_limits.get(header[idx], 30))
                for idx, value in enumerate(row)
            ]
        )

    col_widths: List[int] = []
    for idx, column_name in enumerate(header):
        max_len = len(column_name)
        for row in display_rows:
            max_len = max(max_len, len(row[idx]))
        col_widths.append(max_len)

    line = " | ".join(
        header_item.ljust(col_widths[idx]) for idx, header_item in enumerate(header)
    )
    separator = " | ".join("-" * width for width in col_widths)
    print(line)
    print(separator)
    for row in display_rows:
        print(" | ".join(row[idx].ljust(col_widths[idx]) for idx in range(len(row))))
