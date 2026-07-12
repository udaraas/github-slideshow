"""Unit tests for WebAutomationExecutor (Playwright mocked)."""
import unittest
from unittest.mock import MagicMock, patch

from nextgen_test_automation.core.models import ElementLocator, StepAction, TestCase, TestStep
from nextgen_test_automation.execution.web_executor import ExecutionResult, WebAutomationExecutor


def _make_tc(*step_actions, **kwargs) -> TestCase:
    steps = [TestStep(action=a, description=f"step {i}") for i, a in enumerate(step_actions)]
    return TestCase(name="test", industry="test", steps=steps, **kwargs)


class TestWebExecutorNoPlaywright(unittest.TestCase):
    """Tests that run without a real browser — Playwright import is mocked."""

    def test_empty_steps_returns_failed(self):
        executor = WebAutomationExecutor()
        tc = TestCase(name="empty", industry="test", steps=[])
        result = executor.run(tc)
        self.assertFalse(result.passed)
        self.assertIn("No steps", result.message)

    def test_playwright_not_installed_returns_failed(self):
        executor = WebAutomationExecutor()
        tc = _make_tc(StepAction.NAVIGATE)
        tc.steps[0].payload["url"] = "https://example.com"
        with patch("nextgen_test_automation.execution.web_executor._PLAYWRIGHT_AVAILABLE", False):
            result = executor.run(tc)
        self.assertFalse(result.passed)
        self.assertIn("Playwright not installed", result.message)


class TestWebExecutorWithMockedPlaywright(unittest.TestCase):
    """Full step dispatch tests with a mocked Playwright context."""

    def _run_with_mock(self, steps: list[TestStep], *, page_setup=None) -> ExecutionResult:
        """Run executor against *steps* with a fully mocked Playwright."""
        mock_page = MagicMock()
        mock_page.url = "https://example.com"

        if page_setup:
            page_setup(mock_page)

        mock_browser = MagicMock()
        mock_browser.new_page.return_value = mock_page

        mock_chromium = MagicMock()
        mock_chromium.launch.return_value = mock_browser

        mock_pw_ctx = MagicMock()
        mock_pw_ctx.chromium = mock_chromium
        mock_pw_ctx.__enter__ = MagicMock(return_value=mock_pw_ctx)
        mock_pw_ctx.__exit__ = MagicMock(return_value=False)

        mock_sync_playwright = MagicMock(return_value=mock_pw_ctx)

        tc = TestCase(name="mock-tc", industry="test", steps=steps)

        with patch(
            "nextgen_test_automation.execution.web_executor.sync_playwright",
            mock_sync_playwright,
        ), patch("nextgen_test_automation.execution.web_executor._PLAYWRIGHT_AVAILABLE", True):
            executor = WebAutomationExecutor()
            return executor.run(tc)

    def test_navigate_step_passes(self):
        step = TestStep(
            action=StepAction.NAVIGATE,
            description="go home",
            payload={"url": "https://example.com"},
        )
        result = self._run_with_mock([step])
        self.assertTrue(result.passed)

    def test_wait_step_passes(self):
        step = TestStep(action=StepAction.WAIT, description="wait", payload={"ms": 200})
        result = self._run_with_mock([step])
        self.assertTrue(result.passed)

    def test_scroll_step_passes(self):
        step = TestStep(action=StepAction.SCROLL, description="scroll", payload={"x": 0, "y": 300})
        result = self._run_with_mock([step])
        self.assertTrue(result.passed)

    def test_key_press_step_passes(self):
        step = TestStep(action=StepAction.KEY_PRESS, description="enter", payload={"key": "Enter"})
        result = self._run_with_mock([step])
        self.assertTrue(result.passed)

    def test_click_step_with_locator_passes(self):
        def setup(page):
            loc = MagicMock()
            loc.count.return_value = 1
            page.locator.return_value = loc

        step = TestStep(
            action=StepAction.CLICK,
            description="click login",
            locator=ElementLocator(css="#login"),
        )
        result = self._run_with_mock([step], page_setup=setup)
        self.assertTrue(result.passed)

    def test_click_step_without_locator_fails(self):
        step = TestStep(action=StepAction.CLICK, description="no locator")
        result = self._run_with_mock([step])
        self.assertFalse(result.passed)
        self.assertIn("locator required", result.message)

    def test_click_step_unresolvable_locator_fails(self):
        def setup(page):
            loc = MagicMock()
            loc.count.return_value = 0
            page.locator.return_value = loc

        step = TestStep(
            action=StepAction.CLICK,
            description="missing element",
            locator=ElementLocator(css="#gone"),
        )
        result = self._run_with_mock([step], page_setup=setup)
        self.assertFalse(result.passed)
        self.assertIn("healing required", result.message)

    def test_assert_step_passes_when_text_matches(self):
        def setup(page):
            loc = MagicMock()
            loc.count.return_value = 1
            elem = MagicMock()
            elem.inner_text.return_value = "Welcome, User!"
            elem.is_visible.return_value = True
            loc.first = elem
            page.locator.return_value = loc

        step = TestStep(
            action=StepAction.ASSERT,
            description="check welcome msg",
            locator=ElementLocator(css="#msg"),
            expected={"text": "Welcome"},
        )
        result = self._run_with_mock([step], page_setup=setup)
        self.assertTrue(result.passed)

    def test_assert_step_fails_when_text_mismatch(self):
        def setup(page):
            loc = MagicMock()
            loc.count.return_value = 1
            elem = MagicMock()
            elem.inner_text.return_value = "Error occurred"
            elem.is_visible.return_value = True
            loc.first = elem
            page.locator.return_value = loc

        step = TestStep(
            action=StepAction.ASSERT,
            description="check welcome",
            locator=ElementLocator(css="#msg"),
            expected={"text": "Welcome"},
        )
        result = self._run_with_mock([step], page_setup=setup)
        self.assertFalse(result.passed)
        self.assertIn("Assert failed", result.message)

    def test_report_contains_step_details(self):
        def setup(page):
            loc = MagicMock()
            loc.count.return_value = 1
            page.locator.return_value = loc

        steps = [
            TestStep(action=StepAction.NAVIGATE, description="nav", payload={"url": "https://x.com"}),
            TestStep(action=StepAction.CLICK, description="click", locator=ElementLocator(css="#btn")),
        ]
        result = self._run_with_mock(steps, page_setup=setup)
        self.assertTrue(result.passed)
        self.assertIsNotNone(result.report)
        self.assertEqual(len(result.report.steps), 2)
        self.assertTrue(all(s.passed for s in result.report.steps))

    def test_duration_is_set(self):
        step = TestStep(action=StepAction.NAVIGATE, description="nav", payload={"url": "https://x.com"})
        result = self._run_with_mock([step])
        self.assertGreaterEqual(result.duration_ms, 0)


if __name__ == "__main__":
    unittest.main()
