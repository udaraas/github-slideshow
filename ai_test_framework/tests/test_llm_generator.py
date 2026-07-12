"""Unit tests for LLMTestCaseGenerator."""
import json
import unittest
from dataclasses import replace
from unittest.mock import MagicMock, patch

from nextgen_test_automation.core.models import StepAction, TestCase
from nextgen_test_automation.walkthrough.events import WalkthroughEvent, WalkthroughSession
from nextgen_test_automation.ai.llm_generator import LLMTestCaseGenerator


def _make_session() -> WalkthroughSession:
    session = WalkthroughSession(app_name="DemoBank", platform="web")
    session.record(WalkthroughEvent(action=StepAction.NAVIGATE, payload={"url": "https://demo.bank/login"}))
    session.record(WalkthroughEvent(action=StepAction.TYPE, payload={"value": "user@demo.bank"}))
    session.record(WalkthroughEvent(action=StepAction.CLICK, payload={}))
    return session


class TestLLMGeneratorStubFallback(unittest.TestCase):
    """Tests using the rule-based stub (no LLM key needed)."""

    def setUp(self):
        self.gen = LLMTestCaseGenerator()

    def test_stub_generates_test_case(self):
        session = _make_session()
        tc = self.gen.generate(session, industry="BFSI")
        self.assertIsInstance(tc, TestCase)
        self.assertEqual(len(tc.steps), 3)

    def test_stub_tags_contain_industry(self):
        session = _make_session()
        tc = self.gen.generate(session, industry="BFSI")
        self.assertIn("BFSI", tc.tags)

    def test_stub_uses_app_name_in_test_name(self):
        session = _make_session()
        tc = self.gen.generate(session, industry="BFSI")
        self.assertIn("DemoBank", tc.name)

    def test_empty_session_produces_empty_steps(self):
        session = WalkthroughSession(app_name="X", platform="web")
        tc = self.gen.generate(session, industry="general")
        self.assertEqual(len(tc.steps), 0)


class TestLLMGeneratorResponseParsing(unittest.TestCase):
    """Tests the JSON parsing path without making real LLM calls."""

    def setUp(self):
        self.gen = LLMTestCaseGenerator()

    def test_parse_valid_llm_response(self):
        payload = {
            "name": "Login flow",
            "steps": [
                {
                    "action": "navigate",
                    "description": "Open login page",
                    "locator_css": None,
                    "locator_text": None,
                    "locator_aria_label": None,
                    "payload": {"url": "https://demo.bank/login"},
                    "expected": {},
                },
                {
                    "action": "type",
                    "description": "Enter email",
                    "locator_css": "#email",
                    "locator_text": None,
                    "locator_aria_label": "email",
                    "payload": {"value": "user@demo.bank"},
                    "expected": {},
                },
                {
                    "action": "assert",
                    "description": "Verify dashboard",
                    "locator_css": "#dashboard-title",
                    "locator_text": "Dashboard",
                    "locator_aria_label": None,
                    "payload": {},
                    "expected": {"text": "Dashboard"},
                },
            ],
            "tags": ["BFSI", "ai-generated", "login"],
        }
        session = _make_session()
        tc = self.gen._parse_response(json.dumps(payload), session, "BFSI")
        self.assertEqual(tc.name, "Login flow")
        self.assertEqual(len(tc.steps), 3)
        self.assertEqual(tc.steps[0].action, StepAction.NAVIGATE)
        self.assertEqual(tc.steps[1].locator.css, "#email")
        self.assertEqual(tc.steps[2].expected["text"], "Dashboard")
        self.assertIn("login", tc.tags)

    def test_parse_handles_missing_optional_fields(self):
        payload = {
            "name": "Minimal",
            "steps": [{"action": "navigate", "description": "go"}],
            "tags": [],
        }
        session = WalkthroughSession(app_name="X", platform="web")
        tc = self.gen._parse_response(json.dumps(payload), session, "general")
        self.assertEqual(len(tc.steps), 1)
        self.assertIsNone(tc.steps[0].locator)

    def test_llm_path_mocked(self):
        """Verify the LLM code path is invoked when the key is available."""
        payload = {
            "name": "AI Login",
            "steps": [{"action": "navigate", "description": "go to login"}],
            "tags": ["BFSI", "ai-generated"],
        }
        session = _make_session()
        expected_tc = self.gen._parse_response(json.dumps(payload), session, "BFSI")

        with patch.object(LLMTestCaseGenerator, "_llm_available", return_value=True), \
             patch.object(LLMTestCaseGenerator, "_llm_generate", return_value=expected_tc) as mock_gen:
            tc = self.gen.generate(session, industry="BFSI")

        self.assertEqual(tc.name, "AI Login")
        mock_gen.assert_called_once()

    def test_falls_back_to_stub_on_llm_exception(self):
        """If the LLM raises, the stub generator must be used."""
        session = _make_session()
        with patch.object(LLMTestCaseGenerator, "_llm_available", return_value=True), \
             patch.object(LLMTestCaseGenerator, "_llm_generate", side_effect=RuntimeError("API error")):
            tc = self.gen.generate(session, industry="BFSI")
        self.assertIsInstance(tc, TestCase)
        self.assertEqual(len(tc.steps), 3)


if __name__ == "__main__":
    unittest.main()
