# gcal-edit

Linux/macOS terminal helpers for managing birthdays, anniversaries, and other special dates inside Google Calendar. `gcal-edit` centers on a single interactive CLI (`main.py`) that lists calendars, applies advanced filters to events, and ships the same CRUD/CSV workflows that you'd expect from a desktop assistant.

## What it does

- **Google Calendar CLI.** `main.py` launches `CalendarCLI`, which handles sign-in via `calendar_service.authenticate_google_calendar`, keeps a selectable calendar list, and exposes helpers such as `add`, `edit`, `delete`, `transfer`, `export`, `import`, and `batch`.
- **Smart table output.** The `events` command formats a width-limited table with the easily-selectable index column first, the `Event ID` column last, and truncated text (30 characters per column) so long summaries stay readable.
- **Powerful filters.** Append `|`-separated expressions to `events` (e.g., `events | (start <= '2025-01-01' & end >= '2024-01-01') | name match Birthday`) to compare `start`, `end`, `name`, `recurrence`, `location`, or `id`, with `<`, `>`, `<=`, `>=`, `=`, `!=`, or `match` (regex) operators.
- **Per-calendar rule sets.** `calendar_rules.CalendarRulesManager` persists recurrence defaults, reminders, and description templates per calendar, and `set-rules`/`rules` operate on `calendar_rules.json`.
- **CSV workflows & automation.** `CalendarManager` exposes helpers for exporting calendars, importing CSV rows, running batch CSV files, and transferring events; reuse those helpers directly in scripts if you outgrow the CLI.

## Getting started

1. Install dependencies (Python 3.13+):

   ```bash
   pip install -e .
   ```

2. Download `credentials.json` from the Google Calendar API console and place it in the repo root.

3. Run the CLI:

   ```bash
   python main.py
   ```

   The first run opens a browser to grant OAuth consent and stores credentials in `token.pickle`.

## CLI commands

Every entry from `COMMANDS` is available inside the prompt; here are the highlights:

- `calendars`: refresh and list calendars with numbered indexes.
- `select <number|id>`: choose a calendar and display its current rule set.
- `events`: show the current calendar’s events (with optional filters).
- `add`, `edit`, `delete`, `transfer`: mutate events via their index or Google event ID.
- `rules` / `set-rules`: read or update recurrence/reminder defaults for the selected calendar.
- `export` / `import` / `batch`: delegate to the same CSV import/export/batch helpers used by the manager.
- `create`: make a new calendar (optionally specifying a time zone).

Unrecognized commands display the built-in help text.

### Filtering tips

Filters are split by `|` segments. Within each segment, use `&` to chain multiple clauses. Clause examples:

- `start <= '2025-01-01'`
- `end >= '2024-06-01T09:00:00'`
- `name match Birthday`
- `recurrence = RRULE:FREQ=YEARLY`

Regex filters (`match`) support any valid Python expression and operate on the stringified field. Filter results reorder the index column so you can easily edit the filtered subset.

## Rules file (`calendar_rules.json`)

Rules are keyed by calendar ID:

```json
{
  "calendars": {
    "c_12345": {
      "name": "Family",
      "recurrence": ["RRULE:FREQ=YEARLY"],
      "reminders": [
        {"method": "popup", "minutes": 2880},
        {"method": "popup", "minutes": 1440},
        {"method": "popup", "minutes": 0}
      ],
      "description_template": "Family birthday"
    }
  }
}
```

`set-rules` writes this file, while `rules` prints the current defaults.

## CSV workflows & shared helpers

- `export`: writes every event from the selected calendar to a CSV path you choose.
- `import`: loads rows with at least `summary` and `date`, optionally using `id` to dedupe.
- `batch`: processes a CSV containing `action` (`add`, `update`, `delete`) lines plus `id`, `summary`, `date`, and `description` columns.

If you need to script against Google Calendar outside the CLI, instantiate `CalendarManager` directly—its `_collect_pages` helper plus `list_events`, `add_event`, `transfer_event`, and CSV helpers make automation easy.

## Troubleshooting

- Delete `token.pickle` to force re-authentication.
- Ensure `credentials.json` comes from an enabled Google Calendar API project.
- Use Python 3.13+ as stated in `pyproject.toml`; the project depends on `google-api-python-client`, `google-auth`, `google-auth-oauthlib`, and `pandas`.# Google Calendar Manager

This is a Textual-based terminal application that lets you explore, edit, and synchronize events across any Google Calendar you have access to. After authentication it creates a lightweight dashboard with calendar selection, events table, rule management, and CSV-driven workflows.

## Features
- **Event filtering:** Use the built-in filter syntax to quickly locate events by date, name, or recurrence pattern. The filter results reorder the index column so you can easily edit the filtered subset.
- **Multi-calendar management:** Browse all calendars, create new ones, and keep working against whichever calendar you choose without hardcoding a name.
- **Per-calendar rules:** Persist recurrence and reminder defaults for each calendar in `calendar_rules.json` (the app ships with annual reminders and popup alerts as defaults). Editing rules triggers future events to honor the new defaults.
- **Event transfer + batch edits:** Transfer an event to another calendar (optionally removing it from the source), import/export via CSV, and run batch add/update/delete operations with a simple `action` column.

## Quick setup

1. Enable the Google Calendar API and download `credentials.json` into this folder, as described in the official docs.
2. Install dependencies (you are already pegged to Python 3.13+):
   ```bash
   pip install -e .
   ```
3. Run the app via [uv](https://docs.astral.sh/uv/):
   ```bash
   uv run main.py
   ```
   The Textual UI shows calendars on the left, events in the middle, and action buttons underneath.

## Calendar rules (`calendar_rules.json`)

Rules are stored per calendar ID. Each entry can define:

```json
{
  "calendars": {
    "<calendar-id>": {
      "name": "Family",
      "recurrence": ["RRULE:FREQ=YEARLY"],
      "reminders": [{"method": "popup", "minutes": 2880}],
      "description_template": "Family birthday"
    }
  }
}
```

- `recurrence` is a list of RRULE strings.
- `reminders` is a list of popup/reminder overrides in minutes.
- `description_template` is optional text applied when adding events. The UI exposes a "Set Rules" button for updating this file.

## CSV workflows

- **Export:** Choose `Export CSV`, type a path, and get all events from the current calendar.
- **Import:** Select a calendar, choose `Import CSV`, and the app will add any rows that have at least `summary` and `date` columns. If an `id` column is present it will skip existing events.
- **Batch:** Provide a CSV with an `action` column (`add`, `update`, or `delete`). Additional columns include `id`, `summary`, `date`, and `description`.

Example batch row:

```
action,id,summary,date,description
add,,New Year's Party,2026-01-01,Annual kickoff
update,abc123,Updated Title,2025-12-30,Rescheduled
delete,xyz789,,,
```

## Additional notes

- The UI logs every operation in the bottom panel so you can audit transfers, imports, and edits.
- If you need to script something, you can still re-use `calendar_service.CalendarManager` for non-interactive automation thanks to the new generalized helpers.
- If you prefer a more minimal workflow, `python cli.py` launches a simple interactive prompt that can list calendars, show events, edit titles/dates, transfer entries, and run the same CSV workflows without the Textual UI.
