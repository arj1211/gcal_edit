from argparse import ArgumentParser
from pathlib import Path

from gcal_edit.cli.calendar_cli import CalendarCLI
from gcal_edit.dsl.interpreter import DSLInterpreter


def main() -> None:
    parser = ArgumentParser(description="Run the gcal-edit CLI or DSL scripts")
    parser.add_argument(
        "-f",
        "--script",
        type=Path,
        nargs="+",
        help="Path to one or more DSL scripts",
    )
    args = parser.parse_args()
    if args.script:
        interpreter = DSLInterpreter()
        for script_path in args.script:
            try:
                interpreter.run(script_path)
            except FileNotFoundError:
                print(f"Script file not found: {script_path}")
            except Exception as exc:
                print(f"Unable to run script {script_path}: {exc}")
    else:
        CalendarCLI().run()


if __name__ == "__main__":
    main()
