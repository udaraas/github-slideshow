from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from nextgen_test_automation.core.models import ElementLocator, StepAction


@dataclass(slots=True)
class WalkthroughEvent:
    action: StepAction
    locator: ElementLocator | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class WalkthroughSession:
    app_name: str
    platform: str
    actor: str = "default"
    events: list[WalkthroughEvent] = field(default_factory=list)
    session_id: str = field(default_factory=lambda: str(uuid4()))

    def record(self, event: WalkthroughEvent) -> None:
        self.events.append(event)
