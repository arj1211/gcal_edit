import unittest
from datetime import date, timedelta
from unittest.mock import MagicMock, call

from gcal_edit.dsl.handlers import (
    handle_add,
    handle_delete,
    handle_series,
    handle_transfer,
)
from gcal_edit.dsl.interpreter import DSLInterpreter
from gcal_edit.dsl.types import DSLAction, ExecutionContext


class TestDSLHandlers(unittest.TestCase):
    def setUp(self):
        self.mock_manager = MagicMock()
        self.interpreter = DSLInterpreter(manager=self.mock_manager)
        # Mock resolve_calendar to return the input as ID
        self.interpreter.resolve_calendar = MagicMock(side_effect=lambda x: x)

        self.context = ExecutionContext(
            calendar_id="cal_id_1", calendar_name="Test Calendar", dry_run=False
        )

    def test_handle_add(self):
        action = DSLAction(
            verb="add",
            assignments={
                "name": "Test Event",
                "date": "2025-01-01",
                "description": "Test Desc",
            },
        )

        handle_add(self.interpreter, action, self.context)

        self.mock_manager.add_event.assert_called_once_with(
            "cal_id_1",
            "Test Event",
            "2025-01-01",
            description="Test Desc",
            recurrence=None,
            reminders=None,
        )

    def test_handle_add_dry_run(self):
        self.context.dry_run = True
        action = DSLAction(
            verb="add", assignments={"name": "Test Event", "date": "2025-01-01"}
        )

        handle_add(self.interpreter, action, self.context)

        self.mock_manager.add_event.assert_not_called()

    def test_handle_delete(self):
        # Setup context with selected events
        self.context.filtered_events = [
            {"id": "evt1", "summary": "Event 1"},
            {"id": "evt2", "summary": "Event 2"},
        ]
        action = DSLAction(verb="delete")

        # Ensure delete_event returns True so we don't get __bool__ calls on a mock return value
        self.mock_manager.delete_event.return_value = True

        handle_delete(self.interpreter, action, self.context)

        self.assertEqual(self.mock_manager.delete_event.call_count, 2)
        self.mock_manager.delete_event.assert_has_calls(
            [call("cal_id_1", "evt1"), call("cal_id_1", "evt2")]
        )

    def test_handle_transfer(self):
        self.context.filtered_events = [{"id": "evt1"}]
        action = DSLAction(
            verb="transfer",
            target_calendar="Target Cal",
            assignments={"delete_source": "true"},
        )

        # Mock resolve_calendar to return None so ensure_calendar is called
        # Must clear side_effect from setUp
        self.interpreter.resolve_calendar.side_effect = None
        self.interpreter.resolve_calendar.return_value = None
        # Mock ensure_calendar to return a target ID
        self.mock_manager.ensure_calendar.return_value = "target_id_1"

        handle_transfer(self.interpreter, action, self.context)

        self.mock_manager.transfer_event.assert_called_once_with(
            "cal_id_1", "target_id_1", "evt1", delete_source=True
        )

    def test_handle_series_offsets(self):
        # Test series with explicit offsets
        action = DSLAction(
            verb="series",
            assignments={
                "start": "2025-01-01",
                "offsets": "1 day, 1 week",
                "name": "Series %idx",
                "verb": "add",
            },
        )

        # We need to mock the handler map used inside handle_series
        # Since handle_series imports HANDLER_MAP, we can patch it or just check calls to interpreter
        # But handle_series calls handlers directly.
        # A better way is to mock the 'add' handler in the map, but that's global.
        # Alternatively, we can check if manager.add_event was called multiple times.

        handle_series(self.interpreter, action, self.context)

        # Should result in 2 add_event calls
        self.assertEqual(self.mock_manager.add_event.call_count, 2)

        # Check dates
        # 2025-01-01 + 1 day = 2025-01-02
        # 2025-01-01 + 1 week = 2025-01-08
        calls = self.mock_manager.add_event.call_args_list
        self.assertEqual(calls[0][0][2], "2025-01-02")  # date arg
        self.assertEqual(calls[1][0][2], "2025-01-08")

    def test_handle_series_checkpoints(self):
        # Test backward generation
        action = DSLAction(
            verb="series",
            assignments={
                "deadline": "2025-01-10",
                "offsets": "1 day, 3 days",
                "name": "Checkpoint",
                "verb": "add",
            },
        )

        handle_series(self.interpreter, action, self.context)

        self.assertEqual(self.mock_manager.add_event.call_count, 2)

        # Check dates
        # 2025-01-10 - 1 day = 2025-01-09
        # 2025-01-10 - 3 days = 2025-01-07
        calls = self.mock_manager.add_event.call_args_list
        self.assertEqual(calls[0][0][2], "2025-01-09")
        self.assertEqual(calls[1][0][2], "2025-01-07")


if __name__ == "__main__":
    unittest.main()
