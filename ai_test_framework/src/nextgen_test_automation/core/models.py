from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class StepAction(str, Enum):
    NAVIGATE = "navigate"
    CLICK = "click"
    TYPE = "type"
    ASSERT = "assert"
    API_CALL = "api_call"
    DB_QUERY = "db_query"
    SCREENSHOT = "screenshot"
    WAIT = "wait"
    SELECT = "select"
    HOVER = "hover"
    SCROLL = "scroll"
    KEY_PRESS = "key_press"
    ACCESSIBILITY_SCAN = "accessibility_scan"


@dataclass(slots=True)
class ElementLocator:
    css: str | None = None
    xpath: str | None = None
    text: str | None = None
    aria_label: str | None = None
    dom_fingerprint: dict[str, Any] = field(default_factory=dict)
    visual_fingerprint: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TestStep:
    action: StepAction
    description: str
    locator: ElementLocator | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    expected: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TestCase:
    name: str
    industry: str
    steps: list[TestStep] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class TestSuite:
    name: str
    description: str = ""
    test_cases: list[TestCase] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class HealingLog:
    test_case_id: str
    step_index: int
    old_locator: ElementLocator
    new_locator: ElementLocator
    reason: str
    confidence: float
    approved: bool = False
    created_at: datetime = field(default_factory=utc_now)
