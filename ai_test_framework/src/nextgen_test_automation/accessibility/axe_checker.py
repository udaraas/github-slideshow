"""axe-core WCAG accessibility scanner via Playwright page injection.

axe-core is the industry-standard open-source accessibility engine used by
Deque's toolchain, Chrome DevTools, and many CI pipelines.

Usage::

    checker = AxeAccessibilityChecker()
    report = checker.check(page)          # page is a Playwright Page object
    if not report.passed:
        for v in report.violations:
            print(v.impact, v.id, v.description)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# Pinned axe-core version served from cdnjs
_AXE_CDN_URL = (
    "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.9.1/axe.min.js"
)

# axe-core tag aliases for common WCAG conformance levels
WCAG_LEVELS: dict[str, list[str]] = {
    "A": ["wcag2a"],
    "AA": ["wcag2a", "wcag2aa"],
    "AAA": ["wcag2a", "wcag2aa", "wcag2aaa"],
    "best-practice": ["best-practice"],
}


@dataclass(slots=True)
class AccessibilityViolation:
    """A single axe-core violation."""

    id: str
    impact: str  # "critical" | "serious" | "moderate" | "minor"
    description: str
    help_url: str
    nodes_affected: int
    wcag_criteria: list[str] = field(default_factory=list)


@dataclass(slots=True)
class AccessibilityReport:
    """Full axe scan result for one page."""

    url: str
    wcag_level: str
    violations: list[AccessibilityViolation] = field(default_factory=list)
    passes: int = 0
    incomplete: int = 0
    inapplicable: int = 0

    @property
    def passed(self) -> bool:
        return len(self.violations) == 0

    @property
    def critical_count(self) -> int:
        return sum(1 for v in self.violations if v.impact == "critical")

    @property
    def serious_count(self) -> int:
        return sum(1 for v in self.violations if v.impact == "serious")

    def summary(self) -> str:
        if self.passed:
            return f"✓ No violations ({self.passes} rules passed)"
        parts = []
        if self.critical_count:
            parts.append(f"{self.critical_count} critical")
        if self.serious_count:
            parts.append(f"{self.serious_count} serious")
        other = len(self.violations) - self.critical_count - self.serious_count
        if other:
            parts.append(f"{other} other")
        return f"✗ {len(self.violations)} violations ({', '.join(parts)})"


class AxeAccessibilityChecker:
    """Inject axe-core into a live Playwright page and run a WCAG scan.

    Parameters
    ----------
    wcag_level:
        One of ``"A"``, ``"AA"`` (default), ``"AAA"``, or ``"best-practice"``.
    inject_timeout_ms:
        How long to wait for axe-core to load from the CDN.
    """

    def __init__(
        self,
        wcag_level: str = "AA",
        inject_timeout_ms: int = 15_000,
    ) -> None:
        self.wcag_level = wcag_level
        self.inject_timeout_ms = inject_timeout_ms

    def check(self, page: Any) -> AccessibilityReport:
        """Run a WCAG scan on *page* and return an :class:`AccessibilityReport`.

        *page* must be a Playwright ``Page`` object with an open document.
        """
        url = page.url
        tags = WCAG_LEVELS.get(self.wcag_level, ["wcag2aa"])
        tags_json = str(tags).replace("'", '"')  # valid JSON

        # Inject axe-core from CDN (safe to call multiple times — axe won't re-init)
        page.add_script_tag(url=_AXE_CDN_URL)
        page.wait_for_function(
            "() => typeof axe !== 'undefined'",
            timeout=self.inject_timeout_ms,
        )

        raw: dict = page.evaluate(
            f"""async () => {{
              return await axe.run(document, {{
                runOnly: {{ type: 'tag', values: {tags_json} }}
              }});
            }}"""
        )

        violations = [
            AccessibilityViolation(
                id=v["id"],
                impact=v.get("impact", "unknown"),
                description=v.get("description", ""),
                help_url=v.get("helpUrl", ""),
                nodes_affected=len(v.get("nodes", [])),
                wcag_criteria=[
                    tag
                    for tag in v.get("tags", [])
                    if tag.startswith("wcag")
                ],
            )
            for v in raw.get("violations", [])
        ]

        return AccessibilityReport(
            url=url,
            wcag_level=self.wcag_level,
            violations=violations,
            passes=len(raw.get("passes", [])),
            incomplete=len(raw.get("incomplete", [])),
            inapplicable=len(raw.get("inapplicable", [])),
        )
