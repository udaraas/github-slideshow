from __future__ import annotations

from dataclasses import replace
from datetime import timezone, datetime

from .models import TestCase, TestSuite


class InMemoryTestCaseManager:
    """Basic CRUD manager for suites and test cases."""

    def __init__(self) -> None:
        self._suites: dict[str, TestSuite] = {}

    def create_suite(self, suite: TestSuite) -> TestSuite:
        self._suites[suite.id] = suite
        return suite

    def list_suites(self) -> list[TestSuite]:
        return list(self._suites.values())

    def get_suite(self, suite_id: str) -> TestSuite | None:
        return self._suites.get(suite_id)

    def add_test_case(self, suite_id: str, test_case: TestCase) -> TestCase:
        suite = self._require_suite(suite_id)
        suite.test_cases.append(test_case)
        suite.updated_at = datetime.now(timezone.utc)
        return test_case

    def update_test_case(self, suite_id: str, test_case_id: str, patch: dict) -> TestCase:
        suite = self._require_suite(suite_id)
        for index, case in enumerate(suite.test_cases):
            if case.id == test_case_id:
                updated = replace(case, **patch, updated_at=datetime.now(timezone.utc))
                suite.test_cases[index] = updated
                suite.updated_at = datetime.now(timezone.utc)
                return updated
        raise KeyError(f"test case not found: {test_case_id}")

    def delete_test_case(self, suite_id: str, test_case_id: str) -> None:
        suite = self._require_suite(suite_id)
        before = len(suite.test_cases)
        suite.test_cases = [case for case in suite.test_cases if case.id != test_case_id]
        if len(suite.test_cases) == before:
            raise KeyError(f"test case not found: {test_case_id}")
        suite.updated_at = datetime.now(timezone.utc)

    def _require_suite(self, suite_id: str) -> TestSuite:
        suite = self.get_suite(suite_id)
        if suite is None:
            raise KeyError(f"suite not found: {suite_id}")
        return suite
