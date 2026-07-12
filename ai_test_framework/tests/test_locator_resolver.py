"""Unit tests for LocatorResolver (no browser required — uses mocks)."""
import unittest
from unittest.mock import MagicMock

from nextgen_test_automation.core.models import ElementLocator
from nextgen_test_automation.execution.locator_resolver import LocatorResolver, ResolvedLocator


def _mock_page(found_selectors: set[str]) -> MagicMock:
    """Return a mock Playwright Page that finds elements for selectors in *found_selectors*."""
    page = MagicMock()

    def locator_side_effect(selector):
        loc = MagicMock()
        loc.count.return_value = 1 if selector in found_selectors else 0
        return loc

    page.locator.side_effect = locator_side_effect
    return page


class TestLocatorResolver(unittest.TestCase):

    def setUp(self):
        self.resolver = LocatorResolver()

    # ── Tier 1: CSS ────────────────────────────────────────────────────────

    def test_resolves_css_when_present(self):
        page = _mock_page({"#login-btn"})
        loc = ElementLocator(css="#login-btn", text="Log in", aria_label="login")
        result = self.resolver.resolve(page, loc)
        self.assertIsNotNone(result)
        self.assertEqual(result.strategy, "css")
        self.assertEqual(result.selector, "#login-btn")

    # ── Tier 2: ARIA label ─────────────────────────────────────────────────

    def test_falls_back_to_aria_when_css_missing(self):
        # CSS is provided but not found; aria should match
        page = _mock_page({"[aria-label='login']"})
        loc = ElementLocator(css="#gone", aria_label="login")
        result = self.resolver.resolve(page, loc)
        self.assertIsNotNone(result)
        self.assertEqual(result.strategy, "aria")

    # ── Tier 3: Text ───────────────────────────────────────────────────────

    def test_falls_back_to_text(self):
        page = _mock_page({"text=Log in"})
        loc = ElementLocator(css="#gone", aria_label="missing", text="Log in")
        result = self.resolver.resolve(page, loc)
        self.assertIsNotNone(result)
        self.assertEqual(result.strategy, "text")

    # ── Tier 4: XPath ──────────────────────────────────────────────────────

    def test_falls_back_to_xpath(self):
        page = _mock_page({"xpath=//button[@id='x']"})
        loc = ElementLocator(xpath="//button[@id='x']")
        result = self.resolver.resolve(page, loc)
        self.assertIsNotNone(result)
        self.assertEqual(result.strategy, "xpath")

    # ── None case ──────────────────────────────────────────────────────────

    def test_returns_none_when_nothing_found(self):
        page = _mock_page(set())
        loc = ElementLocator(css="#x", aria_label="y", text="z")
        result = self.resolver.resolve(page, loc)
        self.assertIsNone(result)

    def test_returns_none_for_empty_locator(self):
        page = _mock_page(set())
        result = self.resolver.resolve(page, ElementLocator())
        self.assertIsNone(result)

    # ── Exception tolerance ────────────────────────────────────────────────

    def test_tolerates_playwright_exception(self):
        page = MagicMock()
        page.locator.side_effect = RuntimeError("browser crashed")
        loc = ElementLocator(css="#btn")
        result = self.resolver.resolve(page, loc)
        self.assertIsNone(result)

    # ── best_selector ──────────────────────────────────────────────────────

    def test_best_selector_priority(self):
        loc = ElementLocator(css="#id", text="text", aria_label="aria")
        self.assertEqual(self.resolver.best_selector(loc), "#id")

    def test_best_selector_aria_when_no_css(self):
        loc = ElementLocator(aria_label="submit", text="Submit")
        self.assertEqual(self.resolver.best_selector(loc), "[aria-label='submit']")

    def test_best_selector_returns_none_for_empty(self):
        self.assertIsNone(self.resolver.best_selector(ElementLocator()))


if __name__ == "__main__":
    unittest.main()
