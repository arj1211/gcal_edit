import unittest
from pathlib import Path
from unittest.mock import mock_open, patch

from gcal_edit.dsl.filters import filter_events, parse_boolean_expression
from gcal_edit.dsl.parsing import _strip_literal_value, parse_action_line, parse_script
from gcal_edit.dsl.types import DSLAction, DSLBlock


class TestDSLParsing(unittest.TestCase):
    def test_strip_literal_value(self):
        self.assertEqual(_strip_literal_value('"hello"'), "hello")
        self.assertEqual(_strip_literal_value("'world'"), "world")
        self.assertEqual(_strip_literal_value("plain"), "plain")
        self.assertEqual(
            _strip_literal_value('"quoted with spaces"'), "quoted with spaces"
        )

    def test_parse_action_line(self):
        # Test simple verb
        action = parse_action_line("events")
        self.assertEqual(action.verb, "events")

        # Test transfer with target
        action = parse_action_line("transfer calendar['Target']")
        self.assertEqual(action.verb, "transfer")
        self.assertEqual(action.target_calendar, "Target")

        # Test export with path
        action = parse_action_line("export to 'data.csv'")
        self.assertEqual(action.verb, "export")
        self.assertEqual(action.path, "data.csv")

    def test_parse_script_structure(self):
        script_content = """
calendar['MyCal'] > events
    | where name match 'Test'
    | set description = "Updated"
"""
        with patch("builtins.open", mock_open(read_data=script_content)):
            blocks = parse_script(Path("dummy.gc"))

        self.assertEqual(len(blocks), 1)
        block = blocks[0]
        self.assertEqual(block.calendar_name, "MyCal")
        self.assertEqual(len(block.actions), 1)

        action = block.actions[0]
        self.assertEqual(action.verb, "events")
        self.assertIn("name match 'Test'", action.filters)
        self.assertEqual(action.assignments["description"], "Updated")

    def test_parse_script_multiple_blocks(self):
        script_content = """
calendar['Cal1'] > events
calendar['Cal2'] > add
    | set name = "New Event"
"""
        with patch("builtins.open", mock_open(read_data=script_content)):
            blocks = parse_script(Path("dummy.gc"))

        self.assertEqual(len(blocks), 2)
        self.assertEqual(blocks[0].calendar_name, "Cal1")
        self.assertEqual(blocks[1].calendar_name, "Cal2")
        self.assertEqual(blocks[1].actions[0].verb, "add")


class TestDSLFilters(unittest.TestCase):
    def test_simple_match(self):
        events = [
            {"summary": "Birthday Party"},
            {"summary": "Meeting"},
        ]
        # Filter: name match 'Birthday'
        filtered = filter_events(events, "name match 'Birthday'")
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["summary"], "Birthday Party")

    def test_boolean_and(self):
        events = [
            {"summary": "A", "start": {"date": "2025-01-01"}},
            {"summary": "B", "start": {"date": "2025-01-02"}},
            {"summary": "A", "start": {"date": "2025-01-03"}},
        ]
        # Filter: name match 'A' and start > '2025-01-02'
        # Note: start > 2025-01-02 matches 2025-01-03
        filtered = filter_events(events, "name match 'A' and start > '2025-01-02'")
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["summary"], "A")
        self.assertEqual(filtered[0]["start"]["date"], "2025-01-03")

    def test_boolean_or(self):
        events = [
            {"summary": "Cat"},
            {"summary": "Dog"},
            {"summary": "Fish"},
        ]
        # Filter: name match 'Cat' or name match 'Dog'
        filtered = filter_events(events, "name match 'Cat' or name match 'Dog'")
        self.assertEqual(len(filtered), 2)
        self.assertTrue(any(e["summary"] == "Cat" for e in filtered))
        self.assertTrue(any(e["summary"] == "Dog" for e in filtered))

    def test_parentheses(self):
        events = [
            {"summary": "A", "description": "yes"},
            {"summary": "A", "description": "no"},
            {"summary": "B", "description": "yes"},
        ]
        # Filter: (name match 'A' or name match 'B') and description match 'yes'
        filtered = filter_events(
            events, "(name match 'A' or name match 'B') and description match 'yes'"
        )
        self.assertEqual(len(filtered), 2)
        for e in filtered:
            self.assertEqual(e["description"], "yes")

    def test_comparison_operators(self):
        events = [
            {"start": {"date": "2025-01-01"}},
            {"start": {"date": "2025-01-10"}},
            {"start": {"date": "2025-01-20"}},
        ]
        # Filter: start >= '2025-01-10'
        filtered = filter_events(events, "start >= '2025-01-10'")
        self.assertEqual(len(filtered), 2)

        # Filter: start < '2025-01-10'
        filtered = filter_events(events, "start < '2025-01-10'")
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["start"]["date"], "2025-01-01")


if __name__ == "__main__":
    unittest.main()
