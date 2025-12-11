# Gemini Analysis & Roadmap

## Executive Summary

The `gcal_edit` project aims to be a powerful, scriptable tool for managing Google Calendar events, specifically targeting bulk operations, rule enforcement, and complex event generation (series).

**Current Status:**
The project has a solid architectural foundation with a clear separation between the CLI, DSL interpreter, and the underlying Service layer. The core "plumbing" (Google API auth, basic CRUD, CSV handling) is implemented and functional.

**The Problem:**
The "Vision" described in `planning.md` and the "Reality" of the implementation have diverged. The DSL syntax has drifted, key safety features like "Dry Run" are missing, and the parsing logic is fragile. The project is currently a "happy path" prototype that needs to mature into a robust tool.

---

## Codebase Analysis

### 1. Architecture
**Verdict:** ✅ **Solid**
The architecture follows the `gcal_edit_architecture.d2` diagram faithfully.
-   **Service Layer (`gcal_edit/service/`):** The `CalendarManager` is a reusable, well-structured wrapper around the Google Calendar API. It handles pagination and authentication correctly.
-   **DSL Layer (`gcal_edit/dsl/`):** The separation of `parsing`, `interpreter`, and `handlers` is correct. This allows for easy extension of new commands.
-   **CLI Layer (`gcal_edit/cli/`):** Reuses the Service layer, ensuring consistency between interactive and scripted modes.

### 2. DSL Implementation
**Verdict:** ⚠️ **Needs Improvement**
-   **Parsing (`parsing.py`):** Relies on simple Regex. This is brittle. It struggles with nested structures, quoted strings containing delimiters, and complex boolean logic.
-   **Filtering (`filters.py`):** Currently supports `AND` logic (via sequential application) but lacks true `OR` support, despite `example.gc` comments suggesting it exists.
-   **Handlers (`handlers.py`):** The logic is sound, but it lacks a "simulation" mode. Actions are executed immediately against the live API.

### 3. Feature Gaps (Vision vs. Reality)

| Feature       | Vision (`planning.md`)              | Reality (`current code`)                   | Gap                                                                                                            |
| :------------ | :---------------------------------- | :----------------------------------------- | :------------------------------------------------------------------------------------------------------------- |
| **Syntax**    | `! .prop val`, `? .prop < val`      | `\| set prop = val`, `\| where prop < val` | Syntax drift. The current pipe-based syntax is actually *better* (more unix-like), but inconsistent with docs. |
| **Dry Run**   | Explicit `! dry run` command        | **Missing**                                | Critical safety gap. No way to preview changes.                                                                |
| **Filtering** | Regex, Comparators, Boolean Logic   | Regex, Comparators, `AND` only             | Missing `OR` logic and complex grouping.                                                                       |
| **Series**    | `idx=(1,2,3)`, `%idx` interpolation | `offsets=...`, `{index}` interpolation     | Functional but syntax differs.                                                                                 |
| **Safety**    | Implicitly expected                 | **None**                                   | No undo, no confirmation for bulk deletes in DSL.                                                              |

---

## Recommendations & Roadmap

To turn this "half-baked" project into the "final real thing", I propose the following roadmap:

### Phase 1: Core Stabilization & Safety (The "Dry Run" Update)
**Status:** ✅ **Completed**
**Goal:** Make the tool safe to use.
1.  **Implement `DryRun` Context:** Modify `ExecutionContext` to hold a `dry_run` flag.
2.  **Update Handlers:** All handlers (`add`, `delete`, `transfer`, `edit`) must check this flag. If true, they should print *what* they would do without calling the API.
3.  **Global Flag:** Add a `--dry-run` flag to `main.py` that propagates to the interpreter.

### Phase 2: DSL Parser Upgrade
**Status:** ✅ **Completed**
**Goal:** Support complex logic and robust parsing.
1.  **Tokenization:** Move away from simple `split('|')`. Use a proper tokenizer (or a more robust regex state machine) to handle quoted strings and nested parentheses.
2.  **Boolean Logic:** Implement a proper expression parser for `where` clauses to support `(A or B) and C`.
3.  **Syntax Unification:** Decide on the final syntax. I recommend sticking to the current Pipe-based syntax (`| where`, `| set`) as it's more readable than the `!/?` syntax in `planning.md`. Update `planning.md` to reflect this.

### Phase 3: Advanced Features
**Status:** ✅ **Completed**
**Goal:** Fulfill the "Vision".
1.  **Series Enhancements:** Support the `idx` list syntax from planning docs if desired, or standardize on the current `offsets` model.
2.  **Checkpoints:** Implement the "checkpoints" logic (generating events backwards from a date, or spaced out) using the `series` handler.
3.  **Undo/Transaction Log:** (Stretch Goal) Write a transaction log to disk for every destructive action, allowing a `rollback` command.

### Phase 4: CLI/DSL Unification
**Status:** ✅ **Completed**
**Goal:** Ensure parity between CLI and DSL execution engines.
1.  **Refactor CLI:** Modify `CalendarCLI` to use `DSLInterpreter` logic internally where possible, or ensure both use the exact same Service layer methods with identical parameters.
2.  **Command Parity:** Audit all CLI commands and DSL verbs to ensure every capability exists in both worlds.

### Phase 5: Testing
**Status:** 📅 **Planned**
**Goal:** Confidence.
1.  **Mocked Tests:** Create unit tests for `handlers.py` that mock `CalendarManager`. Verify that the correct API calls *would* be made.
2.  **Integration Tests:** The current `.gc` files are manual. We need a test runner that executes them against a mocked service and asserts the state of the "world" afterwards.

## Decisions Log
- **Syntax:** We are sticking with the current pipe-based syntax (`| set`, `| where`) as it is functional and readable.
- **Series:** We will use a functional and sensible syntax for series, likely building on the current implementation but ensuring it covers the use cases.
- **Dry Run:** Implemented as a global flag (`--dry-run`) that prevents write operations to the API and prints simulation messages instead.
- **Boolean Logic:** Implemented a recursive parser for `where` clauses supporting `AND`, `OR`, and parentheses grouping.
- **Series Logic:** Enhanced `series` handler to support:
    -   `idx` lists (e.g., `(1, 2, 3)`).
    -   Duration strings in offsets (e.g., `1 week, 2 days`).
    -   Backward generation (Checkpoints) by providing `end` or `deadline` instead of `start`.
    -   Interpolation of `%idx` and `{index}`.
- **CLI Unification:** Refactored `CalendarCLI` to delegate `add`, `edit`, `delete`, `transfer`, and `create` commands to the corresponding DSL handlers. This ensures that logic improvements (like Dry Run support or rule application) benefit both interfaces.



