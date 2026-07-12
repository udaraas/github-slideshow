"""Unit tests for BrowserRecorder."""
import unittest

from nextgen_test_automation.core.models import StepAction
from nextgen_test_automation.walkthrough.browser_recorder import BrowserRecorder, _dedupe_input_events
from nextgen_test_automation.walkthrough.events import WalkthroughSession


_SAMPLE_EVENTS = [
    {
        "action": "navigate",
        "locator": {},
        "payload": {"url": "https://demo.bank/login"},
        "timestamp": "2026-08-16T10:00:00Z",
    },
    {
        "action": "click",
        "locator": {"css": "#email", "text": "Email", "aria_label": "email input"},
        "payload": {},
        "timestamp": "2026-08-16T10:00:01Z",
    },
    {
        "action": "type",
        "locator": {"css": "#email", "text": None, "aria_label": None},
        "payload": {"value": "user@demo.bank"},
        "timestamp": "2026-08-16T10:00:02Z",
    },
    {
        "action": "click",
        "locator": {"css": "#submit", "text": "Log in", "aria_label": "login"},
        "payload": {},
        "timestamp": "2026-08-16T10:00:03Z",
    },
]


class TestBrowserRecorder(unittest.TestCase):

    def setUp(self):
        self.recorder = BrowserRecorder()

    def test_record_from_events_builds_session(self):
        session = self.recorder.record_from_events(_SAMPLE_EVENTS, app_name="DemoBank")
        self.assertIsInstance(session, WalkthroughSession)
        self.assertEqual(session.app_name, "DemoBank")
        self.assertEqual(session.platform, "web")
        self.assertEqual(len(session.events), 4)

    def test_actions_parsed_correctly(self):
        session = self.recorder.record_from_events(_SAMPLE_EVENTS, app_name="X")
        self.assertEqual(session.events[0].action, StepAction.NAVIGATE)
        self.assertEqual(session.events[1].action, StepAction.CLICK)
        self.assertEqual(session.events[2].action, StepAction.TYPE)

    def test_locator_fields_populated(self):
        session = self.recorder.record_from_events(_SAMPLE_EVENTS, app_name="X")
        click_evt = session.events[1]
        self.assertEqual(click_evt.locator.css, "#email")
        self.assertEqual(click_evt.locator.text, "Email")
        self.assertEqual(click_evt.locator.aria_label, "email input")

    def test_payload_preserved(self):
        session = self.recorder.record_from_events(_SAMPLE_EVENTS, app_name="X")
        type_evt = session.events[2]
        self.assertEqual(type_evt.payload["value"], "user@demo.bank")

    def test_session_id_generated(self):
        session = self.recorder.record_from_events([], app_name="X")
        self.assertIsNotNone(session.session_id)
        self.assertTrue(len(session.session_id) > 0)

    def test_empty_events_produces_empty_session(self):
        session = self.recorder.record_from_events([], app_name="Empty")
        self.assertEqual(len(session.events), 0)

    def test_unknown_action_defaults_to_click(self):
        raw = [{"action": "unknown_action", "locator": {}, "payload": {}}]
        session = self.recorder.record_from_events(raw, app_name="X")
        self.assertEqual(session.events[0].action, StepAction.CLICK)

    def test_actor_forwarded(self):
        session = self.recorder.record_from_events([], app_name="X", actor="qa_engineer")
        self.assertEqual(session.actor, "qa_engineer")

    def test_injector_script_contains_recorder_guard(self):
        self.assertIn("__nextgen_recorder_active", self.recorder.injector_script)

    def test_injector_script_captures_click(self):
        self.assertIn("click", self.recorder.injector_script)

    def test_injector_script_captures_input(self):
        self.assertIn("input", self.recorder.injector_script)


class TestDedupeInputEvents(unittest.TestCase):

    def test_collapses_consecutive_type_events(self):
        events = [
            {"action": "type", "locator": {"css": "#q"}, "payload": {"value": "h"}},
            {"action": "type", "locator": {"css": "#q"}, "payload": {"value": "he"}},
            {"action": "type", "locator": {"css": "#q"}, "payload": {"value": "hello"}},
        ]
        result = _dedupe_input_events(events)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["payload"]["value"], "hello")

    def test_does_not_collapse_different_elements(self):
        events = [
            {"action": "type", "locator": {"css": "#a"}, "payload": {"value": "x"}},
            {"action": "type", "locator": {"css": "#b"}, "payload": {"value": "y"}},
        ]
        result = _dedupe_input_events(events)
        self.assertEqual(len(result), 2)

    def test_does_not_collapse_click_between_types(self):
        events = [
            {"action": "type", "locator": {"css": "#q"}, "payload": {"value": "a"}},
            {"action": "click", "locator": {"css": "#btn"}, "payload": {}},
            {"action": "type", "locator": {"css": "#q"}, "payload": {"value": "b"}},
        ]
        result = _dedupe_input_events(events)
        self.assertEqual(len(result), 3)


if __name__ == "__main__":
    unittest.main()
