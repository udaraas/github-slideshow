from __future__ import annotations

from dataclasses import dataclass

from nextgen_test_automation.core.models import TestCase


@dataclass(slots=True)
class ExecutionResult:
    test_case_id: str
    passed: bool
    failed_step_index: int | None = None
    message: str = ""


class WebAutomationExecutor:
    """Execution skeleton for Playwright/Selenium backends."""

    def run(self, test_case: TestCase) -> ExecutionResult:
        if not test_case.steps:
            return ExecutionResult(test_case_id=test_case.id, passed=False, failed_step_index=None, message="No steps to execute")
        return ExecutionResult(test_case_id=test_case.id, passed=True, message="Execution skeleton completed")
