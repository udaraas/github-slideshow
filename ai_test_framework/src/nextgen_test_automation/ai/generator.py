from __future__ import annotations

from dataclasses import dataclass

from nextgen_test_automation.core.models import TestCase, TestStep
from nextgen_test_automation.walkthrough.events import WalkthroughSession


@dataclass(slots=True)
class AITestCaseGenerator:
    model_name: str = "stub-model"

    def generate(self, session: WalkthroughSession, industry: str) -> TestCase:
        """Placeholder generator; replace with LLM-backed implementation."""
        steps = [
            TestStep(action=event.action, description=f"Auto-generated from walkthrough event {i + 1}", locator=event.locator, payload=event.payload)
            for i, event in enumerate(session.events)
        ]
        name = f"{session.app_name} - {session.platform} generated flow"
        return TestCase(name=name, industry=industry, steps=steps, tags=[industry, "ai-generated"])
