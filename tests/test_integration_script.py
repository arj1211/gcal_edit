import unittest
from pathlib import Path
from unittest.mock import MagicMock, call, patch

from gcal_edit.dsl.interpreter import DSLInterpreter


class TestIntegrationScript(unittest.TestCase):
    def setUp(self):
        self.mock_manager = MagicMock()
        self.interpreter = DSLInterpreter(manager=self.mock_manager)

        # Mock list_calendars to return our test calendars
        self.mock_manager.list_calendars.return_value = [
            {"id": "sandbox_id", "summary": "Test Sandbox"},
            {"id": "archive_id", "summary": "Test Archive"},
        ]
        # Update interpreter's cache
        self.interpreter.calendars = self.mock_manager.list_calendars()

    def test_full_lifecycle_dry_run(self):
        script_path = Path("tests/gc/full_lifecycle.gc")

        # Run the script
        self.interpreter.run(script_path, dry_run=True)

        # Verify interactions
        # 1. Create
        # ensure_calendar is called even in dry run? No, handle_create returns early.
        # But we can check if it printed the right things?
        # Actually, checking stdout is hard. Let's check what we can.

        # In dry run, manager methods shouldn't be called for mutations.
        self.mock_manager.add_event.assert_not_called()
        self.mock_manager.delete_event.assert_not_called()

    def test_full_lifecycle_execution(self):
        script_path = Path("tests/gc/full_lifecycle.gc")

        # Mock event listing for the 'events' commands
        self.mock_manager.list_events.return_value = [
            {
                "id": "evt1",
                "summary": "Integration Test Event",
                "start": {"date": "2025-06-01"},
            }
        ]

        # Mock ensure_calendar to return IDs
        self.mock_manager.ensure_calendar.side_effect = (
            lambda name, **kwargs: "sandbox_id" if "Sandbox" in name else "archive_id"
        )

        # Run the script
        self.interpreter.run(script_path, dry_run=False)

        # Verify Create
        self.mock_manager.ensure_calendar.assert_any_call(
            "Test Sandbox", time_zone="UTC"
        )

        # Verify Add
        self.mock_manager.add_event.assert_called_with(
            "sandbox_id",
            "Integration Test Event",
            "2025-06-01",
            description="Created by integration test",
            recurrence=None,
            reminders=None,
        )

        # Verify Edit
        # The script filters for 'Integration Test Event' and updates description/recurrence
        self.mock_manager.update_event.assert_called()
        call_args = self.mock_manager.update_event.call_args
        self.assertEqual(call_args[0][0], "sandbox_id")  # calendar_id
        self.assertEqual(call_args[0][1], "evt1")  # event_id
        self.assertEqual(call_args[1]["description"], "Updated description")
        self.assertEqual(call_args[1]["summary"], None)  # name wasn't changed

        # Verify Transfer
        self.mock_manager.transfer_event.assert_called_with(
            "sandbox_id", "archive_id", "evt1", delete_source=True
        )

        # Verify Delete (on Archive)
        # The script switches to Test Archive and deletes the event
        # Note: In a real run, the event would need to exist on Archive.
        # Our mock list_events returns the same event for all calls, so it "exists" on Archive too.
        self.mock_manager.delete_event.assert_called_with("archive_id", "evt1")


if __name__ == "__main__":
    unittest.main()
