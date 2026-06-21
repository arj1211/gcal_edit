# gcal-edit

`gcal-edit` is a Python-first assistant for managing birthdays, anniversaries, and other special dates inside Google Calendar. It ships with a single interactive CLI entrypoint (`main.py` / the `gcal_edit` package) plus a built-in DSL interpreter that you can trigger via the `-f` flag or the `script` command so that you can switch between manual exploration and scripted workflows.

## Key capabilities

- **Single CLI surface.** `main.py` launches `CalendarCLI`, which lists calendars, applies filters, and pushes CRUD/transfer/CSV actions through the shared `CalendarManager` helpers.
- **Powerful filtering.** The CLI exposes an index-first table limited to around 30 characters per column, and `events | …` supports `where` clauses and `match` expressions for fields such as `start`, `end`, `name`, `location`, `recurrence`, and `id`.
- **CSV workflows.** Export, import, and batch helpers reuse the same logic in both the CLI and the DSL runner so you never type repetitive sequences.
- **DSL scripting.** The same interpreter now lives under `gcal_edit.dsl` and powers both the CLI-only `script` command plus the `-f/--script` flag on `main.py`, so your `example.gc` automation runs from one surface.

## Requirements

- Python **3.13+** (see `pyproject.toml`).
- A Google Calendar API project with `credentials.json` stored in the repo root.
- Install dependencies:
  ```bash
  uv sync
  ```

## Authentication

The first CLI or DSL invocation opens a browser for OAuth consent and caches the credentials in `token.pickle`. Delete that file to force a fresh consent flow.

## Running the CLI

```bash
uv run python main.py
```

Pass `-f/--script` when you need to run DSL files directly, and once inside the prompt trigger `script <path>` to execute a file after authentication. Commands include `calendars`, `select`, `events`, `add`, `edit`, `delete`, `transfer`, `export`, `import`, `batch`, `create`, and `help`. Use `events | …` with pipes and `where`/`match` clauses to filter results and keep the index column aligned with your filtered subset for easy selection.

## Filtering examples

```
events | (start <= '2025-01-01' & end >= '2024-01-01T07:00:00') | name match Birthday
```

Each clause compares stringified event properties, so ISO datetimes, summaries, and recurrence text behave consistently.

## CSV workflows

- **Export:** `export` writes every event from the selected calendar to a CSV you specify.
- **Import:** `import` reads rows with at least `summary` and `date`.
- **Batch:** `batch` processes a CSV with `action` (`add`, `update`, `delete`) plus optional `id`, `summary`, `date`, and `description` columns.

## DSL scripting

Use DSL scripts (see `example.gc`) to automate transfers, CRUD operations, and CSV imports/exports. The embedded interpreter reuses the OAuth helpers, resolves calendar selectors, applies the filter pipeline (`| where ...`), and turns verbs such as `events`, `transfer`, `add`, `delete`, `edit`, `create`, `series`, `export`, `import`, and `batch` into Google Calendar API calls. Assignments declared with `| set key=value` are reused across actions so you can pass summaries, dates, recurrence/reminder strings, and rule templates without altering the interpreter code. Special `series` actions emit multiple child verbs (default `add`) by iterating over day offsets or interval+count pairs, so you can generate anniversary/milestone sequences without repeating lines.

```bash
uv run python main.py -f example.gc
```

The parser currently understands calendar selectors, `events` filters, the verbs listed above, simple recurrence aliases (`yearly`, `monthly`, `RRULE:`), and reminders expressed like `1 week, 1 day`. Extend it by adding new verbs or parsing additional fields under `gcal_edit.dsl` as your DSL evolves.

## Advanced automation

`gcal_edit.service.calendar_service.CalendarManager` is reusable for non-interactive scripts; the CLI and DSL interpreter both rely on it. Reuse `authenticate_google_calendar()` if you build other automation surfaces.

## Troubleshooting

- Delete `token.pickle` to force a fresh OAuth flow.
- Ensure `credentials.json` is from an enabled Google Calendar API project.
- Use Python 3.13+ (per `pyproject.toml`) and keep dependencies synced via `uv sync`.
