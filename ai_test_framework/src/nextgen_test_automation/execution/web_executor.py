"""Playwright-backed web executor with 3-tier locator resolution and screenshot capture."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nextgen_test_automation.core.models import StepAction, TestCase
from nextgen_test_automation.execution.locator_resolver import LocatorResolver
from nextgen_test_automation.reporting.report_models import StepReport, TestRunReport

try:
    from playwright.sync_api import sync_playwright
    _PLAYWRIGHT_AVAILABLE = True
except ImportError:  # pragma: no cover
    sync_playwright = None  # type: ignore[assignment]
    _PLAYWRIGHT_AVAILABLE = False


@dataclass(slots=True)
class ExecutionResult:
    test_case_id: str
    passed: bool
    failed_step_index: int | None = None
    message: str = ""
    report: TestRunReport | None = None
    screenshots: list[str] = field(default_factory=list)
    duration_ms: float = 0.0


class WebAutomationExecutor:
    """Playwright-backed web executor with 3-tier locator resolution.

    Usage::

        executor = WebAutomationExecutor(headless=True)
        result = executor.run(test_case)
    """

    def __init__(
        self,
        browser_type: str = "chromium",
        headless: bool = True,
        screenshot_dir: str | None = None,
        timeout_ms: int = 30_000,
    ) -> None:
        self.browser_type = browser_type
        self.headless = headless
        self.screenshot_dir = Path(screenshot_dir) if screenshot_dir else Path("screenshots")
        self.timeout_ms = timeout_ms
        self._resolver = LocatorResolver()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, test_case: TestCase) -> ExecutionResult:
        """Execute all steps in *test_case* and return a detailed result."""
        if not test_case.steps:
            return ExecutionResult(
                test_case_id=test_case.id, passed=False, message="No steps to execute"
            )

        if not _PLAYWRIGHT_AVAILABLE or sync_playwright is None:
            return ExecutionResult(
                test_case_id=test_case.id,
                passed=False,
                message="Playwright not installed. Run: pip install -e .[web]",
            )

        started = datetime.now(timezone.utc)
        report = TestRunReport(test_case_id=test_case.id, started_at=started)
        screenshots: list[str] = []
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)

        with sync_playwright() as pw:
            browser = getattr(pw, self.browser_type).launch(headless=self.headless)
            page = browser.new_page()
            page.set_default_timeout(self.timeout_ms)

            for i, step in enumerate(test_case.steps):
                step_passed, step_msg, ss = self._execute_step(page, step, i, test_case.id)
                if ss:
                    screenshots.append(ss)
                report.steps.append(
                    StepReport(step_index=i, passed=step_passed, message=step_msg)
                )

                if not step_passed:
                    browser.close()
                    report.finished_at = datetime.now(timezone.utc)
                    duration = (report.finished_at - started).total_seconds() * 1000
                    return ExecutionResult(
                        test_case_id=test_case.id,
                        passed=False,
                        failed_step_index=i,
                        message=step_msg,
                        report=report,
                        screenshots=screenshots,
                        duration_ms=duration,
                    )

            browser.close()

        report.finished_at = datetime.now(timezone.utc)
        duration = (report.finished_at - started).total_seconds() * 1000
        return ExecutionResult(
            test_case_id=test_case.id,
            passed=True,
            message="All steps passed",
            report=report,
            screenshots=screenshots,
            duration_ms=duration,
        )

    # ------------------------------------------------------------------
    # Internal step dispatch
    # ------------------------------------------------------------------

    def _execute_step(
        self, page: Any, step: Any, index: int, tc_id: str
    ) -> tuple[bool, str, str | None]:
        """Execute a single step. Returns (passed, message, screenshot_path|None)."""
        screenshot_path: str | None = None
        try:
            if step.action == StepAction.NAVIGATE:
                url = step.payload.get("url") or step.description
                page.goto(url)
                return True, f"Navigated to {url}", None

            if step.action == StepAction.SCREENSHOT:
                path = str(self.screenshot_dir / f"{tc_id}_step{index}.png")
                page.screenshot(path=path)
                return True, f"Screenshot saved: {path}", path

            if step.action == StepAction.WAIT:
                ms = int(step.payload.get("ms", 1000))
                page.wait_for_timeout(ms)
                return True, f"Waited {ms} ms", None

            if step.action == StepAction.SCROLL:
                x = int(step.payload.get("x", 0))
                y = int(step.payload.get("y", 500))
                page.evaluate(f"window.scrollBy({x}, {y})")
                return True, f"Scrolled by ({x}, {y})", None

            if step.action == StepAction.KEY_PRESS:
                key = step.payload.get("key", "Enter")
                page.keyboard.press(key)
                return True, f"Key pressed: {key}", None

            if step.action in (
                StepAction.CLICK,
                StepAction.TYPE,
                StepAction.SELECT,
                StepAction.HOVER,
                StepAction.ASSERT,
            ):
                if not step.locator:
                    return False, f"Step {index}: locator required for {step.action}", None

                resolved = self._resolver.resolve(page, step.locator)
                if resolved is None:
                    return (
                        False,
                        f"Step {index}: no element found — healing required "
                        f"(tried css={step.locator.css}, aria={step.locator.aria_label}, "
                        f"text={step.locator.text})",
                        None,
                    )

                elem = page.locator(resolved.selector).first

                if step.action == StepAction.CLICK:
                    elem.click()
                    return True, f"Clicked via {resolved.strategy}: {resolved.selector}", None

                if step.action == StepAction.HOVER:
                    elem.hover()
                    return True, f"Hovered via {resolved.strategy}: {resolved.selector}", None

                if step.action == StepAction.TYPE:
                    value = str(step.payload.get("value", ""))
                    elem.fill(value)
                    return True, f"Typed '{value}' via {resolved.strategy}", None

                if step.action == StepAction.SELECT:
                    value = str(step.payload.get("value", ""))
                    elem.select_option(value)
                    return True, f"Selected '{value}' via {resolved.strategy}", None

                if step.action == StepAction.ASSERT:
                    return self._run_assertion(page, elem, step, index, tc_id, resolved.strategy)

            if step.action == StepAction.ACCESSIBILITY_SCAN:
                # Handled externally via AxeAccessibilityChecker; skip silently here.
                return True, "Accessibility scan deferred to AxeAccessibilityChecker", None

            # Non-web actions (API_CALL, DB_QUERY) are skipped with a notice.
            return True, f"Step {index}: action '{step.action}' skipped (non-web)", None

        except Exception as exc:
            path = str(self.screenshot_dir / f"{tc_id}_error_step{index}.png")
            try:
                page.screenshot(path=path)
                screenshot_path = path
            except Exception:
                pass
            return False, f"Step {index} raised: {exc}", screenshot_path

    def _run_assertion(
        self, page: Any, elem: Any, step: Any, index: int, tc_id: str, strategy: str
    ) -> tuple[bool, str, str | None]:
        failures: list[str] = []

        expected_text = step.expected.get("text")
        if expected_text is not None:
            actual = elem.inner_text()
            if expected_text not in actual:
                failures.append(f"text: expected '{expected_text}', got '{actual}'")

        expected_value = step.expected.get("value")
        if expected_value is not None:
            actual_val = elem.input_value()
            if str(expected_value) not in actual_val:
                failures.append(f"value: expected '{expected_value}', got '{actual_val}'")

        if step.expected.get("visible", None) is True and not elem.is_visible():
            failures.append("element is not visible")

        if step.expected.get("visible", None) is False and elem.is_visible():
            failures.append("element is visible (expected hidden)")

        if failures:
            path = str(self.screenshot_dir / f"{tc_id}_assert_fail_step{index}.png")
            try:
                page.screenshot(path=path)
            except Exception:
                path = ""  # type: ignore[assignment]
            return False, f"Assert failed at step {index}: {'; '.join(failures)}", path or None

        return True, f"Assertion passed via {strategy}", None
