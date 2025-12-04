# gcal-edit

`gcal-edit` is a Python-first assistant for managing birthdays, anniversaries, and other special dates inside Google Calendar. It ships with a single interactive CLI entrypoint (`main.py`) plus a DSL-based runner (`dsl_runner.py`) so that you can switch between manual exploration and scripted workflows.

## Key capabilities

- **Single CLI surface.** `main.py` launches `CalendarCLI`, which lists calendars, applies filters, and pushes CRUD/transfer/CSV actions through the shared `CalendarManager` helpers.
- **Powerful filtering.** The CLI exposes an index-first table limited to around 30 characters per column, and `events | …` supports `where` clauses and `match` expressions for fields such as `start`, `end`, `name`, `location`, `recurrence`, and `id`.
- **Per-calendar rule sets.** `calendar_rules.json` stores recurrence, reminder, and description-template defaults for each calendar. `rules`/`set-rules` from the CLI expose this functionality interactively.
- **CSV workflows.** Export, import, and batch helpers reuse the same logic in both the CLI and the DSL runner so you never type repetitive sequences.
- **DSL scripting.** `dsl_runner.py` interprets the DSL you sketched in `example.gc`, turning calendar selectors, filters, transfers, and `set` clauses into real API calls.

## Requirements

- Python **3.13+** (see `pyproject.toml`).
- A Google Calendar API project with `credentials.json` stored in the repo root.
- Install dependencies:
  ```bash
  pip install -e .
  ```

## Authentication

The first CLI or DSL invocation opens a browser for OAuth consent and caches the credentials in `token.pickle`. Delete that file to force a fresh consent flow.

## Running the CLI

```bash
python main.py
```

Commands include `calendars`, `select`, `events`, `add`, `edit`, `delete`, `transfer`, `rules`, `set-rules`, `export`, `import`, `batch`, `create`, and `help`. Use `events | …` with pipes and `where`/`match` clauses to filter results and keep the index column aligned with your filtered subset for easy selection.

## Filtering examples

```
events | (start <= '2025-01-01' & end >= '2024-01-01T07:00:00') | name match Birthday
```

Each clause compares stringified event properties, so ISO datetimes, summaries, and recurrence text behave consistently.

## Calendar rules (`calendar_rules.json`)

Rules look like this:

```json
{
  "calendars": {
    "your-calendar-id": {
      "name": "Birthday Calendar",
      "recurrence": ["RRULE:FREQ=YEARLY"],
      "reminders": [
        {"method": "popup", "minutes": 20160},
        {"method": "popup", "minutes": 2880},
        {"method": "popup", "minutes": 0}
      ],
      "description_template": "Remember to celebrate"
    }
  }
}
```

`rules` prints the defaults for the selected calendar, while `set-rules` updates this file.

## CSV workflows

- **Export:** `export` writes every event from the selected calendar to a CSV you specify.
- **Import:** `import` reads rows with at least `summary` and `date`, using the calendar’s current recurrence/reminder defaults.
- **Batch:** `batch` processes a CSV with `action` (`add`, `update`, `delete`) plus optional `id`, `summary`, `date`, and `description` columns.

## DSL runner (`dsl_runner.py`)

Use DSL scripts (see `example.gc`) to automate transfers, rule updates, CRUD operations, and CSV imports/exports. The runner authenticates with the same OAuth helpers, resolves calendar selectors, applies the filter pipeline (`| where ...`), and turns verbs such as `events`, `transfer`, `add`, `delete`, `edit`, `rules`, `set-rules`, `create`, `series`, `export`, `import`, and `batch` into Google Calendar API calls. Assignments declared with `| set key=value` are reused across actions so you can pass summaries, dates, recurrence/reminder strings, and rule templates without altering the interpreter code. Special `series` actions emit multiple child verbs (default `add`) by iterating over day offsets or interval+count pairs, so you can generate anniversary/milestone sequences without repeating lines.

```bash
python dsl_runner.py example.gc
```

The parser currently understands calendar selectors, `events` filters, the verbs listed above, simple recurrence aliases (`yearly`, `monthly`, `RRULE:`), and reminders expressed like `1 week, 1 day`. Extend it by adding new verbs or parsing additional fields in `dsl_runner.py` as your DSL evolves.

## Advanced automation

`calendar_service.CalendarManager` is reusable for non-interactive scripts; the CLI and DSL runner both rely on it. Reuse `authenticate_google_calendar()` and `CalendarRulesManager` if you build other automation surfaces.

## Troubleshooting

- Delete `token.pickle` to force a fresh OAuth flow.
- Ensure `credentials.json` is from an enabled Google Calendar API project.
- Use Python 3.13+ (per `pyproject.toml`) and keep dependencies synced via `pip install -e .`.
