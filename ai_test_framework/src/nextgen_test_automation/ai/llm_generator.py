"""LangChain/GPT-4o test case generator with a rule-based fallback.

When ``OPENAI_API_KEY`` is set and ``langchain-openai`` is installed the
generator calls GPT-4o to convert a :class:`WalkthroughSession` into a
structured :class:`TestCase`.  If the LLM is unavailable (no key, no
package, or a network error) it falls back to the rule-based stub in
:mod:`nextgen_test_automation.ai.generator`.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass

from nextgen_test_automation.ai.generator import AITestCaseGenerator
from nextgen_test_automation.core.models import ElementLocator, StepAction, TestCase, TestStep
from nextgen_test_automation.walkthrough.events import WalkthroughSession

try:
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage, SystemMessage
    _LANGCHAIN_AVAILABLE = True
except ImportError:
    ChatOpenAI = None  # type: ignore[assignment,misc]
    HumanMessage = None  # type: ignore[assignment]
    SystemMessage = None  # type: ignore[assignment]
    _LANGCHAIN_AVAILABLE = False


_SYSTEM_PROMPT = """You are a senior QA architect. Convert recorded browser walkthrough events \
into a structured JSON test case.

Output ONLY valid JSON that matches this exact schema (no markdown fences, no extra text):
{
  "name": "<descriptive test case name>",
  "steps": [
    {
      "action": "<navigate|click|type|select|hover|assert|screenshot|wait>",
      "description": "<human-readable description>",
      "locator_css": "<css selector or null>",
      "locator_text": "<visible text label or null>",
      "locator_aria_label": "<aria-label value or null>",
      "payload": {},
      "expected": {}
    }
  ],
  "tags": ["<tag1>", "<tag2>"]
}

Rules:
- Each test case covers a single business objective.
- For assert steps set "expected" with keys like "text", "value", or "visible".
- Prefer locator priority: aria_label > text > css.
- Tags should include the industry and "ai-generated".
"""


@dataclass(slots=True)
class LLMTestCaseGenerator:
    """LangChain-backed test case generator.

    Falls back to the rule-based stub when the LLM is unavailable so the
    tool is always usable even without an API key.
    """

    model_name: str = "gpt-4o"
    temperature: float = 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self, session: WalkthroughSession, industry: str) -> TestCase:
        """Generate a :class:`TestCase` from a recorded :class:`WalkthroughSession`."""
        if self._llm_available():
            try:
                return self._llm_generate(session, industry)
            except Exception:
                pass  # degrade gracefully
        return self._stub_generate(session, industry)

    # ------------------------------------------------------------------
    # LLM path
    # ------------------------------------------------------------------

    def _llm_available(self) -> bool:
        return _LANGCHAIN_AVAILABLE and bool(os.environ.get("OPENAI_API_KEY"))

    def _llm_generate(self, session: WalkthroughSession, industry: str) -> TestCase:
        events_text = "\n".join(
            f"  {i + 1}. action={e.action.value}"
            + (f"  css={e.locator.css}" if e.locator and e.locator.css else "")
            + (f"  aria={e.locator.aria_label}" if e.locator and e.locator.aria_label else "")
            + (f"  text={e.locator.text}" if e.locator and e.locator.text else "")
            + (f"  payload={e.payload}" if e.payload else "")
            for i, e in enumerate(session.events)
        )

        user_message = (
            f"App: {session.app_name}\n"
            f"Platform: {session.platform}\n"
            f"Industry: {industry}\n\n"
            f"Recorded events:\n{events_text}\n\n"
            "Generate the test case JSON."
        )

        llm = ChatOpenAI(model=self.model_name, temperature=self.temperature)
        response = llm.invoke(
            [SystemMessage(content=_SYSTEM_PROMPT), HumanMessage(content=user_message)]
        )
        return self._parse_response(str(response.content), session, industry)

    def _parse_response(
        self, content: str, session: WalkthroughSession, industry: str
    ) -> TestCase:
        data = json.loads(content.strip())
        steps: list[TestStep] = []
        for s in data.get("steps", []):
            css = s.get("locator_css")
            text = s.get("locator_text")
            aria = s.get("locator_aria_label")
            locator = ElementLocator(css=css, text=text, aria_label=aria) if any([css, text, aria]) else None
            steps.append(
                TestStep(
                    action=StepAction(s["action"]),
                    description=s.get("description", ""),
                    locator=locator,
                    payload=s.get("payload") or {},
                    expected=s.get("expected") or {},
                )
            )
        return TestCase(
            name=data.get("name", f"{session.app_name} generated flow"),
            industry=industry,
            steps=steps,
            tags=data.get("tags") or [industry, "ai-generated"],
        )

    # ------------------------------------------------------------------
    # Rule-based fallback
    # ------------------------------------------------------------------

    def _stub_generate(self, session: WalkthroughSession, industry: str) -> TestCase:
        return AITestCaseGenerator(model_name="stub").generate(session, industry)
