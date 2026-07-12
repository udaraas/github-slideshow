"""Unit tests for AxeAccessibilityChecker (Playwright mocked)."""
import unittest
from unittest.mock import MagicMock

from nextgen_test_automation.accessibility.axe_checker import (
    AccessibilityReport,
    AccessibilityViolation,
    AxeAccessibilityChecker,
    WCAG_LEVELS,
)


def _mock_page(axe_result: dict) -> MagicMock:
    page = MagicMock()
    page.url = "https://example.com/"
    page.evaluate.return_value = axe_result
    return page


_CLEAN_RESULT = {"violations": [], "passes": [{}] * 42, "incomplete": [], "inapplicable": []}

_VIOLATION_RESULT = {
    "violations": [
        {
            "id": "color-contrast",
            "impact": "serious",
            "description": "Elements must have sufficient color contrast",
            "helpUrl": "https://dequeuniversity.com/rules/axe/4.9/color-contrast",
            "tags": ["wcag2aa", "wcag143"],
            "nodes": [{"html": "<p class='light'>"}],
        },
        {
            "id": "image-alt",
            "impact": "critical",
            "description": "Images must have alternate text",
            "helpUrl": "https://dequeuniversity.com/rules/axe/4.9/image-alt",
            "tags": ["wcag2a", "wcag111"],
            "nodes": [{"html": "<img src='logo.png'>"}, {"html": "<img src='hero.jpg'>"}],
        },
    ],
    "passes": [{}] * 38,
    "incomplete": [{}] * 2,
    "inapplicable": [{}] * 5,
}


class TestAccessibilityReport(unittest.TestCase):

    def test_passed_when_no_violations(self):
        report = AccessibilityReport(url="https://x.com", wcag_level="AA")
        self.assertTrue(report.passed)

    def test_failed_when_violations_present(self):
        v = AccessibilityViolation(
            id="color-contrast", impact="serious",
            description="contrast", help_url="", nodes_affected=1
        )
        report = AccessibilityReport(url="https://x.com", wcag_level="AA", violations=[v])
        self.assertFalse(report.passed)

    def test_critical_count(self):
        vs = [
            AccessibilityViolation(id="a", impact="critical", description="", help_url="", nodes_affected=1),
            AccessibilityViolation(id="b", impact="serious", description="", help_url="", nodes_affected=1),
            AccessibilityViolation(id="c", impact="critical", description="", help_url="", nodes_affected=1),
        ]
        report = AccessibilityReport(url="", wcag_level="AA", violations=vs)
        self.assertEqual(report.critical_count, 2)

    def test_summary_clean(self):
        report = AccessibilityReport(url="", wcag_level="AA", violations=[], passes=42)
        self.assertIn("No violations", report.summary())

    def test_summary_with_violations(self):
        vs = [
            AccessibilityViolation(id="a", impact="critical", description="", help_url="", nodes_affected=1),
            AccessibilityViolation(id="b", impact="moderate", description="", help_url="", nodes_affected=1),
        ]
        report = AccessibilityReport(url="", wcag_level="AA", violations=vs)
        self.assertIn("critical", report.summary())


class TestAxeCheckerWithMockedPage(unittest.TestCase):

    def setUp(self):
        self.checker = AxeAccessibilityChecker(wcag_level="AA")

    def test_clean_page_returns_passed_report(self):
        page = _mock_page(_CLEAN_RESULT)
        report = self.checker.check(page)
        self.assertTrue(report.passed)
        self.assertEqual(len(report.violations), 0)
        self.assertEqual(report.passes, 42)

    def test_violation_page_returns_failed_report(self):
        page = _mock_page(_VIOLATION_RESULT)
        report = self.checker.check(page)
        self.assertFalse(report.passed)
        self.assertEqual(len(report.violations), 2)

    def test_violation_fields_populated(self):
        page = _mock_page(_VIOLATION_RESULT)
        report = self.checker.check(page)
        v0 = report.violations[0]
        self.assertEqual(v0.id, "color-contrast")
        self.assertEqual(v0.impact, "serious")
        self.assertEqual(v0.nodes_affected, 1)
        self.assertIn("wcag2aa", v0.wcag_criteria)

    def test_critical_violation_parsed(self):
        page = _mock_page(_VIOLATION_RESULT)
        report = self.checker.check(page)
        critical = [v for v in report.violations if v.impact == "critical"]
        self.assertEqual(len(critical), 1)
        self.assertEqual(critical[0].nodes_affected, 2)

    def test_report_url_set(self):
        page = _mock_page(_CLEAN_RESULT)
        report = self.checker.check(page)
        self.assertEqual(report.url, "https://example.com/")

    def test_wcag_level_stored(self):
        page = _mock_page(_CLEAN_RESULT)
        report = self.checker.check(page)
        self.assertEqual(report.wcag_level, "AA")

    def test_incomplete_count(self):
        page = _mock_page(_VIOLATION_RESULT)
        report = self.checker.check(page)
        self.assertEqual(report.incomplete, 2)

    def test_inapplicable_count(self):
        page = _mock_page(_VIOLATION_RESULT)
        report = self.checker.check(page)
        self.assertEqual(report.inapplicable, 5)

    def test_axe_script_added(self):
        page = _mock_page(_CLEAN_RESULT)
        self.checker.check(page)
        page.add_script_tag.assert_called_once()


class TestWcagLevels(unittest.TestCase):

    def test_aa_includes_a_and_aa(self):
        self.assertIn("wcag2a", WCAG_LEVELS["AA"])
        self.assertIn("wcag2aa", WCAG_LEVELS["AA"])

    def test_a_only_contains_a(self):
        self.assertNotIn("wcag2aa", WCAG_LEVELS["A"])

    def test_aaa_contains_all(self):
        self.assertIn("wcag2aaa", WCAG_LEVELS["AAA"])


if __name__ == "__main__":
    unittest.main()
