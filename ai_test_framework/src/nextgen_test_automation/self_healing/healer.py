from __future__ import annotations

from dataclasses import dataclass

from nextgen_test_automation.core.models import ElementLocator, HealingLog


@dataclass(slots=True)
class HealingCandidate:
    locator: ElementLocator
    confidence: float
    reason: str


class SelfHealingEngine:
    """Locator healing skeleton using fingerprint + semantic fallback strategy."""

    def propose(self, *, test_case_id: str, step_index: int, failed_locator: ElementLocator) -> HealingLog:
        candidate = HealingCandidate(locator=failed_locator, confidence=0.0, reason="No healing strategy implemented yet")
        return HealingLog(
            test_case_id=test_case_id,
            step_index=step_index,
            old_locator=failed_locator,
            new_locator=candidate.locator,
            reason=candidate.reason,
            confidence=candidate.confidence,
            approved=False,
        )
