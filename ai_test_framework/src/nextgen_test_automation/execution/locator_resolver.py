"""3-tier locator resolution: CSS → ARIA label → visible text → XPath fallback."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from nextgen_test_automation.core.models import ElementLocator

if TYPE_CHECKING:
    pass  # Playwright Page type is injected at runtime to avoid a hard dep.


@dataclass(slots=True)
class ResolvedLocator:
    strategy: str  # "css" | "aria" | "text" | "xpath"
    selector: str


class LocatorResolver:
    """
    3-tier locator resolution strategy.

    Tier 1 — CSS selector       (fastest, most brittle)
    Tier 2 — ARIA label         (semantic, robust across re-styles)
    Tier 3 — Visible text       (natural-language fallback)
    Tier 4 — XPath              (last resort)
    """

    def resolve(self, page: Any, locator: ElementLocator) -> ResolvedLocator | None:
        """Try each tier in priority order; return the first one that finds an element.

        Returns None if no tier matches — signalling a healing opportunity.
        """
        candidates: list[tuple[str, str]] = []

        if locator.css:
            candidates.append(("css", locator.css))
        if locator.aria_label:
            candidates.append(("aria", f"[aria-label='{locator.aria_label}']"))
        if locator.text:
            candidates.append(("text", f"text={locator.text}"))
        if locator.xpath:
            candidates.append(("xpath", f"xpath={locator.xpath}"))

        for strategy, selector in candidates:
            try:
                if page.locator(selector).count() > 0:
                    return ResolvedLocator(strategy=strategy, selector=selector)
            except Exception:
                continue

        return None

    def best_selector(self, locator: ElementLocator) -> str | None:
        """Return the highest-priority non-None selector string without hitting the browser.

        Useful for generating readable test scripts.
        """
        if locator.css:
            return locator.css
        if locator.aria_label:
            return f"[aria-label='{locator.aria_label}']"
        if locator.text:
            return f"text={locator.text}"
        if locator.xpath:
            return f"xpath={locator.xpath}"
        return None
